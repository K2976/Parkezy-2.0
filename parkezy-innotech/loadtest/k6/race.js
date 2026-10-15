// Double-booking race: N drivers try to book the SAME slot for the SAME time at the same instant.
// Correct result: exactly one 201, everyone else 409 slot_unavailable, zero 5xx.
//   ./loadtest/k6.sh race -e RACERS=200
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';
import { BASE_URL, FIXTURE } from './lib/config.js';
import { authHeaders, login, window } from './lib/api.js';

const RACERS = Number(__ENV.RACERS || 100);
const wins = new Counter('race_wins');
const losses = new Counter('race_losses');
const errors = new Counter('race_errors');

export const options = {
  scenarios: { race: { executor: 'per-vu-iterations', vus: RACERS, iterations: 1, maxDuration: '2m' } },
  thresholds: {
    race_wins: ['count==1'],
    race_errors: ['count==0'],
    [`race_losses`]: [`count==${RACERS - 1}`],
  },
};

http.setResponseCallback(http.expectedStatuses({ min: 200, max: 299 }, 409));

export function setup() {
  // A fresh random window each run, so repeated runs don't collide with earlier winners.
  const win = window(24 + Math.floor(Math.random() * 24 * 25), 2);
  return { win, fireAt: Date.now() + 15000 + RACERS * 60 }; // time for every VU to sign in first
}

export default function (data) {
  const tok = login();
  const wait = (data.fireAt - Date.now()) / 1000;
  if (wait > 0) sleep(wait); // everyone fires together
  const res = http.post(
    `${BASE_URL}/v1/bookings`,
    JSON.stringify({ listing_id: FIXTURE.race_listing.id, slot_id: FIXTURE.race_listing.slot_id, ...data.win }),
    { ...authHeaders(tok, { 'Idempotency-Key': `race-${__VU}-${data.fireAt}` }), tags: { name: 'POST /v1/bookings (race)' } },
  );
  if (res.status === 201) wins.add(1);
  else if (res.status === 409) losses.add(1);
  else errors.add(1);
  check(res, { 'race 201 or 409': (r) => r.status === 201 || r.status === 409 });
}
