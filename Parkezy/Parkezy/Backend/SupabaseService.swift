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
    
    // MARK: - Auth & User Profiles
    
    /// Queries the 'profiles' table to fetch the current user
    func getUserProfile(id: String) async -> AppUser? {
        do {
            return try await client.database.from("profiles").select().eq("id", value: id).single().execute().value
        } catch {
            print("Supabase Error [getUserProfile]: \(error)")
            return nil
        }
    }
    
    /// Queries the 'profiles' table to update user profile
    func updateUserProfile(_ user: AppUser) async -> Bool {
        do {
            try await client.database.from("profiles").update(user).eq("id", value: user.id).execute()
            return true
        } catch {
            print("Supabase Error [updateUserProfile]: \(error)")
            return false
        }
    }
    
    // MARK: - Private Listings
    
    /// Queries the 'private_listings' table for driver view
    func getAllPrivateListings() async -> [PrivateParkingListing] {
        do {
            return try await client.database.from("private_listings").select().execute().value
        } catch {
            print("Supabase Error [getAllPrivateListings]: \(error)")
            return []
        }
    }
    
    /// Queries the 'private_listings' table for host view
    func getMyPrivateListings(ownerID: String) async -> [PrivateParkingListing] {
        do {
            return try await client.database.from("private_listings").select().eq("owner_id", value: ownerID).execute().value
        } catch {
            print("Supabase Error [getMyPrivateListings]: \(error)")
            return []
        }
    }
    
    /// Inserts into the 'private_listings' table
    func createPrivateListing(_ listing: PrivateParkingListing) async -> PrivateParkingListing? {
        do {
            return try await client.database.from("private_listings").insert(listing).single().execute().value
        } catch {
            print("Supabase Error [createPrivateListing]: \(error)")
            return nil
        }
    }
    
    /// Updates the 'private_listings' table
    func updatePrivateListing(_ listing: PrivateParkingListing) async -> Bool {
        do {
            try await client.database.from("private_listings").update(listing).eq("id", value: listing.id.uuidString).execute()
            return true
        } catch {
            print("Supabase Error [updatePrivateListing]: \(error)")
            return false
        }
    }
    
    /// Deletes from the 'private_listings' table
    func deletePrivateListing(id: String) async -> Bool {
        do {
            try await client.database.from("private_listings").delete().eq("id", value: id).execute()
            return true
        } catch {
            print("Supabase Error [deletePrivateListing]: \(error)")
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
            print("Supabase Error [getNearbyFacilities]: \(error)")
            return []
        }
    }
    
    // MARK: - Bookings
    
    /// Queries the 'bookings' table for private bookings
    func getPrivateBookings(userID: String) async -> [BookingSession] {
        do {
            return try await client.database.from("bookings").select().eq("user_id", value: userID).eq("type", value: "private").execute().value
        } catch {
            print("Supabase Error [getPrivateBookings]: \(error)")
            return []
        }
    }
    
    /// Inserts into the 'bookings' table
    func requestPrivateBooking(_ request: BookingSession) async -> BookingSession? {
        do {
            return try await client.database.from("bookings").insert(request).single().execute().value
        } catch {
            print("Supabase Error [requestPrivateBooking]: \(error)")
            return nil
        }
    }
}
