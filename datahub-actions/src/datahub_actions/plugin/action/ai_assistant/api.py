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
    DebugConnectionRequest,
    DebugConnectionResponse,
    SourceSummary,
    BackfillMappingRequest,
    BackfillMappingResponse,
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

    @app.post("/debug/connection-info", response_model=DebugConnectionResponse)
    async def debug_connection_info(request: DebugConnectionRequest):
        """Inspect how connector resolution would happen for a dataset (no query executed)."""
        try:
            dataset_urn = request.dataset_urn
            platform = None
            try:
                platform = sql_executor._extract_platform(dataset_urn)
            except Exception:
                platform = None

            mapping_property_urn = None
            try:
                bag = graph.get_entity_semityped(dataset_urn, aspects=["datasetProperties"])
                if bag and bag.get("datasetProperties"):
                    dp = bag["datasetProperties"]
                    custom = getattr(dp, "customProperties", None)
                    if isinstance(custom, dict):
                        mapping_property_urn = custom.get("datahub.ingestion.sourceUrn")
            except Exception:
                mapping_property_urn = None

            pipeline_name_urn = None
            try:
                # Use registry helper to read system metadata pipelineName
                pipeline_name_urn = connector_registry._get_source_urn_from_system_metadata(dataset_urn)  # type: ignore[attr-defined]
            except Exception:
                pipeline_name_urn = None

            selected_source = None
            try:
                src = connector_registry.find_ingestion_source_for_dataset(dataset_urn)
                if src:
                    selected_source = SourceSummary(
                        name=src.get("name"), urn=src.get("urn"), type=src.get("type")
                    )
            except Exception:
                selected_source = None

            candidates_count = 0
            try:
                # Count candidate sources for this platform
                sources_map = connector_registry._load_ingestion_sources()  # type: ignore[attr-defined]
                if platform and sources_map.get(platform):
                    candidates_count = len(sources_map[platform])
            except Exception:
                candidates_count = 0

            native_available = False
            engine_available = False
            try:
                native = connector_registry.get_native_connection(dataset_urn)
                if native is not None:
                    native_available = True
                    try:
                        native.close()
                    except Exception:
                        pass
            except Exception:
                native_available = False
            try:
                engine = connector_registry.get_engine(dataset_urn)
                if engine is not None:
                    engine_available = True
            except Exception:
                engine_available = False

            return DebugConnectionResponse(
                platform=platform,
                mapping_property_urn=mapping_property_urn,
                pipeline_name_urn=pipeline_name_urn,
                selected_source=selected_source,
                native_available=native_available,
                engine_available=engine_available,
                candidates_count=candidates_count,
            )

        except Exception as e:
            logger.error(f"Debug connection-info failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=str(e),
                    code="DEBUG_CONNECTION_INFO_FAILED",
                ).dict(),
            )

    @app.post("/debug/backfill-mapping", response_model=BackfillMappingResponse)
    async def backfill_mapping(request: BackfillMappingRequest):
        """
        Backfill dataset→ingestion source mapping by reading system metadata across common aspects
        and persisting it into DatasetProperties.customProperties.
        """
        try:
            urn = request.dataset_urn

            # 0) Respect explicit override
            if request.source_urn:
                try:
                    from datahub.metadata.schema_classes import DatasetPropertiesClass
                    existing = graph.get_entity_semityped(urn, aspects=["datasetProperties"]) or {}
                    dp = existing.get("datasetProperties") or DatasetPropertiesClass(customProperties={})
                    if dp.customProperties is None:
                        dp.customProperties = {}
                    dp.customProperties["datahub.ingestion.sourceUrn"] = request.source_urn
                    from datahub.emitter.mcp import MetadataChangeProposalWrapper
                    mcw = MetadataChangeProposalWrapper(entityUrn=urn, aspect=dp)
                    graph.emit(mcw)
                    return BackfillMappingResponse(ok=True, source_urn=request.source_urn)
                except Exception as e:
                    return BackfillMappingResponse(ok=False, error=str(e))

            # Try existing helpers first
            source_urn = None
            try:
                # 1) Explicit mapping on properties
                bag = graph.get_entity_semityped(urn, aspects=["datasetProperties"])
                if bag and bag.get("datasetProperties"):
                    dp = bag["datasetProperties"]
                    custom = getattr(dp, "customProperties", None)
                    if isinstance(custom, dict) and custom.get("datahub.ingestion.sourceUrn"):
                        return BackfillMappingResponse(ok=True, source_urn=custom.get("datahub.ingestion.sourceUrn"))
            except Exception:
                pass

            try:
                # 2) System metadata via registry helper on datasetProperties
                source_urn = connector_registry._get_source_urn_from_system_metadata(urn)  # type: ignore[attr-defined]
            except Exception:
                source_urn = None

            # 3) If still not found, scan a few aspects with system metadata
            if not source_urn:
                aspects_to_scan = ["schemaMetadata", "status", "browsePathsV2", "datasetProperties"]
                try:
                    entities = graph.get_entities(
                        entity_name="dataset",
                        urns=[urn],
                        aspects=aspects_to_scan,
                        with_system_metadata=True,
                    )
                    entry = entities.get(urn, {})
                    for aspect_name in aspects_to_scan:
                        tpl = entry.get(aspect_name)
                        if not tpl:
                            continue
                        _, sysmeta = tpl
                        if not sysmeta:
                            continue
                        props = getattr(sysmeta, "properties", None)
                        candidate = None
                        if isinstance(props, dict):
                            candidate = props.get("pipelineName")
                        candidate = candidate or getattr(sysmeta, "pipelineName", None)
                        if isinstance(candidate, str) and candidate.startswith("urn:li:dataHubIngestionSource:"):
                            source_urn = candidate
                            break
                except Exception:
                    pass

            if not source_urn or not isinstance(source_urn, str) or not source_urn.startswith("urn:li:dataHubIngestionSource:"):
                # 4) As a pragmatic fallback, if exactly one candidate source exists for the platform, select it.
                if request.auto_select_if_single:
                    try:
                        platform = sql_executor._extract_platform(urn)
                        sources_map = connector_registry._load_ingestion_sources()  # type: ignore[attr-defined]
                        candidates = sources_map.get(platform.lower(), []) if platform else []
                        if len(candidates) == 1:
                            source_urn = candidates[0].get("urn")
                    except Exception:
                        pass
                if not source_urn:
                    return BackfillMappingResponse(ok=False, error="Could not resolve pipelineName from system metadata")

            # Persist mapping
            try:
                from datahub.metadata.schema_classes import DatasetPropertiesClass
                existing = graph.get_entity_semityped(urn, aspects=["datasetProperties"]) or {}
                dp = existing.get("datasetProperties") or DatasetPropertiesClass(customProperties={})
                if dp.customProperties is None:
                    dp.customProperties = {}
                dp.customProperties["datahub.ingestion.sourceUrn"] = source_urn

                mcp = AssertionPersistence(graph)._build_mcp_for_assertion if False else None  # noqa: placeholder to satisfy import grouping
                # Emit via DataHubGraph
                from datahub.emitter.mcp import MetadataChangeProposalWrapper
                mcw = MetadataChangeProposalWrapper(entityUrn=urn, aspect=dp)
                graph.emit(mcw)
                return BackfillMappingResponse(ok=True, source_urn=source_urn)
            except Exception as e:
                return BackfillMappingResponse(ok=False, error=str(e))

        except Exception as e:
            logger.error(f"Backfill mapping failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=str(e),
                    code="BACKFILL_MAPPING_FAILED",
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
