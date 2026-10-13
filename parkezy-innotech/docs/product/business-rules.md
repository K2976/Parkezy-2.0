# Business Rules

Every rule below is enforced **only on the client** (no server logic exists). Rebuild requirement: move authoritative rules to the backend ([ADR-002](../decisions/README.md)).

| ID | Rule | Source | Notes |
|---|---|---|---|
| BR-01 | Currency ₹; GST 18% added to price shown/paid | `CommercialBookingSheet.totalCost`, `CommercialParkingViewModel.bookSlot` (×1.18), `BookingViewModel.extendSession`/`updateSessionMetrics`, `PrivateListingDetailView.totalCost` | **Inconsistent:** `PrivateParkingViewModel.requestBooking` stores `estimatedCost = rate × hours` **without** GST |
| BR-02 | Commercial booking cost = slot `hourlyRateOverride ?? facility.defaultHourlyRate` × hours × 1.18 | `CommercialParkingViewModel.bookSlot` | `CommercialSlotType.priceMultiplier` and `flatDayRate` are **not** applied |
| BR-03 | Commercial bookings are auto-approved; initial status `.pending` ("scheduled, not started") | `CommercialParking.swift` comments + `bookSlot` | Nothing ever moves the status to `.active`/`.completed` |
| BR-04 | Private booking: `autoAcceptBookings` → status `.approved` with PIN immediately; else `.pendingApproval` and host must approve (PIN generated on approval) | `PrivateParkingViewModel.requestBooking/approveBooking` | Approval UI absent |
| BR-05 | Overstay fee = ₹20 × ceil(overstay minutes / 15), added to total on end | `BookingViewModel.endSession`; live display in `updateSessionMetrics`; text in `NotificationManager` | Legacy flow only |
| BR-06 | Session warnings at T-15 min, T-5 min, and at end | `NotificationManager.scheduleSessionWarnings` | Permission never requested (F-30) |
| BR-07 | Extend session: adds hours, cost += `pricePerHour × hours × 1.18` | `BookingViewModel.extendSession` | Not persisted |
| BR-08 | Access PIN: 6 random digits (`Int.random(100000...999999)`); legacy spots reuse `spot.accessPIN` (stored in table readable by all) | `BookingViewModel.createBooking`, `PrivateParkingViewModel` | Not cryptographically random; PIN fallback "428915" hard-coded in `PINEntryView` |
| BR-09 | PIN entry: 6 digits, 3 attempts | `PINEntryView` | Local only |
| BR-10 | QR payload `PARKEZY:{bookingID}:{spotID}`; private `PARKEZY-PVT:{id}:{slot}`; commercial `PARKEZY-COM:{id}:{slot}` | `QRCodeService`, models | Unsigned; parser accepts only `PARKEZY` |
| BR-11 | Host commission: 12% mall, 15% private, used to compute "earnings" | `HostViewModel.calculateEarnings` | Semantically inverted/mislabeled (BUG-05); `PrivateBooking.hostEarnings` ("after platform fee") is never set |
| BR-12 | Suggested hourly price = mean hourly rate of other listings within 2 000 m; default ₹40 | `PrivateParkingViewModel.calculateSuggestedPrices` | Competitiveness bands: ≤0.9 competitive, ≤1.1 fair, ≤1.3 high, else too expensive (`PrivateParkingListing.priceCompetitiveness`) |
| BR-13 | Listing defaults: daily ₹300, monthly ₹3000, hourly ₹40 (comments) | `PrivateParking.swift`, `createListing` | Wizard overrides with 0 for private mode |
| BR-14 | Booking duration limits enum: 1/2/4/8/24 h/unlimited | `BookingDurationLimit` | Not enforced in booking |
| BR-15 | Listing availability: `is24Hours`, `availableFrom/To`, `availableDays` 1–7 | `PrivateParkingListing` | Not enforced in booking; time-of-day stored as full `Date` |
| BR-16 | Slot is bookable only if `!isOccupied && !isDisabled` | `bookSlot`, `requestBooking`, `filteredListings` | Client-side, racy (BUG-06) |
| BR-17 | Password ≥ 8 chars; name ≥ 2 on sign-up | `AuthenticationView.isFormValid` | |
| BR-18 | Add-listing validation: location set; ≥1 photo and a "video"; title non-empty; slots ≥ 1; commercial mode needs rate > 0 | `AddParkingFlowView.canProceed` | |
| BR-19 | Max 5 photos | `MediaStepView` | |
| BR-20 | Privacy: policy URL placeholder `YOUR_PRIVACY_POLICY_URL`; Terms URL `https://parkezy.com/terms` | `AppConfig`, `SettingsView` | Placeholder = App Store blocker |
