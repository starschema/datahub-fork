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

from typing import Optional

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


class TableRowCountTest(BaseTestTemplate):
    """
    Profile-based test that validates table row count is within expected range.

    Uses cached profile data - no database queries required.
    """

    def get_test_type(self) -> str:
        return "table_row_count"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_ROWS

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.ROW_COUNT

    def get_category(self) -> str:
        return "VOLUME"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        min_rows = self.params.get("min_rows")
        max_rows = self.params.get("max_rows")

        return AssertionStdParameters(
            minValue=AssertionStdParameter(
                value=str(min_rows) if min_rows else None,
                type=AssertionStdParameterType.NUMBER,
            ),
            maxValue=AssertionStdParameter(
                value=str(max_rows) if max_rows else None,
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or profile.rowCount is None:
            return TestResult(
                success=False,
                native_results={
                    "error": "Profile data not available or row count is missing"
                },
            )

        actual_row_count = profile.rowCount
        min_rows = int(self.params.get("min_rows", 0))
        max_rows = self.params.get("max_rows")

        success = actual_row_count >= min_rows
        if max_rows is not None:
            success = success and actual_row_count <= int(max_rows)

        return TestResult(
            success=success,
            actual_value=str(actual_row_count),
            row_count=actual_row_count,
            native_results={
                "actual_row_count": str(actual_row_count),
                "min_rows": str(min_rows),
                "max_rows": str(max_rows) if max_rows else "unlimited",
                "status": "PASS" if success else "FAIL",
            },
        )


class TableRowCountEqualsTest(BaseTestTemplate):
    """Validate table row count equals exact value."""

    def get_test_type(self) -> str:
        return "table_row_count_equals"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_ROWS

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.EQUAL_TO

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.ROW_COUNT

    def get_category(self) -> str:
        return "VOLUME"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        value = self.params.get("value")
        return AssertionStdParameters(
            value=AssertionStdParameter(
                value=str(value) if value else None,
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or profile.rowCount is None:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        actual_row_count = profile.rowCount
        expected_count = int(self.params.get("value", 0))
        success = actual_row_count == expected_count

        return TestResult(
            success=success,
            actual_value=str(actual_row_count),
            row_count=actual_row_count,
            native_results={
                "actual_row_count": str(actual_row_count),
                "expected_count": str(expected_count),
                "status": "PASS" if success else "FAIL",
            },
        )


class TableColumnCountEqualsTest(BaseTestTemplate):
    """Validate table column count equals exact value."""

    def get_test_type(self) -> str:
        return "table_column_count_equals"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_SCHEMA

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.EQUAL_TO

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.COLUMN_COUNT

    def get_category(self) -> str:
        return "SCHEMA"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        value = self.params.get("value")
        return AssertionStdParameters(
            value=AssertionStdParameter(
                value=str(value) if value else None,
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or profile.columnCount is None:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        actual_column_count = profile.columnCount
        expected_count = int(self.params.get("value", 0))
        success = actual_column_count == expected_count

        return TestResult(
            success=success,
            actual_value=str(actual_column_count),
            native_results={
                "actual_column_count": str(actual_column_count),
                "expected_count": str(expected_count),
                "status": "PASS" if success else "FAIL",
            },
        )


class TableColumnCountBetweenTest(BaseTestTemplate):
    """Validate table column count is within range."""

    def get_test_type(self) -> str:
        return "table_column_count_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_SCHEMA

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.COLUMN_COUNT

    def get_category(self) -> str:
        return "SCHEMA"

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
        if profile is None or profile.columnCount is None:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        actual_column_count = profile.columnCount
        min_count = int(self.params.get("min_value", 0))
        max_count = self.params.get("max_value")

        success = actual_column_count >= min_count
        if max_count is not None:
            success = success and actual_column_count <= int(max_count)

        return TestResult(
            success=success,
            actual_value=str(actual_column_count),
            native_results={
                "actual_column_count": str(actual_column_count),
                "min_value": str(min_count),
                "max_value": str(max_count) if max_count else "unlimited",
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnValuesNotNullTest(BaseTestTemplate):
    """Validate column has no null values (using profile data)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_values_not_null test")

    def get_test_type(self) -> str:
        return "column_values_not_null"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.EQUAL_TO

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.NULL_COUNT

    def get_category(self) -> str:
        return "COMPLETENESS"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        return AssertionStdParameters(
            value=AssertionStdParameter(
                value="0",
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.nullCount is None:
            return TestResult(
                success=False,
                native_results={"error": f"Column '{self.column}' not found in profile"},
            )

        null_count = field_profile.nullCount
        success = null_count == 0

        return TestResult(
            success=success,
            actual_value=str(null_count),
            native_results={
                "null_count": str(null_count),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnValuesUniqueTest(BaseTestTemplate):
    """Validate all column values are unique (using profile data)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_values_unique test")

    def get_test_type(self) -> str:
        return "column_values_unique"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.EQUAL_TO

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.UNIQUE_COUNT

    def get_category(self) -> str:
        return "UNIQUENESS"
        return "COLUMN"

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None:
            return TestResult(
                success=False,
                native_results={"error": f"Column '{self.column}' not found in profile"},
            )

        if field_profile.uniqueCount is None or field_profile.nullCount is None:
            return TestResult(
                success=False,
                native_results={"error": "Unique count data not available"},
            )

        unique_count = field_profile.uniqueCount
        non_null_count = (profile.rowCount or 0) - field_profile.nullCount
        success = unique_count == non_null_count

        return TestResult(
            success=success,
            actual_value=str(unique_count),
            native_results={
                "unique_count": str(unique_count),
                "non_null_count": str(non_null_count),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnMinBetweenTest(BaseTestTemplate):
    """Validate column minimum value is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_min_between test")

    def get_test_type(self) -> str:
        return "column_min_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.MIN

    def get_category(self) -> str:
        return "COLUMN"

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
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.min is None:
            return TestResult(
                success=False,
                native_results={"error": f"Min value not available for column '{self.column}'"},
            )

        actual_min = float(field_profile.min)
        min_value = float(self.params.get("min_value", float("-inf")))
        max_value = float(self.params.get("max_value", float("inf")))

        success = min_value <= actual_min <= max_value

        return TestResult(
            success=success,
            actual_value=str(actual_min),
            native_results={
                "actual_min": str(actual_min),
                "expected_min": str(min_value),
                "expected_max": str(max_value),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnMaxBetweenTest(BaseTestTemplate):
    """Validate column maximum value is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_max_between test")

    def get_test_type(self) -> str:
        return "column_max_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.MAX

    def get_category(self) -> str:
        return "COLUMN"

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
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.max is None:
            return TestResult(
                success=False,
                native_results={"error": f"Max value not available for column '{self.column}'"},
            )

        actual_max = float(field_profile.max)
        min_value = float(self.params.get("min_value", float("-inf")))
        max_value = float(self.params.get("max_value", float("inf")))

        success = min_value <= actual_max <= max_value

        return TestResult(
            success=success,
            actual_value=str(actual_max),
            native_results={
                "actual_max": str(actual_max),
                "expected_min": str(min_value),
                "expected_max": str(max_value),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnMeanBetweenTest(BaseTestTemplate):
    """Validate column mean value is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_mean_between test")

    def get_test_type(self) -> str:
        return "column_mean_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.MEAN

    def get_category(self) -> str:
        return "COLUMN"

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
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.mean is None:
            return TestResult(
                success=False,
                native_results={"error": f"Mean value not available for column '{self.column}'"},
            )

        actual_mean = float(field_profile.mean)
        min_value = float(self.params.get("min_value", float("-inf")))
        max_value = float(self.params.get("max_value", float("inf")))

        success = min_value <= actual_mean <= max_value

        return TestResult(
            success=success,
            actual_value=str(actual_mean),
            native_results={
                "actual_mean": str(actual_mean),
                "expected_min": str(min_value),
                "expected_max": str(max_value),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnMedianBetweenTest(BaseTestTemplate):
    """Validate column median value is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_median_between test")

    def get_test_type(self) -> str:
        return "column_median_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.MEDIAN

    def get_category(self) -> str:
        return "COLUMN"

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
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.median is None:
            return TestResult(
                success=False,
                native_results={"error": f"Median value not available for column '{self.column}'"},
            )

        actual_median = float(field_profile.median)
        min_value = float(self.params.get("min_value", float("-inf")))
        max_value = float(self.params.get("max_value", float("inf")))

        success = min_value <= actual_median <= max_value

        return TestResult(
            success=success,
            actual_value=str(actual_median),
            native_results={
                "actual_median": str(actual_median),
                "expected_min": str(min_value),
                "expected_max": str(max_value),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnStddevBetweenTest(BaseTestTemplate):
    """Validate column standard deviation is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_stddev_between test")

    def get_test_type(self) -> str:
        return "column_stddev_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.STDDEV

    def get_category(self) -> str:
        return "COLUMN"

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
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.stdev is None:
            return TestResult(
                success=False,
                native_results={"error": f"Standard deviation not available for column '{self.column}'"},
            )

        actual_stdev = float(field_profile.stdev)
        min_value = float(self.params.get("min_value", 0))
        max_value = float(self.params.get("max_value", float("inf")))

        success = min_value <= actual_stdev <= max_value

        return TestResult(
            success=success,
            actual_value=str(actual_stdev),
            native_results={
                "actual_stddev": str(actual_stdev),
                "expected_min": str(min_value),
                "expected_max": str(max_value),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnDistinctCountBetweenTest(BaseTestTemplate):
    """Validate column distinct count is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_distinct_count_between test")

    def get_test_type(self) -> str:
        return "column_distinct_count_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.UNIQUE_COUNT

    def get_category(self) -> str:
        return "UNIQUENESS"
        return "COLUMN"

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
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.uniqueCount is None:
            return TestResult(
                success=False,
                native_results={"error": f"Unique count not available for column '{self.column}'"},
            )

        actual_unique_count = field_profile.uniqueCount
        min_value = int(self.params.get("min_value", 0))
        max_value = self.params.get("max_value")

        success = actual_unique_count >= min_value
        if max_value is not None:
            success = success and actual_unique_count <= int(max_value)

        return TestResult(
            success=success,
            actual_value=str(actual_unique_count),
            native_results={
                "actual_unique_count": str(actual_unique_count),
                "min_value": str(min_value),
                "max_value": str(max_value) if max_value else "unlimited",
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnUniqueProportionBetweenTest(BaseTestTemplate):
    """Validate column unique proportion is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_unique_proportion_between test")

    def get_test_type(self) -> str:
        return "column_unique_proportion_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.UNIQUE_PROPOTION

    def get_category(self) -> str:
        return "UNIQUENESS"
        return "COLUMN"

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
        if profile is None or not profile.fieldProfiles or profile.rowCount is None:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.uniqueCount is None:
            return TestResult(
                success=False,
                native_results={"error": f"Unique count not available for column '{self.column}'"},
            )

        unique_proportion = float(field_profile.uniqueCount) / float(profile.rowCount) if profile.rowCount > 0 else 0.0
        min_value = float(self.params.get("min_value", 0.0))
        max_value = float(self.params.get("max_value", 1.0))

        success = min_value <= unique_proportion <= max_value

        return TestResult(
            success=success,
            actual_value=str(unique_proportion),
            native_results={
                "actual_unique_proportion": str(unique_proportion),
                "unique_count": str(field_profile.uniqueCount),
                "row_count": str(profile.rowCount),
                "min_value": str(min_value),
                "max_value": str(max_value),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnNullCountEqualsTest(BaseTestTemplate):
    """Validate column null count equals exact value."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_null_count_equals test")

    def get_test_type(self) -> str:
        return "column_null_count_equals"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.EQUAL_TO

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.NULL_COUNT

    def get_category(self) -> str:
        return "COMPLETENESS"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        value = self.params.get("value")
        return AssertionStdParameters(
            value=AssertionStdParameter(
                value=str(value) if value else None,
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or not profile.fieldProfiles:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.nullCount is None:
            return TestResult(
                success=False,
                native_results={"error": f"Null count not available for column '{self.column}'"},
            )

        actual_null_count = field_profile.nullCount
        expected_count = int(self.params.get("value", 0))
        success = actual_null_count == expected_count

        return TestResult(
            success=success,
            actual_value=str(actual_null_count),
            native_results={
                "actual_null_count": str(actual_null_count),
                "expected_count": str(expected_count),
                "status": "PASS" if success else "FAIL",
            },
        )


class DatasetProfileFreshnessTest(BaseTestTemplate):
    """
    Validate dataset profile was updated within specified time window.

    Uses profile timestamp to check data freshness.
    """

    def get_test_type(self) -> str:
        return "dataset_profile_freshness"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_ROWS

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.LESS_THAN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation._NATIVE_

    def get_category(self) -> str:
        return "FRESHNESS"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        max_age_hours = self.params.get("max_age_hours")
        return AssertionStdParameters(
            value=AssertionStdParameter(
                value=str(max_age_hours) if max_age_hours else None,
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        import time

        if profile is None or profile.timestampMillis is None:
            return TestResult(
                success=False,
                native_results={"error": "Profile timestamp not available"},
            )

        max_age_hours = float(self.params.get("max_age_hours", 24))
        max_age_ms = max_age_hours * 60 * 60 * 1000

        current_time_ms = int(round(time.time() * 1000))
        profile_age_ms = current_time_ms - profile.timestampMillis
        profile_age_hours = profile_age_ms / (60 * 60 * 1000)

        success = profile_age_ms <= max_age_ms

        return TestResult(
            success=success,
            actual_value=str(profile_age_hours),
            native_results={
                "profile_age_hours": f"{profile_age_hours:.2f}",
                "max_age_hours": str(max_age_hours),
                "profile_timestamp": str(profile.timestampMillis),
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnNullPercentageBetweenTest(BaseTestTemplate):
    """Validate column null percentage is within acceptable range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_null_percentage_between test")

    def get_test_type(self) -> str:
        return "column_null_percentage_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.NULL_PROPORTION

    def get_category(self) -> str:
        return "COMPLETENESS"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        min_percentage = self.params.get("min_percentage", 0)
        max_percentage = self.params.get("max_percentage", 100)
        return AssertionStdParameters(
            minValue=AssertionStdParameter(
                value=str(float(min_percentage) / 100.0),
                type=AssertionStdParameterType.NUMBER,
            ),
            maxValue=AssertionStdParameter(
                value=str(float(max_percentage) / 100.0),
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or not profile.fieldProfiles or profile.rowCount is None:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.nullCount is None:
            return TestResult(
                success=False,
                native_results={"error": f"Null count not available for column '{self.column}'"},
            )

        null_percentage = (float(field_profile.nullCount) / float(profile.rowCount) * 100.0) if profile.rowCount > 0 else 0.0
        min_percentage = float(self.params.get("min_percentage", 0))
        max_percentage = float(self.params.get("max_percentage", 100))

        success = min_percentage <= null_percentage <= max_percentage

        return TestResult(
            success=success,
            actual_value=str(null_percentage),
            native_results={
                "actual_null_percentage": f"{null_percentage:.2f}%",
                "null_count": str(field_profile.nullCount),
                "row_count": str(profile.rowCount),
                "min_percentage": f"{min_percentage}%",
                "max_percentage": f"{max_percentage}%",
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnCompletenessPercentageBetweenTest(BaseTestTemplate):
    """Validate column completeness percentage (non-null %) is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_completeness_percentage_between test")

    def get_test_type(self) -> str:
        return "column_completeness_percentage_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation._NATIVE_

    def get_category(self) -> str:
        return "COMPLETENESS"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        min_percentage = self.params.get("min_percentage", 0)
        max_percentage = self.params.get("max_percentage", 100)
        return AssertionStdParameters(
            minValue=AssertionStdParameter(
                value=str(min_percentage),
                type=AssertionStdParameterType.NUMBER,
            ),
            maxValue=AssertionStdParameter(
                value=str(max_percentage),
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or not profile.fieldProfiles or profile.rowCount is None:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.nullCount is None:
            return TestResult(
                success=False,
                native_results={"error": f"Null count not available for column '{self.column}'"},
            )

        non_null_count = profile.rowCount - field_profile.nullCount
        completeness_percentage = (float(non_null_count) / float(profile.rowCount) * 100.0) if profile.rowCount > 0 else 0.0
        min_percentage = float(self.params.get("min_percentage", 0))
        max_percentage = float(self.params.get("max_percentage", 100))

        success = min_percentage <= completeness_percentage <= max_percentage

        return TestResult(
            success=success,
            actual_value=str(completeness_percentage),
            native_results={
                "actual_completeness_percentage": f"{completeness_percentage:.2f}%",
                "non_null_count": str(non_null_count),
                "row_count": str(profile.rowCount),
                "min_percentage": f"{min_percentage}%",
                "max_percentage": f"{max_percentage}%",
                "status": "PASS" if success else "FAIL",
            },
        )


class ColumnUniquenessPercentageBetweenTest(BaseTestTemplate):
    """Validate column uniqueness percentage (unique values / total values) is within range."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.column:
            raise ValueError("column parameter is required for column_uniqueness_percentage_between test")

    def get_test_type(self) -> str:
        return "column_uniqueness_percentage_between"

    def get_scope(self) -> DatasetAssertionScope:
        return DatasetAssertionScope.DATASET_COLUMN

    def get_operator(self) -> AssertionStdOperator:
        return AssertionStdOperator.BETWEEN

    def get_aggregation(self) -> AssertionStdAggregation:
        return AssertionStdAggregation.UNIQUE_PROPOTION

    def get_category(self) -> str:
        return "UNIQUENESS"

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        min_percentage = self.params.get("min_percentage", 0)
        max_percentage = self.params.get("max_percentage", 100)
        return AssertionStdParameters(
            minValue=AssertionStdParameter(
                value=str(float(min_percentage) / 100.0),
                type=AssertionStdParameterType.NUMBER,
            ),
            maxValue=AssertionStdParameter(
                value=str(float(max_percentage) / 100.0),
                type=AssertionStdParameterType.NUMBER,
            ),
        )

    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        if profile is None or not profile.fieldProfiles or profile.rowCount is None:
            return TestResult(
                success=False,
                native_results={"error": "Profile data not available"},
            )

        field_profile = next(
            (fp for fp in profile.fieldProfiles if fp.fieldPath == self.column), None
        )

        if field_profile is None or field_profile.uniqueCount is None:
            return TestResult(
                success=False,
                native_results={"error": f"Unique count not available for column '{self.column}'"},
            )

        uniqueness_percentage = (float(field_profile.uniqueCount) / float(profile.rowCount) * 100.0) if profile.rowCount > 0 else 0.0
        min_percentage = float(self.params.get("min_percentage", 0))
        max_percentage = float(self.params.get("max_percentage", 100))

        success = min_percentage <= uniqueness_percentage <= max_percentage

        return TestResult(
            success=success,
            actual_value=str(uniqueness_percentage),
            native_results={
                "actual_uniqueness_percentage": f"{uniqueness_percentage:.2f}%",
                "unique_count": str(field_profile.uniqueCount),
                "row_count": str(profile.rowCount),
                "min_percentage": f"{min_percentage}%",
                "max_percentage": f"{max_percentage}%",
                "status": "PASS" if success else "FAIL",
            },
        )
