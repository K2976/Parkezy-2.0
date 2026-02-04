//
//  CommercialFacilityDetailView.swift
//  ParkEzy
//
//  Driver view for commercial parking facility with slot selection
//

import SwiftUI
import CoreLocation

struct CommercialFacilityDetailView: View {
    let facility: CommercialParkingFacility
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: CommercialParkingViewModel
    
    @State private var selectedFloor: Int = 0
    @State private var selectedSlot: CommercialParkingSlot?
    @State private var showBookingSheet = false
    
    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                // MARK: - Header
                headerSection
                
                // MARK: - Availability Counter
                availabilitySection
                
                // MARK: - Floor Picker
                floorPicker
                
                // MARK: - Slot Grid
                slotGrid
                
                // MARK: - Amenities
                amenitiesSection
            }
        }
        .navigationTitle(facility.name)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showBookingSheet) {
            if let slot = selectedSlot {
                CommercialBookingSheet(facility: facility, slot: slot)
            }
        }
        .onAppear {
            // Set initial floor
            if let firstFloor = viewModel.floorsInFacility(facility).first {
                selectedFloor = firstFloor
            }
        }
    }
    
    // MARK: - Header Section
    
    private var headerSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            // Facility Type Badge
            HStack {
                Label(facility.facilityType.rawValue, systemImage: facility.facilityType.icon)
                    .font(.caption.bold())
                    .foregroundColor(.white)
                    .padding(.horizontal, DesignSystem.Spacing.m)
                    .padding(.vertical, DesignSystem.Spacing.s)
                    .background(facility.facilityType.color)
                    .cornerRadius(20)
                
                Spacer()
                
                // Rating
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .foregroundColor(.yellow)
                    Text(String(format: "%.1f", facility.rating))
                        .fontWeight(.semibold)
                    Text("(\(facility.reviewCount))")
                        .foregroundColor(.secondary)
                }
                .font(.subheadline)
            }
            
            Text(facility.address)
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            // Pricing
            HStack {
                VStack(alignment: .leading) {
                    Text("Starting from")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("₹\(Int(facility.defaultHourlyRate))/hr")
                        .font(.title2.bold())
                        .foregroundColor(DesignSystem.Colors.primary)
                }
                
                Spacer()
                
                if let dayRate = facility.flatDayRate {
                    VStack(alignment: .trailing) {
                        Text("Day Pass")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text("₹\(Int(dayRate))")
                            .font(.headline)
                            .foregroundColor(.green)
                    }
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
    }
    
    // MARK: - Availability Section
    
    private var availabilitySection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Available Now")
                    .font(.headline)
                HStack(spacing: 4) {
                    Text("\(facility.availableSlots)")
                        .font(.system(size: 32, weight: .bold))
                        .foregroundColor(.green)
                    Text("/ \(facility.totalSlots)")
                        .font(.title3)
                        .foregroundColor(.secondary)
                    Text("slots")
                        .foregroundColor(.secondary)
                }
            }
            
            Spacer()
            
            // Real-time indicator
            HStack(spacing: 4) {
                Circle()
                    .fill(.green)
                    .frame(width: 8, height: 8)
                Text("Live")
                    .font(.caption.bold())
                    .foregroundColor(.green)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Color.green.opacity(0.1))
            .cornerRadius(20)
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.secondarySystemBackground))
    }
    
    // MARK: - Floor Picker
    
    private var floorPicker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: DesignSystem.Spacing.s) {
                ForEach(viewModel.floorsInFacility(facility), id: \.self) { floor in
                    let floorSlots = viewModel.slotsForFloor(floor, in: facility)
                    let available = floorSlots.filter { !$0.isOccupied && !$0.isDisabled }.count
                    
                    Button {
                        withAnimation(.spring(response: 0.3)) {
                            selectedFloor = floor
                        }
                    } label: {
                        VStack(spacing: 4) {
                            Text(floorLabel(floor))
                                .font(.headline)
                            Text("\(available) free")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .padding(.horizontal, DesignSystem.Spacing.m)
                        .padding(.vertical, DesignSystem.Spacing.s)
                        .background(selectedFloor == floor ? DesignSystem.Colors.primary : Color(.tertiarySystemBackground))
                        .foregroundColor(selectedFloor == floor ? .white : .primary)
                        .cornerRadius(10)
                    }
                }
            }
            .padding(.horizontal, DesignSystem.Spacing.m)
            .padding(.vertical, DesignSystem.Spacing.s)
        }
    }
    
    private func floorLabel(_ floor: Int) -> String {
        if floor < 0 { return "B\(abs(floor))" }
        if floor == 0 { return "Ground" }
        return "Level \(floor)"
    }
    
    // MARK: - Slot Grid
    
    private var slotGrid: some View {
        let slots = viewModel.slotsForFloor(selectedFloor, in: facility)
        let columns = [GridItem(.adaptive(minimum: 80), spacing: DesignSystem.Spacing.s)]
        
        return VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Select a Slot")
                .font(.headline)
                .padding(.horizontal, DesignSystem.Spacing.m)
            
            // Legend
            slotLegend
            
            LazyVGrid(columns: columns, spacing: DesignSystem.Spacing.s) {
                ForEach(slots) { slot in
                    CommercialSlotCard(
                        slot: slot,
                        isSelected: selectedSlot?.id == slot.id,
                        hourlyRate: slot.hourlyRateOverride ?? facility.defaultHourlyRate
                    ) {
                        if !slot.isOccupied && !slot.isDisabled {
                            withAnimation(.spring(response: 0.3)) {
                                selectedSlot = slot
                                showBookingSheet = true
                            }
                        }
                    }
                }
            }
            .padding(.horizontal, DesignSystem.Spacing.m)
        }
        .padding(.vertical, DesignSystem.Spacing.m)
    }
    
    private var slotLegend: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: DesignSystem.Spacing.m) {
                LegendItem(color: .green, label: "Available")
                LegendItem(color: .red.opacity(0.6), label: "Occupied")
                LegendItem(color: .gray.opacity(0.4), label: "Disabled")
                LegendItem(color: .blue, label: "EV Charging")
                LegendItem(color: .purple, label: "Accessible")
            }
            .padding(.horizontal, DesignSystem.Spacing.m)
        }
    }
    
    // MARK: - Amenities Section
    
    private var amenitiesSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Amenities")
                .font(.headline)
            
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 150))], spacing: DesignSystem.Spacing.s) {
                if facility.hasCCTV {
                    AmenityBadge(icon: "video.fill", label: "CCTV")
                }
                if facility.hasEVCharging {
                    AmenityBadge(icon: "bolt.car.fill", label: "EV Charging")
                }
                if facility.hasValetService {
                    AmenityBadge(icon: "person.fill.badge.plus", label: "Valet")
                }
                if facility.hasCarWash {
                    AmenityBadge(icon: "drop.fill", label: "Car Wash")
                }
                if facility.is24Hours {
                    AmenityBadge(icon: "24.circle.fill", label: "24 Hours")
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
    }
}

