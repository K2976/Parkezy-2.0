//
//  ActiveSessionView.swift
//  ParkEzy
//
//  Live session view with countdown timer, cost counter, and session controls
//

import SwiftUI
import MapKit

struct ActiveSessionView: View {
    // MARK: - Environment
    
    @EnvironmentObject var bookingViewModel: BookingViewModel
    @EnvironmentObject var mapViewModel: MapViewModel
    @Environment(\.dismiss) private var dismiss
    
    // MARK: - State
    
    @State private var showExtendSheet = false
    @State private var showEndConfirmation = false
    @State private var showDisputeView = false
    @State private var showReceiptView = false
    
    // Timer for live updates
    @State private var timer: Timer?
    @State private var currentTime = Date()
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignSystem.Spacing.l) {
                    // MARK: - Status Header
                    
                    statusHeader
                    
                    // MARK: - Timer Card
                    
                    timerCard
                    
                    // MARK: - Cost Card
                    
                    costCard
                    
                    // MARK: - Live Map
                    
                    liveMapCard
                    
                    // MARK: - Quick Actions
                    
                    quickActionsGrid
                    
                    // MARK: - Main Actions
                    
                    mainActionButtons
                }
                .padding(DesignSystem.Spacing.m)
            }
            .navigationTitle("Active Session")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showDisputeView = true
                    } label: {
                        Image(systemName: "exclamationmark.triangle")
                            .foregroundColor(DesignSystem.Colors.error)
                    }
                }
            }
            .sheet(isPresented: $showExtendSheet) {
                ExtendSessionSheet(isPresented: $showExtendSheet)
            }
            .sheet(isPresented: $showDisputeView) {
                DisputeView(isPresented: $showDisputeView)
            }
            .fullScreenCover(isPresented: $showReceiptView) {
                if let session = bookingViewModel.lastCompletedSession {
                    ReceiptView(session: session, isPresented: $showReceiptView)
                }
            }
            .alert("End Session?", isPresented: $showEndConfirmation) {
                Button("Cancel", role: .cancel) {}
                Button("End Session", role: .destructive) {
                    endSession()
                }
            } message: {
                Text("Are you sure you want to end your parking session? You'll be charged ₹\(Int(bookingViewModel.currentCost)).")
            }
        }
        .onAppear {
            startTimer()
        }
        .onDisappear {
            stopTimer()
        }
    }
    
    // MARK: - Status Header
    
    private var statusHeader: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Circle()
                        .fill(statusColor)
                        .frame(width: 10, height: 10)
                    
                    Text(statusText)
                        .font(.headline)
                        .foregroundColor(statusColor)
                }
                
                if let spot = currentSpot {
                    Text(spot.address)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            
            Spacer()
            
            // Parking Icon
            ZStack {
                Circle()
                    .fill(statusColor.opacity(0.1))
                    .frame(width: 50, height: 50)
                
                Image(systemName: "parkingsign")
                    .font(.title2)
                    .foregroundColor(statusColor)
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Timer Card
    
    private var timerCard: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            Text(isOverstaying ? "OVERSTAY" : "TIME REMAINING")
                .font(.caption.bold())
                .foregroundColor(.secondary)
            
            Text(formattedTimeRemaining)
                .font(.system(size: 56, weight: .bold, design: .rounded))
                .foregroundColor(timerColor)
                .contentTransition(.numericText())
            
            // Progress Bar
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 8)
                    
                    Capsule()
                        .fill(timerColor)
                        .frame(width: max(0, geometry.size.width * progress), height: 8)
                        .animation(.linear(duration: 1), value: progress)
                }
            }
            .frame(height: 8)
            
            // Time Labels
            HStack {
                Text("Started: \(formattedStartTime)")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Text("Ends: \(formattedEndTime)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(DesignSystem.Spacing.l)
        .background(
            RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
                .fill(timerColor.opacity(0.05))
                .overlay(
                    RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
                        .stroke(timerColor.opacity(0.2), lineWidth: 2)
                )
        )
    }
    
    // MARK: - Cost Card
    
    private var costCard: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("CURRENT COST")
                    .font(.caption.bold())
                    .foregroundColor(.secondary)
                
                HStack(alignment: .firstTextBaseline, spacing: 4) {
                    Text("₹")
                        .font(.title2)
                        .foregroundColor(DesignSystem.Colors.primary)
                    
                    Text(String(format: "%.2f", bookingViewModel.currentCost))
                        .font(.system(size: 36, weight: .bold, design: .rounded))
                        .foregroundColor(DesignSystem.Colors.primary)
                        .contentTransition(.numericText())
                }
                
                Text("Incl. 18% GST")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            // Overstay Warning
            if let overstayFee = bookingViewModel.overstayFee, overstayFee > 0 {
                VStack(alignment: .trailing, spacing: 4) {
                    Text("OVERSTAY FEE")
                        .font(.caption.bold())
                        .foregroundColor(DesignSystem.Colors.error)
                    
                    Text("+₹\(Int(overstayFee))")
                        .font(.title2.bold())
                        .foregroundColor(DesignSystem.Colors.error)
                }
                .padding(DesignSystem.Spacing.s)
                .background(DesignSystem.Colors.error.opacity(0.1))
                .cornerRadius(DesignSystem.Spacing.s)
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Live Map Card
    
    private var liveMapCard: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
            Text("Your Location")
                .font(.headline)
            
            Map {
                // User Location
                UserAnnotation()
                
                // Parking Spot
                if let spot = currentSpot {
                    Marker("Your Spot", coordinate: spot.coordinates)
                        .tint(DesignSystem.Colors.primary)
                }
            }
            .frame(height: 150)
            .cornerRadius(DesignSystem.Spacing.s)
            .overlay(alignment: .bottomTrailing) {
                if let distance = distanceToSpot {
                    Text(distance)
                        .font(.caption.bold())
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(.ultraThinMaterial)
                        .cornerRadius(4)
                        .padding(8)
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Quick Actions Grid
    
    private var quickActionsGrid: some View {
        LazyVGrid(columns: [
            GridItem(.flexible()),
            GridItem(.flexible()),
            GridItem(.flexible())
        ], spacing: DesignSystem.Spacing.m) {
            QuickActionButton(icon: "arrow.clockwise", title: "Extend") {
                showExtendSheet = true
            }
            
            QuickActionButton(icon: "qrcode", title: "Show QR") {
                // Show QR code again
            }
            
            QuickActionButton(icon: "phone.fill", title: "Call Host") {
                // Mock call action
            }
        }
    }
    
    // MARK: - Main Action Buttons
    
    private var mainActionButtons: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            // End Session Button
            Button {
                showEndConfirmation = true
            } label: {
                HStack {
                    Image(systemName: "stop.fill")
                    Text("End Session")
                        .font(.headline)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(DesignSystem.Colors.error)
                .foregroundColor(.white)
                .cornerRadius(DesignSystem.Spacing.m)
            }
            
            // Report Issue Button
            Button {
                showDisputeView = true
            } label: {
                HStack {
                    Image(systemName: "exclamationmark.triangle")
                    Text("Report Issue")
                        .font(.headline)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.gray.opacity(0.1))
                .foregroundColor(.primary)
                .cornerRadius(DesignSystem.Spacing.m)
            }
        }
    }
    
    // MARK: - Computed Properties
    
    private var currentSpot: ParkingSpot? {
        guard let session = bookingViewModel.activeSession else { return nil }
        return mapViewModel.spots.first { $0.id == session.spotID }
    }
    
    private var statusColor: Color {
        if isOverstaying {
            return DesignSystem.Colors.error
        } else if timeRemaining < 300 { // Less than 5 min
            return .orange
        }
        return DesignSystem.Colors.success
    }
    
    private var statusText: String {
        if isOverstaying {
            return "Overstaying"
        } else if timeRemaining < 300 {
            return "Ending Soon"
        }
        return "Active"
    }
    
    private var timerColor: Color {
        if isOverstaying {
            return DesignSystem.Colors.error
        } else if timeRemaining < 300 {
            return .orange
        } else if timeRemaining < 900 { // 15 min
            return .yellow
        }
        return DesignSystem.Colors.success
    }
    
    private var timeRemaining: TimeInterval {
        bookingViewModel.timeRemaining
    }
    
    private var isOverstaying: Bool {
        timeRemaining < 0
    }
    
    private var progress: CGFloat {
        guard let session = bookingViewModel.activeSession,
              let startTime = session.actualStartTime else { return 0 }
        
        let total = session.scheduledEndTime.timeIntervalSince(startTime)
        let elapsed = currentTime.timeIntervalSince(startTime)
        
        return min(1, max(0, CGFloat(elapsed / total)))
    }
    
    private var formattedTimeRemaining: String {
        let absTime = abs(timeRemaining)
        let hours = Int(absTime) / 3600
        let minutes = (Int(absTime) % 3600) / 60
        let seconds = Int(absTime) % 60
        
        let prefix = isOverstaying ? "+" : ""
        
        if hours > 0 {
            return "\(prefix)\(hours):\(String(format: "%02d", minutes)):\(String(format: "%02d", seconds))"
        }
        return "\(prefix)\(minutes):\(String(format: "%02d", seconds))"
    }
    
    private var formattedStartTime: String {
        guard let session = bookingViewModel.activeSession,
              let startTime = session.actualStartTime else { return "--:--" }
        
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: startTime)
    }
    
    private var formattedEndTime: String {
        guard let session = bookingViewModel.activeSession else { return "--:--" }
        
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: session.scheduledEndTime)
    }
    
    private var distanceToSpot: String? {
        guard let spot = currentSpot else { return nil }
        let distance = mapViewModel.distanceToSpot(spot)
        if distance < 1000 {
            return "\(Int(distance))m away"
        }
        return String(format: "%.1f km away", distance / 1000)
    }
    
    // MARK: - Methods
    
    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
            currentTime = Date()
            bookingViewModel.updateSessionMetrics()
        }
    }
    
    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }
    
    private func endSession() {
        bookingViewModel.endSession()
        
        // Haptic feedback
        UINotificationFeedbackGenerator().notificationOccurred(.success)
        
        // Show receipt
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            showReceiptView = true
        }
    }
}

