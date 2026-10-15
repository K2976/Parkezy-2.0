"""reviews, favourites, payouts, receipts, social sign-in, user suspension

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-15
"""

import json

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

NEW_SETTINGS = (
    ("review_window_days", 14, "Days after check-out a driver may write or edit a review"),
    ("min_payout_amount", "100.00", "Smallest withdrawal a host may request"),
)


def upgrade() -> None:
    # ---------------------------------------------------------------- users
    # token_version is embedded in access tokens; bumping it signs the user out everywhere at once.
    op.execute("""
    ALTER TABLE users
        ADD COLUMN token_version integer NOT NULL DEFAULT 0,
        ADD COLUMN suspended_at timestamptz,
        ADD COLUMN suspension_reason text
    """)
    op.execute("CREATE INDEX ix_users_created ON users (created_at DESC, id DESC)")

    op.execute("""
    CREATE TABLE social_identities (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider varchar(16) NOT NULL CHECK (provider IN ('google', 'apple')),
        subject varchar(255) NOT NULL,
        email citext,
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_social_identities_provider_subject UNIQUE (provider, subject)
    )""")
    op.execute("CREATE INDEX ix_social_identities_user ON social_identities (user_id)")

    # ---------------------------------------------------------------- reviews
    op.execute("""
    CREATE TABLE reviews (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
        booking_id uuid NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
        listing_id uuid NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
        author_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        rating smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
        comment text,
        host_reply text,
        host_replied_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_reviews_booking UNIQUE (booking_id)
    )""")
    op.execute("CREATE INDEX ix_reviews_listing ON reviews (listing_id, created_at DESC, id DESC)")

    # ---------------------------------------------------------------- favourites
    op.execute("""
    CREATE TABLE favorites (
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        listing_id uuid NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (user_id, listing_id)
    )""")
    op.execute("CREATE INDEX ix_favorites_user ON favorites (user_id, created_at DESC, listing_id DESC)")

    # ---------------------------------------------------------------- payouts
    op.execute("""
    CREATE TABLE payout_accounts (
        user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        method varchar(16) NOT NULL CHECK (method IN ('upi', 'bank_account')),
        upi_id varchar(256),
        account_holder_name varchar(120),
        account_number varchar(18),
        ifsc varchar(11),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CHECK (
            (method = 'upi' AND upi_id IS NOT NULL)
            OR (method = 'bank_account' AND account_number IS NOT NULL AND ifsc IS NOT NULL
                AND account_holder_name IS NOT NULL)
        )
    )""")
    op.execute("""
    CREATE TABLE payouts (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
        host_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        amount numeric(12,2) NOT NULL CHECK (amount > 0),
        currency varchar(3) NOT NULL,
        status varchar(16) NOT NULL CHECK (status IN ('requested', 'paid', 'rejected', 'cancelled')),
        method varchar(16) NOT NULL,
        destination jsonb NOT NULL,
        idempotency_key varchar(64) NOT NULL,
        reference varchar(128),
        reject_reason text,
        decided_by uuid REFERENCES users(id),
        requested_at timestamptz NOT NULL,
        paid_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_payouts_host_idempotency UNIQUE (host_id, idempotency_key)
    )""")
    op.execute("CREATE INDEX ix_payouts_host ON payouts (host_id, created_at DESC, id DESC)")
    op.execute("CREATE INDEX ix_payouts_status ON payouts (status, created_at DESC, id DESC)")

    # ---------------------------------------------------------------- receipts
    # Numbers come from a sequence: unique and increasing, assigned once on first issue.
    op.execute("CREATE SEQUENCE invoice_number_seq")
    op.execute("""
    CREATE TABLE receipts (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
        booking_id uuid NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
        invoice_number varchar(32) NOT NULL,
        issued_at timestamptz NOT NULL,
        CONSTRAINT uq_receipts_booking UNIQUE (booking_id),
        CONSTRAINT uq_receipts_invoice_number UNIQUE (invoice_number)
    )""")

    for key, value, description in NEW_SETTINGS:
        op.execute(
            "INSERT INTO platform_settings (key, value, description) VALUES "
            f"('{key}', '{json.dumps(value)}'::jsonb, '{description}')"
        )


def downgrade() -> None:
    op.execute("DELETE FROM platform_settings WHERE key IN ('review_window_days', 'min_payout_amount')")
    for table in ("receipts", "payouts", "payout_accounts", "favorites", "reviews", "social_identities"):
        op.execute(f"DROP TABLE IF EXISTS {table}")
    op.execute("DROP SEQUENCE IF EXISTS invoice_number_seq")
    op.execute("DROP INDEX IF EXISTS ix_users_created")
    op.execute("ALTER TABLE users DROP COLUMN suspension_reason, DROP COLUMN suspended_at, DROP COLUMN token_version")
