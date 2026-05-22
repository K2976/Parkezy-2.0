# Parkezy Changelog

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
