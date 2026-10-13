"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""

import json

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _in(*values: str) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


BLOCKING = _in("pending_approval", "pending_payment", "confirmed", "checked_in")

# Business rules are data. Admins change them at runtime via PATCH /v1/admin/settings.
PLATFORM_SETTINGS: list[tuple[str, object, str]] = [
    ("currency", "INR", "ISO currency for all prices"),
    ("gst_rate", "0.18", "GST charged to the driver on the booking subtotal"),
    ("commission_rate_private", "0.15", "Platform commission on private listings"),
    ("commission_rate_commercial", "0.12", "Platform commission on commercial listings"),
    ("booking_step_minutes", 15, "Booking start/end must align to this many minutes"),
    ("min_booking_minutes", 30, "Shortest bookable duration"),
    ("max_booking_minutes", 10080, "Longest bookable duration"),
    ("max_advance_days", 30, "How far ahead a booking may start"),
    ("payment_hold_minutes", 10, "Slot hold while an online payment is pending"),
    ("approval_timeout_minutes", 30, "Host must answer a request within this time"),
    ("early_checkin_minutes", 15, "Check-in allowed this long before start"),
    ("overstay_grace_minutes", 5, "No overstay fee within this grace period"),
    ("overstay_block_minutes", 15, "Overstay is charged per started block"),
    ("overstay_block_fee", "20.00", "Fee per started overstay block (before GST)"),
    ("free_cancellation_minutes", 60, "Free cancellation until this long before start"),
    ("late_cancellation_fee_rate", "0.25", "Share of subtotal kept on late cancellation"),
    ("reminder_minutes_before_end", 15, "Session-ending reminder lead time"),
    ("min_listing_photos", 1, "Photos required before a listing can go live"),
    ("max_listing_photos", 5, "Photos per listing"),
    ("max_slots_per_listing", 500, "Slots per listing"),
    ("max_dispute_photos", 5, "Evidence photos per problem report"),
    ("search_default_radius_km", 5, "Default search radius"),
    ("search_max_radius_km", 25, "Largest allowed search radius"),
    ("search_max_results", 200, "Most listings returned by one search"),
    ("default_page_size", 20, "Default page size for list endpoints"),
    ("max_page_size", 100, "Largest page size for list endpoints"),
]


