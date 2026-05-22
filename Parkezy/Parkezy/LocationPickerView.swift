//
//  LocationPickerView.swift
//  ParkEzy
//
//  Reusable map-based location picker for selecting precise coordinates
//

import SwiftUI
import MapKit

struct LocationPickerView: View {
    @Environment(\.dismiss) var dismiss
    @Binding var selectedCoordinate: CLLocationCoordinate2D?
    @Binding var selectedAddress: String
    
    @State private var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090), // Default: New Delhi
        span: MKCoordinateSpan(latitudeDelta: 0.01, longitudeDelta: 0.01)
    )
    @State private var searchText = ""
    @State private var markerPosition: CLLocationCoordinate2D?
    @State private var isSearching = false
    var body: some View {
        NavigationStack {
            ZStack(alignment: .top) {
                // Map View
                Map(coordinateRegion: $region, interactionModes: .all, showsUserLocation: true, annotationItems: markerPosition != nil ? [MapMarker(coordinate: markerPosition!)] : []) { marker in
                    MapPin(coordinate: marker.coordinate, tint: .red)
                }
                .onTapGesture(coordinateSpace: .local) { location in
                    // Convert tap location to coordinate
                    // This is approximate, MapKit doesn't provide direct tap-to-coordinate
                    // For better implementation, use UIViewRepresentable with MKMapView
                }
                .ignoresSafeArea(edges: .bottom)
                
                // Search Bar
                VStack(spacing: 0) {
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundColor(.gray)
                        TextField("Search for address", text: $searchText)
                            .textFieldStyle(.plain)
                            .onSubmit {
                                searchAddress()
                            }
                        if !searchText.isEmpty {
                            Button(action: { searchText = "" }) {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundColor(.gray)
                            }
                        }
                    }
                    .padding()
                    .background(Color(.systemBackground))
                    .cornerRadius(12)
                    .shadow(radius: 4)
                    .padding()
                    
                    Spacer()
                }
                
                // Center Pin Indicator
                VStack {
                    Spacer()
                    Image(systemName: "mappin.circle.fill")
                        .font(.system(size: 50))
                        .foregroundColor(.red)
                    Spacer()
                }
                .allowsHitTesting(false)
                
                // Bottom Action Card
                VStack {
                    Spacer()
                    
                    VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
                        if let coord = markerPosition ?? (region.center.latitude != 28.6139 ? region.center : nil) {
                            Text("Selected Location")
                                .font(.headline)
                            
                            if !selectedAddress.isEmpty {
                                Text(selectedAddress)
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                            }
                            
                            Text("Lat: \(String(format: "%.6f", coord.latitude)), Lon: \(String(format: "%.6f", coord.longitude))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Button(action: confirmLocation) {
                                HStack {
                                    Image(systemName: "checkmark.circle.fill")
                                    Text("Confirm Location")
                                }
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(DesignSystem.Colors.primary)
                                .foregroundColor(.white)
                                .cornerRadius(12)
                            }
                        } else {
                            Text("Move map to select location")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .frame(maxWidth: .infinity, alignment: .center)
                        }
                    }
                    .padding()
                    .background(Color(.systemBackground))
                    .cornerRadius(16, corners: [.topLeft, .topRight])
                    .shadow(radius: 8)
                }
            }
            .navigationTitle("Select Location")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        centerOnUserLocation()
                    } label: {
                        Image(systemName: "location.fill")
                    }
                }
            }
            .onChange(of: region.center) { newCenter in
                // Update selected coordinates as map moves
                markerPosition = newCenter
                reverseGeocode(coordinate: newCenter)
            }
        }
    }
    
    private func searchAddress() {
        isSearching = true
        let searchRequest = MKLocalSearch.Request()
        searchRequest.naturalLanguageQuery = searchText
        searchRequest.region = region
        
        let search = MKLocalSearch(request: searchRequest)
        search.start { response, error in
            isSearching = false
            guard let response = response, let firstItem = response.mapItems.first else {
                return
            }
            
            let coordinate = firstItem.placemark.coordinate
            region = MKCoordinateRegion(
                center: coordinate,
                span: MKCoordinateSpan(latitudeDelta: 0.01, longitudeDelta: 0.01)
            )
            markerPosition = coordinate
            selectedAddress = firstItem.placemark.title ?? searchText
        }
    }
    
    private func reverseGeocode(coordinate: CLLocationCoordinate2D) {
        let geocoder = CLGeocoder()
        let location = CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)
        
        geocoder.reverseGeocodeLocation(location) { placemarks, error in
            guard let placemark = placemarks?.first, error == nil else {
                selectedAddress = "Unknown Location"
                return
            }
            
            var addressParts: [String] = []
            if let name = placemark.name { addressParts.append(name) }
            if let locality = placemark.locality { addressParts.append(locality) }
            if let administrativeArea = placemark.administrativeArea { addressParts.append(administrativeArea) }
            
            selectedAddress = addressParts.joined(separator: ", ")
        }
    }
    
    private func centerOnUserLocation() {
        // Request user location
        // This would typically use CLLocationManager
        // For now, default to Delhi
    }
    
    private func confirmLocation() {
        selectedCoordinate = markerPosition ?? region.center
        dismiss()
    }
}

// Helper for map markers
struct MapMarker: Identifiable {
    let id = UUID()
    let coordinate: CLLocationCoordinate2D
}


#Preview {
    LocationPickerView(
        selectedCoordinate: .constant(nil),
        selectedAddress: .constant("")
    )
}
