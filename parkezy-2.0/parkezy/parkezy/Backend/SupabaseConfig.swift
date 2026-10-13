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
    static let supabaseURLString = "https://zhpwqvetlpktlvcitygh.supabase.co"
    static let supabaseAnonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpocHdxdmV0bHBrdGx2Y2l0eWdoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0MzE1MzAsImV4cCI6MjA5NTAwNzUzMH0.hfJqRaYGrKJOFp9Rlce2BRsNjNHOfuLIlMCG_irbG6I"
    
    // MARK: - Shared Client
    static let client: SupabaseClient = {
        guard let url = URL(string: supabaseURLString) else {
            preconditionFailure("⚠️ Invalid Supabase URL: \(supabaseURLString). Update SupabaseConfig.swift with your project URL.")
        }
        return SupabaseClient(supabaseURL: url, supabaseKey: supabaseAnonKey)
    }()
    
    private init() {}
}
