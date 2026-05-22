//
//  BookingViewModel.swift
//  ParkEzy
//
//  Manages booking lifecycle, timer updates, and overstay logic
//

import SwiftUI
import Combine

@MainActor
class BookingViewModel: ObservableObject {
    // MARK: - Published Properties
    
    /// Current active booking session
    @Published var activeSession: BookingSession?
    
    /// Last completed session (for receipt display)
    @Published var lastCompletedSession: BookingSession?
    
    /// Booking history
    @Published var bookingHistory: [BookingSession] = []
    
    /// Time remaining in current session (seconds)
    @Published var timeRemaining: TimeInterval = 0
    
    /// Current running cost
    @Published var currentCost: Double = 0
    
    /// Overstay fee (if any)
    @Published var overstayFee: Double?
    
    /// Session state
    @Published var isSessionActive = false
    
    // MARK: - Private Properties
    
    private var timer: Timer?
    private var cancellables = Set<AnyCancellable>()
    private var currentSpot: ParkingSpot?
    
    // MARK: - Initialization
    
    init() {
        setupGeofenceObservers()
    }
    
    // MARK: - Setup
    
    private func setupGeofenceObservers() {
        NotificationCenter.default.publisher(for: .didEnterParkingGeofence)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] notification in
                if let spotID = notification.userInfo?["spotID"] as? UUID {
                    self?.handleGeofenceEntry(spotID: spotID)
                }
            }
            .store(in: &cancellables)
        
        NotificationCenter.default.publisher(for: .didExitParkingGeofence)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] notification in
                if let spotID = notification.userInfo?["spotID"] as? UUID {
                    self?.handleGeofenceExit(spotID: spotID)
                }
            }
            .store(in: &cancellables)
    }
    
    // MARK: - Booking Creation
    
    func createBooking(spot: ParkingSpot, duration: Double, totalCost: Double) {
        let now = Date()
        let endTime = Calendar.current.date(byAdding: .minute, value: Int(duration * 60), to: now)!
        
        let session = BookingSession(
            id: UUID(),
            spotID: spot.id,
            userID: UUID(), // In production, get from auth
            bookingTime: now,
            scheduledStartTime: now,
            actualStartTime: nil,
            scheduledEndTime: endTime,
            actualEndTime: nil,
            duration: duration,
            totalCost: totalCost,
            overstayFee: nil,
            status: .confirmed,
            accessCode: spot.accessPIN ?? String(format: "%06d", Int.random(in: 100000...999999))
        )
        
        activeSession = session
        currentSpot = spot
        isSessionActive = false // Not started until verified
        
        // Start geofence monitoring
        LocationManager.shared.monitorGeofence(for: spot.id, at: spot.coordinates)
        
        // Schedule notifications
        NotificationManager.shared.scheduleSessionWarnings(for: session)
        
        print("✅ Booking created: \(session.id.uuidString.prefix(8))")
    }
    
    // MARK: - Session Control
    
    func startSession() {
        guard var session = activeSession else { return }
        
        session.actualStartTime = Date()
        session.status = .active
        activeSession = session
        isSessionActive = true
        
        // Start timer updates
        startTimer()
        
        // Start Live Activity (if available)
        startLiveActivity()
        
        print("▶️ Session started: \(session.id.uuidString.prefix(8))")
    }
    
    func endSession() {
        guard var session = activeSession else { return }
        
        session.actualEndTime = Date()
        session.status = .completed
        
        // Calculate final overstay
        if let startTime = session.actualStartTime {
            let actualDuration = Date().timeIntervalSince(startTime)
            let scheduledDuration = session.scheduledEndTime.timeIntervalSince(startTime)
            
            if actualDuration > scheduledDuration {
                let overstayMinutes = (actualDuration - scheduledDuration) / 60
                session.overstayFee = ceil(overstayMinutes / 15) * 20
                session.totalCost += session.overstayFee ?? 0
            }
        }
        
        lastCompletedSession = session
        bookingHistory.append(session)
        
        // Cleanup
        stopTimer()
        endLiveActivity()
        NotificationManager.shared.cancelSessionWarnings(for: session)
        
        if let spot = currentSpot {
            LocationManager.shared.stopMonitoringGeofence(for: spot.id)
            MockDataService.shared.updateSpotOccupancy(id: spot.id, isOccupied: false)
        }
        
        activeSession = nil
        currentSpot = nil
        isSessionActive = false
        overstayFee = nil
        
        print("⏹️ Session ended: \(session.id.uuidString.prefix(8))")
    }
    
    func extendSession(by hours: Double) {
        guard var session = activeSession else { return }
        
        let additionalMinutes = Int(hours * 60)
        session.scheduledEndTime = Calendar.current.date(
            byAdding: .minute,
            value: additionalMinutes,
            to: session.scheduledEndTime
        )!
        
        session.duration += hours
        
        if let spot = currentSpot {
            let additionalCost = spot.pricePerHour * hours * 1.18 // Including GST
            session.totalCost += additionalCost
        }
        
        activeSession = session
        
        // Update notifications
        NotificationManager.shared.cancelSessionWarnings(for: session)
        NotificationManager.shared.scheduleSessionWarnings(for: session)
        
        // Update Live Activity
        updateLiveActivity()
        
        print("⏰ Session extended by \(hours) hours")
    }
    
    // MARK: - Timer Management
    
    func updateSessionMetrics() {
        guard let session = activeSession,
              let startTime = session.actualStartTime else { return }
        
        let now = Date()
        
        // Calculate time remaining
        timeRemaining = session.scheduledEndTime.timeIntervalSince(now)
        
        // Calculate current cost
        let elapsedHours = now.timeIntervalSince(startTime) / 3600
        
        if let spot = currentSpot {
            let baseCost = spot.pricePerHour * elapsedHours
            let gst = baseCost * 0.18
            currentCost = baseCost + gst
        }
        
        // Calculate overstay if applicable
        if timeRemaining < 0 {
            let overstayMinutes = abs(timeRemaining) / 60
            overstayFee = ceil(overstayMinutes / 15) * 20
        } else {
            overstayFee = nil
        }
        
        // Update Live Activity
        updateLiveActivity()
    }
    
    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.updateSessionMetrics()
            }
        }
    }
    
    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }
    
    func refreshSessionState() {
        if activeSession != nil {
            updateSessionMetrics()
        }
    }
    
    // MARK: - Geofence Handling
    
    private func handleGeofenceEntry(spotID: UUID) {
        guard let session = activeSession,
              session.spotID == spotID else { return }
        
        print("📍 Arrived at parking spot")
        
        // Prompt user to verify (handled by notification)
    }
    
    private func handleGeofenceExit(spotID: UUID) {
        guard let session = activeSession,
              session.spotID == spotID,
              session.status == .active else { return }
        
        print("👋 Left parking spot - consider ending session")
        
        // In production, auto-end or prompt
    }
    
    // MARK: - Live Activity
    
    private func startLiveActivity() {
        // Live Activity implementation is in ParkingLiveActivity.swift
        // This would call ActivityKit to start the activity
        print("🔴 Live Activity started")
    }
    
    private func updateLiveActivity() {
        // Update the Live Activity with current metrics
    }
    
    private func endLiveActivity() {
        print("⚪ Live Activity ended")
    }
}
