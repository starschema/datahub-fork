"""Schema validator - fetches dataset schema from DataHub GMS."""

import logging
from typing import Optional

from datahub.ingestion.graph.client import DataHubGraph
from datahub.metadata.schema_classes import SchemaMetadataClass

from datahub_actions.plugin.action.ai_assistant.models import (
    ColumnSchema,
    DatasetSchema,
)

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates dataset schemas and NL rules."""

    def __init__(self, graph: DataHubGraph):
        self.graph = graph

    def get_dataset_schema(self, dataset_urn: str) -> Optional[DatasetSchema]:
        """
        Fetch dataset schema from DataHub GMS.

        Args:
            dataset_urn: URN of the dataset (e.g., urn:li:dataset:(urn:li:dataPlatform:snowflake,db.schema.table,PROD))

        Returns:
            DatasetSchema or None if not found
        """
        try:
            # Parse URN to extract platform and table info
            platform, table_parts = self._parse_dataset_urn(dataset_urn)

            # Fetch schema metadata aspect
            schema_metadata = self.graph.get_aspect(
                entity_urn=dataset_urn,
                aspect_type=SchemaMetadataClass
            )

            if not schema_metadata:
                logger.warning(f"No schema metadata found for {dataset_urn}")
                return None

            # Parse columns from schema metadata
            columns = []
            for field in schema_metadata.get("fields", []):
                col = ColumnSchema(
                    name=field.get("fieldPath", ""),
                    type=self._normalize_type(field.get("nativeDataType", "STRING")),
                    nullable=field.get("nullable", True),
                    primary_key=field.get("isPartOfKey", False),
                    description=field.get("description"),
                )
                columns.append(col)

            # Split table_parts into database.schema.table
            parts = table_parts.split(".")
            database = parts[0] if len(parts) > 2 else None
            schema_name = parts[1] if len(parts) > 2 else (parts[0] if len(parts) > 1 else None)
            table = parts[-1]

            dataset_schema = DatasetSchema(
                columns=columns,
                platform=platform,
                database=database,
                schema_name=schema_name,
                table=table,
            )

            logger.info(
                f"Fetched schema for {dataset_urn}: {len(columns)} columns"
            )
            return dataset_schema

        except Exception as e:
            logger.error(f"Failed to fetch schema for {dataset_urn}: {e}", exc_info=True)
            return None

    def _parse_dataset_urn(self, urn: str) -> tuple[str, str]:
        """
        Parse dataset URN to extract platform and table identifier.

        Example URN: urn:li:dataset:(urn:li:dataPlatform:snowflake,db.schema.table,PROD)
        Returns: ("snowflake", "db.schema.table")
        """
        try:
            # Format: urn:li:dataset:(urn:li:dataPlatform:PLATFORM,TABLE_ID,ENV)
            if not urn.startswith("urn:li:dataset:("):
                raise ValueError(f"Invalid dataset URN format: {urn}")

            # Remove prefix and trailing paren
            content = urn[len("urn:li:dataset:("):-1]

            # Split by comma
            parts = content.split(",")
            if len(parts) < 2:
                raise ValueError(f"Invalid dataset URN structure: {urn}")

            # Extract platform from urn:li:dataPlatform:PLATFORM
            platform_urn = parts[0]
            if not platform_urn.startswith("urn:li:dataPlatform:"):
                raise ValueError(f"Invalid platform URN: {platform_urn}")

            platform = platform_urn[len("urn:li:dataPlatform:"):]

            # Table identifier is the second part
            table_id = parts[1]

            return platform, table_id

        except Exception as e:
            logger.error(f"Failed to parse URN {urn}: {e}")
            raise ValueError(f"Invalid dataset URN: {urn}")

    def _normalize_type(self, native_type: str) -> str:
        """
        Normalize database-specific types to generic SQL types.

        Args:
            native_type: Database-specific type (e.g., VARCHAR(255), NUMBER(10,2))

        Returns:
            Normalized type (e.g., STRING, NUMBER, DATE)
        """
        native_upper = native_type.upper()

        # String types
        if any(t in native_upper for t in ["VARCHAR", "CHAR", "TEXT", "STRING"]):
            return "STRING"

        # Numeric types
        if any(t in native_upper for t in ["INT", "INTEGER", "BIGINT", "SMALLINT"]):
            return "INTEGER"
        if any(t in native_upper for t in ["DECIMAL", "NUMERIC", "NUMBER", "FLOAT", "DOUBLE"]):
            return "NUMBER"

        # Date/time types
        if any(t in native_upper for t in ["DATE"]):
            return "DATE"
        if any(t in native_upper for t in ["TIMESTAMP", "DATETIME"]):
            return "TIMESTAMP"
        if any(t in native_upper for t in ["TIME"]):
            return "TIME"

        # Boolean
        if any(t in native_upper for t in ["BOOL", "BOOLEAN"]):
            return "BOOLEAN"

        # JSON/Array
        if any(t in native_upper for t in ["JSON", "JSONB"]):
            return "JSON"
        if any(t in native_upper for t in ["ARRAY"]):
            return "ARRAY"

        # Default to STRING for unknown types
        logger.debug(f"Unknown type {native_type}, defaulting to STRING")
        return "STRING"
