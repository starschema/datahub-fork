import json
import logging
from typing import Optional, Tuple, cast

from pydantic import BaseModel

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    ChangeTypeClass,
    DatasetPropertiesClass,
    MetadataChangeLogClass,
    StatusClass,
)
from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.event.event_registry import METADATA_CHANGE_LOG_EVENT_V1_TYPE
from datahub_actions.pipeline.pipeline_context import PipelineContext

logger = logging.getLogger(__name__)


class IngestionSourceMapperConfig(BaseModel):
    enabled: bool = True
    property_key: str = "datahub.ingestion.sourceUrn"


class IngestionSourceMapperAction(Action):
    """
    Maintains a durable {dataset -> ingestion source URN} mapping on DatasetProperties.customProperties.

    Create/Update: On dataset writes, resolves the pipelineName (ingestion source URN) from
    system metadata and upserts customProperties[property_key] = sourceUrn.

    Delete: On dataset removal (Status.removed=true or DELETE change), removes the custom property.
    """

    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> "Action":
        cfg = IngestionSourceMapperConfig.model_validate(config_dict or {})
        return cls(cfg, ctx)

    def __init__(self, config: IngestionSourceMapperConfig, ctx: PipelineContext) -> None:
        self.config = config
        self.ctx = ctx
        logger.info(
            "IngestionSourceMapperAction initialized (enabled=%s, property_key=%s)",
            self.config.enabled,
            self.config.property_key,
        )

    # ---- Helpers ----

    def _resolve_source_urn_from_system_metadata(self, dataset_urn: str) -> Optional[str]:
        """Reads datasetProperties with system metadata and returns pipelineName if present."""
        try:
            if not self.ctx.graph:
                return None
            graph = self.ctx.graph.graph
            entities = graph.get_entities(
                entity_name="dataset",
                urns=[dataset_urn],
                aspects=["datasetProperties"],
                with_system_metadata=True,
            )
            entry = entities.get(dataset_urn)
            if not entry:
                return None
            _, sysmeta = entry.get("datasetProperties", (None, None))
            if not sysmeta:
                return None
            # Prefer properties map if present
            props = getattr(sysmeta, "properties", None)
            if isinstance(props, dict) and props.get("pipelineName"):
                return cast(str, props.get("pipelineName"))
            # Fall back to direct attribute if available in current model
            return cast(Optional[str], getattr(sysmeta, "pipelineName", None))
        except Exception as e:
            logger.debug("Failed to fetch system metadata for %s: %s", dataset_urn, e)
            return None

    def _read_current_properties(self, dataset_urn: str) -> DatasetPropertiesClass:
        if not self.ctx.graph:
            return DatasetPropertiesClass(customProperties={})
        graph = self.ctx.graph.graph
        bag = graph.get_entity_semityped(dataset_urn, aspects=["datasetProperties"])
        dp = cast(DatasetPropertiesClass, bag.get("datasetProperties")) if bag else None
        if dp is None:
            return DatasetPropertiesClass(customProperties={})
        # Ensure dicts exist
        if dp.customProperties is None:
            dp.customProperties = {}
        return dp

    def _upsert_property(self, dataset_urn: str, source_urn: str) -> None:
        dp = self._read_current_properties(dataset_urn)
        if dp.customProperties is None:
            dp.customProperties = {}
        existing = dp.customProperties.get(self.config.property_key)
        if existing == source_urn:
            logger.debug(
                "Property already set for  => ; skipping upsert", dataset_urn, source_urn
            )
            return
        dp.customProperties[self.config.property_key] = source_urn
        mcp = MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=dp)
        self.ctx.graph.graph.emit(mcp)
        logger.info(
            "Upserted mapping %s -> %s on %s",
            self.config.property_key,
            source_urn,
            dataset_urn,
        )

    def _remove_property(self, dataset_urn: str) -> None:
        dp = self._read_current_properties(dataset_urn)
        if not dp.customProperties or self.config.property_key not in dp.customProperties:
            return
        dp.customProperties.pop(self.config.property_key, None)
        mcp = MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=dp)
        self.ctx.graph.graph.emit(mcp)
        logger.info(
            "Removed mapping key %s from %s", self.config.property_key, dataset_urn
        )

    # ---- Action interface ----

    def act(self, event: EventEnvelope) -> None:
        if not self.config.enabled:
            return
        if event.event_type is not METADATA_CHANGE_LOG_EVENT_V1_TYPE:
            return

        orig = cast(MetadataChangeLogClass, event.event)
        if orig.get("entityType") != "dataset":
            return
        dataset_urn = orig.get("entityUrn")
        if not dataset_urn:
            return

        aspect_name = orig.get("aspectName")
        change_type = orig.get("changeType")

        # Handle deletion (status.removed=true or explicit DELETE)
        try:
            if aspect_name == StatusClass.ASPECT_NAME:
                # attempt to parse status
                aspect_json = orig.get("aspect")
                if aspect_json:
                    status_obj = json.loads(aspect_json).get(
                        "com.linkedin.common.Status", {}
                    )
                    if status_obj.get("removed") is True:
                        self._remove_property(dataset_urn)
                        return
            if change_type == ChangeTypeClass.DELETE or change_type == "DELETE":
                self._remove_property(dataset_urn)
                return
        except Exception as e:
            logger.debug("Delete handling failed for %s: %s", dataset_urn, e)

        # Upsert mapping on any dataset write.
        # Prefer pipelineName from the event's own systemMetadata; fall back to OpenAPI lookup.
        source_urn: Optional[str] = None
        try:
            sysmeta = orig.get("systemMetadata")
            if isinstance(sysmeta, dict):
                props = sysmeta.get("properties") if isinstance(sysmeta.get("properties"), dict) else None
                source_urn = (props or {}).get("pipelineName") or sysmeta.get("pipelineName")
        except Exception:
            source_urn = None

        if not source_urn:
            source_urn = self._resolve_source_urn_from_system_metadata(dataset_urn)

        if not source_urn or not isinstance(source_urn, str) or not source_urn.startswith("urn:li:dataHubIngestionSource:"):
            logger.debug(
                "No pipelineName found in system metadata for %s; skipping mapping", dataset_urn
            )
            return
        self._upsert_property(dataset_urn, source_urn)

    def close(self) -> None:  # type: ignore[override]
        return
