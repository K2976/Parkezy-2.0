//
//  AppConfig.swift
//  ParkEzy
//
//  App-wide configuration for switching between mock data and Firebase.
//  Set useFirebase to true when Firebase is configured.
//

import Foundation

/// Global app configuration
struct AppConfig {
    /// Set to true to use Firebase backend, false for mock data
    /// Change this to true once GoogleService-Info.plist is added
    static var useFirebase: Bool {
        // Check if Firebase is properly configured
        #if DEBUG
        // In debug, allow mock data for testing
        return _useFirebaseOverride ?? hasFirebaseConfig
        #else
        // In release, always try to use Firebase
        return hasFirebaseConfig
        #endif
    }
    
    /// Override for testing (DEBUG only)
    static var _useFirebaseOverride: Bool?
    
    /// Check if GoogleService-Info.plist exists
    private static var hasFirebaseConfig: Bool {
        Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist") != nil
    }
}

