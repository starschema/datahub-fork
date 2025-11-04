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

import json
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

    def _emit_via_rest(self, entity_urn: str, entity_type: str, aspect_name: str, aspect_value: dict) -> bool:
        """
        Emit aspect via REST API to avoid Avro serialization issues.

        Args:
            entity_urn: URN of the entity
            entity_type: Type of entity (e.g., "test", "dataset")
            aspect_name: Name of the aspect (e.g., "testInfo", "testResults")
            aspect_value: Aspect data as dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            import requests

            # Get GMS server URL from graph config
            gms_url = self.graph.graph.config.server

            payload = {
                "proposal": {
                    "entityType": entity_type,
                    "entityUrn": entity_urn,
                    "aspectName": aspect_name,
                    "aspect": {
                        "contentType": "application/json",
                        "value": json.dumps(aspect_value)
                    },
                    "changeType": "UPSERT"
                }
            }

            headers = {
                "Content-Type": "application/json",
                "X-RestLi-Protocol-Version": "2.0.0"
            }

            # Add auth headers if present
            if self.graph.graph.config.token:
                headers["Authorization"] = f"Bearer {self.graph.graph.config.token}"

            response = requests.post(
                f"{gms_url}/aspects?action=ingestProposal",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            logger.debug(f"Successfully emitted {aspect_name} for {entity_urn} via REST API")
            return True

        except Exception as e:
            logger.error(f"Failed to emit {aspect_name} via REST API: {e}", exc_info=True)
            return False

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
                # First create TestKey aspect (required for Test entity)
                # Extract the test ID from URN: urn:li:test:governance.rule_name.check_type
                test_id = test_urn.split(":")[-1]

                test_key_dict = {
                    "id": test_id
                }

                key_success = self._emit_via_rest(
                    entity_urn=test_urn,
                    entity_type="test",
                    aspect_name="testKey",
                    aspect_value=test_key_dict
                )

                if not key_success:
                    logger.warning(f"Failed to create TestKey for {test_urn}, skipping testInfo")
                    continue

                # Now create TestInfo aspect
                test_info_dict = {
                    "name": f"{result.rule_name} - {check_result.check_type}",
                    "category": "GOVERNANCE",
                    "description": f"Governance check: {check_result.message}",
                    "definition": f"Rule: {result.rule_name}, Check: {check_result.check_type}",
                }

                success = self._emit_via_rest(
                    entity_urn=test_urn,
                    entity_type="test",
                    aspect_name="testInfo",
                    aspect_value=test_info_dict
                )

                if success:
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

            test_result_entry = {
                "test": test_urn,
                "type": "SUCCESS" if check_result.passed else "FAILURE",
            }

            if check_result.passed:
                passing_tests.append(test_result_entry)
            else:
                failing_tests.append(test_result_entry)

        # Create TestResults aspect as dict
        test_results_dict = {
            "passing": passing_tests,
            "failing": failing_tests,
        }

        try:
            success = self._emit_via_rest(
                entity_urn=result.entity_urn,
                entity_type="dataset",  # Entity type of the entity being tested
                aspect_name="testResults",
                aspect_value=test_results_dict
            )

            if success:
                logger.info(
                    f"Emitted TestResults for {result.entity_urn}: "
                    f"{len(passing_tests)} passing, {len(failing_tests)} failing"
                )
        except Exception as e:
            logger.error(f"Failed to emit TestResults aspect: {e}", exc_info=True)
