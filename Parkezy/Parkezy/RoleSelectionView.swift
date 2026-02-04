//
//  RoleSelectionView.swift
//  ParkEzy
//
//  Landing page for role selection (Driver vs Host mode)
//

import SwiftUI

struct RoleSelectionView: View {
    // MARK: - State
    
    @State private var selectedRole: UserRole = .driver
    @State private var navigateToRole = false
    @State private var showOnboarding = false
    
    // MARK: - Environment
    
    @EnvironmentObject var authViewModel: AuthViewModel
    @EnvironmentObject var mapViewModel: MapViewModel
    @EnvironmentObject var bookingViewModel: BookingViewModel
    @EnvironmentObject var hostViewModel: HostViewModel
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            ZStack {
                // Background Image
                GeometryReader { geometry in
                    Image("parking_city_bg")
                        .resizable()
                        .scaledToFill()
                        .frame(width: geometry.size.width, height: geometry.size.height)
                        .clipped()
                        .overlay(
                            LinearGradient(
                                colors: [.black.opacity(0.7), .black.opacity(0.2), .black.opacity(0.4)],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                }
                .ignoresSafeArea()
                
                VStack(spacing: DesignSystem.Spacing.xl) {
                    // MARK: - Header
                    
                    VStack(spacing: DesignSystem.Spacing.s) {
                        Image(systemName: "parkingsign.circle.fill")
                            .font(.system(size: 80))
                            .foregroundColor(.white)
                            .shadow(color: .black.opacity(0.5), radius: 20, x: 0, y: 10)
                        
                        Text("ParkEzy")
                            .font(.system(size: 48, weight: .bold, design: .rounded))
                            .foregroundColor(.white)
                            .shadow(color: .black.opacity(0.5), radius: 4, x: 0, y: 2)
                        
                        //Text("Your Smart Parking Solution")
                            .font(.title3)
                            .fontWeight(.medium)
                            .foregroundColor(.white.opacity(0.95))
                            .shadow(color: .black.opacity(0.5), radius: 2, x: 0, y: 1)
                    }
                    .padding(.top, DesignSystem.Spacing.xxl)
                    
                    Spacer()
                    
                    // MARK: - Role Cards
                    
                    VStack(spacing: DesignSystem.Spacing.l) {
                        // Driver Card
                        RoleCard(
                            role: .driver,
                            icon: "car.fill",
                            title: "Driver Mode",
                            subtitle: "Find & book parking spots",
                            isSelected: selectedRole == .driver
                        ) {
                            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                                selectedRole = .driver
                            }
                        }
                        
                        // Host Card
                        RoleCard(
                            role: .host,
                            icon: "building.2.fill",
                            title: "Host Mode",
                            subtitle: "Manage your parking spaces",
                            isSelected: selectedRole == .host
                        ) {
                            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                                selectedRole = .host
                            }
                        }
                    }
                    .padding(.horizontal, DesignSystem.Spacing.l)
                    
                    Spacer()
                    
                    // MARK: - Continue Button
                    
                    Button {
                        withAnimation {
                            navigateToRole = true
                        }
                    } label: {
                        HStack {
                            Text("Continue")
                                .font(.headline)
                            Image(systemName: "arrow.right")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.white)
                        .foregroundColor(DesignSystem.Colors.primary)
                        .cornerRadius(DesignSystem.Spacing.m)
                        .shadow(color: .black.opacity(0.2), radius: 10, x: 0, y: 5)
                    }
                    .padding(.horizontal, DesignSystem.Spacing.l)
                    .padding(.bottom, DesignSystem.Spacing.l)
                }
            }
            .navigationDestination(isPresented: $navigateToRole) {
                destinationView
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        authViewModel.signOut()
                    } label: {
                        Image(systemName: "rectangle.portrait.and.arrow.right")
                            .font(.title3)
                            .foregroundColor(.white)
                            .padding(10)
                            .background(Color.white.opacity(0.2))
                            .clipShape(Circle())
                    }
                }
            }
        }
    }
    
    // MARK: - Destination View
    
    @ViewBuilder
    private var destinationView: some View {
        switch selectedRole {
        case .driver:
            UnifiedMapView()
                .navigationBarBackButtonHidden(false)
        case .host:
            UnifiedHostDashboardView()
                .navigationBarBackButtonHidden(false)
        }
    }
}

// MARK: - Host Type Selection View

