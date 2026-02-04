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
import FirebaseAuth

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
    
    /// Filters
    @Published var filterMinPrice: Double?
    @Published var filterMaxPrice: Double?
    @Published var filterHasEV: Bool = false

    @Published var filterIsCovered: Bool = false
    
    /// User Profile
    @Published var currentUser: UserProfile?
    
    // Repository reference (for Firebase mode)
    private let listingRepo = PrivateListingRepository.shared
    private let bookingRepo = BookingRepository.shared
    
    // Timer for countdown updates
    private var countdownTimer: Timer?
    
    // Loading states
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    // MARK: - Initialization
    
    init() {
        if AppConfig.useFirebase {
            // Load from Backend (Django)
            Task {
                await refreshListingsFromBackend()
            }
        } else {
            // Use mock data for development/testing
            generateMockListings()
            generateMockBookings()
            calculateSuggestedPrices()
        }
        startCountdownTimer()
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
    
    // MARK: - Firebase Data Loading
    
    /// Load listings and bookings from Firebase
    // MARK: - Legacy Firebase Data Loading (Removed)
    
    // loadFromFirebase removed as we now use refreshListingsFromBackend

    
    /// Refresh listings from Backend (Django)
    func refreshListingsFromBackend(near location: CLLocationCoordinate2D? = nil) async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            // 1. Fetch ALL listings for Driver View
            let backendListings = try await ParkingAPIService.shared.getAllPrivateListings()
            let mappedListings = backendListings.map { $0.toAppModel() }
            
            await MainActor.run {
                self.listings = mappedListings
            }
            
            // 2. Fetch MY listings for Host View (if logged in)
            if Auth.auth().currentUser != nil {
                let myListingsResponse = try await ParkingAPIService.shared.getMyPrivateListings()
                let mappedMyListings = myListingsResponse.map { $0.toAppModel() }
                
                await MainActor.run {
                    self.myListings = mappedMyListings
                }
            } else {
                await MainActor.run {
                    self.myListings = []
                }
            }
            
            // 3. Fetch User Profile
            if Auth.auth().currentUser != nil {
                await fetchCurrentUser()
            }
            
            await MainActor.run {
                calculateSuggestedPrices()
            }
            
        } catch {
            print("❌ Backend fetch failed: \(error.localizedDescription)")
            await MainActor.run {
                errorMessage = error.localizedDescription
            }
        }
    }
    
    // MARK: - Mock Data Generation
    
    private func generateMockListings() {
        let ownerID = UUID() // Current host
        
        listings = [
            // GK-1 area listings
            createListing(
                title: "Covered Driveway in GK-1",
                address: "M-45, Greater Kailash 1",
                lat: 28.5494, lon: 77.2344,
                slots: 2, hourly: 45, daily: 350, monthly: 3200,
                isCovered: true, hasEV: false, ownerID: ownerID, ownerName: "Priya Sharma"
            ),
            createListing(
                title: "Secure Garage Parking",
                address: "C-12, Greater Kailash 2",
                lat: 28.5398, lon: 77.2420,
                slots: 1, hourly: 55, daily: 400, monthly: 3800,
                isCovered: true, hasEV: true, ownerID: ownerID, ownerName: "Rahul Mehta"
            ),
            
            // Defence Colony
            createListing(
                title: "Open Driveway Space",
                address: "A-23, Defence Colony",
                lat: 28.5742, lon: 77.2310,
                slots: 3, hourly: 35, daily: 280, monthly: 2800,
                isCovered: false, hasEV: false, ownerID: UUID(), ownerName: "Amit Singh"
            ),
            createListing(
                title: "Premium Basement Parking",
                address: "B-Block, Defence Colony",
                lat: 28.5720, lon: 77.2335,
                slots: 2, hourly: 60, daily: 450, monthly: 4200,
                isCovered: true, hasEV: true, ownerID: UUID(), ownerName: "Neha Gupta"
            ),
            
            // Hauz Khas
            createListing(
                title: "Artist Colony Parking",
                address: "Hauz Khas Village",
                lat: 28.5494, lon: 77.2001,
                slots: 1, hourly: 40, daily: 300, monthly: 3000,
                isCovered: false, hasEV: false, ownerID: UUID(), ownerName: "Vikram Bhatia"
            ),
            
            // Vasant Vihar
            createListing(
                title: "Secure Home Parking",
                address: "C-45, Vasant Vihar",
                lat: 28.5612, lon: 77.1598,
                slots: 2, hourly: 50, daily: 380, monthly: 3600,
                isCovered: true, hasEV: true, ownerID: UUID(), ownerName: "Sunita Kapoor"
            ),
            
            // Green Park
            createListing(
                title: "Convenient Street Parking",
                address: "Green Park Extension",
                lat: 28.5598, lon: 77.2089,
                slots: 2, hourly: 30, daily: 250, monthly: 2500,
                isCovered: false, hasEV: false, ownerID: UUID(), ownerName: "Rajesh Kumar"
            ),
            
            // Lajpat Nagar
            createListing(
                title: "Market Area Parking",
                address: "Lajpat Nagar II",
                lat: 28.5680, lon: 77.2408,
                slots: 4, hourly: 35, daily: 270, monthly: 2700,
                isCovered: true, hasEV: false, ownerID: UUID(), ownerName: "Pooja Verma"
            ),
            
            // Noida
            createListing(
                title: "Society Visitor Parking",
                address: "Sector 62, Noida",
                lat: 28.6273, lon: 77.3649,
                slots: 3, hourly: 25, daily: 200, monthly: 2000,
                isCovered: true, hasEV: true, ownerID: UUID(), ownerName: "Arun Joshi"
            ),
            
            // Gurugram
            createListing(
                title: "Luxury Villa Parking",
                address: "DLF Phase 4, Gurugram",
                lat: 28.4650, lon: 77.0920,
                slots: 3, hourly: 70,
                isCovered: true, hasEV: true, ownerID: UUID(), ownerName: "Kavita Malhotra"
            ),
            createListing(
                title: "Budget Friendly Spot",
                address: "Sushant Lok, Gurugram",
                lat: 28.4698, lon: 77.0715,
                slots: 1, hourly: 30, daily: 220, monthly: 2200,
                isCovered: false, hasEV: false, ownerID: UUID(), ownerName: "Deepak Arora"
            )
        ]
        
        
        
        // Filter "my listings" to strictly match the current mock owner
        myListings = listings.filter { $0.ownerID == ownerID }
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
                vehicleSize: [.compact, .standard, .large].randomElement()!,
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
    
    private func generateMockBookings() {
        let calendar = Calendar.current
        let now = Date()
        
        // Generate bookings for listings
        for listing in listings {
            // Completed bookings
            for _ in 0..<Int.random(in: 3...10) {
                guard let slot = listing.slots.randomElement() else { continue }
                let daysAgo = Int.random(in: 1...30)
                let startTime = calendar.date(byAdding: .day, value: -daysAgo, to: now)!
                let durationType: PrivateBookingDuration = [.hourly, .daily].randomElement()!
                let duration = durationType == .hourly ? Double.random(in: 2...8) : 24
                let endTime = calendar.date(byAdding: .hour, value: Int(duration), to: startTime)!
                let rate = durationType == .hourly ? listing.hourlyRate : listing.dailyRate
                
                let booking = PrivateBooking(
                    id: UUID(),
                    listingID: listing.id,
                    slotID: slot.id,
                    driverID: UUID(),
                    hostID: listing.ownerID,
                    driverName: ["Rohit", "Sneha", "Arjun", "Meera", "Karan"].randomElement()!,
                    driverPhone: "+91 98765 \(Int.random(in: 10000...99999))",
                    vehicleNumber: "DL \(Int.random(in: 1...14)) \(["A", "B", "C", "S"].randomElement()!) \(Int.random(in: 1000...9999))",
                    requestTime: startTime.addingTimeInterval(-7200),
                    scheduledStartTime: startTime,
                    scheduledEndTime: endTime,
                    actualStartTime: startTime,
                    actualEndTime: endTime,
                    durationType: durationType,
                    agreedRate: rate,
                    estimatedCost: rate * (durationType == .hourly ? duration : 1),
                    actualCost: rate * (durationType == .hourly ? duration : 1),
                    hostEarnings: rate * (durationType == .hourly ? duration : 1) * 0.85,
                    status: .completed,
                    approvalTime: startTime.addingTimeInterval(-3600),
                    rejectionReason: nil,
                    accessPIN: String(format: "%06d", Int.random(in: 100000...999999)),
                    driverMessage: nil,
                    hostMessage: nil
                )
                bookings.append(booking)
            }
        }
        
        // Add some pending approvals for host demo
        for i in 0..<3 {
            let listing = myListings[i % myListings.count]
            guard let slot = listing.slots.first(where: { !$0.isOccupied }) else { continue }
            
            let booking = PrivateBooking(
                id: UUID(),
                listingID: listing.id,
                slotID: slot.id,
                driverID: UUID(),
                hostID: listing.ownerID,
                driverName: ["Aarav Sharma", "Diya Patel", "Vihaan Kapoor"][i],
                driverPhone: "+91 99887 \(Int.random(in: 10000...99999))",
                vehicleNumber: "DL \(Int.random(in: 1...14)) S \(Int.random(in: 1000...9999))",
                requestTime: Date().addingTimeInterval(-Double.random(in: 300...3600)),
                scheduledStartTime: Date().addingTimeInterval(Double.random(in: 1800...7200)),
                scheduledEndTime: Date().addingTimeInterval(Double.random(in: 14400...28800)),
                actualStartTime: nil,
                actualEndTime: nil,
                durationType: .hourly,
                agreedRate: listing.hourlyRate,
                estimatedCost: listing.hourlyRate * Double.random(in: 2...6),
                actualCost: nil,
                hostEarnings: nil,
                status: .pendingApproval,
                approvalTime: nil,
                rejectionReason: nil,
                accessPIN: nil,
                driverMessage: ["Need parking for meeting", "Shopping trip", nil][i],
                hostMessage: nil
            )
            pendingApprovals.append(booking)
            bookings.append(booking)
        }
        
        activeBookings = bookings.filter { $0.status == .active }
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
        // For Firebase mode, use async version
        if AppConfig.useFirebase {
            Task {
                await requestBookingAsync(
                    listingID: listingID.uuidString,
                    slotID: slotID.uuidString,
                    startTime: startTime,
                    endTime: endTime,
                    durationType: durationType,
                    driverMessage: driverMessage
                )
            }
            return nil // Booking created asynchronously
        }
        
        // Mock data path (existing logic)
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
        
        let booking = PrivateBooking(
            id: UUID(),
            listingID: listingID,
            slotID: slotID,
            driverID: UUID(),
            hostID: listing.ownerID,
            driverName: "Current User", // Would come from auth
            driverPhone: "+91 98765 43210",
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
        
        return booking
    }
    
    /// Firebase-integrated async booking request
    func requestBookingAsync(listingID: String, slotID: String, startTime: Date, endTime: Date, durationType: PrivateBookingDuration, driverMessage: String?) async {
        guard let listing = listings.first(where: { $0.id.uuidString == listingID }) else { return }
        
        let rate = listing.hourlyRate
        let duration = endTime.timeIntervalSince(startTime) / 3600
        let cost = rate * duration
        
        let request = PrivateBookingRequest(
            listingID: listingID,
            slotID: slotID,
            hostID: listing.ownerID.uuidString,
            scheduledStart: startTime,
            scheduledEnd: endTime,
            hourlyRate: rate,
            estimatedCost: cost * 1.18, // Including GST
            driverMessage: driverMessage
        )
        
        do {
            _ = try await bookingRepo.requestPrivateBooking(request)
            // Refresh listings to show updated availability
            await refreshListingsFromBackend()
        } catch {
            errorMessage = error.localizedDescription
        }
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
    }
    
    /// Reuse the rejection logic
    func rejectBooking(_ bookingID: UUID, reason: String?) {
        guard let index = bookings.firstIndex(where: { $0.id == bookingID }) else { return }
        
        bookings[index].status = .rejected
        bookings[index].rejectionReason = reason
        
        pendingApprovals.removeAll { $0.id == bookingID }
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
        // Use async task to POST to Django backend
        Task {
            do {
                // Create request for Django API
                let request = CreatePrivateListingRequest(
                    title: title,
                    address: address,
                    latitude: coordinates.latitude,
                    longitude: coordinates.longitude,
                    description: description.isEmpty ? nil : description,
                    hourlyRate: hourlyRate,
                    dailyRate: dailyRate > 0 ? dailyRate : nil,
                    monthlyRate: monthlyRate > 0 ? monthlyRate : nil,
                    availableSlots: slots,
                    isCovered: isCovered,
                    hasCctv: hasCCTV,
                    hasEvCharging: hasEVCharging,
                    is24Hours: is24x7,
                    availableStartTime: availableStartTime?.formatted(date: .omitted, time: .shortened),
                    availableEndTime: availableEndTime?.formatted(date: .omitted, time: .shortened),
                    availableDays: availableDays.isEmpty ? nil : availableDays
                )
                
                // POST to Django backend
                let response = try await ParkingAPIService.shared.createPrivateListing(request)
                
                print("✅ Parking listing created successfully with ID: \(response.id)")
                
                // Convert response to app model and add to local list
                await MainActor.run {
                    let newListing = response.toAppModel()
                    listings.insert(newListing, at: 0)
                    myListings.insert(newListing, at: 0)
                    
                    // Calculate suggested prices including the new listing
                    calculateSuggestedPrices()
                }
                
                // Refresh all listings from backend to ensure sync
                await refreshListingsFromBackend()
                
            } catch {
                print("❌ Failed to create parking listing: \(error.localizedDescription)")
                errorMessage = "Failed to create listing: \(error.localizedDescription)"
                
                // Fallback: Create listing locally (for offline mode)
                await MainActor.run {
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
            }
        }
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
        let ownerID = myListings.first?.ownerID ?? UUID()
        let ownerName = myListings.first?.ownerName ?? "Current User"
        
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
    }
    
    /// Update an existing listing
    func updateListing(_ updatedListing: PrivateParkingListing, completion: @escaping (Bool) -> Void) {
        Task {
            isLoading = true
            defer { isLoading = false }
            
            do {
                if !AppConfig.useFirebase, let backendID = updatedListing.backendID {
                    // Update on Backend
                    let request = UpdatePrivateListingRequest(
                        title: updatedListing.title,
                        address: updatedListing.address,
                        latitude: updatedListing.coordinates.latitude,
                        longitude: updatedListing.coordinates.longitude,
                        description: updatedListing.listingDescription,
                        hourlyRate: updatedListing.hourlyRate,
                        dailyRate: updatedListing.dailyRate,
                        monthlyRate: updatedListing.monthlyRate,
                        availableSlots: updatedListing.totalSlots,
                        isCovered: updatedListing.isCovered,
                        hasCctv: updatedListing.hasCCTV,
                        hasEvCharging: updatedListing.hasEVCharging,
                        is24Hours: updatedListing.is24Hours,
                        availableStartTime: nil, // TODO: Format dates if needed
                        availableEndTime: nil,
                        availableDays: updatedListing.availableDays,
                        autoAcceptBookings: updatedListing.autoAcceptBookings
                    )
                    
                    _ = try await ParkingAPIService.shared.updatePrivateListing(id: backendID, request: request)
                    print("✅ Listing updated on Backend: \(updatedListing.title)")
                }
                
                // Update local state
                await MainActor.run {
                    if let index = self.listings.firstIndex(where: { $0.id == updatedListing.id }) {
                        self.listings[index] = updatedListing
                    }
                    if let index = self.myListings.firstIndex(where: { $0.id == updatedListing.id }) {
                        self.myListings[index] = updatedListing
                    }
                    self.calculateSuggestedPrices()
                    completion(true)
                }
                
            } catch {
                print("❌ Failed to update listing: \(error.localizedDescription)")
                await MainActor.run {
                    self.errorMessage = "Failed to update listing: \(error.localizedDescription)"
                    completion(false)
                }
            }
        }
    }
    
    /// Fetch current user profile
    func fetchCurrentUser() async {
        do {
            let profile = try await ParkingAPIService.shared.getUserProfile()
            await MainActor.run {
                self.currentUser = profile
            }
        } catch {
            print("⚠️ Failed to fetch user profile: \(error.localizedDescription)")
        }
    }
    
    /// Delete a listing
    func deleteListing(_ listing: PrivateParkingListing, completion: @escaping (Bool) -> Void) {
        listings.removeAll { $0.id == listing.id }
        myListings.removeAll { $0.id == listing.id }
        
        // TODO: Sync with backend when API is ready
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            print("✅ Listing deleted: \(listing.title)")
            completion(true)
        }
    }
    
    /// Refresh listings from Django backend
    // Duplicate refreshListingsFromBackend removed

    
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
