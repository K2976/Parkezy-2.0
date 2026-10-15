"""Map domain objects to response schemas. Keeps routers thin and output consistent."""

import uuid
from decimal import Decimal

from app.db.models import Dispute, Favorite, Listing, Payout, PayoutAccount, Review, User
from app.domain.enums import BookingStatus, ListingKind, PaymentMode, UserStatus
from app.domain.pricing import money
from app.integrations.storage import ObjectStorage
from app.schemas.bookings import (
    BookingListingOut,
    BookingOut,
    BookingSlotOut,
    PartyOut,
    ReceiptLineOut,
    ReceiptListingOut,
    ReceiptOut,
    ReceiptPartyOut,
)
from app.schemas.listings import FavoriteOut, HostSummary, ListingOut, ListingSearchItem, MediaOut, SlotOut
from app.schemas.misc import DisputeOut
from app.schemas.payouts import PayoutAccountOut, PayoutOut
from app.schemas.reviews import ReviewAuthor, ReviewOut
from app.schemas.users import AdminUserDetail, AdminUserOut, UserOut
from app.services.booking_service import BookingView
from app.services.listing_service import effective_rate
from app.services.receipt_service import ReceiptDoc

# Drivers see the gate/access instructions and host phone only once the booking is real.
REVEAL_STATUSES = {BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value}


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        email_verified=user.email_verified_at is not None,
        is_host=user.is_host,
        is_commercial_host=user.is_commercial_host,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


def listing_out(
    listing: Listing,
    host: User,
    storage: ObjectStorage,
    *,
    availability: dict[uuid.UUID, bool] | None = None,
    include_private: bool = False,
    include_inactive_slots: bool = False,
) -> ListingOut:
    slots = [s for s in listing.slots if include_inactive_slots or s.is_active]
    return ListingOut(
        id=listing.id,
        kind=listing.kind,
        status=listing.status,
        title=listing.title,
        description=listing.description,
        address_line=listing.address_line,
        city=listing.city,
        postal_code=listing.postal_code,
        latitude=listing.latitude,
        longitude=listing.longitude,
        timezone=listing.timezone,
        amenities=list(listing.amenities),
        hourly_rate=listing.hourly_rate,
        daily_cap=listing.daily_cap,
        currency=listing.currency,
        auto_accept=listing.auto_accept,
        is_24h=listing.is_24h,
        open_time=listing.open_time,
        close_time=listing.close_time,
        open_days=list(listing.open_days),
        rating_avg=listing.rating_avg,
        rating_count=listing.rating_count,
        host=HostSummary(id=host.id, first_name=host.full_name.split(" ")[0]),
        slots=[
            SlotOut(
                id=s.id,
                label=s.label,
                floor=s.floor,
                slot_type=s.slot_type,
                hourly_rate=effective_rate(listing, s),
                is_active=s.is_active,
                available=None if availability is None else availability.get(s.id, False),
            )
            for s in slots
        ],
        media=[MediaOut(id=m.id, url=storage.download_url(m.storage_key), position=m.position) for m in listing.media],
        access_instructions=listing.access_instructions if include_private else None,
    )


def search_item(row: dict, storage: ObjectStorage) -> ListingSearchItem:
    cover = row.pop("cover_key", None)
    return ListingSearchItem(**row, cover_photo_url=storage.download_url(cover) if cover else None)


def booking_out(view: BookingView, viewer: User) -> BookingOut:
    b = view.booking
    is_host = viewer.id == b.host_id
    reveal = is_host or b.status in REVEAL_STATUSES
    return BookingOut(
        id=b.id,
        status=b.status,
        payment_mode=b.payment_mode,
        starts_at=b.starts_at,
        ends_at=b.ends_at,
        vehicle_number=b.vehicle_number,
        currency=b.currency,
        hourly_rate=b.hourly_rate,
        subtotal=b.subtotal,
        tax_amount=b.tax_amount,
        total_amount=b.total_amount,
        overstay_minutes=b.overstay_minutes,
        overstay_fee=b.overstay_fee,
        overstay_tax=b.overstay_tax,
        final_amount=b.final_amount,
        amount_paid=view.amount_paid,
        amount_due=view.amount_due,
        hold_expires_at=b.hold_expires_at,
        approval_expires_at=b.approval_expires_at,
        checked_in_at=b.checked_in_at,
        checked_out_at=b.checked_out_at,
        cancelled_at=b.cancelled_at,
        cancel_reason=b.cancel_reason,
        created_at=b.created_at,
        listing=BookingListingOut.model_validate(view.listing),
        slot=BookingSlotOut.model_validate(view.slot),
        driver=PartyOut(
            id=view.driver.id, full_name=view.driver.full_name, phone=view.driver.phone if is_host else None
        ),
        host=PartyOut(id=view.host.id, full_name=view.host.full_name, phone=view.host.phone if reveal else None),
        access_instructions=view.listing.access_instructions if reveal else None,
        host_earnings=host_earnings(b.subtotal + b.overstay_fee, b.commission_rate) if is_host else None,
    )


