"""Assertion persistence to DataHub GMS."""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from datahub.emitter.mcp import MetadataChangeProposalWrapper
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

from datahub_actions.api.action_graph import AcrylDataHubGraph
from datahub_actions.plugin.action.ai_assistant.models import (
    AssertionConfig,
    AssertionMetadata,
)

logger = logging.getLogger(__name__)


class AssertionPersistence:
    """Persists AI-generated assertions to DataHub."""

    def __init__(self, graph: AcrylDataHubGraph):
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
                # UI-recognized bucket for now; ai_category retains the semantic intent
                "category": "CUSTOM_SQL",
                "ai_category": "AI_GENERATED",
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
            self.graph.graph.emit(mcp)

            logger.info(f"Persisted AI assertion: {assertion_urn}")
            return assertion_urn

        except Exception as e:
            logger.error(f"Failed to persist assertion: {e}", exc_info=True)
            raise ValueError(f"Assertion persistence failed: {str(e)}")

    def persist_assertion_with_result(
        self,
        dataset_urn: str,
        sql: str,
        config: AssertionConfig,
        passed: bool,
        metrics: Dict[str, Any],
        nl_rule: Optional[str] = None,
        metadata: Optional[AssertionMetadata] = None,
    ) -> str:
        """
        Create and persist an AI-generated assertion with its execution result to DataHub.

        This follows the PROFILE TEST pattern (WORKING!):
        1. Simple AssertionRunEvent (no BatchSpec, PartitionSpec, runtimeContext)
        2. Use graph.emit() (NOT DatahubRestEmitter)
        3. Emit only 2 aspects:
           - AssertionInfo (definition)
           - AssertionRunEvent (result - timeseries aspect)

        Args:
            dataset_urn: URN of the dataset this assertion applies to
            sql: SQL query for the assertion
            config: Assertion configuration
            passed: Whether the assertion passed
            metrics: Execution metrics
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
                # UI-recognized bucket for now; ai_category retains the semantic intent
                "category": "CUSTOM_SQL",
                "ai_category": "AI_GENERATED",
                "sql_hash": self._hash_sql(sql),
                "created_with": "AI Assistant v1",
            }
            if nl_rule:
                custom_properties["nl_rule"] = nl_rule

            # 1. Build AssertionInfo aspect
            assertion_info = self._build_assertion_info(
                dataset_urn=dataset_urn,
                sql=sql,
                config=config,
                metadata=metadata,
                custom_properties=custom_properties,
            )

            # 2. Build AssertionRunEvent aspect
            (
                native_results,
                row_count,
                actual_agg_value,
            ) = self._normalize_metrics(metrics or {})

            # Create simple AssertionRunEvent - following PROFILE TEST pattern (WORKING!)
            # NO BatchSpec, NO PartitionSpec, NO runtimeContext - just the essentials!
            # See: datahub-actions/plugin/action/data_quality/templates/base.py:163-184
            run_event = AssertionRunEvent(
                timestampMillis=int(round(time.time() * 1000)),
                assertionUrn=assertion_urn,
                asserteeUrn=dataset_urn,
                runId=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                result=AssertionResult(
                    type=(
                        AssertionResultType.SUCCESS
                        if passed
                        else AssertionResultType.FAILURE
                    ),
                    rowCount=row_count,
                    actualAggValue=actual_agg_value,
                    # MUST be str->str for Avro serialization (match profile-based pattern)
                    nativeResults=native_results,
                ),
                status=AssertionRunStatus.COMPLETE,
            )

            # Use graph.graph.emit() like profile tests (NOT DatahubRestEmitter!)
            # CRITICAL: self.graph is AcrylDataHubGraph, need .graph.emit() for underlying DataHubGraph
            # See: datahub-actions/plugin/action/data_quality/action.py:139
            logger.info(f"Emitting assertion to DataHub: {assertion_urn}")

            # Emit only 2 MCPs (like profile tests - NO DataPlatformInstance needed)
            assertion_info_mcp = MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=assertion_info,
            )
            self.graph.graph.emit(assertion_info_mcp)  # CRITICAL: .graph.graph (not just .graph)

            assertion_result_mcp = MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=run_event,
            )
            self.graph.graph.emit(assertion_result_mcp)  # CRITICAL: .graph.graph (not just .graph)

            logger.info(
                f"Successfully persisted AI assertion with result: {assertion_urn}, passed={passed}"
            )
            return assertion_urn

        except Exception as e:
            logger.error(f"Failed to persist assertion with result: {e}", exc_info=True)
            raise ValueError(f"Assertion persistence with result failed: {str(e)}")

    def report_assertion_result(
        self,
        assertion_urn: str,
        dataset_urn: str,
        passed: bool,
        metrics: Dict[str, Any],
        sql: str,
        config: AssertionConfig,
        nl_rule: Optional[str] = None,
        metadata: Optional[AssertionMetadata] = None,
    ) -> None:
        """
        DEPRECATED: Use persist_assertion_with_result instead.

        This method is kept for backward compatibility but should not be used.
        The new approach emits all 3 aspects atomically using DatahubRestEmitter.
        """
        logger.warning(
            "report_assertion_result is deprecated. Use persist_assertion_with_result instead."
        )

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

        # Derive correct AssertionType based on scope/aggregation/category
        # This ensures AI assertions appear in the correct UI group (SQL, Volume, Schema, etc.)
        # instead of always showing in "Other"
        assertion_type = self._derive_assertion_type(
            scope=dataset_assertion.scope,
            aggregation=dataset_assertion.aggregation,
            category=custom_properties.get("category", ""),
        )

        return AssertionInfo(
            type=assertion_type,
            datasetAssertion=dataset_assertion,
            description=description,
            customProperties=custom_properties,
        )

    def _normalize_metrics(
        self, metrics: Dict[str, Any]
    ) -> tuple[Dict[str, str], Optional[int], Optional[float]]:
        """
        Normalize executor metrics to the shapes expected by AssertionResult:
        - nativeResults must be a map of strings (Avro requirement)
        - rowCount should be an int when provided
        - actualAggValue should be a float when numeric, else None
        """
        native_results: Dict[str, str] = {}
        row_count: Optional[int] = None
        actual_value: Optional[float] = None

        # row_count -> rowCount
        if "row_count" in metrics:
            try:
                row_count = int(metrics["row_count"])
            except (ValueError, TypeError):
                row_count = None

        # result_value -> actualAggValue
        if "result_value" in metrics:
            try:
                actual_value = float(metrics["result_value"])
            except (ValueError, TypeError):
                actual_value = None

        # Everything else -> nativeResults (stringified)
        for k, v in metrics.items():
            try:
                native_results[k] = str(v)
            except Exception:
                native_results[k] = repr(v)

        return native_results, row_count, actual_value

    def _derive_assertion_type(
        self,
        scope: DatasetAssertionScope,
        aggregation: AssertionStdAggregation,
        category: str,
    ) -> AssertionType:
        """
        Map assertion characteristics to AssertionType for UI grouping.

        The DataHub UI groups assertions by AssertionType (enum), not by customProperties["category"].
        This method derives the correct AssertionType so AI assertions appear in the right UI group.

        Based on: datahub-actions/plugin/action/data_quality/templates/base.py:162-188
        """
        category_upper = (category or "").upper()

        # IMPORTANT: Check explicit category first before aggregation-based fallbacks
        # This ensures CUSTOM_SQL assertions don't get misclassified as VOLUME

        # Custom SQL → SQL (appears in "SQL" group)
        if category_upper == "CUSTOM_SQL":
            return AssertionType.SQL

        # Column-scoped assertions → Field (appears in "Column" group)
        if scope == DatasetAssertionScope.DATASET_COLUMN:
            return AssertionType.FIELD

        # Schema-related → DataSchema (appears in "Schema" group)
        if aggregation == AssertionStdAggregation.COLUMN_COUNT or category_upper == "SCHEMA":
            return AssertionType.DATA_SCHEMA

        # Volume-related → Volume (appears in "Volume" group)
        if aggregation == AssertionStdAggregation.ROW_COUNT or category_upper == "VOLUME":
            return AssertionType.VOLUME

        # Fallback → Dataset (appears in "Other" group)
        return AssertionType.DATASET

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