struct HostTypeSelectionView: View {
    @EnvironmentObject var hostViewModel: HostViewModel
    @EnvironmentObject var privateViewModel: PrivateParkingViewModel
    
    @State private var selectedHostType: HostType = .privateParking
    @State private var navigateToDashboard = false
    
    enum HostType {
        case commercial
        case privateParking
    }
    
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [.orange.opacity(0.8), .pink.opacity(0.6)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
            
            VStack(spacing: DesignSystem.Spacing.xl) {
                Text("What type of parking\ndo you manage?")
                    .font(.title.bold())
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)
                    .padding(.top, DesignSystem.Spacing.xxl)
                
                Spacer()
                
                VStack(spacing: DesignSystem.Spacing.l) {
                    HostTypeCard(
                        icon: "building.2.fill",
                        title: "Commercial",
                        subtitle: "Mall, Office, Hospital, Airport",
                        isSelected: selectedHostType == .commercial
                    ) {
                        withAnimation(.spring()) {
                            selectedHostType = .commercial
                        }
                    }
                    
                    HostTypeCard(
                        icon: "house.fill",
                        title: "Private",
                        subtitle: "Home driveway, Garage",
                        isSelected: selectedHostType == .privateParking
                    ) {
                        withAnimation(.spring()) {
                            selectedHostType = .privateParking
                        }
                    }
                }
                .padding(.horizontal, DesignSystem.Spacing.l)
                
                Spacer()
                
                Button {
                    navigateToDashboard = true
                } label: {
                    HStack {
                        Text("Continue")
                            .font(.headline)
                        Image(systemName: "arrow.right")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.white)
                    .foregroundColor(.orange)
                    .cornerRadius(DesignSystem.Spacing.m)
                }
                .padding(.horizontal, DesignSystem.Spacing.l)
                .padding(.bottom, DesignSystem.Spacing.l)
            }
        }
        .navigationDestination(isPresented: $navigateToDashboard) {
            // Both types now use the unified dashboard with toggle
            UnifiedHostDashboardView()
        }
        .navigationTitle("Host Type")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Host Type Card

struct HostTypeCard: View {
    let icon: String
    let title: String
    let subtitle: String
    let isSelected: Bool
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack(spacing: DesignSystem.Spacing.m) {
                Image(systemName: icon)
                    .font(.title)
                    .foregroundColor(isSelected ? .white : .orange)
                    .frame(width: 50, height: 50)
                    .background(isSelected ? Color.orange : Color.orange.opacity(0.2))
                    .cornerRadius(12)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.headline)
                        .foregroundColor(.primary)
                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.orange)
                        .font(.title2)
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(Color.white)
            .cornerRadius(16)
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(isSelected ? Color.orange : Color.clear, lineWidth: 3)
            )
            .shadow(color: .black.opacity(0.05), radius: 5)
        }
    }
}

// MARK: - Role Card Component

struct RoleCard: View {
    let role: UserRole
    let icon: String
    let title: String
    let subtitle: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: DesignSystem.Spacing.m) {
                // Icon
                Image(systemName: icon)
                    .font(.system(size: 40))
                    .foregroundColor(isSelected ? DesignSystem.Colors.primary : .gray)
                    .frame(width: 60, height: 60)
                    .background(
                        Circle()
                            .fill(isSelected ? Color.white : Color.white.opacity(0.3))
                    )
                
                // Text
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.title2.bold())
                        .foregroundColor(.white)
                    Text(subtitle)
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.8))
                }
                
                Spacer()
                
                // Selection Indicator
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.title2)
                        .foregroundColor(.white)
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(.ultraThinMaterial)
            .cornerRadius(DesignSystem.Spacing.m)
            .overlay(
                RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
                    .stroke(Color.white.opacity(isSelected ? 0.8 : 0.4), lineWidth: 1.5)
            )
            .shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 5)
        }
        .scaleEffect(isSelected ? 1.05 : 1.0)
        .animation(.spring(response: 0.3, dampingFraction: 0.7), value: isSelected)
    }
}

// MARK: - User Role Enum

enum UserRole {
    case driver
    case host
}

// MARK: - Preview

#Preview {
    RoleSelectionView()
        .environmentObject(MapViewModel())
        .environmentObject(BookingViewModel())
        .environmentObject(HostViewModel())
        .environmentObject(CommercialParkingViewModel())
        .environmentObject(PrivateParkingViewModel())
}
