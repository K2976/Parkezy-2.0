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
    

    // Timer for countdown updates
    private var countdownTimer: Timer?

    // Loading states
    @Published var isLoading = false
    @Published var errorMessage: String?

    // Cached from the last session check, used to attribute new bookings to the signed-in driver
    private var currentDriverID: UUID?
    
    // MARK: - Initialization
    
    init() {
        activeBookings = []
        startCountdownTimer()
        Task { await refreshFacilitiesFromBackend() }
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

    /// Fetches commercial facilities (and, if signed in, the driver's own bookings) from Supabase.
    /// `coordinate` is accepted for a future radius-scoped query; today it fetches all facilities.
    func refreshFacilitiesFromBackend(near coordinate: CLLocationCoordinate2D? = nil) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        facilities = await SupabaseService.shared.getAllCommercialFacilities()

        if let session = try? await SupabaseConfig.client.auth.session {
            currentDriverID = session.user.id
            bookings = await SupabaseService.shared.getCommercialBookings(driverID: session.user.id.uuidString)
        }

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
            driverID: currentDriverID ?? UUID(),
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

        Task { _ = await SupabaseService.shared.createCommercialBooking(booking) }

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
