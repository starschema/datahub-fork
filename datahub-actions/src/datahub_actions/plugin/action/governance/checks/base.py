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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CheckResult:
    """Result of a governance check evaluation."""

    check_name: str
    check_type: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.check_type}: {self.message}"


class BaseGovernanceCheck(ABC):
    """
    Base class for all governance checks.

    Governance checks evaluate entity metadata against specific criteria
    and return a CheckResult indicating pass/fail status with details.
    """

    @property
    @abstractmethod
    def check_type(self) -> str:
        """Return the type identifier for this check (e.g., 'requires_owner')."""
        pass

    @abstractmethod
    def evaluate(
        self,
        entity_urn: str,
        metadata: Dict[str, Any],
        params: Dict[str, Any],
    ) -> CheckResult:
        """
        Evaluate the check against entity metadata.

        Args:
            entity_urn: URN of the entity being checked
            metadata: Entity metadata fetched from DataHub (ownership, tags, terms, etc.)
            params: Check-specific parameters from rule configuration

        Returns:
            CheckResult with pass/fail status and details
        """
        pass

    def _create_result(
        self,
        check_name: str,
        passed: bool,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> CheckResult:
        """Helper method to create a CheckResult."""
        return CheckResult(
            check_name=check_name,
            check_type=self.check_type,
            passed=passed,
            message=message,
            details=details or {},
        )
