
import SwiftUI
import CoreLocation

struct AddPrivateListingView: View {
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: PrivateParkingViewModel
    
    // Listing Details
    @State private var title = ""
    @State private var address = ""
    @State private var coordinates: CLLocationCoordinate2D?
    @State private var description = ""
    @State private var slots = 1
    
    // Pricing
    @State private var hourlyRate: Double = 40
    
    // Amenities
    @State private var isCovered = false
    @State private var hasCCTV = false
    @State private var hasEV = false
    
    // Location Picker
    @State private var showLocationPicker = false
    
    // Validation
    var isValid: Bool {
        !title.isEmpty && !address.isEmpty && coordinates != nil && slots > 0
    }
    
    var body: some View {
        NavigationStack {
            Form {
                Section("Location") {
                    TextField("Listing Title", text: $title)
                    
                    VStack(alignment: .leading) {
                        if address.isEmpty {
                            Button(action: { showLocationPicker = true }) {
                                HStack {
                                    Image(systemName: "map.fill")
                                    Text("Select Location on Map")
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                }
                            }
                        } else {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Address")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Text(address)
                                    .font(.subheadline)
                                Button("Change Location") {
                                    showLocationPicker = true
                                }
                                .font(.caption)
                            }
                        }
                    }
                }
                
                Section("Capacity") {
                    Stepper(value: $slots, in: 1...10) {
                        HStack {
                            Text("Number of Slots")
                            Spacer()
                            Text("\(slots)")
                                .fontWeight(.bold)
                                .foregroundColor(DesignSystem.Colors.primary)
                        }
                    }
                }
                
                Section("Hourly Pricing") {
                    HStack {
                        Text("Rate per Hour")
                        Spacer()
                        TextField("₹", value: $hourlyRate, format: .number)
                            .keyboardType(.numberPad)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 80)
                    }
                }
                
                Section("Description") {
                    TextField("Describe your parking space", text: $description, axis: .vertical)
                        .lineLimit(3...5)
                }
                
                Section("Amenities") {
                    Toggle("Covered Parking", isOn: $isCovered)
                    Toggle("CCTV Surveillance", isOn: $hasCCTV)
                    Toggle("EV Charging", isOn: $hasEV)
                }
                
                Section {
                    Button(action: createListing) {
                        Text("Create Listing")
                            .font(.headline)
                            .frame(maxWidth: .infinity, alignment: .center)
                            .padding(.vertical, 4)
                    }
                    .disabled(!isValid)
                }
            }
            .navigationTitle("Add New Listing")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .sheet(isPresented: $showLocationPicker) {
                LocationPickerView(
                    selectedCoordinate: $coordinates,
                    selectedAddress: $address
                )
            }
        }
    }
    
    private func createListing() {
        guard let coords = coordinates else { return }
        viewModel.addListingWithCoordinates(
            title: title,
            address: address,
            coordinates: coords,
            slots: slots,
            hourlyRate: hourlyRate,
            isCovered: isCovered,
            hasCCTV: hasCCTV,
            hasEV: hasEV,
            description: description.isEmpty ? "A great parking spot." : description
        )
        dismiss()
    }
}

#Preview {
    AddPrivateListingView()
        .environmentObject(PrivateParkingViewModel())
}
