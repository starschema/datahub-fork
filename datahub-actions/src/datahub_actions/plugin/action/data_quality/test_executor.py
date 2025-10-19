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
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.ingestion.graph.client import DataHubGraph
from datahub.metadata.schema_classes import DatasetProfileClass
from datahub_actions.plugin.action.data_quality.config import TestConfig
from datahub_actions.plugin.action.data_quality.templates.base import BaseTestTemplate

if TYPE_CHECKING:
    from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry
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
from datahub_actions.plugin.action.data_quality.templates.query_based import (
    ColumnLengthBetweenTest,
    ColumnValueRangeTest,
    ColumnValuesInSetTest,
    ColumnValuesMatchRegexTest,
    ColumnValuesNotInSetTest,
    ColumnValuesNotMatchRegexTest,
    TableCustomSQLTest,
)

logger = logging.getLogger(__name__)


TEST_REGISTRY: Dict[str, Type[BaseTestTemplate]] = {
    # Profile-based table tests
    "table_row_count": TableRowCountTest,
    "table_row_count_equals": TableRowCountEqualsTest,
    "table_column_count_equals": TableColumnCountEqualsTest,
    "table_column_count_between": TableColumnCountBetweenTest,
    # Profile-based column tests
    "column_values_not_null": ColumnValuesNotNullTest,
    "column_values_unique": ColumnValuesUniqueTest,
    "column_min_between": ColumnMinBetweenTest,
    "column_max_between": ColumnMaxBetweenTest,
    "column_mean_between": ColumnMeanBetweenTest,
    "column_median_between": ColumnMedianBetweenTest,
    "column_stddev_between": ColumnStddevBetweenTest,
    "column_distinct_count_between": ColumnDistinctCountBetweenTest,
    "column_unique_proportion_between": ColumnUniqueProportionBetweenTest,
    "column_null_count_equals": ColumnNullCountEqualsTest,
    # Query-based column tests
    "column_value_range": ColumnValueRangeTest,
    "column_values_in_set": ColumnValuesInSetTest,
    "column_values_not_in_set": ColumnValuesNotInSetTest,
    "column_values_match_regex": ColumnValuesMatchRegexTest,
    "column_values_not_match_regex": ColumnValuesNotMatchRegexTest,
    "column_length_between": ColumnLengthBetweenTest,
    # Query-based table tests
    "table_custom_sql": TableCustomSQLTest,
}


class TestExecutor:
    """
    Orchestrates execution of data quality tests for a dataset.

    Retrieves profile data from DataHub and executes configured tests.
    """

    def __init__(
        self,
        graph,  # AcrylDataHubGraph wrapper, use graph.graph to access DataHubGraph
        test_configs: List[TestConfig],
        connector_registry: Optional["ConnectorRegistry"] = None,
    ):
        self.graph = graph
        self.test_configs = test_configs
        self.connector_registry = connector_registry

    def execute_tests_for_dataset(
        self, dataset_urn: str
    ) -> List[MetadataChangeProposalWrapper]:
        """
        Execute all applicable tests for a dataset and return assertion MCPs.

        Args:
            dataset_urn: URN of the dataset to test

        Returns:
            List of MetadataChangeProposalWrapper for assertions
        """
        logger.info(f"Executing data quality tests for dataset: {dataset_urn}")

        # Find matching tests for this dataset
        matching_tests = self._find_matching_tests(dataset_urn)
        if not matching_tests:
            logger.debug(f"No matching tests found for dataset: {dataset_urn}")
            return []

        # Retrieve profile data (needed for profile-based tests)
        profile = self._get_dataset_profile(dataset_urn)
        if profile:
            logger.debug(
                f"Retrieved profile for {dataset_urn}: rowCount={profile.rowCount}"
            )
        else:
            logger.warning(f"No profile data found for {dataset_urn}")

        # Execute tests and collect assertion MCPs
        mcps: List[MetadataChangeProposalWrapper] = []
        for test_config in matching_tests:
            try:
                test_mcps = self._execute_single_test(
                    test_config, dataset_urn, profile
                )
                mcps.extend(test_mcps)
            except Exception as e:
                logger.error(f"Failed to execute test {test_config.name}: {e}")
                continue

        logger.info(
            f"Executed {len(matching_tests)} tests for {dataset_urn}, generated {len(mcps)} MCPs"
        )
        return mcps

    def _find_matching_tests(self, dataset_urn: str) -> List[TestConfig]:
        """Find tests that match the dataset URN pattern."""
        matching = []
        for test_config in self.test_configs:
            if fnmatch(dataset_urn, test_config.dataset_pattern):
                matching.append(test_config)
                logger.debug(
                    f"Test {test_config.name} matches dataset {dataset_urn}"
                )
        return matching

    def _get_dataset_profile(self, dataset_urn: str) -> DatasetProfileClass | None:
        """Retrieve dataset profile from DataHub."""
        try:
            # Access underlying DataHubGraph from AcrylDataHubGraph wrapper
            profile = self.graph.graph.get_aspect(
                entity_urn=dataset_urn,
                aspect_type=DatasetProfileClass,
                version=0,
            )
            return profile
        except Exception as e:
            logger.warning(f"Failed to retrieve profile for {dataset_urn}: {e}")
            return None

    def _execute_single_test(
        self,
        test_config: TestConfig,
        dataset_urn: str,
        profile: DatasetProfileClass | None,
    ) -> List[MetadataChangeProposalWrapper]:
        """Execute a single test and return assertion MCPs."""
        test_class = TEST_REGISTRY.get(test_config.type)
        if not test_class:
            logger.warning(f"Unknown test type: {test_config.type}")
            return []

        # Instantiate test template
        test = test_class(
            test_name=test_config.name,
            dataset_urn=dataset_urn,
            params=test_config.params,
            column=test_config.column,
        )

        # Execute test - pass connector_registry for query-based tests
        if hasattr(test, "set_connector_registry") and self.connector_registry:
            test.set_connector_registry(self.connector_registry)

        result = test.execute(profile=profile)

        # Build assertions
        assertion_urn = test.build_assertion_urn()
        assertion_info = test.build_assertion_info()
        assertion_result = test.build_assertion_result(result, assertion_urn)

        logger.info(
            f"Test {test_config.name} completed: {'PASS' if result.success else 'FAIL'}"
        )

        # Create MCPs for assertion info and result
        mcps = [
            MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=assertion_info,
            ),
            MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=assertion_result,
            ),
        ]

        return mcps
