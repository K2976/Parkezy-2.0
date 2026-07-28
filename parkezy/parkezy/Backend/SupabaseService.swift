//
//  SupabaseService.swift
//  ParkEzy
//
//  Centralized service for Supabase interactions.
//

import Foundation
import CoreLocation

@MainActor
final class SupabaseService {
    static let shared = SupabaseService()
    private let client = SupabaseConfig.client
    
    private init() {}
    
    // MARK: - Auth Notifications
    static let sessionExpiredNotification = Notification.Name("SupabaseSessionExpired")
    
    // MARK: - Helper
    private func handleSupabaseError(_ error: Error, context: String) {
        print("Supabase Error [\(context)]: \(error)")
        // Simplified auth error check based on generic Supabase error structures
        let errorStr = String(describing: error).lowercased()
        if errorStr.contains("jwt") || errorStr.contains("expired") || errorStr.contains("unauthorized") {
            NotificationCenter.default.post(name: Self.sessionExpiredNotification, object: nil)
        }
    }
    
    // MARK: - Auth & User Profiles
    
    /// Queries the 'profiles' table to fetch the current user
    func getUserProfile(id: String) async -> AppUser? {
        do {
            return try await client.database.from("profiles").select().eq("id", value: id).single().execute().value
        } catch {
            handleSupabaseError(error, context: "getUserProfile")
            return nil
        }
    }
    
    /// Queries the 'profiles' table to update user profile
    func updateUserProfile(_ user: AppUser) async -> Bool {
        do {
            try await client.database.from("profiles").update(user).eq("id", value: user.id).execute()
            return true
        } catch {
            handleSupabaseError(error, context: "updateUserProfile")
            return false
        }
    }
    
    // MARK: - Private Listings
    
    /// Queries the 'private_listings' table for driver view
    func getAllPrivateListings() async -> [PrivateParkingListing] {
        do {
            return try await client.database.from("private_listings").select().execute().value
        } catch {
            handleSupabaseError(error, context: "getAllPrivateListings")
            return []
        }
    }
    
    /// Queries the 'private_listings' table for host view
    func getMyPrivateListings(ownerID: String) async -> [PrivateParkingListing] {
        do {
            return try await client.database.from("private_listings").select().eq("owner_id", value: ownerID).execute().value
        } catch {
            handleSupabaseError(error, context: "getMyPrivateListings")
            return []
        }
    }
    
    /// Inserts into the 'private_listings' table
    func createPrivateListing(_ listing: PrivateParkingListing) async -> PrivateParkingListing? {
        do {
            return try await client.database.from("private_listings").insert(listing).single().execute().value
        } catch {
            handleSupabaseError(error, context: "createPrivateListing")
            return nil
        }
    }
    
    /// Updates the 'private_listings' table
    func updatePrivateListing(_ listing: PrivateParkingListing) async -> Bool {
        do {
            try await client.database.from("private_listings").update(listing).eq("id", value: listing.id.uuidString).execute()
            return true
        } catch {
            handleSupabaseError(error, context: "updatePrivateListing")
            return false
        }
    }
    
    /// Deletes from the 'private_listings' table
    func deletePrivateListing(id: String) async -> Bool {
        do {
            try await client.database.from("private_listings").delete().eq("id", value: id).execute()
            return true
        } catch {
            handleSupabaseError(error, context: "deletePrivateListing")
            return false
        }
    }
    
    // MARK: - Commercial Facilities
    
    /// Queries the 'commercial_facilities' table
    func getNearbyFacilities(location: CLLocationCoordinate2D, radiusKm: Double) async -> [CommercialParkingFacility] {
        // Advanced PostGIS query would go here, simple fetch for now
        do {
            return try await client.database.from("commercial_facilities").select().execute().value
        } catch {
            handleSupabaseError(error, context: "getNearbyFacilities")
            return []
        }
    }
    
    // MARK: - Bookings
    
    /// Queries the 'bookings' table for private bookings
    func getPrivateBookings(userID: String) async -> [BookingSession] {
        do {
            return try await client.database.from("bookings").select().eq("user_id", value: userID).eq("type", value: "private").execute().value
        } catch {
            handleSupabaseError(error, context: "getPrivateBookings")
            return []
        }
    }
    
    /// Inserts into the 'bookings' table
    func requestPrivateBooking(_ request: BookingSession) async -> BookingSession? {
        do {
            return try await client.database.from("bookings").insert(request).single().execute().value
        } catch {
            handleSupabaseError(error, context: "requestPrivateBooking")
            return nil
        }
    }
}
