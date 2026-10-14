"""Terms of Service and Privacy Policy: the single source for the in-app screens
(GET /v1/legal/{doc}) and the public pages app stores link to (GET /legal/{doc}).

Fees and time windows are filled in from the live platform rules, so the documents can never
disagree with what the app actually charges. Bump VERSION when the wording changes materially.

Written for an India-based marketplace (IT Act 2000, IT Rules 2021, DPDP Act 2023, CPA 2019).
Have a lawyer review it before launch and whenever the business changes.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.core.config import Settings
from app.domain.rules import PlatformRules

VERSION = "1.0"
EFFECTIVE_DATE = "14 October 2026"

# A block is a paragraph (str) or a bulleted list (list[str]).
Block = str | list[str]


class LegalDoc(StrEnum):
    TERMS = "terms"
    PRIVACY = "privacy"


@dataclass(frozen=True)
class Section:
    heading: str
    blocks: list[Block]


@dataclass(frozen=True)
class Document:
    doc: LegalDoc
    title: str
    version: str
    effective_date: str
    summary: str
    sections: list[Section]

    def as_json(self) -> dict:
        return {
            "doc": self.doc.value,
            "title": self.title,
            "version": self.version,
            "effective_date": self.effective_date,
            "summary": self.summary,
            "sections": [
                {
                    "heading": s.heading,
                    "blocks": [
                        {"type": "list", "items": b} if isinstance(b, list) else {"type": "paragraph", "text": b}
                        for b in s.blocks
                    ],
                }
                for s in self.sections
            ],
        }


def _pct(rate: Decimal) -> str:
    return f"{(rate * 100).normalize():f}%"


def _money(amount: Decimal, currency: str) -> str:
    return f"₹{amount:,.2f}" if currency == "INR" else f"{currency} {amount:,.2f}"


def _contact(s: Settings) -> list[Block]:
    grievance = s.grievance_officer_email or s.support_email
    return [
        f"{s.legal_entity_name}, {s.legal_address}.",
        [
            f"Support: {s.support_email}, or Account → Contact support in the app.",
            f"Grievance Officer: {s.grievance_officer_name}, {grievance}. We acknowledge grievances within "
            "24 hours and resolve them within 15 days.",
        ],
    ]


def terms(s: Settings, r: PlatformRules) -> Document:
    app = s.app_name
    fee = _money(r.overstay_block_fee, r.currency)
    return Document(
        doc=LegalDoc.TERMS,
        title="Terms of Service",
        version=VERSION,
        effective_date=EFFECTIVE_DATE,
        summary=(
            f"{app} connects drivers with people and businesses who have parking to spare. Hosts own and run "
            "their spaces; we run the app, take bookings and handle payments. Book honestly, park within your "
            "time, and treat every space with care."
        ),
        sections=[
            Section(
                "1. Who we are and these terms",
                [
                    f'These Terms are a contract between you and {s.legal_entity_name} ("{app}", "we", "us") '
                    f"for using the {app} mobile app, website and services. By creating an account or making or "
                    "accepting a booking, you agree to them and to our Privacy Policy.",
                    "We may update these Terms. If a change is material we will tell you in the app or by email "
                    "before it takes effect; continuing to use the app afterwards means you accept the new Terms.",
                ],
            ),
            Section(
                "2. Our role",
                [
                    f"{app} is a marketplace and an intermediary under the Information Technology Act, 2000. "
                    "Parking spaces are listed and operated by independent hosts. We do not own, inspect or "
                    "control them, and we are not a party to the arrangement between driver and host except "
                    "as the platform that takes the booking and processes the payment.",
                    "Listing details (location, photos, amenities, opening hours) come from hosts. We may remove "
                    "listings that break these Terms but we do not guarantee their accuracy.",
                ],
            ),
            Section(
                "3. Your account",
                [
                    [
                        "You must be at least 18 years old and able to enter a binding contract.",
                        "Give accurate details and keep them current. Verify your email to make bookings.",
                        "Keep your password private. You are responsible for activity on your account.",
                        "One person, one account. Accounts are not transferable.",
                    ],
                    "You can delete your account at any time in Account → Delete account (see section 12).",
                ],
            ),
            Section(
                "4. Bookings",
                [
                    [
                        "A booking reserves one parking slot for the time window shown. The price, taxes and any "
                        "fees are shown before you confirm and are calculated by us, not the host.",
                        "Some hosts approve requests manually. A request is not a booking until the host accepts "
                        "it; unanswered requests expire automatically and you are not charged.",
                        "Online bookings must be paid within the hold time shown, or the slot is released.",
                        "Your access PIN and QR code are personal and single-use. Do not share them. QR codes "
                        "refresh every few minutes for your security.",
                        "Use the slot only for the vehicle and the time you booked. Check in no earlier than "
                        f"{r.early_checkin_minutes} minutes before your start time.",
                    ],
                ],
            ),
            Section(
                "5. Prices, taxes and payment",
                [
                    f"Prices include the host's rate plus GST at {_pct(r.gst_rate)} where applicable. {app} keeps "
                    f"a service commission from the host's earnings ({_pct(r.commission_rate_private)} for private "
                    f"hosts, {_pct(r.commission_rate_commercial)} for commercial operators); drivers do not pay it "
                    "on top.",
                    "Online payments are processed by our payment partner (Razorpay). We never see or store your "
                    'full card, UPI or bank details. Where a listing is marked "pay at venue" you pay the host '
                    "directly the amount shown in the app.",
                ],
            ),
            Section(
                "6. Cancellations and refunds",
                [
                    [
                        f"Free cancellation: cancel at least {r.free_cancellation_minutes} minutes before your "
                        "start time for a full refund.",
                        f"Late cancellation: after that, a fee of {_pct(r.late_cancellation_fee_rate)} of the "
                        "booking price (before tax) applies and the rest is refunded.",
                        "If a host rejects or cancels your booking, or the space is unavailable when you arrive, "
                        "you get a full refund. Report it in the app so we can act on the host's account.",
                        "Refunds go back to the original payment method, usually within 5–7 business days "
                        "depending on your bank.",
                    ],
                ],
            ),
            Section(
                "7. Overstays",
                [
                    f"Please leave by your end time. After a {r.overstay_grace_minutes}-minute grace period, "
                    f"overstay is charged at {fee} (plus GST) for every started {r.overstay_block_minutes}-minute "
                    "block, added to your booking total. Repeated overstays can lead to suspension.",
                ],
            ),
            Section(
                "8. Hosts",
                [
                    "If you list a space you confirm that:",
                    [
                        "you own the space or have permission (from a landlord, society or RWA) to let it;",
                        "your listing is accurate, including location, photos, hours and restrictions;",
                        "the space is safe and available for every booking you accept;",
                        "you comply with local laws, building rules and tax obligations on your earnings;",
                        "you verify drivers using the in-app PIN or QR check and do not charge extra off-app.",
                    ],
                    "Payouts are the booking amount minus our commission and any refunds. We may hold payouts "
                    "while a dispute about the booking is open.",
                ],
            ),
            Section(
                "9. Acceptable use",
                [
                    "You must not:",
                    [
                        "list a space you are not entitled to let, or create fake listings, bookings or reviews;",
                        "use a space for anything other than parking a lawful, roadworthy vehicle;",
                        "leave hazardous materials or park an unregistered or uninsured vehicle;",
                        "harass, threaten or discriminate against other users;",
                        "arrange or pay for bookings outside the app to avoid fees;",
                        "scrape, reverse-engineer, overload or try to break the security of the app or API.",
                    ],
                ],
            ),
            Section(
                "10. Vehicles, safety and liability",
                [
                    "You park at your own risk. Hosts provide space, not vehicle custody. Neither the host nor "
                    f"{app} is responsible for theft of or damage to your vehicle or belongings unless caused by "
                    "their negligence. Keep your vehicle locked and insured as the law requires.",
                    f"To the extent the law allows, {app}'s total liability to you for any claim is limited to the "
                    "fees you paid us in the three months before the claim. Nothing in these Terms limits "
                    "liability that cannot be limited by law, including your rights under the Consumer "
                    "Protection Act, 2019.",
                ],
            ),
            Section(
                "11. Problems and disputes",
                [
                    "If something goes wrong (blocked slot, damage, wrong charge), use Report a problem on the "
                    "booking with photos as soon as you can. We review the evidence from both sides and decide "
                    "refunds or fees fairly. You can also contact support or our Grievance Officer (section 14).",
                ],
            ),
            Section(
                "12. Suspension and account deletion",
                [
                    "We may suspend or close accounts that break these Terms, put others at risk or are used for "
                    "fraud. Where possible we tell you why and let you respond.",
                    "You can delete your account in the app. Active bookings must finish or be cancelled first. "
                    "Deleting your account removes your personal details; records we must keep by law are "
                    "anonymised as described in the Privacy Policy.",
                ],
            ),
            Section(
                "13. Governing law",
                [
                    "These Terms are governed by the laws of India. Courts in Bengaluru, Karnataka have "
                    "jurisdiction, without affecting your right to approach a consumer forum where you live.",
                ],
            ),
            Section("14. Contact", _contact(s)),
        ],
    )


def privacy(s: Settings, r: PlatformRules) -> Document:
    app = s.app_name
    return Document(
        doc=LegalDoc.PRIVACY,
        title="Privacy Policy",
        version=VERSION,
        effective_date=EFFECTIVE_DATE,
        summary=(
            "We collect only what we need to run bookings: your account details, your bookings and payments "
            "status, and what hosts and drivers upload. We don't sell your data, we don't store your location, "
            "and you can delete your account from the app at any time."
        ),
        sections=[
            Section(
                "1. About this policy",
                [
                    f'This policy explains how {s.legal_entity_name} ("{app}") processes personal data when you '
                    f"use the {app} app and services. We are the Data Fiduciary under India's Digital Personal "
                    "Data Protection Act, 2023 (DPDP Act).",
                ],
            ),
            Section(
                "2. What we collect",
                [
                    [
                        "Account: name, email address, optional phone number, and your password, which we store "
                        "only as a one-way Argon2 hash.",
                        "Bookings: listing, slot, times, optional vehicle number, check-in and check-out times, "
                        "amounts, cancellations and overstay charges.",
                        "Payments: payment status and the payment partner's order and payment IDs. Card, UPI and "
                        "bank details go directly to Razorpay and never reach our servers.",
                        "Hosts: listing address and map coordinates, photos, prices, opening hours and access "
                        "instructions.",
                        "Uploads and reports: photos you add to listings or problem reports, and what you write "
                        "in reports and support requests.",
                        "Device: a push notification token if you allow notifications, and basic technical "
                        "information (app version, IP address, request logs) used for security.",
                    ],
                    "Location: when you search, your phone sends its approximate position to find nearby "
                    "parking. We use it for that search only and do not store it or link it to your account.",
                ],
            ),
            Section(
                "3. Why we use it",
                [
                    [
                        "To create and secure your account, and to verify your email.",
                        "To take bookings, issue access PINs and QR codes, and calculate prices, fees and taxes.",
                        "To process payments and refunds and keep the financial records the law requires.",
                        "To send booking updates, receipts and reminders by email and push. You can turn off "
                        "push notifications in your phone's settings, or ask support to stop non-essential emails.",
                        "To handle support requests, disputes and fraud, and to keep the service secure.",
                    ],
                    "We process this data to perform the service you asked for, with your consent (which you can "
                    "withdraw), and where the law requires us to. We do not sell personal data, show third-party "
                    "ads or use your data for automated decisions with legal effects.",
                ],
            ),
            Section(
                "4. Who we share it with",
                [
                    [
                        "The other party to your booking: hosts see the driver's name, phone number (if given) "
                        "and vehicle number; once a booking is confirmed, drivers see the host's name, phone "
                        "number (if given), the address and access instructions.",
                        "Service providers who process data for us under contract: Neon (database hosting), "
                        "Redis Cloud (caching), Backblaze (photo storage), Resend (email), Expo (push "
                        "notifications), Razorpay (payments) and, if enabled, Sentry (error reports).",
                        "Authorities, when required by law or to protect someone's safety.",
                    ],
                    "Some providers store data outside India (mainly the United States). We transfer data only "
                    "to countries the Government of India has not restricted, under contracts that protect it.",
                ],
            ),
            Section(
                "5. How long we keep it",
                [
                    [
                        "Account data: while your account is open.",
                        "Booking, payment and ledger records: as long as tax and accounting law requires "
                        "(typically up to 8 years). After account deletion they no longer identify you.",
                        "Sign-in sessions expire after 30 days; email codes after "
                        f"{s.verification_code_ttl_minutes} minutes; expired ones are purged daily.",
                        f"Photos uploaded but never used are deleted after {s.stale_upload_hours} hours.",
                    ],
                ],
            ),
            Section(
                "6. Deleting your account",
                [
                    "Go to Account → Delete account and confirm with your password. Active bookings must finish "
                    "or be cancelled first. We then immediately:",
                    [
                        "replace your name, email and phone number with anonymous placeholders and remove your "
                        "password, so you can no longer sign in;",
                        "sign you out on every device and delete your push notification tokens;",
                        "unpublish any parking spaces you host;",
                        "email you a confirmation.",
                    ],
                    "The same email address can be used to register again afterwards.",
                ],
            ),
            Section(
                "7. Your rights",
                [
                    "Under the DPDP Act you can:",
                    [
                        "access a summary of the personal data we hold about you;",
                        "correct or update it (Account → Edit profile);",
                        "erase it (Account → Delete account);",
                        "withdraw consent, for example to notifications;",
                        "nominate someone to exercise your rights if you die or become incapacitated;",
                        "raise a grievance with us, and then with the Data Protection Board of India.",
                    ],
                    "To exercise a right, use Contact support in the app or email us. We may need to verify "
                    "your identity first.",
                ],
            ),
            Section(
                "8. Security",
                [
                    "Data is encrypted in transit (HTTPS/TLS). Passwords are hashed with Argon2, access codes are "
                    "signed and short-lived, sign-in sessions can be revoked, and access to production systems "
                    "is restricted. No system is perfectly secure; if a breach affects you we will notify you "
                    "and the Data Protection Board as the law requires.",
                ],
            ),
            Section(
                "9. Children",
                [
                    f"{app} is for people aged 18 and over. We do not knowingly process children's data; if you "
                    "believe a child has an account, contact us and we will delete it.",
                ],
            ),
            Section(
                "10. Changes",
                [
                    "If we change this policy materially we will tell you in the app or by email before the "
                    "change takes effect. The version and date at the top show the current policy.",
                ],
            ),
            Section("11. Contact and grievances", _contact(s)),
        ],
    )


def build(doc: LegalDoc, settings: Settings, rules: PlatformRules) -> Document:
    return (terms if doc is LegalDoc.TERMS else privacy)(settings, rules)
