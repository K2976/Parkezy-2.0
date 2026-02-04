//
//  PrivateListingDetailView.swift
//  ParkEzy
//
//  Driver view for private parking listings with slot selection
//

import SwiftUI
import CoreLocation

struct PrivateListingDetailView: View {
    let listing: PrivateParkingListing
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: PrivateParkingViewModel
    
    @State private var selectedSlot: PrivateParkingSlot?
    @State private var hourlyDuration: Double = 3
    @State private var startDate = Date()
    @State private var message = ""
    @State private var isBooking = false
    @State private var bookingSuccess = false
    @State private var bookingRequestID: UUID?
    @State private var showEditSheet = false
    
    // Detect if this is the owner viewing their own listing
    private var isOwnerView: Bool {
        viewModel.myListings.contains { $0.id == listing.id }
    }
    
    var body: some View {
        Group {
            if bookingSuccess {
                bookingSuccessView
            } else {
                listingContentView
            }
        }
        .navigationTitle(bookingSuccess ? "Booking Confirmed" : (isOwnerView ? listing.title : "Listing Details"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if isOwnerView && !bookingSuccess {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showEditSheet = true
                    } label: {
                        Text("Edit")
                    }
                }
            }
        }
        .sheet(isPresented: $showEditSheet) {
            EditPrivateListingView(listing: listing)
                .environmentObject(viewModel)
        }
    }
    
    private var listingContentView: some View {
        ScrollView {
            VStack(spacing: 0) {
                // MARK: - Header Image Placeholder
                headerSection
                
                // MARK: - Host Info
                hostInfoSection
                
                // MARK: - Pricing
                pricingSection
                
                // MARK: - Availability
                availabilitySection
                
                // MARK: - Slot Selection
                slotSelectionSection
                
                // MARK: - Booking Form
                if selectedSlot != nil {
                    bookingFormSection
                }
                
                // MARK: - Amenities
                amenitiesSection
                
                // MARK: - Description
                descriptionSection
            }
        }
    }
    
    private var bookingSuccessView: some View {
        VStack(spacing: DesignSystem.Spacing.xl) {
            Spacer()
            
            // Success Icon
            ZStack {
                Circle()
                    .fill(listing.autoAcceptBookings ? DesignSystem.Colors.success.opacity(0.1) : DesignSystem.Colors.primary.opacity(0.1))
                    .frame(width: 120, height: 120)
                
                Image(systemName: listing.autoAcceptBookings ? "checkmark.circle.fill" : "clock.badge.checkmark.fill")
                    .font(.system(size: 80))
                    .foregroundColor(listing.autoAcceptBookings ? DesignSystem.Colors.success : DesignSystem.Colors.primary)
            }
            
            Text(listing.autoAcceptBookings ? "Booking Confirmed!" : "Request Sent!")
                .font(.title.bold())
            
            Text(listing.autoAcceptBookings ? "Your parking spot is reserved" : "Waiting for host approval")
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            // Booking Details Card
            VStack(spacing: DesignSystem.Spacing.m) {
                HStack {
                    Text("Location")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(listing.title)
                        .fontWeight(.medium)
                        .multilineTextAlignment(.trailing)
                }
                
                Divider()
                
                if let slot = selectedSlot {
                    HStack {
                        Text("Slot")
                            .foregroundColor(.secondary)
                        Spacer()
                        Text(slot.displayName)
                            .fontWeight(.medium)
                    }
                    
                    Divider()
                }
                
                HStack {
                    Text("Duration")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(String(format: "%.1f", hourlyDuration)) hours")
                        .fontWeight(.medium)
                }
                
                Divider()
                
                HStack {
                    Text("Start Time")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(startDate, style: .time)
                        .fontWeight(.medium)
                }
                
                Divider()
                
                HStack {
                    Text("Total Cost")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("₹\(Int(totalCost))")
                        .fontWeight(.bold)
                        .foregroundColor(DesignSystem.Colors.primary)
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(Color(.systemGray6))
            .cornerRadius(DesignSystem.Spacing.m)
            .padding(.horizontal)
            
            if !listing.autoAcceptBookings {
                VStack(spacing: 8) {
                    Image(systemName: "bell.badge.fill")
                        .font(.title2)
                        .foregroundColor(.orange)
                    Text("You'll receive a notification when the host responds")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding()
            }
            
            Spacer()
            
            Button {
                dismiss()
            } label: {
                Text("Done")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(DesignSystem.Colors.primary)
                    .foregroundColor(.white)
                    .cornerRadius(DesignSystem.Spacing.m)
            }
            .padding(.horizontal)
            .padding(.bottom)
        }
    }
    
    // MARK: - Header Section
    
    private var headerSection: some View {
        ZStack(alignment: .bottomLeading) {
            // Placeholder gradient for image
            LinearGradient(
                colors: [.blue.opacity(0.6), .purple.opacity(0.6)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .frame(height: 200)
            .overlay(
                Image(systemName: "car.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.white.opacity(0.3))
            )
            
            VStack(alignment: .leading, spacing: 4) {
                Text(listing.title)
                    .font(.title2.bold())
                    .foregroundColor(.white)
                
                HStack {
                    Image(systemName: "mappin")
                    Text(listing.address)
                }
                .font(.subheadline)
                .foregroundColor(.white.opacity(0.9))
            }
            .padding(DesignSystem.Spacing.m)
        }
    }
    
    // MARK: - Host Info
    
    private var hostInfoSection: some View {
        HStack {
            // Avatar
            Circle()
                .fill(LinearGradient(colors: [.orange, .pink], startPoint: .topLeading, endPoint: .bottomTrailing))
                .frame(width: 50, height: 50)
                .overlay(
                    Text(String(listing.ownerName.prefix(1)))
                        .font(.title2.bold())
                        .foregroundColor(.white)
                )
            
            VStack(alignment: .leading, spacing: 2) {
                Text("Hosted by")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(listing.ownerName)
                    .font(.headline)
            }
            
            Spacer()
            
            // Rating
            VStack(alignment: .trailing, spacing: 2) {
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .foregroundColor(.yellow)
                    Text(String(format: "%.1f", listing.rating))
                        .fontWeight(.semibold)
                }
                Text("\(listing.reviewCount) reviews")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
    }
    
    // MARK: - Pricing Section
    
    private var pricingSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Pricing")
                .font(.headline)
            
            HStack {
                Image(systemName: "clock.fill")
                    .font(.title2)
                    .foregroundColor(DesignSystem.Colors.primary)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("Hourly Rate")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Text("₹\(Int(listing.hourlyRate))/hour")
                        .font(.title2.bold())
                        .foregroundColor(DesignSystem.Colors.primary)
                }
                
                Spacer()
            }
            .padding()
            .background(DesignSystem.Colors.primary.opacity(0.1))
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(DesignSystem.Colors.primary, lineWidth: 2)
            )
            
            // Pricing intelligence for comparison
            if let suggested = listing.suggestedHourlyRate {
                HStack {
                    Image(systemName: listing.priceCompetitiveness.icon)
                        .foregroundColor(listing.priceCompetitiveness.color)
                    Text("Area average: ₹\(Int(suggested))/hr")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("•")
                        .foregroundColor(.secondary)
                    Text(listing.priceCompetitiveness.rawValue)
                        .font(.caption.bold())
                        .foregroundColor(listing.priceCompetitiveness.color)
                }
                .padding(.top, 4)
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.secondarySystemBackground))
    }
    
    // MARK: - Availability Section
    
    private var availabilitySection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Available Slots")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                HStack(alignment: .bottom, spacing: 4) {
                    Text("\(listing.availableSlots)")
                        .font(.system(size: 28, weight: .bold))
                        .foregroundColor(.green)
                    Text("of \(listing.totalSlots)")
                        .font(.headline)
                        .foregroundColor(.secondary)
                        .padding(.bottom, 2)
                }
            }
            
            Spacer()
            
            // Booking type indicator
            if listing.autoAcceptBookings {
                Label("Instant Book", systemImage: "bolt.fill")
                    .font(.caption.bold())
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.green)
                    .cornerRadius(20)
            } else {
                Label("Request to Book", systemImage: "hand.raised.fill")
                    .font(.caption.bold())
                    .foregroundColor(.orange)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.orange.opacity(0.15))
                    .cornerRadius(20)
            }
        }
        .padding(DesignSystem.Spacing.m)
    }
    
    // MARK: - Slot Selection
    
    private var slotSelectionSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Select a Slot")
                .font(.headline)
            
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 100))], spacing: DesignSystem.Spacing.s) {
                ForEach(listing.slots) { slot in
                    LegacyPrivateSlotCard(
                        slot: slot,
                        isSelected: selectedSlot?.id == slot.id
                    ) {
                        if !slot.isOccupied && !slot.isDisabled {
                            withAnimation(.spring(response: 0.3)) {
                                selectedSlot = slot
                            }
                        }
                    }
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
    }
    
    // MARK: - Amenities
    
    private var amenitiesSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Amenities")
                .font(.headline)
            
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 140))], spacing: DesignSystem.Spacing.s) {
                if listing.isCovered {
                    AmenityBadge(icon: "umbrella.fill", label: "Covered")
                }
                if listing.hasCCTV {
                    AmenityBadge(icon: "video.fill", label: "CCTV")
                }
                if listing.hasEVCharging {
                    AmenityBadge(icon: "bolt.car.fill", label: "EV Charging")
                }
                if listing.hasSecurityGuard {
                    AmenityBadge(icon: "shield.fill", label: "Security")
                }
                if listing.is24Hours {
                    AmenityBadge(icon: "24.circle.fill", label: "24 Hours")
                }
                if listing.hasWaterAccess {
                    AmenityBadge(icon: "drop.fill", label: "Car Wash")
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.secondarySystemBackground))
    }
    
    // MARK: - Description
    
    private var descriptionSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
            Text("About this space")
                .font(.headline)
            Text(listing.listingDescription)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .padding(DesignSystem.Spacing.m)
    }
    
    // MARK: - Booking Form Section
    
    private var bookingFormSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Book This Spot")
                .font(.headline)
            
            // Duration Selector
            VStack(alignment: .leading, spacing: 8) {
                Text("Duration")
                    .font(.subheadline.bold())
                
                Stepper(value: $hourlyDuration, in: 0.5...24, step: 0.5) {
                    HStack {
                        Image(systemName: "clock.fill")
                            .foregroundColor(DesignSystem.Colors.primary)
                        Text("\(String(format: "%.1f", hourlyDuration)) hours")
                            .font(.headline)
                    }
                }
                .padding()
                .background(Color(.secondarySystemBackground))
                .cornerRadius(10)
            }
            
            // Start Time
            VStack(alignment: .leading, spacing: 8) {
                Text("Start Time")
                    .font(.subheadline.bold())
                
                DatePicker("", selection: $startDate, in: Date()...)
                    .labelsHidden()
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(10)
            }
            
            // Message to Host
            VStack(alignment: .leading, spacing: 8) {
                Text("Message to Host (Optional)")
                    .font(.subheadline.bold())
                
                TextField("Any special requests?", text: $message, axis: .vertical)
                    .lineLimit(3...5)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(10)
            }
            
            // Cost Summary
            VStack(spacing: 12) {
                HStack {
                    Text("Rate")
                    Spacer()
                    Text("₹\(Int(listing.hourlyRate))/hour")
                        .foregroundColor(.secondary)
                }
                
                HStack {
                    Text("Duration")
                    Spacer()
                    Text("\(String(format: "%.1f", hourlyDuration)) hrs")
                        .foregroundColor(.secondary)
                }
                
                Divider()
                
                HStack {
                    Text("Total (incl. GST)")
                        .font(.headline)
                    Spacer()
                    Text("₹\(Int(totalCost))")
                        .font(.title3.bold())
                        .foregroundColor(DesignSystem.Colors.primary)
                }
            }
            .padding()
            .background(Color(.secondarySystemBackground))
            .cornerRadius(12)
            
            // Book Button
            Button(action: requestBooking) {
                HStack {
                    if isBooking {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    } else {
                        Image(systemName: "checkmark.circle.fill")
                        Text(listing.autoAcceptBookings ? "Book Now" : "Request Booking")
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(DesignSystem.Colors.primary)
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .disabled(isBooking)
            
            if !listing.autoAcceptBookings {
                Text("This booking requires host approval. You'll be notified once approved.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
    }
    
    // MARK: - Helper Functions
    
    private var totalCost: Double {
        listing.hourlyRate * hourlyDuration * 1.18 // Including GST
    }
    
    private func requestBooking() {
        guard let slot = selectedSlot else { return }
        
        isBooking = true
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            let endTime = startDate.addingTimeInterval(hourlyDuration * 3600)
            
            viewModel.requestBooking(
                listingID: listing.id,
                slotID: slot.id,
                startTime: startDate,
                endTime: endTime,
                durationType: .hourly,
                driverMessage: message.isEmpty ? nil : message
            )
            
            isBooking = false
            
            // Show success view
            withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
                bookingSuccess = true
            }
            
            // Haptic feedback
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.success)
        }
    }
}

