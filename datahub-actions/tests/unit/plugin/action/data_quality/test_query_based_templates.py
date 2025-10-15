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

from unittest.mock import MagicMock, Mock, patch

import pytest

from datahub_actions.plugin.action.data_quality.templates.query_based import (
    ColumnLengthBetweenTest,
    ColumnValueRangeTest,
    ColumnValuesInSetTest,
    ColumnValuesMatchRegexTest,
    ColumnValuesNotInSetTest,
    ColumnValuesNotMatchRegexTest,
    TableCustomSQLTest,
)


@pytest.fixture
def dataset_urn():
    return "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)"


@pytest.fixture
def connection_string():
    return "mysql://user:pass@localhost:3306/mydb"


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine with connection."""
    engine = Mock()
    connection = Mock()
    engine.connect.return_value.__enter__ = Mock(return_value=connection)
    engine.connect.return_value.__exit__ = Mock(return_value=None)
    engine.dialect.name = "mysql"
    return engine, connection


class TestColumnValueRangeTest:
    def test_success_all_values_in_range(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 0 invalid rows
        connection.execute.return_value.fetchone.return_value = (0, 18, 65)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValueRangeTest(
                test_name="age_range",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "min_value": "0", "max_value": "100"},
                column="age",
            )
            result = test.execute()

        assert result.success is True
        assert "0" in result.native_results["invalid_count"]

    def test_failure_values_out_of_range(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 15 invalid rows
        connection.execute.return_value.fetchone.return_value = (15, 5, 120)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValueRangeTest(
                test_name="age_range",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "min_value": "18", "max_value": "65"},
                column="age",
            )
            result = test.execute()

        assert result.success is False
        assert "15" in result.native_results["invalid_count"]

    def test_error_missing_connection_string(self, dataset_urn):
        test = ColumnValueRangeTest(
            test_name="age_range",
            dataset_urn=dataset_urn,
            params={"min_value": "0", "max_value": "100"},
            column="age",
        )
        result = test.execute()

        assert result.success is False
        assert "connection_string" in result.native_results["error"]

    def test_error_missing_column(self, dataset_urn):
        with pytest.raises(ValueError, match="column parameter is required"):
            ColumnValueRangeTest(
                test_name="range_test",
                dataset_urn=dataset_urn,
                params={"connection_string": "mysql://localhost"},
            )

    def test_error_sql_execution_failure(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        connection.execute.side_effect = Exception("Database connection failed")

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValueRangeTest(
                test_name="age_range",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "min_value": "0", "max_value": "100"},
                column="age",
            )
            result = test.execute()

        assert result.success is False
        assert "failed" in result.native_results["error"].lower()


class TestColumnValuesInSetTest:
    def test_success_all_values_in_set(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 0 rows outside the allowed set
        connection.execute.return_value.fetchone.return_value = (0,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesInSetTest(
                test_name="status_in_set",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "value_set": "active, inactive, pending"},
                column="status",
            )
            result = test.execute()

        assert result.success is True

    def test_failure_values_not_in_set(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 5 rows have invalid values
        connection.execute.return_value.fetchone.return_value = (5,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesInSetTest(
                test_name="status_in_set",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "value_set": "active, inactive"},
                column="status",
            )
            result = test.execute()

        assert result.success is False
        assert "5" in result.native_results["invalid_count"]

    def test_error_missing_value_set(self, dataset_urn, connection_string):
        test = ColumnValuesInSetTest(
            test_name="status_in_set",
            dataset_urn=dataset_urn,
            params={"connection_string": connection_string},
            column="status",
        )
        result = test.execute()

        assert result.success is False
        assert "value_set" in result.native_results["error"]


class TestColumnValuesNotInSetTest:
    def test_success_no_forbidden_values(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 0 rows have forbidden values
        connection.execute.return_value.fetchone.return_value = (0,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesNotInSetTest(
                test_name="status_not_deleted",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "value_set": "deleted, archived"},
                column="status",
            )
            result = test.execute()

        assert result.success is True

    def test_failure_has_forbidden_values(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 3 rows have forbidden values
        connection.execute.return_value.fetchone.return_value = (3,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesNotInSetTest(
                test_name="status_not_deleted",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "value_set": "deleted"},
                column="status",
            )
            result = test.execute()

        assert result.success is False
        assert "3" in result.native_results["invalid_count"]


class TestColumnValuesMatchRegexTest:
    def test_success_all_match_regex_mysql(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        engine.dialect.name = "mysql"
        # Mock query result: 0 rows don't match regex
        connection.execute.return_value.fetchone.return_value = (0,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesMatchRegexTest(
                test_name="email_format",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
                column="email",
            )
            result = test.execute()

        assert result.success is True

    def test_success_postgres_regex_operator(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        engine.dialect.name = "postgresql"
        connection.execute.return_value.fetchone.return_value = (0,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesMatchRegexTest(
                test_name="phone_format",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "regex": r"^\d{3}-\d{3}-\d{4}$"},
                column="phone",
            )
            result = test.execute()

        # Should use ~ operator for PostgreSQL
        assert result.success is True

    def test_failure_some_dont_match(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 12 rows don't match regex
        connection.execute.return_value.fetchone.return_value = (12,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesMatchRegexTest(
                test_name="email_format",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "regex": r"^.+@.+\..+$"},
                column="email",
            )
            result = test.execute()

        assert result.success is False
        assert "12" in result.native_results["invalid_count"]

    def test_error_missing_regex(self, dataset_urn, connection_string):
        test = ColumnValuesMatchRegexTest(
            test_name="email_format",
            dataset_urn=dataset_urn,
            params={"connection_string": connection_string},
            column="email",
        )
        result = test.execute()

        assert result.success is False
        assert "regex" in result.native_results["error"]


class TestColumnValuesNotMatchRegexTest:
    def test_success_none_match_forbidden_regex(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 0 rows match the forbidden regex
        connection.execute.return_value.fetchone.return_value = (0,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesNotMatchRegexTest(
                test_name="no_special_chars",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "regex": r"[^a-zA-Z0-9]"},
                column="username",
            )
            result = test.execute()

        assert result.success is True

    def test_failure_some_match_forbidden_regex(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 8 rows match the forbidden regex
        connection.execute.return_value.fetchone.return_value = (8,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnValuesNotMatchRegexTest(
                test_name="no_sql_keywords",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "regex": r"(?i)(DROP|DELETE|TRUNCATE|ALTER)"},
                column="user_input",
            )
            result = test.execute()

        assert result.success is False
        assert "8" in result.native_results["invalid_count"]


class TestColumnLengthBetweenTest:
    def test_success_all_lengths_in_range(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 0 rows have invalid lengths
        connection.execute.return_value.fetchone.return_value = (0,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnLengthBetweenTest(
                test_name="username_length",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "min_length": "3", "max_length": "20"},
                column="username",
            )
            result = test.execute()

        assert result.success is True

    def test_failure_some_lengths_out_of_range(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: 7 rows have invalid lengths
        connection.execute.return_value.fetchone.return_value = (7,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnLengthBetweenTest(
                test_name="password_length",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "min_length": "8"},
                column="password",
            )
            result = test.execute()

        assert result.success is False
        assert "7" in result.native_results["invalid_count"]

    def test_only_min_length_specified(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        connection.execute.return_value.fetchone.return_value = (0,)

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = ColumnLengthBetweenTest(
                test_name="description_min_length",
                dataset_urn=dataset_urn,
                params={"connection_string": connection_string, "min_length": "10"},
                column="description",
            )
            result = test.execute()

        assert result.success is True
        assert result.native_results["max_length"] == "unlimited"


class TestTableCustomSQLTest:
    def test_success_result_matches_expected(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: returns 100
        connection.execute.return_value.scalar.return_value = 100

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = TableCustomSQLTest(
                test_name="active_user_count",
                dataset_urn=dataset_urn,
                params={
                    "connection_string": connection_string,
                    "sql": "SELECT COUNT(*) FROM users WHERE status = 'active'",
                    "expected_result": "100",
                },
            )
            result = test.execute()

        assert result.success is True
        assert result.actual_value == "100"

    def test_failure_result_differs_from_expected(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: returns 75
        connection.execute.return_value.scalar.return_value = 75

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = TableCustomSQLTest(
                test_name="active_user_count",
                dataset_urn=dataset_urn,
                params={
                    "connection_string": connection_string,
                    "sql": "SELECT COUNT(*) FROM users WHERE status = 'active'",
                    "expected_result": "100",
                },
            )
            result = test.execute()

        assert result.success is False
        assert "75" in result.native_results["actual_result"]
        assert "100" in result.native_results["expected_result"]

    def test_type_coercion_integer_result(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        # Mock query result: returns integer 42
        connection.execute.return_value.scalar.return_value = 42

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = TableCustomSQLTest(
                test_name="custom_check",
                dataset_urn=dataset_urn,
                params={
                    "connection_string": connection_string,
                    "sql": "SELECT MAX(id) FROM users",
                    "expected_result": "42",  # String expected, int returned
                },
            )
            result = test.execute()

        # Should handle type conversion
        assert result.success is True

    def test_error_missing_sql_param(self, dataset_urn, connection_string):
        test = TableCustomSQLTest(
            test_name="missing_sql",
            dataset_urn=dataset_urn,
            params={
                "connection_string": connection_string,
                "expected_result": "100",
            },
        )
        result = test.execute()

        assert result.success is False
        assert "sql" in result.native_results["error"]

    def test_error_missing_expected_result(self, dataset_urn, connection_string):
        test = TableCustomSQLTest(
            test_name="missing_expected",
            dataset_urn=dataset_urn,
            params={
                "connection_string": connection_string,
                "sql": "SELECT COUNT(*) FROM users",
            },
        )
        result = test.execute()

        assert result.success is False
        assert "expected_result" in result.native_results["error"]

    def test_error_sql_execution_failure(self, dataset_urn, connection_string, mock_engine):
        engine, connection = mock_engine
        connection.execute.side_effect = Exception("SQL syntax error")

        with patch("datahub_actions.plugin.action.data_quality.templates.query_based.create_engine", return_value=engine):
            test = TableCustomSQLTest(
                test_name="custom_check",
                dataset_urn=dataset_urn,
                params={
                    "connection_string": connection_string,
                    "sql": "SELECT INVALID SQL",
                    "expected_result": "0",
                },
            )
            result = test.execute()

        assert result.success is False
        assert "failed" in result.native_results["error"].lower()
