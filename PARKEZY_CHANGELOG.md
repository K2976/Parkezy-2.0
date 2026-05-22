# Parkezy Changelog

## Phase 4: UI Stability & Crash Prevention
**Date**: May 2026

### 🐛 Force-Unwrap Elimination (0 remaining)
- **BookingConfirmationView.swift**: Wrapped `bookingViewModel.activeSession!` in `if let` (2 sites).
- **BookingViewModel.swift**: Replaced `Calendar.date(byAdding:)!` with `?? now` fallback (2 sites).
- **BookingSession.swift**: Fixed `mockSession` static property `Calendar.date!` (2 sites).
- **CommercialParkingViewModel.swift**: Fixed `Calendar.date!` (2 sites) and `randomElement()!` (1 site — already done in prior pass).
- **PrivateParkingViewModel.swift**: Fixed `Calendar.date!` (3 sites), `randomElement()!` (4 sites), and array literal subscript `[i]` → `[i % 3]` (2 sites).
- **HostViewModel.swift**: Fixed `Calendar.date!` in `generateRevenueData` and `updateRevenueData` (4 sites).
- **SettingsView.swift**: Wrapped `URL(string:)!` for Terms, Privacy, and shareApp (3 sites).
- **FindParkingIntent.swift**: Replaced `URL(string:)!` with `guard let … throw` (2 sites).
- **ParkingLiveActivity.swift**: Wrapped `URL(string:)!` deep-link in `if let` (1 site).
- **ParkingWidget.swift**: Fixed `Calendar.date!` (1 site) and `URL(string:)!` deep-links (2 sites).
- **SupabaseConfig.swift**: Replaced `URL(string:)!` with `guard let … preconditionFailure` with clear diagnostic message.

### 🔧 Mock Data Cleanup
- **HostViewModel.swift**: Removed 100% mock-data `loadMockHostData()` and `generateMockBookings()` methods. Replaced with `loadHostData()` async method that loads user profile and bookings from `SupabaseService`.
- **PrivateParkingViewModel.swift**: Replaced `deleteListing` local-only logic with `SupabaseService.shared.deletePrivateListing()` async call.
- **PrivateParkingViewModel.swift**: Scrubbed all hardcoded fake phone numbers (`+91 98765 xxxxx`).
- **MockDataService.swift**: Added `TESTING ONLY — NOT USED IN PRODUCTION` markers to all public methods.
- **AuthenticationView.swift**: Commented out the `testLoginButton` and its `test@parkezy.com` credential.
- **SettingsView.swift**: Commented out unimplemented Call/Email support links with hardcoded phone/email.

### 🚫 Dead Code Disabled
- **BookingViewModel.swift**: Wrapped `startLiveActivity()`, `updateLiveActivity()`, `endLiveActivity()` in `if #available(iOS 16.2, *)` stubs.
- **ParkingLiveActivity.swift**: Already had Widget code commented out — no changes needed.
- **FindParkingIntent.swift**: `ParkEzyShortcuts` AppShortcutsProvider already commented out — confirmed.
- **ParkingAPIService.swift**: Confirmed deleted (Phase 2).
- **AuthRepository.swift**: Confirmed deleted (Phase 2).

### ✨ New Files
- **`Backend/NetworkMonitor.swift`**: `NWPathMonitor`-based singleton that publishes `isConnected` and `connectionType` on `@MainActor`. Used by `OfflineBannerView`.
- **`Components/StandardStateViews.swift`**: Reusable UI components:
  - `LoadingStateView` — spinner + message.
  - `EmptyStateView` — icon + title + message + optional action button.
  - `ErrorStateView` — warning icon + message + optional retry button.
  - `OfflineBannerView` — red banner auto-shown when `NetworkMonitor.isConnected == false`.

### 🏗️ App Entry Point
- **ParkezyApp.swift**: Added `ZStack` with `OfflineBannerView()` overlay so the offline banner appears globally above all screens.

## Phase 3: Authentication Rewrite
**Date**: May 2026

### 🗑️ Removed
- Removed all legacy `FirebaseAuth` and `FirebaseCore` imports.
- Removed dummy stub logic from `AuthViewModel.swift`.

### 🔧 Modified
- **AuthViewModel.swift**: Fully rewritten to use Supabase Auth.
  - Replaced email sign-up/in calls with `client.auth.signUp()` and `client.auth.signIn()`.
  - Added `restoreSession()` to check and restore existing session on app launch.
  - Rewrote Apple Sign-In flow to use `signInWithIdToken` and secure cryptographic nonce generation.
  - Added a session expiry handler that resets auth state.
- **ParkezyApp.swift**: Removed Firebase auth listener and added a `.task { await authViewModel.restoreSession() }` to properly manage session persistence automatically at app startup.
- **AuthenticationView.swift**:
  - Implemented inline error text beneath the form (removed error alerts).
  - Enforced 8-character password validation minimum for new sign-ups.
- **SettingsView.swift**: Integrated `authViewModel.signOut()` directly into the Log Out button logic and disabled the button while logout is processing.
- **SupabaseService.swift**: Added `sessionExpiredNotification` broadcaster. Captures authorization errors globally and notifies `AuthViewModel` to force the user back to the login screen gracefully.

### ✨ Added
- Real end-to-end user authentication flow bound to `supabase.auth` and the newly created `profiles` table.

## Phase 2: Supabase Migration
**Date**: May 2026

### 🗑️ Removed
- Deleted old Django API client (`ParkingAPIService.swift`)
- Removed `FirebaseManager.swift` and all `FirebaseApp.configure()` calls
- Emptied legacy Firebase repositories (`AuthRepository`, `UserRepository`, `BookingRepository`, `PrivateListingRepository`, `CommercialFacilityRepository`) to strip Firebase dependencies.
- Removed orphaned views: `AddPrivateListingView.swift`, `BookingDetailView.swift`, `PricingIntelligenceView.swift`, `MapView.swift`, `HomeMapView.swift`

### 🔧 Modified
- **View Models**: Cleaned `PrivateParkingViewModel` and `CommercialParkingViewModel` to rely purely on local mock data for UI state. Removed backend network call paths to prevent build errors.
- **AuthViewModel**: Stubbed out `FirebaseAuth` logic to allow safe deletion of legacy repos without breaking compilation.
- **User Models**: Replaced the duplicate mock `User` and Firebase `AppUser` with a single, unified `AppUser.swift` struct designed to match the Supabase `profiles` table. Added convenience properties (`canDrive`, `isHost`, etc.).
- **AppConfig**: Replaced `useFirebase` flag with `useSupabase` flag and added placeholder checks.
- **AppDelegate**: Removed Firebase configuration and added a Supabase connection test.

### ✨ Added
- **Supabase SDK**: Prepared for `supabase-swift` integration (to be added manually in Xcode by the developer).
- **SupabaseConfig.swift**: Created singleton config for Supabase URL and anon key (with placeholder values).
- **SupabaseService.swift**: Created a centralized service for all Supabase database queries matching the legacy repository signatures (using async/await).
- **supabase_schema.sql**: Created the complete SQL schema with tables (`profiles`, `private_listings`, `commercial_facilities`, `bookings`, `disputes`), foreign keys, RLS policies, and an auth trigger for user creation.
