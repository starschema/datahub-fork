"""SQL executor using DataHub Actions connectors."""

import logging
from typing import Any, Dict, Optional

from datahub.ingestion.graph.client import DataHubGraph
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from datahub_actions.plugin.action.ai_assistant.ingestion_source_client import (
    IngestionSourceClient,
)
from datahub_actions.plugin.action.data_quality.connector_registry import (
    ConnectorRegistry,
)

logger = logging.getLogger(__name__)


class SQLExecutor:
    """Executes read-only SQL queries using DataHub connectors."""

    def __init__(self, connector_registry: ConnectorRegistry, graph: DataHubGraph):
        self.connector_registry = connector_registry
        self.graph = graph
        self.ingestion_source_client = IngestionSourceClient(graph)

    def execute_query(
        self,
        dataset_urn: str,
        sql: str,
        timeout_sec: int = 8,
        row_limit: int = 1000,
    ) -> tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Execute SQL query against the dataset's database.

        Args:
            dataset_urn: URN of the dataset to execute against
            sql: Read-only SQL query
            timeout_sec: Query timeout in seconds
            row_limit: Maximum rows to process

        Returns:
            (passed: bool, metrics: Dict, error: Optional[str])
        """
        try:
            # Validate SQL is read-only
            if not self._is_readonly_sql(sql):
                return False, {}, "SQL must be read-only (SELECT only)"

            platform = self._extract_platform(dataset_urn)

            # Try native connector first (dataset-specific, all platforms)
            try:
                native_conn = self.connector_registry.get_native_connection(dataset_urn)
            except Exception as e:
                native_conn = None
                logger.debug(f"Native connection lookup failed: {e}")

            if native_conn is not None:
                logger.info(
                    f"Executing SQL via native connector for {dataset_urn}: {sql[:100]}..."
                )
                cursor = native_conn.native_connection().cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                columns = [d[0] for d in cursor.description] if cursor.description else []
                cursor.close()
                native_conn.close()

                result_list = [
                    dict(zip(columns, row)) for row in rows[:row_limit]
                ] if rows else []
                passed, metrics = self._parse_query_result(result_list, row_limit)
                return passed, metrics, None

            # Fallback: SQLAlchemy via ConnectorRegistry (works for all platforms)
            engine = self.connector_registry.get_engine(dataset_urn)
            
            if not engine:
                return (
                    False,
                    {},
                    "No database connection available (native or SQLAlchemy) for this dataset. "
                    "Ensure ingestion source exists and secrets resolve, or configure a connector.",
                )

            # Execute query with SQLAlchemy
            logger.info(f"Executing SQL for {dataset_urn}: {sql[:100]}...")
            with engine.connect() as connection:
                # Execute raw SQL using text()
                result = connection.execute(text(sql))

                # Fetch results
                rows = result.fetchall()
                if rows:
                    columns = result.keys()
                    # Convert to list of dicts
                    result_list = [dict(zip(columns, row)) for row in rows[:row_limit]]
                else:
                    result_list = []

            # Parse result
            passed, metrics = self._parse_query_result(result_list, row_limit)

            logger.info(
                f"Query executed successfully for {dataset_urn}: passed={passed}"
            )
            return passed, metrics, None

        except Exception as e:
            logger.error(f"Query execution failed for {dataset_urn}: {e}", exc_info=True)
            return False, {}, str(e)

    def _execute_snowflake_native(
        self, dataset_urn: str, sql: str, row_limit: int
    ) -> tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Execute query using native snowflake.connector (bypasses SQLAlchemy auth issues).

        Args:
            dataset_urn: URN of the dataset
            sql: SQL query to execute
            row_limit: Maximum rows to process

        Returns:
            (passed: bool, metrics: Dict, error: Optional[str])
        """
        try:
            # Resolve and log the exact ingestion source used for this dataset
            selected_source = None
            try:
                selected_source = self.connector_registry.find_ingestion_source_for_dataset(
                    dataset_urn
                )
                if selected_source:
                    logger.info(
                        "Using ingestion source for execution: name=%s urn=%s",
                        selected_source.get("name"),
                        selected_source.get("urn"),
                    )
            except Exception:
                # Non-fatal for execution; continue to obtain a connection
                logger.debug("Could not pre-resolve selected ingestion source for logging")

            # Get dataset-specific native connection selected from the exact ingestion source
            connection = self.connector_registry.get_native_connection(dataset_urn)

            if not connection:
                return False, {}, "No native Snowflake connection available for this dataset"

            logger.info(f"Executing SQL via native connector for {dataset_urn}: {sql[:100]}...")
            cursor = connection.native_connection().cursor()
            cursor.execute(sql)

            # Fetch results
            rows = cursor.fetchall()
            if rows:
                columns = [desc[0] for desc in cursor.description]
                # Convert to list of dicts
                result_list = [dict(zip(columns, row)) for row in rows[:row_limit]]
            else:
                result_list = []

            cursor.close()
            connection.close()

            # Parse result
            passed, metrics = self._parse_query_result(result_list, row_limit)

            logger.info(f"Query executed successfully for {dataset_urn}: passed={passed}")
            return passed, metrics, None

        except Exception as e:
            logger.error(f"Snowflake native query execution failed: {e}", exc_info=True)
            return False, {}, str(e)

    def _is_readonly_sql(self, sql: str) -> bool:
        """
        Validate SQL is read-only (no DDL/DML).

        Args:
            sql: SQL query to validate

        Returns:
            True if read-only, False otherwise
        """
        sql_upper = sql.upper().strip()

        # Forbidden keywords
        forbidden = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "MERGE",
            "GRANT",
            "REVOKE",
        ]

        for keyword in forbidden:
            if keyword in sql_upper:
                logger.warning(f"SQL contains forbidden keyword: {keyword}")
                return False

        # Must start with SELECT or WITH (for CTEs)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            logger.warning("SQL must start with SELECT or WITH")
            return False

        return True

    def _extract_platform(self, dataset_urn: str) -> str:
        """Extract platform from dataset URN."""
        try:
            # Format: urn:li:dataset:(urn:li:dataPlatform:PLATFORM,...)
            if "urn:li:dataPlatform:" not in dataset_urn:
                raise ValueError(f"Invalid dataset URN: {dataset_urn}")

            start = dataset_urn.index("urn:li:dataPlatform:") + len("urn:li:dataPlatform:")
            end = dataset_urn.index(",", start)
            platform = dataset_urn[start:end]

            return platform

        except Exception as e:
            logger.error(f"Failed to extract platform from {dataset_urn}: {e}")
            raise ValueError(f"Invalid dataset URN format: {dataset_urn}")

    def _parse_query_result(
        self, result: Any, row_limit: int
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Parse query result and determine if assertion passed.

        Args:
            result: Query result from connector
            row_limit: Maximum rows to process

        Returns:
            (passed: bool, metrics: Dict)
        """
        try:
            metrics = {}

            # Handle different result types
            if result is None:
                return True, {"row_count": 0}

            # If result is a list of rows
            if isinstance(result, list):
                row_count = len(result)
                metrics["row_count"] = min(row_count, row_limit)

                # If single row with single value, extract it
                if row_count == 1 and len(result[0]) == 1:
                    value = list(result[0].values())[0] if isinstance(result[0], dict) else result[0][0]
                    metrics["result_value"] = value

                    # Determine pass/fail based on value
                    # Convention: 0 = fail, non-zero = pass (for COUNT queries)
                    # Or: 1 = pass, 0 = fail (for boolean checks)
                    passed = bool(value) if isinstance(value, (int, bool)) else True
                else:
                    # Multiple rows - assume query is checking for violations
                    # If rows returned, there are violations (fail)
                    passed = row_count == 0

                return passed, metrics

            # If result is a single value
            if isinstance(result, (int, float, bool)):
                metrics["result_value"] = result
                passed = bool(result)
                return passed, metrics

            # Unknown result type - assume pass
            logger.warning(f"Unknown result type: {type(result)}")
            return True, {"raw_result": str(result)}

        except Exception as e:
            logger.error(f"Failed to parse query result: {e}")
            return False, {"error": str(e)}
