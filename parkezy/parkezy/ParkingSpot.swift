//
//  ParkingSpot.swift
//  ParkEzy
//
//  Model representing a parking location
//

import Foundation
import CoreLocation

struct ParkingSpot: Identifiable, Hashable {
    let id: UUID
    let address: String
    let coordinates: CLLocationCoordinate2D
    let type: SpotType
    let pricePerHour: Double
    
    // Features
    let hasCCTV: Bool
    let isCovered: Bool
    let hasEVCharging: Bool
    let isAccessible: Bool
    let is24Hours: Bool
    let hasInsurance: Bool
    
    // Status
    var isOccupied: Bool
    var rating: Double
    var reviewCount: Int
    
    // Access
    var accessPIN: String? // For private spots
    
    // Distance (calculated dynamically)
    var distance: Double = 0
    
    // MARK: - Hashable Conformance
    
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
    
    static func == (lhs: ParkingSpot, rhs: ParkingSpot) -> Bool {
        lhs.id == rhs.id
    }
    
    // MARK: - Mock Data
    
    static var mockSpot: ParkingSpot {
        ParkingSpot(
            id: UUID(),
            address: "Greater Kailash I, New Delhi",
            coordinates: CLLocationCoordinate2D(latitude: 28.5494, longitude: 77.2344),
            type: .privateDriveway,
            pricePerHour: 50,
            hasCCTV: true,
            isCovered: true,
            hasEVCharging: false,
            isAccessible: true,
            is24Hours: true,
            hasInsurance: true,
            isOccupied: false,
            rating: 4.5,
            reviewCount: 128,
            accessPIN: "428915"
        )
    }
}

// MARK: - Spot Type

enum SpotType: String, Codable {
    case mall = "Mall Parking"
    case privateDriveway = "Private Driveway"
}

// MARK: - CLLocationCoordinate2D Extension

extension CLLocationCoordinate2D: Hashable {
    public func hash(into hasher: inout Hasher) {
        hasher.combine(latitude)
        hasher.combine(longitude)
    }
    
    public static func == (lhs: CLLocationCoordinate2D, rhs: CLLocationCoordinate2D) -> Bool {
        lhs.latitude == rhs.latitude && lhs.longitude == rhs.longitude
    }
}