// MARK: - Private Slot Card

struct LegacyPrivateSlotCard: View {
    let slot: PrivateParkingSlot
    let isSelected: Bool
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 6) {
                // Icon
                Image(systemName: slot.vehicleSize.icon)
                    .font(.title2)
                    .foregroundColor(slotColor)
                
                // Label
                Text(slot.displayName)
                    .font(.subheadline.bold())
                    .foregroundColor(slot.isDisabled ? .gray : .primary)
                
                // Size badges
                HStack(spacing: 4) {
                    if slot.canFitSUV {
                        Text("SUV")
                            .font(.system(size: 8, weight: .bold))
                            .foregroundColor(.white)
                            .padding(.horizontal, 4)
                            .padding(.vertical, 2)
                            .background(Color.blue)
                            .cornerRadius(3)
                    }
                }
                
                // Timer for occupied
                if let timeRemaining = slot.formattedTimeRemaining {
                    SlotTimerBadge(timeText: timeRemaining)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(DesignSystem.Spacing.m)
            .background(backgroundColor)
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? DesignSystem.Colors.primary : Color.clear, lineWidth: 3)
            )
        }
        .disabled(slot.isOccupied || slot.isDisabled)
    }
    
    private var slotColor: Color {
        if slot.isDisabled { return .gray.opacity(0.5) }
        if slot.isOccupied { return .red.opacity(0.6) }
        return .green
    }
    
    private var backgroundColor: Color {
        if slot.isDisabled { return Color.gray.opacity(0.1) }
        if slot.isOccupied { return Color.red.opacity(0.05) }
        return Color.green.opacity(0.1)
    }
}

