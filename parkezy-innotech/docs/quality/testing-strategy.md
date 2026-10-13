# Testing Strategy

## Existing testing infrastructure (verified)
None. No XCTest/Swift Testing target in `project.pbxproj`, no test files, no UI-test target, no CI, no fixtures. `MockDataService.swift` and the simulator-detection branches (`EmulatorDetector`) are *demo* helpers, not tests. **No tests were run in this investigation.**

## Recommended pyramid for the rebuild
| Level | Tool | Scope |
|---|---|---|
| Unit | Swift Testing / XCTest | Pricing, GST, overstay, validation, QR token parsing, view-model state machines with fake repositories |
| Database / RLS | pgTAP or SQL tests via `supabase test db`, run against a local/branch DB | Policies, constraints, RPCs, triggers |
| Contract / integration | XCTest against a Supabase branch or local stack | Repository ↔ PostgREST/RPC schemas, error mapping |
| UI | XCUITest | Navigation graph, forms, empty/error/loading states, accessibility identifiers |
| End-to-end | XCUITest + seeded backend | Journeys J-01…J-08 |
| Security regression | pgTAP + script | RLS negative tests, capability escalation, PIN brute-force, QR replay |
| Performance | XCTest metrics | Map with N=5 000 markers, list scrolling, cold start |
| Build/deploy | CI (`xcodebuild test`, `supabase db lint`) | Every PR |

## Test scenarios (rebuild)
| ID | Feature/Req | Level | Preconditions | Action | Expected | Edge cases |
|---|---|---|---|---|---|---|
| T-01 | F-01 | UI/E2E | New email | Sign up with valid data | Account created; if confirmation required show "check email" and stay logged out | weak password (<8), invalid email, duplicate email, offline |
| T-02 | F-01/F-03 | Integration | Logged-in, relaunch | Cold start | Session restored; profile loaded; no flash of login | expired refresh token → login |
| T-03 | F-02 | Manual/device | Entitlement set | Apple sign-in | Session created; name stored first time | cancel, revoked credential |
| T-04 | F-05 | Unit/UI | User A logged in with data | Sign out, sign in as B | No A data visible (BUG-07) | fast switching |
| T-05 | F-06 | E2E | Test user with listings/bookings | Delete account | Auth user + data removed/anonymized; login fails | active booking blocks deletion? (Q-07) |
| T-10 | F-20 | Integration | 3 facilities in/out of viewport | Open map | Only viewport rows fetched, paginated | no results, fetch failure shows error not empty |
| T-11 | F-24/BR-02 | Unit | Rate 60, 2 h | Compute total | 60×2 + 18% GST, server == client display | 0.5 h step, slot multiplier |
| T-12 | BUG-06 | DB/Integration | Two drivers, one slot | Book simultaneously | Exactly one succeeds; other gets conflict | overlapping intervals, adjacent intervals allowed |
| T-13 | F-26/F-44 | E2E | Private listing, manual approval | Driver requests → host approves | Driver sees approval, PIN issued, slot reserved | reject, expiry, auto-accept |
| T-14 | F-41 | UI/device | Real device | Add listing | Real photos captured and uploaded; listing visible | permission denied, large image, offline retry |
| T-15 | F-42 | UI | Own listing | Edit price | Persisted; other user cannot edit (T-31) | |
| T-20 | PIN | Unit/Security | Booking with PIN | 3 wrong attempts | Lockout/throttle server-side | replay after expiry |
| T-21 | F-46 | Unit/E2E | Signed QR | Scan valid/expired/forged/other-host | Accept/reject accordingly | screenshot replay |
| T-22 | BR-05 | Unit | End 20 min late | Compute fee | ₹40 (2 started 15-min blocks) | exact boundary, early end |
| T-30 | SEC-02 | RLS | Authenticated user | `update profiles set capabilities…` | Denied | other user's row |
| T-31 | SEC-08 | RLS | User A | Update/delete user B's listing/booking | Denied | with forged `owner_id` on insert |
| T-32 | SEC-03 | RLS | Anonymous | `select access_pin` anywhere | Denied/absent | |
| T-33 | SEC-11 | RLS | Anonymous (anon key only) | `select email, phone_number from profiles` | Zero rows / permission denied | authenticated user reading other users |
| T-40 | F-60 | UI | Airplane mode | Launch/refresh | Offline banner, cached data, actionable errors | flapping |
| T-41 | A11y | UI | VoiceOver, largest Dynamic Type | Traverse key screens | Labels present, no truncation | |
| T-60 | Payments (M-07) | Integration | Test-mode provider | Pay for booking | Booking `confirmed` only after webhook; duplicate webhook is idempotent | declined card, timeout, refund (T-61) |
| T-61 | Payments | Integration | Paid booking | Cancel within policy | Refund recorded in ledger | partial refund |
| T-62 | F-48 (M-10) | Unit/DB | Ledger rows | Compute host earnings | Equals sum of host payouts; no random data | no bookings |
| T-50 | Build | CI | Clean checkout | `xcodebuild build test` | Green on required Xcode version | |

## Existing-behavior characterization (do before deleting legacy code)
Because the legacy flow is unreachable, no characterization tests are needed; instead treat [business-rules](../product/business-rules.md) as the spec and confirm each rule with the product owner (Q-03).

## Safe verification of audit findings (non-destructive)
Compile on a machine with Xcode (BUG-01); inspect generated Info.plist keys (BUG-03); run on a device and open Add Parking (BUG-04); on a **Supabase branch**, run T-30..T-32 (SEC-01/02/03).
