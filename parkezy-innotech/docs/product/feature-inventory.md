# Feature Inventory

Status values: see [legend](../README.md#status-legend). "Reach" = reachable from `parkezyApp` → `RoleSelectionView`. Evidence paths are relative to `parkezy/parkezy/`. **No feature has been runtime-verified**; there are no automated tests (proposed tests: [testing-strategy](../quality/testing-strategy.md)).

**Permissions:** every feature is open to any signed-in user; no capability gating exists in the client, and server enforcement is only partly known ([roles doc](user-roles-and-permissions.md), [SEC-02](../quality/audit-findings.md)). **Existing tests:** none for any feature.

Rebuild action: **P**reserve · **I**mprove · **R**edesign · **X** remove · **?** investigate.

## Authentication & account
| ID | Feature | Status | Evidence | Notes / limitations | Rebuild |
|---|---|---|---|---|---|
| F-01 | Email sign-up / sign-in | Implemented | `Backend/AuthViewModel.swift` `signUp`/`signIn`; `AuthenticationView.swift` | Validation: email contains `@` and `.`, password ≥ 8, name ≥ 2 (`isFormValid`). Sign-up sets `isAuthenticated = true` even if Supabase requires email confirmation (no session) | I |
| F-02 | Sign in with Apple | Broken | `AuthViewModel.handleAppleSignIn`, `AuthenticationView.swift:208` | Nonce+SHA256 logic is correct. **No entitlements file / `CODE_SIGN_ENTITLEMENTS`** in `project.pbxproj`, so the capability is likely not enabled; Apple's name is not captured | I |
| F-03 | Session restore on launch | Implemented | `parkezyApp.swift` `.task`, `AuthViewModel.restoreSession` | Profile fetch failure leaves `currentUser = nil` while `isAuthenticated = true` | I |
| F-04 | Forgot password (send email) | Partial | `AuthenticationView.swift` `ForgotPasswordSheet`, `sendPasswordReset` | Sends reset email only; no recovery deep-link handling in app | I |
| F-05 | Sign out | Implemented | `RoleSelectionView.swift` toolbar → `signOut()` | View models are **not** reset (stale data leaks across accounts, BUG-07) | I |
| F-06 | Delete account | Broken | `AuthViewModel.deleteAccount` (line 154), `SettingsView.swift` | `user.id` is `String`; `.uuidString` does not exist → likely compile error. Only deletes the `profiles` row, which historical RLS (no DELETE policy) silently blocks; Auth user remains. UI (Settings) unreachable | R |
| F-07 | Session-expiry handling | Partial | `SupabaseService.handleSupabaseError`, `AuthViewModel.handleSessionExpired` | Detects expiry by substring match on `String(describing: error)` | R |
| F-08 | Edit profile (name/phone) | Unreachable | `AuthViewModel.updateProfile` (0 callers) | Settings UI unreachable | I |
| F-09 | Enable host capabilities | Unreachable | `enablePrivateHosting`/`enableCommercialHosting` (0 callers) | Client writes `capabilities`; nothing gates on capabilities | R |
| F-10 | Role selection (Driver / Host mode) | Implemented | `RoleSelectionView.swift` | Pure navigation switch, not tied to capabilities. `HostTypeSelectionView` is an orphan | I |

## Driver discovery & booking
| ID | Feature | Status | Evidence | Notes | Rebuild |
|---|---|---|---|---|---|
| F-20 | Map of commercial + private supply | Implemented | `UnifiedMapView.swift`, `CommercialParkingViewModel.refreshFacilitiesFromBackend`, `PrivateParkingViewModel.refreshListingsFromBackend` | Fetches **all** rows (no viewport/radius filter). Pull-to-refresh. Default camera Delhi | I |
| F-21 | Address search / geocode | Implemented | `UnifiedMapView.performSearch`, `MapViewModel.searchLocation` (CLGeocoder) | Re-centers map; no distance filtering | I |
| F-22 | Filters (Commercial/Private toggle, EV) | Implemented | `UnifiedMapView.filterSection` | `MapViewModel` filters (CCTV, covered, max price, available only) are unused by this view | I |
| F-23 | Commercial facility detail + slot grid | Implemented | `CommercialFacilityDetailView.swift` | Floor picker, slot cards, legend, countdown badges. `CommercialSlotType.priceMultiplier` exists but is **not** applied to booking cost | I |
| F-24 | Commercial slot booking | Partial | `CommercialBookingSheet.bookSlot` → `CommercialParkingViewModel.bookSlot` → `SupabaseService.createCommercialBooking` | Depends on `commercial_bookings`, which has no DDL in git (BUG-22); fake 1 s delay; fire-and-forget insert (success UI even if insert fails); price and access code client-made; QR is a placeholder icon; "Amount Paid" with no payment; status stays `.pending` | R |
| F-25 | Private listing detail (driver) | Partial | `EnhancedPrivateListingDetailView.swift` | Forced 3 s fake skeleton (`asyncAfter 3.0`); image area is placeholder | I |
| F-26 | Private booking request (driver) | Stub | `BookingSheetView` "Full booking flow coming soon!" | The real request form (`PrivateBookingSheet`, `PrivateListingDetailView`) is reachable only from the host dashboard (own listing) | R |
| F-27 | Legacy single-spot session flow: spot sheet → pay → PIN/QR → live timer → extend → end → receipt | Unreachable | `SpotDetailSheet`, `BookingConfirmationView`, `PINEntryView`, `QRDisplayView`, `ActiveSessionView`, `ReceiptView`, `BookingViewModel` | Complete UI; payment simulated (2 s); hard-coded fallback PIN "428915"; "Demo PIN" shown on screen | R |
| F-28 | Overstay fee (₹20 per started 15 min) and running cost with 18% GST | Unreachable | `BookingViewModel.endSession`, `updateSessionMetrics` | Client-computed. See BR-05 | R |
| F-29 | Geofence arrival/exit events | Unreachable | `LocationManager.monitorGeofence`, `BookingViewModel.handleGeofenceEntry/Exit` | Only logs | ? |
| F-30 | Session-warning local notifications (15 min, 5 min, end) | Broken | `NotificationManager.scheduleSessionWarnings` | `requestAuthorization` has **0 call sites**, so permission is never requested | I |
| F-31 | User location on map | Broken | `MapViewModel.startLocationTracking` (0 callers); `requestLocationPermission` only in host `LocationStepView` | Driver map never asks for permission; no usage-description key set | I |
| F-32 | Dispute / report issue | Unreachable | `DisputeView.swift`, `SupabaseService.createDispute` | Photos never uploaded (`photoURLs: []`); uses a mock camera; `disputes` DDL has no `photo_urls` column (BUG-21) | I |
| F-33 | Receipt | Unreachable | `ReceiptView.swift` | Hard-coded "Apple Pay •••• 4242" | R |
| F-34 | Live Activity / widget / Siri App Intents | Unreachable | `ParkingLiveActivity.swift`, `ParkingWidget.swift`, `FindParkingIntent.swift` | Compiled into the app target; no extension target, no `NSSupportsLiveActivities`; `BookingViewModel` live-activity methods are stubs; `AppShortcutsProvider` commented out | R |

## Host
| ID | Feature | Status | Evidence | Notes | Rebuild |
|---|---|---|---|---|---|
| F-40 | Host dashboard (welcome, earnings tiles, active parking, my listings) | Partial | `UnifiedHostDashboardView.swift`, `HostViewModel.swift` | Earnings read from the wrong source (BUG-05); `HostViewModel` loads once at app start, never after login | R |
| F-41 | Add listing wizard (Location → Media → Details → Review) | Partial | `AddParkingFlowView.swift` | Requires ≥1 photo **and** a "recorded video", but capture is **simulated** (`MediaStepView.capturePhoto` appends a placeholder image, `recordVideo` just sets a flag); on a real device `capturePhoto` only sets `showingPhotoCapture`, which nothing reads, so **the wizard cannot pass the Media step on hardware** (BUG-04); nothing is uploaded (`imageURLs` stays `[]`); "Commercial" mode creates a *private* listing; Private mode saves `hourlyRate = 0`; random slot occupancy (BUG-08) | R |
| F-42 | Edit listing | Implemented | `EditPrivateListingView.swift` → `updatePrivateListing` | Amenities, auto-accept, 24 h, etc. | I |
| F-43 | Delete listing | Unreachable | `PrivateParkingViewModel.deleteListing` (0 UI callers) | | I |
| F-44 | Approve / reject private booking request | Absent | `approveBooking`/`rejectBooking` have 0 callers | Pending requests can never be resolved in-app | R |
| F-45 | Host bookings list (Active / History, search) | Broken | `HostBookingsView.swift`, `HostViewModel.loadHostData` | Queries `bookings` where `user_id = host` and `type = 'private'`; historical RLS lets only the booking's own user read it, and `type` is NOT NULL but never sent by the DTO (BUG-13) | R |
| F-46 | QR scan for entry/exit (host) | Unreachable | `QRScannerView.swift`, `HostViewModel.validateQRCode`, `QRCodeService` | `ownedSpots` is never populated so a real scan returns `.wrongHost`; QR unsigned; confirm entry/exit not persisted; private/commercial QR prefixes are not parsed by `parseQRCode` | R |
| F-47 | Suggested price (average of listings within 2 km) | Implemented | `PrivateParkingViewModel.calculateSuggestedPrices` | Client-side O(n²); default ₹40 | I |
| F-48 | Revenue / peak-hour / mix charts data | Partial | `HostViewModel.generate*` | `updateRevenueData(for:)` uses `Double.random` (0 callers); commission math reports the platform cut (12%/15%) as host earnings | R |
| F-49 | Commercial facility onboarding/management | Absent | — | No UI/API creates or edits `commercial_facilities`; rows must be seeded externally | R |
| F-50 | Pricing/availability/payout/support settings | Stub | `SettingsView.swift` sub-screens (unreachable) | Local `@State` only; "Help article here..." placeholders | X |

## Platform / cross-cutting
| ID | Feature | Status | Evidence | Rebuild |
|---|---|---|---|---|
| F-60 | Global offline banner | Implemented | `Backend/NetworkMonitor.swift`, `Components/StandardStateViews.swift`, `parkezyApp.swift` | P |
| F-61 | Loading/empty/error state components, skeletons | Partial | `Components/StandardStateViews.swift`, `SkeletonView.swift` (barely used) | I |
| F-62 | Design system (colors, spacing, typography) | Implemented | `DesignSystem.swift` | I |
| F-63 | Mock data service | Dead | `MockDataService.swift` (0 callers) | X |
| F-64 | Environment switch `AppConfig.useSupabase` | Dead | `Backend/AppConfig.swift` (0 callers) | X |

## Status totals
41 features. Implemented: 12 · Unreachable: 10 · Partial: 8 · Broken: 5 · Stub: 2 · Absent: 2 · Dead: 2

(Counted by script from the tables above.)
