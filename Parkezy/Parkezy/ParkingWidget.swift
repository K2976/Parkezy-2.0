//
//  ParkingWidget.swift
//  ParkEzy
//
//  Home Screen widget showing active parking session
//

import WidgetKit
import SwiftUI
import AppIntents

// MARK: - Widget Entry

struct ParkingWidgetEntry: TimelineEntry {
    let date: Date
    let configuration: ConfigurationAppIntent
    
    // Session data
    let hasActiveSession: Bool
    let spotAddress: String
    let endTime: Date
    let timeRemaining: TimeInterval
    let currentCost: Double
    let isOverstaying: Bool
}

// MARK: - Configuration Intent

struct ConfigurationAppIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Configuration"
    static var description = IntentDescription("ParkEzy Widget Configuration")
}

// MARK: - Timeline Provider

struct ParkingWidgetProvider: AppIntentTimelineProvider {
    typealias Entry = ParkingWidgetEntry
    typealias Intent = ConfigurationAppIntent
    
    func placeholder(in context: Context) -> Entry {
        ParkingWidgetEntry(
            date: Date(),
            configuration: ConfigurationAppIntent(),
            hasActiveSession: true,
            spotAddress: "Select Citywalk, Saket",
            endTime: Date().addingTimeInterval(3600),
            timeRemaining: 3600,
            currentCost: 59.0,
            isOverstaying: false
        )
    }
    
    func snapshot(for configuration: ConfigurationAppIntent, in context: Context) async -> Entry {
        // Return current state for snapshots
        return placeholder(in: context)
    }
    
    func timeline(for configuration: ConfigurationAppIntent, in context: Context) async -> Timeline<Entry> {
        var entries: [Entry] = []
        let currentDate = Date()
        
        // In production, read from App Groups shared storage
        // For demo, we'll show a mock active session
        let hasSession = true // UserDefaults(suiteName: "group.com.parkezy.shared")?.bool(forKey: "hasActiveSession") ?? false
        
        if hasSession {
            // Generate entries every minute for the next hour
            for minuteOffset in stride(from: 0, to: 60, by: 1) {
                let entryDate = Calendar.current.date(byAdding: .minute, value: minuteOffset, to: currentDate)!
                let endTime = currentDate.addingTimeInterval(3600) // Mock 1 hour session
                let timeRemaining = endTime.timeIntervalSince(entryDate)
                
                let entry = ParkingWidgetEntry(
                    date: entryDate,
                    configuration: configuration,
                    hasActiveSession: true,
                    spotAddress: "Select Citywalk, Saket",
                    endTime: endTime,
                    timeRemaining: timeRemaining,
                    currentCost: 59.0 + Double(minuteOffset) * 1.0,
                    isOverstaying: timeRemaining < 0
                )
                entries.append(entry)
            }
        } else {
            // No active session
            let entry = ParkingWidgetEntry(
                date: currentDate,
                configuration: configuration,
                hasActiveSession: false,
                spotAddress: "",
                endTime: Date(),
                timeRemaining: 0,
                currentCost: 0,
                isOverstaying: false
            )
            entries.append(entry)
        }
        
        return Timeline(entries: entries, policy: .atEnd)
    }
}

// MARK: - Widget View

struct ParkingWidgetEntryView: View {
    var entry: ParkingWidgetEntry
    @Environment(\.widgetFamily) var family
    
    var body: some View {
        if entry.hasActiveSession {
            activeSessionView
        } else {
            noSessionView
        }
    }
    
    // MARK: - Active Session View
    
    @ViewBuilder
    private var activeSessionView: some View {
        switch family {
        case .systemSmall:
            smallActiveView
        case .systemMedium:
            mediumActiveView
        default:
            smallActiveView
        }
    }
    
