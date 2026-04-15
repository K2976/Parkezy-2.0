//
//  ParkingLiveActivity.swift
//  ParkEzy
//
//  Live Activity for parking session monitoring on Lock Screen and Dynamic Island
//

import ActivityKit
import WidgetKit
import SwiftUI
import Combine

// MARK: - Activity Attributes

struct ParkingActivityAttributes: ActivityAttributes {
    // Static data that doesn't change during the activity
    public struct ContentState: Codable, Hashable {
        var timeRemaining: TimeInterval
        var currentCost: Double
        var isOverstaying: Bool
    }
    
    // Activity metadata
    let spotAddress: String
    let endTime: Date
    let sessionID: String
}

// MARK: - Live Activity Manager

@MainActor
class LiveActivityManager: ObservableObject {
    // MARK: - Singleton
    
    static let shared = LiveActivityManager()
    
    // MARK: - Properties
    
    @Published var currentActivity: Activity<ParkingActivityAttributes>?
    
    // MARK: - Check Availability
    
    var areActivitiesEnabled: Bool {
        ActivityAuthorizationInfo().areActivitiesEnabled
    }
    
    // MARK: - Start Activity
    
    func startActivity(
        spotAddress: String,
        endTime: Date,
        sessionID: String,
        initialCost: Double
    ) {
        guard areActivitiesEnabled else {
            print("⚠️ Live Activities not enabled")
            return
        }
        
        let attributes = ParkingActivityAttributes(
            spotAddress: spotAddress,
            endTime: endTime,
            sessionID: sessionID
        )
        
        let initialState = ParkingActivityAttributes.ContentState(
            timeRemaining: endTime.timeIntervalSinceNow,
            currentCost: initialCost,
            isOverstaying: false
        )
        
        let content = ActivityContent(
            state: initialState,
            staleDate: nil
        )
        
        do {
            currentActivity = try Activity.request(
                attributes: attributes,
                content: content,
                pushType: nil
            )
            print("🔴 Live Activity started: \(currentActivity?.id ?? "unknown")")
        } catch {
            print("❌ Failed to start Live Activity: \(error.localizedDescription)")
        }
    }
    
    // MARK: - Update Activity
    
    func updateActivity(timeRemaining: TimeInterval, currentCost: Double) {
        guard let activity = currentActivity else { return }
        
        let isOverstaying = timeRemaining < 0
        
        let updatedState = ParkingActivityAttributes.ContentState(
            timeRemaining: timeRemaining,
            currentCost: currentCost,
            isOverstaying: isOverstaying
        )
        
        let content = ActivityContent(
            state: updatedState,
            staleDate: nil
        )
        
        Task {
            await activity.update(content)
        }
    }
    
    // MARK: - End Activity
    
    func endActivity(finalCost: Double) {
        guard let activity = currentActivity else { return }
        
        let finalState = ParkingActivityAttributes.ContentState(
            timeRemaining: 0,
            currentCost: finalCost,
            isOverstaying: false
        )
        
        let content = ActivityContent(
            state: finalState,
            staleDate: nil
        )
        
        Task {
            await activity.end(content, dismissalPolicy: .default)
            currentActivity = nil
            print("⚪ Live Activity ended")
        }
    }
    
    // MARK: - Cancel All
    
    func cancelAllActivities() {
        Task {
            for activity in Activity<ParkingActivityAttributes>.activities {
                await activity.end(nil, dismissalPolicy: .immediate)
            }
            currentActivity = nil
        }
    }
}

// MARK: - Live Activity Widget (WidgetKit Extension)

// NOTE: This struct would be in the Widget extension target
// Here for reference - actual implementation needs Widget target

