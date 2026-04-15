//
//  AppUser.swift
//  ParkEzy
//
//  User model for Firebase - renamed to avoid conflict with Swift's User type.
//  A single user can act as driver, private host, and commercial host.
//

import Foundation
import FirebaseFirestore

/// User model representing an authenticated user
struct AppUser: Identifiable, Codable {
    let id: String  // Firebase Auth UID
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
    
    // MARK: - Firestore Conversion
    
    /// Convert to Firestore data format
    func toFirestoreData() -> [String: Any] {
        return [
            "email": email,
            "name": name,
            "phoneNumber": phoneNumber,
            "profileImageURL": profileImageURL as Any,
            "capabilities": [
                "canDrive": capabilities.canDrive,
                "canHostPrivate": capabilities.canHostPrivate,
                "canHostCommercial": capabilities.canHostCommercial
            ],
            "stats": [
                "totalBookingsAsDriver": stats.totalBookingsAsDriver,
                "hostRating": stats.hostRating as Any,
                "totalEarnings": stats.totalEarnings
            ]
        ]
    }
}

/// What capabilities a user has - all independent, no role switching needed
struct UserCapabilities: Codable {
    var canDrive: Bool = true          // Everyone can be a driver
    var canHostPrivate: Bool = false   // Can list private parking spaces
    var canHostCommercial: Bool = false // Can manage commercial facilities
}

/// User statistics
struct UserStats: Codable {
    var totalBookingsAsDriver: Int = 0
    var hostRating: Double? = nil
    var totalEarnings: Double = 0
}

// MARK: - Preview/Test Helper

#if DEBUG
extension AppUser {
    /// Sample user for previews
    static var preview: AppUser {
        AppUser(
            id: "preview-user-id",
            email: "test@parkezy.com",
            name: "Test User",
            phoneNumber: "+91 98765 12345",
            profileImageURL: nil,
            createdAt: Date(),
            capabilities: UserCapabilities(canDrive: true, canHostPrivate: true, canHostCommercial: false),
            stats: UserStats(totalBookingsAsDriver: 5, hostRating: 4.5, totalEarnings: 2500)
        )
    }
}
#endif