def _exec(sql: str) -> None:
    """asyncpg runs one statement per call; split on ';' outside $$-quoted bodies."""
    statement, in_body = [], False
    for part in sql.split(";"):
        statement.append(part)
        in_body ^= part.count("$$") % 2 == 1
        if not in_body:
            text = ";".join(statement).strip()
            if text:
                op.execute(text)
            statement = []


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    _exec(f"""
    CREATE TABLE users (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email citext NOT NULL UNIQUE,
        password_hash text,
        full_name varchar(120) NOT NULL,
        phone varchar(20),
        avatar_key text,
        email_verified_at timestamptz,
        status varchar(16) NOT NULL DEFAULT 'active'
            CHECK (status IN {_in("active", "suspended", "deleted")}),
        is_host boolean NOT NULL DEFAULT false,
        is_commercial_host boolean NOT NULL DEFAULT false,
        is_admin boolean NOT NULL DEFAULT false,
        deleted_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""")

    _exec("""
    CREATE TABLE refresh_tokens (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash varchar(64) NOT NULL UNIQUE,
        family_id uuid NOT NULL,
        expires_at timestamptz NOT NULL,
        revoked_at timestamptz,
        user_agent varchar(255),
        created_at timestamptz NOT NULL
    );
    CREATE INDEX ix_refresh_tokens_family ON refresh_tokens (family_id);
    CREATE INDEX ix_refresh_tokens_user ON refresh_tokens (user_id);
    """)

    _exec(f"""
    CREATE TABLE verification_codes (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        purpose varchar(32) NOT NULL CHECK (purpose IN {_in("email_verify", "password_reset")}),
        code_hash varchar(64) NOT NULL,
        expires_at timestamptz NOT NULL,
        attempts smallint NOT NULL DEFAULT 0,
        consumed_at timestamptz,
        created_at timestamptz NOT NULL
    );
    CREATE INDEX ix_verification_codes_user_purpose ON verification_codes (user_id, purpose);
    """)

    _exec(f"""
    CREATE TABLE push_tokens (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token text NOT NULL UNIQUE,
        platform varchar(16) NOT NULL CHECK (platform IN {_in("ios", "android")}),
        last_seen_at timestamptz NOT NULL
    );
    CREATE INDEX ix_push_tokens_user ON push_tokens (user_id);
    """)

    _exec("""
    CREATE TABLE platform_settings (
        key varchar(64) PRIMARY KEY,
        value jsonb NOT NULL,
        description text NOT NULL,
        updated_at timestamptz NOT NULL DEFAULT now()
    )""")

    _exec(f"""
    CREATE TABLE listings (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        owner_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        kind varchar(16) NOT NULL CHECK (kind IN {_in("private", "commercial")}),
        status varchar(16) NOT NULL CHECK (status IN {_in("draft", "active", "paused", "archived")}),
        title varchar(120) NOT NULL,
        description text,
        access_instructions text,
        address_line varchar(255) NOT NULL,
        city varchar(80) NOT NULL,
        postal_code varchar(16),
        latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
        longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
        location geography(Point, 4326)
            GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography)
            STORED,
        timezone varchar(64) NOT NULL,
        amenities varchar(32)[] NOT NULL DEFAULT '{{}}',
        hourly_rate numeric(12,2) NOT NULL CHECK (hourly_rate > 0),
        daily_cap numeric(12,2) CHECK (daily_cap IS NULL OR daily_cap > 0),
        currency varchar(3) NOT NULL,
        auto_accept boolean NOT NULL DEFAULT true,
        is_24h boolean NOT NULL DEFAULT true,
        open_time time,
        close_time time,
        open_days smallint[] NOT NULL DEFAULT '{{1,2,3,4,5,6,7}}',
        rating_avg numeric(3,2),
        rating_count integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_listings_hours CHECK (
            is_24h OR (open_time IS NOT NULL AND close_time IS NOT NULL AND open_time < close_time)
        )
    );
    CREATE INDEX ix_listings_location_active ON listings USING gist (location)
        WHERE status = 'active';
    CREATE INDEX ix_listings_owner ON listings (owner_id);
    """)

    _exec(f"""
    CREATE TABLE slots (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        listing_id uuid NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
        label varchar(32) NOT NULL,
        floor varchar(16),
        slot_type varchar(16) NOT NULL
            CHECK (slot_type IN {_in("standard", "compact", "large", "ev", "accessible", "bike")}),
        hourly_rate_override numeric(12,2) CHECK (hourly_rate_override IS NULL OR hourly_rate_override > 0),
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_slots_listing_label UNIQUE (listing_id, label)
    );
    """)

    _exec(f"""
    CREATE TABLE uploads (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        purpose varchar(32) NOT NULL
            CHECK (purpose IN {_in("listing_photo", "dispute_evidence", "avatar")}),
        storage_key text NOT NULL UNIQUE,
        content_type varchar(64) NOT NULL,
        size_bytes bigint,
        status varchar(16) NOT NULL CHECK (status IN {_in("pending", "uploaded")}),
        created_at timestamptz NOT NULL
    );
    CREATE INDEX ix_uploads_owner ON uploads (owner_id);

    CREATE TABLE listing_media (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        listing_id uuid NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
        upload_id uuid NOT NULL UNIQUE REFERENCES uploads(id) ON DELETE CASCADE,
        storage_key text NOT NULL,
        position smallint NOT NULL,
        created_at timestamptz NOT NULL
    );
    CREATE INDEX ix_listing_media_listing ON listing_media (listing_id, position);
    """)

    statuses = _in(
        "pending_approval",
        "pending_payment",
        "confirmed",
        "checked_in",
        "completed",
        "cancelled",
        "rejected",
        "expired",
    )
    _exec(f"""
    CREATE TABLE bookings (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        driver_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        host_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        listing_id uuid NOT NULL REFERENCES listings(id) ON DELETE RESTRICT,
        slot_id uuid NOT NULL REFERENCES slots(id) ON DELETE RESTRICT,
        period tstzrange NOT NULL CHECK (NOT isempty(period) AND lower_inc(period) AND NOT upper_inc(period)),
        status varchar(24) NOT NULL CHECK (status IN {statuses}),
        payment_mode varchar(16) NOT NULL CHECK (payment_mode IN {_in("online", "pay_at_venue")}),
        vehicle_number varchar(16),
        idempotency_key varchar(64) NOT NULL,
        currency varchar(3) NOT NULL,
        hourly_rate numeric(12,2) NOT NULL,
        subtotal numeric(12,2) NOT NULL CHECK (subtotal >= 0),
        tax_amount numeric(12,2) NOT NULL CHECK (tax_amount >= 0),
        platform_fee numeric(12,2) NOT NULL CHECK (platform_fee >= 0),
        total_amount numeric(12,2) NOT NULL CHECK (total_amount >= 0),
        tax_rate numeric(5,4) NOT NULL,
        commission_rate numeric(5,4) NOT NULL,
        hold_expires_at timestamptz,
        approval_expires_at timestamptz,
        approved_at timestamptz,
        cancelled_at timestamptz,
        cancel_reason text,
        checked_in_at timestamptz,
        checked_out_at timestamptz,
        overstay_minutes integer NOT NULL DEFAULT 0,
        overstay_fee numeric(12,2) NOT NULL DEFAULT 0,
        overstay_tax numeric(12,2) NOT NULL DEFAULT 0,
        final_amount numeric(12,2),
        reminder_sent_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_bookings_driver_idempotency UNIQUE (driver_id, idempotency_key),
        -- The core integrity guarantee: one slot can never hold two overlapping live bookings.
        CONSTRAINT ex_bookings_no_overlap EXCLUDE USING gist (slot_id WITH =, period WITH &&)
            WHERE (status IN {BLOCKING})
    );
    CREATE INDEX ix_bookings_driver ON bookings (driver_id, created_at DESC);
    CREATE INDEX ix_bookings_host ON bookings (host_id, created_at DESC);
    CREATE INDEX ix_bookings_listing_period ON bookings USING gist (listing_id, period)
        WHERE status IN {BLOCKING};
    CREATE INDEX ix_bookings_hold ON bookings (hold_expires_at) WHERE status = 'pending_payment';
    CREATE INDEX ix_bookings_approval ON bookings (approval_expires_at)
        WHERE status = 'pending_approval';
    CREATE INDEX ix_bookings_active_end ON bookings (upper(period))
        WHERE status IN ('confirmed', 'checked_in');
    """)

    _exec(f"""
    CREATE TABLE payments (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        booking_id uuid NOT NULL REFERENCES bookings(id) ON DELETE RESTRICT,
        provider varchar(16) NOT NULL,
        provider_order_id varchar(64) NOT NULL UNIQUE,
        provider_payment_id varchar(64),
        amount numeric(12,2) NOT NULL CHECK (amount > 0),
        refunded_amount numeric(12,2) NOT NULL DEFAULT 0 CHECK (refunded_amount >= 0),
        currency varchar(3) NOT NULL,
        status varchar(16) NOT NULL CHECK (status IN {_in("created", "captured", "failed", "refunded")}),
        failure_reason text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_payments_booking ON payments (booking_id);

    CREATE TABLE ledger_entries (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        txn_id uuid NOT NULL,
        booking_id uuid REFERENCES bookings(id),
        account varchar(32) NOT NULL,
        user_id uuid REFERENCES users(id),
        amount numeric(12,2) NOT NULL,
        currency varchar(3) NOT NULL,
        memo varchar(255) NOT NULL,
        created_at timestamptz NOT NULL
    );
    CREATE INDEX ix_ledger_user_account ON ledger_entries (user_id, account);
    CREATE INDEX ix_ledger_txn ON ledger_entries (txn_id);

    -- Double-entry invariant: every transaction must balance to zero.
    CREATE FUNCTION ledger_txn_balanced() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF (SELECT COALESCE(SUM(amount), 0) FROM ledger_entries WHERE txn_id = NEW.txn_id) <> 0 THEN
            RAISE EXCEPTION 'ledger transaction % does not balance', NEW.txn_id;
        END IF;
        RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER trg_ledger_balanced AFTER INSERT ON ledger_entries
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_txn_balanced();
    """)

    _exec("""
    CREATE TABLE notifications (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        type varchar(48) NOT NULL,
        title varchar(160) NOT NULL,
        body text NOT NULL,
        data jsonb NOT NULL DEFAULT '{}',
        read_at timestamptz,
        created_at timestamptz NOT NULL
    );
    CREATE INDEX ix_notifications_user ON notifications (user_id, created_at DESC);

    CREATE TABLE outbox_events (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        type varchar(64) NOT NULL,
        payload jsonb NOT NULL,
        created_at timestamptz NOT NULL,
        available_at timestamptz NOT NULL,
        processed_at timestamptz,
        attempts smallint NOT NULL DEFAULT 0,
        last_error text
    );
    CREATE INDEX ix_outbox_pending ON outbox_events (available_at) WHERE processed_at IS NULL;
    """)

    _exec(f"""
    CREATE TABLE email_log (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid REFERENCES users(id) ON DELETE SET NULL,
        to_email citext NOT NULL,
        template varchar(64) NOT NULL,
        dedupe_key varchar(160) NOT NULL UNIQUE,
        provider_message_id varchar(128),
        status varchar(16) NOT NULL CHECK (status IN {
        _in("queued", "sent", "delivered", "bounced", "complained", "failed", "skipped")
    }),
        error text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_email_log_provider_id ON email_log (provider_message_id);

    CREATE TABLE email_suppressions (
        email citext PRIMARY KEY,
        reason varchar(32) NOT NULL,
        created_at timestamptz NOT NULL
    );

    CREATE TABLE webhook_events (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        provider varchar(16) NOT NULL,
        event_id varchar(128) NOT NULL,
        event_type varchar(64) NOT NULL,
        received_at timestamptz NOT NULL,
        CONSTRAINT uq_webhook_events_provider_event UNIQUE (provider, event_id)
    );
    """)

    _exec(f"""
    CREATE TABLE disputes (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        booking_id uuid NOT NULL REFERENCES bookings(id) ON DELETE RESTRICT,
        reporter_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        reason varchar(32) NOT NULL CHECK (reason IN {
        _in("spot_occupied", "access_denied", "wrong_charge", "damage", "safety", "other")
    }),
        description text NOT NULL,
        evidence_keys text[] NOT NULL DEFAULT '{{}}',
        status varchar(16) NOT NULL CHECK (status IN {_in("open", "in_review", "resolved", "rejected")}),
        resolution text,
        resolved_by uuid REFERENCES users(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_disputes_booking ON disputes (booking_id);
    CREATE INDEX ix_disputes_status ON disputes (status, created_at);
    """)

    for key, value, description in PLATFORM_SETTINGS:
        op.execute(
            "INSERT INTO platform_settings (key, value, description) VALUES "
            f"('{key}', '{json.dumps(value)}'::jsonb, '{description}')"
        )


def downgrade() -> None:
    for table in (
        "disputes",
        "webhook_events",
        "email_suppressions",
        "email_log",
        "outbox_events",
        "notifications",
        "ledger_entries",
        "payments",
        "bookings",
        "listing_media",
        "uploads",
        "slots",
        "listings",
        "platform_settings",
        "push_tokens",
        "verification_codes",
        "refresh_tokens",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    op.execute("DROP FUNCTION IF EXISTS ledger_txn_balanced()")