// MARK: - Quick Action Button

struct QuickActionButton: View {
    let icon: String
    let title: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: DesignSystem.Spacing.s) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundColor(DesignSystem.Colors.primary)
                
                Text(title)
                    .font(.caption)
                    .foregroundColor(.primary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, DesignSystem.Spacing.m)
            .background(Color(.systemBackground))
            .cornerRadius(DesignSystem.Spacing.s)
            .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
        }
    }
}

// MARK: - Extend Session Sheet

struct ExtendSessionSheet: View {
    @Binding var isPresented: Bool
    @EnvironmentObject var bookingViewModel: BookingViewModel
    
    @State private var extensionMinutes: Double = 30
    @State private var isProcessing = false
    
    var body: some View {
        NavigationStack {
            VStack(spacing: DesignSystem.Spacing.l) {
                // Extension Duration Picker
                VStack(spacing: DesignSystem.Spacing.m) {
                    Text("Extend By")
                        .font(.headline)
                    
                    Text("\(Int(extensionMinutes)) min")
                        .font(.system(size: 48, weight: .bold, design: .rounded))
                        .foregroundColor(DesignSystem.Colors.primary)
                    
                    Slider(value: $extensionMinutes, in: 15...120, step: 15)
                        .tint(DesignSystem.Colors.primary)
                    
                    HStack {
                        Text("15 min")
                        Spacer()
                        Text("2 hours")
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)
                }
                .padding(DesignSystem.Spacing.m)
                .background(Color(.systemBackground))
                .cornerRadius(DesignSystem.Spacing.m)
                
                // Cost Preview
                HStack {
                    Text("Additional Cost")
                    Spacer()
                    Text("₹\(Int(extensionCost))")
                        .font(.headline)
                }
                .padding(DesignSystem.Spacing.m)
                .background(Color(.systemBackground))
                .cornerRadius(DesignSystem.Spacing.m)
                
                Spacer()
                
                // Confirm Button
                Button {
                    extendSession()
                } label: {
                    if isProcessing {
                        ProgressView()
                            .tint(.white)
                    } else {
                        HStack {
                            Image(systemName: "plus.circle.fill")
                            Text("Extend & Pay ₹\(Int(extensionCost))")
                        }
                    }
                }
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
                .background(DesignSystem.Colors.primary)
                .foregroundColor(.white)
                .cornerRadius(DesignSystem.Spacing.m)
                .disabled(isProcessing)
            }
            .padding(DesignSystem.Spacing.m)
            .navigationTitle("Extend Session")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Cancel") {
                        isPresented = false
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }
    
    private var extensionCost: Double {
        guard let session = bookingViewModel.activeSession,
              let spot = MockDataService.shared.parkingSpots.first(where: { $0.id == session.spotID }) else {
            return 0
        }
        let hours = extensionMinutes / 60
        return spot.pricePerHour * hours * 1.18 // Including GST
    }
    
    private func extendSession() {
        isProcessing = true
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            bookingViewModel.extendSession(by: extensionMinutes / 60)
            
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            
            isProcessing = false
            isPresented = false
        }
    }
}

// MARK: - Preview

#Preview {
    ActiveSessionView()
        .environmentObject(BookingViewModel())
        .environmentObject(MapViewModel())
}
