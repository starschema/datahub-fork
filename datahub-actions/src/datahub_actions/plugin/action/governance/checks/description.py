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

from typing import Any, Dict

from datahub_actions.plugin.action.governance.checks.base import (
    BaseGovernanceCheck,
    CheckResult,
)


class DescriptionCheck(BaseGovernanceCheck):
    """
    Checks if an entity has a non-empty description.

    Validates:
    - Presence of description text
    - Minimum description length (optional)
    """

    @property
    def check_type(self) -> str:
        return "requires_description"

    def evaluate(
        self,
        entity_urn: str,
        metadata: Dict[str, Any],
        params: Dict[str, Any],
    ) -> CheckResult:
        """
        Evaluate description requirements.

        Params:
            min_length (int): Minimum description length in characters (default: 1)
        """
        min_length = params.get("min_length", 1)

        # Check editableProperties first (user-editable description)
        editable_props = metadata.get("editableProperties")
        if editable_props:
            description = editable_props.get("description")
            if description and len(description.strip()) >= min_length:
                return self._create_result(
                    check_name="has_description",
                    passed=True,
                    message=f"Description found ({len(description)} characters)",
                    details={
                        "description_length": len(description),
                        "min_length": min_length,
                        "source": "editableProperties",
                    },
                )

        # Fall back to properties (platform-provided description)
        properties = metadata.get("properties")
        if properties:
            description = properties.get("description")
            if description and len(description.strip()) >= min_length:
                return self._create_result(
                    check_name="has_description",
                    passed=True,
                    message=f"Description found ({len(description)} characters)",
                    details={
                        "description_length": len(description),
                        "min_length": min_length,
                        "source": "properties",
                    },
                )

        # Check institutionalMemory for documentation links
        institutional_memory = metadata.get("institutionalMemory")
        if institutional_memory:
            elements = institutional_memory.get("elements", [])
            if elements:
                return self._create_result(
                    check_name="has_description",
                    passed=True,
                    message=f"Documentation links found ({len(elements)} link(s))",
                    details={
                        "doc_links": len(elements),
                        "source": "institutionalMemory",
                    },
                )

        # No description found
        return self._create_result(
            check_name="has_description",
            passed=False,
            message=f"No description found (minimum length: {min_length} characters)",
            details={"min_length": min_length},
        )
