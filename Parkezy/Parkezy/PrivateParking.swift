//
//  PrivateParking.swift
//  ParkEzy
//
//  Models for Private Parking (Home Owners)
//  SEPARATE from Commercial Parking - DO NOT MERGE
//

import Foundation
import CoreLocation
import SwiftUI

// MARK: - Private Parking Listing

/// Represents a private parking listing (Home owner's driveway/garage)
/// One listing per location, can have multiple slots
/// Owner can have multiple listings at different locations
struct PrivateParkingListing: Identifiable, Hashable {
    let id: UUID
    var backendID: Int? = nil // ID from Django backend
    var ownerID: UUID
    var ownerName: String
    
    // Location
    var title: String // e.g., "Spacious Driveway in GK-1"
    var address: String
    var coordinates: CLLocationCoordinate2D
    var listingDescription: String
    
    // Slots
    var slots: [PrivateParkingSlot]
    var totalSlots: Int { slots.count }
    var availableSlots: Int { slots.filter { !$0.isOccupied && !$0.isDisabled }.count }
    
    // Pricing (owner adjustable, with defaults)
    var hourlyRate: Double // Default ₹40
    var dailyRate: Double // Default ₹300
    var monthlyRate: Double // Default ₹3000
    var flatFullBookingRate: Double? // Optional flat rate for full listing
    
    // Booking settings
    var autoAcceptBookings: Bool // Default: false (manual approval)
    var instantBookingDiscount: Double? // Optional discount for instant bookings
    
    // Amenities
    var hasCCTV: Bool
    var isCovered: Bool
    var hasEVCharging: Bool
    var hasSecurityGuard: Bool
    var hasWaterAccess: Bool // For car wash
    
    // Availability
    var is24Hours: Bool
    var availableFrom: Date?
    var availableTo: Date?
    var availableDays: [Int] // 1-7 for Sun-Sat
    
    // Rating
    var rating: Double
    var reviewCount: Int
    
    // Images
    var imageURLs: [String]
    
    // MARK: - Captured Media (for new listings)
    
    /// Photo data captured during listing creation
    var capturedPhotoData: [Data]?
    
    /// Video URL captured during listing creation
    var capturedVideoURL: URL?
    
    // MARK: - Booking Duration Limit
    
    /// Maximum booking duration allowed
    var maxBookingDuration: BookingDurationLimit
    
    // MARK: - Pricing Intelligence
    
    /// Suggested price based on nearby listings
    var suggestedHourlyRate: Double?
    
    var priceCompetitiveness: PriceCompetitiveness {
        guard let suggested = suggestedHourlyRate, suggested > 0 else {
            return .unknown
        }
        let ratio = hourlyRate / suggested
        if ratio <= 0.9 {
            return .competitive
        } else if ratio <= 1.1 {
            return .fair
        } else if ratio <= 1.3 {
            return .high
        } else {
            return .tooExpensive
        }
    }
    
    // MARK: - Hashable
    
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
    
    static func == (lhs: PrivateParkingListing, rhs: PrivateParkingListing) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - Booking Duration Limit

enum BookingDurationLimit: String, CaseIterable, Codable {
    case oneHour = "1 Hour"
    case twoHours = "2 Hours"
    case fourHours = "4 Hours"
    case eightHours = "8 Hours"
    case oneDay = "24 Hours"
    case unlimited = "Unlimited"
    
    var hours: Int? {
        switch self {
        case .oneHour: return 1
        case .twoHours: return 2
        case .fourHours: return 4
        case .eightHours: return 8
        case .oneDay: return 24
        case .unlimited: return nil
        }
    }
}


// MARK: - Price Competitiveness

enum PriceCompetitiveness: String {
    case competitive = "Competitive"
    case fair = "Fair"
    case high = "High"
    case tooExpensive = "Too Expensive"
    case unknown = "Unknown"
    
    var color: Color {
        switch self {
        case .competitive: return .green
        case .fair: return .blue
        case .high: return .orange
        case .tooExpensive: return .red
        case .unknown: return .gray
        }
    }
    
