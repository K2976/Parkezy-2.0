from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class CodePurpose(StrEnum):
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


class ListingKind(StrEnum):
    PRIVATE = "private"
    COMMERCIAL = "commercial"


class ListingStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class SlotType(StrEnum):
    STANDARD = "standard"
    COMPACT = "compact"
    LARGE = "large"
    EV = "ev"
    ACCESSIBLE = "accessible"
    BIKE = "bike"


class Amenity(StrEnum):
    COVERED = "covered"
    CCTV = "cctv"
    SECURITY_GUARD = "security_guard"
    EV_CHARGING = "ev_charging"
    WHEELCHAIR_ACCESS = "wheelchair_access"
    WELL_LIT = "well_lit"
    GATED = "gated"
    RESTROOM = "restroom"


class BookingStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


# Statuses that occupy a slot. Mirrored by the exclusion constraint in the migration.
BLOCKING_STATUSES: frozenset[BookingStatus] = frozenset(
    {
        BookingStatus.PENDING_APPROVAL,
        BookingStatus.PENDING_PAYMENT,
        BookingStatus.CONFIRMED,
        BookingStatus.CHECKED_IN,
    }
)


class PaymentMode(StrEnum):
    ONLINE = "online"
    PAY_AT_VENUE = "pay_at_venue"


class PaymentStatus(StrEnum):
    CREATED = "created"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class UploadPurpose(StrEnum):
    LISTING_PHOTO = "listing_photo"
    DISPUTE_EVIDENCE = "dispute_evidence"
    AVATAR = "avatar"


class UploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"


class SupportCategory(StrEnum):
    ACCOUNT = "account"
    BOOKING = "booking"
    PAYMENT = "payment"
    HOSTING = "hosting"
    PRIVACY = "privacy"
    BUG = "bug"
    OTHER = "other"


class SupportStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class DisputeReason(StrEnum):
    SPOT_OCCUPIED = "spot_occupied"
    ACCESS_DENIED = "access_denied"
    WRONG_CHARGE = "wrong_charge"
    DAMAGE = "damage"
    SAFETY = "safety"
    OTHER = "other"


class DisputeStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class EmailStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    FAILED = "failed"
    SKIPPED = "skipped"


class LedgerAccount(StrEnum):
    DRIVER_PAYMENTS = "driver_payments"
    HOST_COLLECTED = "host_collected"
    HOST_PAYABLE = "host_payable"
    PLATFORM_REVENUE = "platform_revenue"
    PLATFORM_FEE_RECEIVABLE = "platform_fee_receivable"
    GST_PAYABLE = "gst_payable"


class NotificationChannel(StrEnum):
    PUSH = "push"
    EMAIL = "email"


class NotificationCategory(StrEnum):
    BOOKINGS = "bookings"
    REMINDERS = "reminders"
    RECEIPTS = "receipts"
    DISPUTES = "disputes"


# Notification "type" (as stored on the inbox row / push data) -> preference category.
NOTIFICATION_CATEGORY: dict[str, NotificationCategory] = {
    "booking_request": NotificationCategory.BOOKINGS,
    "booking_update": NotificationCategory.BOOKINGS,
    "session": NotificationCategory.REMINDERS,
    "receipt": NotificationCategory.RECEIPTS,
    "dispute": NotificationCategory.DISPUTES,
}
