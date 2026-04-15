//
//  UserRepository.swift
//  ParkEzy
//
//  Manages user profiles and capabilities in Firestore.
//

import Foundation
import FirebaseFirestore
import Combine

/// Repository for managing user data
final class UserRepository: ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = UserRepository()
    
    // MARK: - Properties
    
    private let firebase = FirebaseManager.shared
    private var userListener: ListenerRegistration?
    
    // MARK: - Initialization
    
    private init() {}
    
    deinit {
        userListener?.remove()
    }
    
    // MARK: - Fetch User
    
    /// Fetch a user by ID
    /// - Parameter id: The user's Firebase Auth UID
    /// - Returns: The user object
    func getUser(id: String) async throws -> AppUser {
        let document = try await firebase.userDocument(id: id).getDocument()
        guard let data = document.data() else {
            throw UserError.notFound
        }
        return try parseUser(from: data, id: id)
    }
    
    /// Get the current authenticated user's profile
    func getCurrentUser() async throws -> AppUser {
        guard let userID = firebase.currentUserID else {
            throw AuthError.notAuthenticated
        }
        return try await getUser(id: userID)
    }
    
    // MARK: - Update User
    
    /// Update user profile fields
    func updateUser(_ user: AppUser) async throws {
        let data = user.toFirestoreData()
        try await firebase.userDocument(id: user.id).updateData(data)
    }
    
    /// Update specific user fields
    func updateUserFields(id: String, fields: [String: Any]) async throws {
        try await firebase.userDocument(id: id).updateData(fields)
    }
    
    // MARK: - Capabilities
    
    /// Enable a capability for a user
    func enableCapability(_ capability: UserCapability, for userID: String) async throws {
        let field = "capabilities.\(capability.rawValue)"
        try await firebase.userDocument(id: userID).updateData([field: true])
    }
    
    /// Disable a capability for a user
    func disableCapability(_ capability: UserCapability, for userID: String) async throws {
        let field = "capabilities.\(capability.rawValue)"
        try await firebase.userDocument(id: userID).updateData([field: false])
    }
    
    // MARK: - Real-time Listener
    
    /// Listen to real-time updates for a user
    /// - Parameter id: The user's ID
    /// - Returns: A publisher that emits user updates
    func userListener(id: String) -> AnyPublisher<AppUser, Error> {
        let subject = PassthroughSubject<AppUser, Error>()
        
        userListener?.remove()
        userListener = firebase.userDocument(id: id).addSnapshotListener { snapshot, error in
            if let error = error {
                subject.send(completion: .failure(error))
                return
            }
            
            guard let data = snapshot?.data() else {
                subject.send(completion: .failure(UserError.notFound))
                return
            }
            
            do {
                let user = try self.parseUser(from: data, id: id)
                subject.send(user)
            } catch {
                subject.send(completion: .failure(error))
            }
        }
        
        return subject.eraseToAnyPublisher()
    }
    
    // MARK: - Stats Update
    
    /// Increment booking count for a driver
    func incrementDriverBookingCount(userID: String) async throws {
        try await firebase.userDocument(id: userID).updateData([
            "stats.totalBookingsAsDriver": FieldValue.increment(Int64(1))
        ])
    }
    
    /// Update host rating
    func updateHostRating(userID: String, rating: Double) async throws {
        try await firebase.userDocument(id: userID).updateData([
            "stats.hostRating": rating
        ])
    }
    
    /// Add to host earnings
    func addHostEarnings(userID: String, amount: Double) async throws {
        try await firebase.userDocument(id: userID).updateData([
            "stats.totalEarnings": FieldValue.increment(amount)
        ])
    }
    
    // MARK: - Parsing
    
    /// Parse Firestore data into AppUser
    private func parseUser(from data: [String: Any], id: String) throws -> AppUser {
        guard let email = data["email"] as? String,
              let name = data["name"] as? String else {
            throw UserError.invalidData
        }
        
        // Parse capabilities
        var capabilities = UserCapabilities()
        if let capsData = data["capabilities"] as? [String: Bool] {
            capabilities.canDrive = capsData["canDrive"] ?? true
            capabilities.canHostPrivate = capsData["canHostPrivate"] ?? false
            capabilities.canHostCommercial = capsData["canHostCommercial"] ?? false
        }
        
        // Parse stats
        var stats = UserStats()
        if let statsData = data["stats"] as? [String: Any] {
            stats.totalBookingsAsDriver = statsData["totalBookingsAsDriver"] as? Int ?? 0
            stats.hostRating = statsData["hostRating"] as? Double
            stats.totalEarnings = statsData["totalEarnings"] as? Double ?? 0
        }
        
        return AppUser(
            id: id,
            email: email,
            name: name,
            phoneNumber: data["phoneNumber"] as? String ?? "",
            profileImageURL: data["profileImageURL"] as? String,
            createdAt: (data["createdAt"] as? Timestamp)?.dateValue() ?? Date(),
            capabilities: capabilities,
            stats: stats
        )
    }
}

// MARK: - User Errors

enum UserError: LocalizedError {
    case notFound
    case invalidData
    
    var errorDescription: String? {
        switch self {
        case .notFound:
            return "User not found"
        case .invalidData:
            return "Invalid user data"
        }
    }
}

// MARK: - User Capability

enum UserCapability: String {
    case canDrive
    case canHostPrivate
    case canHostCommercial
}
