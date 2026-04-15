//
//  CommercialFacilityRepository.swift
//  ParkEzy
//
//  Manages commercial parking facilities in Firestore.
//  Uses capacity-based model (not individual slots) with Firestore transactions.
//

import Foundation
import FirebaseFirestore
import CoreLocation
import Combine

/// Repository for managing commercial parking facilities
final class CommercialFacilityRepository: ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = CommercialFacilityRepository()
    
    // MARK: - Properties
    
    private let firebase = FirebaseManager.shared
    private var facilitiesListener: ListenerRegistration?
    
    // MARK: - Initialization
    
    private init() {}
    
    deinit {
        facilitiesListener?.remove()
    }
    
    // MARK: - Create
    
    /// Create a new commercial facility
    func createFacility(_ data: CommercialFacilityData) async throws -> String {
        guard let ownerID = firebase.currentUserID else {
            throw AuthError.notAuthenticated
        }
        
        let docRef = firebase.commercialFacilitiesCollection.document()
        let facilityID = docRef.documentID
        
        var firestoreData = data.toFirestoreData()
        firestoreData["id"] = facilityID
        firestoreData["ownerID"] = ownerID
        firestoreData["isActive"] = true
        firestoreData["isDeleted"] = false
        firestoreData["createdAt"] = FieldValue.serverTimestamp()
        
        try await docRef.setData(firestoreData)
        
        // Enable commercial host capability
        try await UserRepository.shared.enableCapability(.canHostCommercial, for: ownerID)
        
        return facilityID
    }
    
    // MARK: - Read
    
    /// Fetch a single facility by ID
    func getFacility(id: String) async throws -> CommercialParkingFacility {
        let doc = try await firebase.commercialFacilityDocument(id: id).getDocument()
        guard let data = doc.data() else {
            throw FacilityError.notFound
        }
        return try parseFacility(from: data, id: id)
    }
    
    /// Fetch all facilities for an owner
    func getOwnerFacilities(ownerID: String) async throws -> [CommercialParkingFacility] {
        let snapshot = try await firebase.commercialFacilitiesCollection
            .whereField("ownerID", isEqualTo: ownerID)
            .whereField("isDeleted", isEqualTo: false)
            .getDocuments()
        
        return try snapshot.documents.compactMap { doc in
            try parseFacility(from: doc.data(), id: doc.documentID)
        }
    }
    
    /// Fetch nearby facilities
    func getNearbyFacilities(location: CLLocationCoordinate2D, radiusKm: Double = 15) async throws -> [CommercialParkingFacility] {
        let lat = location.latitude
        let lon = location.longitude
        let latDelta = radiusKm / 110.574
        let lonDelta = radiusKm / (111.320 * cos(lat * .pi / 180))
        
        let snapshot = try await firebase.commercialFacilitiesCollection
            .whereField("isActive", isEqualTo: true)
            .whereField("isDeleted", isEqualTo: false)
            .whereField("location.lat", isGreaterThan: lat - latDelta)
            .whereField("location.lat", isLessThan: lat + latDelta)
            .getDocuments()
        
        return try snapshot.documents.compactMap { doc in
            let data = doc.data()
            guard let locData = data["location"] as? [String: Double],
                  let docLon = locData["lon"],
                  docLon > lon - lonDelta && docLon < lon + lonDelta else {
                return nil
            }
            return try parseFacility(from: data, id: doc.documentID)
        }
    }
    
    /// Fetch all active facilities (for map view)
    func getAllActiveFacilities() async throws -> [CommercialParkingFacility] {
        let snapshot = try await firebase.commercialFacilitiesCollection
            .whereField("isActive", isEqualTo: true)
            .whereField("isDeleted", isEqualTo: false)
            .getDocuments()
        
        return try snapshot.documents.compactMap { doc in
            try parseFacility(from: doc.data(), id: doc.documentID)
        }
    }
    
    // MARK: - Update
    
    /// Update a facility
    func updateFacility(id: String, data: CommercialFacilityData) async throws {
        let updateData = data.toFirestoreData()
        try await firebase.commercialFacilityDocument(id: id).updateData(updateData)
    }
    
    /// Update specific fields
    func updateFacilityFields(id: String, fields: [String: Any]) async throws {
        try await firebase.commercialFacilityDocument(id: id).updateData(fields)
    }
    
    /// Toggle facility active status
    func toggleActive(id: String, isActive: Bool) async throws {
        try await firebase.commercialFacilityDocument(id: id).updateData([
            "isActive": isActive
        ])
    }
    
    // MARK: - Capacity Management (with Transactions)
    
    /// Decrement available capacity (when booking)
    /// Uses Firestore transaction to prevent race conditions
    func decrementCapacity(facilityID: String) async throws {
        let docRef = firebase.commercialFacilityDocument(id: facilityID)
        
        try await firebase.db.runTransaction { transaction, errorPointer in
            // Read current data
            let snapshot: DocumentSnapshot
            do {
                snapshot = try transaction.getDocument(docRef)
            } catch let error as NSError {
                errorPointer?.pointee = error
                return nil
            }
            
            guard let data = snapshot.data(),
                  let capacity = data["capacity"] as? [String: Int],
                  let available = capacity["available"],
                  available > 0 else {
                let error = NSError(domain: "FacilityError", code: -1,
                                   userInfo: [NSLocalizedDescriptionKey: "No capacity available"])
                errorPointer?.pointee = error
                return nil
            }
            
            // Decrement available count
            transaction.updateData([
                "capacity.available": FieldValue.increment(Int64(-1))
            ], forDocument: docRef)
            
            return nil
        }
    }
    
    /// Increment available capacity (when cancelling or completing)
    func incrementCapacity(facilityID: String) async throws {
        let docRef = firebase.commercialFacilityDocument(id: facilityID)
        
        try await firebase.db.runTransaction { transaction, errorPointer in
            let snapshot: DocumentSnapshot
            do {
                snapshot = try transaction.getDocument(docRef)
            } catch let error as NSError {
                errorPointer?.pointee = error
                return nil
            }
            
            guard let data = snapshot.data(),
                  let capacity = data["capacity"] as? [String: Int],
                  let total = capacity["total"],
                  let available = capacity["available"],
                  available < total else {
                // Already at max capacity, nothing to do
                return nil
            }
            
            transaction.updateData([
                "capacity.available": FieldValue.increment(Int64(1))
            ], forDocument: docRef)
            
            return nil
        }
    }
    
    /// Update total capacity
    func updateCapacity(facilityID: String, total: Int) async throws {
        let doc = try await firebase.commercialFacilityDocument(id: facilityID).getDocument()
        guard let data = doc.data(),
              let capacity = data["capacity"] as? [String: Int],
              let currentTotal = capacity["total"],
              let available = capacity["available"] else {
            throw FacilityError.invalidData
        }
        
        // Calculate new available based on occupancy
        let occupied = currentTotal - available
        let newAvailable = max(0, total - occupied)
        
        try await firebase.commercialFacilityDocument(id: facilityID).updateData([
            "capacity.total": total,
            "capacity.available": newAvailable
        ])
    }
    
    // MARK: - Delete (Soft)
    
    /// Soft delete a facility
    func softDeleteFacility(id: String) async throws {
        try await firebase.commercialFacilityDocument(id: id).updateData([
            "isDeleted": true,
            "isActive": false
        ])
    }
    
    // MARK: - Real-time Listeners
    
    /// Listen to owner's facilities in real-time
    func ownerFacilitiesListener(ownerID: String) -> AnyPublisher<[CommercialParkingFacility], Error> {
        let subject = PassthroughSubject<[CommercialParkingFacility], Error>()
        
        facilitiesListener?.remove()
        facilitiesListener = firebase.commercialFacilitiesCollection
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
                
                let facilities = documents.compactMap { doc -> CommercialParkingFacility? in
                    try? self?.parseFacility(from: doc.data(), id: doc.documentID)
                }
                subject.send(facilities)
            }
        
        return subject.eraseToAnyPublisher()
    }
    
    // MARK: - Parsing
    
    /// Parse Firestore data to CommercialParkingFacility
    private func parseFacility(from data: [String: Any], id: String) throws -> CommercialParkingFacility {
        guard let ownerID = data["ownerID"] as? String,
              let name = data["name"] as? String,
              let address = data["address"] as? String,
              let location = data["location"] as? [String: Double],
              let lat = location["lat"],
              let lon = location["lon"] else {
            throw FacilityError.invalidData
        }
        
        let typeString = data["facilityType"] as? String ?? "mall"
        let facilityType = CommercialFacilityType(rawValue: typeString) ?? .mall
        
        let pricing = data["pricing"] as? [String: Double] ?? [:]
        let amenities = data["amenities"] as? [String: Bool] ?? [:]
        let capacity = data["capacity"] as? [String: Int] ?? ["total": 100, "available": 100]
        
        // Create placeholder slots based on capacity (not individual slots in Firestore)
        let totalSlots = capacity["total"] ?? 100
        let availableSlots = capacity["available"] ?? totalSlots
        
        return CommercialParkingFacility(
            id: UUID(uuidString: id) ?? UUID(),
            name: name,
            address: address,
            coordinates: CLLocationCoordinate2D(latitude: lat, longitude: lon),
            facilityType: facilityType,
            slots: [], // Not using individual slots anymore
            defaultHourlyRate: pricing["defaultHourlyRate"] ?? 60,
            flatDayRate: pricing["flatDayRate"],
            hasCCTV: amenities["hasCCTV"] ?? true,
            hasEVCharging: amenities["hasEVCharging"] ?? false,
            hasValetService: amenities["hasValetService"] ?? false,
            hasCarWash: amenities["hasCarWash"] ?? false,
            is24Hours: amenities["is24Hours"] ?? true,
            rating: data["rating"] as? Double ?? 0,
            reviewCount: data["reviewCount"] as? Int ?? 0,
            ownerID: UUID(uuidString: ownerID) ?? UUID(),
            ownerName: data["ownerName"] as? String ?? ""
        )
    }
}

