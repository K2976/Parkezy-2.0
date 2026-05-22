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
    static let supabaseURL = URL(string: "https://PLACEHOLDER_SUPABASE_PROJECT_URL.supabase.co")!
    static let supabaseAnonKey = "PLACEHOLDER_SUPABASE_ANON_KEY"
    
    // MARK: - Shared Client
    static let client = SupabaseClient(
        supabaseURL: supabaseURL,
        supabaseKey: supabaseAnonKey
    )
    
    private init() {}
}