    var icon: String {
        switch self {
        case .competitive: return "checkmark.circle.fill"
        case .fair: return "equal.circle.fill"
        case .high: return "exclamationmark.triangle.fill"
        case .tooExpensive: return "xmark.circle.fill"
        case .unknown: return "questionmark.circle.fill"
        }
    }
}

// MARK: - Private Parking Slot

/// Individual parking slot within a private listing
struct PrivateParkingSlot: Identifiable, Hashable {
    let id: UUID
    var slotNumber: Int // 1, 2, 3, etc.
    var slotLabel: String? // Optional label like "Garage", "Driveway Left"
    
    // Capacity
    var vehicleSize: PrivateSlotSize
    var canFitSUV: Bool
    var canFitBike: Bool // Motorcycle
    
    // Status
    var isOccupied: Bool
    var isDisabled: Bool
    var currentBookingID: UUID?
    var bookingEndTime: Date?
    
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
    
    var displayName: String {
        slotLabel ?? "Slot \(slotNumber)"
    }
}

// MARK: - Private Slot Size

enum PrivateSlotSize: String, CaseIterable, Codable {
    case compact = "Compact"
    case standard = "Standard"
    case large = "Large"
    
    var icon: String {
        switch self {
        case .compact: return "car.side.fill"
        case .standard: return "car.fill"
        case .large: return "truck.pickup.side.fill"
        }
    }
}

// MARK: - Private Booking

/// Booking for private parking - can require manual approval
struct PrivateBooking: Identifiable, Hashable {
    let id: UUID
    let listingID: UUID
    let slotID: UUID
    let driverID: UUID
    let hostID: UUID
    
    // Driver info
    var driverName: String
    var driverPhone: String?
    var vehicleNumber: String?
    
    // Timing
    let requestTime: Date // When booking was requested
    let scheduledStartTime: Date
    let scheduledEndTime: Date
    var actualStartTime: Date?
    var actualEndTime: Date?
    
    // Duration type
    var durationType: PrivateBookingDuration
    
    // Pricing
    let agreedRate: Double // Rate at time of booking
    let estimatedCost: Double
    var actualCost: Double?
    var hostEarnings: Double? // After platform fee
    
    // Status
    var status: PrivateBookingStatus
    var approvalTime: Date? // When host approved
    var rejectionReason: String?
    
    // Access
    var accessPIN: String? // 6-digit PIN for entry
    var qrCodeData: String { "PARKEZY-PVT:\(id.uuidString):\(slotID.uuidString)" }
    
    // Communication
    var driverMessage: String?
    var hostMessage: String?
    
    // Computed
    var isPending: Bool { status == .pendingApproval }
    var isApproved: Bool { status == .approved || status == .active }
    var isActive: Bool { status == .active }
}

// MARK: - Private Booking Duration Type

enum PrivateBookingDuration: String, CaseIterable, Codable {
    case hourly = "Hourly"
    case daily = "Daily"
    case monthly = "Monthly"
    
    var icon: String {
        switch self {
        case .hourly:
            return "clock.fill"
        case .daily:
            return "calendar.badge.clock"
        case .monthly:
            return "calendar"
        }
    }
}

// MARK: - Private Booking Status

enum PrivateBookingStatus: String, CaseIterable, Codable {
    case pendingApproval = "Pending Approval"
    case approved = "Approved"
    case rejected = "Rejected"
    case active = "Active"
    case completed = "Completed"
    case cancelled = "Cancelled"
    case expired = "Expired" // Request expired without response
    
    var color: Color {
        switch self {
        case .pendingApproval: return .orange
        case .approved: return .blue
        case .rejected: return .red
        case .active: return .green
        case .completed: return .purple
        case .cancelled: return .gray
        case .expired: return .secondary
        }
    }
    
    var icon: String {
        switch self {
        case .pendingApproval: return "hourglass"
        case .approved: return "checkmark.circle.fill"
        case .rejected: return "xmark.circle.fill"
        case .active: return "car.fill"
        case .completed: return "flag.checkered"
        case .cancelled: return "xmark"
        case .expired: return "clock.badge.xmark.fill"
        }
    }
}
