//
//  SupabaseConfig.swift
//  ParkEzy
//
//  Supabase Client Configuration
//

import Foundation
import Supabase

/// Singleton configuration for Supabase
final class SupabaseConfig {
    
    // MARK: - Supabase Credentials
    // ⚠️ These are placeholder keys. DO NOT commit real keys to source control.
    // Fill these in manually in your local environment.
    private static let supabaseURLString = "https://PLACEHOLDER_SUPABASE_PROJECT_URL.supabase.co"
    static let supabaseAnonKey = "PLACEHOLDER_SUPABASE_ANON_KEY"
    
    // MARK: - Shared Client
    static let client: SupabaseClient = {
        guard let url = URL(string: supabaseURLString) else {
            preconditionFailure("⚠️ Invalid Supabase URL: \(supabaseURLString). Update SupabaseConfig.swift with your project URL.")
        }
        return SupabaseClient(supabaseURL: url, supabaseKey: supabaseAnonKey)
    }()
    
    private init() {}
}
