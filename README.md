# Parkezy - App Audit & Architecture Overview

**Parkezy** is a comprehensive smart parking solution built for iOS using **Swift** and **SwiftUI**. The application offers a dual-role architecture, allowing users to seamlessly switch between **Driver Mode** (to find and book parking spots) and **Host Mode** (to list and manage personal or commercial parking spaces).

This document serves as a detailed audit and technical overview of the Parkezy application.

---

## 🏗 System Architecture & Technology Stack

- **Platform:** iOS (Swift, SwiftUI)
- **Architecture Pattern:** MVVM (Model-View-ViewModel) paired with Repository patterns.
- **Backend Infrastructure:** Firebase (Authentication, Firestore Database)
- **Key Frameworks:** 
  - `SwiftUI` for responsive and declarative UI design.
  - `MapKit` & `CoreLocation` for maps, routing, and location services.
  - `ActivityKit` & `WidgetKit` for Live Activities (Dynamic Island / Lock Screen).
  - `VisionKit` for QR Code scanning capabilities.

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
- **Pricing Intelligence:** An AI-inspired recommendation view (`PricingIntelligenceView.swift`) that compares the host's hourly rates against regional averages and projects weekly/monthly earnings.
- **QR Code Scanning:** The host can use the camera to scan a driver's QR code (`QRScannerView.swift`) to validate entries and exits securely.

---

## 🗄 Backend Data Layer

The backend uses **Firebase** for cloud data syncing, coupled with a solid Repository pattern to abstract Firebase logic from the presentation layer (ViewModels).

### Repositories (Stored in `/Backend/`)
- **`AuthRepository.swift`**: Handles user registration, sign-in, and auth-state persistence.
- **`UserRepository.swift`**: Manages the user profile model (`AppUser.swift`).
- **`BookingRepository.swift`**: Creates, updates, and completes booking requests and sessions.
- **`PrivateListingRepository.swift` & `CommercialFacilityRepository.swift`**: Manage CRUD operations for different parking assets.

### Firebase Integration
- **`FirebaseManager.swift`**: A singleton that acts as the core interface to Firestore, defining root collections:
  - `users`
  - `privateListings`
  - `commercialFacilities`
  - `bookings`
- It is instantiated on startup within the `ParkezyApp.swift` (`AppConfig`). offline persistence is strategically enabled via `FirestoreSettings().cacheSettings`.

### Mock Data & Prototyping
The application is equipped with a highly detailed `MockDataService.swift` containing pre-populated entries for various locations in Delhi NCR (e.g., Select Citywalk, DLF Promenade, Private Driveways in Greater Kailash, Cyber Hub). This allows fast UI prototyping and simulator debugging without live Firebase connections.

---

## 🎨 UI/UX Design System

The app utilizes a centralized `DesignSystem.swift` to keep visual consistency across typography, spacing, and colors.

- **Vibrant & Modern UI:** Uses transparency effects (`.ultraThinMaterial`), drop shadows, and linear gradients to convey a premium feel.
- **Animations:** View transitions, popup sheets (`SpotDetailSheet.swift`), and interactive sliders are animated smoothly.
- **Dark/Light Mode Ready:** Native SwiftUI colors and custom palettes from `Assets.xcassets` guarantee visual harmony across system appearances.
- **Monospaced Fonts:** heavily used in `QRScannerView` and receipt details for clarity on numbers and codes.

---

## 📱 Standout Engineering Features

1. **Live Activities Integration (`ParkingLiveActivity.swift`)**
   - Implements both widget configurations and lock screen views.
   - Calculates time variations, flags overstays with UI warnings (red text, alert icons), and dynamically bumps up calculated costs if the driver exceeds their booked duration.

2. **Scanner & Camera Integration (`QRScannerView.swift`)**
   - Safe Fallbacks: Detects Simulator environments and falls back to a "Mock Scanner View" providing buttons to simulate entries and exits for testing purposes.
   - VisionKit integration correctly restricts payload handling to `Set([.barcode()])`.

3. **Smart Pricing Algorithm Interface**
   - Provides visual indicators regarding a Host's competitiveness (e.g., `tooExpensive`, `competitive`, `fair`) based on neighborhood average data logic within `PricingIntelligenceView.swift`.

---

## 🛠 Future Improvements / Recommendations

If the application is scaled up towards production, consider the following technical roadmap:

1. **Environment Separation:** Enhance `AppConfig.swift` to gracefully handle `Dev`, `Staging`, and `Prod` Firebase Plists instead of a hardcoded monolithic project.
2. **Offline Resilience:** While Firestore handles offline cache natively, edge-case sync conflicts for simultaneous bookings on the same parking spot would require optimistic locking or Cloud Functions (transactional commits) to prevent double-booking.
3. **Payment Gateway Integration:** The current system acts as a ledger (`currentCost`, `totalCost`), but real fiat movement would require Stripe or Razorpay backend logic integrations. 

---

### Conclusion
Parkezy's architecture is robust, strictly following modular principles by separating the ViewModels from the Firebase logic. It extensively leverages standard Apple APIs (MapKit, ActivityKit, CoreLocation, Vision) ensuring a deeply native OS experience.
