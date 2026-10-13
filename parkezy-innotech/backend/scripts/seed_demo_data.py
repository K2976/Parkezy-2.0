"""Seed rich, realistic demo data for Parkezy.

Creates:
- Demo accounts:
  * demo@parkezy.com / Password123! (Driver + Host with active/upcoming bookings & listings)
  * host@parkezy.com / Password123! (Dedicated Host)
  * driver@parkezy.com / Password123! (Dedicated Driver)
  * 10 other community users
- 220 realistic listings across Bengaluru neighborhoods (Indiranagar, Koramangala, HSR, MG Road, Whitefield, etc.)
- 800+ slots with standard, compact, EV, large, bike types
- 80+ bookings (active sessions, upcoming, completed, pending approval)
- Notifications for the demo user
"""

import asyncio
import random
import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import Range

from app.core.config import get_settings
from app.core.security import PasswordHasher
from app.db.models import Booking, Listing, Notification, Slot, User
from app.db.session import create_engine, create_session_factory
from app.domain.enums import Amenity, BookingStatus, ListingKind, ListingStatus, SlotType

# Bengaluru Locality Templates
LOCALITIES = [
    {
        "name": "Indiranagar 100 Feet Road",
        "lat": 12.9719,
        "lng": 77.6412,
        "city": "Bengaluru",
        "pin": "560038",
        "kinds": ["commercial", "private"],
        "prefixes": ["100 Feet Hub", "Defence Colony Bay", "CMH Road Spot", "HAL 2nd Stage Driveway", "Indiranagar Metro"],
    },
    {
        "name": "Koramangala 5th Block",
        "lat": 12.9352,
        "lng": 77.6245,
        "city": "Bengaluru",
        "pin": "560095",
        "kinds": ["private", "commercial"],
        "prefixes": ["Sony World Corner", "Koramangala Club Bay", "80 Feet Road Stand", "Jyoti Nivas Parking", "Forum Mall Lane"],
    },
    {
        "name": "HSR Layout Sector 1 & 2",
        "lat": 12.9121,
        "lng": 77.6446,
        "city": "Bengaluru",
        "pin": "560102",
        "kinds": ["private", "private", "commercial"],
        "prefixes": ["27th Main HSR Bay", "Sector 2 Villa Parking", "HSR BDA Complex Slot", "19th Main Driveway", "Agara Lake Stand"],
    },
    {
        "name": "MG Road & Church Street",
        "lat": 12.9756,
        "lng": 77.6066,
        "city": "Bengaluru",
        "pin": "560001",
        "kinds": ["commercial", "commercial", "private"],
        "prefixes": ["Church Street Plaza", "Brigade Road Safe Spot", "MG Road Metro Bay", "Lavelle Road Basement", "Residency Road Hub"],
    },
    {
        "name": "Whitefield ITPL",
        "lat": 12.9863,
        "lng": 77.7341,
        "city": "Bengaluru",
        "pin": "560066",
        "kinds": ["commercial", "private"],
        "prefixes": ["ITPL TechPark Bay", "Hope Farm Junction Slot", "ECC Road Safe Driveway", "Prestige Shantiniketan Gate", "Brookefield Stand"],
    },
    {
        "name": "Electronic City Phase 1",
        "lat": 12.8452,
        "lng": 77.6602,
        "city": "Bengaluru",
        "pin": "560100",
        "kinds": ["commercial", "private"],
        "prefixes": ["Infosys Gate 1 Slot", "Wipro Junction Bay", "Velankani Driveway", "E-City Elevated Stand", "NeoTown Parking"],
    },
    {
        "name": "Jayanagar 4th Block",
        "lat": 12.9298,
        "lng": 77.5838,
        "city": "Bengaluru",
        "pin": "560011",
        "kinds": ["private", "commercial"],
        "prefixes": ["Jayanagar Shopping Complex", "South End Circle Spot", "Ashoka Pillar Driveway", "9th Block Metro Bay", "Cool Joint Stand"],
    },
    {
        "name": "Malleshwaram 8th Cross",
        "lat": 12.9982,
        "lng": 77.5704,
        "city": "Bengaluru",
        "pin": "560003",
        "kinds": ["private", "commercial"],
        "prefixes": ["Sampige Road Bay", "Margosa Heritage Driveway", "CTR Corner Spot", "18th Cross Malleshwaram", "Kadu Malleshwara Bay"],
    },
    {
        "name": "Bellandur & Outer Ring Road",
        "lat": 12.9304,
        "lng": 77.6784,
        "city": "Bengaluru",
        "pin": "560103",
        "kinds": ["commercial", "commercial", "private"],
        "prefixes": ["EcoSpace Tech Gateway", "EcoWorld Visitor Deck", "Central Mall Bay", "Green Glen Layout Slot", "Devarabisanahalli Stand"],
    },
    {
        "name": "BTM Layout 2nd Stage",
        "lat": 12.9166,
        "lng": 77.6101,
        "city": "Bengaluru",
        "pin": "560076",
        "kinds": ["private", "commercial"],
        "prefixes": ["Udupi Garden Bay", "BTM Lake View Spot", "Bannerghatta Link Slot", "7th Main BTM Driveway", "Mico Layout Stand"],
    },
]

