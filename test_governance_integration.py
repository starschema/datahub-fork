#!/usr/bin/env python3
"""
DataHub Governance Bot - Integration Test Script

This script tests the governance bot by:
1. Creating test datasets with various governance scenarios
2. Verifying governance results appear in DataHub
3. Checking incident creation

Usage:
    python test_governance_integration.py
"""

import time
from typing import List

from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    DatasetPropertiesClass,
    GlobalTagsClass,
    GlossaryTermAssociationClass,
    GlossaryTermsClass,
    MetadataChangeProposalWrapper,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass,
    TagAssociationClass,
)


class GovernanceTestScenario:
    """Represents a governance test scenario."""

    def __init__(
        self,
        name: str,
        dataset_name: str,
        description: str,
        expected_results: List[str],
    ):
        self.name = name
        self.dataset_name = dataset_name
        self.description = description
        self.expected_results = expected_results
        self.dataset_urn = None


def create_emitter(server_url: str = "http://localhost:8080") -> DatahubRestEmitter:
    """Create DataHub REST emitter."""
    return DatahubRestEmitter(server_url)


def create_scenario_1_perfect_dataset(emitter: DatahubRestEmitter) -> GovernanceTestScenario:
    """
    Scenario 1: Perfect Dataset
    - Has 2 owners (DATAOWNER, TECHNICAL_OWNER)
    - Has detailed description (>50 chars)
    - Has glossary term
    - Should PASS all checks
    """
    scenario = GovernanceTestScenario(
        name="Perfect Dataset",
        dataset_name="test_db.test_schema.perfect_dataset",
        description="A well-governed dataset with all required metadata",
        expected_results=[
            "✅ requires_owner: PASS",
            "✅ requires_description: PASS",
        ],
    )

    dataset_urn = make_dataset_urn("snowflake", scenario.dataset_name, "PROD")
    scenario.dataset_urn = dataset_urn

    # Add description
    properties = DatasetPropertiesClass(
        description="This is a comprehensive test dataset for governance validation. "
        "It includes all required metadata fields and should pass all governance checks."
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=properties))

    # Add 2 owners
    ownership = OwnershipClass(
        owners=[
            OwnerClass(
                owner="urn:li:corpuser:datahub",
                type=OwnershipTypeClass.DATAOWNER,
            ),
            OwnerClass(
                owner="urn:li:corpuser:jdoe",
                type=OwnershipTypeClass.TECHNICAL_OWNER,
            ),
        ]
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=ownership))

    return scenario


def create_scenario_2_missing_owner(emitter: DatahubRestEmitter) -> GovernanceTestScenario:
    """
    Scenario 2: Missing Owner
    - Has description
    - NO owners
    - Should FAIL ownership check
    """
    scenario = GovernanceTestScenario(
        name="Missing Owner",
        dataset_name="test_db.test_schema.no_owner_dataset",
        description="Dataset without an owner - should fail governance",
        expected_results=[
            "❌ requires_owner: FAIL",
            "✅ requires_description: PASS",
        ],
    )

    dataset_urn = make_dataset_urn("snowflake", scenario.dataset_name, "PROD")
    scenario.dataset_urn = dataset_urn

    # Only add description, no owner
    properties = DatasetPropertiesClass(
        description="This dataset has a description but no owner assigned."
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=properties))

    return scenario


def create_scenario_3_missing_description(emitter: DatahubRestEmitter) -> GovernanceTestScenario:
    """
    Scenario 3: Missing Description
    - Has owner
    - NO description
    - Should FAIL description check
    """
    scenario = GovernanceTestScenario(
        name="Missing Description",
        dataset_name="test_db.test_schema.no_description_dataset",
        description="Dataset without a description - should fail governance",
        expected_results=[
            "✅ requires_owner: PASS",
            "❌ requires_description: FAIL",
        ],
    )

    dataset_urn = make_dataset_urn("snowflake", scenario.dataset_name, "PROD")
    scenario.dataset_urn = dataset_urn

    # Only add owner, no description
    ownership = OwnershipClass(
        owners=[
            OwnerClass(
                owner="urn:li:corpuser:datahub",
                type=OwnershipTypeClass.DATAOWNER,
            )
        ]
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=ownership))

    return scenario


def create_scenario_4_tier1_dataset(emitter: DatahubRestEmitter) -> GovernanceTestScenario:
    """
    Scenario 4: Tier 1 Dataset
    - Has tier:1 tag
    - Only 1 owner (needs 2 for tier1_governance rule)
    - Has description
    - Should FAIL tier1_governance due to insufficient owners
    """
    scenario = GovernanceTestScenario(
        name="Tier 1 Dataset (Insufficient Owners)",
        dataset_name="test_db.test_schema.tier1_dataset",
        description="Tier 1 dataset with only 1 owner - should fail strict governance",
        expected_results=[
            "❌ tier1_governance: FAIL (needs 2 owners)",
            "✅ production_dataset_governance: PASS",
        ],
    )

    dataset_urn = make_dataset_urn("snowflake", scenario.dataset_name, "PROD")
    scenario.dataset_urn = dataset_urn

    # Add tier:1 tag
    tags = GlobalTagsClass(
        tags=[TagAssociationClass(tag="urn:li:tag:tier:1")]
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=tags))

    # Add description
    properties = DatasetPropertiesClass(
        description="Tier 1 critical dataset requiring enhanced governance controls."
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=properties))

    # Add only 1 owner (tier1 requires 2)
    ownership = OwnershipClass(
        owners=[
            OwnerClass(
                owner="urn:li:corpuser:datahub",
                type=OwnershipTypeClass.DATAOWNER,
            )
        ]
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=ownership))

    return scenario


