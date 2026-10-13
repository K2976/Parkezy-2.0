# Parkezy - App Audit & Architecture Overview

**Parkezy** is a comprehensive smart parking solution built for iOS using **Swift** and **SwiftUI**. The application offers a dual-role architecture, allowing users to seamlessly switch between **Driver Mode** (to find and book parking spots) and **Host Mode** (to list and manage personal or commercial parking spaces).

This document serves as a detailed audit and technical overview of the Parkezy application.

---

## 🏗 System Architecture & Technology Stack

- **Platform:** iOS (Swift, SwiftUI)
- **Architecture Pattern:** MVVM (Model-View-ViewModel) paired with centralized Services.
- **Backend Infrastructure:** Supabase (Authentication, PostgreSQL Database, Row Level Security)
- **Key Frameworks:** 
  - `SwiftUI` for responsive and declarative UI design.
  - `MapKit` & `CoreLocation` for maps, routing, and location services.
  - `ActivityKit` & `WidgetKit` for Live Activities (Dynamic Island / Lock Screen).
  - `VisionKit` for QR Code scanning capabilities.
  - `AuthenticationServices` & `CryptoKit` for secure Apple Sign-In.

---

## 🚗 User Roles & Core Flows

The app implements a scalable **Role Selection** concept (`RoleSelectionView.swift`), separating concerns based on the user's intent:

### 1. Driver Mode
Allows users to browse, locate, and book available parking spots.
- **Unified Map View:** A centralized `UnifiedMapView.swift` that uses `MapViewModel` & `LocationManager` to show real-time spot availability.
- **Booking Flow:** Drivers can select a spot, choose the duration, and initialize a `BookingSession`.
- **Active Session Tracking:** 
  - Drivers can view their active sessions through `ActiveSessionView`.
  - The app integrates heavily with **Live Activities** (`ParkingLiveActivity.swift`), providing real-time timer updates, overstay warnings, and current cost on the Lock Screen and Dynamic Island.
- **Payments & Receipts:** Completed bookings generate receipts (`ReceiptView.swift`) displaying total costs and overstay fees if applicable.
- **QR Code Check-In/Out:** Generates and displays QR codes (`QRDisplayView.swift`) for access control when entering/exiting closed parking spaces.

### 2. Host Mode
Allows users to monetize their empty parking spaces or manage commercial lots.
- **Unified Dashboard:** `UnifiedHostDashboardView.swift` provides a high-level overview of bookings, income, and active sessions.
- **Listing Types:**
  - **Private Listings:** For home driveways or personal garages (`PrivateParking.swift`, `PrivateListingDetailView.swift`).
  - **Commercial Facilities:** For malls, hospitals, office spaces (`CommercialParking.swift`, `CommercialFacilityDetailView.swift`).
- **QR Code Scanning:** The host can use the camera to scan a driver's QR code (`QRScannerView.swift`) to validate entries and exits securely.

---

## 🗄 Backend Data Layer (Supabase)

The backend has been migrated from Firebase/Django to **Supabase**, leveraging PostgreSQL for robust relational data and Row Level Security (RLS).

### Services (Stored in `/Backend/`)
- **`SupabaseConfig.swift`**: Global configuration singleton providing the `SupabaseClient` securely.
- **`SupabaseService.swift`**: Centralized service handling all database operations, including fetching user profiles, managing private/commercial listings, and tracking bookings. It uses modern Swift concurrency (`async/await`).
- **`AuthViewModel.swift`**: Handles user registration, sign-in, Apple Sign-In integration, session restoration, and Account Deletion logic.

### Database Schema
The database uses a structured SQL schema (`supabase_schema.sql`):
- `profiles` (Auto-created via Postgres triggers on auth signup)
- `private_listings`
- `commercial_facilities`
- `bookings`
- `disputes`

### Mock Data & Offline State
- **`MockDataService.swift`**: Contains detailed mock data (Delhi NCR locations) isolated purely for testing/prototyping. It is strictly disabled for production paths.
- **`NetworkMonitor.swift`**: A global `NWPathMonitor` service that displays a system-wide `OfflineBannerView` to warn users when connectivity drops.

---

## 🎨 UI/UX Design System

The app utilizes a centralized `DesignSystem.swift` to keep visual consistency across typography, spacing, and colors.

- **Vibrant & Modern UI:** Uses transparency effects (`.ultraThinMaterial`), drop shadows, and linear gradients to convey a premium feel.
- **Animations:** View transitions, popup sheets (`SpotDetailSheet.swift`), and interactive sliders are animated smoothly.
- **Standardized States:** Incorporates reusable `LoadingStateView`, `EmptyStateView`, and `ErrorStateView` components to ensure a consistent experience across all lists and fetching processes.
- **Dark/Light Mode Ready:** Native SwiftUI colors and custom palettes from `Assets.xcassets` guarantee visual harmony across system appearances.
- **Monospaced Fonts:** heavily used in `QRScannerView` and receipt details for clarity on numbers and codes.

---

## 📱 Standout Engineering Features

1. **Live Activities Integration (`ParkingLiveActivity.swift`)**
   - Implements both widget configurations and lock screen views.
   - Calculates time variations, flags overstays with UI warnings, and dynamically updates calculated costs.

2. **Scanner & Camera Integration (`QRScannerView.swift`)**
   - Safe Fallbacks: Detects Simulator environments and falls back to a "Mock Scanner View" providing buttons to simulate entries and exits for testing purposes.
   - VisionKit integration correctly restricts payload handling to `Set([.barcode()])`.

3. **App Store Compliance Ready**
   - Implemented standard Account Deletion and Apple Sign-In features.
   - App Transport Security (ATS) strictly enforced via HTTPS.
   - Detailed privacy and info permissions isolated for review.

---

## 🛠 Future Improvements / Recommendations

If the application is scaled up towards production, consider the following technical roadmap:

1. **Environment Separation:** Enhance `AppConfig.swift` to gracefully handle `Dev`, `Staging`, and `Prod` Supabase URLs instead of a hardcoded monolithic project.
2. **Offline Resilience:** Implement `SwiftData` or `CoreData` caching layers for offline resilience, backed by Supabase Edge Functions for handling concurrent booking transaction conflicts safely.
3. **Payment Gateway Integration:** The current system acts as a ledger (`currentCost`, `totalCost`), but real fiat movement would require Stripe or Razorpay backend logic integrations. 

---

### Conclusion
Parkezy's architecture is robust, strictly following modular principles by separating the ViewModels from the Supabase backend. It extensively leverages standard Apple APIs (MapKit, ActivityKit, CoreLocation, Vision) ensuring a deeply native OS experience.
