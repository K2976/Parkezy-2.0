# Security Policy

## Supported versions

Security fixes go into the latest release of the Android app and into the backend that is currently deployed.

| Component | Supported |
|---|---|
| Android app, latest release ([v1.1.x](https://github.com/honoursbhaduria/Parkezy-2.0/releases/latest)) | ✅ |
| Older app releases | ❌ (please update) |
| Backend API (`parkezy-api.onrender.com`) and website | ✅ |
| `parkezy-2.0/` (archived iOS prototype) | ❌ |

## Reporting a vulnerability

**Please do not open a public issue.** Report privately through
[GitHub security advisories](https://github.com/honoursbhaduria/Parkezy-2.0/security/advisories/new).

Include what you found, the steps to reproduce it, and the impact you expect. Screenshots or a short proof of
concept help.

What to expect:

- An acknowledgement within **3 days**.
- An assessment and a plan within **7 days**.
- A fix as soon as practical, and credit in the release notes if you would like it.

## Scope

In scope: the API, the Android app, the website, and anything in this repository.

Please **do not**:

- access, change or delete other people's data, or make real payments;
- run denial-of-service, spam or social-engineering attacks;
- test against accounts you do not own. Create your own test accounts instead.

Good-faith research that follows these rules is welcome, and we will not pursue it.

## How Parkezy protects users

Passwords are hashed with argon2id; sessions use short-lived tokens with rotating refresh tokens and reuse
detection; logins are protected by rate limits and adaptive abuse protection; payments and webhooks are
signature-verified; gate QR codes are single-use; and no secrets are stored in this repository. The
[security docs](https://parkezy-landing.vercel.app/docs/security) explain each of these.
