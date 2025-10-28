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

import logging

from datahub.metadata.schema_classes import (
    EntityChangeEventClass as EntityChangeEvent,
    MetadataChangeLogClass as MetadataChangeLog,
)
from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.action.data_quality.config import DataQualityConfig
from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry
from datahub_actions.plugin.action.data_quality.test_executor import TestExecutor

logger = logging.getLogger(__name__)


class DataQualityAction(Action):
    """
    DataHub Action that executes data quality tests on dataset changes.

    Monitors dataset update events and runs configured quality checks using
    both profile-based (cached) and query-based (fresh) validation approaches.
    """

    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> "Action":
        action_config = DataQualityConfig.model_validate(config_dict or {})
        logger.info(
            f"Data Quality Action configured with {len(action_config.tests)} tests"
        )
        return cls(action_config, ctx)

    def __init__(self, config: DataQualityConfig, ctx: PipelineContext):
        self.config = config
        self.ctx = ctx

        if not ctx.graph:
            raise ValueError("DataHub graph client is required for Data Quality Action")

        # Initialize connector registry with graph for zero-duplication credential sharing
        connector_configs_dict = {
            platform: {"connection_string": conn_config.connection_string}
            for platform, conn_config in config.connectors.items()
        }
        self.connector_registry = ConnectorRegistry(
            connector_configs_dict,
            graph=ctx.graph,  # Pass graph to enable automatic ingestion config reuse
        )

        self.executor = TestExecutor(
            graph=ctx.graph,
            test_configs=config.tests,
            connector_registry=self.connector_registry,
        )

    def act(self, event: EventEnvelope) -> None:
        """
        Process incoming DataHub events and execute quality tests.

        Listens for MetadataChangeLogEvent_v1 (with datasetProfile aspect)
        or EntityChangeEvent_v1 on datasets and triggers configured tests,
        emitting assertion results back to DataHub.
        """
        if not self.config.enabled:
            logger.debug("Data Quality Action is disabled, skipping event")
            return

        try:
            dataset_urn = None

            # Handle MetadataChangeLog events (primary path for profiling)
            if event.event_type == "MetadataChangeLogEvent_v1":
                assert isinstance(event.event, MetadataChangeLog)
                mcl: MetadataChangeLog = event.event

                # Only process dataset entities with datasetProfile aspect
                if mcl.entityType != "dataset":
                    logger.debug(f"Skipping non-dataset MCL: {mcl.entityType}")
                    return

                if mcl.aspectName != "datasetProfile":
                    logger.debug(f"Skipping non-profile aspect: {mcl.aspectName}")
                    return

                dataset_urn = mcl.entityUrn
                logger.info(
                    f"Processing dataset profile update for: {dataset_urn}"
                )

            # Handle EntityChangeEvent (legacy/alternative path)
            elif event.event_type == "EntityChangeEvent_v1":
                assert isinstance(event.event, EntityChangeEvent)
                entity_change: EntityChangeEvent = event.event

                # Only process dataset entity changes
                if entity_change.entityType != "dataset":
                    logger.debug(
                        f"Skipping non-dataset entity: {entity_change.entityType}"
                    )
                    return

                dataset_urn = entity_change.entityUrn
                logger.info(
                    f"Processing dataset change event for: {dataset_urn}"
                )

            else:
                logger.debug(
                    f"Skipping unsupported event type: {event.event_type}"
                )
                return

            # Execute tests for this dataset
            if dataset_urn:
                assertion_mcps = self.executor.execute_tests_for_dataset(
                    dataset_urn
                )

                # Emit assertions to DataHub
                if self.ctx.graph and assertion_mcps:
                    for mcp in assertion_mcps:
                        try:
                            # Use underlying graph.emit() instead of emit_mcp()
                            # AcrylDataHubGraph wraps DataHubGraph and uses emit()
                            self.ctx.graph.graph.emit(mcp)
                            logger.debug(f"Emitted assertion: {mcp.entityUrn}")
                        except Exception as e:
                            logger.error(
                                f"Failed to emit assertion {mcp.entityUrn}: {e}"
                            )

                    logger.info(
                        f"Successfully emitted {len(assertion_mcps)} assertions for {dataset_urn}"
                    )
                else:
                    logger.debug(f"No assertions to emit for {dataset_urn}")

        except Exception as e:
            logger.error(f"Failed to process event: {e}", exc_info=True)

    def close(self) -> None:
        """Cleanup resources."""
        logger.info("Data Quality Action closing")
        self.connector_registry.close_all()