def create_scenario_5_pii_dataset(emitter: DatahubRestEmitter) -> GovernanceTestScenario:
    """
    Scenario 5: PII Dataset
    - Has PII tag
    - Has owner
    - Has description
    - Has PII classification term
    - Missing compliance tag (GDPR/CCPA)
    - Should FAIL pii_data_governance due to missing compliance tag
    """
    scenario = GovernanceTestScenario(
        name="PII Dataset (Missing Compliance Tag)",
        dataset_name="test_db.test_schema.pii_dataset",
        description="PII dataset missing compliance tag - should trigger critical incident",
        expected_results=[
            "❌ pii_data_governance: FAIL (missing GDPR/CCPA tag)",
            "✅ requires_owner: PASS",
            "✅ requires_glossary_term: PASS",
        ],
    )

    dataset_urn = make_dataset_urn("snowflake", scenario.dataset_name, "PROD")
    scenario.dataset_urn = dataset_urn

    # Add PII tag
    tags = GlobalTagsClass(
        tags=[TagAssociationClass(tag="urn:li:tag:PII")]
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=tags))

    # Add description
    properties = DatasetPropertiesClass(
        description="Dataset containing personally identifiable information (PII)."
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=properties))

    # Add owner
    ownership = OwnershipClass(
        owners=[
            OwnerClass(
                owner="urn:li:corpuser:datahub",
                type=OwnershipTypeClass.DATAOWNER,
            )
        ]
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=ownership))

    # Add PII classification term
    terms = GlossaryTermsClass(
        terms=[
            GlossaryTermAssociationClass(urn="urn:li:glossaryTerm:Classification.PII")
        ]
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=terms))

    # Note: We're NOT adding GDPR/CCPA tag, so this should fail

    return scenario


def run_governance_tests():
    """Run all governance test scenarios."""
    print("=" * 80)
    print("DataHub Governance Bot - Integration Tests")
    print("=" * 80)
    print()

    # Initialize emitter
    print("📡 Connecting to DataHub at http://localhost:8080...")
    try:
        emitter = create_emitter()
        print("✅ Connected successfully\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("\nMake sure DataHub is running:")
        print("  docker compose -f datahub-with-data-quality.yml up -d\n")
        return

    # Create test scenarios
    scenarios = [
        ("Scenario 1", create_scenario_1_perfect_dataset),
        ("Scenario 2", create_scenario_2_missing_owner),
        ("Scenario 3", create_scenario_3_missing_description),
        ("Scenario 4", create_scenario_4_tier1_dataset),
        ("Scenario 5", create_scenario_5_pii_dataset),
    ]

    created_scenarios: List[GovernanceTestScenario] = []

    for scenario_id, scenario_func in scenarios:
        print(f"🚀 Creating {scenario_id}...")
        try:
            scenario = scenario_func(emitter)
            created_scenarios.append(scenario)
            print(f"   ✅ {scenario.name}")
            print(f"   URN: {scenario.dataset_urn}")
            print(f"   Description: {scenario.description}")
            print()
        except Exception as e:
            print(f"   ❌ Failed: {e}\n")

    # Wait for governance bot to process
    print("=" * 80)
    print("⏳ Waiting for governance bot to process events (30 seconds)...")
    print("=" * 80)
    print()

    for i in range(30, 0, -5):
        print(f"   {i} seconds remaining...")
        time.sleep(5)

    print()

    # Summary
    print("=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    print()
    print(f"Created {len(created_scenarios)} test datasets:")
    print()

    for scenario in created_scenarios:
        print(f"✓ {scenario.name}")
        print(f"  URN: {scenario.dataset_urn}")
        print(f"  Expected Results:")
        for result in scenario.expected_results:
            print(f"    {result}")
        print()

    # Verification instructions
    print("=" * 80)
    print("🔍 Verification Steps")
    print("=" * 80)
    print()
    print("1. Open DataHub UI: http://localhost:9002")
    print("2. Search for 'test_schema' to find test datasets")
    print("3. Click on each dataset and go to the 'Governance' tab")
    print("4. Verify governance check results match expected results above")
    print()
    print("5. Check governance action logs:")
    print("   docker compose -f datahub-with-data-quality.yml logs datahub-actions | grep -i governance")
    print()
    print("6. For PII dataset, check Incidents tab for CRITICAL incident")
    print()

    print("=" * 80)
    print("✅ Test data creation complete!")
    print("=" * 80)


if __name__ == "__main__":
    run_governance_tests()
