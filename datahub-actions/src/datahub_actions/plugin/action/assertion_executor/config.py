from typing import Dict, Optional

from pydantic import BaseModel, Field


class AssertionExecutorConfig(BaseModel):
    """
    Configuration for Assertion Executor Action.

    This action automatically executes assertions when datasets are ingested or profiled.
    """

    enabled: bool = Field(
        default=True,
        description="Enable or disable the assertion executor",
    )

    trigger_on_ingestion: bool = Field(
        default=True,
        description="Execute assertions when datasets are ingested (status aspect changes)",
    )

    trigger_on_profile: bool = Field(
        default=True,
        description="Execute assertions when datasets are profiled (datasetProfile aspect changes)",
    )

    connector_configs: Optional[Dict[str, Dict]] = Field(
        default=None,
        description="Optional override connector configurations for testing",
    )

    max_retries: int = Field(
        default=2,
        description="Maximum number of retries for assertion execution",
    )

    timeout_seconds: int = Field(
        default=60,
        description="Timeout for assertion execution in seconds",
    )

    emit_results: bool = Field(
        default=True,
        description="Whether to emit assertion results as AssertionRunEvent",
    )
