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

from typing import Any, Dict, List, Set

from datahub_actions.plugin.action.governance.checks.base import (
    BaseGovernanceCheck,
    CheckResult,
)


class TagCheck(BaseGovernanceCheck):
    """
    Checks if an entity has required tags attached.

    Validates:
    - Presence of at least one required tag (any_of)
    - Presence of all required tags (all_of)
    """

    @property
    def check_type(self) -> str:
        return "requires_tag"

    def evaluate(
        self,
        entity_urn: str,
        metadata: Dict[str, Any],
        params: Dict[str, Any],
    ) -> CheckResult:
        """
        Evaluate tag requirements.

        Params:
            any_of (List[str]): Entity must have at least one of these tags
            all_of (List[str]): Entity must have all of these tags
        """
        any_of: List[str] = params.get("any_of", [])
        all_of: List[str] = params.get("all_of", [])

        if not any_of and not all_of:
            return self._create_result(
                check_name="has_tags",
                passed=False,
                message="No tag requirements specified in params (use 'any_of' or 'all_of')",
                details={},
            )

        global_tags = metadata.get("globalTags")
        if not global_tags:
            return self._create_result(
                check_name="has_tags",
                passed=False,
                message="No tags attached",
                details={
                    "required_any_of": any_of,
                    "required_all_of": all_of,
                    "actual_tags": [],
                },
            )

        tags = global_tags.get("tags", [])
        if not tags:
            return self._create_result(
                check_name="has_tags",
                passed=False,
                message="No tags attached",
                details={
                    "required_any_of": any_of,
                    "required_all_of": all_of,
                    "actual_tags": [],
                },
            )

        # Extract tag URNs from the metadata
        actual_tag_urns: Set[str] = set()
        for tag in tags:
            # Handle both dict format and nested structure
            if isinstance(tag, dict):
                tag_urn = tag.get("tag")
                if tag_urn:
                    actual_tag_urns.add(tag_urn)

        # Check any_of requirement
        if any_of:
            required_tags_set = set(any_of)
            found_tags = actual_tag_urns.intersection(required_tags_set)

            if found_tags:
                return self._create_result(
                    check_name="has_tags",
                    passed=True,
                    message=f"Found required tag(s): {', '.join(found_tags)}",
                    details={
                        "required_any_of": any_of,
                        "actual_tags": list(actual_tag_urns),
                        "matched_tags": list(found_tags),
                    },
                )
            else:
                return self._create_result(
                    check_name="has_tags",
                    passed=False,
                    message=f"None of the required tags found. Required: {', '.join(any_of)}",
                    details={
                        "required_any_of": any_of,
                        "actual_tags": list(actual_tag_urns),
                    },
                )

        # Check all_of requirement
        if all_of:
            required_tags_set = set(all_of)
            missing_tags = required_tags_set - actual_tag_urns

            if not missing_tags:
                return self._create_result(
                    check_name="has_tags",
                    passed=True,
                    message=f"All required tags found: {', '.join(all_of)}",
                    details={
                        "required_all_of": all_of,
                        "actual_tags": list(actual_tag_urns),
                    },
                )
            else:
                return self._create_result(
                    check_name="has_tags",
                    passed=False,
                    message=f"Missing required tags: {', '.join(missing_tags)}",
                    details={
                        "required_all_of": all_of,
                        "actual_tags": list(actual_tag_urns),
                        "missing_tags": list(missing_tags),
                    },
                )

        return self._create_result(
            check_name="has_tags",
            passed=False,
            message="Unknown error in tag evaluation",
            details={},
        )
