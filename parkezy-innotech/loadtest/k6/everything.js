// Every endpoint, end to end, under load. One iteration = one realistic "day" in the app:
//   new account lifecycle -> host creates a listing with photos/slots -> driver searches, saves,
//   books "now", checks in/out, extends, gets a receipt, reviews, reports a problem -> host replies,
//   approves/rejects requests, sets up payouts -> admin reviews users/disputes/payouts/outbox.
// Every response is compared with the statuses that endpoint SHOULD return; anything else is
// counted in `unexpected_responses{name,status}` and the first bodies are logged.
//
//   ./loadtest/k6.sh everything -e PROFILE=stress -e VUS=20
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import encoding from 'k6/encoding';
import { BASE_URL, FIXTURE, stages } from './lib/config.js';
import { pick, uuid } from './lib/api.js';

const unexpected = new Counter('unexpected_responses');
const journeys = new Counter('journeys_completed');
const journeyTime = new Trend('journey_duration', true);
const PASSWORD = FIXTURE.password;
const PNG = encoding.b64decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4DwABAQEAGNhOAAAAAElFTkSuQmCC',
);

export const options = {
  scenarios: { day: { executor: 'ramping-vus', startVUs: 0, stages: stages(), gracefulRampDown: '60s' } },
  thresholds: {
    unexpected_responses: ['count<1'],
    http_req_failed: ['rate<0.01'], // here: 5xx and network errors only (see callback below)
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(95)', 'p(99)', 'max'],
};

// Business errors (4xx) are asserted per call below; "failed" means the server broke (5xx / timeout).
http.setResponseCallback(http.expectedStatuses({ min: 200, max: 499 }, 503)); // 503 = social sign-in not configured locally

let logged = 0;
function call(method, path, body, { token, name, ok = [200], headers = {}, raw = false } = {}) {
  const h = { ...headers };
  if (!raw && body !== null && body !== undefined) h['Content-Type'] = 'application/json';
  if (token) h.Authorization = `Bearer ${token}`;
  const url = path.startsWith('http') ? path : `${BASE_URL}${path}`;
  const payload = body === null || body === undefined ? null : raw ? body : JSON.stringify(body);
  const res = http.request(method, url, payload, { headers: h, tags: { name: name || `${method} ${path}` } });
  const good = ok.includes(res.status);
  check(res, { [`${name} -> ${ok.join('|')}`]: () => good });
  if (!good) {
    unexpected.add(1, { name, status: String(res.status) });
    if (logged++ < 40) console.warn(`UNEXPECTED ${name}: ${res.status} ${String(res.body).slice(0, 300)}`);
  }
  return res;
}

const j = (res, path) => {
  try {
    return res.json(path);
  } catch (_) {
    return undefined;
  }
};

function login(email) {
  const r = call('POST', '/v1/auth/login', { email, password: PASSWORD }, { name: 'POST /v1/auth/login' });
  return j(r, 'tokens.access_token');
}

// Booking windows sit on the 15-minute grid. "now" = the current block (the API allows it).
const STEP = 15 * 60 * 1000;
function win(startOffsetMin, minutes) {
  const start = Math.floor(Date.now() / STEP) * STEP + startOffsetMin * 60 * 1000;
  return { starts_at: new Date(start).toISOString(), ends_at: new Date(start + minutes * 60 * 1000).toISOString() };
}
const book = (token, listingId, w, name, ok = [201]) =>
  call('POST', '/v1/bookings', { listing_id: listingId, ...w }, {
    token,
    name,
    ok,
    headers: { 'Idempotency-Key': uuid() },
  });

function uploadPhoto(token) {
  const u = call('POST', '/v1/uploads', { purpose: 'listing_photo', content_type: 'image/png' }, {
    token,
    name: 'POST /v1/uploads',
    ok: [201],
  });
  if (u.status !== 201) return null;
  const put = http.put(j(u, 'upload_url'), PNG, { headers: j(u, 'headers'), tags: { name: 'PUT s3 (presigned)' } });
  if (!check(put, { 'presigned PUT 200': (r) => r.status === 200 || r.status === 204 })) {
    unexpected.add(1, { name: 'PUT s3 (presigned)', status: String(put.status) });
  }
  call('POST', `/v1/uploads/${j(u, 'id')}/complete`, null, { token, name: 'POST /v1/uploads/{id}/complete' });
  return j(u, 'id');
}

const tokens = {};
const tokenFor = (email) => (tokens[email] = tokens[email] || login(email));

export default function () {
  const started = Date.now();
  const host = FIXTURE.hosts[(__VU - 1) % FIXTURE.hosts.length];
  const driverEmail = FIXTURE.drivers[(__VU - 1) % FIXTURE.drivers.length];
  const adminEmail = FIXTURE.admins[(__VU - 1) % FIXTURE.admins.length];
  const H = tokenFor(host.email);
  const D = tokenFor(driverEmail);
  const A = tokenFor(adminEmail);
  if (!H || !D || !A) return;

  // ---------------------------------------------------------------- public + health
  group('public', () => {
    call('GET', '/health/live', null, { name: 'GET /health/live' });
    call('GET', '/health/ready', null, { name: 'GET /health/ready' });
    call('GET', '/v1/config', null, { name: 'GET /v1/config' });
    call('GET', `/v1/legal/${pick(['terms', 'privacy'])}`, null, { name: 'GET /v1/legal/{doc}' });
    call('GET', `/legal/${pick(['terms', 'privacy'])}`, null, { name: 'GET /legal/{doc} (html)' });
    call('GET', '/metrics', null, {
      name: 'GET /metrics',
      headers: { Authorization: 'Bearer loadtest-metrics-token' },
    });
  });

  // ---------------------------------------------------------------- account lifecycle
  let tempId = null;
  group('account', () => {
    const email = `lt-tmp-${uuid().slice(0, 12)}@loadtest.parkezy.dev`;
    const reg = call(
      'POST',
      '/v1/auth/register',
      { email, password: PASSWORD, full_name: 'Temp User', phone: '+919811112222' },
      { name: 'POST /v1/auth/register', ok: [201] },
    );
    let T = j(reg, 'tokens.access_token');
    const refresh = j(reg, 'tokens.refresh_token');
    tempId = j(reg, 'user.id');
    if (!T) return;
    call('POST', '/v1/auth/register', { email, password: PASSWORD, full_name: 'Dup User' }, {
      name: 'POST /v1/auth/register (duplicate)',
      ok: [409],
    });
    call('GET', '/v1/me', null, { token: T, name: 'GET /v1/me' });
    call('PATCH', '/v1/me', { full_name: 'Temp User Renamed' }, { token: T, name: 'PATCH /v1/me' });
    call('POST', '/v1/auth/resend-verification', null, { token: T, name: 'POST /v1/auth/resend-verification' });
    call('POST', '/v1/auth/verify-email', { code: '000000' }, {
      token: T,
      name: 'POST /v1/auth/verify-email (wrong code)',
      ok: [422],
    });
    call('POST', '/v1/me/become-host', null, { token: T, name: 'POST /v1/me/become-host (unverified)', ok: [403] });
    call('POST', '/v1/auth/forgot-password', { email }, { name: 'POST /v1/auth/forgot-password' });
    call('POST', '/v1/auth/reset-password', { email, code: '000000', new_password: 'NewPass123' }, {
      name: 'POST /v1/auth/reset-password (wrong code)',
      ok: [422],
    });
    call('POST', '/v1/auth/login', { email, password: 'WrongPass1' }, {
      name: 'POST /v1/auth/login (wrong password)',
      ok: [401],
    });
    call('POST', '/v1/auth/social', { provider: 'google', id_token: 'not-configured-here' }, {
      name: 'POST /v1/auth/social (no client ids)',
      ok: [503],
    });
    const rot = call('POST', '/v1/auth/refresh', { refresh_token: refresh }, { name: 'POST /v1/auth/refresh' });
    call('POST', '/v1/auth/refresh', { refresh_token: refresh }, {
      name: 'POST /v1/auth/refresh (reused token)',
      ok: [401],
    });
    // Reuse of a rotated token revokes the family; sign in again.
    T = login(email);
    call('POST', '/v1/auth/change-password', { current_password: PASSWORD, new_password: 'Changed123' }, {
      token: T,
      name: 'POST /v1/auth/change-password',
    });
    call('GET', '/v1/me', null, { token: T, name: 'GET /v1/me (after password change)', ok: [401] });
    const re = call('POST', '/v1/auth/login', { email, password: 'Changed123' }, { name: 'POST /v1/auth/login' });
    T = j(re, 'tokens.access_token');
    call('POST', '/v1/auth/logout', { refresh_token: j(re, 'tokens.refresh_token') }, { name: 'POST /v1/auth/logout' });
    void rot;

    // Admin suspends and reinstates this account, then it deletes itself.
    call('POST', `/v1/admin/users/${tempId}/suspend`, { reason: 'load test suspension' }, {
      token: A,
      name: 'POST /v1/admin/users/{id}/suspend',
    });
    call('POST', '/v1/auth/login', { email, password: 'Changed123' }, {
      name: 'POST /v1/auth/login (suspended)',
      ok: [401],
    });
    call('POST', `/v1/admin/users/${tempId}/unsuspend`, null, { token: A, name: 'POST /v1/admin/users/{id}/unsuspend' });
    T = j(call('POST', '/v1/auth/login', { email, password: 'Changed123' }, { name: 'POST /v1/auth/login' }), 'tokens.access_token');
    call('DELETE', '/v1/me', { password: 'Changed123' }, { token: T, name: 'DELETE /v1/me' });
  });

  // ---------------------------------------------------------------- host builds a listing
  let listing = null;
  group('host listing', () => {
    call('GET', '/v1/host/listings', null, { token: H, name: 'GET /v1/host/listings' });
    const photo = uploadPhoto(H);
    if (!photo) return;
    const created = call(
      'POST',
      '/v1/host/listings',
      {
        title: `Journey spot ${__VU}-${__ITER}`,
        address_line: `${__ITER} Journey Road`,
        city: 'Bengaluru',
        latitude: FIXTURE.center[0] + (Math.random() - 0.5) * 0.1,
        longitude: FIXTURE.center[1] + (Math.random() - 0.5) * 0.1,
        hourly_rate: '40.00',
        amenities: ['covered', 'cctv'],
        slots: [{ label: 'A1' }, { label: 'A2', slot_type: 'ev', hourly_rate_override: '60.00' }],
        photo_upload_ids: [photo],
        auto_accept: true,
      },
      { token: H, name: 'POST /v1/host/listings', ok: [201] },
    );
    listing = created.status === 201 ? created.json() : null;
    if (!listing) return;
    const L = `/v1/host/listings/${listing.id}`;
    call('GET', L, null, { token: H, name: 'GET /v1/host/listings/{id}' });
    call('PATCH', L, { description: 'Updated by the load test', access_instructions: 'Gate code 1234' }, {
      token: H,
      name: 'PATCH /v1/host/listings/{id}',
    });
    const withSlot = call('POST', `${L}/slots`, [{ label: 'B1' }], { token: H, name: 'POST /v1/host/listings/{id}/slots' });
    const b1 = (j(withSlot, 'slots') || []).find((s) => s.label === 'B1');
    if (b1) {
      call('PATCH', `${L}/slots/${b1.id}`, { floor: 'G' }, { token: H, name: 'PATCH /v1/host/listings/{id}/slots/{slot_id}' });
      call('DELETE', `${L}/slots/${b1.id}`, null, { token: H, name: 'DELETE /v1/host/listings/{id}/slots/{slot_id}' });
    }
    call('POST', `${L}/slots`, [{ label: 'A1' }], { token: H, name: 'POST /v1/host/listings/{id}/slots (duplicate)', ok: [409] });
    const extra = uploadPhoto(H);
    if (extra) {
      const withPhoto = call('POST', `${L}/photos`, { upload_ids: [extra] }, { token: H, name: 'POST /v1/host/listings/{id}/photos' });
      const media = j(withPhoto, 'media') || [];
      if (media.length > 1) {
        call('DELETE', `${L}/photos/${media[media.length - 1].id}`, null, {
          token: H,
          name: 'DELETE /v1/host/listings/{id}/photos/{media_id}',
        });
      }
    }
    call('GET', '/v1/host/dashboard', null, { token: H, name: 'GET /v1/host/dashboard' });
  });
  if (!listing) return;
  const slotA1 = listing.slots.find((s) => s.label === 'A1').id;

  // ---------------------------------------------------------------- driver discovers it
  group('driver discovery', () => {
    const qs = `latitude=${listing.latitude}&longitude=${listing.longitude}&radius_km=2`;
    call('GET', `/v1/listings?${qs}`, null, { name: 'GET /v1/listings' });
    call('GET', `/v1/listings/${listing.id}`, null, { token: D, name: 'GET /v1/listings/{id}' });
    call('GET', `/v1/listings/${listing.id}/reviews`, null, { name: 'GET /v1/listings/{id}/reviews' });
    call('PUT', `/v1/me/favorites/${listing.id}`, null, { token: D, name: 'PUT /v1/me/favorites/{id}', ok: [204] });
    call('GET', '/v1/me/favorites?limit=10', null, { token: D, name: 'GET /v1/me/favorites' });
    call('DELETE', `/v1/me/favorites/${listing.id}`, null, { token: D, name: 'DELETE /v1/me/favorites/{id}', ok: [204] });
    call('GET', '/v1/me/notification-preferences', null, { token: D, name: 'GET /v1/me/notification-preferences' });
    call('PUT', '/v1/me/notification-preferences', { push: { reminders: true } }, {
      token: D,
      name: 'PUT /v1/me/notification-preferences',
    });
    const pt = { token: `ExponentPushToken[lt-${__VU}-${__ITER}]`, platform: 'android' };
    call('POST', '/v1/me/push-tokens', pt, { token: D, name: 'POST /v1/me/push-tokens', ok: [204] });
    call('POST', '/v1/me/push-tokens/remove', pt, { token: D, name: 'POST /v1/me/push-tokens/remove', ok: [204] });
  });

  // ---------------------------------------------------------------- book now -> park -> leave
  let done = null;
  group('parking session', () => {
    const now = win(0, 60);
    call('POST', '/v1/bookings/quote', { listing_id: listing.id, slot_id: slotA1, ...now }, { name: 'POST /v1/bookings/quote' });
    const b = book(D, listing.id, { slot_id: slotA1, ...now }, 'POST /v1/bookings');
    if (b.status !== 201) return;
    const id = b.json('id');
    book(D, listing.id, { slot_id: slotA1, ...now }, 'POST /v1/bookings (same slot taken)', [409]);
    call('GET', `/v1/bookings/${id}`, null, { token: D, name: 'GET /v1/bookings/{id}' });
    call('GET', '/v1/bookings?limit=20', null, { token: D, name: 'GET /v1/bookings' });
    call('POST', `/v1/bookings/${id}/payment`, null, { token: D, name: 'POST /v1/bookings/{id}/payment (offline)', ok: [409] });
    call('POST', `/v1/bookings/${id}/payment/confirm`, { order_id: 'order_x', payment_id: 'pay_x', signature: 'x' }, {
      token: D,
      name: 'POST /v1/bookings/{id}/payment/confirm (offline)',
      ok: [409],
    });
    const later = new Date(new Date(b.json('ends_at')).getTime() + STEP).toISOString();
    call('POST', `/v1/bookings/${id}/extend/quote`, { ends_at: later }, { token: D, name: 'POST /v1/bookings/{id}/extend/quote' });
    call('POST', `/v1/bookings/${id}/extend`, { ends_at: later }, { token: D, name: 'POST /v1/bookings/{id}/extend' });
    const creds = call('GET', `/v1/bookings/${id}/access`, null, { token: D, name: 'GET /v1/bookings/{id}/access' });
    call('POST', '/v1/host/access/verify', { qr_token: j(creds, 'qr_token') }, { token: H, name: 'POST /v1/host/access/verify (check-in)' });
    call('POST', '/v1/host/access/verify', { qr_token: j(creds, 'qr_token') }, {
      token: H,
      name: 'POST /v1/host/access/verify (replayed QR)',
      ok: [403],
    });
    const out = call('POST', `/v1/bookings/${id}/check-out`, null, { token: D, name: 'POST /v1/bookings/{id}/check-out' });
    if (j(out, 'status') === 'completed') done = id;
  });

  // ---------------------------------------------------------------- after the visit
  group('after the visit', () => {
    if (!done) return;
    call('GET', `/v1/bookings/${done}/receipt`, null, { token: D, name: 'GET /v1/bookings/{id}/receipt' });
    call('GET', `/v1/bookings/${done}/receipt.pdf`, null, { token: H, name: 'GET /v1/bookings/{id}/receipt.pdf' });
    const rv = call('POST', `/v1/bookings/${done}/review`, { rating: 4, comment: 'Smooth entry' }, {
      token: D,
      name: 'POST /v1/bookings/{id}/review',
      ok: [201],
    });
    const reviewId = j(rv, 'id');
    if (reviewId) {
      call('PATCH', `/v1/reviews/${reviewId}`, { rating: 5 }, { token: D, name: 'PATCH /v1/reviews/{id}' });
      call('POST', `/v1/host/reviews/${reviewId}/reply`, { reply: 'Thanks for parking with us!' }, {
        token: H,
        name: 'POST /v1/host/reviews/{id}/reply',
      });
      call('GET', `/v1/listings/${listing.id}/reviews`, null, { name: 'GET /v1/listings/{id}/reviews' });
      if (Math.random() < 0.3) call('DELETE', `/v1/reviews/${reviewId}`, null, { token: D, name: 'DELETE /v1/reviews/{id}', ok: [204] });
    }
    const dispute = call(
      'POST',
      '/v1/disputes',
      { booking_id: done, reason: 'wrong_charge', description: 'Load test: please check the overstay.' },
      { token: D, name: 'POST /v1/disputes', ok: [201] },
    );
    call('GET', '/v1/disputes', null, { token: D, name: 'GET /v1/disputes' });
    if (j(dispute, 'id')) {
      call('PATCH', `/v1/admin/disputes/${j(dispute, 'id')}`, { status: 'in_review' }, {
        token: A,
        name: 'PATCH /v1/admin/disputes/{id}',
      });
    }
    call('POST', '/v1/support', { category: 'booking', subject: 'Load test', message: 'Load test support ticket.', booking_id: done }, {
      token: D,
      name: 'POST /v1/support',
      ok: [201],
    });
    call('GET', '/v1/support/tickets', null, { token: D, name: 'GET /v1/support/tickets' });
    call('GET', '/v1/notifications', null, { token: D, name: 'GET /v1/notifications' });
    call('POST', '/v1/notifications/read', {}, { token: D, name: 'POST /v1/notifications/read', ok: [204] });
  });

  // ---------------------------------------------------------------- requests: approve / reject / cancel
  group('host requests', () => {
    call('PATCH', `/v1/host/listings/${listing.id}`, { auto_accept: false }, { token: H, name: 'PATCH /v1/host/listings/{id}' });
    const r1 = book(D, listing.id, { slot_id: slotA1, ...win(180, 60) }, 'POST /v1/bookings (request)');
    const r2 = book(D, listing.id, { slot_id: slotA1, ...win(300, 60) }, 'POST /v1/bookings (request)');
    call('GET', '/v1/host/bookings?group=upcoming', null, { token: H, name: 'GET /v1/host/bookings' });
    if (r1.status === 201) {
      call('POST', `/v1/host/bookings/${r1.json('id')}/approve`, null, { token: H, name: 'POST /v1/host/bookings/{id}/approve' });
      call('POST', `/v1/bookings/${r1.json('id')}/cancel`, { reason: 'plans changed' }, {
        token: D,
        name: 'POST /v1/bookings/{id}/cancel',
      });
    }
    if (r2.status === 201) {
      call('POST', `/v1/host/bookings/${r2.json('id')}/reject`, { reason: 'Blocked' }, { token: H, name: 'POST /v1/host/bookings/{id}/reject' });
    }
  });

  // ---------------------------------------------------------------- payouts
  group('payouts', () => {
    call('PUT', '/v1/host/payout-account', { method: 'upi', upi_id: `host${__VU}@okaxis` }, {
      token: H,
      name: 'PUT /v1/host/payout-account',
    });
    call('GET', '/v1/host/payout-account', null, { token: H, name: 'GET /v1/host/payout-account' });
    call('GET', '/v1/host/payouts/balance', null, { token: H, name: 'GET /v1/host/payouts/balance' });
    // Pay-at-venue earnings are held by the host, so the platform owes nothing: 409 is correct.
    call('POST', '/v1/host/payouts', { amount: '100.00' }, {
      token: H,
      name: 'POST /v1/host/payouts (pay-at-venue host)',
      ok: [409],
      headers: { 'Idempotency-Key': uuid() },
    });
    call('GET', '/v1/host/payouts', null, { token: H, name: 'GET /v1/host/payouts' });
    call('POST', `/v1/host/payouts/${uuid()}/cancel`, null, { token: H, name: 'POST /v1/host/payouts/{id}/cancel (unknown)', ok: [404] });
  });

  // ---------------------------------------------------------------- admin
  group('admin', () => {
    call('GET', '/v1/admin/users?limit=20', null, { token: A, name: 'GET /v1/admin/users' });
    call('GET', '/v1/admin/users?q=load%20driver&status=active', null, { token: A, name: 'GET /v1/admin/users (search)' });
    call('GET', `/v1/admin/users/${host.id}`, null, { token: A, name: 'GET /v1/admin/users/{id}' });
    call('POST', `/v1/admin/users/${host.id}/commercial-host`, null, { token: A, name: 'POST /v1/admin/users/{id}/commercial-host' });
    call('GET', '/v1/admin/settings', null, { token: A, name: 'GET /v1/admin/settings' });
    if (Math.random() < 0.05) {
      call('PATCH', '/v1/admin/settings', { changes: { max_page_size: 100 } }, { token: A, name: 'PATCH /v1/admin/settings' });
    }
    call('GET', '/v1/admin/disputes?limit=20', null, { token: A, name: 'GET /v1/admin/disputes' });
    call('GET', '/v1/admin/payouts?limit=20', null, { token: A, name: 'GET /v1/admin/payouts' });
    call('POST', `/v1/admin/payouts/${uuid()}/mark-paid`, { reference: 'UTR1' }, { token: A, name: 'POST /v1/admin/payouts/{id}/mark-paid (unknown)', ok: [404] });
    call('POST', `/v1/admin/payouts/${uuid()}/reject`, { reason: 'x' }, { token: A, name: 'POST /v1/admin/payouts/{id}/reject (unknown)', ok: [404] });
    call('GET', '/v1/admin/outbox/stats', null, { token: A, name: 'GET /v1/admin/outbox/stats' });
    call('GET', '/v1/admin/outbox/dead-letters', null, { token: A, name: 'GET /v1/admin/outbox/dead-letters' });
    call('POST', `/v1/admin/outbox/${uuid()}/retry`, null, { token: A, name: 'POST /v1/admin/outbox/{id}/retry (unknown)', ok: [404] });
    call('GET', '/v1/admin/users', null, { token: D, name: 'GET /v1/admin/users (as driver)', ok: [403] });
    call('POST', '/v1/webhooks/razorpay', '{}', {
      name: 'POST /v1/webhooks/razorpay (offline)',
      ok: [409],
      raw: true,
      headers: { 'Content-Type': 'application/json', 'x-razorpay-signature': 'x', 'x-razorpay-event-id': uuid() },
    });
  });

  // ---------------------------------------------------------------- clean up: delete the listing
  group('delete listing', () => {
    call('DELETE', `/v1/host/listings/${listing.id}`, null, { token: H, name: 'DELETE /v1/host/listings/{id}', ok: [204] });
    call('GET', `/v1/listings/${listing.id}`, null, { name: 'GET /v1/listings/{id} (deleted)', ok: [404] });
  });

  journeys.add(1);
  journeyTime.add(Date.now() - started);
  sleep(1);
}
