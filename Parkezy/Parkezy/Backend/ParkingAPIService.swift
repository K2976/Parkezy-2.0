//
//  ParkingAPIService.swift
//  ParkEzy
//
//  Network service for Django parking API.
//  Handles create/read operations for parking listings.
//

import Foundation
import CoreLocation
import FirebaseAuth

/// Service for interacting with Django parking APIs
final class ParkingAPIService {
    
    // MARK: - Singleton
    
    static let shared = ParkingAPIService()
    
    // MARK: - Properties
    
    private let baseURL = "http://127.0.0.1:8000/api"
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    
    // MARK: - Initialization
    
    private init() {
        decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        
        encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
    }
    
    // MARK: - Private Parking Listings
    
    /// Create a new private parking listing
    func createPrivateListing(_ request: CreatePrivateListingRequest) async throws -> PrivateParkingResponse {
        let url = URL(string: "\(baseURL)/parking/private-listings/")!
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Add auth token if available
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        urlRequest.httpBody = try encoder.encode(request)
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw ParkingAPIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 201 else {
            throw ParkingAPIError.httpError(statusCode: httpResponse.statusCode)
        }
        
        return try decoder.decode(PrivateParkingResponse.self, from: data)
    }
    
    /// Get nearby private parking listings
    func getNearbyPrivateListings(latitude: Double, longitude: Double, radiusKm: Double = 10) async throws -> [PrivateParkingResponse] {
        var components = URLComponents(string: "\(baseURL)/parking/private-listings/nearby/")!
        components.queryItems = [
            URLQueryItem(name: "lat", value: "\(latitude)"),
            URLQueryItem(name: "lon", value: "\(longitude)"),
            URLQueryItem(name: "radius_km", value: "\(radiusKm)")
        ]
        
        guard let url = components.url else {
            throw ParkingAPIError.invalidURL
        }
        
        var urlRequest = URLRequest(url: url)
        
        // Add auth token if available
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ParkingAPIError.fetchFailed
        }
        
