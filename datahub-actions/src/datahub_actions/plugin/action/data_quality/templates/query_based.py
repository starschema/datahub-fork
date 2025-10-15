# Copyright 2021 Acryl Data, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy import create_engine

from datahub.metadata.com.linkedin.pegasus2avro.assertion import (
    AssertionStdAggregation,
    AssertionStdOperator,
    AssertionStdParameter,
    AssertionStdParameters,
    AssertionStdParameterType,
    DatasetAssertionScope,
)
from datahub.metadata.schema_classes import DatasetProfileClass
from datahub_actions.plugin.action.data_quality.templates.base import (
    BaseTestTemplate,
    TestResult,
)

if TYPE_CHECKING:
    from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class QueryBasedTestTemplate(BaseTestTemplate):
    """
    Base class for query-based tests that need database connections.

    Provides support for connector registry to look up connections by platform.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connector_registry: Optional["ConnectorRegistry"] = None

    def set_connector_registry(self, registry: "ConnectorRegistry") -> None:
        """Set the connector registry for this test."""
        self.connector_registry = registry

    def get_connection_string(self) -> Optional[str]:
        """
        Get connection string for this test.

        Tries the following in order:
        1. `connection_string` parameter (backward compatibility)
        2. Connector registry lookup by dataset URN

        Returns:
            Connection string or None if not found
        """
        # First check if connection_string is directly provided in params
        if "connection_string" in self.params:
            return self.params["connection_string"]

        # Otherwise, try connector registry
        if self.connector_registry:
            return self.connector_registry.get_connection_string(self.dataset_urn)

        return None


class ColumnValueRangeTest(QueryBasedTestTemplate):
    """
    Query-based test that validates column values fall within expected range.

    Executes SQL queries against the database to check min/max values.
    Requires connection_string parameter in test config.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_value_range test")

    def get_test_type(self) -> str:
        return "column_value_range"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.IDENTITY

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        min_value = self.params.get("min_value")
        max_value = self.params.get("max_value")

        return AssertionStdParameters(
            minValue=AssertionStdParameter(
                value=str(min_value) if min_value else None,
                type=AssertionStdParameterType.NUMBER,
            ),
            maxValue=AssertionStdParameter(
                value=str(max_value) if max_value else None,
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        """
        Execute query to validate column value range.

        Connection string can be provided via:
        1. connection_string parameter (backward compatibility)
        2. Connector registry lookup by platform
        """
        connection_string = self.get_connection_string()
        if not connection_string:
            return TestResult(
                success=False,
                native_results={
                    "error": "connection_string parameter is required for query-based tests"
                },
            )

        # Parse table name from dataset URN
        # Format: urn:li:dataset:(urn:li:dataPlatform:mysql,db.schema.table,PROD)
        try:
            table_name = self._parse_table_name_from_urn()
        except Exception as e:
            logger.error(f"Failed to parse table name from URN: {e}")
            return TestResult(
                success=False,
                native_results={"error": f"Failed to parse table name: {str(e)}"},
            )

        try:
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                # Query for values outside the expected range
                min_value = float(self.params.get("min_value", float("-inf")))
                max_value = float(self.params.get("max_value", float("inf")))

                # Count rows where value is outside range
                query = sa.text(
                    f"""
                    SELECT COUNT(*) as invalid_count,
                           MIN({self.column}) as actual_min,
                           MAX({self.column}) as actual_max
                    FROM {table_name}
                    WHERE {self.column} < :min_value OR {self.column} > :max_value
                """
                )

                result = conn.execute(
                    query, {"min_value": min_value, "max_value": max_value}
                ).fetchone()

                invalid_count = result[0] if result else 0
                actual_min = result[1] if result and len(result) > 1 else None
                actual_max = result[2] if result and len(result) > 2 else None

                success = invalid_count == 0

                return TestResult(
                    success=success,
                    actual_value=f"{actual_min} to {actual_max}",
                    native_results={
                        "invalid_count": str(invalid_count),
                        "actual_min": str(actual_min) if actual_min is not None else "N/A",
                        "actual_max": str(actual_max) if actual_max is not None else "N/A",
                        "expected_range": f"[{min_value}, {max_value}]",
                        "status": "PASS" if success else "FAIL",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return TestResult(
                success=False,
                native_results={"error": f"Query execution failed: {str(e)}"},
            )

    def _parse_table_name_from_urn(self) -> str:
        """
        Parse table name from dataset URN.

        Example URN: urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)
        Returns: mydb.users
        """
        urn_parts = self.dataset_urn.split(",")
        if len(urn_parts) < 2:
            raise ValueError(f"Invalid dataset URN format: {self.dataset_urn}")

        # Second part contains the table identifier
        table_identifier = urn_parts[1]
        return table_identifier


class ColumnValuesInSetTest(QueryBasedTestTemplate):
    """Query-based test that validates column values are in allowed set."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_values_in_set test")

    def get_test_type(self) -> str:
        return "column_values_in_set"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.IN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.IDENTITY

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        connection_string = self.get_connection_string()
        if not connection_string:
            return TestResult(
                success=False,
                native_results={"error": "connection_string parameter is required"},
            )

        value_set = self.params.get("value_set")
        if not value_set:
            return TestResult(
                success=False,
                native_results={"error": "value_set parameter is required"},
            )

        values = [v.strip() for v in str(value_set).split(",")]

        try:
            table_name = self._parse_table_name_from_urn()
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                # Count rows where value is not in the allowed set
                placeholders = ", ".join([f":value_{i}" for i in range(len(values))])
                query = sa.text(
                    f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {self.column} NOT IN ({placeholders})
                    AND {self.column} IS NOT NULL
                    """
                )

                params = {f"value_{i}": v for i, v in enumerate(values)}
                result = conn.execute(query, params).fetchone()
                invalid_count = result[0] if result else 0
                success = invalid_count == 0

                return TestResult(
                    success=success,
                    native_results={
                        "invalid_count": str(invalid_count),
                        "allowed_values": value_set,
                        "status": "PASS" if success else "FAIL",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return TestResult(
                success=False,
                native_results={"error": f"Query execution failed: {str(e)}"},
            )

    def _parse_table_name_from_urn(self) -> str:
        urn_parts = self.dataset_urn.split(",")
        if len(urn_parts) < 2:
            raise ValueError(f"Invalid dataset URN format: {self.dataset_urn}")
        return urn_parts[1]


class ColumnValuesNotInSetTest(QueryBasedTestTemplate):
    """Query-based test that validates column values are not in forbidden set."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_values_not_in_set test")

    def get_test_type(self) -> str:
        return "column_values_not_in_set"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.NOT_IN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.IDENTITY

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        connection_string = self.get_connection_string()
        if not connection_string:
            return TestResult(
                success=False,
                native_results={"error": "connection_string parameter is required"},
            )

        value_set = self.params.get("value_set")
        if not value_set:
            return TestResult(
                success=False,
                native_results={"error": "value_set parameter is required"},
            )

        values = [v.strip() for v in str(value_set).split(",")]

        try:
            table_name = self._parse_table_name_from_urn()
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                # Count rows where value is in the forbidden set
                placeholders = ", ".join([f":value_{i}" for i in range(len(values))])
                query = sa.text(
                    f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {self.column} IN ({placeholders})
                    """
                )

                params = {f"value_{i}": v for i, v in enumerate(values)}
                result = conn.execute(query, params).fetchone()
                invalid_count = result[0] if result else 0
                success = invalid_count == 0

                return TestResult(
                    success=success,
                    native_results={
                        "invalid_count": str(invalid_count),
                        "forbidden_values": value_set,
                        "status": "PASS" if success else "FAIL",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return TestResult(
                success=False,
                native_results={"error": f"Query execution failed: {str(e)}"},
            )

    def _parse_table_name_from_urn(self) -> str:
        urn_parts = self.dataset_urn.split(",")
        if len(urn_parts) < 2:
            raise ValueError(f"Invalid dataset URN format: {self.dataset_urn}")
        return urn_parts[1]


class ColumnValuesMatchRegexTest(QueryBasedTestTemplate):
    """Query-based test that validates column values match regex pattern."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_values_match_regex test")

    def get_test_type(self) -> str:
        return "column_values_match_regex"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.REGEX_MATCH

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.IDENTITY

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        connection_string = self.get_connection_string()
        if not connection_string:
            return TestResult(
                success=False,
                native_results={"error": "connection_string parameter is required"},
            )

        regex = self.params.get("regex")
        if not regex:
            return TestResult(
                success=False,
                native_results={"error": "regex parameter is required"},
            )

        try:
            table_name = self._parse_table_name_from_urn()
            engine = create_engine(connection_string)

            # Use platform-specific regex syntax
            dialect_name = engine.dialect.name
            if dialect_name == "mysql":
                regex_operator = "REGEXP"
            elif dialect_name in ["postgresql", "postgres"]:
                regex_operator = "~"
            else:
                regex_operator = "REGEXP"  # Default

            with engine.connect() as conn:
                # Count rows where value doesn't match regex
                query = sa.text(
                    f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {self.column} IS NOT NULL
                    AND NOT ({self.column} {regex_operator} :regex_pattern)
                    """
                )

                result = conn.execute(query, {"regex_pattern": regex}).fetchone()
                invalid_count = result[0] if result else 0
                success = invalid_count == 0

                return TestResult(
                    success=success,
                    native_results={
                        "invalid_count": str(invalid_count),
                        "regex_pattern": regex,
                        "status": "PASS" if success else "FAIL",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return TestResult(
                success=False,
                native_results={"error": f"Query execution failed: {str(e)}"},
            )

    def _parse_table_name_from_urn(self) -> str:
        urn_parts = self.dataset_urn.split(",")
        if len(urn_parts) < 2:
            raise ValueError(f"Invalid dataset URN format: {self.dataset_urn}")
        return urn_parts[1]


class ColumnValuesNotMatchRegexTest(QueryBasedTestTemplate):
    """Query-based test that validates column values don't match regex pattern."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_values_not_match_regex test")

    def get_test_type(self) -> str:
        return "column_values_not_match_regex"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.NOT_REGEX_MATCH

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.IDENTITY

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        connection_string = self.get_connection_string()
        if not connection_string:
            return TestResult(
                success=False,
                native_results={"error": "connection_string parameter is required"},
            )

        regex = self.params.get("regex")
        if not regex:
            return TestResult(
                success=False,
                native_results={"error": "regex parameter is required"},
            )

        try:
            table_name = self._parse_table_name_from_urn()
            engine = create_engine(connection_string)

            # Use platform-specific regex syntax
            dialect_name = engine.dialect.name
            if dialect_name == "mysql":
                regex_operator = "REGEXP"
            elif dialect_name in ["postgresql", "postgres"]:
                regex_operator = "~"
            else:
                regex_operator = "REGEXP"  # Default

            with engine.connect() as conn:
                # Count rows where value matches the forbidden regex
                query = sa.text(
                    f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {self.column} {regex_operator} :regex_pattern
                    """
                )

                result = conn.execute(query, {"regex_pattern": regex}).fetchone()
                invalid_count = result[0] if result else 0
                success = invalid_count == 0

                return TestResult(
                    success=success,
                    native_results={
                        "invalid_count": str(invalid_count),
                        "forbidden_regex_pattern": regex,
                        "status": "PASS" if success else "FAIL",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return TestResult(
                success=False,
                native_results={"error": f"Query execution failed: {str(e)}"},
            )

    def _parse_table_name_from_urn(self) -> str:
        urn_parts = self.dataset_urn.split(",")
        if len(urn_parts) < 2:
            raise ValueError(f"Invalid dataset URN format: {self.dataset_urn}")
        return urn_parts[1]


class ColumnLengthBetweenTest(QueryBasedTestTemplate):
    """Query-based test that validates column string length is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_length_between test")

    def get_test_type(self) -> str:
        return "column_length_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.LENGTH

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        min_length = self.params.get("min_length")
        max_length = self.params.get("max_length")
        return AssertionStdParameters(
            minValue=AssertionStdParameter(
                value=str(min_length) if min_length else None,
                type=AssertionStdParameterType.NUMBER,
            ),
            maxValue=AssertionStdParameter(
                value=str(max_length) if max_length else None,
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        connection_string = self.get_connection_string()
        if not connection_string:
            return TestResult(
                success=False,
                native_results={"error": "connection_string parameter is required"},
            )

        min_length = int(self.params.get("min_length", 0))
        max_length = self.params.get("max_length")

        try:
            table_name = self._parse_table_name_from_urn()
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                # Count rows where length is outside range
                query_parts = [
                    f"SELECT COUNT(*) as invalid_count FROM {table_name}",
                    f"WHERE {self.column} IS NOT NULL",
                ]

                if max_length is not None:
                    query_parts.append(
                        f"AND (LENGTH({self.column}) < :min_length OR LENGTH({self.column}) > :max_length)"
                    )
                    params = {"min_length": min_length, "max_length": int(max_length)}
                else:
                    query_parts.append(f"AND LENGTH({self.column}) < :min_length")
                    params = {"min_length": min_length}

                query = sa.text(" ".join(query_parts))
                result = conn.execute(query, params).fetchone()
                invalid_count = result[0] if result else 0
                success = invalid_count == 0

                return TestResult(
                    success=success,
                    native_results={
                        "invalid_count": str(invalid_count),
                        "min_length": str(min_length),
                        "max_length": str(max_length) if max_length else "unlimited",
                        "status": "PASS" if success else "FAIL",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return TestResult(
                success=False,
                native_results={"error": f"Query execution failed: {str(e)}"},
            )

    def _parse_table_name_from_urn(self) -> str:
        urn_parts = self.dataset_urn.split(",")
        if len(urn_parts) < 2:
            raise ValueError(f"Invalid dataset URN format: {self.dataset_urn}")
        return urn_parts[1]


class TableCustomSQLTest(QueryBasedTestTemplate):
    """Query-based test that executes custom SQL and validates result."""

    def get_test_type(self) -> str:
        return "table_custom_sql"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_ROWS

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.EQUAL_TO

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation._NATIVE_

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        connection_string = self.get_connection_string()
        if not connection_string:
            return TestResult(
                success=False,
                native_results={"error": "connection_string parameter is required"},
            )

        sql = self.params.get("sql")
        if not sql:
            return TestResult(
                success=False,
                native_results={"error": "sql parameter is required"},
            )

        expected_result = self.params.get("expected_result")
        if expected_result is None:
            return TestResult(
                success=False,
                native_results={"error": "expected_result parameter is required"},
            )

        try:
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                result = conn.execute(sa.text(sql)).scalar()

                # Try to convert both to same type for comparison
                try:
                    expected = type(result)(expected_result)
                except (ValueError, TypeError):
                    expected = str(expected_result)
                    result = str(result)

                success = result == expected

                return TestResult(
                    success=success,
                    actual_value=str(result),
                    native_results={
                        "actual_result": str(result),
                        "expected_result": str(expected_result),
                        "sql": sql,
                        "status": "PASS" if success else "FAIL",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to execute custom SQL: {e}")
            return TestResult(
                success=False,
                native_results={"error": f"Query execution failed: {str(e)}"},
            )

    def _parse_table_name_from_urn(self) -> str:
        urn_parts = self.dataset_urn.split(",")
        if len(urn_parts) < 2:
            raise ValueError(f"Invalid dataset URN format: {self.dataset_urn}")
        return urn_parts[1]
