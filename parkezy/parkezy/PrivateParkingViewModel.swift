//
//  PrivateParkingViewModel.swift
//  ParkEzy
//
//  ViewModel for Private Parking - SEPARATE from Commercial Parking
//  Manages private listings, slots, bookings, and pricing intelligence
//

import SwiftUI
import CoreLocation
import Combine


@MainActor
class PrivateParkingViewModel: ObservableObject {
    // MARK: - Published Properties
    
    /// All private listings
    @Published var listings: [PrivateParkingListing] = []
    
    /// Currently selected listing (for detail view)
    @Published var selectedListing: PrivateParkingListing?
    
    /// All private bookings
    @Published var bookings: [PrivateBooking] = []
    
    /// Pending approval requests (for host)
    @Published var pendingApprovals: [PrivateBooking] = []
    
    /// Active bookings
    @Published var activeBookings: [PrivateBooking] = []
    
    /// Current host's listings (when in host mode)
    @Published var myListings: [PrivateParkingListing] = []

    /// Current signed-in user's profile (used to scope "my listings"/"my bookings")
    @Published var currentUser: AppUser?

    /// Filters
    @Published var filterMinPrice: Double?
    @Published var filterMaxPrice: Double?
    @Published var filterHasEV: Bool = false

    @Published var filterIsCovered: Bool = false
    
    // Timer for countdown updates
    private var countdownTimer: Timer?
    
    // Loading states
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    // MARK: - Initialization
    
    init() {
        startCountdownTimer()
        Task { await refreshListingsFromBackend() }
    }

    deinit {
        countdownTimer?.invalidate()
    }

    // MARK: - Countdown Timer