PRIVATE_TITLES = [
    "Covered Villa Driveway with 24/7 CCTV",
    "Gated Independent House Parking with EV Charging",
    "Spacious Basement Slot near Main Road",
    "Secure Apartment Stilt Parking with Guard",
    "Safe Residential Driveway - SUV & Sedan Friendly",
    "Dedicated Private Bay with Wide Gate",
    "Tree-Shaded Safe Porch Parking",
    "Quiet Lane Dedicated Driveway with Night Lights",
]

COMMERCIAL_TITLES = [
    "Multi-Level Covered Parking Complex",
    "Plaza Visitor Underground Parking",
    "Commercial Mall Valet-Assisted Parking",
    "Tech Park Multi-Floor EV-Ready Facility",
    "Central Metro Station Commuter Deck",
    "Premium Secured Commercial Lot",
    "Retail Arcade High-Clearance Parking",
    "Corporate Tower Dedicated Visitor Bays",
]

AMENITIES_LIST = [
    Amenity.COVERED.value,
    Amenity.CCTV.value,
    Amenity.SECURITY_GUARD.value,
    Amenity.EV_CHARGING.value,
    Amenity.WELL_LIT.value,
    Amenity.GATED.value,
    Amenity.WHEELCHAIR_ACCESS.value,
    Amenity.RESTROOM.value,
]


