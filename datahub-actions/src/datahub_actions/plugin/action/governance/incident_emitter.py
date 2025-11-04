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
from typing import Any, Dict, List, Optional

from datahub_actions.plugin.action.governance.config import (
    GovernanceRuleConfig,
    IncidentConfig,
)
from datahub_actions.plugin.action.governance.rules_engine import RuleEvaluationResult
from datahub_actions.plugin.action.governance.utils.urn_utils import make_incident_id

logger = logging.getLogger(__name__)

# GraphQL mutation for raising incidents
# See: https://datahubproject.io/docs/incidents/
RAISE_INCIDENT_MUTATION = """
mutation raiseIncident($input: RaiseIncidentInput!) {
  raiseIncident(input: $input)
}
"""

# GraphQL mutation for updating incident status
UPDATE_INCIDENT_STATUS_MUTATION = """
mutation updateIncidentStatus($urn: String!, $input: UpdateIncidentStatusInput!) {
  updateIncidentStatus(urn: $urn, input: $input)
}
"""

# GraphQL query to check if incident exists
GET_INCIDENT_QUERY = """
query getIncident($urn: String!) {
  incident(urn: $urn) {
    urn
    status {
      state
    }
  }
}
"""


class IncidentEmitter:
    """
    Creates and manages incidents for governance violations.

    Features:
    - Creates incidents for failed checks (if configured)
    - Deduplicates incidents using custom incident IDs
    - Auto-resolves incidents when violations are fixed
    """

    def __init__(self, graph: Any):
        """
        Initialize the incident emitter.

        Args:
            graph: DataHub graph client with get_by_graphql_query capability
        """
        self.graph = graph
        self._incident_cache: Dict[str, str] = {}  # incident_id -> incident_urn

    def handle_violations(
        self,
        rule: GovernanceRuleConfig,
        result: RuleEvaluationResult,
    ) -> None:
        """
        Handle governance violations by creating or updating incidents.

        Args:
            rule: Governance rule configuration
            result: Rule evaluation result with check outcomes
        """
        if not rule.create_incident_on_fail:
            logger.debug(f"Incident creation disabled for rule: {rule.name}")
            return

        if not rule.incident_config:
            logger.warning(
                f"Incident creation enabled but no incident_config for rule: {rule.name}"
            )
            return

        if result.passed:
            # Rule passed - resolve any existing incidents
            self._resolve_incidents_if_needed(result)
        else:
            # Rule failed - create or update incidents
            self._create_or_update_incident(rule, result)

    def _create_or_update_incident(
        self,
        rule: GovernanceRuleConfig,
        result: RuleEvaluationResult,
    ) -> None:
        """Create a new incident or update existing one for a violation."""
        incident_config = rule.incident_config
        if not incident_config:
            return

        # Generate unique incident ID for this entity + rule combination
        incident_id = make_incident_id(
            result.entity_urn,
            rule.name,
            ",".join([c.check_type for c in result.failures]),
        )

        # Build incident description with failure details
        failure_details = "\n".join(
            [f"- {f.message}" for f in result.failures]
        )

        description = f"""Governance rule '{rule.name}' failed for entity {result.entity_urn}

Failed checks:
{failure_details}

Total checks: {len(result.check_results)}
Failed: {len(result.failures)}
Passed: {len(result.successes)}

This incident was automatically created by the DataHub Governance Bot.
"""

        # Check if incident already exists
        existing_incident_urn = self._find_incident(incident_id)

        if existing_incident_urn:
            logger.info(
                f"Incident already exists for {result.entity_urn}: {existing_incident_urn}"
            )
            return

        # Create new incident
        try:
            input_data = {
                "type": "CUSTOM",
                "customType": incident_config.custom_type,
                "title": f"Governance: {rule.name}",
                "description": description,
                "resourceUrn": result.entity_urn,
                "priority": incident_config.priority,
                "status": {
                    "state": "ACTIVE",
                    "stage": "TRIAGE",
                },
            }

            # Add assignees if configured
            if incident_config.assignees:
                input_data["assigneeUrns"] = incident_config.assignees

            response = self.graph.get_by_graphql_query(
                {
                    "query": RAISE_INCIDENT_MUTATION,
                    "variables": {"input": input_data},
                }
            )

            if response:
                incident_urn = response.get("raiseIncident")
                self._incident_cache[incident_id] = incident_urn
                logger.info(f"Created incident {incident_urn} for {result.entity_urn}")
            else:
                logger.error(f"Failed to create incident: {response}")

        except Exception as e:
            logger.error(
                f"Failed to create incident for {result.entity_urn}: {e}",
                exc_info=True,
            )

    def _resolve_incidents_if_needed(self, result: RuleEvaluationResult) -> None:
        """
        Resolve any open incidents for this entity+rule if they now pass.

        This auto-resolves incidents when violations are fixed.
        """
        for check_result in result.successes:
            incident_id = make_incident_id(
                result.entity_urn,
                result.rule_name,
                check_result.check_type,
            )

            existing_incident_urn = self._find_incident(incident_id)
            if existing_incident_urn:
                try:
                    # Update incident status to RESOLVED
                    response = self.graph.get_by_graphql_query(
                        {
                            "query": UPDATE_INCIDENT_STATUS_MUTATION,
                            "variables": {
                                "urn": existing_incident_urn,
                                "input": {
                                    "state": "RESOLVED",
                                    "message": "Governance check now passes. Auto-resolved by Governance Bot.",
                                },
                            },
                        }
                    )

                    logger.info(
                        f"Resolved incident {existing_incident_urn} for {result.entity_urn}"
                    )

                    # Remove from cache
                    self._incident_cache.pop(incident_id, None)

                except Exception as e:
                    logger.error(f"Failed to resolve incident: {e}", exc_info=True)

    def _find_incident(self, incident_id: str) -> Optional[str]:
        """
        Find an existing incident by custom ID.

        Note: This is a simplified implementation. In production, you'd need
        a proper incident search/query mechanism, potentially using custom aspects
        or properties to store incident_id for lookup.

        For now, we rely on in-memory cache.
        """
        return self._incident_cache.get(incident_id)
