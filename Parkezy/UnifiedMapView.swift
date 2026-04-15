//
//  UnifiedMapView.swift
//  ParkEzy
//
//  Driver map view showing both Commercial and Private parking
//

import SwiftUI
import MapKit

struct UnifiedMapView: View {
    // MARK: - Environment
    
    @EnvironmentObject var commercialViewModel: CommercialParkingViewModel
    @EnvironmentObject var privateViewModel: PrivateParkingViewModel
    @EnvironmentObject var mapViewModel: MapViewModel
    
    // MARK: - State
    
    @State private var cameraPosition: MapCameraPosition = .automatic
    @State private var selectedCommercialFacility: CommercialParkingFacility?
    @State private var selectedPrivateListing: PrivateParkingListing?
    @State private var showCommercialDetail = false
    @State private var showPrivateDetail = false
    @State private var showFilters = false
    @State private var searchText = ""
    
    // Filters
    @State private var showCommercial = true
    @State private var showPrivate = true
    @State private var filterHasEV = false
    
    // MARK: - Body
    
    var body: some View {
        ZStack(alignment: .top) {
            // MARK: - Map
            mapView
            
            // MARK: - Top Controls
            VStack(spacing: 0) {
                searchBar
                
                if showFilters {
                    filterSection
                        .transition(.move(edge: .top).combined(with: .opacity))
                }
            }
            .animation(.spring(response: 0.3), value: showFilters)
            
            // MARK: - Bottom Stats
            VStack {
                Spacer()
                bottomStatsBar
            }
        }
        .sheet(isPresented: $showCommercialDetail) {
            if let facility = selectedCommercialFacility {
                NavigationStack {
                    CommercialFacilityDetailView(facility: facility)
                }
            }
        }
        .sheet(isPresented: $showPrivateDetail) {
            if let listing = selectedPrivateListing {
                NavigationStack {
                    EnhancedPrivateListingDetailView(listing: listing)
                        .environmentObject(privateViewModel)
                }
            }
        }
        .onAppear {
            setupMap()
            Task {
                await loadParkingDataFromBackend()
            }
        }
        .refreshable {
            await loadParkingDataFromBackend()
        }
        .navigationTitle("Find Parking")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    // MARK: - Map View
    
    private var mapView: some View {
        Map(position: $cameraPosition) {
            UserAnnotation()
            
            // Search Result Marker
            if let searchLoc = mapViewModel.searchedLocation {
                Marker(searchText.isEmpty ? "Searched Location" : searchText, systemImage: "mappin.circle.fill", coordinate: searchLoc)
                    .tint(.red)
            }
            
            // Commercial Facility Markers
            if showCommercial {
                ForEach(filteredCommercialFacilities) { facility in
                    Annotation(facility.name, coordinate: facility.coordinates) {
                        CommercialAnnotationView(facility: facility)
                            .onTapGesture {
                                withAnimation(.spring(response: 0.4)) {
                                    selectedCommercialFacility = facility
                                    showCommercialDetail = true
                                    centerOnCoordinate(facility.coordinates)
                                }
                            }
                    }
                }
            }
            
            // Private Listing Markers
            if showPrivate {
                ForEach(filteredPrivateListings) { listing in
                    Annotation(listing.title, coordinate: listing.coordinates) {
                        PrivateAnnotationView(listing: listing)
                            .onTapGesture {
                                withAnimation(.spring(response: 0.4)) {
                                    selectedPrivateListing = listing
                                    showPrivateDetail = true
                                    centerOnCoordinate(listing.coordinates)
                                }
                            }
                    }
                }
            }
        }
        .mapStyle(.standard(elevation: .realistic))
        .mapControls {
            MapUserLocationButton()
            MapCompass()
            MapScaleView()
        }
        .ignoresSafeArea()
    }
    
    // MARK: - Search Bar
    
    private var searchBar: some View {
        HStack(spacing: DesignSystem.Spacing.m) {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.gray)
                
                TextField("Search parking...", text: $searchText)
                    .textFieldStyle(.plain)
                    .onSubmit {
                        performSearch()
                    }
                
                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.gray)
                    }
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(Color.white)
            .cornerRadius(12)
            .shadow(color: .black.opacity(0.1), radius: 5, x: 0, y: 2)
            
