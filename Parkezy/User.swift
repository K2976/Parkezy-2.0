//
//  User.swift
//  ParkEzy
//
//  Model representing a user (Driver or Host)
//

import Foundation

struct User: Identifiable, Codable {
    let id: UUID
    var name: String
    var email: String
    var phoneNumber: String
    var profileImageURL: String?
    
    // Role
    var isHost: Bool
    
    // Stats
    var hostRating: Double?
    var totalBookings: Int
    
    // MARK: - Mock Data
    
    static var mockDriver: User {
        User(
            id: UUID(),
            name: "Kartik Sharma",
            email: "kartik@example.com",
            phoneNumber: "+91 98765 12345",
            profileImageURL: nil,
            isHost: false,
            hostRating: nil,
            totalBookings: 15
        )
    }
    
    static var mockHost: User {
        User(
            id: UUID(),
            name: "Rohit Sharma",
            email: "rohit@parkezy.com",
            phoneNumber: "+91 98765 43210",
            profileImageURL: nil,
            isHost: true,
            hostRating: 4.8,
            totalBookings: 456
        )
    }
}
