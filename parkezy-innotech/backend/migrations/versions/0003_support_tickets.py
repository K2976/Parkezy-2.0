"""support tickets

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-14
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE support_tickets (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
        user_id uuid REFERENCES users(id) ON DELETE SET NULL,
        email citext NOT NULL,
        name varchar(120),
        category varchar(16) NOT NULL,
        subject varchar(160) NOT NULL,
        message text NOT NULL,
        booking_id uuid REFERENCES bookings(id) ON DELETE SET NULL,
        status varchar(16) NOT NULL DEFAULT 'open',
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX ix_support_tickets_user ON support_tickets (user_id, created_at DESC)")
    op.execute("CREATE INDEX ix_support_tickets_open ON support_tickets (created_at) WHERE status = 'open'")


def downgrade() -> None:
    op.execute("DROP TABLE support_tickets")
