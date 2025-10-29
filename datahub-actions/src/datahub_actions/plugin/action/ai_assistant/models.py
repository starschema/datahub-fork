"""Pydantic models for AI Assistant API requests and responses."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Schema information for a single column."""

    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    description: Optional[str] = None


class DatasetSchema(BaseModel):
    """Complete schema for a dataset."""

    columns: List[ColumnSchema]
    platform: str
    database: Optional[str] = None
    schema_name: Optional[str] = None
    table: str


class ValidateRequest(BaseModel):
    """Request to validate an NL rule against dataset schema."""

    dataset_urn: str = Field(..., description="URN of the dataset")
    nl_rule: str = Field(..., description="Natural language quality rule")


class ValidateResponse(BaseModel):
    """Response from validation."""

    feasible: bool
    reasons: List[str] = Field(default_factory=list)
    schema: Optional[DatasetSchema] = None


class Guardrails(BaseModel):
    """Safety guardrails for SQL execution."""

    readonly: bool = True
    limits: Dict[str, int] = Field(
        default_factory=lambda: {"rowLimit": 1000, "timeoutSec": 8}
    )


class AssertionConfig(BaseModel):
    """Configuration for the assertion."""

    type: str
    params: Dict[str, Any]


class GenerateRequest(BaseModel):
    """Request to generate SQL and assertion config."""

    dataset_urn: str
    nl_rule: str


class GenerateResponse(BaseModel):
    """Response from SQL generation."""

    sql: str
    config: AssertionConfig
    guardrails: Guardrails


class ExecuteRequest(BaseModel):
    """Request to execute generated SQL."""

    dataset_urn: str
    sql: str
    config: AssertionConfig


class ExecuteResponse(BaseModel):
    """Response from SQL execution."""

    passed: bool
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class AssertionMetadata(BaseModel):
    """Optional metadata for the assertion."""

    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class PersistRequest(BaseModel):
    """Request to persist assertion to DataHub."""

    dataset_urn: str
    sql: str
    config: AssertionConfig
    metadata: Optional[AssertionMetadata] = None
    nl_rule: Optional[str] = None
    passed: Optional[bool] = None
    metrics: Optional[Dict[str, Any]] = None


class PersistResponse(BaseModel):
    """Response from assertion persistence."""

    assertion_urn: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    llm_provider: str = "gemini"


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    code: str
    details: Optional[Dict[str, Any]] = None


# Self-test models for connector health checks
class SnowflakeSelfTestRequest(BaseModel):
    """Request to self-test Snowflake connectivity via AI Assistant executor."""

    dataset_urn: str


class SnowflakeSelfTestResponse(BaseModel):
    """Response for Snowflake self-test."""

    ok: bool
    version: Optional[str] = None
    error: Optional[str] = None


# Debug connection inspection models
class DebugConnectionRequest(BaseModel):
    """Request to inspect connector resolution for a dataset."""

    dataset_urn: str


class SourceSummary(BaseModel):
    name: Optional[str] = None
    urn: Optional[str] = None
    type: Optional[str] = None


class DebugConnectionResponse(BaseModel):
    """Details about how connection resolution was derived."""

    platform: Optional[str] = None
    mapping_property_urn: Optional[str] = None
    pipeline_name_urn: Optional[str] = None
    selected_source: Optional[SourceSummary] = None
    native_available: bool = False
    engine_available: bool = False
    candidates_count: int = 0


class BackfillMappingRequest(BaseModel):
    """Request to backfill dataset→source mapping by reading system metadata and persisting it."""
    dataset_urn: str
    # Optional override: force map to a specific source URN
    source_urn: Optional[str] = None
    # If true, and exactly one candidate source exists for the platform, auto-select it
    auto_select_if_single: bool = True


class BackfillMappingResponse(BaseModel):
    """Response for backfill operation."""

    ok: bool
    source_urn: Optional[str] = None
    error: Optional[str] = None
