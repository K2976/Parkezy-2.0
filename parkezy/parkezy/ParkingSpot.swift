//
//  ParkingSpot.swift
//  ParkEzy
//
//  Model representing a parking location
//

import Foundation
import CoreLocation

struct ParkingSpot: Identifiable, Hashable, Codable {
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

    // Distance (calculated dynamically, never persisted)
    var distance: Double = 0

    // MARK: - Hashable Conformance

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: ParkingSpot, rhs: ParkingSpot) -> Bool {
        lhs.id == rhs.id
    }

    // MARK: - Codable (maps to the 'parking_spots' table; lat/lng columns <-> coordinates)

    private enum CodingKeys: String, CodingKey {
        case id, address, type
        case lat, lng
        case pricePerHour = "price_per_hour"
        case hasCCTV = "has_cctv"
        case isCovered = "is_covered"
        case hasEVCharging = "has_ev_charging"
        case isAccessible = "is_accessible"
        case is24Hours = "is_24_hours"
        case hasInsurance = "has_insurance"
        case isOccupied = "is_occupied"
        case rating
        case reviewCount = "review_count"
        case accessPIN = "access_pin"
    }

    init(id: UUID, address: String, coordinates: CLLocationCoordinate2D, type: SpotType, pricePerHour: Double, hasCCTV: Bool, isCovered: Bool, hasEVCharging: Bool, isAccessible: Bool, is24Hours: Bool, hasInsurance: Bool, isOccupied: Bool, rating: Double, reviewCount: Int, accessPIN: String? = nil, distance: Double = 0) {
        self.id = id
        self.address = address
        self.coordinates = coordinates
        self.type = type
        self.pricePerHour = pricePerHour
        self.hasCCTV = hasCCTV
        self.isCovered = isCovered
        self.hasEVCharging = hasEVCharging
        self.isAccessible = isAccessible
        self.is24Hours = is24Hours
        self.hasInsurance = hasInsurance
        self.isOccupied = isOccupied
        self.rating = rating
        self.reviewCount = reviewCount
        self.accessPIN = accessPIN
        self.distance = distance
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        address = try container.decode(String.self, forKey: .address)
        let lat = try container.decode(Double.self, forKey: .lat)
        let lng = try container.decode(Double.self, forKey: .lng)
        coordinates = CLLocationCoordinate2D(latitude: lat, longitude: lng)
        type = try container.decode(SpotType.self, forKey: .type)
        pricePerHour = try container.decode(Double.self, forKey: .pricePerHour)
        hasCCTV = try container.decode(Bool.self, forKey: .hasCCTV)
        isCovered = try container.decode(Bool.self, forKey: .isCovered)
        hasEVCharging = try container.decode(Bool.self, forKey: .hasEVCharging)
        isAccessible = try container.decode(Bool.self, forKey: .isAccessible)
        is24Hours = try container.decode(Bool.self, forKey: .is24Hours)
        hasInsurance = try container.decode(Bool.self, forKey: .hasInsurance)
        isOccupied = try container.decode(Bool.self, forKey: .isOccupied)
        rating = try container.decode(Double.self, forKey: .rating)
        reviewCount = try container.decode(Int.self, forKey: .reviewCount)
        accessPIN = try container.decodeIfPresent(String.self, forKey: .accessPIN)
        distance = 0
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(address, forKey: .address)
        try container.encode(coordinates.latitude, forKey: .lat)
        try container.encode(coordinates.longitude, forKey: .lng)
        try container.encode(type, forKey: .type)
        try container.encode(pricePerHour, forKey: .pricePerHour)
        try container.encode(hasCCTV, forKey: .hasCCTV)
        try container.encode(isCovered, forKey: .isCovered)
        try container.encode(hasEVCharging, forKey: .hasEVCharging)
        try container.encode(isAccessible, forKey: .isAccessible)
        try container.encode(is24Hours, forKey: .is24Hours)
        try container.encode(hasInsurance, forKey: .hasInsurance)
        try container.encode(isOccupied, forKey: .isOccupied)
        try container.encode(rating, forKey: .rating)
        try container.encode(reviewCount, forKey: .reviewCount)
        try container.encodeIfPresent(accessPIN, forKey: .accessPIN)
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