            Button {
                showFilters.toggle()
            } label: {
                Image(systemName: showFilters ? "line.3.horizontal.decrease.circle.fill" : "line.3.horizontal.decrease.circle")
                    .font(.title2)
                    .foregroundColor(DesignSystem.Colors.primary)
                    .padding(DesignSystem.Spacing.m)
                    .background(Color.white)
                    .clipShape(Circle())
                    .shadow(color: .black.opacity(0.1), radius: 5, x: 0, y: 2)
            }
        }
        .padding(.horizontal, DesignSystem.Spacing.m)
        .padding(.top, DesignSystem.Spacing.m)
    }
    
    // MARK: - Filter Section
    
    private var filterSection: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: DesignSystem.Spacing.s) {
                FilterChip(
                    label: "Commercial",
                    icon: "building.2.fill",
                    isSelected: showCommercial
                ) {
                    showCommercial.toggle()
                }
                
                FilterChip(
                    label: "Private",
                    icon: "house.fill",
                    isSelected: showPrivate
                ) {
                    showPrivate.toggle()
                }
                
                FilterChip(
                    label: "EV Charging",
                    icon: "bolt.car.fill",
                    isSelected: filterHasEV
                ) {
                    filterHasEV.toggle()
                }
            }
            .padding(.horizontal, DesignSystem.Spacing.m)
            .padding(.vertical, DesignSystem.Spacing.s)
        }
        .background(Color(.systemBackground).opacity(0.95))
    }
    
    // MARK: - Bottom Stats Bar
    
    private var bottomStatsBar: some View {
        HStack(spacing: DesignSystem.Spacing.l) {
            // Commercial count
            if showCommercial {
                MiniStatCard(
                    icon: "building.2.fill",
                    value: "\(filteredCommercialFacilities.count)",
                    label: "Commercial",
                    color: .blue
                )
            }
            
            // Private count
            if showPrivate {
                MiniStatCard(
                    icon: "house.fill",
                    value: "\(filteredPrivateListings.count)",
                    label: "Private",
                    color: .orange
                )
            }
            
            // Cheapest
            if let cheapest = cheapestOption {
                MiniStatCard(
                    icon: "indianrupeesign.circle.fill",
                    value: "₹\(cheapest)",
                    label: "From",
                    color: .green
                )
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.1), radius: 10)
        .padding(DesignSystem.Spacing.m)
    }
    
    // MARK: - Computed Properties
    
    private var filteredCommercialFacilities: [CommercialParkingFacility] {
        commercialViewModel.facilities.filter { facility in
            if filterHasEV && !facility.hasEVCharging { return false }
            return true
        }
    }
    
    private var filteredPrivateListings: [PrivateParkingListing] {
        privateViewModel.listings.filter { listing in
            if filterHasEV && !listing.hasEVCharging { return false }
            if listing.availableSlots == 0 { return false }
            return true
        }
    }
    
    private var cheapestOption: Int? {
        var prices: [Double] = []
        if showCommercial {
            prices.append(contentsOf: filteredCommercialFacilities.map { $0.defaultHourlyRate })
        }
        if showPrivate {
            prices.append(contentsOf: filteredPrivateListings.map { $0.hourlyRate })
        }
        return prices.min().map { Int($0) }
    }
    
    // MARK: - Methods
    
    private func setupMap() {
        if let userLocation = mapViewModel.userLocation {
            cameraPosition = .camera(MapCamera(centerCoordinate: userLocation.coordinate, distance: 8000))
        } else {
            // Default to Delhi
            cameraPosition = .camera(MapCamera(
                centerCoordinate: CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090),
                distance: 15000
            ))
        }
    }
    
    private func loadParkingDataFromBackend(near coordinate: CLLocationCoordinate2D? = nil) async {
        // Get search location or user location
        let location = coordinate ?? mapViewModel.userLocation?.coordinate ?? CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090)
            
        // Load private listings
        await privateViewModel.refreshListingsFromBackend(near: location)
            
        // Load commercial facilities
        // await commercialViewModel.refreshFacilitiesFromBackend(near: location)
            
        print("🔄 Refreshed parking data from backend")
    }
    
    private func centerOnCoordinate(_ coordinate: CLLocationCoordinate2D) {
        withAnimation(.easeInOut(duration: 0.5)) {
            cameraPosition = .camera(MapCamera(centerCoordinate: coordinate, distance: 2000))
        }
    }
    
    private func performSearch() {
        guard !searchText.isEmpty else { return }
        
        mapViewModel.searchLocation(query: searchText) { coordinate in
            if let coordinate = coordinate {
                centerOnCoordinate(coordinate)
                Task {
                    await loadParkingDataFromBackend(near: coordinate)
                }
            }
        }
    }
}

// MARK: - Commercial Annotation View

struct CommercialAnnotationView: View {
    let facility: CommercialParkingFacility
    
    var body: some View {
        VStack(spacing: 2) {
            ZStack {
                Circle()
                    .fill(facility.facilityType.color)
                    .frame(width: 44, height: 44)
                    .shadow(color: facility.facilityType.color.opacity(0.5), radius: 4)
                
                Image(systemName: facility.facilityType.icon)
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(.white)
            }
            
            // Availability badge
            Text("\(facility.availableSlots)")
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(.white)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(facility.availableSlots > 0 ? Color.green : Color.red)
                .cornerRadius(8)
        }
    }
}

// MARK: - Private Annotation View

struct PrivateAnnotationView: View {
    let listing: PrivateParkingListing
    
    var body: some View {
        VStack(spacing: 2) {
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [.orange, .pink],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 40, height: 40)
                    .shadow(color: .orange.opacity(0.5), radius: 4)
                
                Image(systemName: "house.fill")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundColor(.white)
            }
            
            // Price badge
            Text("₹\(Int(listing.hourlyRate))")
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(.white)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(listing.priceCompetitiveness == .competitive ? Color.green : Color.orange)
                .cornerRadius(8)
        }
    }
}

// MARK: - Filter Chip

struct FilterChip: View {
    let label: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.caption)
                Text(label)
                    .font(.caption.bold())
            }
            .foregroundColor(isSelected ? .white : .primary)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(isSelected ? DesignSystem.Colors.primary : Color(.tertiarySystemBackground))
            .cornerRadius(20)
        }
    }
}

// MARK: - Mini Stat Card

struct MiniStatCard: View {
    let icon: String
    let value: String
    let label: String
    let color: Color
    
    var body: some View {
        VStack(spacing: 2) {
            Image(systemName: icon)
                .font(.caption)
                .foregroundColor(color)
            Text(value)
                .font(.subheadline.bold())
            Text(label)
                .font(.system(size: 9))
                .foregroundColor(.secondary)
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        UnifiedMapView()
            .environmentObject(CommercialParkingViewModel())
            .environmentObject(PrivateParkingViewModel())
            .environmentObject(MapViewModel())
    }
}
