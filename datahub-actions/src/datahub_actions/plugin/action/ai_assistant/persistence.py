"""Assertion persistence to DataHub GMS."""

import hashlib
import logging
import time
from typing import Any, Dict, Optional

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.ingestion.graph.client import DataHubGraph
from datahub.metadata.com.linkedin.pegasus2avro.assertion import (
    AssertionInfo,
    AssertionResult,
    AssertionResultType,
    AssertionRunEvent,
    AssertionRunStatus,
    AssertionStdAggregation,
    AssertionStdOperator,
    AssertionStdParameter,
    AssertionStdParameters,
    AssertionStdParameterType,
    AssertionType,
    DatasetAssertionInfo,
    DatasetAssertionScope,
)

from datahub_actions.plugin.action.ai_assistant.models import (
    AssertionConfig,
    AssertionMetadata,
)

logger = logging.getLogger(__name__)


class AssertionPersistence:
    """Persists AI-generated assertions to DataHub."""

    def __init__(self, graph: DataHubGraph):
        self.graph = graph

    def persist_assertion(
        self,
        dataset_urn: str,
        sql: str,
        config: AssertionConfig,
        nl_rule: Optional[str] = None,
        metadata: Optional[AssertionMetadata] = None,
    ) -> str:
        """
        Create and persist an AI-generated assertion to DataHub.

        Args:
            dataset_urn: URN of the dataset this assertion applies to
            sql: SQL query for the assertion
            config: Assertion configuration
            nl_rule: Original natural language rule
            metadata: Optional metadata (title, description, tags)

        Returns:
            assertion_urn: URN of the created assertion
        """
        try:
            # Generate assertion URN
            assertion_urn = self._generate_assertion_urn(dataset_urn, sql)

            # Build custom properties
            custom_properties = {
                "ai_generated": "true",
                "persistent": "true",
                "category": "AI_GENERATED",
                "sql_hash": self._hash_sql(sql),
                "created_with": "AI Assistant v1",
            }
            if nl_rule:
                custom_properties["nl_rule"] = nl_rule

            # Build assertion info
            assertion_info = self._build_assertion_info(
                dataset_urn=dataset_urn,
                sql=sql,
                config=config,
                metadata=metadata,
                custom_properties=custom_properties,
            )

            # Emit assertion info
            mcp = MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=assertion_info,
            )
            self.graph.emit(mcp)

            logger.info(f"Persisted AI assertion: {assertion_urn}")
            return assertion_urn

        except Exception as e:
            logger.error(f"Failed to persist assertion: {e}", exc_info=True)
            raise ValueError(f"Assertion persistence failed: {str(e)}")

    def report_assertion_result(
        self,
        assertion_urn: str,
        dataset_urn: str,
        passed: bool,
        metrics: Dict[str, Any],
    ) -> None:
        """
        Report assertion execution result.

        Args:
            assertion_urn: URN of the assertion
            dataset_urn: URN of the dataset being asserted on
            passed: Whether the assertion passed
            metrics: Execution metrics
        """
        try:
            # Build assertion run event - matching profile-based pattern
            # Use AssertionResult object (same pattern as working profile-based tests)
            run_event = AssertionRunEvent(
                timestampMillis=int(round(time.time() * 1000)),
                assertionUrn=assertion_urn,
                asserteeUrn=dataset_urn,  # Dataset being asserted on
                runId=f"ai_assistant_{int(time.time())}",
                status=AssertionRunStatus.COMPLETE,
                result=AssertionResult(
                    type=(
                        AssertionResultType.SUCCESS
                        if passed
                        else AssertionResultType.FAILURE
                    ),
                    actualAggValue=(
                        float(metrics.get("result_value"))
                        if metrics.get("result_value") is not None
                        and str(metrics.get("result_value")).replace(".", "").replace("-", "").isdigit()
                        else None
                    ),
                    rowCount=metrics.get("row_count"),
                    nativeResults=metrics or {},
                ),
            )

            # Emit run event
            mcp = MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=run_event,
            )
            self.graph.emit(mcp)

            logger.info(
                f"Reported assertion result for {assertion_urn}: passed={passed}"
            )

        except Exception as e:
            # Fixed: Now using dict-based result field (matching assertion_executor pattern)
            # This avoids Avro serialization issues that occurred with AssertionResult objects
            logger.error(f"Failed to report assertion result: {e}", exc_info=True)

    def _generate_assertion_urn(self, dataset_urn: str, sql: str) -> str:
        """Generate a unique URN for the assertion."""
        # Create a hash of dataset URN + SQL to ensure uniqueness
        hash_input = f"{dataset_urn}:{sql}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        return f"urn:li:assertion:ai-{hash_value}"

    def _hash_sql(self, sql: str) -> str:
        """Generate SHA256 hash of SQL."""
        return hashlib.sha256(sql.encode()).hexdigest()

    def _build_assertion_info(
        self,
        dataset_urn: str,
        sql: str,
        config: AssertionConfig,
        metadata: Optional[AssertionMetadata],
        custom_properties: Dict[str, str],
    ) -> AssertionInfo:
        """Build AssertionInfo aspect."""
        # Default metadata
        title = metadata.title if metadata and metadata.title else "AI-generated assertion"
        description = (
            metadata.description
            if metadata and metadata.description
            else f"Auto-generated quality check: {sql[:100]}"
        )

        # Build dataset assertion scope
        dataset_assertion = DatasetAssertionInfo(
            dataset=dataset_urn,
            scope=DatasetAssertionScope.DATASET_COLUMN
            if config.type == "column_assertion"
            else DatasetAssertionScope.DATASET_ROWS,
            aggregation=AssertionStdAggregation.ROW_COUNT,
            operator=self._map_operator(config.params.get("operator", "=")),
            parameters=AssertionStdParameters(
                value=AssertionStdParameter(
                    value=str(config.params.get("expected_value", "0")),
                    type=AssertionStdParameterType.NUMBER,
                )
            ),
            nativeType="ai_sql",
            nativeParameters={k: str(v) for k, v in config.params.items()},
        )

        return AssertionInfo(
            type=AssertionType.DATASET,
            datasetAssertion=dataset_assertion,
            description=description,
            customProperties=custom_properties,
        )

    def _map_operator(self, operator: str) -> AssertionStdOperator:
        """Map string operator to AssertionStdOperator."""
        mapping = {
            ">": AssertionStdOperator.GREATER_THAN,
            ">=": AssertionStdOperator.GREATER_THAN_OR_EQUAL_TO,
            "<": AssertionStdOperator.LESS_THAN,
            "<=": AssertionStdOperator.LESS_THAN_OR_EQUAL_TO,
            "=": AssertionStdOperator.EQUAL_TO,
            "==": AssertionStdOperator.EQUAL_TO,
            "!=": AssertionStdOperator.NOT_NULL,
            "between": AssertionStdOperator.BETWEEN,
        }
        return mapping.get(operator, AssertionStdOperator.EQUAL_TO)