// MARK: - Private Booking Sheet

struct PrivateBookingSheet: View {
    let listing: PrivateParkingListing
    let slot: PrivateParkingSlot
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: PrivateParkingViewModel
    
    @State private var hourlyDuration: Double = 3
    @State private var startDate = Date()
    @State private var message = ""
    @State private var isBooking = false
    
    private var totalCost: Double {
        listing.hourlyRate * hourlyDuration * 1.18
    }
    
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Text("Location")
                        Spacer()
                        Text(listing.title)
                            .foregroundColor(.secondary)
                            .lineLimit(1)
                    }
                    HStack {
                        Text("Slot")
                        Spacer()
                        Text(slot.displayName)
                            .foregroundColor(.secondary)
                    }
                }
                
                Section("Booking Details") {
                    Stepper(value: $hourlyDuration, in: 1...24, step: 0.5) {
                        Text("\(String(format: "%.1f", hourlyDuration)) hours")
                    }
                    DatePicker("Start Time", selection: $startDate, in: Date()...)
                }
                
                Section("Message to Host (Optional)") {
                    TextField("Any special requests?", text: $message, axis: .vertical)
                        .lineLimit(3...5)
                }
                
                Section {
                    HStack {
                        Text("Rate")
                        Spacer()
                        Text("₹\(Int(listing.hourlyRate))/hour")
                    }
                    HStack {
                        Text("Total (incl. GST)")
                            .fontWeight(.bold)
                        Spacer()
                        Text("₹\(Int(totalCost))")
                            .font(.title3.bold())
                            .foregroundColor(DesignSystem.Colors.primary)
                    }
                } header: {
                    Text("Payment")
                }
                
                Section {
                    Button {
                        requestBooking()
                    } label: {
                        HStack {
                            Spacer()
                            if isBooking {
                                ProgressView()
                            } else {
                                Text(listing.autoAcceptBookings ? "Book Now" : "Request Booking")
                                    .fontWeight(.semibold)
                            }
                            Spacer()
                        }
                    }
                    .disabled(isBooking)
                } footer: {
                    if !listing.autoAcceptBookings {
                        Text("This booking requires host approval. You'll be notified once approved.")
                    }
                }
            }
            .navigationTitle("Book Parking")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
    
    private func requestBooking() {
        isBooking = true
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            let endTime = startDate.addingTimeInterval(hourlyDuration * 3600)
            
            _ = viewModel.requestBooking(
                listingID: listing.id,
                slotID: slot.id,
                startTime: startDate,
                endTime: endTime,
                durationType: .hourly,
                driverMessage: message.isEmpty ? nil : message
            )
            
            isBooking = false
            dismiss()
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        PrivateListingDetailView(
            listing: PrivateParkingListing(
                id: UUID(),
                ownerID: UUID(),
                ownerName: "Test Host",
                title: "Sample Listing",
                address: "123 Test Street",
                coordinates: .init(latitude: 28.5, longitude: 77.2),
                listingDescription: "A nice parking spot",
                slots: [],
                hourlyRate: 40,
                dailyRate: 300,
                monthlyRate: 3000,
                flatFullBookingRate: nil,
                autoAcceptBookings: false,
                instantBookingDiscount: nil,
                hasCCTV: true, isCovered: true, hasEVCharging: true, hasSecurityGuard: true, hasWaterAccess: false, is24Hours: true,
                availableFrom: nil, availableTo: nil, availableDays: [1,2,3,4,5,6,7],
                rating: 4.5, reviewCount: 50,
                imageURLs: [],
                capturedPhotoData: nil,
                capturedVideoURL: nil,
                maxBookingDuration: .unlimited,
                suggestedHourlyRate: 45
            )
        )
        .environmentObject(PrivateParkingViewModel())
    }
}
