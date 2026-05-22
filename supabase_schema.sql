-- PASTE THIS INTO SUPABASE SQL EDITOR

-- 1. Profiles Table (Matches AppUser.swift)
CREATE TABLE profiles (
    id UUID REFERENCES auth.users NOT NULL PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    profile_image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    capabilities JSONB NOT NULL DEFAULT '{"canDrive": true, "canHostPrivate": false, "canHostCommercial": false}'::jsonb,
    stats JSONB NOT NULL DEFAULT '{"totalBookingsAsDriver": 0, "hostRating": null, "totalEarnings": null}'::jsonb
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public profiles are viewable by everyone." ON profiles FOR SELECT USING (true);
CREATE POLICY "Users can insert their own profile." ON profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update own profile." ON profiles FOR UPDATE USING (auth.uid() = id);

-- Trigger to create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name, phone_number)
  VALUES (
    new.id, 
    new.email, 
    COALESCE(new.raw_user_meta_data->>'name', 'New User'),
    COALESCE(new.raw_user_meta_data->>'phone_number', '')
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();


-- 2. Private Listings Table (Matches PrivateParkingListing)
CREATE TABLE private_listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID REFERENCES profiles(id) NOT NULL,
    owner_name TEXT NOT NULL,
    title TEXT NOT NULL,
    address TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    description TEXT NOT NULL,
    slots JSONB NOT NULL,
    hourly_rate DOUBLE PRECISION NOT NULL,
    daily_rate DOUBLE PRECISION NOT NULL,
    monthly_rate DOUBLE PRECISION NOT NULL,
    flat_full_booking_rate DOUBLE PRECISION,
    auto_accept_bookings BOOLEAN NOT NULL DEFAULT false,
    instant_booking_discount DOUBLE PRECISION,
    has_cctv BOOLEAN NOT NULL DEFAULT false,
    is_covered BOOLEAN NOT NULL DEFAULT false,
    has_ev_charging BOOLEAN NOT NULL DEFAULT false,
    has_security_guard BOOLEAN NOT NULL DEFAULT false,
    has_water_access BOOLEAN NOT NULL DEFAULT false,
    is_24_hours BOOLEAN NOT NULL DEFAULT true,
    available_from TIMESTAMPTZ,
    available_to TIMESTAMPTZ,
    available_days JSONB NOT NULL,
    rating DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    review_count INTEGER NOT NULL DEFAULT 0,
    image_urls JSONB,
    max_booking_duration TEXT NOT NULL DEFAULT 'unlimited',
    suggested_hourly_rate DOUBLE PRECISION
);

CREATE INDEX private_listings_owner_id_idx ON private_listings(owner_id);
CREATE INDEX private_listings_lat_lng_idx ON private_listings(lat, lng);

ALTER TABLE private_listings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Listings are viewable by everyone" ON private_listings FOR SELECT USING (true);
CREATE POLICY "Users can manage their own listings" ON private_listings FOR ALL USING (auth.uid() = owner_id);


-- 3. Commercial Facilities Table (Matches CommercialParkingFacility)
CREATE TABLE commercial_facilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    facility_type TEXT NOT NULL,
    slots JSONB NOT NULL,
    default_hourly_rate DOUBLE PRECISION NOT NULL,
    flat_day_rate DOUBLE PRECISION,
    has_cctv BOOLEAN NOT NULL DEFAULT true,
    has_ev_charging BOOLEAN NOT NULL DEFAULT false,
    has_valet_service BOOLEAN NOT NULL DEFAULT false,
    has_car_wash BOOLEAN NOT NULL DEFAULT false,
    is_24_hours BOOLEAN NOT NULL DEFAULT false,
    rating DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    review_count INTEGER NOT NULL DEFAULT 0,
    owner_id UUID REFERENCES profiles(id) NOT NULL,
    owner_name TEXT NOT NULL
);

CREATE INDEX commercial_facilities_lat_lng_idx ON commercial_facilities(lat, lng);

ALTER TABLE commercial_facilities ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Commercial facilities are viewable by everyone" ON commercial_facilities FOR SELECT USING (true);
CREATE POLICY "Commercial owners can manage their own facilities" ON commercial_facilities FOR ALL USING (auth.uid() = owner_id);


-- 4. Bookings Table (Matches BookingSession)
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    spot_id UUID NOT NULL, -- references either private_listings or commercial_facilities in jsonb slots
    user_id UUID REFERENCES profiles(id) NOT NULL,
    type TEXT NOT NULL, -- 'private' or 'commercial'
    booking_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_start_time TIMESTAMPTZ NOT NULL,
    actual_start_time TIMESTAMPTZ,
    scheduled_end_time TIMESTAMPTZ NOT NULL,
    actual_end_time TIMESTAMPTZ,
    duration DOUBLE PRECISION NOT NULL,
    total_cost DOUBLE PRECISION NOT NULL,
    overstay_fee DOUBLE PRECISION,
    status TEXT NOT NULL,
    access_code TEXT
);

CREATE INDEX bookings_user_id_idx ON bookings(user_id);
CREATE INDEX bookings_spot_id_idx ON bookings(spot_id);
CREATE INDEX bookings_status_idx ON bookings(status);

ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own bookings" ON bookings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own bookings" ON bookings FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update their own bookings" ON bookings FOR UPDATE USING (auth.uid() = user_id);
-- Note: A separate policy would be needed to allow hosts to view bookings for their spots


-- 5. Disputes Table (Matches DisputeReport)
CREATE TABLE disputes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID REFERENCES bookings(id) NOT NULL,
    reporter_id UUID REFERENCES profiles(id) NOT NULL,
    reason TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

ALTER TABLE disputes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own disputes" ON disputes FOR SELECT USING (auth.uid() = reporter_id);
CREATE POLICY "Users can create disputes" ON disputes FOR INSERT WITH CHECK (auth.uid() = reporter_id);
