# Audit Findings

Method: static reading of the 50 Swift files, `project.pbxproj`, git history (including the historical `supabase_schema.sql`), and a failed attempt to inspect the live Supabase DB. `swiftc -parse` (syntax only) passes on all files; **nothing was compiled or executed.** "Confidence" = confidence the finding is true; *High (static)* means certain from the source text but not compiler/runtime-confirmed. "Blocks rebuild?" = must be resolved or consciously designed around before/during the rebuild.

## Summary
Counts cover SEC-xx and BUG-xx (34 findings); GAP and DEBT items are listed separately.

| Severity | Count |
|---|---:|
| Critical | 0 confirmed (SEC-01/SEC-11 may rise once live RLS is read) |
| High | 14 |
| Medium | 13 |
| Low | 7 |

## Security
| ID | Sev | Conf | Finding | Evidence | Impact | Verify safely | Fix | Blocks? |
|---|---|---|---|---|---|---|---|---|
| SEC-01 | High | Medium | Live schema/RLS unverified (DB unreachable) and current schema is not in version control. Historical DDL (`git show e72c855:supabase_schema.sql`) covers 5 of 8 tables; `parking_spots`, `private_bookings`, `commercial_bookings` have **no DDL anywhere**, so their RLS (and existence) is unknown. The app has no server logic, so RLS is the sole authorization layer | no `.sql` at HEAD; MCP `list_tables` auth failures ×4 | Unknown exposure on the three undocumented tables | Restore DB access; `select * from pg_policies`; Supabase security advisors | Version all schema/RLS in `supabase/migrations`; deny-by-default | **Yes** |
| SEC-02 | High | High (historical DDL; live unverified) | `profiles` UPDATE policy is `using (auth.uid() = id)` with no `WITH CHECK` or column restriction, so any user can rewrite their own `capabilities` and `stats` (earnings, rating) via PostgREST; the app itself does this client-side | `e72c855:supabase_schema.sql`, `AuthViewModel.enablePrivateHosting` | Privilege escalation; forged stats | On a branch DB, update own `capabilities` as a test user | Server-only capability grant; column privileges | Yes |
| SEC-03 | High | High (static) | Access PINs: client-generated with `Int.random`; legacy `parking_spots.access_pin` (table has no DDL in git) would be part of the row every client downloads; fallback PIN `"428915"` hard-coded; PIN displayed on screen as "Demo PIN" | `BookingViewModel.createBooking`, `ParkingSpot.accessPIN`, `PINEntryView` | Anyone can enter any private spot | Inspect network response of `parking_spots` | Server-issued per-booking codes, hash at rest, attempt throttling | Yes |
| SEC-04 | Medium | High | QR payload is `PARKEZY:{bookingID}:{spotID}`, unsigned; IDs are guessable only via leaks but QR can be copied/forged | `QRCodeService` | Forged entry/exit | Static | Signed, short-lived tokens | Yes |
| SEC-05 | High | High (static + historical DDL) | Account deletion deletes the `profiles` row via PostgREST, but the historical DDL has **no DELETE policy on `profiles`** (RLS silently affects 0 rows), the FKs from `private_listings`/`bookings` have no cascade, and `auth.users` is untouched; code likely does not compile and the UI is unreachable → App Store 5.1.1(v) risk (old checklist wrongly says compliant) | `AuthViewModel.deleteAccount`, `SettingsView` unreachable | Policy rejection; privacy-law exposure | Static | Edge Function with service role deleting the auth user + cascading/anonymizing data | Yes |
| SEC-06 | Low | High | `.claude/settings.local.json` tracked despite ignore; legacy Django `SECRET_KEY` (commits `226f9d5`, `35be30d`) and Firebase plist remain in git history | `git log -G` (values not printed) | Residual secret exposure if reused | n/a | Rotate if still in use; `git rm --cached`; consider history purge only if the repo is public | No |
| SEC-07 | Medium | High (static) | No entitlements file → the Sign in with Apple button offered on the login screen cannot work (capability absent) | `project.pbxproj` has no `CODE_SIGN_ENTITLEMENTS` | Apple sign-in fails at runtime | Run on device | Add capability (or remove the button) | No |
| SEC-08 | High | High (historical DDL for `bookings`) | All business values (prices, totals, statuses, `owner_id`, `driver_id`, ratings) are chosen by the client; the historical `bookings` UPDATE policy has no `WITH CHECK`, so a driver can rewrite `total_cost`/`status`/`access_code` after creation; driver/owner ids fall back to random `UUID()` in the app; `rating` defaults to 5.0 and is owner-writable | `CommercialParkingViewModel.bookSlot`, `PrivateParkingViewModel.requestBooking`, `createListingLocally`, DDL | Fraud, orphaned rows, data integrity | Review live RLS `with check` | Server RPCs compute everything | Yes |
| SEC-09 | Low | Medium | PII denormalized: driver phone in `private_bookings`, owner name in public listings; no privacy policy URL (`YOUR_PRIVACY_POLICY_URL`) | models, `AppConfig` | Privacy | Static | Minimize, add policy | No |
| SEC-10 | Low | High | Single hard-coded environment | `SupabaseConfig.swift` | Cannot separate dev/prod; key rotation requires rebuild | Static | `.xcconfig` per scheme | No |
| SEC-11 | High | High (historical DDL; live unverified) | `profiles` SELECT policy is `using (true)`: **anyone, including unauthenticated callers with the anon key, can read every user's email and phone number** | `e72c855:supabase_schema.sql` | PII leak / harvesting | `select email, phone_number from profiles` with the anon key on a branch | Own-row select + a public view with non-PII fields | Yes |
| SEC-12 | Medium | High (historical DDL) | `commercial_facilities` and `private_listings` accept inserts from any signed-in user (`FOR ALL using (auth.uid() = owner_id)`), with no capability/verification check, so anyone can publish a fake "commercial facility" with arbitrary rating | DDL | Fake supply, fraud | Branch DB test | Host verification + server-side creation | Yes |