async def seed():
    settings = get_settings()
    engine = create_engine(settings, pooled=False)
    sf = create_session_factory(engine)
    hasher = PasswordHasher()
    hashed_pwd = hasher.hash("Password123!")

    now = datetime.now(UTC)

    async with sf() as session:
        print("🌱 Seeding Demo Users...")

        # 1. Primary Demo Account (Driver + Host)
        demo_user = (await session.execute(select(User).where(User.email == "demo@parkezy.com"))).scalar_one_or_none()
        if not demo_user:
            demo_user = User(
                id=uuid.uuid4(),
                email="demo@parkezy.com",
                password_hash=hashed_pwd,
                full_name="Honours Bhadauria",
                phone="+919876543210",
                email_verified_at=now,
                is_host=True,
                is_commercial_host=True,
                is_admin=True,
                status="active",
            )
            session.add(demo_user)
        else:
            demo_user.password_hash = hashed_pwd
            demo_user.email_verified_at = now
            demo_user.is_host = True
            demo_user.is_commercial_host = True

        # 2. Dedicated Host Account
        host_user = (await session.execute(select(User).where(User.email == "host@parkezy.com"))).scalar_one_or_none()
        if not host_user:
            host_user = User(
                id=uuid.uuid4(),
                email="host@parkezy.com",
                password_hash=hashed_pwd,
                full_name="Bengaluru Parking Services",
                phone="+919876543211",
                email_verified_at=now,
                is_host=True,
                is_commercial_host=True,
                status="active",
            )
            session.add(host_user)
        else:
            host_user.password_hash = hashed_pwd
            host_user.email_verified_at = now

        # 3. Dedicated Driver Account
        driver_user = (await session.execute(select(User).where(User.email == "driver@parkezy.com"))).scalar_one_or_none()
        if not driver_user:
            driver_user = User(
                id=uuid.uuid4(),
                email="driver@parkezy.com",
                password_hash=hashed_pwd,
                full_name="Rajesh Sharma",
                phone="+919876543212",
                email_verified_at=now,
                is_host=False,
                status="active",
            )
            session.add(driver_user)
        else:
            driver_user.password_hash = hashed_pwd
            driver_user.email_verified_at = now

        # 4. Other community hosts & drivers
        community_names = [
            ("Priya Nair", "priya@parkezy.com"),
            ("Arjun Mehta", "arjun@parkezy.com"),
            ("Vikram Rao", "vikram@parkezy.com"),
            ("Sneha Reddy", "sneha@parkezy.com"),
            ("Kavita Joshi", "kavita@parkezy.com"),
            ("Rohan Gupta", "rohan@parkezy.com"),
            ("Ananya Das", "ananya@parkezy.com"),
            ("Suresh Kumar", "suresh@parkezy.com"),
        ]
        community_users = []
        for name, email in community_names:
            u = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if not u:
                u = User(
                    id=uuid.uuid4(),
                    email=email,
                    password_hash=hashed_pwd,
                    full_name=name,
                    phone=f"+9198{random.randint(10000000, 99999999)}",
                    email_verified_at=now,
                    is_host=True,
                    status="active",
                )
                session.add(u)
            community_users.append(u)

        await session.flush()
        print(f"✅ Users ready: Demo User ({demo_user.id})")

        # Clean existing mock listings to seed fresh 220+ listings
        existing_count = (await session.execute(text("SELECT count(*) FROM listings"))).scalar()
        if existing_count < 200:
            print(f"📦 Generating 220 full-loop listings across Bengaluru (current: {existing_count})...")
            
            all_hosts = [demo_user, host_user] + community_users
            demo_listings = []
            all_seeded_listings = []
            all_seeded_slots = []

            for i in range(220):
                # Pick locality
                loc = LOCALITIES[i % len(LOCALITIES)]
                # First 15 listings go to demo_user so Host tab is rich
                if i < 15:
                    owner = demo_user
                elif i < 35:
                    owner = host_user
                else:
                    owner = random.choice(all_hosts)

                kind = random.choice(loc["kinds"])
                prefix = random.choice(loc["prefixes"])
                title_template = random.choice(COMMERCIAL_TITLES if kind == "commercial" else PRIVATE_TITLES)
                title = f"{prefix}: {title_template}"

                # Add tiny geographic jitter around the neighborhood center
                lat = loc["lat"] + random.uniform(-0.018, 0.018)
                lng = loc["lng"] + random.uniform(-0.018, 0.018)

                hourly_rate = Decimal(str(random.choice([20, 30, 40, 50, 60, 75, 90, 120])))
                daily_cap = Decimal(str(int(hourly_rate * random.choice([5, 6, 7, 8])))) if random.random() < 0.7 else None
                is_24h = random.random() < 0.75
                open_t = None if is_24h else time(random.choice([6, 7, 8]), 0)
                close_t = None if is_24h else time(random.choice([21, 22, 23]), 0)

                # Pick 3 to 7 amenities
                amenity_count = random.randint(3, 6)
                amenities = random.sample(AMENITIES_LIST, amenity_count)
                if kind == "commercial" and Amenity.CCTV.value not in amenities:
                    amenities.append(Amenity.CCTV.value)

                rating_avg = Decimal(str(round(random.uniform(4.2, 5.0), 2)))
                rating_count = random.randint(6, 95)

                listing = Listing(
                    id=uuid.uuid4(),
                    owner_id=owner.id,
                    kind=kind,
                    status=ListingStatus.ACTIVE.value,
                    title=title,
                    description=f"Well-maintained, highly accessible parking in {loc['name']}. Gate clearance 2.2m. 24/7 security surveillance and fast access.",
                    access_instructions="Approach the security gate and show your Parkezy booking pass on your phone.",
                    address_line=f"{random.randint(10, 890)}, {loc['name']}",
                    city=loc["city"],
                    postal_code=loc["pin"],
                    latitude=lat,
                    longitude=lng,
                    timezone="Asia/Kolkata",
                    amenities=amenities,
                    hourly_rate=hourly_rate,
                    daily_cap=daily_cap,
                    currency="INR",
                    auto_accept=random.random() < 0.65,
                    is_24h=is_24h,
                    open_time=open_t,
                    close_time=close_t,
                    open_days=[1, 2, 3, 4, 5, 6, 7],
                    rating_avg=rating_avg,
                    rating_count=rating_count,
                )
                session.add(listing)
                all_seeded_listings.append(listing)
                if owner.id == demo_user.id:
                    demo_listings.append(listing)

                # Create 2 to 6 slots per listing
                num_slots = random.randint(2, 6) if kind == "private" else random.randint(4, 10)
                for s_idx in range(num_slots):
                    slot_type = SlotType.STANDARD.value
                    if s_idx == 0 and Amenity.EV_CHARGING.value in amenities:
                        slot_type = SlotType.EV.value
                    elif s_idx == 1:
                        slot_type = random.choice([SlotType.COMPACT.value, SlotType.LARGE.value])
                    elif s_idx > 3:
                        slot_type = random.choice([SlotType.BIKE.value, SlotType.ACCESSIBLE.value, SlotType.STANDARD.value])

                    label = f"P-{s_idx + 1}" if kind == "commercial" else f"Slot {chr(65 + s_idx)}"
                    floor = random.choice(["B1", "B2", "Ground"]) if kind == "commercial" else None

                    slot = Slot(
                        id=uuid.uuid4(),
                        listing_id=listing.id,
                        label=label,
                        floor=floor,
                        slot_type=slot_type,
                        hourly_rate_override=None,
                        is_active=True,
                    )
                    session.add(slot)
                    all_seeded_slots.append(slot)

            await session.flush()
            print(f"✅ Created {len(all_seeded_listings)} listings and {len(all_seeded_slots)} slots!")

            # -----------------------------------------------------------------
            # Seed Rich Bookings for Demo User
            # -----------------------------------------------------------------
            print("🚗 Creating realistic bookings for demo user...")
            
            # Booking 1: ACTIVE RIGHT NOW (Checked In) for demo_user as Driver
            active_listing = all_seeded_listings[20]
            active_slot = (await session.execute(select(Slot).where(Slot.listing_id == active_listing.id))).scalars().first()
            if active_slot:
                period_start = now - timedelta(minutes=45)
                period_end = now + timedelta(hours=2, minutes=15)
                hourly = active_listing.hourly_rate
                subtotal = hourly * Decimal("3")
                tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
                total = subtotal + tax

                b1 = Booking(
                    id=uuid.uuid4(),
                    driver_id=demo_user.id,
                    host_id=active_listing.owner_id,
                    listing_id=active_listing.id,
                    slot_id=active_slot.id,
                    period=Range(period_start, period_end),
                    status=BookingStatus.CHECKED_IN.value,
                    payment_mode="pay_at_venue",
                    vehicle_number="KA-01-MJ-4040",
                    idempotency_key=uuid.uuid4().hex,
                    currency="INR",
                    hourly_rate=hourly,
                    subtotal=subtotal,
                    tax_amount=tax,
                    platform_fee=(subtotal * Decimal("0.15")).quantize(Decimal("0.01")),
                    total_amount=total,
                    tax_rate=Decimal("0.18"),
                    commission_rate=Decimal("0.15"),
                    checked_in_at=period_start + timedelta(minutes=5),
                    approved_at=period_start - timedelta(minutes=10),
                )
                session.add(b1)

            # Booking 2: UPCOMING CONFIRMED for demo_user as Driver
            up_listing = all_seeded_listings[22]
            up_slot = (await session.execute(select(Slot).where(Slot.listing_id == up_listing.id))).scalars().first()
            if up_slot:
                up_start = now + timedelta(days=1, hours=2)
                up_end = up_start + timedelta(hours=3)
                hourly = up_listing.hourly_rate
                subtotal = hourly * Decimal("3")
                tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
                total = subtotal + tax

                b2 = Booking(
                    id=uuid.uuid4(),
                    driver_id=demo_user.id,
                    host_id=up_listing.owner_id,
                    listing_id=up_listing.id,
                    slot_id=up_slot.id,
                    period=Range(up_start, up_end),
                    status=BookingStatus.CONFIRMED.value,
                    payment_mode="pay_at_venue",
                    vehicle_number="KA-01-MJ-4040",
                    idempotency_key=uuid.uuid4().hex,
                    currency="INR",
                    hourly_rate=hourly,
                    subtotal=subtotal,
                    tax_amount=tax,
                    platform_fee=(subtotal * Decimal("0.15")).quantize(Decimal("0.01")),
                    total_amount=total,
                    tax_rate=Decimal("0.18"),
                    commission_rate=Decimal("0.15"),
                    approved_at=now - timedelta(hours=1),
                )
                session.add(b2)

            # Booking 3: COMPLETED PAST BOOKING for demo_user as Driver
            past_listing = all_seeded_listings[24]
            past_slot = (await session.execute(select(Slot).where(Slot.listing_id == past_listing.id))).scalars().first()
            if past_slot:
                past_start = now - timedelta(days=2, hours=3)
                past_end = past_start + timedelta(hours=2)
                hourly = past_listing.hourly_rate
                subtotal = hourly * Decimal("2")
                tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
                total = subtotal + tax

                b3 = Booking(
                    id=uuid.uuid4(),
                    driver_id=demo_user.id,
                    host_id=past_listing.owner_id,
                    listing_id=past_listing.id,
                    slot_id=past_slot.id,
                    period=Range(past_start, past_end),
                    status=BookingStatus.COMPLETED.value,
                    payment_mode="pay_at_venue",
                    vehicle_number="KA-01-MJ-4040",
                    idempotency_key=uuid.uuid4().hex,
                    currency="INR",
                    hourly_rate=hourly,
                    subtotal=subtotal,
                    tax_amount=tax,
                    platform_fee=(subtotal * Decimal("0.15")).quantize(Decimal("0.01")),
                    total_amount=total,
                    final_amount=total,
                    tax_rate=Decimal("0.18"),
                    commission_rate=Decimal("0.15"),
                    checked_in_at=past_start,
                    checked_out_at=past_end,
                )
                session.add(b3)

            # Host Bookings on demo_user's listings
            if demo_listings:
                host_listing = demo_listings[0]
                host_slots = (await session.execute(select(Slot).where(Slot.listing_id == host_listing.id))).scalars().all()
                if len(host_slots) >= 2:
                    # 1 parked guest right now
                    guest_driver = community_users[0]
                    p_start = now - timedelta(minutes=30)
                    p_end = now + timedelta(hours=3)
                    hb1 = Booking(
                        id=uuid.uuid4(),
                        driver_id=guest_driver.id,
                        host_id=demo_user.id,
                        listing_id=host_listing.id,
                        slot_id=host_slots[0].id,
                        period=Range(p_start, p_end),
                        status=BookingStatus.CHECKED_IN.value,
                        payment_mode="pay_at_venue",
                        vehicle_number="KA-03-AB-1234",
                        idempotency_key=uuid.uuid4().hex,
                        currency="INR",
                        hourly_rate=host_listing.hourly_rate,
                        subtotal=host_listing.hourly_rate * Decimal("3.5"),
                        tax_amount=(host_listing.hourly_rate * Decimal("3.5") * Decimal("0.18")).quantize(Decimal("0.01")),
                        platform_fee=(host_listing.hourly_rate * Decimal("3.5") * Decimal("0.15")).quantize(Decimal("0.01")),
                        total_amount=(host_listing.hourly_rate * Decimal("3.5") * Decimal("1.18")).quantize(Decimal("0.01")),
                        tax_rate=Decimal("0.18"),
                        commission_rate=Decimal("0.15"),
                        checked_in_at=p_start + timedelta(minutes=2),
                    )
                    session.add(hb1)

                    # 1 pending approval request for demo_user to review
                    guest_driver2 = community_users[1]
                    req_start = now + timedelta(hours=4)
                    req_end = req_start + timedelta(hours=2)
                    hb2 = Booking(
                        id=uuid.uuid4(),
                        driver_id=guest_driver2.id,
                        host_id=demo_user.id,
                        listing_id=host_listing.id,
                        slot_id=host_slots[1].id,
                        period=Range(req_start, req_end),
                        status=BookingStatus.PENDING_APPROVAL.value,
                        payment_mode="pay_at_venue",
                        vehicle_number="KA-05-XY-9999",
                        idempotency_key=uuid.uuid4().hex,
                        currency="INR",
                        hourly_rate=host_listing.hourly_rate,
                        subtotal=host_listing.hourly_rate * Decimal("2"),
                        tax_amount=(host_listing.hourly_rate * Decimal("2") * Decimal("0.18")).quantize(Decimal("0.01")),
                        platform_fee=(host_listing.hourly_rate * Decimal("2") * Decimal("0.15")).quantize(Decimal("0.01")),
                        total_amount=(host_listing.hourly_rate * Decimal("2") * Decimal("1.18")).quantize(Decimal("0.01")),
                        tax_rate=Decimal("0.18"),
                        commission_rate=Decimal("0.15"),
                        approval_expires_at=now + timedelta(minutes=30),
                    )
                    session.add(hb2)

            # Notifications for demo_user
            notifs = [
                Notification(
                    id=uuid.uuid4(),
                    user_id=demo_user.id,
                    type="booking_request",
                    title="New Booking Request!",
                    body="Priya Nair requested to book Slot B for today at 04:00 PM.",
                    data={"type": "request"},
                    created_at=now - timedelta(minutes=15),
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=demo_user.id,
                    type="session",
                    title="Active Session Running",
                    body="Your parking session at Indiranagar 100 Feet Hub is active.",
                    data={"type": "active"},
                    created_at=now - timedelta(minutes=45),
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=demo_user.id,
                    type="receipt",
                    title="Payment Settled",
                    body="Received ₹141.60 for your completed parking booking.",
                    data={"type": "payout"},
                    created_at=now - timedelta(days=2),
                ),
            ]
            for n in notifs:
                session.add(n)

            await session.commit()
            print("🎉 Full seed successfully committed!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
