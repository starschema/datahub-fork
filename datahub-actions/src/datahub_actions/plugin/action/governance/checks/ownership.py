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

from typing import Any, Dict, List

from datahub_actions.plugin.action.governance.checks.base import (
    BaseGovernanceCheck,
    CheckResult,
)


class OwnershipCheck(BaseGovernanceCheck):
    """
    Checks if an entity has sufficient ownership information.

    Validates:
    - Minimum number of owners
    - Owner types (e.g., DATAOWNER, TECHNICAL_OWNER, BUSINESS_OWNER)
    """

    @property
    def check_type(self) -> str:
        return "requires_owner"

    def evaluate(
        self,
        entity_urn: str,
        metadata: Dict[str, Any],
        params: Dict[str, Any],
    ) -> CheckResult:
        """
        Evaluate ownership requirements.

        Params:
            min_owners (int): Minimum number of owners required (default: 1)
            allowed_types (List[str]): Allowed owner types. If specified, only
                owners with these types count. If empty, all types are allowed.
        """
        min_owners = params.get("min_owners", 1)
        allowed_types: List[str] = params.get("allowed_types", [])

        ownership = metadata.get("ownership")
        if not ownership:
            return self._create_result(
                check_name=f"min_{min_owners}_owners",
                passed=False,
                message=f"No ownership information found (required: {min_owners} owner(s))",
                details={"min_owners": min_owners, "actual_owners": 0},
            )

        owners = ownership.get("owners", [])
        if not owners:
            return self._create_result(
                check_name=f"min_{min_owners}_owners",
                passed=False,
                message=f"No owners assigned (required: {min_owners} owner(s))",
                details={"min_owners": min_owners, "actual_owners": 0},
            )

        # Filter by allowed types if specified
        if allowed_types:
            valid_owners = [
                owner
                for owner in owners
                if owner.get("type") in allowed_types or owner.get("typeUrn") in allowed_types
            ]
        else:
            valid_owners = owners

        passed = len(valid_owners) >= min_owners

        if passed:
            return self._create_result(
                check_name=f"min_{min_owners}_owners",
                passed=True,
                message=f"Found {len(valid_owners)} valid owner(s) (required: {min_owners})",
                details={
                    "min_owners": min_owners,
                    "actual_owners": len(valid_owners),
                    "owner_urns": [o.get("owner") for o in valid_owners],
                    "owner_types": [o.get("type") for o in valid_owners],
                },
            )
        else:
            return self._create_result(
                check_name=f"min_{min_owners}_owners",
                passed=False,
                message=f"Insufficient owners: found {len(valid_owners)}, required {min_owners}",
                details={
                    "min_owners": min_owners,
                    "actual_owners": len(valid_owners),
                    "allowed_types": allowed_types,
                    "total_owners": len(owners),
                },
            )
