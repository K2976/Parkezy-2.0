# Login abuse protection

Code: `app/services/login_protection.py` (risk check), `app/integrations/challenge.py` (CAPTCHA),
`app/api/v1/auth.py` (`POST /v1/auth/login`). Tests: `tests/test_login_protection.py`.

## Request flow

```
POST /v1/auth/login
  1. body validation (pydantic: email format, password <= 128 chars, token <= 2048) and 1 MiB body cap
  2. per-IP auth limit (route dependency) + per-account attempt limit       existing, unchanged
  3. LoginProtection.check()        one Redis MULTI/EXEC round trip, ~1 ms locally
       hard ceilings per subnet / device / whole service      -> 429 + Retry-After
       risk score from failure history                         -> LOW | MEDIUM | HIGH
       HIGH                                                    -> 429 + Retry-After (temporary)
       MEDIUM, no challenge_token                              -> 403 challenge_required
       MEDIUM, token replayed / rejected by provider           -> 403 challenge_failed
       MEDIUM, no provider configured                          -> 429, short Retry-After
  4. argon2 verify (always exactly one, dummy hash for unknown emails)  ~70 ms CPU
  5. record_failure() or record_success()   one more round trip
```

Requests stopped in step 2 or 3 never reach argon2. A request that is allowed through is always
fully password-verified; nothing skips or weakens the hash.

## Signals and scoring

Each rule adds `weight * min(cap, value // threshold)` points (`score()` is a pure function).

| Signal | Meaning | threshold | weight | cap | max |
|---|---|---|---|---|---|
| `account_failures` | failed logins on this email, any IP, last `LOGIN_FAILURE_WINDOW_SECONDS` | 5 | 25 | 3 | 75 |
| `ip_failures` | failed logins from this IP | 5 | 20 | 3 | 60 |
| `subnet_failures` | from this IPv4 /24 or IPv6 /64 | 20 | 15 | 3 | 45 |
| `device_failures` | from this `X-Device-Id` | 5 | 20 | 3 | 60 |
| `ip_distinct_accounts` | accounts that **failed** from this IP | 4 | 25 | 3 | 75 |
| `account_distinct_ips` | IPs that **failed** on this account | 5 | 20 | 3 | 60 |
| `global_failures` | failed logins service-wide in `RATE_LIMIT_WINDOW_SECONDS` | 100 | 15 | 3 | 45 |
| `automation_user_agent` | curl, python-requests, headless browsers… | 1 | 15 | 1 | 15 |
| `missing_user_agent` | no User-Agent | 1 | 10 | 1 | 10 |
| `known_device` | this device signed in to this account before | 1 | **-30** | 1 | -30 |

`LOGIN_RISK_MEDIUM_SCORE=40`, `LOGIN_RISK_HIGH_SCORE=80`. No single signal can reach HIGH on its
own (largest is 75); HIGH needs independent signals together. The score is floored at 0.

What that means in practice (default rules):

* 1-4 typos: LOW. The 6th attempt after 5 failures from the same IP: MEDIUM (challenge).
* 10 failures on one account from one IP: HIGH until the window slides.
* One IP failing on 5 different accounts: MEDIUM on the next attempt.
* Botnet, one guess per IP per account: per-IP signals stay low, but `global_failures` rises; at 100+
  failures a minute every unknown device gets +15 to +45, so many attempts become MEDIUM, while
  users on a known device keep signing in normally.
* An attacker hammering a victim's email from many IPs gets HIGH; the victim on their usual phone
  (known device, -30) is only challenged, never locked out. Nothing is permanent: every counter expires.

Successful sign-ins are not counted in the spread signals, so a campus or carrier NAT with many real
users does not look like credential stuffing. A success also clears that account's failure count.

## Configuration

All optional; defaults shown.

```
LOGIN_PROTECTION_ENABLED=true
LOGIN_FAILURE_WINDOW_SECONDS=900
LOGIN_SUBNET_ATTEMPTS_PER_WINDOW=60        # per RATE_LIMIT_WINDOW_SECONDS (60)
LOGIN_DEVICE_ATTEMPTS_PER_WINDOW=20
LOGIN_GLOBAL_ATTEMPTS_PER_WINDOW=3000
LOGIN_RISK_MEDIUM_SCORE=40
LOGIN_RISK_HIGH_SCORE=80
LOGIN_RISK_RULES={}                         # JSON; only the keys you give replace defaults
LOGIN_THROTTLE_RETRY_SECONDS=120            # Retry-After for HIGH
LOGIN_KNOWN_DEVICE_TTL_DAYS=90
LOGIN_FALLBACK_ATTEMPTS_PER_WINDOW=20       # per process, only while Redis is down
LOGIN_CHALLENGE_PROVIDER=none               # none | turnstile
LOGIN_CHALLENGE_UNAVAILABLE_RETRY_SECONDS=30
LOGIN_CHALLENGE_ACTION=login
LOGIN_CHALLENGE_MAX_AGE_SECONDS=300
LOGIN_CHALLENGE_EXPECTED_HOSTNAMES=         # comma-separated, empty = not checked
TURNSTILE_SITE_KEY=
TURNSTILE_SECRET_KEY=                       # secret: Render dashboard only
```

