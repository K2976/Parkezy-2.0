//
//  PrivateListingRepository.swift
//  ParkEzy
//
//  Manages private parking listings in Firestore.
//  Handles CRUD, soft delete, and edit blocking when active bookings exist.
//

import Foundation
import FirebaseFirestore
import CoreLocation
import Combine

/// Repository for managing private parking listings
final class PrivateListingRepository: ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = PrivateListingRepository()
    
    // MARK: - Properties
    
    private let firebase = FirebaseManager.shared
    private var listingsListener: ListenerRegistration?
    
    // MARK: - Initialization
    
    private init() {}
    
    deinit {
        listingsListener?.remove()
    }
    
    // MARK: - Create
    
    /// Create a new private listing
    /// - Parameter listing: The listing data to create
    /// - Returns: The created listing ID
    func createListing(_ data: PrivateListingData) async throws -> String {
        guard let ownerID = firebase.currentUserID else {
            throw AuthError.notAuthenticated
        }
        
        let docRef = firebase.privateListingsCollection.document()
        let listingID = docRef.documentID
        
        // Build Firestore document
        var firestoreData = data.toFirestoreData()
        firestoreData["id"] = listingID
        firestoreData["ownerID"] = ownerID
        firestoreData["isActive"] = true
        firestoreData["isDeleted"] = false
        firestoreData["hasActiveBooking"] = false
        firestoreData["createdAt"] = FieldValue.serverTimestamp()
        
        try await docRef.setData(firestoreData)
        
        // Enable host capability if not already
        try await UserRepository.shared.enableCapability(.canHostPrivate, for: ownerID)
        
        return listingID
    }
    
    // MARK: - Read
    
    /// Fetch a single listing by ID
    func getListing(id: String) async throws -> PrivateParkingListing {
        let doc = try await firebase.privateListingDocument(id: id).getDocument()
        guard let data = doc.data() else {
            throw ListingError.notFound
        }
        return try parseListing(from: data, id: id)
    }
    
    /// Fetch all listings for an owner
    func getOwnerListings(ownerID: String) async throws -> [PrivateParkingListing] {
        let snapshot = try await firebase.privateListingsCollection
            .whereField("ownerID", isEqualTo: ownerID)
            .whereField("isDeleted", isEqualTo: false)
            .getDocuments()
        
        return try snapshot.documents.compactMap { doc in
            try parseListing(from: doc.data(), id: doc.documentID)
        }
    }
    
    /// Fetch nearby listings within radius
    /// Note: For proper geo queries, consider using GeoFirestore library
    func getNearbyListings(location: CLLocationCoordinate2D, radiusKm: Double = 10) async throws -> [PrivateParkingListing] {
        // Simple bounding box query (not accurate for large radii)
        let lat = location.latitude
        let lon = location.longitude
        let latDelta = radiusKm / 110.574 // km per degree latitude
        let lonDelta = radiusKm / (111.320 * cos(lat * .pi / 180)) // km per degree longitude
        
        let snapshot = try await firebase.privateListingsCollection
            .whereField("isActive", isEqualTo: true)
            .whereField("isDeleted", isEqualTo: false)
            .whereField("location.lat", isGreaterThan: lat - latDelta)
            .whereField("location.lat", isLessThan: lat + latDelta)
            .getDocuments()
        
        // Filter by longitude in memory (Firestore can't do range on two fields)
        return try snapshot.documents.compactMap { doc in
            let data = doc.data()
            guard let locData = data["location"] as? [String: Double],
                  let docLon = locData["lon"],
                  docLon > lon - lonDelta && docLon < lon + lonDelta else {
                return nil
            }
            return try parseListing(from: data, id: doc.documentID)
        }
    }
    
    // MARK: - Update
    
    /// Update a listing
    /// - Throws: If listing has an active booking
    func updateListing(id: String, data: PrivateListingData) async throws {
        // Check if listing has active booking
        let doc = try await firebase.privateListingDocument(id: id).getDocument()
        if let hasActiveBooking = doc.data()?["hasActiveBooking"] as? Bool, hasActiveBooking {
            throw ListingError.cannotEditWithActiveBooking
        }
        
        let updateData = data.toFirestoreData()
        try await firebase.privateListingDocument(id: id).updateData(updateData)
    }
    
    /// Update specific fields
    func updateListingFields(id: String, fields: [String: Any]) async throws {
        try await firebase.privateListingDocument(id: id).updateData(fields)
    }
    
    /// Toggle listing active status
    func toggleActive(id: String, isActive: Bool) async throws {
        try await firebase.privateListingDocument(id: id).updateData([
            "isActive": isActive
        ])
    }
    
    // MARK: - Delete (Soft)
    
    /// Soft delete a listing (sets isDeleted flag)
    func softDeleteListing(id: String) async throws {
        // Check for active bookings first
        let doc = try await firebase.privateListingDocument(id: id).getDocument()
        if let hasActiveBooking = doc.data()?["hasActiveBooking"] as? Bool, hasActiveBooking {
            throw ListingError.cannotDeleteWithActiveBooking
        }
        
        try await firebase.privateListingDocument(id: id).updateData([
            "isDeleted": true,
            "isActive": false
        ])
    }
    
    // MARK: - Slots
    
    /// Add a slot to a listing
    func addSlot(listingID: String, slot: PrivateSlotData) async throws -> String {
        let slotRef = firebase.privateListingDocument(id: listingID)
            .collection("slots").document()
        
        var slotData = slot.toFirestoreData()
        slotData["id"] = slotRef.documentID
        
        try await slotRef.setData(slotData)
        return slotRef.documentID
    }
    
    /// Get slots for a listing
    func getSlots(listingID: String) async throws -> [PrivateParkingSlot] {
        let snapshot = try await firebase.privateListingDocument(id: listingID)
            .collection("slots")
            .getDocuments()
        
        return snapshot.documents.compactMap { doc in
            parseSlot(from: doc.data(), id: doc.documentID)
        }
    }
    
    /// Update slot status
    func updateSlotStatus(listingID: String, slotID: String, isOccupied: Bool, bookingID: String?, endTime: Date?) async throws {
        try await firebase.privateListingDocument(id: listingID)
            .collection("slots").document(slotID)
            .updateData([
                "isOccupied": isOccupied,
                "currentBookingID": bookingID as Any,
                "bookingEndTime": endTime as Any
            ])
    }
    
    // MARK: - Real-time Listeners
    
    /// Listen to owner's listings in real-time
    func ownerListingsListener(ownerID: String) -> AnyPublisher<[PrivateParkingListing], Error> {
        let subject = PassthroughSubject<[PrivateParkingListing], Error>()
        
        listingsListener?.remove()
        listingsListener = firebase.privateListingsCollection
            .whereField("ownerID", isEqualTo: ownerID)
            .whereField("isDeleted", isEqualTo: false)
            .addSnapshotListener { [weak self] snapshot, error in
                if let error = error {
                    subject.send(completion: .failure(error))
                    return
                }
                
                guard let documents = snapshot?.documents else {
                    subject.send([])
                    return
                }
                
                let listings = documents.compactMap { doc -> PrivateParkingListing? in
                    try? self?.parseListing(from: doc.data(), id: doc.documentID)
                }
                subject.send(listings)
            }
        
        return subject.eraseToAnyPublisher()
    }
    
    // MARK: - Booking Flag
    
    /// Set the active booking flag on a listing
    func setActiveBookingFlag(listingID: String, hasActiveBooking: Bool) async throws {
        try await firebase.privateListingDocument(id: listingID).updateData([
            "hasActiveBooking": hasActiveBooking
        ])
    }
    
    // MARK: - Parsing
    
    /// Parse Firestore data to PrivateParkingListing
    private func parseListing(from data: [String: Any], id: String) throws -> PrivateParkingListing {
        guard let ownerID = data["ownerID"] as? String,
              let ownerName = data["ownerName"] as? String,
              let title = data["title"] as? String,
              let address = data["address"] as? String,
              let location = data["location"] as? [String: Double],
              let lat = location["lat"],
              let lon = location["lon"],
              let pricing = data["pricing"] as? [String: Double] else {
            throw ListingError.invalidData
        }
        
        let amenities = data["amenities"] as? [String: Bool] ?? [:]
        
        return PrivateParkingListing(
            id: UUID(uuidString: id) ?? UUID(),
            ownerID: UUID(uuidString: ownerID) ?? UUID(),
            ownerName: ownerName,
            title: title,
            address: address,
            coordinates: CLLocationCoordinate2D(latitude: lat, longitude: lon),
            listingDescription: data["description"] as? String ?? "",
            slots: [], // Slots loaded separately
            hourlyRate: pricing["hourlyRate"] ?? 40,
            dailyRate: pricing["dailyRate"] ?? 300,
            monthlyRate: pricing["monthlyRate"] ?? 3000,
            flatFullBookingRate: pricing["flatRate"],
            autoAcceptBookings: data["autoAcceptBookings"] as? Bool ?? false,
            instantBookingDiscount: data["instantBookingDiscount"] as? Double,
            hasCCTV: amenities["hasCCTV"] ?? false,
            isCovered: amenities["isCovered"] ?? false,
            hasEVCharging: amenities["hasEVCharging"] ?? false,
            hasSecurityGuard: amenities["hasSecurityGuard"] ?? false,
            hasWaterAccess: amenities["hasWaterAccess"] ?? false,
            is24Hours: data["is24Hours"] as? Bool ?? true,
            availableFrom: nil,
            availableTo: nil,
            availableDays: [1, 2, 3, 4, 5, 6, 7],
            rating: data["rating"] as? Double ?? 0,
            reviewCount: data["reviewCount"] as? Int ?? 0,
            imageURLs: data["imageURLs"] as? [String] ?? [],
            capturedPhotoData: nil,
            capturedVideoURL: nil,
            maxBookingDuration: parseMaxDuration(data["maxBookingDuration"]),
            suggestedHourlyRate: nil
        )
    }
    
    /// Parse max booking duration from Firestore data
    private func parseMaxDuration(_ value: Any?) -> BookingDurationLimit {
        if let rawValue = value as? String,
           let duration = BookingDurationLimit(rawValue: rawValue) {
            return duration
        }
        return .unlimited
    }
    
    /// Parse slot data
    private func parseSlot(from data: [String: Any], id: String) -> PrivateParkingSlot? {
        guard let slotNumber = data["slotNumber"] as? Int else { return nil }
        
        let sizeString = data["vehicleSize"] as? String ?? "standard"
        let size = PrivateSlotSize(rawValue: sizeString) ?? .standard
        
        return PrivateParkingSlot(
            id: UUID(uuidString: id) ?? UUID(),
            slotNumber: slotNumber,
            slotLabel: data["slotLabel"] as? String,
            vehicleSize: size,
            canFitSUV: data["canFitSUV"] as? Bool ?? false,
            canFitBike: data["canFitBike"] as? Bool ?? true,
            isOccupied: data["isOccupied"] as? Bool ?? false,
            isDisabled: data["isDisabled"] as? Bool ?? false,
            currentBookingID: (data["currentBookingID"] as? String).flatMap { UUID(uuidString: $0) },
            bookingEndTime: (data["bookingEndTime"] as? Timestamp)?.dateValue()
        )
    }
}

