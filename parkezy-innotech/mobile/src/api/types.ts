// Mirrors backend/app/schemas. Money and rates arrive as decimal strings to avoid float errors.

export type Money = string;

export type User = {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  email_verified: boolean;
  is_host: boolean;
  is_commercial_host: boolean;
  is_admin: boolean;
  created_at: string;
};

export type Tokens = {
  access_token: string;
  access_expires_at: string;
  refresh_token: string;
  refresh_expires_at: string;
};

export type AuthResponse = { user: User; tokens: Tokens };

export type PaymentMode = 'online' | 'pay_at_venue';

export type PublicConfig = {
  currency: string;
  gst_rate: string;
  booking_step_minutes: number;
  min_booking_minutes: number;
  max_booking_minutes: number;
  max_advance_days: number;
  payment_mode: PaymentMode;
  payment_hold_minutes: number;
  free_cancellation_minutes: number;
  late_cancellation_fee_rate: string;
  overstay_grace_minutes: number;
  overstay_block_minutes: number;
  overstay_block_fee: Money;
  early_checkin_minutes: number;
  min_listing_photos: number;
  max_listing_photos: number;
  max_dispute_photos: number;
  max_slots_per_listing: number;
  search_default_radius_km: number;
  search_max_radius_km: number;
  upload_max_bytes: number;
  upload_allowed_types: string[];
  default_timezone: string;
  amenities: string[];
  slot_types: string[];
  dispute_reasons: string[];
};

export type ListingKind = 'private' | 'commercial';
export type ListingStatus = 'draft' | 'active' | 'paused' | 'archived';

export type ListingSearchItem = {
  id: string;
  kind: ListingKind;
  title: string;
  address_line: string;
  city: string;
  latitude: number;
  longitude: number;
  hourly_rate: Money;
  currency: string;
  amenities: string[];
  distance_m: number;
  total_slots: number;
  available_slots: number | null;
  cover_photo_url: string | null;
  rating_avg: string | null;
};

export type Slot = {
  id: string;
  label: string;
  floor: string | null;
  slot_type: string;
  hourly_rate: Money;
  is_active: boolean;
  available: boolean | null;
};

export type Listing = {
  id: string;
  kind: ListingKind;
  status: ListingStatus;
  title: string;
  description: string | null;
  address_line: string;
  city: string;
  postal_code: string | null;
  latitude: number;
  longitude: number;
  timezone: string;
  amenities: string[];
  hourly_rate: Money;
  daily_cap: Money | null;
  currency: string;
  auto_accept: boolean;
  is_24h: boolean;
  open_time: string | null;
  close_time: string | null;
  open_days: number[];
  rating_avg: string | null;
  rating_count: number;
  host: { id: string; first_name: string };
  slots: Slot[];
  media: { id: string; url: string; position: number }[];
  access_instructions: string | null;
};

export type BookingStatus =
  | 'pending_approval'
  | 'pending_payment'
  | 'confirmed'
  | 'checked_in'
  | 'completed'
  | 'cancelled'
  | 'rejected'
  | 'expired';

export type Booking = {
  id: string;
  status: BookingStatus;
  payment_mode: PaymentMode;
  starts_at: string;
  ends_at: string;
  vehicle_number: string | null;
  currency: string;
  hourly_rate: Money;
  subtotal: Money;
  tax_amount: Money;
  total_amount: Money;
  overstay_minutes: number;
  overstay_fee: Money;
  overstay_tax: Money;
  final_amount: Money | null;
  amount_paid: Money;
  amount_due: Money;
  hold_expires_at: string | null;
  approval_expires_at: string | null;
  checked_in_at: string | null;
  checked_out_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  created_at: string;
  listing: {
    id: string;
    title: string;
    address_line: string;
    city: string;
    latitude: number;
    longitude: number;
    timezone: string;
  };
  slot: { id: string; label: string; floor: string | null; slot_type: string };
  driver: { id: string; full_name: string; phone: string | null };
  host: { id: string; full_name: string; phone: string | null };
  access_instructions: string | null;
  host_earnings: Money | null;
};

export type Page<T> = { items: T[]; next_cursor: string | null };

export type Quote = {
  listing_id: string;
  slot_id: string | null;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  hourly_rate: Money;
  subtotal: Money;
  tax_rate: string;
  tax_amount: Money;
  total: Money;
  currency: string;
  payment_mode: PaymentMode;
  requires_approval: boolean;
  available: boolean;
};

export type AccessCredentials = {
  booking_id: string;
  pin: string;
  qr_token: string;
  qr_expires_at: string;
  check_in_opens_at: string;
};

export type AccessVerifyResult = { action: 'checked_in' | 'checked_out'; booking: Booking };

export type UploadTicket = {
  id: string;
  upload_url: string;
  method: string;
  headers: Record<string, string>;
  expires_in: number;
  max_bytes: number;
};

export type PaymentOrder = {
  provider: string;
  order_id: string;
  amount_minor: number;
  currency: string;
  key_id: string;
  booking_id: string;
  description: string;
  prefill_email: string;
  prefill_phone: string | null;
};

export type AppNotification = {
  id: string;
  type: string;
  title: string;
  body: string;
  data: Record<string, string>;
  read_at: string | null;
  created_at: string;
};

export type Dispute = {
  id: string;
  booking_id: string;
  reason: string;
  description: string;
  status: 'open' | 'in_review' | 'resolved' | 'rejected';
  resolution: string | null;
  evidence_urls: string[];
  created_at: string;
  updated_at: string;
};

export type HostDashboard = {
  active_listings: number;
  pending_requests: number;
  upcoming_bookings: number;
  parked_now: number;
  completed_bookings: number;
  earnings_total: Money;
  earnings_period: Money;
  period_days: number;
  /** `day` values are calendar dates in `timezone` (the platform's, e.g. Asia/Kolkata). */
  daily_earnings: { day: string; amount: Money }[];
  currency: string;
  timezone: string;
};

export type SlotInput = {
  label: string;
  floor?: string | null;
  slot_type?: string;
  hourly_rate_override?: string | null;
};

export type ListingInput = {
  kind?: ListingKind;
  title?: string;
  description?: string | null;
  access_instructions?: string | null;
  address_line?: string;
  city?: string;
  postal_code?: string | null;
  latitude?: number;
  longitude?: number;
  amenities?: string[];
  hourly_rate?: string;
  daily_cap?: string | null;
  auto_accept?: boolean;
  is_24h?: boolean;
  open_time?: string | null;
  close_time?: string | null;
  open_days?: number[];
  status?: ListingStatus;
  clear_daily_cap?: boolean;
};

export type SupportCategory = 'account' | 'booking' | 'payment' | 'hosting' | 'privacy' | 'bug' | 'other';

export type SupportTicket = {
  id: string;
  reference: string;
  category: SupportCategory;
  subject: string;
  status: 'open' | 'resolved';
  created_at: string;
};

export type LegalDocKind = 'terms' | 'privacy';

export type LegalBlock = { type: 'paragraph'; text: string } | { type: 'list'; items: string[] };

export type LegalDocument = {
  doc: LegalDocKind;
  title: string;
  version: string;
  effective_date: string;
  summary: string;
  sections: { heading: string; blocks: LegalBlock[] }[];
};
