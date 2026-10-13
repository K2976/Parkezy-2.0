//
//  UnifiedHostDashboardView.swift
//  ParkEzy
//
//  Unified dashboard for hosts with earnings, active parking, and add parking tile
//
//new dashbaord

import SwiftUI

struct UnifiedHostDashboardView: View {
    // MARK: - Environment
    
    @EnvironmentObject var viewModel: PrivateParkingViewModel
    @EnvironmentObject var hostViewModel: HostViewModel
    
    // MARK: - State
    
    @State private var showAddParking = false
    @State private var showAllBookings = false
    
    // MARK: - Body
    
    var body: some View {
        ScrollView {
            VStack(spacing: DesignSystem.Spacing.l) {
                // MARK: - Welcome Header
                welcomeHeader
                
                // MARK: - Earnings Summary
                earningsSummary
                
                // MARK: - Add Parking Tile
                addParkingTile
                
                // MARK: - Active Parking
                activeParking
                
                // MARK: - My Listings
                myListings
            }
            .padding(DesignSystem.Spacing.m)
        }
        .navigationTitle("Host Dashboard")
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                NavigationLink(destination: HostBookingsView()) {
                    Image(systemName: "list.bullet.rectangle")
                        .font(.title2)
                        .foregroundColor(DesignSystem.Colors.primary)
                }
            }
        }
        .sheet(isPresented: $showAddParking) {
            AddParkingFlowView()
                .environmentObject(viewModel)
        }
        .refreshable {
            await viewModel.refreshListingsFromBackend()
        }
    }
    
    // MARK: - Welcome Header
    
    private var welcomeHeader: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Welcome back,")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                Text(viewModel.currentUser?.name ?? hostViewModel.currentHost?.name ?? "Host")
                    .font(.title.bold())
            }
            
            Spacer()
            
            // Profile Avatar
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [DesignSystem.Colors.primary, DesignSystem.Colors.primary.opacity(0.7)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 50, height: 50)
                
                Text(String(viewModel.currentUser?.name.prefix(1) ?? hostViewModel.currentHost?.name.prefix(1) ?? "H"))
                    .font(.title2.bold())
                    .foregroundColor(.white)
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Earnings Summary
    
    private var earningsSummary: some View {
        HStack(spacing: DesignSystem.Spacing.m) {
            // Today's Earnings
            EarningsTile(
                icon: "indianrupeesign.circle.fill",
                title: "Today",
                value: "₹\(Int(hostViewModel.todayEarnings))",
                color: DesignSystem.Colors.success
            )
            
            // Total Earnings
            EarningsTile(
                icon: "chart.line.uptrend.xyaxis",
                title: "Total",
                value: "₹\(formatEarnings(hostViewModel.totalEarnings))",
                color: DesignSystem.Colors.primary
            )
            
            // Active Count
            EarningsTile(
                icon: "car.fill",
                title: "Active",
                value: "\(activeBookingCount)",
                color: .orange
            )
        }
    }
    
    // MARK: - Add Parking Tile
    
    private var addParkingTile: some View {
        Button {
            showAddParking = true
        } label: {
            HStack(spacing: DesignSystem.Spacing.m) {
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [.green, .mint],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 60, height: 60)
                    
                    Image(systemName: "plus")
                        .font(.title.bold())
                        .foregroundColor(.white)
                }
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("Add Parking Space")
                        .font(.headline)
                        .foregroundColor(.primary)
                    
                    Text("List your driveway or garage")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Image(systemName: "chevron.right")
                    .foregroundColor(.secondary)
            }
            .padding(DesignSystem.Spacing.m)
            .background(Color(.systemBackground))
            .cornerRadius(DesignSystem.Spacing.m)
            .shadow(color: .black.opacity(0.08), radius: 10, x: 0, y: 5)
            .overlay(
                RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
                    .stroke(Color.green.opacity(0.3), lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
    }
    
    // MARK: - Active Parking
    
    private var activeParking: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            HStack {
                Text("Active Parking")
                    .font(.headline)
                
                Spacer()
                
                if activeBookingCount > 0 {
                    Text("\(activeBookingCount)")
                        .font(.caption.bold())
                        .foregroundColor(.white)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(DesignSystem.Colors.success)
                        .clipShape(Capsule())
                }
            }
            
            if activeBookings.isEmpty {
                VStack(spacing: DesignSystem.Spacing.m) {
                    Image(systemName: "car.fill")
                        .font(.system(size: 40))
                        .foregroundColor(.gray.opacity(0.5))
                    
                    Text("No active parking")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, DesignSystem.Spacing.xl)
            } else {
                ForEach(activeBookings) { booking in
                    ActiveParkingCard(booking: booking)
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - My Listings
    
    private var myListings: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            HStack {
                Text("My Listings")
                    .font(.headline)
                
                Spacer()
                
                Text("\(viewModel.myListings.count)")
                    .font(.caption.bold())
                    .foregroundColor(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(DesignSystem.Colors.primary)
                    .clipShape(Capsule())
            }
            
            if viewModel.myListings.isEmpty {
                VStack(spacing: DesignSystem.Spacing.m) {
                    Image(systemName: "building.2")
                        .font(.system(size: 40))
                        .foregroundColor(.gray.opacity(0.5))
                    
                    Text("No listings yet")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    Text("Tap 'Add Parking Space' to create your first listing")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, DesignSystem.Spacing.xl)
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: DesignSystem.Spacing.m) {
                        ForEach(viewModel.myListings) { listing in
                            NavigationLink {
                                PrivateListingDetailView(listing: listing)
                            } label: {
                                MyListingCard(listing: listing)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Helper Methods
    
    private var activeBookings: [PrivateBooking] {
        viewModel.bookings.filter { $0.status == .active }
    }
    
    private var activeBookingCount: Int {
        activeBookings.count
    }
    
    private func formatEarnings(_ amount: Double) -> String {
        if amount >= 1000 {
            return String(format: "%.1fK", amount / 1000)
        }
        return String(format: "%.0f", amount)
    }
}

// MARK: - Earnings Tile

struct EarningsTile: View {
    let icon: String
    let title: String
    let value: String
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
            Image(systemName: icon)
                .foregroundColor(color)
                .font(.title2)
            
            Text(value)
                .font(.title2.bold())
            
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
}

// MARK: - Active Parking Card

struct ActiveParkingCard: View {
    let booking: PrivateBooking
    
    var body: some View {
        HStack(spacing: DesignSystem.Spacing.m) {
            Circle()
                .fill(DesignSystem.Colors.success)
                .frame(width: 10, height: 10)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(booking.driverName)
                    .font(.subheadline.bold())
                
                if let vehicle = booking.vehicleNumber {
                    Text(vehicle)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 2) {
                Text("Ends \(formatTime(booking.scheduledEndTime))")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Text("₹\(Int(booking.estimatedCost))")
                    .font(.subheadline.bold())
                    .foregroundColor(DesignSystem.Colors.primary)
            }
        }
        .padding(DesignSystem.Spacing.s)
        .background(DesignSystem.Colors.success.opacity(0.05))
        .cornerRadius(DesignSystem.Spacing.s)
    }
    
    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: date)
    }
}

// MARK: - My Listing Card

struct MyListingCard: View {
    let listing: PrivateParkingListing
    
    var body: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
            // Image placeholder
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(
                        LinearGradient(
                            colors: [DesignSystem.Colors.primary.opacity(0.3), DesignSystem.Colors.primary.opacity(0.1)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(height: 80)
                
                Image(systemName: "car.fill")
                    .font(.title)
                    .foregroundColor(DesignSystem.Colors.primary)
            }
            
            Text(listing.title)
                .font(.subheadline.bold())
                .lineLimit(1)
            
            Text(listing.address)
                .font(.caption)
                .foregroundColor(.secondary)
                .lineLimit(1)
            
            HStack {
                Text("₹\(Int(listing.hourlyRate))/hr")
                    .font(.caption.bold())
                    .foregroundColor(DesignSystem.Colors.primary)
                
                Spacer()
                
                HStack(spacing: 2) {
                    Text("\(listing.availableSlots)")
                        .foregroundColor(.green)
                    Text("/")
                        .foregroundColor(.secondary)
                    Text("\(listing.totalSlots)")
                }
                .font(.caption.bold())
            }
        }
        .frame(width: 150)
        .padding(DesignSystem.Spacing.s)
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        UnifiedHostDashboardView()
            .environmentObject(PrivateParkingViewModel())
            .environmentObject(HostViewModel())
    }
}
