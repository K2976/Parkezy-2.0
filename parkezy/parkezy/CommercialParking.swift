//
//  CommercialParking.swift
//  ParkEzy
//
//  Models for Commercial Parking (Mall, Office, Apartment)
//  SEPARATE from Private Parking - DO NOT MERGE
//

import Foundation
import CoreLocation
import SwiftUI

// MARK: - Commercial Parking Facility

/// Represents a commercial parking facility (Mall, Office, Apartment complex)
/// Contains multiple slots that can be booked independently
struct CommercialParkingFacility: Identifiable, Hashable, Codable {
    let id: UUID
    var name: String
    var address: String
    var coordinates: CLLocationCoordinate2D
    var facilityType: CommercialFacilityType
    
    // Slot management
    var slots: [CommercialParkingSlot]
    var totalSlots: Int { slots.count }
    var availableSlots: Int { slots.filter { !$0.isOccupied }.count }
    
    // Pricing (default hourly rate, can be overridden per slot)
    var defaultHourlyRate: Double
    var flatDayRate: Double? // Optional full-day flat price
    
    // Amenities
    var hasCCTV: Bool
    var hasEVCharging: Bool
    var hasValetService: Bool
    var hasCarWash: Bool
    var is24Hours: Bool
    
    // Ratings
    var rating: Double
    var reviewCount: Int
    
    // Owner info
    var ownerID: UUID
    var ownerName: String
    
    // MARK: - Hashable

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: CommercialParkingFacility, rhs: CommercialParkingFacility) -> Bool {
        lhs.id == rhs.id
    }

    // MARK: - Codable (maps to the 'commercial_facilities' table; lat/lng columns <-> coordinates)

    private enum CodingKeys: String, CodingKey {
        case id, name, address
        case lat, lng
        case facilityType = "facility_type"
        case slots
        case defaultHourlyRate = "default_hourly_rate"
        case flatDayRate = "flat_day_rate"
        case hasCCTV = "has_cctv"
        case hasEVCharging = "has_ev_charging"
        case hasValetService = "has_valet_service"
        case hasCarWash = "has_car_wash"
        case is24Hours = "is_24_hours"
        case rating
        case reviewCount = "review_count"
        case ownerID = "owner_id"
        case ownerName = "owner_name"
    }

    init(id: UUID, name: String, address: String, coordinates: CLLocationCoordinate2D, facilityType: CommercialFacilityType, slots: [CommercialParkingSlot], defaultHourlyRate: Double, flatDayRate: Double? = nil, hasCCTV: Bool, hasEVCharging: Bool, hasValetService: Bool, hasCarWash: Bool, is24Hours: Bool, rating: Double, reviewCount: Int, ownerID: UUID, ownerName: String) {
        self.id = id
        self.name = name
        self.address = address
        self.coordinates = coordinates
        self.facilityType = facilityType
        self.slots = slots
        self.defaultHourlyRate = defaultHourlyRate
        self.flatDayRate = flatDayRate
        self.hasCCTV = hasCCTV
        self.hasEVCharging = hasEVCharging
        self.hasValetService = hasValetService
        self.hasCarWash = hasCarWash
        self.is24Hours = is24Hours
        self.rating = rating
        self.reviewCount = reviewCount
        self.ownerID = ownerID
        self.ownerName = ownerName
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        address = try container.decode(String.self, forKey: .address)
        let lat = try container.decode(Double.self, forKey: .lat)
        let lng = try container.decode(Double.self, forKey: .lng)
        coordinates = CLLocationCoordinate2D(latitude: lat, longitude: lng)
        facilityType = try container.decode(CommercialFacilityType.self, forKey: .facilityType)
        slots = try container.decode([CommercialParkingSlot].self, forKey: .slots)
        defaultHourlyRate = try container.decode(Double.self, forKey: .defaultHourlyRate)
        flatDayRate = try container.decodeIfPresent(Double.self, forKey: .flatDayRate)
        hasCCTV = try container.decode(Bool.self, forKey: .hasCCTV)
        hasEVCharging = try container.decode(Bool.self, forKey: .hasEVCharging)
        hasValetService = try container.decode(Bool.self, forKey: .hasValetService)
        hasCarWash = try container.decode(Bool.self, forKey: .hasCarWash)
        is24Hours = try container.decode(Bool.self, forKey: .is24Hours)
        rating = try container.decode(Double.self, forKey: .rating)
        reviewCount = try container.decode(Int.self, forKey: .reviewCount)
        ownerID = try container.decode(UUID.self, forKey: .ownerID)
        ownerName = try container.decode(String.self, forKey: .ownerName)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(address, forKey: .address)
        try container.encode(coordinates.latitude, forKey: .lat)
        try container.encode(coordinates.longitude, forKey: .lng)
        try container.encode(facilityType, forKey: .facilityType)
        try container.encode(slots, forKey: .slots)
        try container.encode(defaultHourlyRate, forKey: .defaultHourlyRate)
        try container.encodeIfPresent(flatDayRate, forKey: .flatDayRate)
        try container.encode(hasCCTV, forKey: .hasCCTV)
        try container.encode(hasEVCharging, forKey: .hasEVCharging)
        try container.encode(hasValetService, forKey: .hasValetService)
        try container.encode(hasCarWash, forKey: .hasCarWash)
        try container.encode(is24Hours, forKey: .is24Hours)
        try container.encode(rating, forKey: .rating)
        try container.encode(reviewCount, forKey: .reviewCount)
        try container.encode(ownerID, forKey: .ownerID)
        try container.encode(ownerName, forKey: .ownerName)
    }
}

// MARK: - Commercial Facility Type