    private func startCountdownTimer() {
        countdownTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.objectWillChange.send()
            }
        }
    }

    // MARK: - Data Loading

    /// Fetches listings (and, if signed in, the current host's own listings/booking requests) from Supabase.
    /// `coordinate` is accepted for a future radius-scoped query; today it fetches all listings.
    func refreshListingsFromBackend(near coordinate: CLLocationCoordinate2D? = nil) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        if currentUser == nil, let session = try? await SupabaseConfig.client.auth.session {
            currentUser = await SupabaseService.shared.getUserProfile(id: session.user.id.uuidString)
        }

        listings = await SupabaseService.shared.getAllPrivateListings()
        calculateSuggestedPrices()

        guard let ownerID = currentUser?.id else {
            myListings = []
            return
        }

        myListings = listings.filter { $0.ownerID.uuidString == ownerID }

        let requests = await SupabaseService.shared.getPrivateBookingRequests(hostID: ownerID)
        bookings = requests
        pendingApprovals = requests.filter { $0.status == .pendingApproval }
        activeBookings = requests.filter { $0.status == .active }
    }

    private func createListing(
        title: String, address: String, lat: Double, lon: Double,
        slots: Int, hourly: Double, daily: Double = 300, monthly: Double = 3000,
        isCovered: Bool, hasEV: Bool, ownerID: UUID, ownerName: String
    ) -> PrivateParkingListing {
        PrivateParkingListing(
            id: UUID(),
            ownerID: ownerID,
            ownerName: ownerName,
            title: title,
            address: address,
            coordinates: CLLocationCoordinate2D(latitude: lat, longitude: lon),
            listingDescription: "A convenient parking spot in a safe residential area. Easy access and secure location.",
            slots: generatePrivateSlots(count: slots),
            hourlyRate: hourly,
            dailyRate: daily,
            monthlyRate: monthly,
            flatFullBookingRate: hourly * Double(slots) * 8,
            autoAcceptBookings: Bool.random(),
            instantBookingDiscount: Bool.random() ? 10 : nil,
            hasCCTV: Bool.random(),
            isCovered: isCovered,
            hasEVCharging: hasEV,
            hasSecurityGuard: Bool.random(),
            hasWaterAccess: Bool.random(),
            is24Hours: true,
            availableFrom: nil,
            availableTo: nil,
            availableDays: [1, 2, 3, 4, 5, 6, 7],
            rating: Double.random(in: 3.8...4.9),
            reviewCount: Int.random(in: 10...150),
            imageURLs: [],
            capturedPhotoData: nil,
            capturedVideoURL: nil,
            maxBookingDuration: .unlimited,
            suggestedHourlyRate: nil
        )
    }
    
    private func generatePrivateSlots(count: Int) -> [PrivateParkingSlot] {
        let labels = ["Garage", "Driveway Left", "Driveway Right", "Front Yard"]
        var slots: [PrivateParkingSlot] = []
        
        for i in 1...count {
            let isOccupied = Double.random(in: 0...1) < 0.3
            let endTime: Date? = isOccupied ? Date().addingTimeInterval(Double.random(in: 1800...28800)) : nil
            
            slots.append(PrivateParkingSlot(
                id: UUID(),
                slotNumber: i,
                slotLabel: count > 1 ? labels[min(i - 1, labels.count - 1)] : nil,
                vehicleSize: [.compact, .standard, .large].randomElement() ?? .compact,
                canFitSUV: i <= 2,
                canFitBike: true,
                isOccupied: isOccupied,
                isDisabled: false,
                currentBookingID: isOccupied ? UUID() : nil,
                bookingEndTime: endTime
            ))
        }
        return slots
    }
    
    // MARK: - Pricing Intelligence
    
    /// Calculate suggested prices based on nearby listings
    func calculateSuggestedPrices() {
        for i in 0..<listings.count {
            // Find nearby listings (within 2km)
            let nearbyListings = listings.filter { other in
                other.id != listings[i].id &&
                distance(from: listings[i].coordinates, to: other.coordinates) < 2000
            }
            
            guard !nearbyListings.isEmpty else {
                listings[i].suggestedHourlyRate = 40 // Default
                continue
            }
            
            // Calculate average
            let avgPrice = nearbyListings.reduce(0.0) { $0 + $1.hourlyRate } / Double(nearbyListings.count)
            listings[i].suggestedHourlyRate = round(avgPrice * 10) / 10
        }
    }
    
    private func distance(from: CLLocationCoordinate2D, to: CLLocationCoordinate2D) -> Double {
        let fromLocation = CLLocation(latitude: from.latitude, longitude: from.longitude)
        let toLocation = CLLocation(latitude: to.latitude, longitude: to.longitude)
        return fromLocation.distance(from: toLocation)
    }
    
    // MARK: - Booking Methods
    
    /// Request a booking (may require approval)
    func requestBooking(listingID: UUID, slotID: UUID, startTime: Date, endTime: Date, durationType: PrivateBookingDuration, driverMessage: String? = nil) -> PrivateBooking? {

        guard let listingIndex = listings.firstIndex(where: { $0.id == listingID }),
              let slotIndex = listings[listingIndex].slots.firstIndex(where: { $0.id == slotID }) else {
            return nil
        }
        
        let listing = listings[listingIndex]
        let slot = listing.slots[slotIndex]
        
        guard !slot.isOccupied && !slot.isDisabled else { return nil }
        
        let rate = listing.hourlyRate
        let duration = endTime.timeIntervalSince(startTime) / 3600
        let cost = rate * duration
        
        let driverID = currentUser.flatMap { UUID(uuidString: $0.id) } ?? UUID()

        let booking = PrivateBooking(
            id: UUID(),
            listingID: listingID,
            slotID: slotID,
            driverID: driverID,
            hostID: listing.ownerID,
            driverName: currentUser?.name ?? "Current User",
            driverPhone: currentUser?.phoneNumber ?? "",
            vehicleNumber: nil,
            requestTime: Date(),
            scheduledStartTime: startTime,
            scheduledEndTime: endTime,
            actualStartTime: nil,
            actualEndTime: nil,
            durationType: durationType,
            agreedRate: rate,
            estimatedCost: cost,
            actualCost: nil,
            hostEarnings: nil,
            status: listing.autoAcceptBookings ? .approved : .pendingApproval,
            approvalTime: listing.autoAcceptBookings ? Date() : nil,
            rejectionReason: nil,
            accessPIN: listing.autoAcceptBookings ? String(format: "%06d", Int.random(in: 100000...999999)) : nil,
            driverMessage: driverMessage,
            hostMessage: nil
        )

        bookings.append(booking)

        if listing.autoAcceptBookings {
            // Update slot immediately
            listings[listingIndex].slots[slotIndex].isOccupied = true
            listings[listingIndex].slots[slotIndex].currentBookingID = booking.id
            listings[listingIndex].slots[slotIndex].bookingEndTime = endTime
        } else {
            pendingApprovals.append(booking)
        }

        Task { _ = await SupabaseService.shared.createPrivateBookingRequest(booking) }

        return booking
    }


    /// Approve a pending booking (host action)
    func approveBooking(_ bookingID: UUID) {
        guard let index = bookings.firstIndex(where: { $0.id == bookingID }) else { return }

        bookings[index].status = .approved
        bookings[index].approvalTime = Date()
        bookings[index].accessPIN = String(format: "%06d", Int.random(in: 100000...999999))

        // Update slot
        if let listingIndex = listings.firstIndex(where: { $0.id == bookings[index].listingID }),
           let slotIndex = listings[listingIndex].slots.firstIndex(where: { $0.id == bookings[index].slotID }) {
            listings[listingIndex].slots[slotIndex].isOccupied = true
            listings[listingIndex].slots[slotIndex].currentBookingID = bookingID
            listings[listingIndex].slots[slotIndex].bookingEndTime = bookings[index].scheduledEndTime
        }

        pendingApprovals.removeAll { $0.id == bookingID }

        let updated = bookings[index]
        Task { _ = await SupabaseService.shared.updatePrivateBookingRequest(updated) }
    }

    /// Reuse the rejection logic
    func rejectBooking(_ bookingID: UUID, reason: String?) {
        guard let index = bookings.firstIndex(where: { $0.id == bookingID }) else { return }

        bookings[index].status = .rejected
        bookings[index].rejectionReason = reason

        pendingApprovals.removeAll { $0.id == bookingID }

        let updated = bookings[index]
        Task { _ = await SupabaseService.shared.updatePrivateBookingRequest(updated) }
    }
    
    // MARK: - Listing Management
    
    /// Create a new private listing
    func addListing(
        title: String,
        address: String,
        slots: Int,
        hourlyRate: Double,
        isCovered: Bool,
        hasCCTV: Bool,
        hasEV: Bool,
        description: String
    ) {
        // Create user ID (simulating current user)
        let ownerID = myListings.first?.ownerID ?? UUID()
        let ownerName = myListings.first?.ownerName ?? "Current User"
        
        let newListing = createListing(
            title: title,
            address: address,
            lat: 28.5 + Double.random(in: -0.1...0.1), // Random nearby location for demo
            lon: 77.2 + Double.random(in: -0.1...0.1),
            slots: slots,
            hourly: hourlyRate,
            isCovered: isCovered,
            hasEV: hasEV,
            ownerID: ownerID,
            ownerName: ownerName
        )
        
        // Update description and amenities
        var updatedListing = newListing
        updatedListing.listingDescription = description
        updatedListing.hasCCTV = hasCCTV
        
        listings.insert(updatedListing, at: 0)
        myListings.insert(updatedListing, at: 0)
    }
    
    /// Create a new private listing with explicit coordinates
    func addListingWithCoordinates(
        title: String,
        address: String,
        coordinates: CLLocationCoordinate2D,
        slots: Int,
        hourlyRate: Double,
        isCovered: Bool,
        hasCCTV: Bool,
        hasEV: Bool,
        description: String
    ) {
        let ownerID = myListings.first?.ownerID ?? UUID()
        let ownerName = myListings.first?.ownerName ?? "Current User"
        
        let newListing = createListing(
            title: title,
            address: address,
            lat: coordinates.latitude,
            lon: coordinates.longitude,
            slots: slots,
            hourly: hourlyRate,
            isCovered: isCovered,
            hasEV: hasEV,
            ownerID: ownerID,
            ownerName: ownerName
        )
        
        var updatedListing = newListing
        updatedListing.listingDescription = description
        updatedListing.hasCCTV = hasCCTV
        
        listings.insert(updatedListing, at: 0)
        myListings.insert(updatedListing, at: 0)
    }
    
    /// Create a new private listing with full details (from Add Parking Flow)
    func addListingWithFullDetails(
        title: String,
        address: String,
        coordinates: CLLocationCoordinate2D,
        slots: Int,
        hourlyRate: Double,
        dailyRate: Double,
        monthlyRate: Double,
        maxDuration: BookingDurationLimit,
        is24x7: Bool,
        availableStartTime: Date?,
        availableEndTime: Date?,
        availableDays: [Int],
        isCovered: Bool,
        hasCCTV: Bool,
        hasEVCharging: Bool,
        photoData: [Data],
        description: String
    ) {
        createListingLocally(
            title: title,
            address: address,
            coordinates: coordinates,
            slots: slots,
            hourlyRate: hourlyRate,
            dailyRate: dailyRate,
            monthlyRate: monthlyRate,
            is24x7: is24x7,
            availableStartTime: availableStartTime,
            availableEndTime: availableEndTime,
            availableDays: availableDays,
            isCovered: isCovered,
            hasCCTV: hasCCTV,
            hasEVCharging: hasEVCharging,
            photoData: photoData,
            description: description
        )
    }
    
    /// Create listing locally (fallback for offline mode)
    private func createListingLocally(
        title: String,
        address: String,
        coordinates: CLLocationCoordinate2D,
        slots: Int,
        hourlyRate: Double,
        dailyRate: Double,
        monthlyRate: Double,
        is24x7: Bool,
        availableStartTime: Date?,
        availableEndTime: Date?,
        availableDays: [Int],
        isCovered: Bool,
        hasCCTV: Bool,
        hasEVCharging: Bool,
        photoData: [Data],
        description: String
    ) {
        let ownerID = currentUser.flatMap { UUID(uuidString: $0.id) } ?? myListings.first?.ownerID ?? UUID()
        let ownerName = currentUser?.name ?? myListings.first?.ownerName ?? "Current User"

        let newSlots = generatePrivateSlots(count: slots)

        let newListing = PrivateParkingListing(
            id: UUID(),
            ownerID: ownerID,
            ownerName: ownerName,
            title: title,
            address: address,
            coordinates: coordinates,
            listingDescription: description.isEmpty ? "A great parking spot." : description,
            slots: newSlots,
            hourlyRate: hourlyRate,
            dailyRate: dailyRate,
            monthlyRate: monthlyRate,
            flatFullBookingRate: nil,
            autoAcceptBookings: false,
            instantBookingDiscount: nil,
            hasCCTV: hasCCTV,
            isCovered: isCovered,
            hasEVCharging: hasEVCharging,
            hasSecurityGuard: false,
            hasWaterAccess: false,
            is24Hours: is24x7,
            availableFrom: availableStartTime,
            availableTo: availableEndTime,
            availableDays: availableDays.isEmpty ? [1, 2, 3, 4, 5, 6, 7] : availableDays,
            rating: 5.0,
            reviewCount: 0,
            imageURLs: [],
            capturedPhotoData: photoData,
            capturedVideoURL: nil,
            maxBookingDuration: .unlimited,
            suggestedHourlyRate: nil
        )

        listings.insert(newListing, at: 0)
        myListings.insert(newListing, at: 0)

        // Calculate suggested prices including the new listing
        calculateSuggestedPrices()

        Task { _ = await SupabaseService.shared.createPrivateListing(newListing) }
    }

    /// Update an existing listing
    func updateListing(_ updatedListing: PrivateParkingListing, completion: @escaping (Bool) -> Void) {
        Task {
            isLoading = true
            defer { isLoading = false }

            let success = await SupabaseService.shared.updatePrivateListing(updatedListing)

            if success {
                if let index = self.listings.firstIndex(where: { $0.id == updatedListing.id }) {
                    self.listings[index] = updatedListing
                }
                if let index = self.myListings.firstIndex(where: { $0.id == updatedListing.id }) {
                    self.myListings[index] = updatedListing
                }
                self.calculateSuggestedPrices()
            } else {
                self.errorMessage = "Failed to update listing"
            }
            completion(success)
        }
    }
    
    /// Delete a listing
    func deleteListing(_ listing: PrivateParkingListing, completion: @escaping (Bool) -> Void) {
        Task {
            isLoading = true
            let success = await SupabaseService.shared.deletePrivateListing(id: listing.id.uuidString)
            
            await MainActor.run {
                if success {
                    listings.removeAll { $0.id == listing.id }
                    myListings.removeAll { $0.id == listing.id }
                    print("✅ Listing deleted from Supabase: \(listing.title)")
                } else {
                    errorMessage = "Failed to delete listing"
                }
                isLoading = false
                completion(success)
            }
        }
    }
    
    // MARK: - Computed Properties
    
    var filteredListings: [PrivateParkingListing] {
        listings.filter { listing in
            if let min = filterMinPrice, listing.hourlyRate < min {
                return false
            }
            if let max = filterMaxPrice, listing.hourlyRate > max {
                return false
            }
            if filterHasEV && !listing.hasEVCharging {
                return false
            }
            if filterIsCovered && !listing.isCovered {
                return false
            }
            return listing.availableSlots > 0
        }
    }
    
    func totalEarnings(for ownerID: UUID) -> Double {
        bookings
            .filter { $0.hostID == ownerID && $0.status == .completed }
            .compactMap { $0.hostEarnings }
            .reduce(0, +)
    }
    
    func pendingApprovalsCount(for ownerID: UUID) -> Int {
        pendingApprovals.filter { $0.hostID == ownerID }.count
    }
}
