//
//  BookingSession.swift
//  ParkEzy
//
//  Model representing a parking booking session
//

import Foundation

struct BookingSession: Identifiable, Codable, Hashable {
    let id: UUID
    let spotID: UUID
    let userID: UUID
    
            // Timing
    let bookingTime: Date
    let scheduledStartTime: Date
    var actualStartTime: Date?
    var scheduledEndTime: Date
    var actualEndTime: Date?
    
    // Duration & Cost
    var duration: Double // in hours
    var totalCost: Double
    var overstayFee: Double?
    
    // Status
    var status: BookingStatus
    
    // Access
    var accessCode: String?
    
    // MARK: - Computed Properties
    
    var isActive: Bool {
        status == .active && actualEndTime == nil
    }
    
    var hasStarted: Bool {
        actualStartTime != nil
    }
    
    var hasEnded: Bool {
        actualEndTime != nil
    }
    
    var isOverstaying: Bool {
        guard isActive, let startTime = actualStartTime else { return false }
        return Date() > scheduledEndTime
    }
    
    // MARK: - Hashable
    
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
    
    static func == (lhs: BookingSession, rhs: BookingSession) -> Bool {
        lhs.id == rhs.id
    }

    // MARK: - Codable (maps to the 'bookings' table; spotID is stored as spot_id
    // regardless of whether it points at a private_listings or commercial_facilities row)

    enum CodingKeys: String, CodingKey {
        case id
        case spotID = "spot_id"
        case userID = "user_id"
        case bookingTime = "booking_time"
        case scheduledStartTime = "scheduled_start_time"
        case actualStartTime = "actual_start_time"
        case scheduledEndTime = "scheduled_end_time"
        case actualEndTime = "actual_end_time"
        case duration
        case totalCost = "total_cost"
        case overstayFee = "overstay_fee"
        case status
        case accessCode = "access_code"
    }

    // MARK: - Mock Data
    
    static var mockSession: BookingSession {
        let now = Date()
        let startTime = Calendar.current.date(byAdding: .hour, value: -1, to: now) ?? now
        let endTime = Calendar.current.date(byAdding: .hour, value: 1, to: now) ?? now
        
        return BookingSession(
            id: UUID(),
            spotID: UUID(),
            userID: UUID(),
            bookingTime: startTime,
            scheduledStartTime: startTime,
            actualStartTime: startTime,
            scheduledEndTime: endTime,
            actualEndTime: nil,
            duration: 2.0,
            totalCost: 118.0,
            overstayFee: nil,
            status: .active,
            accessCode: "428915"
        )
    }
}

// MARK: - Booking Status

enum BookingStatus: String, Codable {
    case pending = "Pending"
    case confirmed = "Confirmed"
    case active = "Active"
    case completed = "Completed"
    case cancelled = "Cancelled"
    case disputed = "Disputed"
}
