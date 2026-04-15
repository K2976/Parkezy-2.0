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
    
    // MARK: - Mock Data
    
    static var mockSession: BookingSession {
        let now = Date()
        let startTime = Calendar.current.date(byAdding: .hour, value: -1, to: now)!
        let endTime = Calendar.current.date(byAdding: .hour, value: 1, to: now)!
        
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
