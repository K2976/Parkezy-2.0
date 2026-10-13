//
//  EnhancedPrivateListingDetailView.swift
//  ParkEzy
//
//  Beautiful, fast-loading detail view for private parking listings
//

import SwiftUI
import MapKit
import CoreLocation

struct EnhancedPrivateListingDetailView: View {
    let listing: PrivateParkingListing
    var allowEditing: Bool = false // Default to false for driver mode
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: PrivateParkingViewModel
    
    @State private var selectedSlot: PrivateParkingSlot?
    @State private var showBookingSheet = false
    @State private var imageIndex = 0
    @State private var isLoading = true
    
    // Detect if owner
    private var isOwnerView: Bool {
        viewModel.myListings.contains { $0.id == listing.id }
    }
    
    var body: some View {
        ZStack {
            if isLoading {
                skeletonView
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.systemGray5))
                    .zIndex(1)
                    .transition(.opacity)
            } else {
                mainContent
                    .zIndex(0)
            }
        }
        .onAppear {
            // Simulate loading / allow transition to finish
            DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
                withAnimation {
                    isLoading = false
                }
            }
        }
    }
    
    private var mainContent: some View {
        ScrollView {
            VStack(spacing: 0) {
                // MARK: - Hero Image/Map
                heroSection
                
                // MARK: - Quick Info Bar
                quickInfoBar
                
                // MARK: - Main Content
                VStack(spacing: DesignSystem.Spacing.l) {
                    // Title & Address
                    headerSection
                    
                    // Pricing Card
                    pricingCard
                    
                    // Availability
                    availabilitySection
                    
                    // Amenities Grid
                    amenitiesGrid
                    
                    // Slots (if available)
                    if !listing.slots.isEmpty {
                        slotsSection
                    }
                    
                    // Description
                    if !listing.listingDescription.isEmpty {
                        descriptionSection
                    }
                    
                    // Host Info
                    hostCard
                    
                    // Location Map
                    locationMapSection
                }
                .padding(DesignSystem.Spacing.m)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                if allowEditing && isOwnerView {
                    Button("Edit") {
                        // Edit action
                    }
                    .foregroundColor(DesignSystem.Colors.primary)
                } else {
                    ShareLink(item: "Check out this parking: \(listing.title)") {
                        Image(systemName: "square.and.arrow.up")
                    }
                }
            }
        }
        .overlay(alignment: .bottom) {
            if !isOwnerView || !allowEditing {
                bookNowButton
            }
        }
        .sheet(isPresented: $showBookingSheet) {
            BookingSheetView(listing: listing, selectedSlot: selectedSlot)
                .environmentObject(viewModel)
        }
    }
    
    // MARK: - Hero Section
    
    private var heroSection: some View {
        ZStack(alignment: .topTrailing) {
            // Map or Image
            Map(position: .constant(.camera(MapCamera(
                centerCoordinate: listing.coordinates,
                distance: 500
            )))) {
                Annotation("", coordinate: listing.coordinates) {
                    ZStack {
                        Circle()
                            .fill(DesignSystem.Colors.primary)
                            .frame(width: 40, height: 40)
                        
                        Image(systemName: "parkingsign.circle.fill")
                            .font(.title2)
                            .foregroundColor(.white)
                    }
                }
            }
            .mapStyle(.standard(elevation: .realistic))
            .frame(height: 250)
            .allowsHitTesting(false)
            
            // Availability Badge
            HStack(spacing: 4) {
                Circle()
                    .fill(listing.availableSlots > 0 ? Color.green : Color.red)
                    .frame(width: 8, height: 8)
                
                Text(listing.availableSlots > 0 ? "\(listing.availableSlots) Available" : "Full")
                    .font(.caption.weight(.semibold))
                    .foregroundColor(.white)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(.ultraThinMaterial)
            .cornerRadius(20)
            .padding()
        }
    }
    
    // MARK: - Quick Info Bar
    
    private var quickInfoBar: some View {
        HStack(spacing: 16) {
            // Rating
            HStack(spacing: 4) {
                Image(systemName: "star.fill")
                    .font(.caption)
                    .foregroundColor(.orange)
                Text(String(format: "%.1f", listing.rating))
                    .font(.caption.weight(.semibold))
                Text("(\(listing.reviewCount))")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Divider()
                .frame(height: 16)
            
            // Distance (if available)
            HStack(spacing: 4) {
                Image(systemName: "location.fill")
                    .font(.caption)
                    .foregroundColor(DesignSystem.Colors.primary)
                Text("1.2 km away")
                    .font(.caption.weight(.medium))
            }
            
            Divider()
                .frame(height: 16)
            
            // Type
            HStack(spacing: 4) {
                Image(systemName: "house.fill")
                    .font(.caption)
                    .foregroundColor(.blue)
                Text("Private")
                    .font(.caption.weight(.medium))
            }
            
            Spacer()
        }
        .padding(.horizontal, DesignSystem.Spacing.m)
        .padding(.vertical, DesignSystem.Spacing.s)
        .background(Color(.systemGray6))
    }
    
    // MARK: - Header Section
    
    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(listing.title)
                .font(.title2.bold())
            
            HStack(spacing: 4) {
                Image(systemName: "mappin.circle.fill")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                Text(listing.address)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    
    // MARK: - Pricing Card
    
    private var pricingCard: some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Starting from")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text("₹\(Int(listing.hourlyRate))")
                            .font(.system(size: 32, weight: .bold))
                            .foregroundColor(DesignSystem.Colors.primary)
                        
                        Text("/hour")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }
                
                Spacer()
                
                // Price indicator
                if let suggested = listing.suggestedHourlyRate {
                    VStack(alignment: .trailing, spacing: 4) {
                        HStack(spacing: 4) {
                            Image(systemName: listing.priceCompetitiveness.icon)
                                .font(.caption)
                            Text(listing.priceCompetitiveness.rawValue)
                                .font(.caption.weight(.semibold))
                        }
                        .foregroundColor(listing.priceCompetitiveness.color)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(listing.priceCompetitiveness.color.opacity(0.1))
                        .cornerRadius(8)
                        
                        Text("Avg: ₹\(Int(suggested))/hr")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }
            
            Divider()
            
            // Additional pricing
            HStack {
                if listing.dailyRate > 0 {
                    PriceOption(icon: "calendar", label: "Daily", price: listing.dailyRate)
                }
                
                if listing.dailyRate > 0 && listing.monthlyRate > 0 {
                    Spacer()
                }
                
                if listing.monthlyRate > 0 {
                    PriceOption(icon: "calendar.badge.clock", label: "Monthly", price: listing.monthlyRate)
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(
            LinearGradient(
                colors: [
                    DesignSystem.Colors.primary.opacity(0.05),
                    DesignSystem.Colors.primary.opacity(0.02)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(DesignSystem.Colors.primary.opacity(0.2), lineWidth: 1)
        )
        .cornerRadius(16)
    }
    
    // MARK: - Availability Section
    
    private var availabilitySection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Availability", systemImage: "clock.fill")
                .font(.headline)
            
            if listing.is24Hours {
                HStack {
                    Image(systemName: "24.circle.fill")
                        .foregroundColor(.green)
                    Text("Available 24/7")
                        .font(.subheadline)
                    Spacer()
                }
                .padding(12)
                .background(Color.green.opacity(0.1))
                .cornerRadius(10)
            } else if let start = listing.availableFrom, let end = listing.availableTo {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Opens")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text(start, style: .time)
                            .font(.subheadline.weight(.semibold))
                    }
                    
                    Spacer()
                    
                    Image(systemName: "arrow.right")
                        .foregroundColor(.secondary)
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("Closes")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text(end, style: .time)
                            .font(.subheadline.weight(.semibold))
                    }
                }
                .padding(12)
                .background(Color(.systemGray6))
                .cornerRadius(10)
            }
            
            // Days available
            if !listing.availableDays.isEmpty {
                HStack(spacing: 8) {
                    ForEach(1...7, id: \.self) { day in
                        DayCircle(
                            day: dayLabel(day),
                            isAvailable: listing.availableDays.contains(day)
                        )
                    }
                }
            }
        }
    }
    
    // MARK: - Amenities Grid
    
    private var amenitiesGrid: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Amenities & Features", systemImage: "star.fill")
                .font(.headline)
            
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 12) {
                if listing.isCovered {
                    AmenityCard(icon: "roof.fill", label: "Covered", color: .blue)
                }
                
                if listing.hasCCTV {
                    AmenityCard(icon: "video.fill", label: "CCTV", color: .red)
                }
                
                if listing.hasEVCharging {
                    AmenityCard(icon: "bolt.car.fill", label: "EV Charging", color: .green)
                }
                
                if listing.hasSecurityGuard {
                    AmenityCard(icon: "shield.checkered", label: "Security", color: .orange)
                }
                
                if listing.autoAcceptBookings {
                    AmenityCard(icon: "checkmark.circle.fill", label: "Instant Book", color: .purple)
                }
                
                if listing.hasWaterAccess {
                    AmenityCard(icon: "drop.fill", label: "Water", color: .cyan)
                }
            }
        }
    }
    
    // MARK: - Slots Section
    
    private var slotsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("\(listing.slots.count) Parking Slots", systemImage: "square.stack.3d.up.fill")
                    .font(.headline)
                
                Spacer()
                
                Text("\(listing.availableSlots) available")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color(.systemGray5))
                    .cornerRadius(8)
            }
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(listing.slots) { slot in
                        PrivateSlotCard(
                            slot: slot,
                            isSelected: selectedSlot?.id == slot.id
                        ) {
                            selectedSlot = slot
                        }
                    }
                }
            }
        }
    }
    
    // MARK: - Description Section
    
    private var descriptionSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("About this parking", systemImage: "text.alignleft")
                .font(.headline)
            
            Text(listing.listingDescription)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .lineSpacing(4)
        }
    }
    
    // MARK: - Host Card
    
    private var hostCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Hosted by", systemImage: "person.fill")
                .font(.headline)
            
            HStack(spacing: 12) {
                // Avatar
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [.orange, .pink],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 50, height: 50)
                    .overlay(
                        Text(listing.ownerName.prefix(1))
                            .font(.title3.bold())
                            .foregroundColor(.white)
                    )
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(listing.ownerName)
                        .font(.subheadline.weight(.semibold))
                    
                    HStack(spacing: 12) {
                        HStack(spacing: 4) {
                            Image(systemName: "star.fill")
                                .font(.caption2)
                                .foregroundColor(.orange)
                            Text("4.8")
                                .font(.caption)
                        }
                        
                        Text("•")
                            .foregroundColor(.secondary)
                        
                        Text("Superhost")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                Spacer()
                
                Button {
                    // Contact host
                } label: {
                    Image(systemName: "message.fill")
                        .font(.title3)
                        .foregroundColor(DesignSystem.Colors.primary)
                        .padding(10)
                        .background(Color(.systemGray6))
                        .clipShape(Circle())
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
    }
    
    // MARK: - Location Map Section
    
    private var locationMapSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Location", systemImage: "map.fill")
                .font(.headline)
            
            Map(position: .constant(.camera(MapCamera(
                centerCoordinate: listing.coordinates,
                distance: 1000
            )))) {
                Annotation("", coordinate: listing.coordinates) {
                    ZStack {
                        Circle()
                            .fill(DesignSystem.Colors.primary)
                            .frame(width: 30, height: 30)
                        
                        Image(systemName: "parkingsign")
                            .font(.caption)
                            .foregroundColor(.white)
                    }
                }
            }
            .frame(height: 200)
            .cornerRadius(12)
            .allowsHitTesting(true)
            
            Button {
                openInMaps()
            } label: {
                HStack {
                    Image(systemName: "arrow.triangle.turn.up.right.circle.fill")
                    Text("Open in Maps")
                }
                .font(.subheadline.weight(.medium))
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(10)
            }
        }
    }
    
    // MARK: - Book Now Button
    
    private var bookNowButton: some View {
        Button {
            showBookingSheet = true
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("₹\(Int(listing.hourlyRate))/hour")
                        .font(.headline)
                    Text("Tap to book")
                        .font(.caption)
                }
                
                Spacer()
                
                HStack(spacing: 6) {
                    Text("Book Now")
                        .font(.headline)
                    Image(systemName: "arrow.right.circle.fill")
                        .font(.title3)
                }
            }
            .foregroundColor(.white)
            .padding()
            .background(
                LinearGradient(
                    colors: [
                        DesignSystem.Colors.primary,
                        DesignSystem.Colors.primary.opacity(0.8)
                    ],
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .cornerRadius(16)
            .shadow(color: DesignSystem.Colors.primary.opacity(0.3), radius: 10, y: 5)
        }
        .padding()
        .background(.ultraThinMaterial)
    }
    
    // MARK: - Helper Methods
    
    private func dayLabel(_ day: Int) -> String {
        ["S", "M", "T", "W", "T", "F", "S"][day - 1]
    }
    
    private func openInMaps() {
        let mapItem = MKMapItem(placemark: MKPlacemark(coordinate: listing.coordinates))
        mapItem.name = listing.title
        mapItem.openInMaps(launchOptions: [
            MKLaunchOptionsDirectionsModeKey: MKLaunchOptionsDirectionsModeDriving
        ])
    }


    // MARK: - Skeleton View
    
    private var skeletonView: some View {
        ScrollView {
            VStack(spacing: 0) {
                // Hero Placeholder
                SkeletonBlock(height: 250, cornerRadius: 0)
                
                // Quick Info Bar
                HStack(spacing: 16) {
                    ForEach(0..<3) { _ in
                        SkeletonBlock(width: 80, height: 16)
                    }
                    Spacer()
                }
                .padding(DesignSystem.Spacing.m)
                .background(Color(.systemGray6))
                
                VStack(spacing: DesignSystem.Spacing.l) {
                    // Title & Address
                    VStack(alignment: .leading, spacing: 8) {
                        SkeletonBlock(width: 250, height: 28)
                        SkeletonBlock(width: 200, height: 16)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    
                    // Pricing Card
                    SkeletonBlock(height: 120, cornerRadius: 16)
                    
                    // Availability
                    VStack(alignment: .leading, spacing: 12) {
                        SkeletonBlock(width: 120, height: 20)
                        SkeletonBlock(height: 60, cornerRadius: 10)
                        HStack {
                            ForEach(0..<7) { _ in
                                SkeletonCircle(size: 32)
                            }
                        }
                    }
                    
                    // Amenities
                    VStack(alignment: .leading, spacing: 12) {
                        SkeletonBlock(width: 150, height: 20)
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                            ForEach(0..<4) { _ in
                                SkeletonBlock(height: 50, cornerRadius: 10)
                            }
                        }
                    }
                }
                .padding(DesignSystem.Spacing.m)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Supporting Views

struct PriceOption: View {
    let icon: String
    let label: String
    let price: Double
    
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
                .font(.caption)
                .foregroundColor(.secondary)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.caption2)
                    .foregroundColor(.secondary)
                Text("₹\(Int(price))")
                    .font(.subheadline.weight(.semibold))
            }
        }
    }
}

