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

from typing import Dict, List, Optional

from pydantic import Field

from datahub.configuration.common import ConfigModel


class ConnectorConfig(ConfigModel):
    """Configuration for a database connector."""

    connection_string: str = Field(
        description="SQLAlchemy connection string for the database"
    )


class TestConfig(ConfigModel):
    """Configuration for a single data quality test."""

    name: str = Field(description="Unique name for this test")
    type: str = Field(description="Test type (e.g., 'table_row_count', 'column_value_range')")
    dataset_pattern: str = Field(
        description="Dataset URN pattern to match (supports wildcards)"
    )
    column: Optional[str] = Field(
        default=None,
        description="Column name for column-level tests (required for column tests)",
    )
    params: Dict[str, str] = Field(
        default_factory=dict,
        description="Test-specific parameters (e.g., min_rows, max_rows, min_value, max_value)",
    )


class DataQualityConfig(ConfigModel):
    """Configuration for the Data Quality Action."""

    tests: List[TestConfig] = Field(
        default_factory=list,
        description="List of data quality tests to execute on dataset changes",
    )
    enabled: bool = Field(
        default=True,
        description="Whether the action is enabled",
    )
    connectors: Dict[str, ConnectorConfig] = Field(
        default_factory=dict,
        description="Database connectors by platform name (e.g., mysql, postgres). "
                   "Used by query-based tests to look up connections by dataset platform.",
    )