enum CommercialFacilityType: String, CaseIterable, Codable {
    case mall = "Mall"
    case office = "Office"
    case apartment = "Apartment"
    case hospital = "Hospital"
    case airport = "Airport"
    case stadium = "Stadium"
    
    var icon: String {
        switch self {
        case .mall: return "building.2.fill"
        case .office: return "building.fill"
        case .apartment: return "building.columns.fill"
        case .hospital: return "cross.fill"
        case .airport: return "airplane"
        case .stadium: return "sportscourt.fill"
        }
    }
    
    var color: Color {
        switch self {
        case .mall: return .blue
        case .office: return .purple
        case .apartment: return .orange
        case .hospital: return .red
        case .airport: return .cyan
        case .stadium: return .green
        }
    }
}

// MARK: - Commercial Parking Slot

/// Individual parking slot within a commercial facility
struct CommercialParkingSlot: Identifiable, Hashable, Codable {
    let id: UUID
    var slotNumber: String // e.g., "A-01", "B-12", "EV-03"
    var slotType: CommercialSlotType
    var floor: Int // 0 = Ground, 1 = First, -1 = Basement 1
    
    // Status
    var isOccupied: Bool
    var isDisabled: Bool // Maintenance, reserved, etc.
    var currentBookingID: UUID?
    var bookingEndTime: Date? // For countdown timer
    
    // Pricing override (nil = use facility default)
    var hourlyRateOverride: Double?
    
    // Computed: Time remaining if occupied
    var timeRemaining: TimeInterval? {
        guard let endTime = bookingEndTime, isOccupied else { return nil }
        let remaining = endTime.timeIntervalSinceNow
        return remaining > 0 ? remaining : nil
    }
    
    var formattedTimeRemaining: String? {
        guard let remaining = timeRemaining else { return nil }
        let hours = Int(remaining) / 3600
        let minutes = (Int(remaining) % 3600) / 60
        if hours > 0 {
            return "Free in \(hours)h \(minutes)m"
        } else {
            return "Free in \(minutes)m"
        }
    }
}

// MARK: - Commercial Slot Type

enum CommercialSlotType: String, CaseIterable, Codable {
    case regular = "Regular"
    case compact = "Compact"
    case large = "Large/SUV"
    case evCharging = "EV Charging"
    case accessible = "Accessible"
    case valet = "Valet"
    case reserved = "Reserved"
    
    var icon: String {
        switch self {
        case .regular: return "car.fill"
        case .compact: return "car.side.fill"
        case .large: return "truck.pickup.side.fill"
        case .evCharging: return "bolt.car.fill"
        case .accessible: return "figure.roll"
        case .valet: return "person.fill.badge.plus"
        case .reserved: return "lock.fill"
        }
    }
    
    var color: Color {
        switch self {
        case .regular: return .blue
        case .compact: return .teal
        case .large: return .orange
        case .evCharging: return .green
        case .accessible: return .purple
        case .valet: return .pink
        case .reserved: return .gray
        }
    }
    
    var priceMultiplier: Double {
        switch self {
        case .regular: return 1.0
        case .compact: return 0.9
        case .large: return 1.3
        case .evCharging: return 1.5
        case .accessible: return 1.0
        case .valet: return 2.0
        case .reserved: return 1.0
        }
    }
}

// MARK: - Commercial Booking

/// Booking record for commercial parking - ALWAYS AUTO-APPROVED
struct CommercialBooking: Identifiable, Hashable, Codable {
    let id: UUID
    let facilityID: UUID
    let slotID: UUID
    let driverID: UUID

    // Timing
    let bookingTime: Date // When booking was made
    let scheduledStartTime: Date
    let scheduledEndTime: Date
    var actualStartTime: Date?
    var actualEndTime: Date?

    // Pricing
    let hourlyRate: Double
    let estimatedDuration: Double // Hours
    let estimatedCost: Double
    var actualCost: Double?

    // Vehicle
    var vehicleNumber: String?
    var vehicleType: String?

    // Status
    var status: CommercialBookingStatus

    // QR/Access
    let accessCode: String // 6-digit code
    var qrCodeData: String { "PARKEZY-COM:\(id.uuidString):\(slotID.uuidString)" }

    // Computed
    var isActive: Bool { status == .active }
    var isCompleted: Bool { status == .completed }

    // MARK: - Codable (maps to the 'commercial_bookings' table)

    enum CodingKeys: String, CodingKey {
        case id
        case facilityID = "facility_id"
        case slotID = "slot_id"
        case driverID = "driver_id"
        case bookingTime = "booking_time"
        case scheduledStartTime = "scheduled_start_time"
        case scheduledEndTime = "scheduled_end_time"
        case actualStartTime = "actual_start_time"
        case actualEndTime = "actual_end_time"
        case hourlyRate = "hourly_rate"
        case estimatedDuration = "estimated_duration"
        case estimatedCost = "estimated_cost"
        case actualCost = "actual_cost"
        case vehicleNumber = "vehicle_number"
        case vehicleType = "vehicle_type"
        case status
        case accessCode = "access_code"
    }
}

// MARK: - Commercial Booking Status

enum CommercialBookingStatus: String, CaseIterable, Codable {
    case pending = "Pending"      // Scheduled but not started
    case active = "Active"        // Currently parked
    case completed = "Completed"  // Finished and paid
    case cancelled = "Cancelled"
    case noShow = "No Show"
    
    var color: Color {
        switch self {
        case .pending: return .orange
        case .active: return .green
        case .completed: return .blue
        case .cancelled: return .red
        case .noShow: return .gray
        }
    }
}
