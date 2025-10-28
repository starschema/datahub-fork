"""Client for querying DataHub ingestion sources via GraphQL."""

import json
import logging
from typing import Any, Dict, List, Optional

from datahub.ingestion.graph.client import DataHubGraph

logger = logging.getLogger(__name__)


def _resolve_secrets_in_config(config: Dict[str, Any], graph: DataHubGraph) -> Dict[str, Any]:
    """
    Resolve secret references in config (e.g., ${SECRET_NAME}).

    Args:
        config: Configuration dict that may contain secret references
        graph: DataHub graph client

    Returns:
        Config with secrets resolved
    """
    try:
        from datahub.configuration.common import ConfigModel
        from datahub.secret.datahub_secret_store import (
            DataHubSecretStore,
            DataHubSecretStoreConfig,
        )
        from datahub.configuration.config_loader import EnvResolver

        # Find all secret references in the config
        secret_refs = EnvResolver.list_referenced_variables(config)

        if not secret_refs:
            logger.debug("No secret references found in config")
            return config

        logger.info(f"Found {len(secret_refs)} secret reference(s) in config: {secret_refs}")

        # Fetch actual secret values from DataHub
        secret_store = DataHubSecretStore(
            DataHubSecretStoreConfig(graph_client=graph)
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

        logger.info("Successfully resolved all secret references")
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


class IngestionSourceClient:
    """Client for querying ingestion sources from DataHub GMS."""

    def __init__(self, graph: DataHubGraph):
        self.graph = graph

    def query_ingestion_sources(self) -> List[Dict[str, Any]]:
        """
        Query DataHub for all configured ingestion sources using GraphQL.

        Returns:
            List of ingestion sources with urn, type, name, and config (recipe)
        """
        sources = []
        start, count = 0, 10

        while True:
            query_payload = {
                "query": """
query listIngestionSources($input: ListIngestionSourcesInput!) {
  listIngestionSources(input: $input) {
    start
    count
    total
    ingestionSources {
      urn
      type
      name
      config {
        recipe
      }
    }
  }
}
""",
                "variables": {"input": {"start": start, "count": count}},
            }

            try:
                # Use the GMS server URL from graph config
                # Note: Open-source DataHub uses /api/graphql, not /api/v2/graphql
                url = f"{self.graph._gms_server}/api/graphql"
                headers = {
                    "Content-Type": "application/json",
                    "X-DataHub-Actor": "urn:li:corpuser:datahub",
                }

                logger.debug(f"Querying ingestion sources: start={start}, count={count}")
                response = self.graph._session.post(url, json=query_payload, headers=headers)

                if response.status_code != 200:
                    logger.error(
                        f"GraphQL query failed with status {response.status_code}: {response.text}"
                    )
                    break

                result = response.json()
                data = result.get("data", {})

                if not data:
                    logger.warning(f"Empty GraphQL response: {result}")
                    break

                list_ingestion_sources = data.get("listIngestionSources")
                if list_ingestion_sources is None:
                    logger.warning(
                        f"listIngestionSources field not found in response: {data}"
                    )
                    break

                sources.extend(list_ingestion_sources.get("ingestionSources", []))

                cur_total = list_ingestion_sources.get("total", 0)
                if len(sources) >= cur_total or cur_total <= start + count:
                    break

                start += count

            except Exception as e:
                logger.error(f"Failed to query ingestion sources: {e}", exc_info=True)
                break

        logger.info(f"Found {len(sources)} ingestion sources in DataHub")
        return sources

    def get_snowflake_connection_config(
        self, dataset_urn: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the Snowflake connection configuration for a specific dataset.

        This method queries DataHub's ingestion sources to find Snowflake configurations
        and returns the connection config for the source that ingested this dataset.

        Args:
            dataset_urn: URN of the dataset (e.g., urn:li:dataset:(urn:li:dataPlatform:snowflake,...))

        Returns:
            Snowflake connection config dict, or None if not found
        """
        # Get all ingestion sources
        sources = self.query_ingestion_sources()

        # Filter for Snowflake sources
        snowflake_sources = [s for s in sources if s.get("type", "").lower() == "snowflake"]

        if not snowflake_sources:
            logger.warning("No Snowflake ingestion sources found in DataHub")
            return None

        logger.info(f"Found {len(snowflake_sources)} Snowflake ingestion sources")

        # For now, use the first Snowflake source
        # TODO: Implement logic to match dataset to specific source based on URN pattern
        if snowflake_sources:
            source = snowflake_sources[0]
            source_name = source.get("name", "unknown")
            recipe_json = source.get("config", {}).get("recipe")

            if not recipe_json:
                logger.warning(f"No recipe found for Snowflake source '{source_name}'")
                return None

            try:
                recipe = json.loads(recipe_json)
                source_config = recipe.get("source", {}).get("config", {})

                if source_config:
                    logger.info(
                        f"Using Snowflake connection from ingestion source '{source_name}'"
                    )
                    # Resolve secret references (e.g., ${SNOWFLAKE_PASSWORD})
                    resolved_config = _resolve_secrets_in_config(source_config, self.graph)

                    # Log resolved config (masking password)
                    config_summary = {k: '***' if k == 'password' else v for k, v in resolved_config.items()}
                    logger.info(f"Resolved Snowflake config: {config_summary}")

                    return resolved_config
                else:
                    logger.warning(f"No source.config found in recipe for '{source_name}'")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse recipe JSON for '{source_name}': {e}")

        return None
