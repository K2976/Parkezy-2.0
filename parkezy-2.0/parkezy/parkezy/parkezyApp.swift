//
//  ParkezyApp.swift
//  Parkezy
//
//  Main app entry point with Supabase initialization and auth flow.
//

import SwiftUI

@main
struct ParkezyApp: App {
    // App initialization
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    
    // Auth state management
    @StateObject private var authViewModel = AuthViewModel()
    
    // Legacy ViewModels (for existing views - will be updated to use repositories)
    @StateObject private var mapViewModel = MapViewModel()
    @StateObject private var bookingViewModel = BookingViewModel()
    @StateObject private var hostViewModel = HostViewModel()
    
    // Separated ViewModels
    @StateObject private var commercialViewModel = CommercialParkingViewModel()
    @StateObject private var privateViewModel = PrivateParkingViewModel()
    
    var body: some Scene {
        WindowGroup {
            ZStack(alignment: .top) {
                // Show auth screen if not authenticated
                if authViewModel.isAuthenticated {
                    // Main app content
                    RoleSelectionView()
                        .environmentObject(authViewModel)
                        .environmentObject(mapViewModel)
                        .environmentObject(bookingViewModel)
                        .environmentObject(hostViewModel)
                        .environmentObject(commercialViewModel)
                        .environmentObject(privateViewModel)
                } else {
                    // Login/signup screen
                    AuthenticationView()
                        .environmentObject(authViewModel)
                }
                
                // Global offline banner — appears at top of all screens
                OfflineBannerView()
            }
            .task {
                await authViewModel.restoreSession()
            }
        }
    }
}
