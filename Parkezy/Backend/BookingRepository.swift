//
//  BookingRepository.swift
//  ParkEzy
//
//  Manages all bookings in Firestore.
//  Handles both private (with approval) and commercial (instant) bookings.
//  Uses transactions to prevent overbooking.
//

import Foundation
import FirebaseFirestore
import Combine

/// Status enum aligned with booking lifecycle
enum BookingStatusType: String, Codable {
    case requested = "requested"        // Private: waiting for host approval
    case confirmed = "confirmed"        // Approved and scheduled
    case active = "active"              // Currently parked
    case cancelRequested = "cancel_requested"  // Driver requested cancellation
    case cancelled = "cancelled"        // Booking cancelled
    case completed = "completed"        // Booking finished
    case rejected = "rejected"          // Host rejected (private only)
    case noShow = "no_show"             // Didn't show up
}

/// Type of booking
enum BookingType: String, Codable {
    case privateParking = "private"
    case commercialParking = "commercial"
}

/// Repository for managing all bookings
final class BookingRepository: ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = BookingRepository()
    
    // MARK: - Properties
    
    private let firebase = FirebaseManager.shared
    private var driverBookingsListener: ListenerRegistration?
    private var hostBookingsListener: ListenerRegistration?
    
    // MARK: - Initialization
    
    private init() {}
    
    deinit {
        driverBookingsListener?.remove()
        hostBookingsListener?.remove()
    }
    
    // MARK: - Create Private Booking
    
    /// Request a private parking booking (requires host approval unless auto-accept)
    func requestPrivateBooking(_ request: PrivateBookingRequest) async throws -> String {
        guard let driverID = firebase.currentUserID else {
            throw AuthError.notAuthenticated
        }
        
        // Check if listing allows auto-accept
        let listing = try await PrivateListingRepository.shared.getListing(id: request.listingID)
        let initialStatus: BookingStatusType = listing.autoAcceptBookings ? .confirmed : .requested
        
        let docRef = firebase.bookingsCollection.document()
        let bookingID = docRef.documentID
        
        // Generate access PIN
        let accessPIN = String(format: "%06d", Int.random(in: 0...999999))
        
        let bookingData: [String: Any] = [
            "id": bookingID,
            "type": BookingType.privateParking.rawValue,
            "driverID": driverID,
            "hostID": request.hostID,
            "listingID": request.listingID,
            "slotID": request.slotID,
            "timing": [
                "requestedAt": FieldValue.serverTimestamp(),
                "scheduledStart": Timestamp(date: request.scheduledStart),
                "scheduledEnd": Timestamp(date: request.scheduledEnd),
                "actualStart": NSNull(),
                "actualEnd": NSNull()
            ],
            "pricing": [
                "agreedRate": request.hourlyRate,
                "estimatedCost": request.estimatedCost,
                "actualCost": NSNull(),
                "gstAmount": request.estimatedCost * 0.18
            ],
            "status": initialStatus.rawValue,
            "accessPIN": accessPIN,
            "messages": [
                "driverMessage": request.driverMessage as Any,
                "hostMessage": NSNull()
            ],
            "approvalTime": listing.autoAcceptBookings ? FieldValue.serverTimestamp() : NSNull(),
            "rejectionReason": NSNull()
        ]
        
        try await docRef.setData(bookingData)
        
        // If auto-accepted, update slot status
        if listing.autoAcceptBookings {
            try await PrivateListingRepository.shared.updateSlotStatus(
                listingID: request.listingID,
                slotID: request.slotID,
                isOccupied: false, // Not occupied until session starts
                bookingID: bookingID,
                endTime: request.scheduledEnd
            )
            try await PrivateListingRepository.shared.setActiveBookingFlag(
                listingID: request.listingID,
                hasActiveBooking: true
            )
        }
        
        // Increment driver booking count
        try await UserRepository.shared.incrementDriverBookingCount(userID: driverID)
        
        return bookingID
    }
    
    // MARK: - Create Commercial Booking (with Transaction)
    
    /// Book commercial parking (instant confirmation, uses transaction)
    func bookCommercialSpot(_ request: CommercialBookingRequest) async throws -> String {
        guard let driverID = firebase.currentUserID else {
            throw AuthError.notAuthenticated
        }
        
        let facilityRef = firebase.commercialFacilityDocument(id: request.facilityID)
        let bookingRef = firebase.bookingsCollection.document()
        let bookingID = bookingRef.documentID
        
        // Generate access code
        let accessCode = String(format: "%06d", Int.random(in: 0...999999))
        
        // Use transaction to atomically check capacity and create booking
        try await firebase.db.runTransaction { transaction, errorPointer in
            // Read facility
            let facilitySnapshot: DocumentSnapshot
            do {
                facilitySnapshot = try transaction.getDocument(facilityRef)
            } catch let error as NSError {
                errorPointer?.pointee = error
                return nil
            }
            
            guard let data = facilitySnapshot.data(),
                  let capacity = data["capacity"] as? [String: Int],
                  let available = capacity["available"],
                  available > 0 else {
                let error = NSError(
                    domain: "BookingError",
                    code: -1,
                    userInfo: [NSLocalizedDescriptionKey: "No parking spaces available"]
                )
                errorPointer?.pointee = error
                return nil
            }
            
            // Decrement capacity
            transaction.updateData([
                "capacity.available": FieldValue.increment(Int64(-1))
            ], forDocument: facilityRef)
            
            // Create booking
            let bookingData: [String: Any] = [
                "id": bookingID,
                "type": BookingType.commercialParking.rawValue,
                "driverID": driverID,
                "hostID": request.ownerID,
                "facilityID": request.facilityID,
                "timing": [
                    "requestedAt": FieldValue.serverTimestamp(),
                    "scheduledStart": Timestamp(date: request.scheduledStart),
                    "scheduledEnd": Timestamp(date: request.scheduledEnd),
                    "actualStart": NSNull(),
                    "actualEnd": NSNull()
                ],
                "pricing": [
                    "hourlyRate": request.hourlyRate,
                    "estimatedDuration": request.estimatedDuration,
                    "estimatedCost": request.estimatedCost,
                    "actualCost": NSNull()
                ],
                "vehicle": [
                    "vehicleNumber": request.vehicleNumber as Any,
                    "vehicleType": request.vehicleType as Any
                ],
                "status": BookingStatusType.confirmed.rawValue,
                "accessCode": accessCode
            ]
            
            transaction.setData(bookingData, forDocument: bookingRef)
            
            return nil
        }
        
        // Increment driver booking count
        try await UserRepository.shared.incrementDriverBookingCount(userID: driverID)
        
        return bookingID
    }
    
    // MARK: - Approve / Reject (Private)
    
    /// Host approves a private booking
    func approveBooking(id: String) async throws {
        try await updateBookingStatus(id: id, status: .confirmed, extraFields: [
            "approvalTime": FieldValue.serverTimestamp()
        ])
        
        // Get booking to update slot
        let booking = try await getBooking(id: id)
        if let listingID = booking["listingID"] as? String,
           let slotID = booking["slotID"] as? String,
           let timing = booking["timing"] as? [String: Any],
           let endTimestamp = timing["scheduledEnd"] as? Timestamp {
            try await PrivateListingRepository.shared.updateSlotStatus(
                listingID: listingID,
                slotID: slotID,
                isOccupied: false,
                bookingID: id,
                endTime: endTimestamp.dateValue()
            )
            try await PrivateListingRepository.shared.setActiveBookingFlag(
                listingID: listingID,
                hasActiveBooking: true
            )
        }
    }
    
    /// Host rejects a private booking
    func rejectBooking(id: String, reason: String) async throws {
        try await updateBookingStatus(id: id, status: .rejected, extraFields: [
            "rejectionReason": reason
        ])
    }
    
    // MARK: - Cancellation
    
    /// Driver requests cancellation
    func requestCancellation(id: String) async throws {
        let booking = try await getBooking(id: id)
        let bookingType = BookingType(rawValue: booking["type"] as? String ?? "") ?? .privateParking
        
        if bookingType == .privateParking {
            // Private: cancel immediately
            try await cancelBooking(id: id)
        } else {
            // Commercial: set to cancel_requested, needs owner confirmation
            try await updateBookingStatus(id: id, status: .cancelRequested)
        }
    }
    
    /// Owner confirms commercial cancellation (restores capacity)
    func confirmCancellation(id: String) async throws {
        let booking = try await getBooking(id: id)
        
        // Restore capacity
        if let facilityID = booking["facilityID"] as? String {
            try await CommercialFacilityRepository.shared.incrementCapacity(facilityID: facilityID)
        }
        
        try await updateBookingStatus(id: id, status: .cancelled)
    }
    
    /// Cancel a booking directly (for private bookings)
    func cancelBooking(id: String) async throws {
        let booking = try await getBooking(id: id)
        
        // If private, clear slot and listing flag
        if let listingID = booking["listingID"] as? String,
           let slotID = booking["slotID"] as? String {
            try await PrivateListingRepository.shared.updateSlotStatus(
                listingID: listingID,
                slotID: slotID,
                isOccupied: false,
                bookingID: nil,
                endTime: nil
            )
            try await PrivateListingRepository.shared.setActiveBookingFlag(
                listingID: listingID,
                hasActiveBooking: false
            )
        }
        
        try await updateBookingStatus(id: id, status: .cancelled)
    }
    
    // MARK: - Session Management
    
    /// Start parking session
    func startSession(bookingID: String) async throws {
        try await updateBookingStatus(id: bookingID, status: .active, extraFields: [
            "timing.actualStart": FieldValue.serverTimestamp()
        ])
        
        // Update slot to occupied if private
        let booking = try await getBooking(id: bookingID)
        if let listingID = booking["listingID"] as? String,
           let slotID = booking["slotID"] as? String {
            let timing = booking["timing"] as? [String: Any]
            let endTime = (timing?["scheduledEnd"] as? Timestamp)?.dateValue()
            
            try await PrivateListingRepository.shared.updateSlotStatus(
                listingID: listingID,
                slotID: slotID,
                isOccupied: true,
                bookingID: bookingID,
                endTime: endTime
            )
        }
    }
    
    /// End parking session
    func endSession(bookingID: String, actualCost: Double? = nil) async throws {
        var extraFields: [String: Any] = [
            "timing.actualEnd": FieldValue.serverTimestamp()
        ]
        if let cost = actualCost {
            extraFields["pricing.actualCost"] = cost
        }
        
        try await updateBookingStatus(id: bookingID, status: .completed, extraFields: extraFields)
        
        let booking = try await getBooking(id: bookingID)
        let bookingType = BookingType(rawValue: booking["type"] as? String ?? "") ?? .privateParking
        
        if bookingType == .privateParking {
            // Clear slot and listing flag
            if let listingID = booking["listingID"] as? String,
               let slotID = booking["slotID"] as? String {
                try await PrivateListingRepository.shared.updateSlotStatus(
                    listingID: listingID,
                    slotID: slotID,
                    isOccupied: false,
                    bookingID: nil,
                    endTime: nil
                )
                try await PrivateListingRepository.shared.setActiveBookingFlag(
                    listingID: listingID,
                    hasActiveBooking: false
                )
            }
            
            // Add earnings to host
            if let hostID = booking["hostID"] as? String,
               let pricing = booking["pricing"] as? [String: Any],
               let cost = pricing["estimatedCost"] as? Double {
                let earnings = cost * 0.85 // 15% platform fee
                try await UserRepository.shared.addHostEarnings(userID: hostID, amount: earnings)
            }
        } else {
            // Commercial: restore capacity
            if let facilityID = booking["facilityID"] as? String {
                try await CommercialFacilityRepository.shared.incrementCapacity(facilityID: facilityID)
            }
        }
    }
    
    // MARK: - Fetch Bookings
    
    /// Get a single booking
    func getBooking(id: String) async throws -> [String: Any] {
        let doc = try await firebase.bookingDocument(id: id).getDocument()
        guard let data = doc.data() else {
            throw BookingError.notFound
        }
        return data
    }
    
    /// Fetch bookings for a driver
    func getDriverBookings(driverID: String) async throws -> [[String: Any]] {
        let snapshot = try await firebase.bookingsCollection
            .whereField("driverID", isEqualTo: driverID)
            .order(by: "timing.requestedAt", descending: true)
            .getDocuments()
        
        return snapshot.documents.map { $0.data() }
    }
    
    /// Fetch bookings for a host (their listings)
    func getHostBookings(hostID: String) async throws -> [[String: Any]] {
        let snapshot = try await firebase.bookingsCollection
            .whereField("hostID", isEqualTo: hostID)
            .order(by: "timing.requestedAt", descending: true)
            .getDocuments()
        
        return snapshot.documents.map { $0.data() }
    }
    
    /// Fetch pending approvals for a host
    func getPendingApprovals(hostID: String) async throws -> [[String: Any]] {
        let snapshot = try await firebase.bookingsCollection
            .whereField("hostID", isEqualTo: hostID)
            .whereField("status", isEqualTo: BookingStatusType.requested.rawValue)
            .getDocuments()
        
        return snapshot.documents.map { $0.data() }
    }
    
    /// Fetch active bookings for a driver
    func getActiveBookings(driverID: String) async throws -> [[String: Any]] {
        let snapshot = try await firebase.bookingsCollection
            .whereField("driverID", isEqualTo: driverID)
            .whereField("status", isEqualTo: BookingStatusType.active.rawValue)
            .getDocuments()
        
        return snapshot.documents.map { $0.data() }
    }
    
    // MARK: - Real-time Listeners
    
    /// Listen to driver's bookings
    func driverBookingsListener(driverID: String) -> AnyPublisher<[[String: Any]], Error> {
        let subject = PassthroughSubject<[[String: Any]], Error>()
        
        driverBookingsListener?.remove()
        driverBookingsListener = firebase.bookingsCollection
            .whereField("driverID", isEqualTo: driverID)
            .order(by: "timing.requestedAt", descending: true)
            .addSnapshotListener { snapshot, error in
                if let error = error {
                    subject.send(completion: .failure(error))
                    return
                }
                
                let bookings = snapshot?.documents.map { $0.data() } ?? []
                subject.send(bookings)
            }
        
        return subject.eraseToAnyPublisher()
    }
    
    /// Listen to host's pending approvals
    func pendingApprovalsListener(hostID: String) -> AnyPublisher<[[String: Any]], Error> {
        let subject = PassthroughSubject<[[String: Any]], Error>()
        
        hostBookingsListener?.remove()
        hostBookingsListener = firebase.bookingsCollection
            .whereField("hostID", isEqualTo: hostID)
            .whereField("status", isEqualTo: BookingStatusType.requested.rawValue)
            .addSnapshotListener { snapshot, error in
                if let error = error {
                    subject.send(completion: .failure(error))
                    return
                }
                
                let bookings = snapshot?.documents.map { $0.data() } ?? []
                subject.send(bookings)
            }
        
        return subject.eraseToAnyPublisher()
    }
    
    // MARK: - Helper
    
    private func updateBookingStatus(id: String, status: BookingStatusType, extraFields: [String: Any] = [:]) async throws {
        var fields: [String: Any] = ["status": status.rawValue]
        fields.merge(extraFields) { _, new in new }
        
        try await firebase.bookingDocument(id: id).updateData(fields)
    }
}

// MARK: - Booking Errors

enum BookingError: LocalizedError {
    case notFound
    case noCapacity
    case invalidData
    
    var errorDescription: String? {
        switch self {
        case .notFound:
            return "Booking not found"
        case .noCapacity:
            return "No parking spaces available"
        case .invalidData:
            return "Invalid booking data"
        }
    }
}

// MARK: - Request Objects

/// Request for private booking
struct PrivateBookingRequest {
    var listingID: String
    var slotID: String
    var hostID: String
    var scheduledStart: Date
    var scheduledEnd: Date
    var hourlyRate: Double
    var estimatedCost: Double
    var driverMessage: String?
}

/// Request for commercial booking
struct CommercialBookingRequest {
    var facilityID: String
    var ownerID: String
    var scheduledStart: Date
    var scheduledEnd: Date
    var hourlyRate: Double
    var estimatedDuration: Double
    var estimatedCost: Double
    var vehicleNumber: String?
    var vehicleType: String?
}
