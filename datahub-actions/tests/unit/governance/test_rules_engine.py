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

from datahub_actions.plugin.action.governance.config import (
    CheckConfig,
    GovernanceRuleConfig,
    ScopeConfig,
)
from datahub_actions.plugin.action.governance.rules_engine import GovernanceRulesEngine


class TestGovernanceRulesEngine:
    """Test cases for GovernanceRulesEngine."""

    def test_engine_evaluates_matching_rule(self):
        """Test that engine evaluates rules that match entity scope."""
        rule = GovernanceRuleConfig(
            name="test_rule",
            enabled=True,
            scope=ScopeConfig(
                entity_types=["dataset"],
                platforms=["snowflake"],
            ),
            checks=[
                CheckConfig(
                    type="requires_owner",
                    params={"min_owners": 1},
                )
            ],
        )

        engine = GovernanceRulesEngine(rules=[rule])

        metadata = {
            "type": "dataset",
            "platform": {"name": "snowflake"},
            "ownership": {
                "owners": [
                    {"owner": "urn:li:corpuser:jdoe", "type": "DATAOWNER"}
                ]
            },
        }

        results = engine.evaluate(
            entity_urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,db.table,PROD)",
            metadata=metadata,
        )

        assert len(results) == 1
        assert results[0].rule_name == "test_rule"
        assert results[0].passed is True

    def test_engine_skips_non_matching_entity_type(self):
        """Test that engine skips rules that don't match entity type."""
        rule = GovernanceRuleConfig(
            name="dataset_only_rule",
            enabled=True,
            scope=ScopeConfig(
                entity_types=["dataset"],
            ),
            checks=[
                CheckConfig(
                    type="requires_owner",
                    params={"min_owners": 1},
                )
            ],
        )

        engine = GovernanceRulesEngine(rules=[rule])

        metadata = {
            "type": "dashboard",
        }

        results = engine.evaluate(
            entity_urn="urn:li:dashboard:(looker,dashboard_id)",
            metadata=metadata,
        )

        assert len(results) == 0

    def test_engine_skips_non_matching_platform(self):
        """Test that engine skips rules that don't match platform."""
        rule = GovernanceRuleConfig(
            name="snowflake_only_rule",
            enabled=True,
            scope=ScopeConfig(
                entity_types=["dataset"],
                platforms=["snowflake"],
            ),
            checks=[
                CheckConfig(
                    type="requires_owner",
                    params={"min_owners": 1},
                )
            ],
        )

        engine = GovernanceRulesEngine(rules=[rule])

        metadata = {
            "type": "dataset",
            "platform": {"name": "bigquery"},
        }

        results = engine.evaluate(
            entity_urn="urn:li:dataset:(urn:li:dataPlatform:bigquery,project.dataset.table,PROD)",
            metadata=metadata,
        )

        assert len(results) == 0

    def test_engine_filters_by_tags_any(self):
        """Test that engine filters entities by tags_any."""
        rule = GovernanceRuleConfig(
            name="pii_rule",
            enabled=True,
            scope=ScopeConfig(
                entity_types=["dataset"],
                tags_any=["urn:li:tag:PII"],
            ),
            checks=[
                CheckConfig(
                    type="requires_owner",
                    params={"min_owners": 1},
                )
            ],
        )

        engine = GovernanceRulesEngine(rules=[rule])

        # Entity with PII tag - should match
        metadata_with_tag = {
            "type": "dataset",
            "globalTags": {
                "tags": [
                    {"tag": "urn:li:tag:PII"},
                ]
            },
            "ownership": {
                "owners": [{"owner": "urn:li:corpuser:jdoe", "type": "DATAOWNER"}]
            },
        }

        results = engine.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata_with_tag,
        )

        assert len(results) == 1

        # Entity without PII tag - should not match
        metadata_without_tag = {
            "type": "dataset",
            "globalTags": {
                "tags": [
                    {"tag": "urn:li:tag:Production"},
                ]
            },
        }

        results = engine.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata_without_tag,
        )

        assert len(results) == 0

    def test_engine_evaluates_multiple_checks(self):
        """Test that engine evaluates multiple checks in a rule."""
        rule = GovernanceRuleConfig(
            name="multi_check_rule",
            enabled=True,
            scope=ScopeConfig(
                entity_types=["dataset"],
            ),
            checks=[
                CheckConfig(
                    type="requires_owner",
                    params={"min_owners": 1},
                ),
                CheckConfig(
                    type="requires_description",
                    params={"min_length": 10},
                ),
            ],
        )

        engine = GovernanceRulesEngine(rules=[rule])

        metadata = {
            "type": "dataset",
            "ownership": {
                "owners": [{"owner": "urn:li:corpuser:jdoe", "type": "DATAOWNER"}]
            },
            "editableProperties": {
                "description": "Short"  # Too short
            },
        }

        results = engine.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
        )

        assert len(results) == 1
        assert results[0].passed is False  # One check failed
        assert len(results[0].check_results) == 2
        assert len(results[0].failures) == 1  # Description check failed
        assert len(results[0].successes) == 1  # Owner check passed

    def test_engine_skips_disabled_rules(self):
        """Test that engine skips disabled rules."""
        rule = GovernanceRuleConfig(
            name="disabled_rule",
            enabled=False,
            scope=ScopeConfig(
                entity_types=["dataset"],
            ),
            checks=[
                CheckConfig(
                    type="requires_owner",
                    params={"min_owners": 1},
                )
            ],
        )

        engine = GovernanceRulesEngine(rules=[rule])

        metadata = {
            "type": "dataset",
        }

        results = engine.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
        )

        assert len(results) == 0

    def test_engine_evaluates_multiple_rules(self):
        """Test that engine evaluates multiple applicable rules."""
        rule1 = GovernanceRuleConfig(
            name="rule1",
            enabled=True,
            scope=ScopeConfig(entity_types=["dataset"]),
            checks=[CheckConfig(type="requires_owner", params={"min_owners": 1})],
        )

        rule2 = GovernanceRuleConfig(
            name="rule2",
            enabled=True,
            scope=ScopeConfig(entity_types=["dataset"]),
            checks=[CheckConfig(type="requires_description", params={})],
        )

        engine = GovernanceRulesEngine(rules=[rule1, rule2])

        metadata = {
            "type": "dataset",
            "ownership": {
                "owners": [{"owner": "urn:li:corpuser:jdoe", "type": "DATAOWNER"}]
            },
            "editableProperties": {
                "description": "This is a test dataset"
            },
        }

        results = engine.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
        )

        assert len(results) == 2
        assert all(r.passed for r in results)
