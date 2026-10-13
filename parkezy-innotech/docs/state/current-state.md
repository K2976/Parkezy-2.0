# Current State (as of 2026-10-13, commit `64c4240`, branch `main`)

## Summary
Single-target SwiftUI iOS app on Supabase, 50 Swift files / 15,851 lines. Reachable functionality is a partial vertical slice (auth → role select → map → commercial booking write; host dashboard → add/edit private listing). ≈39% of the code is unreachable or dead. No tests, CI, server code, schema files or Info.plist usage strings. Last commit message: *"fixed the app and added the real data from the supabase backend manual testing left"* — the author notes manual testing is unfinished.

## Build and verification status
| Check | Result |
|---|---|
| Xcode build | **Not run** — `xcodebuild` unavailable (`xcode-select` → CommandLineTools). Probable compile error at `Backend/AuthViewModel.swift:154` (BUG-01); everything else unverified |
| `swiftc -parse` (syntax only, all 50 files) | **Passed** (exit 0, no diagnostics). Does not type-check, so BUG-01 remains *high confidence from static reading* |
| Tests | None exist; none run |
| Live Supabase inspection | **Failed**: project listed (`ACTIVE_HEALTHY`, then "hibernated"); `list_tables`, `list_migrations`, `execute_sql`, `get_advisors` all failed on database authentication (4 attempts across the session). Verified via API: Edge Functions list is empty. Schema/RLS knowledge comes from the historical `supabase_schema.sql` (5 of 8 tables) and Swift DTOs; live state is unverified |
| Anon key role | Decoded JWT payload fields only: `role = anon` (not service role) |
| Git-history secret sweep | Counts/paths only; see SEC-06 |
| Visual inspection | Not performed (no screenshots/running app) |

## Investigation checklist (all 50 Swift files were read or structurally scanned)
| Subsystem | Files | Depth |
|---|---|---|
| App entry, config, auth, service | `parkezyApp`, `Backend/*` | Read fully |
| Models | `ParkingSpot`, `BookingSession`, `PrivateParking`, `CommercialParking`, `DisputeReport`, `AppUser` | Read fully |
| View models | Map, Booking, Commercial, Private, Host | Read fully |
| Platform services | Location, Notification, QR, NetworkMonitor, EmulatorDetector | Read (Location: signatures + key lines) |
| Reachable views | RoleSelection, Authentication, UnifiedMap, CommercialFacilityDetail, EnhancedPrivateListingDetail, PrivateListingDetail, UnifiedHostDashboard, HostBookings, AddParkingFlow, EditPrivateListing | Read the logic parts (navigation, state, actions); layout/styling skimmed |
| Unreachable views | SpotDetailSheet, BookingConfirmation, PINEntry, QRDisplay, ActiveSession, Receipt, Dispute, QRScanner, Settings, LocationPicker | Structural scan + key logic grep (not line-by-line) |
| Inert platform code | ParkingLiveActivity, ParkingWidget, FindParkingIntent | Structural scan |
| UI kit / mock | DesignSystem, SkeletonView, StandardStateViews, MockDataService | Structural scan |
| Project config | `project.pbxproj`, `Package.resolved`, asset catalog | Read relevant settings |
| Git history | 61 commits | Log, deleted-backend models, secret sweep |

**Not inspected:** pixel-level UI, runtime behavior, the live database, Apple capabilities in the developer portal, TestFlight/App Store Connect state.

## Legacy documentation discrepancies
| Legacy claim (file) | Reality |
|---|---|
| README: Live Activities "integrated heavily"; `PARKEZY_CHANGELOG`: widget code commented out | Code is mostly *uncommented* but inert: no extension target, no plist key, `BookingViewModel` stubs |
| README/`SUBMISSION_CHECKLIST`: iOS 16.0 target | `IPHONEOS_DEPLOYMENT_TARGET = 26.5` |
| README: schema in `supabase_schema.sql` | File was deleted from HEAD (`02b8530`); recoverable from history (`e72c855`); covers only 5 of 8 tables and has drifted from the app |
| README: account deletion & Apple Sign-In "App Store ready"; checklist ticks them | Delete is broken/unreachable; no Apple entitlement |
| Checklist: "Info.plist permissions match actual code usage" | No usage strings exist |
| Checklist: "Empty/loading/error states on all list screens" | Map and host lists have no loading/error states; state components barely used |
| Checklist: "No mock data reachable" | True, but random/demo data **is** reachable (slot occupancy generators, random chart function) |
| Audit report: file list | Lists deleted files (HomeMapView, MapView, User, BookingDetailView, AddPrivateListingView, PricingIntelligenceView, ParkingAPIService); paths use old `Parkezy/` casing |
| README: Host "Unified dashboard provides income" | Wrong data source (BUG-05) |
| Changelog: force unwraps eliminated | Approximate grep found none — plausible, unverified |

## Known blockers for a release (unchanged from legacy checklist, plus new)
App icon images missing; usage strings; entitlements; privacy policy URL placeholder; account deletion; compile verification.

## Next step
[M-00 / M-01](../rebuild/implementation-roadmap.md). Handoff: [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md).
