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

import time
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

import datahub.emitter.mce_builder as builder
from datahub.emitter.serialization_helper import pre_json_transform
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
from datahub.metadata.schema_classes import DatasetProfileClass


@dataclass
class TestResult:
    """Result of executing a data quality test."""

    success: bool
    actual_value: Optional[str] = None
    row_count: Optional[int] = None
    native_results: Optional[Dict[str, str]] = None


class BaseTestTemplate(metaclass=ABCMeta):
    """
    Abstract base class for all data quality test templates.

    Provides common functionality for building assertions and executing tests.
    """

    def __init__(
        self,
        test_name: str,
        dataset_urn: str,
        params: Dict[str, str],
        column: Optional[str] = None,
    ):
        self.test_name = test_name
        self.dataset_urn = dataset_urn
        self.params = params
        self.column = column
        self.field_urn = (
            builder.make_schema_field_urn(dataset_urn, column) if column else None
        )

    @abstractmethod
    def get_test_type(self) -> str:
        """Return the native test type name (e.g., 'table_row_count')."""
        pass

    @abstractmethod
    def get_scope(self) -> DatasetAssertionScope:
        """Return the assertion scope (DATASET_COLUMN, DATASET_ROWS, etc.)."""
        pass

    @abstractmethod
    def get_operator(self) -> AssertionStdOperator:
        """Return the assertion operator (BETWEEN, EQUAL_TO, etc.)."""
        pass

    @abstractmethod
    def get_aggregation(self) -> AssertionStdAggregation:
        """Return the assertion aggregation (ROW_COUNT, MIN, MAX, etc.)."""
        pass

    @abstractmethod
    def get_category(self) -> str:
        """
        Return the assertion category.

        Categories: VOLUME, SCHEMA, COLUMN, FRESHNESS, UNIQUENESS, COMPLETENESS, CUSTOM_SQL
        """
        pass

    @abstractmethod
    def execute(
        self, profile: Optional[DatasetProfileClass] = None
    ) -> TestResult:
        """
        Execute the test and return the result.

        Args:
            profile: Optional dataset profile for profile-based tests

        Returns:
            TestResult with success status and details
        """
        pass

    def get_parameters(self) -> Optional[AssertionStdParameters]:
        """Build assertion parameters from test params. Override if needed."""
        return None

    def build_assertion_urn(self) -> str:
        """Build deterministic URN for this assertion."""
        return builder.make_assertion_urn(
            builder.datahub_guid(
                pre_json_transform(
                    {
                        "platform": "data-quality",
                        "nativeType": self.get_test_type(),
                        "nativeParameters": self.params,
                        "dataset": self.dataset_urn,
                        "fields": [self.field_urn] if self.field_urn else None,
                    }
                )
            )
        )

    def build_assertion_info(self) -> AssertionInfo:
        """Build AssertionInfo aspect for this test."""
        dataset_assertion = DatasetAssertionInfo(
            dataset=self.dataset_urn,
            fields=[self.field_urn] if self.field_urn else None,
            scope=self.get_scope(),
            operator=self.get_operator(),
            aggregation=self.get_aggregation(),
            parameters=self.get_parameters(),
            nativeType=self.get_test_type(),
            nativeParameters={k: str(v) for k, v in self.params.items()},
        )

        return AssertionInfo(
            type=AssertionType.DATASET,
            datasetAssertion=dataset_assertion,
            customProperties={
                "test_name": self.test_name,
                "category": self.get_category(),
            },
        )

    def build_assertion_result(
        self, test_result: TestResult, assertion_urn: str
    ) -> AssertionRunEvent:
        """Build AssertionRunEvent for the test result."""
        return AssertionRunEvent(
            timestampMillis=int(round(time.time() * 1000)),
            assertionUrn=assertion_urn,
            asserteeUrn=self.dataset_urn,
            runId=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            result=AssertionResult(
                type=(
                    AssertionResultType.SUCCESS
                    if test_result.success
                    else AssertionResultType.FAILURE
                ),
                rowCount=test_result.row_count,
                actualAggValue=(
                    float(test_result.actual_value)
                    if test_result.actual_value
                    and test_result.actual_value.replace(".", "").isdigit()
                    else None
                ),
                nativeResults=test_result.native_results or {},
            ),
            status=AssertionRunStatus.COMPLETE,
        )