def dispute_out(dispute: Dispute, storage: ObjectStorage) -> DisputeOut:
    return DisputeOut(
        id=dispute.id,
        booking_id=dispute.booking_id,
        reason=dispute.reason,
        description=dispute.description,
        status=dispute.status,
        resolution=dispute.resolution,
        evidence_urls=[storage.download_url(k) for k in dispute.evidence_keys],
        created_at=dispute.created_at,
        updated_at=dispute.updated_at,
    )


def host_earnings(gross: Decimal, commission_rate: Decimal) -> Decimal:
    return gross - money(gross * commission_rate)


def first_name(user: User | None) -> str:
    return user.full_name.split(" ")[0] if user and user.full_name else "Parkezy user"


def review_out(review: Review, author: User | None) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        booking_id=review.booking_id,
        listing_id=review.listing_id,
        rating=review.rating,
        comment=review.comment,
        author=ReviewAuthor(first_name=first_name(author)),
        host_reply=review.host_reply,
        host_replied_at=review.host_replied_at,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def favorite_out(listing: Listing, favorite: Favorite, cover_key: str | None, storage: ObjectStorage) -> FavoriteOut:
    return FavoriteOut(
        id=listing.id,
        kind=ListingKind(listing.kind),
        title=listing.title,
        address_line=listing.address_line,
        city=listing.city,
        latitude=listing.latitude,
        longitude=listing.longitude,
        hourly_rate=listing.hourly_rate,
        currency=listing.currency,
        amenities=list(listing.amenities),
        rating_avg=listing.rating_avg,
        rating_count=listing.rating_count,
        cover_photo_url=storage.download_url(cover_key) if cover_key else None,
        saved_at=favorite.created_at,
    )


def payout_out(payout: Payout) -> PayoutOut:
    return PayoutOut.model_validate(payout)


def payout_account_out(account: PayoutAccount) -> PayoutAccountOut:
    bank = account.method == "bank_account"
    return PayoutAccountOut(
        method=account.method,
        upi_id=None if bank else account.upi_id,
        account_holder_name=account.account_holder_name if bank else None,
        account_number_last4=(account.account_number or "")[-4:] if bank else None,
        ifsc=account.ifsc if bank else None,
        updated_at=account.updated_at,
    )


def admin_user_out(user: User) -> AdminUserOut:
    return AdminUserOut(**user_out(user).model_dump(), status=UserStatus(user.status))


def admin_user_detail(user: User, counts: dict[str, int]) -> AdminUserDetail:
    return AdminUserDetail.model_validate(
        admin_user_out(user).model_dump()
        | counts
        | {"suspension_reason": user.suspension_reason, "suspended_at": user.suspended_at}
    )


def receipt_out(doc: ReceiptDoc) -> ReceiptOut:
    b, listing = doc.view.booking, doc.view.listing
    return ReceiptOut(
        invoice_number=doc.receipt.invoice_number,
        issued_at=doc.receipt.issued_at,
        booking_id=b.id,
        currency=b.currency,
        payment_mode=PaymentMode(b.payment_mode),
        listing=ReceiptListingOut(title=listing.title, address_line=listing.address_line, city=listing.city),
        driver=ReceiptPartyOut(full_name=doc.view.driver.full_name),
        host=ReceiptPartyOut(full_name=doc.view.host.full_name),
        starts_at=b.starts_at,
        ends_at=b.ends_at,
        checked_in_at=b.checked_in_at,
        checked_out_at=b.checked_out_at,
        line_items=[ReceiptLineOut(kind=i.kind, description=i.description, amount=i.amount) for i in doc.line_items],
        subtotal=doc.subtotal,
        tax_amount=doc.tax_amount,
        total=doc.total,
        amount_paid=doc.amount_paid,
        amount_due=doc.amount_due,
    )
