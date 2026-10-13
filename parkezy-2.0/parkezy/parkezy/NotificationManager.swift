//
//  NotificationManager.swift
//  ParkEzy
//
//  Local notification management for parking alerts
//

import Foundation
import UserNotifications

class NotificationManager {
    // MARK: - Singleton
    
    static let shared = NotificationManager()
    
    // MARK: - Private Properties
    
    private let notificationCenter = UNUserNotificationCenter.current()
    
    // MARK: - Initialization
    
    private init() {}
    
    // MARK: - Authorization
    
    func requestAuthorization(completion: @escaping (Bool) -> Void) {
        notificationCenter.requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
            if let error = error {
                print("❌ Notification authorization error: \(error.localizedDescription)")
            }
            
            DispatchQueue.main.async {
                completion(granted)
            }
        }
    }
    
    // MARK: - Schedule Notifications
    
    func scheduleNotification(title: String, body: String, delay: TimeInterval) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: max(0.1, delay), repeats: false)
        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: trigger
        )
        
        notificationCenter.add(request) { error in
            if let error = error {
                print("❌ Failed to schedule notification: \(error.localizedDescription)")
            }
        }
    }
    
    // MARK: - Parking Session Notifications
    
    func scheduleSessionWarnings(for session: BookingSession) {
        // 15 minute warning
        let fifteenMinWarning = session.scheduledEndTime.addingTimeInterval(-15 * 60)
        if fifteenMinWarning > Date() {
            scheduleNotification(
                at: fifteenMinWarning,
                title: "⚠️ 15 Minutes Remaining",
                body: "Your parking session ends soon. Consider extending.",
                identifier: "warning-15-\(session.id.uuidString)"
            )
        }
        
        // 5 minute warning
        let fiveMinWarning = session.scheduledEndTime.addingTimeInterval(-5 * 60)
        if fiveMinWarning > Date() {
            scheduleNotification(
                at: fiveMinWarning,
                title: "🚨 5 Minutes Remaining!",
                body: "Your parking session is about to end. Extend now to avoid overstay fees.",
                identifier: "warning-5-\(session.id.uuidString)"
            )
        }
        
        // Session ended
        scheduleNotification(
            at: session.scheduledEndTime,
            title: "🛑 Session Ended",
            body: "Your parking session has ended. Overstay fees now apply (₹20/15 min).",
            identifier: "ended-\(session.id.uuidString)"
        )
    }
    
    func cancelSessionWarnings(for session: BookingSession) {
        let identifiers = [
            "warning-15-\(session.id.uuidString)",
            "warning-5-\(session.id.uuidString)",
            "ended-\(session.id.uuidString)"
        ]
        
        notificationCenter.removePendingNotificationRequests(withIdentifiers: identifiers)
    }
    
    // MARK: - Private Methods
    
    private func scheduleNotification(at date: Date, title: String, body: String, identifier: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        content.interruptionLevel = .timeSensitive
        
        let components = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute, .second], from: date)
        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
        
        let request = UNNotificationRequest(identifier: identifier, content: content, trigger: trigger)
        
        notificationCenter.add(request) { error in
            if let error = error {
                print("❌ Failed to schedule notification: \(error.localizedDescription)")
            }
        }
    }
    
    // MARK: - Clear All
    
    func clearAllNotifications() {
        notificationCenter.removeAllPendingNotificationRequests()
        notificationCenter.removeAllDeliveredNotifications()
    }
}
