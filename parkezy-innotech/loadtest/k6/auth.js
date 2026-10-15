// Sign-in throughput. Password hashing (argon2) is deliberately expensive, so this finds how many
// logins per second the API can absorb (e.g. everyone opening the app after a push notification).
//   ./loadtest/k6.sh auth -e PROFILE=load -e VUS=20
import { sleep } from 'k6';
import { BASE_THRESHOLDS, stages } from './lib/config.js';
import { driverEmail, login } from './lib/api.js';

export const options = {
  scenarios: { logins: { executor: 'ramping-vus', startVUs: 0, stages: stages(), gracefulRampDown: '10s' } },
  thresholds: { ...BASE_THRESHOLDS, 'http_req_duration{name:POST /v1/auth/login}': ['p(95)<1000'] },
};

export default function () {
  login(driverEmail(__ITER));
  sleep(Math.random() + 0.5);
}
