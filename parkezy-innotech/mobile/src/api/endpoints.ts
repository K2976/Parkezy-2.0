import { api } from '@/api/client';
import type {
  AccessCredentials,
  AccessVerifyResult,
  AppNotification,
  AuthResponse,
  Booking,
  Dispute,
  HostDashboard,
  LegalDocKind,
  LegalDocument,
  Listing,
  ListingInput,
  ListingSearchItem,
  Page,
  PaymentOrder,
  PublicConfig,
  Quote,
  SlotInput,
  SupportCategory,
  SupportTicket,
  Tokens,
  UploadTicket,
  User,
} from '@/api/types';

export type SearchParams = {
  latitude: number;
  longitude: number;
  radius_km?: number;
  kind?: string;
  amenities?: string[];
  slot_type?: string;
  max_hourly_rate?: string;
  starts_at?: string;
  ends_at?: string;
  only_available?: boolean;
  sort?: 'distance' | 'price';
};

export type BookingGroup = 'upcoming' | 'active' | 'past';

export const authApi = {
  register: (body: { email: string; password: string; full_name: string; phone?: string | null }) =>
    api.request<AuthResponse>('/v1/auth/register', { method: 'POST', body, auth: false }),
  login: (body: { email: string; password: string }) =>
    api.request<AuthResponse>('/v1/auth/login', { method: 'POST', body, auth: false }),
  refresh: (refresh_token: string) =>
    api.request<Tokens>('/v1/auth/refresh', { method: 'POST', body: { refresh_token }, auth: false }),
  logout: (refresh_token: string) =>
    api.request<void>('/v1/auth/logout', { method: 'POST', body: { refresh_token }, auth: false }),
  verifyEmail: (code: string) => api.request<User>('/v1/auth/verify-email', { method: 'POST', body: { code } }),
  resendVerification: () => api.request<{ message: string }>('/v1/auth/resend-verification', { method: 'POST' }),
  forgotPassword: (email: string) =>
    api.request<{ message: string }>('/v1/auth/forgot-password', { method: 'POST', body: { email }, auth: false }),
  resetPassword: (body: { email: string; code: string; new_password: string }) =>
    api.request<{ message: string }>('/v1/auth/reset-password', { method: 'POST', body, auth: false }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    api.request<{ message: string }>('/v1/auth/change-password', { method: 'POST', body }),
};

export const meApi = {
  get: () => api.request<User>('/v1/me'),
  update: (body: { full_name?: string; phone?: string | null }) =>
    api.request<User>('/v1/me', { method: 'PATCH', body }),
  becomeHost: () => api.request<User>('/v1/me/become-host', { method: 'POST' }),
  addPushToken: (token: string, platform: 'ios' | 'android') =>
    api.request<void>('/v1/me/push-tokens', { method: 'POST', body: { token, platform } }),
  removePushToken: (token: string, platform: 'ios' | 'android') =>
    api.request<void>('/v1/me/push-tokens/remove', { method: 'POST', body: { token, platform } }),
  /** Requires the password again; the server rejects deletion while bookings are active. */
  delete: (password: string) => api.request<{ message: string }>('/v1/me', { method: 'DELETE', body: { password } }),
};

export const supportApi = {
  /** Works signed out too (email + name are then required/used); signed in, the account email is used. */
  create: (body: {
    category: SupportCategory;
    subject: string;
    message: string;
    booking_id?: string | null;
    email?: string | null;
    name?: string | null;
  }) => api.request<SupportTicket>('/v1/support', { method: 'POST', body }),
  mine: () => api.request<SupportTicket[]>('/v1/support/tickets'),
};

export const legalApi = {
  get: (doc: LegalDocKind) => api.request<LegalDocument>(`/v1/legal/${doc}`, { auth: false }),
};

export const discoveryApi = {
  config: () => api.request<PublicConfig>('/v1/config', { auth: false }),
  search: (params: SearchParams, signal?: AbortSignal) =>
    api.request<ListingSearchItem[]>('/v1/listings', { query: params, auth: false, signal }),
  listing: (id: string, window?: { starts_at: string; ends_at: string }) =>
    api.request<Listing>(`/v1/listings/${id}`, { query: window, auth: false }),
};

export const bookingApi = {
  quote: (body: { listing_id: string; slot_id?: string | null; starts_at: string; ends_at: string }) =>
    api.request<Quote>('/v1/bookings/quote', { method: 'POST', body, auth: false }),
  create: (
    body: {
      listing_id: string;
      slot_id?: string | null;
      slot_type?: string | null;
      starts_at: string;
      ends_at: string;
      vehicle_number?: string | null;
    },
    idempotencyKey: string,
  ) =>
    api.request<Booking>('/v1/bookings', {
      method: 'POST',
      body,
      headers: { 'Idempotency-Key': idempotencyKey },
    }),
  list: (group: BookingGroup | undefined, cursor?: string | null) =>
    api.request<Page<Booking>>('/v1/bookings', { query: { group, cursor } }),
  get: (id: string) => api.request<Booking>(`/v1/bookings/${id}`),
  cancel: (id: string, reason?: string) =>
    api.request<Booking>(`/v1/bookings/${id}/cancel`, { method: 'POST', body: { reason: reason ?? null } }),
  access: (id: string) => api.request<AccessCredentials>(`/v1/bookings/${id}/access`),
  checkOut: (id: string) => api.request<Booking>(`/v1/bookings/${id}/check-out`, { method: 'POST' }),
  createPayment: (id: string) => api.request<PaymentOrder>(`/v1/bookings/${id}/payment`, { method: 'POST' }),
  confirmPayment: (id: string, body: { order_id: string; payment_id: string; signature: string }) =>
    api.request<{ message: string }>(`/v1/bookings/${id}/payment/confirm`, { method: 'POST', body }),
};

export const hostApi = {
  dashboard: (days: number) => api.request<HostDashboard>('/v1/host/dashboard', { query: { days } }),
  listings: () => api.request<Listing[]>('/v1/host/listings'),
  listing: (id: string) => api.request<Listing>(`/v1/host/listings/${id}`),
  createListing: (body: ListingInput & { slots: SlotInput[]; photo_upload_ids: string[]; publish: boolean }) =>
    api.request<Listing>('/v1/host/listings', { method: 'POST', body }),
  updateListing: (id: string, body: ListingInput) =>
    api.request<Listing>(`/v1/host/listings/${id}`, { method: 'PATCH', body }),
  addSlots: (id: string, slots: SlotInput[]) =>
    api.request<Listing>(`/v1/host/listings/${id}/slots`, { method: 'POST', body: slots }),
  updateSlot: (id: string, slotId: string, body: Partial<SlotInput> & { is_active?: boolean }) =>
    api.request<Listing>(`/v1/host/listings/${id}/slots/${slotId}`, { method: 'PATCH', body }),
  deleteSlot: (id: string, slotId: string) =>
    api.request<Listing>(`/v1/host/listings/${id}/slots/${slotId}`, { method: 'DELETE' }),
  addPhotos: (id: string, upload_ids: string[]) =>
    api.request<Listing>(`/v1/host/listings/${id}/photos`, { method: 'POST', body: { upload_ids } }),
  removePhoto: (id: string, mediaId: string) =>
    api.request<Listing>(`/v1/host/listings/${id}/photos/${mediaId}`, { method: 'DELETE' }),
  bookings: (group: BookingGroup | undefined, cursor?: string | null) =>
    api.request<Page<Booking>>('/v1/host/bookings', { query: { group, cursor } }),
  approve: (id: string) => api.request<Booking>(`/v1/host/bookings/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason?: string) =>
    api.request<Booking>(`/v1/host/bookings/${id}/reject`, { method: 'POST', body: { reason: reason ?? null } }),
  verifyAccess: (body: { qr_token?: string; listing_id?: string; pin?: string }) =>
    api.request<AccessVerifyResult>('/v1/host/access/verify', { method: 'POST', body }),
};

export const uploadApi = {
  create: (purpose: 'listing_photo' | 'dispute_evidence' | 'avatar', content_type: string) =>
    api.request<UploadTicket>('/v1/uploads', { method: 'POST', body: { purpose, content_type } }),
  complete: (id: string) =>
    api.request<{ id: string; status: string; size_bytes: number | null }>(`/v1/uploads/${id}/complete`, {
      method: 'POST',
    }),
};

export const notificationApi = {
  list: (unreadOnly = false) =>
    api.request<{ items: AppNotification[]; unread_count: number }>('/v1/notifications', {
      query: { unread_only: unreadOnly },
    }),
  markRead: (ids?: string[]) =>
    api.request<void>('/v1/notifications/read', { method: 'POST', body: { ids: ids ?? null } }),
};

export const disputeApi = {
  create: (body: { booking_id: string; reason: string; description: string; evidence_upload_ids: string[] }) =>
    api.request<Dispute>('/v1/disputes', { method: 'POST', body }),
  mine: () => api.request<Dispute[]>('/v1/disputes'),
};
