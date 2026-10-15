import http from 'k6/http';
import { check, fail } from 'k6';
import { BASE_URL, FIXTURE } from './config.js';

export const JSON_HEADERS = { 'Content-Type': 'application/json' };

export function uuid() {
  // RFC 4122 v4-ish; good enough for Idempotency-Key values.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function authHeaders(token, extra = {}) {
  return { headers: { ...JSON_HEADERS, Authorization: `Bearer ${token}`, ...extra } };
}

// Each VU signs in ONCE as its own seeded driver and reuses the token (argon2 is slow on purpose,
// so logging in every iteration would benchmark password hashing, not the API).
let session = null;

export function driverEmail(offset = 0) {
  const drivers = FIXTURE.drivers;
  return drivers[(__VU - 1 + offset) % drivers.length];
}

export function login(email = driverEmail()) {
  const res = http.post(
    `${BASE_URL}/v1/auth/login`,
    JSON.stringify({ email, password: FIXTURE.password }),
    { headers: JSON_HEADERS, tags: { name: 'POST /v1/auth/login' } },
  );
  if (!check(res, { 'login 200': (r) => r.status === 200 })) {
    fail(`login failed for ${email}: ${res.status} ${res.body}`);
  }
  return res.json('tokens.access_token');
}

export function token() {
  if (!session) session = login();
  return session;
}

export function relogin() {
  session = login();
  return session;
}

// Booking windows must sit on the 15-minute grid, start in the future and within 30 days.
export function window(startInHours, hours) {
  const step = 15 * 60 * 1000;
  const start = Math.ceil((Date.now() + startInHours * 3600 * 1000) / step) * step;
  return { starts_at: new Date(start).toISOString(), ends_at: new Date(start + hours * 3600 * 1000).toISOString() };
}

export function randomWindow() {
  const startIn = 1 + Math.random() * 24 * 25; // 1 h .. 25 days ahead
  const hours = [1, 1.5, 2, 3, 4][Math.floor(Math.random() * 5)];
  return window(startIn, hours);
}

export function randomPoint(spreadDeg = 0.1) {
  const [lat, lng] = FIXTURE.center;
  return { latitude: lat + (Math.random() * 2 - 1) * spreadDeg, longitude: lng + (Math.random() * 2 - 1) * spreadDeg };
}

export function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}
