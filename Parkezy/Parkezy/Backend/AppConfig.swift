//
//  AppConfig.swift
//  ParkEzy
//
//  App-wide configuration for backend environment.
//

import Foundation

/// Global app configuration
struct AppConfig {
    
    // MARK: - Supabase Environment Configuration
    
    /// True if Supabase keys are configured, otherwise app uses mock data
    static var useSupabase: Bool {
        #if DEBUG
        return _useSupabaseOverride ?? hasSupabaseConfig
        #else
        return hasSupabaseConfig
        #endif
    }
    
    /// Override for testing (DEBUG only)
    static var _useSupabaseOverride: Bool? = false
    
    /// Check if Supabase placeholders have been replaced
    private static var hasSupabaseConfig: Bool {
        // If the URL still contains "PLACEHOLDER", it's not configured
        !SupabaseConfig.supabaseURLString.contains("PLACEHOLDER")
    }
    
    // MARK: - App Links
    
    /// Privacy Policy URL Placeholder
    static let privacyPolicyURL = "YOUR_PRIVACY_POLICY_URL"
}
