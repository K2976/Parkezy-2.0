// Signed-in drivers doing the full booking journey:
// search -> detail -> quote -> book -> view -> (extend quote) -> cancel most -> my bookings.
// A 409 on book means the slot/time was taken a moment ago: correct behaviour, counted separately.
//   ./loadtest/k6.sh booking -e PROFILE=stress -e VUS=50
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { BASE_THRESHOLDS, BASE_URL, FIXTURE, stages } from './lib/config.js';
import { authHeaders, pick, randomPoint, randomWindow, relogin, token, uuid } from './lib/api.js';

const created = new Counter('bookings_created');
const conflicts = new Counter('bookings_conflict');
const bookLatency = new Trend('booking_create_duration', true);

export const options = {
  scenarios: { drivers: { executor: 'ramping-vus', startVUs: 0, stages: stages(), gracefulRampDown: '20s' } },
  thresholds: {
    ...BASE_THRESHOLDS,
    booking_create_duration: ['p(95)<800'],
    'http_req_duration{name:POST /v1/bookings/quote}': ['p(95)<400'],
    'http_req_duration{name:GET /v1/bookings}': ['p(95)<400'],
  },
};

// 409 = taken slot / no availability: an expected answer under contention, not a failure.
http.setResponseCallback(http.expectedStatuses({ min: 200, max: 299 }, 409));

function call(method, url, body, name, extraHeaders) {
  let res = http.request(method, url, body ? JSON.stringify(body) : null, {
    ...authHeaders(token(), extraHeaders),
    tags: { name },
  });
  if (res.status === 401) {
    res = http.request(method, url, body ? JSON.stringify(body) : null, { ...authHeaders(relogin(), extraHeaders), tags: { name } });
  }
  return res;
}

export default function () {
  const win = randomWindow();
  let listingId = pick(FIXTURE.listings);

  group('find a spot', () => {
    const p = randomPoint();
    const qs = `latitude=${p.latitude}&longitude=${p.longitude}&radius_km=3&starts_at=${encodeURIComponent(win.starts_at)}&ends_at=${encodeURIComponent(win.ends_at)}&only_available=true`;
    const res = http.get(`${BASE_URL}/v1/listings?${qs}`, { tags: { name: 'GET /v1/listings' } });
    check(res, { 'search 200': (r) => r.status === 200 });
    const free = res.status === 200 ? res.json() : [];
    if (free.length) listingId = pick(free).id;
    check(http.get(`${BASE_URL}/v1/listings/${listingId}`, { tags: { name: 'GET /v1/listings/{id}' } }), {
      'detail 200': (r) => r.status === 200,
    });
  });
  sleep(Math.random() + 0.5);

  const quote = call('POST', `${BASE_URL}/v1/bookings/quote`, { listing_id: listingId, ...win }, 'POST /v1/bookings/quote');
  check(quote, { 'quote 200': (r) => r.status === 200 });

  const book = call('POST', `${BASE_URL}/v1/bookings`, { listing_id: listingId, ...win }, 'POST /v1/bookings', {
    'Idempotency-Key': uuid(),
  });
  bookLatency.add(book.timings.duration);
  check(book, { 'book 201 or 409': (r) => r.status === 201 || r.status === 409 });
  if (book.status === 409) {
    conflicts.add(1);
    return;
  }
  if (book.status !== 201) return;
  created.add(1);
  const bookingId = book.json('id');

  group('manage booking', () => {
    check(call('GET', `${BASE_URL}/v1/bookings/${bookingId}`, null, 'GET /v1/bookings/{id}'), {
      'view 200': (r) => r.status === 200,
    });
    if (Math.random() < 0.3 && book.json('status') === 'confirmed') {
      const later = new Date(new Date(book.json('ends_at')).getTime() + 3600 * 1000).toISOString();
      const ext = call('POST', `${BASE_URL}/v1/bookings/${bookingId}/extend/quote`, { ends_at: later }, 'POST /v1/bookings/{id}/extend/quote');
      check(ext, { 'extend quote 200': (r) => r.status === 200 });
    }
    // Cancel most bookings so slots free up and the data set stays realistic over long runs.
    if (Math.random() < 0.8) {
      const c = call('POST', `${BASE_URL}/v1/bookings/${bookingId}/cancel`, { reason: 'load test' }, 'POST /v1/bookings/{id}/cancel');
      check(c, { 'cancel 200': (r) => r.status === 200 });
    }
    check(call('GET', `${BASE_URL}/v1/bookings?limit=20`, null, 'GET /v1/bookings'), { 'list 200': (r) => r.status === 200 });
  });
  sleep(Math.random() * 2 + 1);
}
