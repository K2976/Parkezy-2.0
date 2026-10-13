"""Seed 200+ listings across Delhi NCR / Ghaziabad / Noida / Gurugram.
Ensures that users testing from Delhi NCR / Ghaziabad immediately see 200+ spots around them!
"""

import asyncio
import random
import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Range

from app.core.config import get_settings
from app.db.models import Booking, Listing, Slot, User
from app.db.session import create_engine, create_session_factory
from app.domain.enums import Amenity, BookingStatus, ListingStatus, SlotType

NCR_LOCALITIES = [
    {
        "name": "Indirapuram & Vaishali",
        "lat": 28.6412,
        "lng": 77.3712,
        "city": "Ghaziabad",
        "pin": "201014",
        "kinds": ["private", "commercial"],
        "prefixes": ["Shipra Mall Hub", "Kala Pathar Road Bay", "Vaishali Metro Spot", "Ahinsa Khand Driveway", "Indirapuram Gated Bay"],
    },
    {
        "name": "Noida Sector 18 & Atta Market",
        "lat": 28.5708,
        "lng": 77.3260,
        "city": "Noida",
        "pin": "201301",
        "kinds": ["commercial", "commercial", "private"],
        "prefixes": ["Wave Mall Deck", "DLF Mall of India Bay", "Atta Market Shoppers Spot", "Sector 18 Metro Stand", "CentreStage Parking"],
    },
    {
        "name": "Noida Sector 62 Tech Zone",
        "lat": 28.6280,
        "lng": 77.3649,
        "city": "Noida",
        "pin": "201309",
        "kinds": ["commercial", "private"],
        "prefixes": ["Logix Cyber Park Bay", "Sector 62 Metro Deck", "C-DAC Gate Stand", "I-Thum Tower Parking", "Stellar IT Park Bay"],
    },
    {
        "name": "Connaught Place (CP)",
        "lat": 28.6315,
        "lng": 77.2167,
        "city": "New Delhi",
        "pin": "110001",
        "kinds": ["commercial", "commercial", "private"],
        "prefixes": ["Inner Circle Multi-Level", "Outer Circle Safe Bay", "Janpath Shoppers Deck", "Barakhamba Metro Stand", "Palika Parking Hub"],
    },
    {
        "name": "Cyber City & DLF Phase 2",
        "lat": 28.4950,
        "lng": 77.0895,
        "city": "Gurugram",
        "pin": "122002",
        "kinds": ["commercial", "private"],
        "prefixes": ["Cyber Hub Valet Deck", "DLF Phase 2 Villa Bay", "Rapid Metro Stand", "Building 10 Visitor Parking", "Horizon Center Deck"],
    },
    {
        "name": "Vasundhara & Sahibabad",
        "lat": 28.6612,
        "lng": 77.3572,
        "city": "Ghaziabad",
        "pin": "201012",
        "kinds": ["private", "commercial"],
        "prefixes": ["Vasundhara Sector 14 Bay", "Mohan Nagar Metro Stand", "Sahibabad Industrial Deck", "Atal Chowk Safe Spot", "Prahlad Garhi Bay"],
    },
    {
        "name": "Raj Nagar Extension & RDC",
        "lat": 28.6822,
        "lng": 77.4272,
        "city": "Ghaziabad",
        "pin": "201002",
        "kinds": ["commercial", "private"],
        "prefixes": ["RDC Commercial Hub", "Raj Nagar Gated Bay", "NH-58 Commuter Deck", "Guldhar RRTS Stand", "ALT Centre Bay"],
    },
    {
        "name": "South Delhi Saket & Hauz Khas",
        "lat": 28.5245,
        "lng": 77.2066,
        "city": "New Delhi",
        "pin": "110017",
        "kinds": ["commercial", "private"],
        "prefixes": ["Select Citywalk Bay", "Saket District Centre Deck", "Hauz Khas Village Porch", "Malviya Nagar Stand", "IIT Delhi Gate Bay"],
    },
]

TITLES_PRIVATE = [
    "Covered Villa Driveway with 24/7 CCTV",
    "Gated Independent House Parking with EV Charging",
    "Spacious Basement Slot near Main Road",
    "Secure Apartment Stilt Parking with Guard",
    "Safe Residential Driveway - SUV & Sedan Friendly",
    "Dedicated Private Bay with Wide Gate",
    "Tree-Shaded Safe Porch Parking",
]

TITLES_COMMERCIAL = [
    "Multi-Level Covered Parking Complex",
    "Plaza Visitor Underground Parking",
    "Commercial Mall Valet-Assisted Parking",
    "Tech Park Multi-Floor EV-Ready Facility",
    "Central Metro Station Commuter Deck",
    "Premium Secured Commercial Lot",
]

AMENITIES = [
    Amenity.COVERED.value,
    Amenity.CCTV.value,
    Amenity.SECURITY_GUARD.value,
    Amenity.EV_CHARGING.value,
    Amenity.WELL_LIT.value,
    Amenity.GATED.value,
    Amenity.WHEELCHAIR_ACCESS.value,
]