struct AmenityCard: View {
    let icon: String
    let label: String
    let color: Color
    
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(color)
                .frame(width: 30)
            
            Text(label)
                .font(.subheadline.weight(.medium))
            
            Spacer()
        }
        .padding(12)
        .background(color.opacity(0.1))
        .cornerRadius(10)
    }
}

struct DayCircle: View {
    let day: String
    let isAvailable: Bool
    
    var body: some View {
        Text(day)
            .font(.caption.weight(.semibold))
            .frame(width: 32, height: 32)
            .foregroundColor(isAvailable ? .white : .secondary)
            .background(isAvailable ? DesignSystem.Colors.primary : Color(.systemGray5))
            .clipShape(Circle())
    }
}

struct PrivateSlotCard: View {
    let slot: PrivateParkingSlot
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                // Slot icon
                ZStack {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(slot.isOccupied ? Color.red.opacity(0.2) : Color.green.opacity(0.2))
                        .frame(width: 60, height: 60)
                    
                    Image(systemName: slot.isOccupied ? "car.fill" : "parkingsign")
                        .font(.title2)
                        .foregroundColor(slot.isOccupied ? .red : .green)
                }
                
                // Slot label
                if let label = slot.slotLabel {
                    Text(label)
                        .font(.caption.weight(.medium))
                        .lineLimit(1)
                } else {
                    Text("Slot \(slot.slotNumber)")
                        .font(.caption.weight(.medium))
                }
                
                // Status
                Text(slot.isOccupied ? "Occupied" : "Available")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                
                // Time remaining if occupied
                if let remaining = slot.formattedTimeRemaining {
                    Text(remaining)
                        .font(.caption2)
                        .foregroundColor(.orange)
                }
            }
            .padding(12)
            .background(isSelected ? DesignSystem.Colors.primary.opacity(0.1) : Color(.systemGray6))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? DesignSystem.Colors.primary : Color.clear, lineWidth: 2)
            )
            .cornerRadius(12)
        }
        .disabled(slot.isOccupied || slot.isDisabled)
    }
}

// Simple booking sheet placeholder
struct BookingSheetView: View {
    let listing: PrivateParkingListing
    let selectedSlot: PrivateParkingSlot?
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: PrivateParkingViewModel
    
    var body: some View {
        NavigationStack {
            VStack {
                Text("Book Parking")
                    .font(.title2.bold())
                Text("Full booking flow coming soon!")
                    .foregroundColor(.secondary)
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }
}
