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

import pytest

from datahub.metadata.schema_classes import (
    DatasetFieldProfileClass,
    DatasetProfileClass,
)
from datahub_actions.plugin.action.data_quality.templates.profile_based import (
    ColumnDistinctCountBetweenTest,
    ColumnMaxBetweenTest,
    ColumnMeanBetweenTest,
    ColumnMedianBetweenTest,
    ColumnMinBetweenTest,
    ColumnNullCountEqualsTest,
    ColumnStddevBetweenTest,
    ColumnUniqueProportionBetweenTest,
    ColumnValuesNotNullTest,
    ColumnValuesUniqueTest,
    TableColumnCountBetweenTest,
    TableColumnCountEqualsTest,
    TableRowCountEqualsTest,
    TableRowCountTest,
)


@pytest.fixture
def dataset_urn():
    return "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)"


@pytest.fixture
def dataset_profile_with_fields():
    """Profile with 1000 rows and 5 columns including field profiles."""
    return DatasetProfileClass(
        timestampMillis=1000000,
        rowCount=1000,
        columnCount=5,
        fieldProfiles=[
            DatasetFieldProfileClass(
                fieldPath="user_id",
                uniqueCount=1000,
                nullCount=0,
                min="1",
                max="1000",
                mean="500.5",
                median="500",
                stdev="288.67",
            ),
            DatasetFieldProfileClass(
                fieldPath="age",
                uniqueCount=50,
                nullCount=10,
                min="18",
                max="65",
                mean="35.5",
                median="34",
                stdev="12.3",
            ),
            DatasetFieldProfileClass(
                fieldPath="email",
                uniqueCount=990,
                nullCount=10,
            ),
        ],
    )