// MARK: - Facility Errors

enum FacilityError: LocalizedError {
    case notFound
    case invalidData
    case noCapacity
    
    var errorDescription: String? {
        switch self {
        case .notFound:
            return "Facility not found"
        case .invalidData:
            return "Invalid facility data"
        case .noCapacity:
            return "No parking spaces available"
        }
    }
}

// MARK: - Data Transfer Object

/// Data for creating/updating a facility
struct CommercialFacilityData {
    var name: String
    var address: String
    var latitude: Double
    var longitude: Double
    var facilityType: CommercialFacilityType
    var totalCapacity: Int
    var defaultHourlyRate: Double
    var flatDayRate: Double?
    var hasCCTV: Bool
    var hasEVCharging: Bool
    var hasValetService: Bool
    var hasCarWash: Bool
    var is24Hours: Bool
    var ownerName: String
    
    func toFirestoreData() -> [String: Any] {
        return [
            "name": name,
            "address": address,
            "location": ["lat": latitude, "lon": longitude],
            "facilityType": facilityType.rawValue,
            "capacity": [
                "total": totalCapacity,
                "available": totalCapacity
            ],
            "pricing": [
                "defaultHourlyRate": defaultHourlyRate,
                "flatDayRate": flatDayRate as Any
            ],
            "amenities": [
                "hasCCTV": hasCCTV,
                "hasEVCharging": hasEVCharging,
                "hasValetService": hasValetService,
                "hasCarWash": hasCarWash,
                "is24Hours": is24Hours
            ],
            "ownerName": ownerName,
            "rating": 0,
            "reviewCount": 0
        ]
    }
}
