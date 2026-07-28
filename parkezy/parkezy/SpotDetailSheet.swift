//
//  SpotDetailSheet.swift
//  ParkEzy
//
//  Bottom sheet showing parking spot details with booking option
//

import SwiftUI
import MapKit

struct SpotDetailSheet: View {
    // MARK: - Properties
    
    let spot: ParkingSpot
    @Binding var isPresented: Bool
    
    // MARK: - Environment
    
    @EnvironmentObject var mapViewModel: MapViewModel
    @EnvironmentObject var bookingViewModel: BookingViewModel
    
    // MARK: - State
    
    @State private var showBookingConfirmation = false
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView {
                    VStack(spacing: DesignSystem.Spacing.l) {
                        // MARK: - Header Card
                        
                        headerCard
                        
                        // MARK: - Features Grid
                        
                        featuresSection
                        
                        // MARK: - Location & Distance
                        
                        locationSection
                        
                        // MARK: - Pricing Info
                        
                        pricingSection
                    }
                    .padding(DesignSystem.Spacing.m)
                }
                
                // MARK: - Sticky Book Button
                
                bookButton
                    .padding(.horizontal, DesignSystem.Spacing.m)
                    .padding(.bottom, DesignSystem.Spacing.m)
                    .background(Color(.systemBackground))
            }
            .navigationTitle("Spot Details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        isPresented = false
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.gray)
                            .font(.title2)
                    }
                }
            }
            .navigationDestination(isPresented: $showBookingConfirmation) {
                BookingConfirmationView(spot: spot, isPresented: $isPresented)
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }
    
    // MARK: - Header Card
    
    private var headerCard: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            // Spot Image / Icon
            ZStack {
                RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
                    .fill(
                        LinearGradient(
                            colors: [
                                spot.isOccupied ? DesignSystem.Colors.error : DesignSystem.Colors.success,
                                spot.isOccupied ? DesignSystem.Colors.error.opacity(0.7) : DesignSystem.Colors.success.opacity(0.7)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(height: 120)
                
                VStack {
                    Image(systemName: spot.type == .mall ? "building.2.fill" : "house.fill")
                        .font(.system(size: 48))
                        .foregroundColor(.white)
                    
                    Text(spot.type == .mall ? "Mall Parking" : "Private Driveway")
                        .font(.caption.bold())
                        .foregroundColor(.white.opacity(0.9))
                }
            }
            
            // Title & Rating
            VStack(spacing: DesignSystem.Spacing.xs) {
                Text(spot.address)
                    .font(.title2.bold())
                    .multilineTextAlignment(.center)
                
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .foregroundColor(.yellow)
                    Text(String(format: "%.1f", spot.rating))
                        .font(.subheadline.bold())
                    Text("(\(spot.reviewCount) reviews)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                // Availability Badge
                HStack {
                    Circle()
                        .fill(spot.isOccupied ? DesignSystem.Colors.error : DesignSystem.Colors.success)
                        .frame(width: 10, height: 10)
                    Text(spot.isOccupied ? "Currently Occupied" : "Available Now")
                        .font(.subheadline.bold())
                        .foregroundColor(spot.isOccupied ? DesignSystem.Colors.error : DesignSystem.Colors.success)
                }
                .padding(.horizontal, DesignSystem.Spacing.m)
                .padding(.vertical, DesignSystem.Spacing.xs)
                .background(
                    Capsule()
                        .fill(spot.isOccupied ? DesignSystem.Colors.error.opacity(0.1) : DesignSystem.Colors.success.opacity(0.1))
                )
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Features Section
    
    private var featuresSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Features")
                .font(.headline)
            
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: DesignSystem.Spacing.m) {
                FeatureTag(icon: "video.fill", title: "CCTV", isActive: spot.hasCCTV)
                FeatureTag(icon: "umbrella.fill", title: "Covered", isActive: spot.isCovered)
                FeatureTag(icon: "bolt.car.fill", title: "EV", isActive: spot.hasEVCharging)
                FeatureTag(icon: "figure.walk", title: "Accessible", isActive: spot.isAccessible)
                FeatureTag(icon: "24.circle.fill", title: "24/7", isActive: spot.is24Hours)
                FeatureTag(icon: "shield.fill", title: "Insured", isActive: spot.hasInsurance)
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Location Section
    
    private var locationSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Location")
                .font(.headline)
            
            // Mini Map
            Map {
                Marker(spot.address, coordinate: spot.coordinates)
                    .tint(DesignSystem.Colors.primary)
            }
            .frame(height: 150)
            .cornerRadius(DesignSystem.Spacing.s)
            .disabled(true)
            
            // Distance Info
            HStack(spacing: DesignSystem.Spacing.l) {
                VStack {
                    Image(systemName: "location.fill")
                        .font(.title2)
                        .foregroundColor(DesignSystem.Colors.primary)
                    Text(formattedDistance)
                        .font(.headline)
                    Text("Distance")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                
                Divider()
                
                VStack {
                    Image(systemName: "figure.walk")
                        .font(.title2)
                        .foregroundColor(DesignSystem.Colors.primary)
                    Text(formattedWalkingTime)
                        .font(.headline)
                    Text("Walking")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                
                Divider()
                
                VStack {
                    Image(systemName: "car.fill")
                        .font(.title2)
                        .foregroundColor(DesignSystem.Colors.primary)
                    Text(formattedDrivingTime)
                        .font(.headline)
                    Text("Driving")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
            }
            .padding(.vertical, DesignSystem.Spacing.s)
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Pricing Section
    
    private var pricingSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Pricing")
                .font(.headline)
            
            HStack {
                VStack(alignment: .leading) {
                    Text("₹\(Int(spot.pricePerHour))")
                        .font(.system(size: 36, weight: .bold))
                        .foregroundColor(DesignSystem.Colors.primary)
                    Text("per hour")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    HStack {
                        Text("Overstay fee:")
                        Text("₹20/15 min")
                            .bold()
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)
                    
                    HStack {
                        Text("GST:")
                        Text("18%")
                            .bold()
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Book Button
    
    private var bookButton: some View {
        Button {
            showBookingConfirmation = true
        } label: {
            HStack {
                Image(systemName: "checkmark.circle.fill")
                Text("Book Now")
                    .font(.headline)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(
                spot.isOccupied ? Color.gray : DesignSystem.Colors.primary
            )
            .foregroundColor(.white)
            .cornerRadius(DesignSystem.Spacing.m)
        }
        .disabled(spot.isOccupied)
    }
    
    // MARK: - Computed Properties
    
    private var formattedDistance: String {
        let distance = mapViewModel.distanceToSpot(spot)
        if distance < 1000 {
            return "\(Int(distance))m"
        } else {
            return String(format: "%.1f km", distance / 1000)
        }
    }
    
    private var formattedWalkingTime: String {
        let distance = mapViewModel.distanceToSpot(spot)
        let walkingSpeed = 5.0 // km/h
        let timeInMinutes = (distance / 1000) / walkingSpeed * 60
        return "\(Int(ceil(timeInMinutes))) min"
    }
    
    private var formattedDrivingTime: String {
        let distance = mapViewModel.distanceToSpot(spot)
        let drivingSpeed = 30.0 // km/h average city speed
        let timeInMinutes = (distance / 1000) / drivingSpeed * 60
        return "\(Int(ceil(max(1, timeInMinutes)))) min"
    }
}

// MARK: - Feature Tag Component

struct FeatureTag: View {
    let icon: String
    let title: String
    let isActive: Bool
    
    var body: some View {
        VStack(spacing: 6) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(isActive ? DesignSystem.Colors.primary : .gray)
            
            Text(title)
                .font(.caption)
                .foregroundColor(isActive ? .primary : .secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, DesignSystem.Spacing.s)
        .background(
            RoundedRectangle(cornerRadius: DesignSystem.Spacing.s)
                .fill(isActive ? DesignSystem.Colors.primary.opacity(0.1) : Color.gray.opacity(0.1))
        )
        .overlay(
            RoundedRectangle(cornerRadius: DesignSystem.Spacing.s)
                .stroke(isActive ? DesignSystem.Colors.primary.opacity(0.3) : Color.clear, lineWidth: 1)
        )
    }
}

// MARK: - Preview

#Preview {
    SpotDetailSheet(
        spot: ParkingSpot.mockSpot,
        isPresented: .constant(true)
    )
    .environmentObject(MapViewModel())
    .environmentObject(BookingViewModel())
}