class TestTableRowCountTest:
    def test_success_within_range(self, dataset_urn, dataset_profile_with_fields):
        test = TableRowCountTest(
            test_name="row_count_check",
            dataset_urn=dataset_urn,
            params={"min_rows": "500", "max_rows": "2000"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is True
        assert result.actual_value == "1000"
        assert result.row_count == 1000

    def test_failure_below_min(self, dataset_urn, dataset_profile_with_fields):
        test = TableRowCountTest(
            test_name="row_count_check",
            dataset_urn=dataset_urn,
            params={"min_rows": "2000"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is False

    def test_failure_above_max(self, dataset_urn, dataset_profile_with_fields):
        test = TableRowCountTest(
            test_name="row_count_check",
            dataset_urn=dataset_urn,
            params={"min_rows": "0", "max_rows": "500"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is False

    def test_error_when_profile_missing(self, dataset_urn):
        test = TableRowCountTest(
            test_name="row_count_check",
            dataset_urn=dataset_urn,
            params={"min_rows": "1"},
        )
        result = test.execute(profile=None)
        assert result.success is False
        assert "error" in result.native_results


class TestTableRowCountEqualsTest:
    def test_success_when_count_matches(self, dataset_urn, dataset_profile_with_fields):
        test = TableRowCountEqualsTest(
            test_name="exact_row_count",
            dataset_urn=dataset_urn,
            params={"value": "1000"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is True
        assert result.actual_value == "1000"

    def test_failure_when_count_differs(self, dataset_urn, dataset_profile_with_fields):
        test = TableRowCountEqualsTest(
            test_name="exact_row_count",
            dataset_urn=dataset_urn,
            params={"value": "500"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is False


class TestTableColumnCountEqualsTest:
    def test_success_when_count_matches(self, dataset_urn, dataset_profile_with_fields):
        test = TableColumnCountEqualsTest(
            test_name="exact_column_count",
            dataset_urn=dataset_urn,
            params={"value": "5"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is True

    def test_failure_when_count_differs(self, dataset_urn, dataset_profile_with_fields):
        test = TableColumnCountEqualsTest(
            test_name="exact_column_count",
            dataset_urn=dataset_urn,
            params={"value": "10"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is False


class TestTableColumnCountBetweenTest:
    def test_success_within_range(self, dataset_urn, dataset_profile_with_fields):
        test = TableColumnCountBetweenTest(
            test_name="column_count_range",
            dataset_urn=dataset_urn,
            params={"min_value": "3", "max_value": "10"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is True

    def test_failure_below_min(self, dataset_urn, dataset_profile_with_fields):
        test = TableColumnCountBetweenTest(
            test_name="column_count_range",
            dataset_urn=dataset_urn,
            params={"min_value": "10"},
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is False


class TestColumnValuesNotNullTest:
    def test_success_no_nulls(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnValuesNotNullTest(
            test_name="user_id_not_null",
            dataset_urn=dataset_urn,
            params={},
            column="user_id",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is True
        assert result.actual_value == "0"

    def test_failure_has_nulls(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnValuesNotNullTest(
            test_name="age_not_null",
            dataset_urn=dataset_urn,
            params={},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is False
        assert result.actual_value == "10"

    def test_error_column_not_found(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnValuesNotNullTest(
            test_name="missing_col_not_null",
            dataset_urn=dataset_urn,
            params={},
            column="nonexistent",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        assert result.success is False
        assert "not found" in result.native_results["error"]

    def test_error_missing_column_param(self, dataset_urn):
        with pytest.raises(ValueError, match="column parameter is required"):
            ColumnValuesNotNullTest(
                test_name="test",
                dataset_urn=dataset_urn,
                params={},
            )


class TestColumnValuesUniqueTest:
    def test_success_all_unique(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnValuesUniqueTest(
            test_name="user_id_unique",
            dataset_urn=dataset_urn,
            params={},
            column="user_id",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # user_id has 1000 unique values, 0 nulls, rowCount=1000
        # non_null_count = 1000 - 0 = 1000
        # unique_count = 1000 == non_null_count → success
        assert result.success is True

    def test_failure_not_unique(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnValuesUniqueTest(
            test_name="age_unique",
            dataset_urn=dataset_urn,
            params={},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age has 50 unique values, 10 nulls, rowCount=1000
        # non_null_count = 1000 - 10 = 990
        # unique_count = 50 != 990 → failure
        assert result.success is False


class TestColumnMinBetweenTest:
    def test_success_min_in_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnMinBetweenTest(
            test_name="age_min_check",
            dataset_urn=dataset_urn,
            params={"min_value": "10", "max_value": "25"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age min = 18, which is in [10, 25]
        assert result.success is True
        assert result.actual_value == "18.0"

    def test_failure_min_below_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnMinBetweenTest(
            test_name="age_min_check",
            dataset_urn=dataset_urn,
            params={"min_value": "20", "max_value": "30"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age min = 18, which is < 20
        assert result.success is False


class TestColumnMaxBetweenTest:
    def test_success_max_in_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnMaxBetweenTest(
            test_name="age_max_check",
            dataset_urn=dataset_urn,
            params={"min_value": "60", "max_value": "70"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age max = 65, which is in [60, 70]
        assert result.success is True

    def test_failure_max_above_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnMaxBetweenTest(
            test_name="age_max_check",
            dataset_urn=dataset_urn,
            params={"min_value": "10", "max_value": "50"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age max = 65, which is > 50
        assert result.success is False


class TestColumnMeanBetweenTest:
    def test_success_mean_in_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnMeanBetweenTest(
            test_name="age_mean_check",
            dataset_urn=dataset_urn,
            params={"min_value": "30", "max_value": "40"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age mean = 35.5, which is in [30, 40]
        assert result.success is True

    def test_failure_mean_out_of_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnMeanBetweenTest(
            test_name="age_mean_check",
            dataset_urn=dataset_urn,
            params={"min_value": "10", "max_value": "20"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age mean = 35.5, which is > 20
        assert result.success is False


class TestColumnMedianBetweenTest:
    def test_success_median_in_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnMedianBetweenTest(
            test_name="age_median_check",
            dataset_urn=dataset_urn,
            params={"min_value": "30", "max_value": "40"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age median = 34, which is in [30, 40]
        assert result.success is True

    def test_error_median_not_available(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnMedianBetweenTest(
            test_name="email_median_check",
            dataset_urn=dataset_urn,
            params={"min_value": "0", "max_value": "100"},
            column="email",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # email field has no median data
        assert result.success is False
        assert "not available" in result.native_results["error"]


class TestColumnStddevBetweenTest:
    def test_success_stddev_in_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnStddevBetweenTest(
            test_name="age_stddev_check",
            dataset_urn=dataset_urn,
            params={"min_value": "10", "max_value": "15"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age stdev = 12.3, which is in [10, 15]
        assert result.success is True

    def test_failure_stddev_out_of_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnStddevBetweenTest(
            test_name="age_stddev_check",
            dataset_urn=dataset_urn,
            params={"min_value": "0", "max_value": "5"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age stdev = 12.3, which is > 5
        assert result.success is False


class TestColumnDistinctCountBetweenTest:
    def test_success_distinct_count_in_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnDistinctCountBetweenTest(
            test_name="age_distinct_count_check",
            dataset_urn=dataset_urn,
            params={"min_value": "40", "max_value": "60"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age uniqueCount = 50, which is in [40, 60]
        assert result.success is True
        assert result.actual_value == "50"

    def test_failure_distinct_count_below_min(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnDistinctCountBetweenTest(
            test_name="age_distinct_count_check",
            dataset_urn=dataset_urn,
            params={"min_value": "100"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age uniqueCount = 50, which is < 100
        assert result.success is False


class TestColumnUniqueProportionBetweenTest:
    def test_success_proportion_in_range(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnUniqueProportionBetweenTest(
            test_name="user_id_unique_proportion",
            dataset_urn=dataset_urn,
            params={"min_value": "0.9", "max_value": "1.0"},
            column="user_id",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # user_id: uniqueCount=1000, rowCount=1000 → proportion=1.0
        assert result.success is True
        assert float(result.actual_value) == 1.0

    def test_failure_proportion_too_low(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnUniqueProportionBetweenTest(
            test_name="age_unique_proportion",
            dataset_urn=dataset_urn,
            params={"min_value": "0.5", "max_value": "1.0"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age: uniqueCount=50, rowCount=1000 → proportion=0.05
        assert result.success is False

    def test_handles_zero_row_count(self, dataset_urn):
        profile = DatasetProfileClass(
            timestampMillis=1000000,
            rowCount=0,
            columnCount=1,
            fieldProfiles=[
                DatasetFieldProfileClass(
                    fieldPath="col1",
                    uniqueCount=0,
                    nullCount=0,
                ),
            ],
        )
        test = ColumnUniqueProportionBetweenTest(
            test_name="zero_rows",
            dataset_urn=dataset_urn,
            params={"min_value": "0", "max_value": "1"},
            column="col1",
        )
        result = test.execute(profile=profile)
        # Should handle division by zero gracefully
        assert result.success is True  # proportion = 0.0, which is in [0, 1]


class TestColumnNullCountEqualsTest:
    def test_success_null_count_matches(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnNullCountEqualsTest(
            test_name="age_null_count",
            dataset_urn=dataset_urn,
            params={"value": "10"},
            column="age",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # age has nullCount=10
        assert result.success is True
        assert result.actual_value == "10"

    def test_failure_null_count_differs(self, dataset_urn, dataset_profile_with_fields):
        test = ColumnNullCountEqualsTest(
            test_name="user_id_null_count",
            dataset_urn=dataset_urn,
            params={"value": "5"},
            column="user_id",
        )
        result = test.execute(profile=dataset_profile_with_fields)
        # user_id has nullCount=0, expected=5
        assert result.success is False
