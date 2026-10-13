//
//  SupabaseService.swift
//  ParkEzy
//
//  Centralized service for Supabase interactions.
//

import Foundation
import CoreLocation
import Supabase
import PostgREST

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

    /// Queries all rows in the 'commercial_facilities' table
    func getAllCommercialFacilities() async -> [CommercialParkingFacility] {
        do {
            return try await client.database.from("commercial_facilities").select().execute().value
        } catch {
            handleSupabaseError(error, context: "getAllCommercialFacilities")
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

    /// Queries the generic 'bookings' table for a specific spot's driver session
    func getBookingSessions(userID: String) async -> [BookingSession] {
        do {
            return try await client.database.from("bookings").select().eq("user_id", value: userID).execute().value
        } catch {
            handleSupabaseError(error, context: "getBookingSessions")
            return []
        }
    }

    /// Inserts into the generic 'bookings' table (driver's single active session flow)
    func createBookingSession(_ session: BookingSession) async -> BookingSession? {
        do {
            return try await client.database.from("bookings").insert(session).single().execute().value
        } catch {
            handleSupabaseError(error, context: "createBookingSession")
            return nil
        }
    }

    /// Updates the generic 'bookings' table (e.g. ending a session)
    func updateBookingSession(_ session: BookingSession) async -> Bool {
        do {
            try await client.database.from("bookings").update(session).eq("id", value: session.id.uuidString).execute()
            return true
        } catch {
            handleSupabaseError(error, context: "updateBookingSession")
            return false
        }
    }

    // MARK: - Parking Spots (map pins)

    /// Queries all rows in the 'parking_spots' table
    func getParkingSpots() async -> [ParkingSpot] {
        do {
            return try await client.database.from("parking_spots").select().execute().value
        } catch {
            handleSupabaseError(error, context: "getParkingSpots")
            return []
        }
    }

    /// Updates a single spot's occupancy in the 'parking_spots' table
    func updateParkingSpotOccupancy(id: UUID, isOccupied: Bool) async -> Bool {
        do {
            try await client.database.from("parking_spots").update(["is_occupied": isOccupied]).eq("id", value: id.uuidString).execute()
            return true
        } catch {
            handleSupabaseError(error, context: "updateParkingSpotOccupancy")
            return false
        }
    }

    // MARK: - Private Booking Requests (host-approval flow, 'private_bookings' table)

    /// Queries all private booking requests for the listings a host owns
    func getPrivateBookingRequests(hostID: String) async -> [PrivateBooking] {
        do {
            return try await client.database.from("private_bookings").select().eq("host_id", value: hostID).execute().value
        } catch {
            handleSupabaseError(error, context: "getPrivateBookingRequests")
            return []
        }
    }

    /// Inserts a new booking request into the 'private_bookings' table
    func createPrivateBookingRequest(_ request: PrivateBooking) async -> PrivateBooking? {
        do {
            return try await client.database.from("private_bookings").insert(request).single().execute().value
        } catch {
            handleSupabaseError(error, context: "createPrivateBookingRequest")
            return nil
        }
    }

    /// Updates an existing row in the 'private_bookings' table (approve/reject/complete)
    func updatePrivateBookingRequest(_ request: PrivateBooking) async -> Bool {
        do {
            try await client.database.from("private_bookings").update(request).eq("id", value: request.id.uuidString).execute()
            return true
        } catch {
            handleSupabaseError(error, context: "updatePrivateBookingRequest")
            return false
        }
    }

    // MARK: - Commercial Bookings ('commercial_bookings' table, always auto-approved)

    /// Queries all commercial bookings for a driver
    func getCommercialBookings(driverID: String) async -> [CommercialBooking] {
        do {
            return try await client.database.from("commercial_bookings").select().eq("driver_id", value: driverID).execute().value
        } catch {
            handleSupabaseError(error, context: "getCommercialBookings")
            return []
        }
    }

    /// Inserts a new booking into the 'commercial_bookings' table
    func createCommercialBooking(_ booking: CommercialBooking) async -> CommercialBooking? {
        do {
            return try await client.database.from("commercial_bookings").insert(booking).single().execute().value
        } catch {
            handleSupabaseError(error, context: "createCommercialBooking")
            return nil
        }
    }

    // MARK: - Disputes

    /// Inserts a new dispute into the 'disputes' table
    func createDispute(_ dispute: DisputeReport) async -> DisputeReport? {
        do {
            return try await client.database.from("disputes").insert(dispute).single().execute().value
        } catch {
            handleSupabaseError(error, context: "createDispute")
            return nil
        }
    }
}
