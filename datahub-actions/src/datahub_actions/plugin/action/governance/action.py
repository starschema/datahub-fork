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
from pathlib import Path
from typing import Dict, Any

import yaml
from datahub.metadata.schema_classes import (
    EntityChangeEventClass as EntityChangeEvent,
    MetadataChangeLogClass as MetadataChangeLog,
)
from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.action.governance.config import (
    GovernanceConfig,
    RulesFileConfig,
)
from datahub_actions.plugin.action.governance.incident_emitter import IncidentEmitter
from datahub_actions.plugin.action.governance.rules_engine import GovernanceRulesEngine
from datahub_actions.plugin.action.governance.test_emitter import TestEmitter
from datahub_actions.plugin.action.governance.utils.graphql_helpers import (
    fetch_entity_metadata,
)
from datahub_actions.plugin.action.governance.utils.urn_utils import extract_entity_type

logger = logging.getLogger(__name__)


class GovernanceAction(Action):
    """
    DataHub Action that enforces governance rules on entity changes.

    Features:
    - Monitors entity change events (MetadataChangeLog, EntityChangeEvent)
    - Evaluates governance rules from YAML configuration
    - Emits TestResults aspect for UI visibility (Governance tab)
    - Creates incidents for critical violations (optional)
    - Real-time governance validation

    Configuration:
        enabled: Whether the action is enabled (default: true)
        rules_file: Path to YAML file with governance rules

    See: https://datahubproject.io/docs/actions/
    """

    @classmethod
    def create(cls, config_dict: Dict[str, Any], ctx: PipelineContext) -> "Action":
        """
        Factory method to create GovernanceAction from configuration.

        Args:
            config_dict: Configuration dictionary
            ctx: Pipeline context with graph client

        Returns:
            Initialized GovernanceAction instance
        """
        action_config = GovernanceConfig.model_validate(config_dict or {})
        logger.info(
            f"Governance Action configured with rules file: {action_config.rules_file}"
        )
        return cls(action_config, ctx)

    def __init__(self, config: GovernanceConfig, ctx: PipelineContext):
        """
        Initialize the Governance Action.

        Args:
            config: Governance action configuration
            ctx: Pipeline context with graph client
        """
        self.config = config
        self.ctx = ctx

        if not ctx.graph:
            raise ValueError("DataHub graph client is required for Governance Action")

        # Load governance rules from YAML file
        rules_config = self._load_rules_file(config.rules_file)

        # Initialize rules engine
        self.rules_engine = GovernanceRulesEngine(rules_config.rules)

        # Initialize emitters
        self.test_emitter = TestEmitter(graph=ctx.graph)
        self.incident_emitter = IncidentEmitter(graph=ctx.graph)

        # Track rules by name for easy lookup
        self.rules_by_name = {rule.name: rule for rule in rules_config.rules}

        logger.info(
            f"GovernanceAction initialized with {len(rules_config.rules)} rules"
        )

    def act(self, event: EventEnvelope) -> None:
        """
        Process incoming DataHub events and enforce governance rules.

        Listens for:
        - MetadataChangeLogEvent_v1: Entity metadata changes
        - EntityChangeEvent_v1: Entity lifecycle events

        For each event:
        1. Extract entity URN
        2. Fetch entity metadata via GraphQL
        3. Evaluate applicable governance rules
        4. Emit TestResults for UI visibility
        5. Create/update incidents if configured

        Args:
            event: DataHub event envelope
        """
        if not self.config.enabled:
            logger.debug("Governance Action is disabled, skipping event")
            return

        try:
            entity_urn = None

            # Handle MetadataChangeLog events
            if event.event_type == "MetadataChangeLogEvent_v1":
                assert isinstance(event.event, MetadataChangeLog)
                mcl: MetadataChangeLog = event.event
                entity_urn = mcl.entityUrn

                logger.debug(
                    f"Processing MCL event for {mcl.entityType}: {entity_urn}, "
                    f"aspect: {mcl.aspectName}"
                )

            # Handle EntityChangeEvent
            elif event.event_type == "EntityChangeEvent_v1":
                assert isinstance(event.event, EntityChangeEvent)
                entity_change: EntityChangeEvent = event.event
                entity_urn = entity_change.entityUrn

                logger.debug(
                    f"Processing EntityChangeEvent for {entity_change.entityType}: "
                    f"{entity_urn}"
                )

            else:
                logger.debug(f"Skipping unsupported event type: {event.event_type}")
                return

            if not entity_urn:
                logger.warning("No entity URN found in event, skipping")
                return

            # Process the entity
            self._process_entity(entity_urn)

        except Exception as e:
            logger.error(f"Failed to process event: {e}", exc_info=True)

    def _process_entity(self, entity_urn: str) -> None:
        """
        Process a single entity through governance checks.

        Args:
            entity_urn: URN of the entity to check
        """
        logger.info(f"Processing entity for governance checks: {entity_urn}")

        # Fetch entity metadata via GraphQL
        metadata = fetch_entity_metadata(self.ctx.graph, entity_urn)
        if not metadata:
            logger.warning(f"Could not fetch metadata for {entity_urn}, skipping")
            return

        # Evaluate all applicable governance rules
        rule_results = self.rules_engine.evaluate(entity_urn, metadata)

        if not rule_results:
            logger.debug(f"No applicable rules for {entity_urn}")
            return

        # Emit TestResults aspect for UI visibility
        try:
            self.test_emitter.emit_results(rule_results)
        except Exception as e:
            logger.error(f"Failed to emit test results: {e}", exc_info=True)

        # Handle incidents for violations
        for result in rule_results:
            rule = self.rules_by_name.get(result.rule_name)
            if rule:
                try:
                    self.incident_emitter.handle_violations(rule, result)
                except Exception as e:
                    logger.error(
                        f"Failed to handle incidents for rule {result.rule_name}: {e}",
                        exc_info=True,
                    )

        # Log summary
        total_rules = len(rule_results)
        passed_rules = sum(1 for r in rule_results if r.passed)
        failed_rules = total_rules - passed_rules

        logger.info(
            f"Governance evaluation complete for {entity_urn}: "
            f"{passed_rules}/{total_rules} rules passed, {failed_rules} failed"
        )

    def _load_rules_file(self, rules_file_path: str) -> RulesFileConfig:
        """
        Load and parse governance rules from YAML file.

        Args:
            rules_file_path: Path to rules YAML file

        Returns:
            Parsed rules configuration

        Raises:
            FileNotFoundError: If rules file doesn't exist
            ValueError: If rules file is invalid
        """
        path = Path(rules_file_path)
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_file_path}")

        logger.info(f"Loading governance rules from: {rules_file_path}")

        with open(path, "r") as f:
            rules_dict = yaml.safe_load(f)

        rules_config = RulesFileConfig.model_validate(rules_dict)

        logger.info(f"Loaded {len(rules_config.rules)} governance rules")
        return rules_config

    def close(self) -> None:
        """Cleanup resources."""
        logger.info("Governance Action closing")