## Defects
| ID | Sev | Conf | Finding | Evidence | Blocks? |
|---|---|---|---|---|---|
| BUG-01 | High | High (static) | `user.id.uuidString` where `AppUser.id` is `String` → likely compile error; no `String.uuidString` extension exists | `AuthViewModel.swift:154`, `AppUser.swift` | No (code is being replaced) |
| BUG-02 | High | High | ≈39% of code is unreachable: legacy session/payment/QR/PIN/receipt/dispute flow, Settings (incl. sign-out alt, delete account), QR scanner, location picker | reachability grep, [codebase-map](../architecture/codebase-map.md) | Yes (scope decision Q-02) |
| BUG-03 | High | High (static) | No `NSCameraUsageDescription` / `NSLocationWhenInUseUsageDescription` / photo strings in generated Info.plist → iOS terminates the app on first camera/location request | `project.pbxproj` `INFOPLIST_KEY_*` list | Yes |
| BUG-04 | High | High (static) | On a physical device the Add Listing media step cannot be completed: `showingPhotoCapture` is set but never observed; simulator uses placeholders | `AddParkingFlowView.swift:518,711` | Yes |
| BUG-05 | High | High | Host earnings/bookings use the wrong source: `HostViewModel` reads driver-style `bookings` rows with `user_id = host` and `type='private'`; `ownedSpots` is never populated (every scan = wrong host); "earnings" = 12/15% commission of total (the platform's cut) | `HostViewModel.swift` | Yes |
| BUG-06 | High | High | No double-booking protection: slot occupancy mutated only in client memory, not persisted to facility/listing rows; booking inserts are fire-and-forget; no server uniqueness/overlap constraint | `CommercialParkingViewModel.bookSlot`, `SupabaseService` (no facility/listing slot write) | Yes |
| BUG-07 | Medium | High | View models survive sign-out; `PrivateParkingViewModel.currentUser` is only fetched `if nil` → next account sees previous user's identity/listings | `ParkezyApp`, `PrivateParkingViewModel.refresh…` | Yes |
| BUG-08 | Medium | High | New listings get randomly occupied slots (`generatePrivateSlots`); private-mode listings save `hourlyRate = 0` (free); `owner_id` may be a random UUID | `PrivateParkingViewModel`, `AddParkingFlowView` | Yes |
| BUG-09 | Medium | Medium | Sign-up marks the user authenticated even when no session exists (email-confirmation enabled) | `AuthViewModel.signUp` | No |
| BUG-10 | Medium | High | Notification permission is never requested | 0 call sites of `requestAuthorization` | No |
| BUG-11 | Medium | High | Driver location permission never requested; `startLocationTracking` never called | `MapViewModel` | No |
| BUG-12 | Medium | High | Success UI regardless of backend result (commercial/private booking, listing create) | `CommercialBookingSheet.bookSlot`, `PrivateListingDetailView.requestBooking`, `createListingLocally` | Yes |
| BUG-13 | High | High (historical DDL) | Legacy `bookings.type` is `NOT NULL` but the `BookingSession` DTO never sends it → every `createBookingSession` insert violates the constraint (if live DDL unchanged); `getPrivateBookings` filters on `type`. Combined with RLS (hosts cannot read bookings) the host bookings list is unfixable without schema change | `e72c855:supabase_schema.sql`, `BookingSession.CodingKeys`, `SupabaseService.getPrivateBookings` | No |
| BUG-14 | Medium | High | Session-expiry detection via substring matching of error text; false positives/negatives | `handleSupabaseError` | No |
| BUG-15 | Medium | High | View models fetch in `init()` before auth; `HostViewModel` loads once and never after login | `ParkezyApp`, `HostViewModel.init` | No |
| BUG-16 | Medium | High | QR prefixes `PARKEZY-PVT`/`PARKEZY-COM` generated by models but `parseQRCode` only accepts `PARKEZY` | `PrivateParking.swift`, `CommercialParking.swift`, `QRCodeService` | No |
| BUG-17 | Low | High | Inconsistent GST handling (private booking cost excludes the 18% shown elsewhere); `priceMultiplier`/`flatDayRate` ignored | BR-01, BR-02 | No |
| BUG-18 | Low | High | Fake latency (3 s skeleton, 1–2 s "processing") | `EnhancedPrivateListingDetailView`, booking sheets | No |
| BUG-19 | Low | High | `HostViewModel.updateRevenueData` fabricates random chart data | `HostViewModel.swift` | No |
| BUG-20 | Low | High | `AppDelegate` comment says Firebase; `UserRepository.swift` tombstone; commented-out code blocks | misc | No |
| BUG-21 | Medium | High (historical DDL) | `disputes` has no `photo_urls` column in the committed DDL but `DisputeReport` encodes it → inserts fail (PostgREST unknown-column error) unless altered later; status default `'pending'` vs app `"Pending"` | DDL, `DisputeReport.swift` | No |
| BUG-22 | High | Medium | `parking_spots`, `private_bookings`, `commercial_bookings` are used by the app but have no DDL in git; if they do not exist live, F-24 (commercial booking), F-26/F-44 and the legacy map data are Broken | `SupabaseService.swift`, DDL absence | Yes (resolve in M-00) |

## Product gaps (not bugs)
GAP-01 driver private booking is a stub (F-26) · GAP-02 no host approval UI (F-44) · GAP-03 no payments · GAP-04 no driver "My bookings"/cancel · GAP-05 no commercial facility onboarding (F-49) · GAP-06 no reviews/ratings submission (ratings are static columns) · GAP-07 no push/SMS · GAP-08 no admin/dispute handling.

## Technical debt
DEBT-01 dead/duplicate code (39%) · DEBT-02 two parallel booking models · DEBT-03 **zero tests** (no test target) · DEBT-04 no CI · DEBT-05 `print` logging with emoji · DEBT-06 stale docs (see [current-state](../state/current-state.md)) · DEBT-07 likely deprecated `client.database` alias (verify against supabase-swift 2.46 docs) · DEBT-08 embedded `slots` JSON · DEBT-09 enums persisted as display strings · DEBT-10 no accessibility modifiers (0 occurrences) and fixed-size fonts · DEBT-11 Swift 5 mode, no strict concurrency · DEBT-12 deployment target iOS 26.5 excludes older devices.

## Quality: test coverage
No test target, fixtures, mocks or CI exist. Safe verification for the items above is listed in [testing-strategy](testing-strategy.md).
