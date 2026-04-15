//
//  HomeMapView.swift
//  ParkEzy
//
//  Main driver view with MapKit integration showing all parking spots
//

import SwiftUI
import MapKit

struct HomeMapView: View {
    // MARK: - Environment
    
    @EnvironmentObject var mapViewModel: MapViewModel
    @EnvironmentObject var bookingViewModel: BookingViewModel
    
    // MARK: - State
    
    @State private var selectedSpot: ParkingSpot?
    @State private var showSpotDetail = false
    @State private var showFilters = false
    @State private var searchText = ""
    @State private var cameraPosition: MapCameraPosition = .automatic
    
    // MARK: - Body
    
    var body: some View {
        ZStack(alignment: .top) {
            mapView
            searchBarView
            statsView
        }
        .sheet(isPresented: $showSpotDetail) {
            if let spot = selectedSpot {
                SpotDetailSheet(spot: spot, isPresented: $showSpotDetail)
            }
        }
        .onAppear {
            setupMap()
        }
        .onChange(of: selectedSpot) { _, newSpot in
            if let spot = newSpot {
                withAnimation(.easeInOut(duration: 0.5)) {
                    cameraPosition = .camera(
                        MapCamera(
                            centerCoordinate: spot.coordinates,
                            distance: 1000
                        )
                    )
                }
            }
        }
        .navigationTitle("Find Parking")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    // MARK: - Computed Properties
    
    private var filteredSpots: [ParkingSpot] {
        mapViewModel.filteredSpots(searchQuery: searchText)
    }
    
    // MARK: - View Components
    
    private var mapView: some View {
        Map(position: $cameraPosition, selection: $selectedSpot) {
            UserAnnotation()
            
            ForEach(filteredSpots) { spot in
                Annotation(spot.address, coordinate: spot.coordinates) {
                    SpotAnnotationView(spot: spot, isSelected: selectedSpot?.id == spot.id)
                        .onTapGesture {
                            withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
                                selectedSpot = spot
                                showSpotDetail = true
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
    
    private var searchBarView: some View {
        VStack(spacing: 0) {
            HStack(spacing: DesignSystem.Spacing.m) {
                HStack {
                    Image(systemName: mapViewModel.isGeocoding ? "" : "magnifyingglass")
                        .foregroundColor(.gray)
                    
                    if mapViewModel.isGeocoding {
                        ProgressView()
                            .scaleEffect(0.8)
                    }
                    
                    TextField("Search places (e.g., Noida, Delhi)...", text: $searchText)
                        .textFieldStyle(.plain)
                        .onSubmit {
                            performSearch()
                        }
                    
                    if !searchText.isEmpty {
                        Button {
                            searchText = ""
                            mapViewModel.clearLocationSearch()
                            returnToUserLocation()
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.gray)
                        }
                    }
                }
                .padding(DesignSystem.Spacing.m)
                .background(Color.white)
                .cornerRadius(DesignSystem.Spacing.m)
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
            
            if showFilters {
                FilterPillsView(mapViewModel: mapViewModel)
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(.spring(response: 0.3, dampingFraction: 0.8), value: showFilters)
    }
    
    private var statsView: some View {
        VStack {
            Spacer()
            
            HStack(spacing: DesignSystem.Spacing.l) {
                StatCard(
                    icon: "parkingsign.circle.fill",
                    title: "\(filteredSpots.count)",
                    subtitle: "Available"
                )
                
                if let nearest = mapViewModel.nearestSpot {
                    StatCard(
                        icon: "location.fill",
                        title: String(format: "%.1f km", nearest.distance / 1000),
                        subtitle: "Nearest"
                    )
                }
                
                if let cheapest = filteredSpots.min(by: { $0.pricePerHour < $1.pricePerHour }) {
                    StatCard(
                        icon: "indianrupeesign.circle.fill",
                        title: "₹\(Int(cheapest.pricePerHour))",
                        subtitle: "From"
                    )
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(
                .ultraThinMaterial,
                in: RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
            )
            .shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 5)
            .padding(DesignSystem.Spacing.m)
        }
    }
    
    // MARK: - Methods
    
    private func setupMap() {
        mapViewModel.loadParkingSpots()
        mapViewModel.startLocationTracking()
        
        if let userLocation = mapViewModel.userLocation {
            cameraPosition = .camera(
                MapCamera(
                    centerCoordinate: userLocation.coordinate,
                    distance: 5000
                )
            )
        } else {
            cameraPosition = .camera(
                MapCamera(
                    centerCoordinate: CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090),
                    distance: 10000
                )
            )
        }
    }
    
    private func performSearch() {
        mapViewModel.searchLocation(query: searchText) { coordinate in
            guard let coordinate = coordinate else {
                print("Location not found")
                return
            }
            
            withAnimation(.easeInOut(duration: 0.8)) {
                cameraPosition = .camera(
                    MapCamera(
                        centerCoordinate: coordinate,
                        distance: 3000
                    )
                )
            }
        }
    }
    
    private func returnToUserLocation() {
        if let userLocation = mapViewModel.userLocation {
            withAnimation(.easeInOut(duration: 0.6)) {
                cameraPosition = .camera(
                    MapCamera(
                        centerCoordinate: userLocation.coordinate,
                        distance: 5000
                    )
                )
            }
        }
    }
}

// MARK: - Spot Annotation View

struct SpotAnnotationView: View {
    let spot: ParkingSpot
    let isSelected: Bool
    
    var body: some View {
        VStack(spacing: 4) {
            ZStack {
                Circle()
                    .fill(spot.isOccupied ? DesignSystem.Colors.error : DesignSystem.Colors.success)
                    .frame(width: isSelected ? 50 : 40, height: isSelected ? 50 : 40)
                    .shadow(color: .black.opacity(0.3), radius: 5, x: 0, y: 2)
                
                Image(systemName: "parkingsign")
                    .font(.system(size: isSelected ? 24 : 20))
                    .foregroundColor(.white)
            }
            
            if isSelected {
                Text("₹\(Int(spot.pricePerHour))/hr")
                    .font(.caption.bold())
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.white)
                    .cornerRadius(4)
                    .shadow(color: .black.opacity(0.2), radius: 2, x: 0, y: 1)
            }
        }
        .scaleEffect(isSelected ? 1.2 : 1.0)
        .animation(.spring(response: 0.3, dampingFraction: 0.6), value: isSelected)
    }
}

// MARK: - Filter Pills View

struct FilterPillsView: View {
    @ObservedObject var mapViewModel: MapViewModel
    
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: DesignSystem.Spacing.s) {
                FilterPill(
                    icon: "bolt.car.fill",
                    title: "EV Charging",
                    isActive: mapViewModel.filterEVCharging
                ) {
                    mapViewModel.filterEVCharging.toggle()
                }
                
                FilterPill(
                    icon: "shield.fill",
                    title: "CCTV",
                    isActive: mapViewModel.filterCCTV
                ) {
                    mapViewModel.filterCCTV.toggle()
                }
                
                FilterPill(
                    icon: "umbrella.fill",
                    title: "Covered",
                    isActive: mapViewModel.filterCovered
                ) {
                    mapViewModel.filterCovered.toggle()
                }
                
                FilterPill(
                    icon: "indianrupeesign.circle.fill",
                    title: "Under ₹60",
                    isActive: mapViewModel.filterMaxPrice != nil
                ) {
                    if mapViewModel.filterMaxPrice != nil {
                        mapViewModel.filterMaxPrice = nil
                    } else {
                        mapViewModel.filterMaxPrice = 60
                    }
                }
            }
            .padding(.horizontal, DesignSystem.Spacing.m)
            .padding(.vertical, DesignSystem.Spacing.s)
        }
        .background(Color.white.opacity(0.95))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 3, x: 0, y: 2)
        .padding(.horizontal, DesignSystem.Spacing.m)
    }
}

// MARK: - Filter Pill Component

struct FilterPill: View {
    let icon: String
    let title: String
    let isActive: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption)
                Text(title)
                    .font(.caption.bold())
            }
            .padding(.horizontal, DesignSystem.Spacing.m)
            .padding(.vertical, DesignSystem.Spacing.s)
            .background(isActive ? DesignSystem.Colors.primary : Color.gray.opacity(0.2))
            .foregroundColor(isActive ? .white : .primary)
            .cornerRadius(20)
        }
    }
}

// MARK: - Stat Card Component

struct StatCard: View {
    let icon: String
    let title: String
    let subtitle: String
    
    var body: some View {
        VStack(spacing: 4) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(DesignSystem.Colors.primary)
            
            Text(title)
                .font(.headline)
                .foregroundColor(.primary)
            
            Text(subtitle)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        HomeMapView()
            .environmentObject(MapViewModel())
            .environmentObject(BookingViewModel())
    }
}
