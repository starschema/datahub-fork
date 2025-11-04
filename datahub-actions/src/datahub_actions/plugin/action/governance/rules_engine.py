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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from datahub_actions.plugin.action.governance.checks.base import (
    BaseGovernanceCheck,
    CheckResult,
)
from datahub_actions.plugin.action.governance.checks.description import (
    DescriptionCheck,
)
from datahub_actions.plugin.action.governance.checks.ownership import OwnershipCheck
from datahub_actions.plugin.action.governance.checks.tags import TagCheck
from datahub_actions.plugin.action.governance.checks.terms import GlossaryTermCheck
from datahub_actions.plugin.action.governance.config import GovernanceRuleConfig
from datahub_actions.plugin.action.governance.utils.urn_utils import extract_entity_type

logger = logging.getLogger(__name__)


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a single rule against an entity."""

    rule_name: str
    entity_urn: str
    passed: bool
    check_results: List[CheckResult]

    @property
    def failures(self) -> List[CheckResult]:
        """Return only failed checks."""
        return [r for r in self.check_results if not r.passed]

    @property
    def successes(self) -> List[CheckResult]:
        """Return only passed checks."""
        return [r for r in self.check_results if r.passed]


class GovernanceRulesEngine:
    """
    Evaluates governance rules against entity metadata.

    The engine:
    1. Filters entities by rule scope (entity type, platform, tags, etc.)
    2. Runs configured checks for matching rules
    3. Returns detailed evaluation results
    """

    # Registry of available check implementations
    CHECK_REGISTRY: Dict[str, type] = {
        "requires_owner": OwnershipCheck,
        "requires_description": DescriptionCheck,
        "requires_glossary_term": GlossaryTermCheck,
        "requires_tag": TagCheck,
    }

    def __init__(self, rules: List[GovernanceRuleConfig]):
        """
        Initialize the rules engine.

        Args:
            rules: List of governance rule configurations
        """
        self.rules = [rule for rule in rules if rule.enabled]
        logger.info(f"Initialized GovernanceRulesEngine with {len(self.rules)} enabled rules")

    def evaluate(
        self,
        entity_urn: str,
        metadata: Dict[str, Any],
    ) -> List[RuleEvaluationResult]:
        """
        Evaluate all applicable rules for an entity.

        Args:
            entity_urn: URN of the entity to check
            metadata: Entity metadata from GraphQL

        Returns:
            List of rule evaluation results (only for rules that match scope)
        """
        results: List[RuleEvaluationResult] = []

        for rule in self.rules:
            # Check if entity is in scope for this rule
            if not self._matches_scope(entity_urn, metadata, rule):
                logger.debug(f"Entity {entity_urn} not in scope for rule: {rule.name}")
                continue

            # Run all checks for this rule
            check_results = self._run_checks(entity_urn, metadata, rule)

            # Determine overall rule pass/fail
            passed = all(r.passed for r in check_results)

            results.append(
                RuleEvaluationResult(
                    rule_name=rule.name,
                    entity_urn=entity_urn,
                    passed=passed,
                    check_results=check_results,
                )
            )

            logger.info(
                f"Rule '{rule.name}' evaluation for {entity_urn}: "
                f"{'PASSED' if passed else 'FAILED'} "
                f"({len(check_results)} checks)"
            )

        return results

    def _matches_scope(
        self,
        entity_urn: str,
        metadata: Dict[str, Any],
        rule: GovernanceRuleConfig,
    ) -> bool:
        """
        Check if entity matches the rule's scope filters.

        Scope filters: entity_types, platforms, envs, tags_any, domains
        """
        scope = rule.scope

        # Filter by entity type
        if scope.entity_types:
            entity_type = extract_entity_type(entity_urn) or metadata.get("type", "").lower()
            # Normalize: DATASET -> dataset
            normalized_types = [t.lower() for t in scope.entity_types]
            if entity_type.lower() not in normalized_types:
                logger.debug(f"Entity type {entity_type} not in scope: {scope.entity_types}")
                return False

        # Filter by platform
        if scope.platforms:
            platform = metadata.get("platform")
            if not platform:
                logger.debug("No platform info in metadata, cannot match platform filter")
                return False

            platform_name = platform.get("name") if isinstance(platform, dict) else str(platform)
            if platform_name.lower() not in [p.lower() for p in scope.platforms]:
                logger.debug(f"Platform {platform_name} not in scope: {scope.platforms}")
                return False

        # Filter by tags (tags_any: entity must have at least one)
        if scope.tags_any:
            global_tags = metadata.get("globalTags")
            if not global_tags:
                logger.debug("No tags found, but scope requires tags_any")
                return False

            tags = global_tags.get("tags", [])
            entity_tag_urns = {tag.get("tag") for tag in tags if isinstance(tag, dict)}

            # Check if entity has any of the required tags
            has_required_tag = any(
                tag_urn in entity_tag_urns for tag_urn in scope.tags_any
            )
            if not has_required_tag:
                logger.debug(f"Entity tags {entity_tag_urns} don't match any of {scope.tags_any}")
                return False

        # All filters passed
        return True

    def _run_checks(
        self,
        entity_urn: str,
        metadata: Dict[str, Any],
        rule: GovernanceRuleConfig,
    ) -> List[CheckResult]:
        """Run all configured checks for a rule."""
        results: List[CheckResult] = []

        for check_config in rule.checks:
            check_type = check_config.type

            # Get check implementation from registry
            check_class = self.CHECK_REGISTRY.get(check_type)
            if not check_class:
                logger.warning(
                    f"Unknown check type '{check_type}' in rule '{rule.name}', skipping"
                )
                continue

            # Instantiate and run check
            check_instance: BaseGovernanceCheck = check_class()
            result = check_instance.evaluate(
                entity_urn=entity_urn,
                metadata=metadata,
                params=check_config.params,
            )

            results.append(result)

        return results
