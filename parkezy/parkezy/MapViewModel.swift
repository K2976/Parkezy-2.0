//
//  MapViewModel.swift
//  ParkEzy
//
//  Manages map state, spot filtering, and distance calculations
//

import SwiftUI
import MapKit
import Combine

@MainActor
class MapViewModel: ObservableObject {
    // MARK: - Published Properties
    
    /// All parking spots
    @Published var spots: [ParkingSpot] = []
    
    /// Currently selected spot
    @Published var selectedSpot: ParkingSpot?
    
    /// User's current location
    @Published var userLocation: CLLocation?
    
    /// Nearest available spot
    @Published var nearestSpot: ParkingSpot?
    
    /// Search query
    @Published var searchQuery = ""
    
    /// Searched location from geocoding
    @Published var searchedLocation: CLLocationCoordinate2D?
    
    /// Geocoding in progress
    @Published var isGeocoding = false
    
    // MARK: - Filters
    
    @Published var filterEVCharging = false
    @Published var filterCCTV = false
    @Published var filterCovered = false
    @Published var filterMaxPrice: Double?
    @Published var filterAvailableOnly = true
    
    // MARK: - Private Properties
    
    private var cancellables = Set<AnyCancellable>()
    
    // MARK: - Initialization
    
    init() {
        setupLocationObserver()
    }
    
    // MARK: - Setup
    
    private func setupLocationObserver() {
        LocationManager.shared.$userLocation
            .receive(on: DispatchQueue.main)
            .sink { [weak self] location in
                self?.userLocation = location
                self?.updateDistances()
                self?.updateNearestSpot()
            }
            .store(in: &cancellables)
    }
    
    // MARK: - Data Loading
    
    func loadParkingSpots() {
        spots = MockDataService.shared.parkingSpots
        updateDistances()
        updateNearestSpot()
    }
    
    func startLocationTracking() {
        LocationManager.shared.startLocationUpdates()
    }
    
    // MARK: - Filtering
    
    func filteredSpots(searchQuery: String = "") -> [ParkingSpot] {
        var result = spots
        
        // Filter by availability
        if filterAvailableOnly {
            result = result.filter { !$0.isOccupied }
        }
        
        // Filter by features
        if filterEVCharging {
            result = result.filter { $0.hasEVCharging }
        }
        
        if filterCCTV {
            result = result.filter { $0.hasCCTV }
        }
        
        if filterCovered {
            result = result.filter { $0.isCovered }
        }
        
        // Filter by max price
        if let maxPrice = filterMaxPrice {
            result = result.filter { $0.pricePerHour <= maxPrice }
        }
        
        // Filter by search query
        if !searchQuery.isEmpty {
            result = result.filter { spot in
                spot.address.localizedCaseInsensitiveContains(searchQuery)
            }
        }
        
        // Sort by distance
        result = result.sorted { $0.distance < $1.distance }
        
        return result
    }
    
    // MARK: - Distance Calculations
    
    func distanceToSpot(_ spot: ParkingSpot) -> Double {
        guard let userLocation = userLocation else {
            return spot.distance
        }
        
        let spotLocation = CLLocation(
            latitude: spot.coordinates.latitude,
            longitude: spot.coordinates.longitude
        )
        
        return userLocation.distance(from: spotLocation)
    }
    
    private func updateDistances() {
        guard let userLocation = userLocation else { return }
        
        for index in spots.indices {
            let spotLocation = CLLocation(
                latitude: spots[index].coordinates.latitude,
                longitude: spots[index].coordinates.longitude
            )
            spots[index].distance = userLocation.distance(from: spotLocation)
        }
    }
    
    private func updateNearestSpot() {
        nearestSpot = spots
            .filter { !$0.isOccupied }
            .min { $0.distance < $1.distance }
    }
    
    // MARK: - Spot Selection
    
    func selectSpot(_ spot: ParkingSpot) {
        selectedSpot = spot
    }
    
    func clearSelection() {
        selectedSpot = nil
    }
    
    // MARK: - Location Search
    
    func searchLocation(query: String, completion: @escaping (CLLocationCoordinate2D?) -> Void) {
        guard !query.isEmpty else {
            searchedLocation = nil
            completion(nil)
            return
        }
        
        isGeocoding = true
        
        let geocoder = CLGeocoder()
        geocoder.geocodeAddressString(query) { [weak self] placemarks, error in
            DispatchQueue.main.async {
                self?.isGeocoding = false
                
                if let error = error {
                    print("Geocoding error: \(error.localizedDescription)")
                    self?.searchedLocation = nil
                    completion(nil)
                    return
                }
                
                if let coordinate = placemarks?.first?.location?.coordinate {
                    self?.searchedLocation = coordinate
                    completion(coordinate)
                } else {
                    self?.searchedLocation = nil
                    completion(nil)
                }
            }
        }
    }
    
    func clearLocationSearch() {
        searchedLocation = nil
    }
    
    // MARK: - Reset Filters
    
    func resetFilters() {
        filterEVCharging = false
        filterCCTV = false
        filterCovered = false
        filterMaxPrice = nil
        filterAvailableOnly = true
    }
}
