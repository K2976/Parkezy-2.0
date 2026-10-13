//
//  LocationManager.swift
//  ParkEzy
//
//  CoreLocation manager for GPS tracking and geofencing
//

import Foundation
import CoreLocation
import Combine

class LocationManager: NSObject, ObservableObject {
    // MARK: - Singleton
    
    static let shared = LocationManager()
    
    // MARK: - Published Properties
    
    @Published var userLocation: CLLocation?
    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined
    @Published var isInGeofence = false
    @Published var lastGeofenceEvent: GeofenceEvent?
    
    // MARK: - Private Properties
    
    private let locationManager = CLLocationManager()
    private var monitoredRegions: [CLCircularRegion] = []
    
    // MARK: - Initialization
    
    override private init() {
        super.init()
        setupLocationManager()
    }
    
    // MARK: - Setup
    
    private func setupLocationManager() {
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyBest
        locationManager.distanceFilter = 10 // Update every 10 meters
        // Background location updates require UIBackgroundModes capability in Info.plist
        // Disable for now since the app functions primarily in the foreground
        locationManager.pausesLocationUpdatesAutomatically = true
    }
    
    // MARK: - Public Methods
    
    func requestLocationPermission() {
        locationManager.requestWhenInUseAuthorization()
    }
    
    func requestAlwaysPermission() {
        locationManager.requestAlwaysAuthorization()
    }
    
    func startLocationUpdates() {
        locationManager.startUpdatingLocation()
    }
    
    func stopLocationUpdates() {
        locationManager.stopUpdatingLocation()
    }
    
    // MARK: - Geofencing
    
    /// Geofence radius in meters (editable for testing)
    static var geofenceRadius: Double = 50.0
    
    func monitorGeofence(for spotID: UUID, at coordinate: CLLocationCoordinate2D) {
        let region = CLCircularRegion(
            center: coordinate,
            radius: LocationManager.geofenceRadius,
            identifier: spotID.uuidString
        )
        region.notifyOnEntry = true
        region.notifyOnExit = true
        
        locationManager.startMonitoring(for: region)
        monitoredRegions.append(region)
        
        print("📍 Started monitoring geofence for spot: \(spotID.uuidString.prefix(8))")
    }
    
    func stopMonitoringGeofence(for spotID: UUID) {
        if let region = monitoredRegions.first(where: { $0.identifier == spotID.uuidString }) {
            locationManager.stopMonitoring(for: region)
            monitoredRegions.removeAll { $0.identifier == spotID.uuidString }
            
            print("🛑 Stopped monitoring geofence for spot: \(spotID.uuidString.prefix(8))")
        }
    }
    
    func stopAllGeofenceMonitoring() {
        for region in monitoredRegions {
            locationManager.stopMonitoring(for: region)
        }
        monitoredRegions.removeAll()
    }
    
    // MARK: - Debug Methods (for Simulator)
    
    func simulateArrival(at spotID: UUID) {
        let event = GeofenceEvent(
            spotID: spotID,
            type: .entry,
            timestamp: Date()
        )
        lastGeofenceEvent = event
        isInGeofence = true
        
        NotificationCenter.default.post(
            name: .didEnterParkingGeofence,
            object: nil,
            userInfo: ["spotID": spotID]
        )
        
        print("🎯 Simulated arrival at spot: \(spotID.uuidString.prefix(8))")
    }
    
    func simulateDeparture(from spotID: UUID) {
        let event = GeofenceEvent(
            spotID: spotID,
            type: .exit,
            timestamp: Date()
        )
        lastGeofenceEvent = event
        isInGeofence = false
        
        NotificationCenter.default.post(
            name: .didExitParkingGeofence,
            object: nil,
            userInfo: ["spotID": spotID]
        )
        
        print("👋 Simulated departure from spot: \(spotID.uuidString.prefix(8))")
    }
    
    // MARK: - Distance Calculation
    
    func distance(to coordinate: CLLocationCoordinate2D) -> Double {
        guard let userLocation = userLocation else { return 0 }
        
        let spotLocation = CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)
        return userLocation.distance(from: spotLocation)
    }
}

// MARK: - CLLocationManagerDelegate

extension LocationManager: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        userLocation = location
    }
    
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authorizationStatus = manager.authorizationStatus
        
        switch manager.authorizationStatus {
        case .authorizedWhenInUse, .authorizedAlways:
            startLocationUpdates()
        default:
            break
        }
    }
    
    func locationManager(_ manager: CLLocationManager, didEnterRegion region: CLRegion) {
        guard let circularRegion = region as? CLCircularRegion,
              let spotID = UUID(uuidString: circularRegion.identifier) else { return }
        
        let event = GeofenceEvent(spotID: spotID, type: .entry, timestamp: Date())
        lastGeofenceEvent = event
        isInGeofence = true
        
        NotificationCenter.default.post(
            name: .didEnterParkingGeofence,
            object: nil,
            userInfo: ["spotID": spotID]
        )
        
        // Send notification
        NotificationManager.shared.scheduleNotification(
            title: "🎯 You've Arrived!",
            body: "Tap to verify your parking and start your session.",
            delay: 0.1
        )
        
        print("📍 Entered geofence: \(spotID.uuidString.prefix(8))")
    }
    
    func locationManager(_ manager: CLLocationManager, didExitRegion region: CLRegion) {
        guard let circularRegion = region as? CLCircularRegion,
              let spotID = UUID(uuidString: circularRegion.identifier) else { return }
        
        let event = GeofenceEvent(spotID: spotID, type: .exit, timestamp: Date())
        lastGeofenceEvent = event
        isInGeofence = false
        
        NotificationCenter.default.post(
            name: .didExitParkingGeofence,
            object: nil,
            userInfo: ["spotID": spotID]
        )
        
        print("👋 Exited geofence: \(spotID.uuidString.prefix(8))")
    }
    
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("❌ Location manager error: \(error.localizedDescription)")
    }
}

// MARK: - Geofence Event

struct GeofenceEvent {
    let spotID: UUID
    let type: GeofenceEventType
    let timestamp: Date
}

enum GeofenceEventType {
    case entry
    case exit
}

// MARK: - Notification Names

extension Notification.Name {
    static let didEnterParkingGeofence = Notification.Name("didEnterParkingGeofence")
    static let didExitParkingGeofence = Notification.Name("didExitParkingGeofence")
}
