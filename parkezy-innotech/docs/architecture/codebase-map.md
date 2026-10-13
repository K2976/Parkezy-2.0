# Codebase Map

All Swift sources live under `parkezy/parkezy/` (50 files, 15,851 lines at commit `64c4240`). The Xcode project (`parkezy/parkezy.xcodeproj`) uses a file-system-synchronized group, so new files are compiled automatically. Non-source: `Assets.xcassets` (AccentColor, AppIcon **with no image files**, `parking_city_bg`).

Reachability was computed by grepping for references to each type; see [state/current-state](../state/current-state.md).

| File | Lines | Purpose | Reachability | Component | Rebuild |
|---|---:|---|---|---|---|
| `ActiveSessionView.swift` | 603 | S-24/S-25 | Unreachable | — | Redo |
| `AddParkingFlowView.swift` | 1007 | S-10 wizard (1007 lines, 4 steps) | Reachable (simulator) | C-07 | Redesign |
| `AuthenticationView.swift` | 378 | S-01/S-02 | Reachable | C-02 | Redesign |
| `Backend/AppConfig.swift` | 37 | `useSupabase` flag (0 callers) + privacy URL placeholder | Dead (partly) | C-03 | Replace with xcconfig |
| `Backend/AppDelegate.swift` | 23 | Fires a pointless session fetch at launch; header comment still says Firebase | Reachable | C-01 | Remove |
| `Backend/AppUser.swift` | 63 | Profile DTO, capabilities, stats | Reachable | C-15 | Preserve shape, server-owned |
| `Backend/AuthViewModel.swift` | 303 | Auth state & account ops | Reachable | C-02 | Redesign |
| `Backend/NetworkMonitor.swift` | 73 | NWPathMonitor | Reachable | C-13 | Preserve |
| `Backend/SupabaseConfig.swift` | 29 | Hard-coded URL + anon key; shared client | Reachable | C-03 | Replace |
| `Backend/SupabaseService.swift` | 273 | 22 PostgREST wrappers | Reachable | C-04 | Redesign (typed repositories + RPC) |
| `Backend/UserRepository.swift` | 1 | 1-line tombstone "Deleted per Phase 2" | Dead | — | Remove |
| `BookingConfirmationView.swift` | 477 | S-21 | Unreachable | — | Redo with real payments |
| `BookingSession.swift` | 115 | Legacy `bookings` DTO | Unreachable use | C-15 | Decide (Q-02) |
| `BookingViewModel.swift` | 282 | Legacy session lifecycle | Unreachable features | C-08 | Rebuild as server-driven sessions |
| `CommercialFacilityDetailView.swift` | 650 | S-05/S-06 | Reachable | C-06 | Improve |
| `CommercialParking.swift` | 340 | Commercial facility/slot/booking DTOs | Reachable | C-15 | Redesign schema |
| `CommercialParkingViewModel.swift` | 181 | Commercial data/booking | Reachable | C-06 | Redesign |
| `Components/StandardStateViews.swift` | 177 | Loading/Empty/Error/Offline views | Reachable (banner only) | C-13 | Preserve, use widely |
| `DesignSystem.swift` | 228 | Colors, spacing, typography, Color(hex:) | Reachable | C-14 | Preserve/extend |
| `DisputeReport.swift` | 44 | Dispute DTO | Unreachable use | C-15 | Preserve concept |
| `DisputeView.swift` | 439 | S-27 + mock camera | Unreachable | — | Redo |
| `EditPrivateListingView.swift` | 302 | S-13 | Reachable | C-07 | Preserve |
| `EmulatorDetector.swift` | 24 | `isSimulator` flag used to fake media/location | Reachable | — | Remove from prod paths |
| `EnhancedPrivateListingDetailView.swift` | 819 | S-07/S-08 stub | Reachable | C-07 | Redesign |
| `FindParkingIntent.swift` | 164 | App Intents + DeepLink (provider commented out) | Inert | C-16 | Redo |
| `HostBookingsView.swift` | 160 | S-14 | Reachable (wrong data) | C-11 | Redesign |
| `HostViewModel.swift` | 374 | Host metrics + QR | Reachable (broken data) | C-11 | Redesign |
| `LocationManager.swift` | 232 | CLLocation + geofence | Reachable | C-09 | Preserve |
| `LocationPickerView.swift` | 207 | S-30 duplicate picker | Unreachable | — | Remove |
| `MapViewModel.swift` | 212 | Geocode + location; most filters dead | Reachable (partial) | C-05 | Slim down |
| `MockDataService.swift` | 458 | Delhi sample data | Dead | C-17 | Remove |
| `NotificationManager.swift` | 131 | Local notifications | Reachable (never authorized) | C-10 | Improve |
| `PINEntryView.swift` | 364 | S-22 | Unreachable | — | Redo (server-verified) |
| `ParkingLiveActivity.swift` | 376 | ActivityKit attributes, manager, views | Inert | C-16 | Redo in extension target |
| `ParkingSpot.swift` | 167 | Legacy `parking_spots` DTO | Unreachable use | C-15 | Decide (Q-02) |
| `ParkingWidget.swift` | 326 | WidgetKit provider/views | Inert | C-16 | Redo in extension target |
| `PrivateListingDetailView.swift` | 800 | S-11/S-12 | Reachable (host only) | C-07 | Merge with S-07 |
| `PrivateParking.swift` | 490 | Private listing/slot/booking DTOs | Reachable | C-15 | Redesign schema |
| `PrivateParkingViewModel.swift` | 548 | Private data/booking + demo generators | Reachable | C-07 | Redesign |
| `QRCodeService.swift` | 75 | QR generate/parse | Unreachable | C-12 | Replace with signed tokens |
| `QRDisplayView.swift` | 414 | S-23 (+ wallet mock) | Unreachable | — | Redo |
| `QRScannerView.swift` | 594 | S-28 | Unreachable | — | Redo |
| `ReceiptView.swift` | 495 | S-26 | Unreachable | — | Redo |
| `RoleSelectionView.swift` | 367 | S-03; orphan `HostTypeSelectionView` | Reachable | C-01 | Redesign |
| `SettingsView.swift` | 610 | S-29 + 8 sub-screens | Unreachable | — | Redo (needs delete account) |
| `SkeletonView.swift` | 97 | Shimmer | Reachable | C-14 | Preserve |
| `SpotDetailSheet.swift` | 372 | S-20 | Unreachable | — | Remove/redo |
| `UnifiedHostDashboardView.swift` | 442 | S-09 | Reachable | C-07/C-11 | Redesign |
| `UnifiedMapView.swift` | 454 | S-04 | Reachable | C-06/C-07 | Improve |
| `parkezyApp.swift` | 54 | App entry; VM construction; auth gate | Reachable | C-01 | Redesign |

## Non-source files
| Path | Notes |
|---|---|
| `parkezy/parkezy.xcodeproj/project.pbxproj` | Single app target, generated Info.plist, no entitlements, no test/extension targets |
| `.claude/settings.local.json` | Tracked despite `.gitignore` (SEC-06) |
| `README.md`, `parkezy_audit_report.md`, `PARKEZY_CHANGELOG.md`, `SUBMISSION_CHECKLIST.md` | Legacy docs, partly stale |
| `.gitignore` | Xcode/SPM/macOS ignores |
