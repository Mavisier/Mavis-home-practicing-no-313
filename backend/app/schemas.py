from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

RequestText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=4000)
]
ListingId = Annotated[
    str, StringConstraints(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
]


class Narrative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=4000)
    seller_message: str = Field(min_length=1, max_length=8000)
    questions: list[Annotated[str, StringConstraints(min_length=1, max_length=1000)]] = Field(
        max_length=12
    )


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=80)
    severity: Literal["high", "medium", "info"]
    title: str = Field(min_length=1, max_length=300)
    detail: str = Field(min_length=1, max_length=4000)
    question: str = Field(min_length=1, max_length=1000)
    source_id: str = Field(min_length=1, max_length=100)


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    body: str
    url: HttpUrl | None
    kind: Literal["public_summary", "synthetic_policy"]
    version: str


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    listing: dict
    workflow: Literal["listing_review", "trink_readiness"]
    verdict: Literal["needs_information", "needs_review", "consistent"]
    findings: list[Finding] = Field(max_length=50)
    narrative: Narrative
    sources: list[Evidence] = Field(max_length=10)
    mode: Literal["fixture", "openai", "anthropic", "ollama"]
    embedding_space: str
    explanation_kind: Literal["fixture", "approved_empty", "local_summary", "remote_narrative"] = (
        "fixture"
    )
    latency_ms: int = Field(ge=0)
    limitations: list[str]


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_text: RequestText


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    request_text: str
    intent: str | None
    status: str
    started_at: datetime


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sequence: int
    event_type: str
    payload_json: dict
    created_at: datetime


class ActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tool_name: str
    arguments_json: dict
    status: str
    result_json: dict | None


class RunRead(RunSummary):
    final_response_json: dict | None
    events: list[EventRead]
    action: ActionRead | None = None


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    listing_id: ListingId
    workflow: Literal["listing_review", "trink_readiness"]
    request_text: RequestText


class DescriptionEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: RequestText


class HealthRead(BaseModel):
    status: Literal["ok", "ready", "unavailable"]
    milestone: int = 1
    database: Literal["connected", "unavailable"] | None = None
    vector_extension: bool | None = None
