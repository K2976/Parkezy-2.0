// Anonymous browsing: map search, listing detail, reviews, config. The highest-traffic path.
//   ./loadtest/k6.sh search -e PROFILE=load -e VUS=100
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { BASE_THRESHOLDS, BASE_URL, FIXTURE, stages } from './lib/config.js';
import { pick, randomPoint, randomWindow } from './lib/api.js';

export const options = {
  scenarios: { browse: { executor: 'ramping-vus', startVUs: 0, stages: stages(), gracefulRampDown: '10s' } },
  thresholds: {
    ...BASE_THRESHOLDS,
    'http_req_duration{name:GET /v1/listings}': ['p(95)<400'],
    'http_req_duration{name:GET /v1/listings/{id}}': ['p(95)<300'],
    'http_req_duration{name:GET /v1/listings/{id}/reviews}': ['p(95)<300'],
  },
};

export default function () {
  group('search', () => {
    const p = randomPoint();
    const params = { latitude: p.latitude, longitude: p.longitude, radius_km: pick([1, 2, 3, 5]) };
    if (Math.random() < 0.5) Object.assign(params, randomWindow()); // availability-aware search
    if (Math.random() < 0.2) params.sort = 'price';
    const qs = Object.entries(params).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
    const res = http.get(`${BASE_URL}/v1/listings?${qs}`, { tags: { name: 'GET /v1/listings' } });
    check(res, { 'search 200': (r) => r.status === 200 });
    const results = res.status === 200 ? res.json() : [];
    sleep(Math.random() * 1.5 + 0.5);

    const id = results.length ? pick(results).id : pick(FIXTURE.listings);
    const detail = http.get(`${BASE_URL}/v1/listings/${id}`, { tags: { name: 'GET /v1/listings/{id}' } });
    check(detail, { 'detail 200': (r) => r.status === 200 });
    const reviews = http.get(`${BASE_URL}/v1/listings/${id}/reviews`, {
      tags: { name: 'GET /v1/listings/{id}/reviews' },
    });
    check(reviews, { 'reviews 200': (r) => r.status === 200 });
  });
  if (Math.random() < 0.1) {
    check(http.get(`${BASE_URL}/v1/config`, { tags: { name: 'GET /v1/config' } }), { 'config 200': (r) => r.status === 200 });
  }
  sleep(Math.random() * 2 + 1); // think time
}