async def seed_ncr():
    settings = get_settings()
    engine = create_engine(settings, pooled=False)
    sf = create_session_factory(engine)
    now = datetime.now(UTC)

    async with sf() as session:
        users = (await session.execute(select(User))).scalars().all()
        if not users:
            print("No users found! Run seed_demo_data.py first.")
            return

        demo_user = next((u for u in users if u.email == "demo@parkezy.com"), users[0])
        print(f"🌆 Seeding 200 Delhi NCR / Ghaziabad / Noida listings for user: {demo_user.email}...")

        created_listings = []
        created_slots = []

        for i in range(200):
            loc = NCR_LOCALITIES[i % len(NCR_LOCALITIES)]
            owner = demo_user if i < 15 else random.choice(users)
            kind = random.choice(loc["kinds"])
            prefix = random.choice(loc["prefixes"])
            tmpl = random.choice(TITLES_COMMERCIAL if kind == "commercial" else TITLES_PRIVATE)
            title = f"{prefix}: {tmpl}"

            lat = loc["lat"] + random.uniform(-0.02, 0.02)
            lng = loc["lng"] + random.uniform(-0.02, 0.02)

            hourly_rate = Decimal(str(random.choice([20, 30, 40, 50, 60, 80, 100])))
            daily_cap = Decimal(str(int(hourly_rate * random.choice([5, 6, 7])))) if random.random() < 0.7 else None
            is_24h = random.random() < 0.75
            open_t = None if is_24h else time(random.choice([6, 7, 8]), 0)
            close_t = None if is_24h else time(random.choice([21, 22, 23]), 0)

            amenities = random.sample(AMENITIES, random.randint(3, 5))
            if kind == "commercial" and Amenity.CCTV.value not in amenities:
                amenities.append(Amenity.CCTV.value)

            rating_avg = Decimal(str(round(random.uniform(4.3, 5.0), 2)))
            rating_count = random.randint(8, 88)

            listing = Listing(
                id=uuid.uuid4(),
                owner_id=owner.id,
                kind=kind,
                status=ListingStatus.ACTIVE.value,
                title=title,
                description=f"Spacious and convenient parking located in {loc['name']}. Gate security and easy access.",
                access_instructions="Show your Parkezy app booking pass at the boom barrier or gate security.",
                address_line=f"{random.randint(12, 940)}, {loc['name']}",
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
            created_listings.append(listing)

            num_slots = random.randint(2, 6) if kind == "private" else random.randint(4, 8)
            for s_idx in range(num_slots):
                slot_type = SlotType.STANDARD.value
                if s_idx == 0 and Amenity.EV_CHARGING.value in amenities:
                    slot_type = SlotType.EV.value
                elif s_idx == 1:
                    slot_type = SlotType.COMPACT.value
                elif s_idx > 3:
                    slot_type = SlotType.LARGE.value

                label = f"Bay {s_idx + 1}" if kind == "commercial" else f"Slot {chr(65 + s_idx)}"
                slot = Slot(
                    id=uuid.uuid4(),
                    listing_id=listing.id,
                    label=label,
                    floor="B1" if kind == "commercial" and s_idx % 2 == 0 else None,
                    slot_type=slot_type,
                    hourly_rate_override=None,
                    is_active=True,
                )
                session.add(slot)
                created_slots.append(slot)

        await session.flush()
        print(f"✅ Created {len(created_listings)} Delhi NCR listings and {len(created_slots)} slots!")

        # Add 1 active booking near Ghaziabad/Noida for demo_user so active pass works locally
        ncr_listing = created_listings[0]
        ncr_slot = next((s for s in created_slots if s.listing_id == ncr_listing.id), None)
        if ncr_slot:
            p_start = now - timedelta(minutes=25)
            p_end = now + timedelta(hours=2)
            hourly = ncr_listing.hourly_rate
            subtotal = hourly * Decimal("2")
            tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
            b = Booking(
                id=uuid.uuid4(),
                driver_id=demo_user.id,
                host_id=ncr_listing.owner_id,
                listing_id=ncr_listing.id,
                slot_id=ncr_slot.id,
                period=Range(p_start, p_end),
                status=BookingStatus.CHECKED_IN.value,
                payment_mode="pay_at_venue",
                vehicle_number="UP-14-CC-1010",
                idempotency_key=uuid.uuid4().hex,
                currency="INR",
                hourly_rate=hourly,
                subtotal=subtotal,
                tax_amount=tax,
                platform_fee=(subtotal * Decimal("0.15")).quantize(Decimal("0.01")),
                total_amount=subtotal + tax,
                tax_rate=Decimal("0.18"),
                commission_rate=Decimal("0.15"),
                checked_in_at=p_start + timedelta(minutes=5),
            )
            session.add(b)

        await session.commit()
        print("🎉 Delhi NCR / Ghaziabad listings successfully committed!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_ncr())
