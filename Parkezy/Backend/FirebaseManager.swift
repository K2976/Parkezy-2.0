//
//  FirebaseManager.swift
//  ParkEzy
//
//  Central Firebase access point.
//  Views should NOT use this directly - use Repositories instead.
//

import Foundation
import FirebaseCore
import FirebaseAuth
import FirebaseFirestore

/// Singleton that manages Firebase Auth and Firestore references.
/// All Firebase access goes through this class.
final class FirebaseManager {
    
    // MARK: - Singleton
    
    static let shared = FirebaseManager()
    
    // MARK: - Firebase References
    
    /// Firebase Authentication instance
    let auth: Auth
    
    /// Firestore database instance
    let db: Firestore
    
    // MARK: - Initialization
    
    private init() {
        // Firebase should be configured in AppDelegate before this is called
        self.auth = Auth.auth()
        self.db = Firestore.firestore()
        
        // Enable offline persistence (data available even without network)
        let settings = FirestoreSettings()
        settings.cacheSettings = PersistentCacheSettings()
        db.settings = settings
    }
    
    // MARK: - Current User
    
    /// Returns the current authenticated user's ID, or nil if not logged in
    var currentUserID: String? {
        auth.currentUser?.uid
    }
    
    /// Returns true if a user is currently authenticated
    var isAuthenticated: Bool {
        auth.currentUser != nil
    }
    
    // MARK: - Collection References
    
    /// Reference to the users collection
    var usersCollection: CollectionReference {
        db.collection("users")
    }
    
    /// Reference to the private listings collection
    var privateListingsCollection: CollectionReference {
        db.collection("privateListings")
    }
    
    /// Reference to the commercial facilities collection
    var commercialFacilitiesCollection: CollectionReference {
        db.collection("commercialFacilities")
    }
    
    /// Reference to the bookings collection
    var bookingsCollection: CollectionReference {
        db.collection("bookings")
    }
    
    // MARK: - Document References
    
    /// Get a user document reference by ID
    func userDocument(id: String) -> DocumentReference {
        usersCollection.document(id)
    }
    
    /// Get a private listing document reference by ID
    func privateListingDocument(id: String) -> DocumentReference {
        privateListingsCollection.document(id)
    }
    
    /// Get a commercial facility document reference by ID
    func commercialFacilityDocument(id: String) -> DocumentReference {
        commercialFacilitiesCollection.document(id)
    }
    
    /// Get a booking document reference by ID
    func bookingDocument(id: String) -> DocumentReference {
        bookingsCollection.document(id)
    }
}
