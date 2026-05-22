//
//  FindParkingIntent.swift
//  ParkEzy
//
//  Siri Shortcuts for hands-free parking operations
//

import AppIntents
import CoreLocation

// MARK: - Find Parking Intent

struct FindParkingIntent: AppIntent {
    static var title: LocalizedStringResource = "Find Parking Near Me"
    static var description = IntentDescription("Opens ParkEzy and shows nearby parking spots")
    
    static var openAppWhenRun: Bool = true
    
    func perform() async throws -> some IntentResult & OpensIntent {
        // Deep link to map view
        return .result(opensIntent: OpenURLIntent(URL(string: "parkezy://find")!))
    }
}

// MARK: - Show Timer Intent

struct ShowParkingTimerIntent: AppIntent {
    static var title: LocalizedStringResource = "Show My Parking Timer"
    static var description = IntentDescription("Shows your current parking session timer")
    
    static var openAppWhenRun: Bool = true
    
    func perform() async throws -> some IntentResult & OpensIntent {
        // Deep link to active session
        return .result(opensIntent: OpenURLIntent(URL(string: "parkezy://active-session")!))
    }
}

// MARK: - Extend Parking Intent

struct ExtendParkingIntent: AppIntent {
    static var title: LocalizedStringResource = "Extend Parking"
    static var description = IntentDescription("Extends your current parking session by 30 minutes")
    
    @Parameter(title: "Duration (minutes)")
    var duration: Int?
    
    static var openAppWhenRun: Bool = false
    
    func perform() async throws -> some IntentResult & ProvidesDialog {
        // In production, this would call the booking service
        let minutes = duration ?? 30
        
        return .result(dialog: "Extended your parking by \(minutes) minutes. New total: ₹89")
    }
}

// MARK: - Check Parking Status Intent

struct CheckParkingStatusIntent: AppIntent {
    static var title: LocalizedStringResource = "Check Parking Status"
    static var description = IntentDescription("Check how much time is left in your parking session")
    
    static var openAppWhenRun: Bool = false
    
    func perform() async throws -> some IntentResult & ProvidesDialog {
        // In production, read from shared storage
        // For demo, return mock data
        
        let hasSession = true // Read from App Groups
        
        if hasSession {
            return .result(dialog: "You have 45 minutes remaining at Select Citywalk, Saket. Current cost: ₹59")
        } else {
            return .result(dialog: "You don't have an active parking session. Say 'Find parking near me' to get started.")
        }
    }
}

// MARK: - App Shortcuts Provider

//struct ParkEzyShortcuts: AppShortcutsProvider {
//    static var appShortcuts: [AppShortcut] {
//        AppShortcut(
//            intent: FindParkingIntent(),
//            phrases: [
//                "Find parking with \(.applicationName)",
//                "Find parking near me with \(.applicationName)",
//                "Search for parking in \(.applicationName)",
//                "Open \(.applicationName) map"
//            ],
//            shortTitle: "Find Parking",
//            systemImageName: "parkingsign.circle.fill"
//        )
//        
//        AppShortcut(
//            intent: ShowParkingTimerIntent(),
//            phrases: [
//                "Show my parking timer in \(.applicationName)",
//                "How much parking time do I have left",
//                "Check my parking in \(.applicationName)",
//                "Open my parking session"
//            ],
//            shortTitle: "Parking Timer",
//            systemImageName: "timer"
//        )
//        
//        AppShortcut(
//            intent: ExtendParkingIntent(),
//            phrases: [
//                "Extend my parking with \(.applicationName)",
//                "Add 30 minutes to my parking",
//                "Extend parking session"
//            ],
//            shortTitle: "Extend Parking",
//            systemImageName: "plus.circle.fill"
//        )
//        
//        AppShortcut(
//            intent: CheckParkingStatusIntent(),
//            phrases: [
//                "Check parking status with \(.applicationName)",
//                "What's my parking status",
//                "How long until my parking expires"
//            ],
//            shortTitle: "Check Status",
//            systemImageName: "info.circle"
//        )
//    }
//}

// MARK: - Deep Link Handler

enum DeepLink: String {
    case find = "parkezy://find"
    case activeSession = "parkezy://active-session"
    case extend = "parkezy://extend"
    case booking = "parkezy://booking"
    
    static func handle(_ url: URL) {
        guard let deepLink = DeepLink(rawValue: url.absoluteString) else {
            print("❌ Unknown deep link: \(url)")
            return
        }
        
        switch deepLink {
        case .find:
            print("🔗 Navigate to map view")
        case .activeSession:
            print("🔗 Navigate to active session")
        case .extend:
            print("🔗 Open extend session sheet")
        case .booking:
            // Parse booking ID from query params
            print("🔗 Navigate to booking details")
        }
    }
}
