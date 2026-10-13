//
//  AppUser.swift
//  ParkEzy
//
//  Unified User model for Supabase (profiles table)
//

import Foundation

/// User model representing a Supabase profile
struct AppUser: Identifiable, Codable {
    let id: String  // Supabase Auth UID
    var email: String
    var name: String
    var phoneNumber: String
    var profileImageURL: String?
    var createdAt: Date
    
    // Capabilities - what this user can do
    var capabilities: UserCapabilities
    
    // User statistics
    var stats: UserStats
    
    // MARK: - Convenience Properties
    
    /// Can this user act as a driver?
    var canDrive: Bool { capabilities.canDrive }
    
    /// Can this user host private parking?
    var canHostPrivate: Bool { capabilities.canHostPrivate }
    
    /// Can this user host commercial parking?
    var canHostCommercial: Bool { capabilities.canHostCommercial }
    
    /// Does this user have any hosting capability?
    var isHost: Bool { canHostPrivate || canHostCommercial }
    
    enum CodingKeys: String, CodingKey {
        case id
        case email
        case name
        case phoneNumber = "phone_number"
        case profileImageURL = "profile_image_url"
        case createdAt = "created_at"
        case capabilities
        case stats
    }
}

/// Defines what a user is allowed to do in the app
struct UserCapabilities: Codable {
    var canDrive: Bool
    var canHostPrivate: Bool
    var canHostCommercial: Bool
}

/// Statistics for a user
struct UserStats: Codable {
    var totalBookingsAsDriver: Int
    var hostRating: Double?
    var totalEarnings: Double?
}
