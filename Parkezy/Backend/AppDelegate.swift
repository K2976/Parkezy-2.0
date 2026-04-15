//
//  AppDelegate.swift
//  ParkEzy
//
//  Configures Firebase when the app launches.
//

import UIKit
import FirebaseCore

/// App delegate that initializes Firebase on launch
class AppDelegate: NSObject, UIApplicationDelegate {
    
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Initialize Firebase - must be called before using any Firebase services
        FirebaseApp.configure()
        
        return true
    }
}
