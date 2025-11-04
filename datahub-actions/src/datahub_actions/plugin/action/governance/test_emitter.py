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
from typing import Any, List

from datahub.emitter.mce_builder import make_data_platform_urn
from datahub.metadata.schema_classes import (
    MetadataChangeProposalClass as MetadataChangeProposal,
    TestInfoClass,
    TestResultClass,
    TestResultsClass,
)
from datahub_actions.plugin.action.governance.rules_engine import RuleEvaluationResult
from datahub_actions.plugin.action.governance.utils.urn_utils import make_test_urn

logger = logging.getLogger(__name__)


class TestEmitter:
    """
    Emits Test entities and TestResults aspects for governance checks.

    This makes governance results visible in the DataHub UI Governance tab.

    See: https://datahubproject.io/docs/tests/
    """

    def __init__(self, graph: Any):
        """
        Initialize the test emitter.

        Args:
            graph: DataHub graph client with emit capability
        """
        self.graph = graph
        self._created_tests = set()  # Track created test entities

    def emit_results(self, rule_results: List[RuleEvaluationResult]) -> None:
        """
        Emit test results for governance rule evaluations.

        For each rule evaluation:
        1. Create Test entities (if not already created)
        2. Emit TestResults aspect to the checked entity

        Args:
            rule_results: List of rule evaluation results for entities
        """
        for result in rule_results:
            try:
                # Ensure Test entities exist
                self._ensure_test_entities(result)

                # Emit TestResults aspect to entity
                self._emit_test_results_aspect(result)

            except Exception as e:
                logger.error(
                    f"Failed to emit test results for {result.entity_urn}, rule {result.rule_name}: {e}",
                    exc_info=True,
                )

    def _ensure_test_entities(self, result: RuleEvaluationResult) -> None:
        """
        Create Test entities for each check in the rule (if not already created).

        Test entities represent the governance checks and are shown in the UI.
        """
        for check_result in result.check_results:
            test_urn = make_test_urn(result.rule_name, check_result.check_type)

            if test_urn in self._created_tests:
                # Already created in this session
                continue

            try:
                # Create Test entity
                test_info = TestInfoClass(
                    name=f"{result.rule_name} - {check_result.check_type}",
                    category="GOVERNANCE",
                    description=f"Governance check: {check_result.message}",
                    definition=f"Rule: {result.rule_name}, Check: {check_result.check_type}",
                )

                mcp = MetadataChangeProposal(
                    entityUrn=test_urn,
                    entityType="test",
                    aspectName="testInfo",
                    aspect=test_info,
                    changeType="UPSERT",
                )

                # Try emit_mcp first, fall back to emit
                if hasattr(self.graph.graph, 'emit_mcp'):
                    self.graph.graph.emit_mcp(mcp)
                else:
                    self.graph.graph.emit(mcp)
                self._created_tests.add(test_urn)
                logger.debug(f"Created Test entity: {test_urn}")

            except Exception as e:
                logger.error(f"Failed to create Test entity {test_urn}: {e}")

    def _emit_test_results_aspect(self, result: RuleEvaluationResult) -> None:
        """
        Emit TestResults aspect to the entity, making results visible in Governance tab.

        TestResults aspect contains:
        - passing: List of passed test URNs
        - failing: List of failed test URNs
        """
        passing_tests = []
        failing_tests = []

        for check_result in result.check_results:
            test_urn = make_test_urn(result.rule_name, check_result.check_type)

            test_result_entry = TestResultClass(
                test=test_urn,
                type="SUCCESS" if check_result.passed else "FAILURE",
            )

            if check_result.passed:
                passing_tests.append(test_result_entry)
            else:
                failing_tests.append(test_result_entry)

        # Create TestResults aspect
        test_results = TestResultsClass(
            passing=passing_tests,
            failing=failing_tests,
        )

        mcp = MetadataChangeProposal(
            entityUrn=result.entity_urn,
            entityType=None,  # Will be inferred from URN
            aspectName="testResults",
            aspect=test_results,
            changeType="UPSERT",
        )

        try:
            # Try emit_mcp first, fall back to emit
            if hasattr(self.graph.graph, 'emit_mcp'):
                self.graph.graph.emit_mcp(mcp)
            else:
                self.graph.graph.emit(mcp)
            logger.info(
                f"Emitted TestResults for {result.entity_urn}: "
                f"{len(passing_tests)} passing, {len(failing_tests)} failing"
            )
        except Exception as e:
            logger.error(f"Failed to emit TestResults aspect: {e}", exc_info=True)
