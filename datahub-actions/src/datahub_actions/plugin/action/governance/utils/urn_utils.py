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

from typing import Optional


def extract_entity_type(urn: str) -> Optional[str]:
    """
    Extract entity type from a DataHub URN.

    DataHub URNs follow the format: urn:li:<entity_type>:<key>

    Examples:
        urn:li:dataset:(urn:li:dataPlatform:snowflake,db.schema.table,PROD) -> dataset
        urn:li:dashboard:(looker,dashboard_id) -> dashboard
        urn:li:corpuser:jdoe -> corpuser

    Args:
        urn: DataHub URN string

    Returns:
        Entity type string, or None if URN format is invalid
    """
    if not urn or not urn.startswith("urn:li:"):
        return None

    parts = urn.split(":")
    if len(parts) < 3:
        return None

    return parts[2]


def extract_platform_from_dataset_urn(urn: str) -> Optional[str]:
    """
    Extract platform name from a dataset URN.

    Dataset URN format: urn:li:dataset:(urn:li:dataPlatform:<platform>,<dataset_name>,<env>)

    Example:
        urn:li:dataset:(urn:li:dataPlatform:snowflake,db.schema.table,PROD) -> snowflake

    Args:
        urn: Dataset URN string

    Returns:
        Platform name, or None if not a dataset URN or format is invalid
    """
    if not urn or ":dataset:(" not in urn:
        return None

    try:
        # Extract the key part: (urn:li:dataPlatform:snowflake,db.schema.table,PROD)
        key_start = urn.index(":dataset:(") + len(":dataset:(")
        key_end = urn.rindex(")")
        key = urn[key_start:key_end]

        # Split by comma to get platform URN
        parts = key.split(",")
        if len(parts) < 1:
            return None

        platform_urn = parts[0]
        # Extract platform from: urn:li:dataPlatform:snowflake
        if "urn:li:dataPlatform:" in platform_urn:
            return platform_urn.split("urn:li:dataPlatform:")[1]

        return None
    except (ValueError, IndexError):
        return None


def make_test_urn(rule_name: str, check_type: str) -> str:
    """
    Generate a Test entity URN for governance checks.

    Format: urn:li:test:governance.<rule_name>.<check_type>

    Args:
        rule_name: Name of the governance rule
        check_type: Type of check (e.g., requires_owner, requires_description)

    Returns:
        Test URN string
    """
    # Sanitize names to ensure valid URN format
    safe_rule_name = rule_name.replace(" ", "_").replace(":", "_")
    safe_check_type = check_type.replace(" ", "_").replace(":", "_")

    return f"urn:li:test:governance.{safe_rule_name}.{safe_check_type}"


def make_incident_id(entity_urn: str, rule_name: str, check_type: str) -> str:
    """
    Generate a unique incident ID for governance violations.

    This ID is used to deduplicate incidents and track specific violations.

    Format: governance_<rule_name>_<check_type>_<entity_urn_hash>

    Args:
        entity_urn: URN of the entity with the violation
        rule_name: Name of the governance rule
        check_type: Type of check that failed

    Returns:
        Incident ID string
    """
    safe_rule_name = rule_name.replace(" ", "_").replace(":", "_")
    safe_check_type = check_type.replace(" ", "_").replace(":", "_")

    # Use hash of entity URN to keep ID reasonable length
    urn_hash = str(abs(hash(entity_urn)))[:12]

    return f"governance_{safe_rule_name}_{safe_check_type}_{urn_hash}"