        return try decoder.decode([PrivateParkingResponse].self, from: data)
    }
    
    /// Get all private parking listings
    func getAllPrivateListings() async throws -> [PrivateParkingResponse] {
        let url = URL(string: "\(baseURL)/parking/private-listings/")!
        var urlRequest = URLRequest(url: url)
        
        // Add auth token if available
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ParkingAPIError.fetchFailed
        }
        
        return try decoder.decode([PrivateParkingResponse].self, from: data)
    }
    
    /// Get authenticated user's private parking listings
    func getMyPrivateListings() async throws -> [PrivateParkingResponse] {
        var components = URLComponents(string: "\(baseURL)/parking/private-listings/")!
        components.queryItems = [
            URLQueryItem(name: "mine", value: "true")
        ]
        
        guard let url = components.url else {
            throw ParkingAPIError.invalidURL
        }
        
        var urlRequest = URLRequest(url: url)
        
        // Add auth token (REQUIRED)
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        } else {
             return []
        }
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse else {
             throw ParkingAPIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
             throw ParkingAPIError.httpError(statusCode: httpResponse.statusCode)
        }
        
        return try decoder.decode([PrivateParkingResponse].self, from: data)
    }
    
    // MARK: - User Profile
    
    /// Get current user profile
    func getUserProfile() async throws -> UserProfile {
        let url = URL(string: "\(baseURL)/users/me/")!
        var urlRequest = URLRequest(url: url)
        
        // Add auth token (REQUIRED)
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        } else {
             throw ParkingAPIError.invalidResponse // Auth required
        }
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ParkingAPIError.fetchFailed
        }
        
        return try decoder.decode(UserProfile.self, from: data)
    }
    
    // MARK: - Update Listing
    
    /// Update a private parking listing
    func updatePrivateListing(id: Int, request: UpdatePrivateListingRequest) async throws -> PrivateParkingResponse {
        let url = URL(string: "\(baseURL)/parking/private-listings/\(id)/")!
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "PUT"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Add auth token
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        urlRequest.httpBody = try encoder.encode(request)
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw ParkingAPIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw ParkingAPIError.httpError(statusCode: httpResponse.statusCode)
        }
        
        return try decoder.decode(PrivateParkingResponse.self, from: data)
    }

    func createCommercialFacility(_ request: CreateCommercialFacilityRequest) async throws -> CommercialParkingResponse {
        let url = URL(string: "\(baseURL)/parking/commercial-facilities/")!
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Add auth token if available
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        urlRequest.httpBody = try encoder.encode(request)
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw ParkingAPIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 201 else {
            throw ParkingAPIError.httpError(statusCode: httpResponse.statusCode)
        }
        
        return try decoder.decode(CommercialParkingResponse.self, from: data)
    }
    
    /// Get nearby commercial facilities
    func getNearbyCommercialFacilities(latitude: Double, longitude: Double, radiusKm: Double = 10) async throws -> [CommercialParkingResponse] {
        var components = URLComponents(string: "\(baseURL)/parking/commercial-facilities/nearby/")!
        components.queryItems = [
            URLQueryItem(name: "lat", value: "\(latitude)"),
            URLQueryItem(name: "lon", value: "\(longitude)"),
            URLQueryItem(name: "radius_km", value: "\(radiusKm)")
        ]
        
        guard let url = components.url else {
            throw ParkingAPIError.invalidURL
        }
        
        var urlRequest = URLRequest(url: url)
        
        // Add auth token if available
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ParkingAPIError.fetchFailed
        }
        
        return try decoder.decode([CommercialParkingResponse].self, from: data)
    }
    
    /// Get all commercial facilities
    func getAllCommercialFacilities() async throws -> [CommercialParkingResponse] {
        let url = URL(string: "\(baseURL)/parking/commercial-facilities/")!
        var urlRequest = URLRequest(url: url)
        
        // Add auth token if available
        if let token = try? await getAuthToken() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ParkingAPIError.fetchFailed
        }
        
        return try decoder.decode([CommercialParkingResponse].self, from: data)
    }
    
    // MARK: - Authentication
    
    /// Get Firebase auth token for Django backend
    private func getAuthToken() async throws -> String? {
        guard let currentUser = Auth.auth().currentUser else {
            return nil
        }
        return try await currentUser.getIDToken()
    }
}

// MARK: - Request Models

struct CreatePrivateListingRequest: Codable {
    let title: String
    let address: String
    let latitude: Double
    let longitude: Double
    let description: String?
    let hourlyRate: Double
    let dailyRate: Double?
    let monthlyRate: Double?
    let availableSlots: Int
    let isCovered: Bool
    let hasCctv: Bool
    let hasEvCharging: Bool
    let is24Hours: Bool
    let availableStartTime: String?
    let availableEndTime: String?
    let availableDays: [Int]?
}

struct CreateCommercialFacilityRequest: Codable {
    let name: String
    let address: String
    let latitude: Double
    let longitude: Double
    let description: String?
    let facilityType: String
    let defaultHourlyRate: Double
    let totalSlots: Int
    let isCovered: Bool
    let hasCctv: Bool
    let hasEvCharging: Bool
    let is24Hours: Bool
}

// MARK: - Response Models

struct PrivateParkingResponse: Codable {
    let id: Int
    let title: String
    let address: String
    let latitude: Double
    let longitude: Double
    let description: String?
    let hourlyRate: Double
    let dailyRate: Double?
    let monthlyRate: Double?
    let availableSlots: Int
    let isCovered: Bool
    let hasCctv: Bool
    let hasEvCharging: Bool
    let is24Hours: Bool
    let rating: Double?
    let reviewCount: Int?
    let ownerName: String?
    let distance: Double?
    let createdAt: Date?
}

