from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint("length(trim(request_text)) BETWEEN 3 AND 4000", name="request_length"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requester_id: Mapped[str] = mapped_column(String(80), index=True)
    request_text: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="received")
    final_response_json: Mapped[dict | None] = mapped_column(JSONB)
    provider: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="event_sequence"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(60))
    payload_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="positive_order_amount"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    requester_id: Mapped[str] = mapped_column(String(80))
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    service_used: Mapped[bool] = mapped_column(Boolean)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    requester_id: Mapped[str] = mapped_column(String(80))
    subject: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30))


class VehicleListing(Base):
    __tablename__ = "vehicle_listings"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    requester_id: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    scenario: Mapped[str] = mapped_column(String(80))
    vehicle_json: Mapped[dict] = mapped_column(JSONB)
    description: Mapped[str] = mapped_column(Text)
    photos_json: Mapped[list] = mapped_column(JSONB)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    workflow: Mapped[str] = mapped_column(String(30))
    body: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(30))
    source_version: Mapped[str] = mapped_column(String(30))
    embedding: Mapped[list] = mapped_column(Vector())
    embedding_space: Mapped[str] = mapped_column(String(120))


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id"), unique=True)
    tool_name: Mapped[str] = mapped_column(String(80))
    arguments_json: Mapped[dict] = mapped_column(JSONB)
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="pending_approval")
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_json: Mapped[dict | None] = mapped_column(JSONB)


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    action_id: Mapped[UUID] = mapped_column(ForeignKey("actions.id"), unique=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("vehicle_listings.id"))
    status: Mapped[str] = mapped_column(String(30), default="open")
    payload_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
