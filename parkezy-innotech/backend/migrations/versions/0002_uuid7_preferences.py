"""time-ordered UUIDv7 ids, notification preferences

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13

UUIDv7 (System Design Interview ch. 7, "Snowflake"-style ids): 48-bit millisecond timestamp
prefix + randomness. Still globally unique without coordination, but roughly time-ordered,
so B-tree inserts append to the right edge instead of scattering across the index.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLES = (
    "users", "refresh_tokens", "verification_codes", "push_tokens", "listings", "slots", "uploads",
    "listing_media", "bookings", "payments", "ledger_entries", "notifications", "outbox_events",
    "email_log", "webhook_events", "disputes",
)

UUID7 = """
CREATE OR REPLACE FUNCTION uuid_generate_v7() RETURNS uuid
LANGUAGE plpgsql VOLATILE AS $$
DECLARE
    ms bigint := floor(extract(epoch FROM clock_timestamp()) * 1000);
    b bytea := gen_random_bytes(16);
BEGIN
    b := set_byte(b, 0, ((ms >> 40) & 255)::int);
    b := set_byte(b, 1, ((ms >> 32) & 255)::int);
    b := set_byte(b, 2, ((ms >> 24) & 255)::int);
    b := set_byte(b, 3, ((ms >> 16) & 255)::int);
    b := set_byte(b, 4, ((ms >> 8) & 255)::int);
    b := set_byte(b, 5, (ms & 255)::int);
    b := set_byte(b, 6, (get_byte(b, 6) & 15) | 112);   -- version 7
    b := set_byte(b, 8, (get_byte(b, 8) & 63) | 128);   -- RFC 4122 variant
    RETURN encode(b, 'hex')::uuid;
END $$
"""


def upgrade() -> None:
    op.execute(UUID7)
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT uuid_generate_v7()")

    # Users opt out per channel and category (ch. 10). No row = enabled. The in-app inbox and
    # security emails (verification, password) are always delivered.
    op.execute("""
    CREATE TABLE notification_preferences (
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        channel varchar(16) NOT NULL CHECK (channel IN ('push', 'email')),
        category varchar(24) NOT NULL CHECK (category IN ('bookings', 'reminders', 'receipts', 'disputes')),
        enabled boolean NOT NULL,
        updated_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (user_id, channel, category)
    )""")
    op.execute("CREATE INDEX ix_outbox_dead ON outbox_events (created_at) WHERE processed_at IS NULL AND last_error IS NOT NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_outbox_dead")
    op.execute("DROP TABLE IF EXISTS notification_preferences")
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("DROP FUNCTION IF EXISTS uuid_generate_v7()")
