//
//  AppDelegate.swift
//  ParkEzy
//
//  Configures Firebase when the app launches.
//

import UIKit
import Supabase
/// App delegate that initializes on launch
class AppDelegate: NSObject, UIApplicationDelegate {
    
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Test Supabase connection on launch
        Task {
            let _ = try? await SupabaseConfig.client.auth.session
        }
        return true
    }
}
