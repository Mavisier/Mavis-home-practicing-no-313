"""Request persistence, audit trail and synthetic business records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("requester_id", sa.String(80), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(30)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("final_response_json", postgresql.JSONB()),
        sa.Column("provider", sa.String(40)),
        sa.Column("model", sa.String(100)),
        sa.Column("prompt_version", sa.String(40)),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("length(trim(request_text)) BETWEEN 3 AND 4000", name="request_length"),
    )
    op.create_index("ix_runs_requester_id", "runs", ["requester_id"])
    op.create_table(
        "run_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("run_id", "sequence", name="event_sequence"),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"])
    op.create_table(
        "orders",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("requester_id", sa.String(80), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service_used", sa.Boolean(), nullable=False),
        sa.Column("refunded_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount_minor > 0", name="positive_order_amount"),
    )
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("requester_id", sa.String(80), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
    )


def downgrade():
    op.drop_table("support_tickets")
    op.drop_table("orders")
    op.drop_table("run_events")
    op.drop_table("runs")
    # The extension may be used by other schemas; leave it installed.
