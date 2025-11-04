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

from datahub_actions.plugin.action.governance.checks.description import (
    DescriptionCheck,
)
from datahub_actions.plugin.action.governance.checks.ownership import OwnershipCheck
from datahub_actions.plugin.action.governance.checks.tags import TagCheck
from datahub_actions.plugin.action.governance.checks.terms import GlossaryTermCheck


class TestOwnershipCheck:
    """Test cases for OwnershipCheck."""

    def test_ownership_check_passes_with_sufficient_owners(self):
        """Test that check passes when entity has enough owners."""
        check = OwnershipCheck()

        metadata = {
            "ownership": {
                "owners": [
                    {"owner": "urn:li:corpuser:jdoe", "type": "DATAOWNER"},
                    {"owner": "urn:li:corpuser:asmith", "type": "TECHNICAL_OWNER"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"min_owners": 2},
        )

        assert result.passed is True
        assert result.check_type == "requires_owner"
        assert "2 valid owner" in result.message

    def test_ownership_check_fails_with_insufficient_owners(self):
        """Test that check fails when entity has too few owners."""
        check = OwnershipCheck()

        metadata = {
            "ownership": {
                "owners": [
                    {"owner": "urn:li:corpuser:jdoe", "type": "DATAOWNER"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"min_owners": 2},
        )

        assert result.passed is False
        assert "Insufficient owners" in result.message

    def test_ownership_check_filters_by_type(self):
        """Test that check filters owners by allowed types."""
        check = OwnershipCheck()

        metadata = {
            "ownership": {
                "owners": [
                    {"owner": "urn:li:corpuser:jdoe", "type": "DATAOWNER"},
                    {"owner": "urn:li:corpuser:asmith", "type": "BUSINESS_OWNER"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"min_owners": 2, "allowed_types": ["DATAOWNER"]},
        )

        assert result.passed is False
        assert result.details["actual_owners"] == 1

    def test_ownership_check_fails_when_no_ownership(self):
        """Test that check fails when entity has no ownership information."""
        check = OwnershipCheck()

        metadata = {}

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"min_owners": 1},
        )

        assert result.passed is False
        assert "No ownership information" in result.message


class TestDescriptionCheck:
    """Test cases for DescriptionCheck."""

    def test_description_check_passes_with_editable_properties(self):
        """Test that check passes when entity has editableProperties description."""
        check = DescriptionCheck()

        metadata = {
            "editableProperties": {
                "description": "This is a test dataset with detailed information."
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"min_length": 10},
        )

        assert result.passed is True
        assert result.check_type == "requires_description"
        assert result.details["source"] == "editableProperties"

    def test_description_check_passes_with_properties(self):
        """Test that check passes with platform-provided description."""
        check = DescriptionCheck()

        metadata = {
            "properties": {
                "description": "Platform description"
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"min_length": 5},
        )

        assert result.passed is True
        assert result.details["source"] == "properties"

    def test_description_check_fails_when_too_short(self):
        """Test that check fails when description is too short."""
        check = DescriptionCheck()

        metadata = {
            "editableProperties": {
                "description": "Short"
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"min_length": 50},
        )

        assert result.passed is False

    def test_description_check_passes_with_documentation_links(self):
        """Test that check passes when entity has institutional memory."""
        check = DescriptionCheck()

        metadata = {
            "institutionalMemory": {
                "elements": [
                    {"url": "https://wiki.example.com/dataset", "description": "Wiki page"}
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"min_length": 1},
        )

        assert result.passed is True
        assert result.details["source"] == "institutionalMemory"

    def test_description_check_fails_when_no_description(self):
        """Test that check fails when entity has no description."""
        check = DescriptionCheck()

        metadata = {}

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={},
        )

        assert result.passed is False
        assert "No description found" in result.message


class TestGlossaryTermCheck:
    """Test cases for GlossaryTermCheck."""

    def test_term_check_passes_with_any_of(self):
        """Test that check passes when entity has one of the required terms."""
        check = GlossaryTermCheck()

        metadata = {
            "glossaryTerms": {
                "terms": [
                    {"urn": "urn:li:glossaryTerm:Classification.PII"},
                    {"urn": "urn:li:glossaryTerm:Classification.Public"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={
                "any_of": [
                    "urn:li:glossaryTerm:Classification.PII",
                    "urn:li:glossaryTerm:Classification.Financial",
                ]
            },
        )

        assert result.passed is True
        assert "urn:li:glossaryTerm:Classification.PII" in result.message

    def test_term_check_fails_without_required_terms(self):
        """Test that check fails when entity doesn't have required terms."""
        check = GlossaryTermCheck()

        metadata = {
            "glossaryTerms": {
                "terms": [
                    {"urn": "urn:li:glossaryTerm:Classification.Public"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={
                "any_of": [
                    "urn:li:glossaryTerm:Classification.PII",
                    "urn:li:glossaryTerm:Classification.Financial",
                ]
            },
        )

        assert result.passed is False
        assert "None of the required terms found" in result.message

    def test_term_check_passes_with_all_of(self):
        """Test that check passes when entity has all required terms."""
        check = GlossaryTermCheck()

        metadata = {
            "glossaryTerms": {
                "terms": [
                    {"urn": "urn:li:glossaryTerm:Classification.PII"},
                    {"urn": "urn:li:glossaryTerm:Classification.Financial"},
                    {"urn": "urn:li:glossaryTerm:Classification.Public"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={
                "all_of": [
                    "urn:li:glossaryTerm:Classification.PII",
                    "urn:li:glossaryTerm:Classification.Financial",
                ]
            },
        )

        assert result.passed is True
        assert "All required terms found" in result.message

    def test_term_check_fails_when_no_terms(self):
        """Test that check fails when entity has no glossary terms."""
        check = GlossaryTermCheck()

        metadata = {}

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"any_of": ["urn:li:glossaryTerm:Classification.PII"]},
        )

        assert result.passed is False
        assert "No glossary terms attached" in result.message


class TestTagCheck:
    """Test cases for TagCheck."""

    def test_tag_check_passes_with_any_of(self):
        """Test that check passes when entity has one of the required tags."""
        check = TagCheck()

        metadata = {
            "globalTags": {
                "tags": [
                    {"tag": "urn:li:tag:PII"},
                    {"tag": "urn:li:tag:Production"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={
                "any_of": [
                    "urn:li:tag:PII",
                    "urn:li:tag:Sensitive",
                ]
            },
        )

        assert result.passed is True
        assert "urn:li:tag:PII" in result.message

    def test_tag_check_fails_without_required_tags(self):
        """Test that check fails when entity doesn't have required tags."""
        check = TagCheck()

        metadata = {
            "globalTags": {
                "tags": [
                    {"tag": "urn:li:tag:Production"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={
                "any_of": [
                    "urn:li:tag:PII",
                    "urn:li:tag:Sensitive",
                ]
            },
        )

        assert result.passed is False
        assert "None of the required tags found" in result.message

    def test_tag_check_passes_with_all_of(self):
        """Test that check passes when entity has all required tags."""
        check = TagCheck()

        metadata = {
            "globalTags": {
                "tags": [
                    {"tag": "urn:li:tag:PII"},
                    {"tag": "urn:li:tag:GDPR"},
                    {"tag": "urn:li:tag:Production"},
                ]
            }
        }

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={
                "all_of": [
                    "urn:li:tag:PII",
                    "urn:li:tag:GDPR",
                ]
            },
        )

        assert result.passed is True
        assert "All required tags found" in result.message

    def test_tag_check_fails_when_no_tags(self):
        """Test that check fails when entity has no tags."""
        check = TagCheck()

        metadata = {}

        result = check.evaluate(
            entity_urn="urn:li:dataset:test",
            metadata=metadata,
            params={"any_of": ["urn:li:tag:PII"]},
        )

        assert result.passed is False
        assert "No tags attached" in result.message
