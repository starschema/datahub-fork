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

"""
Connector Registry for Data Quality Tests.

Provides centralized connection management for query-based data quality tests,
allowing tests to look up database connections by platform or dataset URN.
"""

import logging
from typing import Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for managing database connections used by query-based data quality tests.

    Stores connection strings by platform name and provides methods to retrieve
    SQLAlchemy engines for executing validation queries.

    Example configuration:
        connectors:
          mysql:
            connection_string: "mysql://user:pass@localhost:3306/mydb"
          postgres:
            connection_string: "postgresql://user:pass@localhost:5432/db"
          snowflake:
            connection_string: "snowflake://user:pass@account/db"
    """

    def __init__(self, connector_configs: Optional[Dict[str, Dict[str, str]]] = None):
        """
        Initialize the connector registry.

        Args:
            connector_configs: Dictionary mapping platform names to connection configs.
                             Each config must have a 'connection_string' key.
        """
        self.connector_configs = connector_configs or {}
        self._engines: Dict[str, Engine] = {}

    def register_connector(self, platform: str, connection_string: str) -> None:
        """
        Register a new connector for a platform.

        Args:
            platform: Platform name (e.g., 'mysql', 'postgres', 'snowflake')
            connection_string: SQLAlchemy connection string
        """
        self.connector_configs[platform] = {"connection_string": connection_string}
        # Clear cached engine if exists
        if platform in self._engines:
            del self._engines[platform]

    def get_connection_string(self, dataset_urn: str) -> Optional[str]:
        """
        Get connection string for a dataset based on its URN.

        Args:
            dataset_urn: Dataset URN (e.g., "urn:li:dataset:(urn:li:dataPlatform:mysql,db.table,PROD)")

        Returns:
            Connection string if found, None otherwise
        """
        platform = self._extract_platform_from_urn(dataset_urn)
        if not platform:
            logger.warning(f"Could not extract platform from URN: {dataset_urn}")
            return None

        connector_config = self.connector_configs.get(platform)
        if not connector_config:
            logger.debug(f"No connector config found for platform: {platform}")
            return None

        return connector_config.get("connection_string")

    def get_engine(self, dataset_urn: str, connection_string: Optional[str] = None) -> Optional[Engine]:
        """
        Get SQLAlchemy engine for a dataset.

        Args:
            dataset_urn: Dataset URN
            connection_string: Optional connection string to use directly.
                             If not provided, will look up by platform from URN.

        Returns:
            SQLAlchemy Engine if connection string found, None otherwise
        """
        # If connection_string provided explicitly, use it
        if connection_string:
            try:
                return create_engine(connection_string)
            except Exception as e:
                logger.error(f"Failed to create engine from connection string: {e}")
                return None

        # Otherwise, look up by platform
        platform = self._extract_platform_from_urn(dataset_urn)
        if not platform:
            return None

        # Check cache first
        if platform in self._engines:
            return self._engines[platform]

        # Create new engine
        conn_str = self.get_connection_string(dataset_urn)
        if not conn_str:
            return None

        try:
            engine = create_engine(conn_str)
            self._engines[platform] = engine
            return engine
        except Exception as e:
            logger.error(f"Failed to create engine for platform {platform}: {e}")
            return None

    def has_connector(self, dataset_urn: str) -> bool:
        """
        Check if a connector is registered for the dataset's platform.

        Args:
            dataset_urn: Dataset URN

        Returns:
            True if connector exists, False otherwise
        """
        return self.get_connection_string(dataset_urn) is not None

    def close_all(self) -> None:
        """Close all cached database connections."""
        for platform, engine in self._engines.items():
            try:
                engine.dispose()
                logger.debug(f"Closed engine for platform: {platform}")
            except Exception as e:
                logger.warning(f"Error closing engine for {platform}: {e}")
        self._engines.clear()

    @staticmethod
    def _extract_platform_from_urn(dataset_urn: str) -> Optional[str]:
        """
        Extract platform name from dataset URN.

        Args:
            dataset_urn: Dataset URN (e.g., "urn:li:dataset:(urn:li:dataPlatform:mysql,db.table,PROD)")

        Returns:
            Platform name (e.g., "mysql") or None if extraction fails
        """
        try:
            # URN format: urn:li:dataset:(urn:li:dataPlatform:PLATFORM,...)
            if "dataPlatform:" not in dataset_urn:
                return None

            platform_part = dataset_urn.split("dataPlatform:")[1]
            platform = platform_part.split(",")[0]
            return platform
        except (IndexError, AttributeError):
            return None

    def __enter__(self) -> "ConnectorRegistry":
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close all connections on exit."""
        self.close_all()