// MARK: - Slot Card

struct CommercialSlotCard: View {
    let slot: CommercialParkingSlot
    let isSelected: Bool
    let hourlyRate: Double
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 4) {
                // Slot icon
                Image(systemName: slot.slotType.icon)
                    .font(.title2)
                    .foregroundColor(slotColor)
                
                // Slot number
                Text(slot.slotNumber)
                    .font(.caption.bold())
                    .foregroundColor(slot.isDisabled ? .gray : .primary)
                
                // Timer badge for occupied slots
                if let timeRemaining = slot.formattedTimeRemaining {
                    SlotTimerBadge(timeText: timeRemaining)
                }
                
                // Price for available slots
                if !slot.isOccupied && !slot.isDisabled {
                    Text("₹\(Int(hourlyRate))")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
            .frame(width: 80, height: 90)
            .background(backgroundColor)
            .cornerRadius(10)
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(isSelected ? DesignSystem.Colors.primary : Color.clear, lineWidth: 3)
            )
        }
        .disabled(slot.isOccupied || slot.isDisabled)
    }
    
    private var slotColor: Color {
        if slot.isDisabled { return .gray.opacity(0.5) }
        if slot.isOccupied { return .red.opacity(0.6) }
        return slot.slotType.color
    }
    
    private var backgroundColor: Color {
        if slot.isDisabled { return Color.gray.opacity(0.1) }
        if slot.isOccupied { return Color.red.opacity(0.05) }
        return Color.green.opacity(0.1)
    }
}

// MARK: - Slot Timer Badge

struct SlotTimerBadge: View {
    let timeText: String
    
    var body: some View {
        Text(timeText)
            .font(.system(size: 8, weight: .semibold))
            .foregroundColor(.orange)
            .padding(.horizontal, 4)
            .padding(.vertical, 2)
            .background(Color.orange.opacity(0.15))
            .cornerRadius(4)
    }
}

// MARK: - Legend Item

struct LegendItem: View {
    let color: Color
    let label: String
    
    var body: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(color)
                .frame(width: 10, height: 10)
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}

// MARK: - Amenity Badge

struct AmenityBadge: View {
    let icon: String
    let label: String
    
    var body: some View {
        HStack(spacing: DesignSystem.Spacing.s) {
            Image(systemName: icon)
                .foregroundColor(DesignSystem.Colors.primary)
            Text(label)
                .font(.subheadline)
        }
        .padding(.horizontal, DesignSystem.Spacing.m)
        .padding(.vertical, DesignSystem.Spacing.s)
        .background(Color(.tertiarySystemBackground))
        .cornerRadius(8)
    }
}

// MARK: - Commercial Booking Sheet

struct CommercialBookingSheet: View {
    let facility: CommercialParkingFacility
    let slot: CommercialParkingSlot
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: CommercialParkingViewModel
    
