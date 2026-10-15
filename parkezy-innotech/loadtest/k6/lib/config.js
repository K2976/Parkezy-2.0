// Shared settings for every k6 script. Override with -e, e.g. ./loadtest/k6.sh booking -e PROFILE=stress
import { SharedArray } from 'k6/data';

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8001';
export const PROFILE = __ENV.PROFILE || 'smoke';

// Written by loadtest/seed.py. SharedArray: parsed once, shared read-only by every VU.
const fixture = new SharedArray('fixture', () => [JSON.parse(open('/data/users.json'))]);
export const FIXTURE = fixture[0];

// Load shapes (ramping-vus stages). Pick with -e PROFILE=...; VUS scales the peak.
const PEAK = Number(__ENV.VUS || 50);
export const PROFILES = {
  smoke: [{ duration: '30s', target: 2 }],
  load: [
    { duration: '1m', target: PEAK },
    { duration: '5m', target: PEAK },
    { duration: '30s', target: 0 },
  ],
  stress: [
    { duration: '1m', target: PEAK },
    { duration: '2m', target: PEAK * 2 },
    { duration: '2m', target: PEAK * 4 },
    { duration: '2m', target: PEAK * 6 },
    { duration: '1m', target: 0 },
  ],
  spike: [
    { duration: '30s', target: Math.ceil(PEAK / 5) },
    { duration: '10s', target: PEAK * 6 },
    { duration: '1m', target: PEAK * 6 },
    { duration: '10s', target: Math.ceil(PEAK / 5) },
    { duration: '1m', target: Math.ceil(PEAK / 5) },
    { duration: '10s', target: 0 },
  ],
  soak: [
    { duration: '2m', target: PEAK },
    { duration: __ENV.SOAK_DURATION || '1h', target: PEAK },
    { duration: '1m', target: 0 },
  ],
};

export function stages() {
  const s = PROFILES[PROFILE];
  if (!s) throw new Error(`unknown PROFILE "${PROFILE}" (use ${Object.keys(PROFILES).join(', ')})`);
  return s;
}

// Pass/fail limits shared by the scripts. http_req_failed counts only UNEXPECTED statuses
// (each script declares which non-2xx answers are correct behaviour, e.g. a 409 on a taken slot).
export const BASE_THRESHOLDS = {
  http_req_failed: ['rate<0.01'],
  checks: ['rate>0.99'],
};
