"""Vehicle review records, versioned knowledge and approved local tasks."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_vehicle_review"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vehicle_listings",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("requester_id", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("scenario", sa.String(80), nullable=False),
        sa.Column("vehicle_json", JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("photos_json", JSONB(), nullable=False),
    )
    op.create_index("ix_vehicle_listings_requester_id", "vehicle_listings", ["requester_id"])
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("workflow", sa.String(30), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("source_kind", sa.String(30), nullable=False),
        sa.Column("source_version", sa.String(30), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column("embedding_space", sa.String(120), nullable=False),
    )
    op.create_table(
        "actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("runs.id"), unique=True, nullable=False),
        sa.Column("tool_name", sa.String(80), nullable=False),
        sa.Column("arguments_json", JSONB(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("approved_by", sa.String(80)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("result_json", JSONB()),
    )
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("action_id", sa.Uuid(), sa.ForeignKey("actions.id"), unique=True, nullable=False),
        sa.Column(
            "listing_id", sa.String(40), sa.ForeignKey("vehicle_listings.id"), nullable=False
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payload_json", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    for name in ["review_tasks", "actions", "knowledge_chunks", "vehicle_listings"]:
        op.drop_table(name)