    @State private var duration: Double = 2
    @State private var startNow = true
    @State private var scheduledStart = Date()
    @State private var isBooking = false
    @State private var bookingSuccess = false
    @State private var activeBookingID: UUID?
    
    private var hourlyRate: Double {
        slot.hourlyRateOverride ?? facility.defaultHourlyRate
    }
    
    private var totalCost: Double {
        hourlyRate * duration * 1.18 // Including GST
    }
    
    var body: some View {
        NavigationStack {
            if bookingSuccess {
                bookingSuccessView
            } else {
                bookingFormView
            }
        }
    }
    
    private var bookingSuccessView: some View {
        VStack(spacing: DesignSystem.Spacing.xl) {
            Spacer()
            
            // Success Icon
            ZStack {
                Circle()
                    .fill(DesignSystem.Colors.success.opacity(0.1))
                    .frame(width: 120, height: 120)
                
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 80))
                    .foregroundColor(DesignSystem.Colors.success)
            }
            
            Text("Booking Confirmed!")
                .font(.title.bold())
            
            Text("Your parking spot is reserved")
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            // Booking Details Card
            VStack(spacing: DesignSystem.Spacing.m) {
                HStack {
                    Text("Facility")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(facility.name)
                        .fontWeight(.medium)
                }
                
                Divider()
                
                HStack {
                    Text("Slot")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(slot.slotNumber)
                        .fontWeight(.medium)
                }
                
                Divider()
                
                HStack {
                    Text("Duration")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(Int(duration)) hour\(duration > 1 ? "s" : "")")
                        .fontWeight(.medium)
                }
                
                Divider()
                
                HStack {
                    Text("Amount Paid")
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
            
            // QR Code Placeholder
            VStack(spacing: DesignSystem.Spacing.s) {
                Image(systemName: "qrcode")
                    .font(.system(size: 100))
                    .foregroundColor(.primary)
                
                Text("Show this at entry")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(DesignSystem.Spacing.l)
            .background(Color.white)
            .cornerRadius(DesignSystem.Spacing.m)
            .shadow(color: .black.opacity(0.1), radius: 5, x: 0, y: 2)
            
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
        .navigationTitle("Booking Confirmed")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    private var bookingFormView: some View {
        Form {
            Section {
                    HStack {
                        Text("Facility")
                        Spacer()
                        Text(facility.name)
                            .foregroundColor(.secondary)
                    }
                    HStack {
                        Text("Slot")
                        Spacer()
                        Text(slot.slotNumber)
                            .foregroundColor(.secondary)
                    }
                    HStack {
                        Label(slot.slotType.rawValue, systemImage: slot.slotType.icon)
                        Spacer()
                        Text("₹\(Int(hourlyRate))/hr")
                            .foregroundColor(DesignSystem.Colors.primary)
                    }
                }
                
                Section("Duration") {
                    Stepper(value: $duration, in: 1...24, step: 0.5) {
                        Text("\(String(format: "%.1f", duration)) hours")
                    }
                    
                    Toggle("Start Now", isOn: $startNow)
                    
                    if !startNow {
                        DatePicker("Start Time", selection: $scheduledStart, in: Date()...)
                    }
                }
                
                Section {
                    HStack {
                        Text("Subtotal")
                        Spacer()
                        Text("₹\(Int(hourlyRate * duration))")
                    }
                    HStack {
                        Text("GST (18%)")
                        Spacer()
                        Text("₹\(Int(hourlyRate * duration * 0.18))")
                    }
                    HStack {
                        Text("Total")
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
                        bookSlot()
                    } label: {
                        if isBooking {
                            ProgressView()
                                .frame(maxWidth: .infinity)
                        } else {
                            Text("Confirm Booking")
                                .frame(maxWidth: .infinity)
                                .fontWeight(.semibold)
                        }
                    }
                    .disabled(isBooking)
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
    
    private func bookSlot() {
        isBooking = true
        
        // Simulate booking
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            let startTime = startNow ? Date() : scheduledStart
            let booking = viewModel.bookSlot(
                facilityID: facility.id,
                slotID: slot.id,
                startTime: startTime,
                duration: duration
            )
            isBooking = false
            
            if let booking = booking {
                activeBookingID = booking.id
                withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
                    bookingSuccess = true
                }
                
                // Haptic feedback
                let generator = UINotificationFeedbackGenerator()
                generator.notificationOccurred(.success)
            }
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        CommercialFacilityDetailView(
            facility: CommercialParkingFacility(
                id: UUID(),
                name: "Sample Mall",
                address: "123 Main Street",
                coordinates: .init(latitude: 28.5, longitude: 77.2),
                facilityType: .mall,
                slots: [],
                defaultHourlyRate: 60,
                flatDayRate: 400,
                hasCCTV: true, hasEVCharging: true, hasValetService: true, hasCarWash: true, is24Hours: true,
                rating: 4.5, reviewCount: 234,
                ownerID: UUID(), ownerName: "Test"
            )
        )
        .environmentObject(CommercialParkingViewModel())
    }
}
