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

from typing import Any, Dict, List, Optional

from pydantic import Field

from datahub.configuration.common import ConfigModel


class ScopeConfig(ConfigModel):
    """Defines the scope of entities to which a governance rule applies."""

    entity_types: List[str] = Field(
        default_factory=list,
        description="Entity types to check (e.g., DATASET, DASHBOARD, CHART, DATA_JOB)",
    )
    platforms: List[str] = Field(
        default_factory=list,
        description="Platform names to filter (e.g., snowflake, bigquery, dbt)",
    )
    envs: List[str] = Field(
        default_factory=list,
        description="Environments to filter (e.g., PROD, DEV, QA)",
    )
    tags_any: List[str] = Field(
        default_factory=list,
        description="Entities must have at least one of these tags (URNs or tag names)",
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Domain URNs to filter",
    )


class CheckConfig(ConfigModel):
    """Configuration for a single governance check within a rule."""

    type: str = Field(
        description="Check type (e.g., requires_owner, requires_description, requires_glossary_term, requires_tag)"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Check-specific parameters (e.g., min_owners, allowed_types, any_of)",
    )


class IncidentConfig(ConfigModel):
    """Configuration for incident creation when a rule fails."""

    priority: str = Field(
        default="MEDIUM",
        description="Incident priority: LOW, MEDIUM, HIGH, CRITICAL",
    )
    assignees: List[str] = Field(
        default_factory=list,
        description="List of user or group URNs to assign the incident to",
    )
    custom_type: str = Field(
        default="GOVERNANCE_VIOLATION",
        description="Custom incident type for categorization",
    )


class GovernanceRuleConfig(ConfigModel):
    """Configuration for a single governance rule."""

    name: str = Field(
        description="Unique name for this governance rule"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this rule is enabled",
    )
    scope: ScopeConfig = Field(
        description="Scope defining which entities this rule applies to"
    )
    checks: List[CheckConfig] = Field(
        description="List of governance checks to perform"
    )
    emit_test_results: bool = Field(
        default=True,
        description="Whether to emit test results for UI visibility (Governance tab)",
    )
    create_incident_on_fail: bool = Field(
        default=False,
        description="Whether to create incidents when checks fail",
    )
    incident_config: Optional[IncidentConfig] = Field(
        default=None,
        description="Incident configuration (required if create_incident_on_fail is True)",
    )


class RulesFileConfig(ConfigModel):
    """Root configuration structure for the rules YAML file."""

    rules: List[GovernanceRuleConfig] = Field(
        description="List of governance rules to evaluate"
    )


class GovernanceConfig(ConfigModel):
    """Configuration for the Governance Action plugin."""

    enabled: bool = Field(
        default=True,
        description="Whether the Governance Action is enabled",
    )
    rules_file: str = Field(
        description="Path to the YAML file containing governance rules"
    )
