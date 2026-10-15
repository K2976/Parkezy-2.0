// Breakpoint test: raise requests/second on ONE endpoint until it breaks, then stop.
// "Breaks" = p95 over BREAK_P95_MS (default 1000) or more than 5% errors/timeouts.
// The rate reached when k6 aborts is that endpoint's capacity on this machine.
//
//   ./loadtest/k6.sh breakpoint -e TARGET=search -e MAX_RPS=3000 -e RAMP=4m
//   TARGET: search | detail | reviews | config | quote | book | me | bookings | login
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, FIXTURE } from './lib/config.js';
import { authHeaders, login, pick, randomPoint, randomWindow, uuid } from './lib/api.js';

const TARGET = __ENV.TARGET || 'search';
const MAX_RPS = Number(__ENV.MAX_RPS || 2000);
const BREAK_P95 = Number(__ENV.BREAK_P95_MS || 1000);

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 200,
      maxVUs: Number(__ENV.MAX_VUS || 2000),
      stages: [{ duration: __ENV.RAMP || '4m', target: MAX_RPS }],
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: `p(95)<${BREAK_P95}`, abortOnFail: true, delayAbortEval: '20s' }],
    http_req_failed: [{ threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '20s' }],
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(95)', 'p(99)', 'max'],
};

// 409 on a taken slot is a correct answer for `book`.
http.setResponseCallback(http.expectedStatuses({ min: 200, max: 299 }, 409));

export function setup() {
  // Sign in a pool of drivers up front so `login` isn't part of the measurement (except TARGET=login).
  const tokens = TARGET === 'login' ? [] : FIXTURE.drivers.slice(0, 50).map((email) => login(email));
  return { tokens };
}

const listingUrl = () => `${BASE_URL}/v1/listings/${pick(FIXTURE.listings)}`;

export default function (data) {
  const tok = data.tokens.length ? data.tokens[(__VU + __ITER) % data.tokens.length] : null;
  let res;
  switch (TARGET) {
    case 'search': {
      const p = randomPoint();
      res = http.get(`${BASE_URL}/v1/listings?latitude=${p.latitude}&longitude=${p.longitude}&radius_km=3`, {
        tags: { name: 'GET /v1/listings' },
      });
      break;
    }
    case 'detail':
      res = http.get(listingUrl(), { tags: { name: 'GET /v1/listings/{id}' } });
      break;
    case 'reviews':
      res = http.get(`${listingUrl()}/reviews`, { tags: { name: 'GET /v1/listings/{id}/reviews' } });
      break;
    case 'config':
      res = http.get(`${BASE_URL}/v1/config`, { tags: { name: 'GET /v1/config' } });
      break;
    case 'quote':
      res = http.post(`${BASE_URL}/v1/bookings/quote`, JSON.stringify({ listing_id: pick(FIXTURE.listings), ...randomWindow() }), {
        headers: { 'Content-Type': 'application/json' },
        tags: { name: 'POST /v1/bookings/quote' },
      });
      break;
    case 'book':
      res = http.post(`${BASE_URL}/v1/bookings`, JSON.stringify({ listing_id: pick(FIXTURE.listings), ...randomWindow() }), {
        ...authHeaders(tok, { 'Idempotency-Key': uuid() }),
        tags: { name: 'POST /v1/bookings' },
      });
      break;
    case 'me':
      res = http.get(`${BASE_URL}/v1/me`, { ...authHeaders(tok), tags: { name: 'GET /v1/me' } });
      break;
    case 'bookings':
      res = http.get(`${BASE_URL}/v1/bookings?limit=20`, { ...authHeaders(tok), tags: { name: 'GET /v1/bookings' } });
      break;
    case 'login':
      res = http.post(
        `${BASE_URL}/v1/auth/login`,
        JSON.stringify({ email: pick(FIXTURE.drivers), password: FIXTURE.password }),
        { headers: { 'Content-Type': 'application/json' }, tags: { name: 'POST /v1/auth/login' } },
      );
      break;
    default:
      throw new Error(`unknown TARGET ${TARGET}`);
  }
  check(res, { 'expected status': (r) => (r.status >= 200 && r.status < 300) || r.status === 409 });
}
