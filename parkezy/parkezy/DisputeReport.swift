//
//  DisputeReport.swift
//  ParkEzy
//
//  Model representing a dispute/issue report
//

import Foundation

struct DisputeReport: Identifiable, Codable {
    let id: UUID
    let bookingID: UUID
    let reason: String
    let description: String
    let photoURLs: [String]
    var status: DisputeStatus
    let createdAt: Date
    var resolvedAt: Date?
    var resolution: String?
}

// MARK: - Dispute Status

enum DisputeStatus: String, Codable {
    case pending = "Pending"
    case underReview = "Under Review"
    case resolved = "Resolved"
    case rejected = "Rejected"
}