// MARK: - Listing Errors

enum ListingError: LocalizedError {
    case notFound
    case invalidData
    case cannotEditWithActiveBooking
    case cannotDeleteWithActiveBooking
    
    var errorDescription: String? {
        switch self {
        case .notFound:
            return "Listing not found"
        case .invalidData:
            return "Invalid listing data"
        case .cannotEditWithActiveBooking:
            return "Cannot edit listing with an active booking"
        case .cannotDeleteWithActiveBooking:
            return "Cannot delete listing with an active booking"
        }
    }
}

// MARK: - Data Transfer Objects

/// Data for creating/updating a listing
struct PrivateListingData {
    var ownerName: String
    var title: String
    var address: String
    var latitude: Double
    var longitude: Double
    var description: String
    var hourlyRate: Double
    var dailyRate: Double
    var monthlyRate: Double
    var autoAcceptBookings: Bool
    var hasCCTV: Bool
    var isCovered: Bool
    var hasEVCharging: Bool
    var hasSecurityGuard: Bool
    var is24Hours: Bool
    
    func toFirestoreData() -> [String: Any] {
        return [
            "ownerName": ownerName,
            "title": title,
            "address": address,
            "location": ["lat": latitude, "lon": longitude],
            "description": description,
            "pricing": [
                "hourlyRate": hourlyRate,
                "dailyRate": dailyRate,
                "monthlyRate": monthlyRate
            ],
            "autoAcceptBookings": autoAcceptBookings,
            "amenities": [
                "hasCCTV": hasCCTV,
                "isCovered": isCovered,
                "hasEVCharging": hasEVCharging,
                "hasSecurityGuard": hasSecurityGuard
            ],
            "is24Hours": is24Hours,
            "rating": 0,
            "reviewCount": 0,
            "imageURLs": []
        ]
    }
}

/// Data for creating a slot
struct PrivateSlotData {
    var slotNumber: Int
    var slotLabel: String?
    var vehicleSize: PrivateSlotSize
    var canFitSUV: Bool
    
    func toFirestoreData() -> [String: Any] {
        return [
            "slotNumber": slotNumber,
            "slotLabel": slotLabel as Any,
            "vehicleSize": vehicleSize.rawValue,
            "canFitSUV": canFitSUV,
            "canFitBike": true,
            "isOccupied": false,
            "isDisabled": false,
            "currentBookingID": NSNull(),
            "bookingEndTime": NSNull()
        ]
    }
}