/*
struct ParkingLiveActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: ParkingActivityAttributes.self) { context in
            // Lock Screen UI
            LockScreenView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                // Expanded Region
                DynamicIslandExpandedRegion(.leading) {
                    HStack {
                        Image(systemName: "parkingsign.circle.fill")
                            .foregroundColor(.blue)
                        Text(context.attributes.spotAddress)
                            .font(.caption)
                            .lineLimit(1)
                    }
                }
                
                DynamicIslandExpandedRegion(.trailing) {
                    Text("₹\(Int(context.state.currentCost))")
                        .font(.headline)
                        .foregroundColor(.green)
                }
                
                DynamicIslandExpandedRegion(.center) {
                    Text(formatTime(context.state.timeRemaining))
                        .font(.system(size: 32, weight: .bold, design: .rounded))
                        .foregroundColor(context.state.isOverstaying ? .red : .primary)
                }
                
                DynamicIslandExpandedRegion(.bottom) {
                    Button(intent: ExtendParkingIntent()) {
                        Label("Extend +30 min", systemImage: "plus.circle.fill")
                    }
                    .tint(.blue)
                }
            } compactLeading: {
                // Compact Leading
                Image(systemName: "parkingsign")
                    .foregroundColor(.blue)
            } compactTrailing: {
                // Compact Trailing
                Text(formatTimeCompact(context.state.timeRemaining))
                    .font(.caption.bold())
                    .foregroundColor(context.state.isOverstaying ? .red : .primary)
            } minimal: {
                // Minimal (single icon)
                Image(systemName: context.state.isOverstaying ? "exclamationmark.triangle.fill" : "parkingsign")
                    .foregroundColor(context.state.isOverstaying ? .red : .blue)
            }
        }
    }
    
    private func formatTime(_ seconds: TimeInterval) -> String {
        let absSeconds = abs(seconds)
        let hours = Int(absSeconds) / 3600
        let minutes = (Int(absSeconds) % 3600) / 60
        let secs = Int(absSeconds) % 60
        
        let prefix = seconds < 0 ? "+" : ""
        
        if hours > 0 {
            return "\(prefix)\(hours):\(String(format: "%02d", minutes)):\(String(format: "%02d", secs))"
        }
        return "\(prefix)\(minutes):\(String(format: "%02d", secs))"
    }
    
    private func formatTimeCompact(_ seconds: TimeInterval) -> String {
        let absSeconds = abs(seconds)
        let minutes = Int(absSeconds) / 60
        
        let prefix = seconds < 0 ? "+" : ""
        return "\(prefix)\(minutes)m"
    }
}
*/

// MARK: - Lock Screen View

struct LockScreenLiveActivityView: View {
    let spotAddress: String
    let endTime: Date
    let timeRemaining: TimeInterval
    let currentCost: Double
    let isOverstaying: Bool
    
    var body: some View {
        HStack(spacing: 16) {
            // Timer Section
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: "parkingsign.circle.fill")
                        .foregroundColor(.blue)
                    Text("ParkEzy")
                        .font(.caption.bold())
                }
                
                Text(formatTime(timeRemaining))
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundColor(isOverstaying ? .red : .primary)
                
                Text(spotAddress)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
            
            Spacer()
            
            // Cost Section
            VStack(alignment: .trailing, spacing: 4) {
                Text("Current Cost")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Text("₹\(Int(currentCost))")
                    .font(.title2.bold())
                    .foregroundColor(.green)
                
                // Extend Button
                Link(destination: URL(string: "parkezy://extend")!) {
                    Label("Extend", systemImage: "plus.circle.fill")
                        .font(.caption.bold())
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(.blue)
                        .foregroundColor(.white)
                        .cornerRadius(16)
                }
            }
        }
        .padding()
        .background(.regularMaterial)
    }
    
    private func formatTime(_ seconds: TimeInterval) -> String {
        let absSeconds = abs(seconds)
        let hours = Int(absSeconds) / 3600
        let minutes = (Int(absSeconds) % 3600) / 60
        let secs = Int(absSeconds) % 60
        
        let prefix = seconds < 0 ? "+" : ""
        
        if hours > 0 {
            return "\(prefix)\(hours):\(String(format: "%02d", minutes)):\(String(format: "%02d", secs))"
        }
        return "\(prefix)\(minutes):\(String(format: "%02d", secs))"
    }
}

// MARK: - Demo View (For Simulator)

struct LiveActivityDemoView: View {
    @State private var demoTimeRemaining: TimeInterval = 3600 // 1 hour
    @State private var demoCost: Double = 59.0
    @State private var isRunning = false
    @State private var timer: Timer?
    
    var body: some View {
        VStack(spacing: 24) {
            Text("Live Activity Demo")
                .font(.headline)
            
            Text("⚠️ Live Activities don't animate in Simulator")
                .font(.caption)
                .foregroundColor(.secondary)
            
            // Mock Lock Screen View
            LockScreenLiveActivityView(
                spotAddress: "Select Citywalk, Saket",
                endTime: Date().addingTimeInterval(demoTimeRemaining),
                timeRemaining: demoTimeRemaining,
                currentCost: demoCost,
                isOverstaying: demoTimeRemaining < 0
            )
            .cornerRadius(16)
            .shadow(radius: 10)
            .padding()
            
            // Controls
            HStack(spacing: 16) {
                Button(isRunning ? "Pause" : "Start") {
                    toggleTimer()
                }
                .buttonStyle(.borderedProminent)
                
                Button("Skip 5 min") {
                    demoTimeRemaining -= 300
                    demoCost += 5
                }
                .buttonStyle(.bordered)
                
                Button("Reset") {
                    demoTimeRemaining = 3600
                    demoCost = 59.0
                }
                .buttonStyle(.bordered)
            }
        }
        .padding()
        .onDisappear {
            timer?.invalidate()
        }
    }
    
    private func toggleTimer() {
        if isRunning {
            timer?.invalidate()
            isRunning = false
        } else {
            timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
                demoTimeRemaining -= 1
                demoCost += 0.0167 // ~₹60/hour
            }
            isRunning = true
        }
    }
}

#Preview {
    LiveActivityDemoView()
}