Example override: `LOGIN_RISK_RULES={"account_failures": {"threshold": 3, "weight": 30}}`.
The app refuses to start on unknown rule names, `HIGH <= MEDIUM`, or `turnstile` without both keys.

No database migration is needed: all state is in Redis with TTLs.

## Enabling the CAPTCHA (Cloudflare Turnstile)

Without a provider, MEDIUM risk is a 30 s slow-down. That is safe but blunt (a legitimate user
whose account is under attack waits instead of solving a challenge), so configuring one is recommended.

1. Cloudflare dashboard → Turnstile → add a widget (Managed mode). Note the site key and secret.
2. Render: `LOGIN_CHALLENGE_PROVIDER=turnstile`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, and
   `LOGIN_CHALLENGE_EXPECTED_HOSTNAMES` set to the hostname of the page that renders the widget.
3. Client contract: on `403` with `error.code` `challenge_required` or `challenge_failed`, render the
   widget using `error.details.site_key` (action `login`), then repeat the login with
   `"challenge_token": "<token>"`. Each token works once. The mobile app needs a WebView screen for
   this (not built yet).

Accessible fallback: Turnstile's managed mode is usually invisible and has accessible modes. A user
who still cannot pass it can sign in with Google, or use "Forgot password", which goes through
email instead of a challenge. Both have their own limits.

## Observability

Security events (logger `parkezy.security`, JSON field `security`): `login_risk` (level, score,
reasons), `login_rejected`, `login_challenge_required` / `_passed` / `_failed`, `login_failure`,
`login_success`, `login_failure_spike` (once per window). They carry 12-character HMAC prefixes of
the account and IP, never the email, IP, password or tokens. Reasons and scores are only in logs.

Prometheus (`/metrics`):

* `parkezy_login_attempts_total{outcome}`: success, invalid_credentials, challenged,
  challenge_failed, throttled, rate_limited
* `parkezy_login_risk_total{level}`
* `parkezy_login_challenge_verifications_total{result}`: passed, failed, replayed
* `parkezy_password_verify_seconds`: argon2 time including the wait for a hashing slot
* `parkezy_login_protection_degraded_total`: checks done without Redis

## Tuning with real traffic

1. Run a week with defaults and watch `parkezy_login_risk_total` and the `login_risk` reasons.
2. Challenge rate for normal users = `challenged / (success + invalid_credentials)`. Above ~1-2 %
   outside attacks means thresholds are too tight: raise `threshold` of the signal that dominates
   the reasons (often `ip_failures` behind big NATs, or `subnet_failures` on mobile carriers).
3. During an attack, check that `invalid_credentials` stops growing while `throttled`/`challenged`
   rise. If attackers still get through, lower `global_failures.threshold` to around 3-5x your
   normal failures per minute.
4. If `parkezy_password_verify_seconds` p95 climbs well above ~0.1 s, hashing slots are saturated:
   lower `LOGIN_GLOBAL_ATTEMPTS_PER_WINDOW`, or add instances / `PASSWORD_HASH_CONCURRENCY`.

## Threat model

| Threat | Mitigation | Residual risk |
|---|---|---|
| Credential stuffing from a few sources | ip/subnet failures, distinct failed accounts per IP, hard subnet ceiling | Shared NATs can be challenged after several failures |
| Distributed bots (one guess per IP) | account-level counters, distinct IPs per account, service-wide failure spike raises everyone's score | A very slow, wide botnet below `global_failures.threshold` looks like normal traffic; per-account limits still cap guesses per account |
| Account lockout abuse | no permanent lockout, every counter expires, known device lowers score, MEDIUM is a challenge | Without a CAPTCHA provider the victim waits through 30 s slow-downs; attackers can force challenges on a victim |
| CPU exhaustion via argon2 | rejected requests never hash; hashing concurrency is bounded; global attempt ceiling | Requests allowed through still cost ~70 ms each; capacity planning still matters |
| Account enumeration | identical 401 body and headers; dummy-hash verify for unknown emails; risk ignores account existence | Latency noise from the network and queueing; not a constant-time guarantee |
| Header spoofing | X-Forwarded-For only when `TRUST_FORWARDED_FOR=true`, and only its last hop; User-Agent only adds points | If the platform's proxy setup differs from that assumption, all users could share one "IP" |

## Must be validated in production

* **Client IP on Render.** Confirm the last `X-Forwarded-For` hop is the real client and not an edge
  proxy (log a few requests from known IPs). If it is a shared proxy address, per-IP and subnet
  signals would lump all users together.
* **Redis memory.** About 8 short-lived keys per failed attempt (about 3 MB per 1,000), all expiring
  within 2 × `LOGIN_FAILURE_WINDOW_SECONDS`. A large attack can fill a 30 MB free Redis; set the
  eviction policy to `volatile-ttl` or `volatile-lru` so these keys are evicted first, and watch memory.
* **Latency.** Two extra Redis round trips per login. Locally ~1 ms each; Render (Oregon) to Redis
  (Ohio) is ~50 ms each.
* **Thresholds.** The defaults are reasoned, not measured on Parkezy traffic. Tune them with the
  metrics above.
