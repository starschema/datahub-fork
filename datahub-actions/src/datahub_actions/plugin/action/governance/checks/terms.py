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


class GlossaryTermCheck(BaseGovernanceCheck):
    """
    Checks if an entity has required glossary terms attached.

    Validates:
    - Presence of at least one required term (any_of)
    - Presence of all required terms (all_of)
    """

    @property
    def check_type(self) -> str:
        return "requires_glossary_term"

    def evaluate(
        self,
        entity_urn: str,
        metadata: Dict[str, Any],
        params: Dict[str, Any],
    ) -> CheckResult:
        """
        Evaluate glossary term requirements.

        Params:
            any_of (List[str]): Entity must have at least one of these terms
            all_of (List[str]): Entity must have all of these terms
        """
        any_of: List[str] = params.get("any_of", [])
        all_of: List[str] = params.get("all_of", [])

        if not any_of and not all_of:
            return self._create_result(
                check_name="has_glossary_terms",
                passed=False,
                message="No term requirements specified in params (use 'any_of' or 'all_of')",
                details={},
            )

        glossary_terms = metadata.get("glossaryTerms")
        if not glossary_terms:
            return self._create_result(
                check_name="has_glossary_terms",
                passed=False,
                message="No glossary terms attached",
                details={
                    "required_any_of": any_of,
                    "required_all_of": all_of,
                    "actual_terms": [],
                },
            )

        terms = glossary_terms.get("terms", [])
        if not terms:
            return self._create_result(
                check_name="has_glossary_terms",
                passed=False,
                message="No glossary terms attached",
                details={
                    "required_any_of": any_of,
                    "required_all_of": all_of,
                    "actual_terms": [],
                },
            )

        # Extract term URNs from the metadata
        actual_term_urns: Set[str] = set()
        for term in terms:
            # Handle both dict format and nested structure
            if isinstance(term, dict):
                term_urn = term.get("urn") or term.get("term")
                if term_urn:
                    actual_term_urns.add(term_urn)

        # Check any_of requirement
        if any_of:
            required_terms_set = set(any_of)
            found_terms = actual_term_urns.intersection(required_terms_set)

            if found_terms:
                return self._create_result(
                    check_name="has_glossary_terms",
                    passed=True,
                    message=f"Found required term(s): {', '.join(found_terms)}",
                    details={
                        "required_any_of": any_of,
                        "actual_terms": list(actual_term_urns),
                        "matched_terms": list(found_terms),
                    },
                )
            else:
                return self._create_result(
                    check_name="has_glossary_terms",
                    passed=False,
                    message=f"None of the required terms found. Required: {', '.join(any_of)}",
                    details={
                        "required_any_of": any_of,
                        "actual_terms": list(actual_term_urns),
                    },
                )

        # Check all_of requirement
        if all_of:
            required_terms_set = set(all_of)
            missing_terms = required_terms_set - actual_term_urns

            if not missing_terms:
                return self._create_result(
                    check_name="has_glossary_terms",
                    passed=True,
                    message=f"All required terms found: {', '.join(all_of)}",
                    details={
                        "required_all_of": all_of,
                        "actual_terms": list(actual_term_urns),
                    },
                )
            else:
                return self._create_result(
                    check_name="has_glossary_terms",
                    passed=False,
                    message=f"Missing required terms: {', '.join(missing_terms)}",
                    details={
                        "required_all_of": all_of,
                        "actual_terms": list(actual_term_urns),
                        "missing_terms": list(missing_terms),
                    },
                )

        return self._create_result(
            check_name="has_glossary_terms",
            passed=False,
            message="Unknown error in term evaluation",
            details={},
        )
