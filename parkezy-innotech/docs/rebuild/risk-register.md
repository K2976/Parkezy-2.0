# Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Owner/Milestone |
|---|---|---|---|---|---|
| R-01 | Live schema/RLS are not in version control (only a May-2026 snapshot of 5 tables survives in git history) and the DB was unreachable (hibernated/auth failure) → cannot reproduce or audit the backend | High | High | Restore access; export `pg_dump --schema-only` + policies in M-00; commit as migrations | M-00 |
| R-02 | Hidden permissive RLS leaves data modifiable by any signed-in user | Medium | High | pgTAP negative tests before UI work; run Supabase security advisors | M-01 |
| R-03 | Double-booking / overbooking at launch | High (today) | High | Exclusion constraint + RPC; concurrency test T-12 | M-04 |
| R-04 | App Store rejection: account deletion, missing usage strings, placeholder privacy URL, missing icon, Apple Sign-In entitlement | High | High | Checklist items owned in M-01 (strings/entitlements/icon) and M-08 | M-01/M-08 |
| R-05 | Payments/compliance scope underestimated | Medium | High | Decide Q-01 early; use provider-hosted flows; webhook idempotency | M-07 |
| R-06 | Scope creep from legacy "feature-complete" docs that overstate reality | High | Medium | Trust this inventory; one milestone at a time | all |
| R-07 | Single maintainer / knowledge only in chat history | Medium | High | `PROJECT_CONTEXT.md`, ADRs, CLAUDE.md | all |
| R-08 | Supabase free-tier pause or limits break demos/CI | Medium | Medium | Dedicated staging project or local stack; paid tier for prod | M-01 |
| R-09 | iOS 26.5 deployment target excludes most devices | Medium | Medium | Decide Q-04 | M-01 |
| R-10 | Secrets in git history (legacy Django key, Firebase plist) | Low | Low | Rotate if still valid; keep new repo clean; secret scanning in CI | M-01 |
| R-11 | Geofence/background location and push need entitlements/review | Medium | Medium | Prove on device early in M-05/M-06 | M-05 |
| R-12 | Data privacy (phones, locations, vehicle numbers) under Indian DPDP Act | Medium | Medium | Data minimization, retention policy, deletion function (Q-07) | M-08 |
