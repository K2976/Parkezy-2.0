//
//  EditPrivateListingView.swift
//  ParkEzy
//
//  Edit view for modifying private parking listing details
//

import SwiftUI
import CoreLocation

struct EditPrivateListingView: View {
    let listing: PrivateParkingListing
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: PrivateParkingViewModel
    
    // Editable fields
    @State private var title: String
    @State private var listingDescription: String
    @State private var hourlyRate: Double
    @State private var dailyRate: Double?
    @State private var monthlyRate: Double?
    
    // Availability
    @State private var availableStartTime: Date
    @State private var availableEndTime: Date
    @State private var selectedDays: Set<Int>
    @State private var is24Hours: Bool
    
    // Amenities
    @State private var isCovered: Bool
    @State private var hasCCTV: Bool
    @State private var hasEVCharging: Bool
    @State private var hasSecurityGuard: Bool
    @State private var hasWaterAccess: Bool
    
    // Auto booking
    @State private var autoAcceptBookings: Bool
    
    // UI State
    @State private var isSaving = false
    @State private var showSaveSuccess = false
    @State private var errorMessage: String?
    
    private let dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    init(listing: PrivateParkingListing) {
        self.listing = listing
        
        // Initialize state from listing
        _title = State(initialValue: listing.title)
        _listingDescription = State(initialValue: listing.listingDescription)
        _hourlyRate = State(initialValue: listing.hourlyRate)
        _dailyRate = State(initialValue: listing.dailyRate)
        _monthlyRate = State(initialValue: listing.monthlyRate)
        
        // Use existing Date values or create defaults
        let calendar = Calendar.current
        var defaultStart = calendar.date(bySettingHour: 9, minute: 0, second: 0, of: Date()) ?? Date()
        var defaultEnd = calendar.date(bySettingHour: 18, minute: 0, second: 0, of: Date()) ?? Date()
        
        _availableStartTime = State(initialValue: listing.availableFrom ?? defaultStart)
        _availableEndTime = State(initialValue: listing.availableTo ?? defaultEnd)
        
        _selectedDays = State(initialValue: Set(listing.availableDays))
        _is24Hours = State(initialValue: listing.is24Hours)
        
        // Amenities
        _isCovered = State(initialValue: listing.isCovered)
        _hasCCTV = State(initialValue: listing.hasCCTV)
        _hasEVCharging = State(initialValue: listing.hasEVCharging)
        _hasSecurityGuard = State(initialValue: listing.hasSecurityGuard)
        _hasWaterAccess = State(initialValue: listing.hasWaterAccess)
        
        // Booking settings
        _autoAcceptBookings = State(initialValue: listing.autoAcceptBookings)
    }
    
