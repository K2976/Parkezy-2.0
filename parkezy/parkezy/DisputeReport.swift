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
    let reporterID: UUID
    let reason: String
    let description: String
    let photoURLs: [String]
    var status: DisputeStatus
    let createdAt: Date
    var resolvedAt: Date? = nil
    var resolution: String? = nil

    // MARK: - Codable (maps to the 'disputes' table)

    enum CodingKeys: String, CodingKey {
        case id
        case bookingID = "booking_id"
        case reporterID = "reporter_id"
        case reason, description
        case photoURLs = "photo_urls"
        case status
        case createdAt = "created_at"
        case resolvedAt = "resolved_at"
        case resolution = "resolution_notes"
    }
}

// MARK: - Dispute Status

enum DisputeStatus: String, Codable {
    case pending = "Pending"
    case underReview = "Under Review"
    case resolved = "Resolved"
    case rejected = "Rejected"
}
