//
//  CommercialParkingViewModel.swift
//  ParkEzy
//
//  ViewModel for Commercial Parking - SEPARATE from Private Parking
//  Manages commercial facilities, slots, and bookings
//

import SwiftUI
import CoreLocation
import Combine

@MainActor
class CommercialParkingViewModel: ObservableObject {
    // MARK: - Published Properties
    
    /// All commercial facilities
    @Published var facilities: [CommercialParkingFacility] = []
    
    /// Currently selected facility (for detail view)
    @Published var selectedFacility: CommercialParkingFacility?
    
    /// All commercial bookings
    @Published var bookings: [CommercialBooking] = []
    
    /// Active bookings only
    @Published var activeBookings: [CommercialBooking] {
        didSet { updateSlotOccupancy() }
    }
    
    /// Filter states
    @Published var filterByType: CommercialFacilityType?
    @Published var filterHasEV: Bool = false
    @Published var filterHasValet: Bool = false
    
    // Repository references (for Firebase mode)
    private let facilityRepo = CommercialFacilityRepository.shared
    private let bookingRepo = BookingRepository.shared
    
    // Timer for countdown updates
    private var countdownTimer: Timer?
    
    // Loading states
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    // MARK: - Initialization
    
    init() {
        activeBookings = []
        
        if AppConfig.useFirebase {
            loadFromFirebase()
        } else {
            generateMockFacilities()
            generateMockBookings()
        }
        startCountdownTimer()
    }
    
    deinit {
        countdownTimer?.invalidate()
    }
    
    // MARK: - Firebase Data Loading
    
    /// Load facilities from Firebase
    private func loadFromFirebase() {
        Task {
            isLoading = true
            defer { isLoading = false }
            
            do {
                let defaultLocation = CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090)
                facilities = try await facilityRepo.getNearbyFacilities(location: defaultLocation, radiusKm: 20)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }
    
    /// Refresh facilities from Firebase
    func refreshFacilities(near location: CLLocationCoordinate2D? = nil) async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            let searchLocation = location ?? CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090)
            facilities = try await facilityRepo.getNearbyFacilities(location: searchLocation, radiusKm: 20)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
    
    // MARK: - Countdown Timer
    