    var body: some View {
        NavigationStack {
            Form {
                // MARK: - Basic Info
                Section("Basic Information") {
                    TextField("Title", text: $title)
                    
                    TextField("Description", text: $listingDescription, axis: .vertical)
                        .lineLimit(3...6)
                }
                
                // MARK: - Pricing
                Section("Pricing") {
                    HStack {
                        Text("Hourly Rate")
                        Spacer()
                        Text("₹")
                            .foregroundColor(.secondary)
                        TextField("40", value: $hourlyRate, format: .number)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 80)
                    }
                }
                
                // MARK: - Availability
                Section("Availability") {
                    Toggle("24 Hours", isOn: $is24Hours)
                    
                    if !is24Hours {
                        DatePicker("Start Time", selection: $availableStartTime, displayedComponents: .hourAndMinute)
                        
                        DatePicker("End Time", selection: $availableEndTime, displayedComponents: .hourAndMinute)
                    }
                    
                    VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
                        Text("Available Days")
                            .font(.subheadline)
                        
                        HStack(spacing: 6) {
                            ForEach(1...7, id: \.self) { day in
                                Button {
                                    if selectedDays.contains(day) {
                                        selectedDays.remove(day)
                                    } else {
                                        selectedDays.insert(day)
                                    }
                                } label: {
                                    Text(dayNames[day - 1])
                                        .font(.caption.bold())
                                        .frame(width: 36, height: 36)
                                        .background(selectedDays.contains(day) ? DesignSystem.Colors.primary : Color(.secondarySystemBackground))
                                        .foregroundColor(selectedDays.contains(day) ? .white : .primary)
                                        .clipShape(Circle())
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
                
                // MARK: - Amenities
                Section("Amenities") {
                    Toggle("Covered Parking", isOn: $isCovered)
                    Toggle("CCTV Surveillance", isOn: $hasCCTV)
                    Toggle("EV Charging", isOn: $hasEVCharging)
                    Toggle("Security Guard", isOn: $hasSecurityGuard)
                    Toggle("Car Wash / Water", isOn: $hasWaterAccess)
                }
                
                // MARK: - Booking Settings
                Section("Booking Settings") {
                    Toggle("Auto-Accept Bookings", isOn: $autoAcceptBookings)
                    
                    if autoAcceptBookings {
                        Text("Bookings will be automatically confirmed")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    } else {
                        Text("You'll need to manually approve each booking request")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                // MARK: - Protected Media Notice
                Section {
                    HStack(spacing: 12) {
                        Image(systemName: "lock.fill")
                            .foregroundColor(.orange)
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Original Photo & Video")
                                .font(.subheadline.bold())
                            Text("The first photo and video cannot be modified to ensure listing authenticity")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.vertical, 4)
                }
                
                // MARK: - Error Message
                if let error = errorMessage {
                    Section {
                        Text(error)
                            .foregroundColor(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Edit Listing")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        saveChanges()
                    } label: {
                        if isSaving {
                            ProgressView()
                        } else {
                            Text("Save")
                                .fontWeight(.semibold)
                        }
                    }
                    .disabled(isSaving || !isValid)
                }
            }
            .alert("Changes Saved", isPresented: $showSaveSuccess) {
                Button("OK") {
                    dismiss()
                }
            } message: {
                Text("Your listing has been updated successfully.")
            }
        }
    }
    
    private var isValid: Bool {
        !title.trimmingCharacters(in: .whitespaces).isEmpty &&
        hourlyRate > 0 &&
        !selectedDays.isEmpty
    }
    
    private func saveChanges() {
        isSaving = true
        errorMessage = nil
        
        // Create updated listing
        var updatedListing = listing
        updatedListing.title = title
        updatedListing.listingDescription = listingDescription
        updatedListing.hourlyRate = hourlyRate
        updatedListing.dailyRate = dailyRate ?? 0.0 // Unwrap optional
        updatedListing.monthlyRate = monthlyRate ?? 0.0 // Unwrap optional
        updatedListing.availableFrom = is24Hours ? nil : availableStartTime
        updatedListing.availableTo = is24Hours ? nil : availableEndTime
        updatedListing.availableDays = Array(selectedDays)
        updatedListing.is24Hours = is24Hours
        updatedListing.isCovered = isCovered
        updatedListing.hasCCTV = hasCCTV
        updatedListing.hasEVCharging = hasEVCharging
        updatedListing.hasSecurityGuard = hasSecurityGuard
        updatedListing.hasWaterAccess = hasWaterAccess
        updatedListing.autoAcceptBookings = autoAcceptBookings
        
        // Update via view model
        viewModel.updateListing(updatedListing) { success in
            DispatchQueue.main.async {
                isSaving = false
                if success {
                    showSaveSuccess = true
                } else {
                    errorMessage = "Failed to save changes. Please try again."
                }
            }
        }
    }
}

// MARK: - Preview

#Preview {
    EditPrivateListingView(
        listing: PrivateParkingListing(
            id: UUID(),
            ownerID: UUID(),
            ownerName: "Test Host",
            title: "Spacious Driveway",
            address: "123 Main St",
            coordinates: CLLocationCoordinate2D(latitude: 28.5, longitude: 77.2),
            listingDescription: "A nice parking spot with shade",
            slots: [],
            hourlyRate: 50,
            dailyRate: 400,
            monthlyRate: 5000,
            flatFullBookingRate: nil,
            autoAcceptBookings: true,
            instantBookingDiscount: nil,
            hasCCTV: true,
            isCovered: true,
            hasEVCharging: false,
            hasSecurityGuard: true,
            hasWaterAccess: false,
            is24Hours: false,
            availableFrom: Calendar.current.date(bySettingHour: 9, minute: 0, second: 0, of: Date()),
            availableTo: Calendar.current.date(bySettingHour: 18, minute: 0, second: 0, of: Date()),
            availableDays: [1, 2, 3, 4, 5],
            rating: 4.5,
            reviewCount: 25,
            imageURLs: [],
            capturedPhotoData: nil,
            capturedVideoURL: nil,
            maxBookingDuration: .unlimited,
            suggestedHourlyRate: 45
        )
    )
    .environmentObject(PrivateParkingViewModel())
}
