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

ZERO DUPLICATION: Automatically queries DataHub's ingestion source registry
to reuse the same connection configurations used for metadata ingestion.
This eliminates credential duplication and ensures security.
"""

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

if TYPE_CHECKING:
    from datahub_actions.api.action_graph import AcrylDataHubGraph

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for managing database connections used by query-based data quality tests.

    ZERO DUPLICATION ARCHITECTURE:
    Instead of duplicating credentials, this registry queries DataHub's ingestion
    source registry to reuse the same connection configs used for metadata ingestion.

    Connection resolution priority:
    1. Explicit connector_configs (backward compatibility / overrides)
    2. DataHub ingestion sources (RECOMMENDED - zero duplication)
    3. Environment variables (fallback)

    Example configuration (optional, will auto-discover from DataHub):
        connectors:
          mysql:
            connection_string: "mysql://user:pass@localhost:3306/mydb"
          postgres:
            connection_string: "postgresql://user:pass@localhost:5432/db"
    """

    def __init__(
        self,
        connector_configs: Optional[Dict[str, Dict[str, str]]] = None,
        graph: Optional["AcrylDataHubGraph"] = None,
    ):
        """
        Initialize the connector registry.

        Args:
            connector_configs: Optional dictionary mapping platform names to connection configs.
                             Each config must have a 'connection_string' key.
                             If omitted, will query DataHub for ingestion sources.
            graph: AcrylDataHubGraph client for querying DataHub's ingestion source registry.
                  Required for zero-duplication credential sharing.
        """
        self.connector_configs = connector_configs or {}
        self.graph = graph
        self._engines: Dict[str, Engine] = {}
        self._ingestion_source_cache: Optional[Dict[str, Any]] = None

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

    def _load_ingestion_sources(self) -> Dict[str, Any]:
        """
        Query DataHub for all configured ingestion sources.

        Returns mapping of platform -> connection config from ingestion sources.
        Uses caching to avoid repeated GraphQL queries.

        SECURITY: Credentials are retrieved from DataHub's encrypted storage.
        """
        if self._ingestion_source_cache is not None:
            return self._ingestion_source_cache

        if not self.graph:
            logger.debug(
                "No graph client provided to ConnectorRegistry. "
                "Cannot query ingestion sources for automatic credential sharing. "
                "Consider providing graph parameter for zero-duplication architecture."
            )
            return {}

        try:
            import json

            logger.info("Querying DataHub for ingestion source configurations...")
            sources = self.graph.query_ingestion_sources()
            source_map = {}

            for source in sources:
                source_type = source.get("type", "").lower()
                source_name = source.get("name", "")
                recipe_json = source.get("config", {}).get("recipe")

                if not source_type:
                    continue

                logger.debug(f"Found ingestion source: {source_name} (type: {source_type})")

                if not recipe_json:
                    logger.debug(
                        f"No recipe found for source '{source_name}'. "
                        f"This ingestion source may not have a complete configuration."
                    )
                    continue

                try:
                    recipe = json.loads(recipe_json)
                    source_config = recipe.get("source", {}).get("config", {})

                    if source_config:
                        source_map[source_type] = source_config
                        logger.debug(
                            f"Loaded config for platform '{source_type}' from source '{source_name}'"
                        )
                    else:
                        logger.debug(
                            f"Recipe for source '{source_name}' does not contain source.config"
                        )

                except json.JSONDecodeError as je:
                    logger.warning(
                        f"Failed to parse recipe JSON for source '{source_name}': {je}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Error extracting config from source '{source_name}': {e}"
                    )

            self._ingestion_source_cache = source_map
            if source_map:
                logger.info(
                    f"Loaded connection configs for platforms: {', '.join(source_map.keys())}"
                )
            else:
                logger.info(
                    "No ingestion source configs loaded. Query-based tests will use "
                    "explicit connector configs or environment variables."
                )

            return source_map

        except Exception as e:
            logger.warning(f"Failed to load ingestion sources from DataHub: {e}")
            return {}

    def _build_connection_string_from_ingestion_config(
        self, platform: str, config: Dict[str, Any]
    ) -> Optional[str]:
        """
        Build SQLAlchemy connection string from DataHub ingestion source config.

        Reuses DataHub's own config classes to build connection strings,
        ensuring compatibility and proper credential handling.

        Supports: Snowflake, Postgres, MySQL, BigQuery, Redshift, Oracle, etc.

        Args:
            platform: Platform name (e.g., "snowflake", "postgres")
            config: Ingestion source configuration dictionary

        Returns:
            SQLAlchemy connection string or None if platform not supported
        """
        try:
            # Resolve any secret references (${SECRET_NAME}) in the config
            resolved_config = self._resolve_secrets(config)

            if platform == "snowflake":
                from datahub.ingestion.source.snowflake.snowflake_config import (
                    SnowflakeV2Config,
                )

                sf_config = SnowflakeV2Config.parse_obj(resolved_config)
                connection_string = sf_config.get_sql_alchemy_url()
                logger.info("Built Snowflake connection string from ingestion config")
                return connection_string

            elif platform in ("postgres", "postgresql"):
                from datahub.ingestion.source.sql.postgres import PostgresConfig

                pg_config = PostgresConfig.parse_obj(resolved_config)
                connection_string = pg_config.get_sql_alchemy_url()
                logger.info("Built PostgreSQL connection string from ingestion config")
                return connection_string

            elif platform == "mysql":
                from datahub.ingestion.source.sql.mysql import MySQLConfig

                mysql_config = MySQLConfig.parse_obj(resolved_config)
                connection_string = mysql_config.get_sql_alchemy_url()
                logger.info("Built MySQL connection string from ingestion config")
                return connection_string

            # Add more platforms as needed
            else:
                logger.warning(
                    f"Platform '{platform}' is not yet supported for automatic "
                    f"connection string building from ingestion configs. "
                    f"Please configure explicitly in connectors section."
                )
                return None

        except Exception as e:
            logger.error(
                f"Failed to build connection string for {platform} from ingestion config: {e}"
            )
            return None

    def _resolve_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve ${SECRET_NAME} references in config by querying DataHub's secret store.

        DataHub ingestion recipes may contain secret references like:
            password: "${SNOWFLAKE_PASSWORD}"

        This method:
        1. Finds all ${SECRET_NAME} references in the config
        2. Fetches actual values from DataHub's encrypted secret storage
        3. Replaces references with actual values

        Args:
            config: Configuration dictionary that may contain secret references

        Returns:
            Configuration with all secrets resolved

        SECURITY: Secret values are never logged.
        """
        try:
            from datahub.configuration.config_loader import EnvResolver
            from datahub.secret.datahub_secret_store import (
                DataHubSecretStore,
                DataHubSecretStoreConfig,
            )

            # Find all secret references in the config
            secret_refs = EnvResolver.list_referenced_variables(config)

            if not secret_refs:
                logger.debug("No secret references found in config")
                return config

            logger.debug(f"Found {len(secret_refs)} secret reference(s) in config")

            # Fetch actual secret values from DataHub
            if not self.graph:
                logger.warning(
                    "Cannot resolve secrets without graph client. "
                    "Secrets will not be resolved."
                )
                return config

            secret_store = DataHubSecretStore(
                DataHubSecretStoreConfig(graph_client=self.graph.graph)
            )
            secret_values = secret_store.get_secret_values(list(secret_refs))

            # Check for any missing secrets
            missing_secrets = [ref for ref in secret_refs if ref not in secret_values]
            if missing_secrets:
                logger.warning(
                    f"Could not resolve secrets: {', '.join(missing_secrets)}. "
                    f"These secrets may not be configured in DataHub."
                )

            # Resolve all ${SECRET_NAME} references in the config
            resolver = EnvResolver(environ=secret_values)
            resolved_config = resolver.resolve(config)

            logger.debug("Successfully resolved all secret references")
            return resolved_config

        except ImportError as ie:
            logger.warning(
                f"Required modules not available for secret resolution: {ie}. "
                f"Secrets will not be resolved."
            )
            return config
        except Exception as e:
            logger.warning(f"Failed to resolve secrets: {e}. Continuing without resolution.")
            return config

    def get_connection_string(self, dataset_urn: str) -> Optional[str]:
        """
        Get connection string for a dataset based on its URN.

        Resolution priority:
        1. Explicit connector_configs (backward compatibility / overrides)
        2. DataHub ingestion sources (RECOMMENDED - zero duplication)
        3. Environment variables (fallback)

        Args:
            dataset_urn: Dataset URN (e.g., "urn:li:dataset:(urn:li:dataPlatform:mysql,db.table,PROD)")

        Returns:
            Connection string if found, None otherwise

        SECURITY: Never logs connection strings containing credentials.
        """
        platform = self._extract_platform_from_urn(dataset_urn)
        if not platform:
            logger.warning(f"Could not extract platform from URN: {dataset_urn}")
            return None

        # Priority 1: Explicit connector configs (backward compatibility)
        connector_config = self.connector_configs.get(platform)
        if connector_config and connector_config.get("connection_string"):
            logger.debug(f"Using explicit connector config for platform: {platform}")
            return connector_config.get("connection_string")

        # Priority 2: DataHub ingestion sources (RECOMMENDED)
        ingestion_sources = self._load_ingestion_sources()
        if platform in ingestion_sources:
            logger.debug(
                f"Using DataHub ingestion source config for platform: {platform}"
            )
            return self._build_connection_string_from_ingestion_config(
                platform, ingestion_sources[platform]
            )

        # Priority 3: Environment variable fallback
        env_var_name = f"{platform.upper()}_DATAHUB_CONNECTION_STRING"
        env_connection_string = os.getenv(env_var_name)
        if env_connection_string:
            logger.debug(
                f"Using environment variable {env_var_name} for platform: {platform}"
            )
            return env_connection_string

        logger.debug(
            f"No connection config found for platform '{platform}'. "
            f"Query-based tests will be skipped for datasets from this platform. "
            f"To enable: configure an ingestion source for {platform} in DataHub UI, "
            f"or add to connectors section in data-quality-action-config.yaml, "
            f"or set environment variable {env_var_name}."
        )
        return None

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