    private func startCountdownTimer() {
        countdownTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.objectWillChange.send()
            }
        }
    }
    
    // MARK: - Mock Data Generation
    
    private func generateMockFacilities() {
        facilities = [
            // Mall facilities
            createMallFacility(
                name: "Select Citywalk",
                address: "Saket District Centre, Press Enclave Marg",
                lat: 28.5285, lon: 77.2182,
                totalSlots: 120,
                hourlyRate: 60
            ),
            createMallFacility(
                name: "DLF Promenade",
                address: "Vasant Kunj, Nelson Mandela Marg",
                lat: 28.5398, lon: 77.1546,
                totalSlots: 200,
                hourlyRate: 80
            ),
            createMallFacility(
                name: "Ambience Mall",
                address: "NH-8, Gurugram",
                lat: 28.5040, lon: 77.0968,
                totalSlots: 350,
                hourlyRate: 100
            ),
            createMallFacility(
                name: "Pacific Mall",
                address: "Tagore Garden, Subhash Nagar",
                lat: 28.6391, lon: 77.1098,
                totalSlots: 80,
                hourlyRate: 50
            ),
            
            // Office facilities
            createOfficeFacility(
                name: "Cyber Hub Tower",
                address: "DLF Cyber City, Gurugram",
                lat: 28.4949, lon: 77.0884,
                totalSlots: 150,
                hourlyRate: 70
            ),
            createOfficeFacility(
                name: "One Horizon Center",
                address: "Golf Course Road, Gurugram",
                lat: 28.4595, lon: 77.1025,
                totalSlots: 100,
                hourlyRate: 90
            ),
            
            // Hospital
            CommercialParkingFacility(
                id: UUID(),
                name: "Max Super Speciality Hospital",
                address: "Saket, New Delhi",
                coordinates: CLLocationCoordinate2D(latitude: 28.5275, longitude: 77.2150),
                facilityType: .hospital,
                slots: generateSlots(count: 60, hospitalConfig: true),
                defaultHourlyRate: 40,
                flatDayRate: 200,
                hasCCTV: true, hasEVCharging: true, hasValetService: true, hasCarWash: false, is24Hours: true,
                rating: 4.5, reviewCount: 234,
                ownerID: UUID(), ownerName: "Max Healthcare"
            ),
            
            // Airport
            CommercialParkingFacility(
                id: UUID(),
                name: "IGI Airport Terminal 3",
                address: "Indira Gandhi International Airport",
                coordinates: CLLocationCoordinate2D(latitude: 28.5562, longitude: 77.0999),
                facilityType: .airport,
                slots: generateSlots(count: 500, airportConfig: true),
                defaultHourlyRate: 100,
                flatDayRate: 500,
                hasCCTV: true, hasEVCharging: true, hasValetService: true, hasCarWash: true, is24Hours: true,
                rating: 4.7, reviewCount: 1523,
                ownerID: UUID(), ownerName: "Delhi International Airport Ltd"
            )
        ]
    }
    
    private func createMallFacility(name: String, address: String, lat: Double, lon: Double, totalSlots: Int, hourlyRate: Double) -> CommercialParkingFacility {
        CommercialParkingFacility(
            id: UUID(),
            name: name,
            address: address,
            coordinates: CLLocationCoordinate2D(latitude: lat, longitude: lon),
            facilityType: .mall,
            slots: generateSlots(count: totalSlots),
            defaultHourlyRate: hourlyRate,
            flatDayRate: hourlyRate * 8, // 8 hours = day rate
            hasCCTV: true, hasEVCharging: true, hasValetService: true, hasCarWash: true, is24Hours: true,
            rating: Double.random(in: 4.0...4.9),
            reviewCount: Int.random(in: 100...800),
            ownerID: UUID(), ownerName: "\(name) Management"
        )
    }
    
    private func createOfficeFacility(name: String, address: String, lat: Double, lon: Double, totalSlots: Int, hourlyRate: Double) -> CommercialParkingFacility {
        CommercialParkingFacility(
            id: UUID(),
            name: name,
            address: address,
            coordinates: CLLocationCoordinate2D(latitude: lat, longitude: lon),
            facilityType: .office,
            slots: generateSlots(count: totalSlots, officeConfig: true),
            defaultHourlyRate: hourlyRate,
            flatDayRate: hourlyRate * 10,
            hasCCTV: true, hasEVCharging: true, hasValetService: false, hasCarWash: false, is24Hours: false,
            rating: Double.random(in: 4.0...4.8),
            reviewCount: Int.random(in: 50...300),
            ownerID: UUID(), ownerName: "\(name) Properties"
        )
    }
    
    private func generateSlots(count: Int, officeConfig: Bool = false, hospitalConfig: Bool = false, airportConfig: Bool = false) -> [CommercialParkingSlot] {
        var slots: [CommercialParkingSlot] = []
        let floors = airportConfig ? [-2, -1, 0, 1, 2, 3] : [-1, 0, 1, 2]
        let slotsPerFloor = count / floors.count
        
        for floor in floors {
            for i in 1...slotsPerFloor {
                let floorPrefix = floor < 0 ? "B\(abs(floor))" : (floor == 0 ? "G" : "L\(floor)")
                let slotNumber = "\(floorPrefix)-\(String(format: "%02d", i))"
                
                // Determine slot type
                let slotType: CommercialSlotType
                if i <= 2 {
                    slotType = .accessible
                } else if i <= 5 {
                    slotType = .evCharging
                } else if i <= 8 && !officeConfig {
                    slotType = .valet
                } else if i % 10 == 0 {
                    slotType = .large
                } else if i % 7 == 0 {
                    slotType = .compact
                } else {
                    slotType = .regular
                }
                
                // Random occupancy (30-50% occupied)
                let isOccupied = Double.random(in: 0...1) < 0.4
                let endTime: Date? = isOccupied ? Date().addingTimeInterval(Double.random(in: 1800...14400)) : nil
                
                slots.append(CommercialParkingSlot(
                    id: UUID(),
                    slotNumber: slotNumber,
                    slotType: slotType,
                    floor: floor,
                    isOccupied: isOccupied,
                    isDisabled: Double.random(in: 0...1) < 0.05, // 5% disabled
                    currentBookingID: isOccupied ? UUID() : nil,
                    bookingEndTime: endTime,
                    hourlyRateOverride: slotType == .evCharging ? 90 : nil
                ))
            }
        }
        return slots
    }
    
    private func generateMockBookings() {
        let calendar = Calendar.current
        let now = Date()
        
        // Generate 50 completed bookings across facilities
        for facility in facilities {
            for _ in 0..<Int.random(in: 5...15) {
                guard let slot = facility.slots.randomElement() else { continue }
                let daysAgo = Int.random(in: 0...30)
                let startTime = calendar.date(byAdding: .day, value: -daysAgo, to: now)!
                let duration = Double.random(in: 1...6)
                let endTime = calendar.date(byAdding: .hour, value: Int(duration), to: startTime)!
                
                let booking = CommercialBooking(
                    id: UUID(),
                    facilityID: facility.id,
                    slotID: slot.id,
                    driverID: UUID(),
                    bookingTime: startTime.addingTimeInterval(-3600),
                    scheduledStartTime: startTime,
                    scheduledEndTime: endTime,
                    actualStartTime: startTime,
                    actualEndTime: endTime,
                    hourlyRate: facility.defaultHourlyRate,
                    estimatedDuration: duration,
                    estimatedCost: facility.defaultHourlyRate * duration * 1.18,
                    actualCost: facility.defaultHourlyRate * duration * 1.18,
                    vehicleNumber: "DL \(Int.random(in: 1...14)) \(["A", "B", "C", "S", "T"].randomElement()!) \(Int.random(in: 1000...9999))",
                    vehicleType: ["Sedan", "SUV", "Hatchback", "Compact"].randomElement(),
                    status: .completed,
                    accessCode: String(format: "%06d", Int.random(in: 100000...999999))
                )
                bookings.append(booking)
            }
        }
        
        // Active bookings (update from slots that are occupied)
        activeBookings = bookings.filter { $0.status == .active }
    }
    
    // MARK: - Slot Management
    
    private func updateSlotOccupancy() {
        // Update slot occupancy based on active bookings
        for i in 0..<facilities.count {
            for j in 0..<facilities[i].slots.count {
                if let booking = activeBookings.first(where: { $0.slotID == facilities[i].slots[j].id }) {
                    facilities[i].slots[j].isOccupied = true
                    facilities[i].slots[j].currentBookingID = booking.id
                    facilities[i].slots[j].bookingEndTime = booking.scheduledEndTime
                }
            }
        }
    }
    
    // MARK: - Booking Methods
    
    /// Book a slot (auto-approved for commercial)
    func bookSlot(facilityID: UUID, slotID: UUID, startTime: Date, duration: Double) -> CommercialBooking? {
        guard let facilityIndex = facilities.firstIndex(where: { $0.id == facilityID }),
              let slotIndex = facilities[facilityIndex].slots.firstIndex(where: { $0.id == slotID }) else {
            return nil
        }
        
        let facility = facilities[facilityIndex]
        let slot = facility.slots[slotIndex]
        
        guard !slot.isOccupied && !slot.isDisabled else { return nil }
        
        let hourlyRate = slot.hourlyRateOverride ?? facility.defaultHourlyRate
        let endTime = startTime.addingTimeInterval(duration * 3600)
        
        let booking = CommercialBooking(
            id: UUID(),
            facilityID: facilityID,
            slotID: slotID,
            driverID: UUID(), // Would come from auth
            bookingTime: Date(),
            scheduledStartTime: startTime,
            scheduledEndTime: endTime,
            actualStartTime: nil,
            actualEndTime: nil,
            hourlyRate: hourlyRate,
            estimatedDuration: duration,
            estimatedCost: hourlyRate * duration * 1.18,
            actualCost: nil,
            vehicleNumber: nil,
            vehicleType: nil,
            status: .pending,
            accessCode: String(format: "%06d", Int.random(in: 100000...999999))
        )
        
        // Update slot
        facilities[facilityIndex].slots[slotIndex].isOccupied = true
        facilities[facilityIndex].slots[slotIndex].currentBookingID = booking.id
        facilities[facilityIndex].slots[slotIndex].bookingEndTime = endTime
        
        bookings.append(booking)
        return booking
    }
    
    // MARK: - Computed Properties
    
    var filteredFacilities: [CommercialParkingFacility] {
        facilities.filter { facility in
            if let type = filterByType, facility.facilityType != type {
                return false
            }
            if filterHasEV && !facility.hasEVCharging {
                return false
            }
            if filterHasValet && !facility.hasValetService {
                return false
            }
            return true
        }
    }
    
    func availableSlotsCount(for facility: CommercialParkingFacility) -> Int {
        facility.slots.filter { !$0.isOccupied && !$0.isDisabled }.count
    }
    
    func slotsForFloor(_ floor: Int, in facility: CommercialParkingFacility) -> [CommercialParkingSlot] {
        facility.slots.filter { $0.floor == floor }
    }
    
    func floorsInFacility(_ facility: CommercialParkingFacility) -> [Int] {
        Array(Set(facility.slots.map { $0.floor })).sorted()
    }
}