    private var smallActiveView: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "parkingsign.circle.fill")
                    .foregroundColor(.blue)
                Text("ParkEzy")
                    .font(.caption.bold())
            }
            
            Text(formatTime(entry.timeRemaining))
                .font(.system(size: 28, weight: .bold, design: .rounded))
                .foregroundColor(entry.isOverstaying ? .red : .primary)
            
            Text("₹\(Int(entry.currentCost))")
                .font(.headline)
                .foregroundColor(.green)
            
            Text(entry.spotAddress)
                .font(.caption2)
                .foregroundColor(.secondary)
                .lineLimit(1)
        }
        .padding()
        .containerBackground(.fill, for: .widget)
    }
    
    private var mediumActiveView: some View {
        HStack(spacing: 16) {
            // Timer Section
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: "parkingsign.circle.fill")
                        .foregroundColor(.blue)
                    Text("Active Session")
                        .font(.caption.bold())
                }
                
                Text(formatTime(entry.timeRemaining))
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundColor(entry.isOverstaying ? .red : .primary)
                
                Text(entry.spotAddress)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
            
            Spacer()
            
            // Cost & Action
            VStack(alignment: .trailing, spacing: 8) {
                VStack(alignment: .trailing, spacing: 2) {
                    Text("Current Cost")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Text("₹\(Int(entry.currentCost))")
                        .font(.title.bold())
                        .foregroundColor(.green)
                }
                
                // Deep link to extend
                Link(destination: URL(string: "parkezy://extend")!) {
                    HStack(spacing: 4) {
                        Image(systemName: "plus.circle.fill")
                        Text("Extend")
                    }
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
        .containerBackground(.fill, for: .widget)
    }
    
    // MARK: - No Session View
    
    private var noSessionView: some View {
        VStack(spacing: 12) {
            Image(systemName: "parkingsign.circle")
                .font(.system(size: 40))
                .foregroundColor(.blue.opacity(0.5))
            
            Text("No Active Session")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Link(destination: URL(string: "parkezy://find")!) {
                HStack {
                    Image(systemName: "magnifyingglass")
                    Text("Find Parking")
                }
                .font(.caption.bold())
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(.blue)
                .foregroundColor(.white)
                .cornerRadius(16)
            }
        }
        .padding()
        .containerBackground(.fill, for: .widget)
    }
    
    // MARK: - Helpers
    
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

// MARK: - Widget Configuration

struct ParkingWidget: Widget {
    let kind: String = "ParkingWidget"
    
    var body: some WidgetConfiguration {
        AppIntentConfiguration(
            kind: kind,
            intent: ConfigurationAppIntent.self,
            provider: ParkingWidgetProvider()
        ) { entry in
            ParkingWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("Parking Session")
        .description("View your active parking session at a glance.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

// MARK: - Widget Bundle

struct ParkingWidgetBundle: WidgetBundle {
    var body: some Widget {
        ParkingWidget()
    }
}

// MARK: - Preview

#Preview(as: .systemMedium) {
    ParkingWidget()
} timeline: {
    ParkingWidgetEntry(
        date: Date(),
        configuration: ConfigurationAppIntent(),
        hasActiveSession: true,
        spotAddress: "Select Citywalk, Saket",
        endTime: Date().addingTimeInterval(1800),
        timeRemaining: 1800,
        currentCost: 59.0,
        isOverstaying: false
    )
    
    ParkingWidgetEntry(
        date: Date().addingTimeInterval(1800),
        configuration: ConfigurationAppIntent(),
        hasActiveSession: true,
        spotAddress: "Select Citywalk, Saket",
        endTime: Date().addingTimeInterval(1800),
        timeRemaining: 0,
        currentCost: 89.0,
        isOverstaying: false
    )
    
    ParkingWidgetEntry(
        date: Date().addingTimeInterval(2100),
        configuration: ConfigurationAppIntent(),
        hasActiveSession: true,
        spotAddress: "Select Citywalk, Saket",
        endTime: Date().addingTimeInterval(1800),
        timeRemaining: -300,
        currentCost: 109.0,
        isOverstaying: true
    )
}
