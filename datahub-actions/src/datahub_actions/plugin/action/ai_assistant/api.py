"""FastAPI application for AI Assistant service."""

import logging
import os
from typing import Optional

from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from datahub_actions.api.action_graph import AcrylDataHubGraph
from datahub_actions.plugin.action.ai_assistant.executor import SQLExecutor
from datahub_actions.plugin.action.ai_assistant.llm_client import LLMClient
from datahub_actions.plugin.action.ai_assistant.models import (
    AssertionConfig,
    ErrorResponse,
    ExecuteRequest,
    ExecuteResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    SnowflakeSelfTestRequest,
    SnowflakeSelfTestResponse,
    PersistRequest,
    PersistResponse,
    ValidateRequest,
    ValidateResponse,
)
from datahub_actions.plugin.action.ai_assistant.persistence import (
    AssertionPersistence,
)
from datahub_actions.plugin.action.ai_assistant.validator import SchemaValidator
from datahub_actions.plugin.action.data_quality.connector_registry import (
    ConnectorRegistry,
)

logger = logging.getLogger(__name__)


def create_app(
    graph: Optional[DataHubGraph] = None,
    connector_registry: Optional[ConnectorRegistry] = None,
) -> FastAPI:
    """
    Create FastAPI application for AI Assistant.

    Args:
        graph: DataHub graph client (optional, will create if not provided)
        connector_registry: Connector registry (optional, will create if not provided)

    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="DataHub AI Assertion Builder",
        description="AI-powered data quality assertion generation",
        version="1.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize components
    if graph is None:
        gms_server = os.getenv("DATAHUB_GMS_URL", "http://datahub-gms:8080")
        config = DatahubClientConfig(server=gms_server)
        graph = DataHubGraph(config=config)
        logger.info(f"Initialized DataHub graph client: {gms_server}")

    if connector_registry is None:
        # Wrap DataHubGraph in AcrylDataHubGraph for ingestion source querying
        acryl_graph = AcrylDataHubGraph(baseGraph=graph)
        # Create connector registry - will auto-discover from ingestion sources
        connector_registry = ConnectorRegistry({}, graph=acryl_graph)
        logger.info("Initialized connector registry with auto-discovery")

    llm_client = LLMClient(
        provider=os.getenv("LLM_PROVIDER", "gemini"),
        api_key=os.getenv("GEMINI_API_KEY"),
        model=os.getenv("GEMINI_MODEL"),
    )

    schema_validator = SchemaValidator(graph)
    sql_executor = SQLExecutor(connector_registry, graph)
    assertion_persistence = AssertionPersistence(graph)

    logger.info("AI Assistant API initialized successfully")

    @app.get("/healthz", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(
            status="ok",
            llm_provider=os.getenv("LLM_PROVIDER", "gemini"),
        )

    @app.post("/validate", response_model=ValidateResponse)
    async def validate(request: ValidateRequest):
        """
        Validate if an NL rule is feasible for a dataset.

        Phase 1: Validate
        """
        try:
            logger.info(f"Validate request for {request.dataset_urn}")

            # Fetch schema
            schema = schema_validator.get_dataset_schema(request.dataset_urn)
            if not schema:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        error="Schema not found",
                        code="SCHEMA_NOT_FOUND",
                        details={"dataset_urn": request.dataset_urn},
                    ).dict(),
                )

            # Validate with LLM
            feasible, reasons = llm_client.validate_rule(request.nl_rule, schema)

            return ValidateResponse(
                feasible=feasible,
                reasons=reasons,
                schema=schema,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=str(e),
                    code="VALIDATION_FAILED",
                ).dict(),
            )

    @app.post("/generate", response_model=GenerateResponse)
    async def generate(request: GenerateRequest):
        """
        Generate SQL and assertion config from NL rule.

        Phase 2: Generate
        """
        try:
            logger.info(f"Generate request for {request.dataset_urn}")

            # Fetch schema
            schema = schema_validator.get_dataset_schema(request.dataset_urn)
            if not schema:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        error="Schema not found",
                        code="SCHEMA_NOT_FOUND",
                    ).dict(),
                )

            # Generate SQL with LLM
            sql, config_dict = llm_client.generate_sql_assertion(
                request.nl_rule, schema
            )

            # Validate SQL is read-only
            if not sql_executor._is_readonly_sql(sql):
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error="Generated SQL is not read-only",
                        code="GENERATION_FAILED",
                    ).dict(),
                )

            return GenerateResponse(
                sql=sql,
                config=AssertionConfig(**config_dict),
                guardrails={"readonly": True, "limits": {"rowLimit": 1000, "timeoutSec": 8}},
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=str(e),
                    code="GENERATION_FAILED",
                ).dict(),
            )

    @app.post("/execute", response_model=ExecuteResponse)
    async def execute(request: ExecuteRequest):
        """
        Execute generated SQL query.

        Phase 3: Execute
        """
        try:
            logger.info(f"Execute request for {request.dataset_urn}")

            # Execute SQL
            passed, metrics, error = sql_executor.execute_query(
                dataset_urn=request.dataset_urn,
                sql=request.sql,
                timeout_sec=8,
                row_limit=1000,
            )

            if error:
                return ExecuteResponse(
                    passed=False,
                    metrics=metrics,
                    error=error,
                )

            return ExecuteResponse(
                passed=passed,
                metrics=metrics,
            )

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=str(e),
                    code="EXECUTION_FAILED",
                ).dict(),
            )

    @app.post("/selftest/snowflake", response_model=SnowflakeSelfTestResponse)
    async def snowflake_selftest(request: SnowflakeSelfTestRequest):
        """Run a quick Snowflake connectivity test using the native connector.

        Executes SELECT CURRENT_VERSION() against the dataset's Snowflake connection.
        """
        try:
            platform = sql_executor._extract_platform(request.dataset_urn)
            if platform.lower() != "snowflake":
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error="Dataset is not a Snowflake dataset",
                        code="INVALID_PLATFORM",
                        details={"platform": platform},
                    ).dict(),
                )

            passed, metrics, error = sql_executor.execute_query(
                dataset_urn=request.dataset_urn,
                sql="SELECT CURRENT_VERSION()",
                timeout_sec=6,
                row_limit=1,
            )

            if error:
                return SnowflakeSelfTestResponse(ok=False, error=error)

            version = None
            if isinstance(metrics, dict):
                # Prefer result_value populated by the executor result parser
                version = str(metrics.get("result_value") or metrics.get("raw_result") or "") or None

            return SnowflakeSelfTestResponse(ok=passed, version=version)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Snowflake self-test failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=str(e),
                    code="SELF_TEST_FAILED",
                ).dict(),
            )

    @app.post("/persist", response_model=PersistResponse)
    async def persist(request: PersistRequest):
        """
        Persist assertion to DataHub.

        Phase 4: Persist
        """
        try:
            logger.info(f"Persist request for {request.dataset_urn}")

            # Persist assertion
            assertion_urn = assertion_persistence.persist_assertion(
                dataset_urn=request.dataset_urn,
                sql=request.sql,
                config=request.config,
                nl_rule=request.nl_rule,
                metadata=request.metadata,
            )

            # Report execution result if provided
            if request.passed is not None and request.metrics is not None:
                logger.info(f"Reporting assertion result: passed={request.passed}")
                assertion_persistence.report_assertion_result(
                    assertion_urn=assertion_urn,
                    dataset_urn=request.dataset_urn,
                    passed=request.passed,
                    metrics=request.metrics,
                )

            return PersistResponse(assertion_urn=assertion_urn)

        except Exception as e:
            logger.error(f"Persistence failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=str(e),
                    code="PERSIST_FAILED",
                ).dict(),
            )

    return app


# For standalone execution
if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8082)