struct CommercialParkingResponse: Codable {
    let id: Int
    let name: String
    let address: String
    let latitude: Double
    let longitude: Double
    let description: String?
    let facilityType: String
    let defaultHourlyRate: Double
    let totalSlots: Int
    let availableSlots: Int
    let isCovered: Bool
    let hasCctv: Bool
    let hasEvCharging: Bool
    let is24Hours: Bool
    let rating: Double?
    let reviewCount: Int?
    let ownerName: String?
    let distance: Double?
}

// MARK: - Errors

enum ParkingAPIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(statusCode: Int)
    case createFailed
    case fetchFailed
    case networkError(Error)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid API URL"
        case .invalidResponse:
            return "Invalid server response"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .createFailed:
            return "Failed to create parking listing"
        case .fetchFailed:
            return "Failed to fetch parking listings"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}

// MARK: - Extensions

// MARK: - User Models

struct UserProfile: Codable {
    let id: Int
    let email: String
    let name: String
    let phoneNumber: String?
    let isHost: Bool
    let profileImageUrl: String?
}

// MARK: - Request Models

struct UpdatePrivateListingRequest: Codable {
    let title: String
    let address: String
    let latitude: Double
    let longitude: Double
    let description: String?
    let hourlyRate: Double
    let dailyRate: Double?
    let monthlyRate: Double?
    let availableSlots: Int
    let isCovered: Bool
    let hasCctv: Bool
    let hasEvCharging: Bool
    let is24Hours: Bool
    let availableStartTime: String?
    let availableEndTime: String?
    let availableDays: [Int]?
    let autoAcceptBookings: Bool?
}

extension PrivateParkingResponse {
    /// Convert API response to app model
    func toAppModel() -> PrivateParkingListing {
        PrivateParkingListing(
            id: UUID(),
            backendID: id,
            ownerID: UUID(),
            ownerName: ownerName ?? "Unknown",
            title: title,
            address: address,
            coordinates: CLLocationCoordinate2D(latitude: latitude, longitude: longitude),
            listingDescription: description ?? "",
            slots: [],
            hourlyRate: hourlyRate,
            dailyRate: dailyRate ?? 0,
            monthlyRate: monthlyRate ?? 0,
            flatFullBookingRate: nil,
            autoAcceptBookings: false,
            instantBookingDiscount: nil,
            hasCCTV: hasCctv,
            isCovered: isCovered,
            hasEVCharging: hasEvCharging,
            hasSecurityGuard: false,
            hasWaterAccess: false,
            is24Hours: is24Hours,
            availableFrom: nil,
            availableTo: nil,
            availableDays: [1, 2, 3, 4, 5, 6, 7],
            rating: rating ?? 0,
            reviewCount: reviewCount ?? 0,
            imageURLs: [],
            capturedPhotoData: nil,
            capturedVideoURL: nil,
            maxBookingDuration: .unlimited,
            suggestedHourlyRate: nil
        )
    }
}

extension CommercialParkingResponse {
    /// Convert API response to app model
    func toAppModel() -> CommercialParkingFacility {
        let type: CommercialFacilityType = {
            switch facilityType.lowercased() {
            case "mall": return .mall
            case "airport": return .airport
            case "hospital": return .hospital
            case "office": return .office
            case "apartment": return .apartment
            case "stadium": return .stadium
            default: return .office // Default fallback
            }
        }()
        
        return CommercialParkingFacility(
            id: UUID(),
            name: name,
            address: address,
            coordinates: CLLocationCoordinate2D(latitude: latitude, longitude: longitude),
            facilityType: type,
            slots: [], // Slots would be loaded separately
            defaultHourlyRate: defaultHourlyRate,
            flatDayRate: nil,
            hasCCTV: hasCctv,
            hasEVCharging: hasEvCharging,
            hasValetService: false,
            hasCarWash: false,
            is24Hours: is24Hours,
            rating: rating ?? 0,
            reviewCount: reviewCount ?? 0,
            ownerID: UUID(),
            ownerName: ownerName ?? "Unknown"
        )
    }
}
