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
    // The anon key is safe to ship in client code — Row Level Security on every
    // table is what actually enforces access control, not secrecy of this key.
    static let supabaseURLString = Secrets.supabaseURL
    static let supabaseAnonKey = Secrets.supabaseAnonKey
    
    // MARK: - Shared Client
    static let client: SupabaseClient = {
        guard let url = URL(string: supabaseURLString) else {
            preconditionFailure("⚠️ Invalid Supabase URL: \(supabaseURLString). Set supabaseURL in Secrets.swift.")
        }
        return SupabaseClient(supabaseURL: url, supabaseKey: supabaseAnonKey)
    }()
    
    private init() {}
}
