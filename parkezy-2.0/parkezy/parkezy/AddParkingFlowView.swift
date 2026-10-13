    //
//  AddParkingFlowView.swift
//  ParkEzy
//
//  Multi-step wizard for adding a new parking listing
//  Steps: Location → Photos/Video → Details & Schedule → Review
//

import SwiftUI
import MapKit
import CoreLocation

// MARK: - Flow Step Enum

enum AddParkingStep: Int, CaseIterable {
    case location = 0
    case media = 1
    case details = 2
    case review = 3
    
    var title: String {
        switch self {
        case .location: return "Location"
        case .media: return "Photos & Video"
        case .details: return "Details"
        case .review: return "Review"
        }
    }
    
    var icon: String {
        switch self {
        case .location: return "location.fill"
        case .media: return "camera.fill"
        case .details: return "doc.text.fill"
        case .review: return "checkmark.circle.fill"
        }
    }
}

// MARK: - Parking Mode

enum ParkingMode: String, CaseIterable {
    case private_ = "Private"  // Schedule-based parking with owner-defined availability
    case commercial = "Commercial"  // Real-time parking with automatic tracking
    
    var displayName: String {
        return self.rawValue
    }
}

// MARK: - Main Flow View

struct AddParkingFlowView: View {
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var viewModel: PrivateParkingViewModel
    
    // MARK: - Flow State
    
    @State private var currentStep: AddParkingStep = .location
    
    // MARK: - Location Data
    
    @State private var selectedCoordinate: CLLocationCoordinate2D?
    @State private var selectedAddress: String = ""
    
    // MARK: - Media Data
    
    @State private var capturedPhotos: [UIImage] = []
    @State private var hasRecordedVideo: Bool = false
    
    // MARK: - Listing Details
    
    @State private var parkingMode: ParkingMode = .private_  // Default to Private mode
    @State private var title: String = ""
    @State private var listingDescription: String = ""
    @State private var numberOfSlots: Int = 1
    @State private var hourlyRate: Double = 40
    
    // MARK: - Availability Schedule (Private Mode Only)
    
    @State private var availableStartTime: Date = Calendar.current.date(from: DateComponents(hour: 9, minute: 0)) ?? Date()
    @State private var availableEndTime: Date = Calendar.current.date(from: DateComponents(hour: 22, minute: 0)) ?? Date()
    @State private var selectedDays: Set<Int> = Set(1...7) // All days selected by default
    
    // MARK: - Amenities
    
    @State private var isCovered: Bool = false
    @State private var hasCCTV: Bool = false
    @State private var hasEVCharging: Bool = false
    
    // MARK: - UI State
    
    @State private var isSubmitting: Bool = false
    @State private var showError: Bool = false
    @State private var errorMessage: String = ""
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Progress Indicator
                progressIndicator
                
                // Content
                TabView(selection: $currentStep) {
                    LocationStepView(
                        selectedCoordinate: $selectedCoordinate,
                        selectedAddress: $selectedAddress
                    )
                    .tag(AddParkingStep.location)
                    
                    MediaStepView(
                        capturedPhotos: $capturedPhotos,
                        hasRecordedVideo: $hasRecordedVideo
                    )
                    .tag(AddParkingStep.media)
                    
                    DetailsStepView(
                        parkingMode: $parkingMode,
                        title: $title,
                        listingDescription: $listingDescription,
                        numberOfSlots: $numberOfSlots,
                        hourlyRate: $hourlyRate,
                        availableStartTime: $availableStartTime,
                        availableEndTime: $availableEndTime,
                        selectedDays: $selectedDays,
                        isCovered: $isCovered,
                        hasCCTV: $hasCCTV,
                        hasEVCharging: $hasEVCharging
                    )
                    .tag(AddParkingStep.details)
                    
                    ReviewStepView(
                        parkingMode: parkingMode,
                        address: selectedAddress,
                        photoCount: capturedPhotos.count,
                        hasVideo: hasRecordedVideo,
                        title: title,
                        slots: numberOfSlots,
                        hourlyRate: hourlyRate,
                        startTime: availableStartTime,
                        endTime: availableEndTime,
                        selectedDays: selectedDays,
                        amenities: (isCovered, hasCCTV, hasEVCharging)
                    )
                    .tag(AddParkingStep.review)
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                .animation(.easeInOut, value: currentStep)
                
                // Navigation Buttons
                navigationButtons
            }
            .navigationTitle("Add Parking")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage)
            }
        }
    }
    
    // MARK: - Progress Indicator
    
    private var progressIndicator: some View {
        HStack(spacing: 0) {
            ForEach(AddParkingStep.allCases, id: \.self) { step in
                HStack(spacing: 4) {
                    ZStack {
                        Circle()
                            .fill(step.rawValue <= currentStep.rawValue ? DesignSystem.Colors.primary : Color.gray.opacity(0.3))
                            .frame(width: 30, height: 30)
                        
                        if step.rawValue < currentStep.rawValue {
                            Image(systemName: "checkmark")
                                .font(.caption.bold())
                                .foregroundColor(.white)
                        } else {
                            Text("\(step.rawValue + 1)")
                                .font(.caption.bold())
                                .foregroundColor(step.rawValue <= currentStep.rawValue ? .white : .gray)
                        }
                    }
                    
                    if step != .review {
                        Rectangle()
                            .fill(step.rawValue < currentStep.rawValue ? DesignSystem.Colors.primary : Color.gray.opacity(0.3))
                            .frame(height: 2)
                    }
                }
            }
        }
        .padding(.horizontal, DesignSystem.Spacing.l)
        .padding(.vertical, DesignSystem.Spacing.m)
    }
    
    // MARK: - Navigation Buttons
    
    private var navigationButtons: some View {
        HStack(spacing: DesignSystem.Spacing.m) {
            // Back Button
            if currentStep != .location {
                Button {
                    withAnimation {
                        if let prevStep = AddParkingStep(rawValue: currentStep.rawValue - 1) {
                            currentStep = prevStep
                        }
                    }
                } label: {
                    HStack {
                        Image(systemName: "chevron.left")
                        Text("Back")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .foregroundColor(.primary)
                    .cornerRadius(12)
                }
                .buttonStyle(.plain)
            }
            
            // Next/Submit Button
            Button {
                if currentStep == .review {
                    submitListing()
                } else {
                    if validateCurrentStep() {
                        withAnimation {
                            if let nextStep = AddParkingStep(rawValue: currentStep.rawValue + 1) {
                                currentStep = nextStep
                            }
                        }
                    }
                }
            } label: {
                HStack {
                    Text(currentStep == .review ? "Submit Listing" : "Next")
                    if currentStep != .review {
                        Image(systemName: "chevron.right")
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(canProceed ? DesignSystem.Colors.primary : Color.gray.opacity(0.3))
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .buttonStyle(.plain)
            .disabled(!canProceed || isSubmitting)
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
    }
    
    // MARK: - Validation
    
    private var canProceed: Bool {
        switch currentStep {
        case .location:
            return selectedCoordinate != nil && !selectedAddress.isEmpty
        case .media:
            return !capturedPhotos.isEmpty && hasRecordedVideo
        case .details:
            // Private mode: Only need title and slots
            // Commercial mode: Also need hourly rate
            if parkingMode == .commercial {
                return !title.isEmpty && numberOfSlots > 0 && hourlyRate > 0
            } else {
                return !title.isEmpty && numberOfSlots > 0
            }
        case .review:
            return true
        }
    }
    
    private func validateCurrentStep() -> Bool {
        switch currentStep {
        case .location:
            if selectedCoordinate == nil {
                errorMessage = "Please confirm your location"
                showError = true
                return false
            }
        case .media:
            if capturedPhotos.isEmpty {
                errorMessage = "Please capture at least one photo"
                showError = true
                return false
            }
            if !hasRecordedVideo {
                errorMessage = "Please record a 10-second video"
                showError = true
                return false
            }
        case .details:
            if title.isEmpty {
                errorMessage = "Please enter a title for your listing"
                showError = true
                return false
            }
        case .review:
            break
        }
        return true
    }
    
    // MARK: - Submit
    
    private func submitListing() {
        guard let coordinates = selectedCoordinate else { return }
        
        isSubmitting = true
        
        // Convert images to data
        let photoData = capturedPhotos.compactMap { $0.jpegData(compressionQuality: 0.8) }
        
        // Create the listing based on mode
        if parkingMode == .private_ {
            // Private mode: Schedule-based, no pricing in this version
            viewModel.addListingWithFullDetails(
                title: title,
                address: selectedAddress,
                coordinates: coordinates,
                slots: numberOfSlots,
                hourlyRate: 0,  // Not used in Private mode for MVP
                dailyRate: 0,
                monthlyRate: 0,
                maxDuration: .unlimited,
                is24x7: false,  // Private always uses schedule
                availableStartTime: availableStartTime,
                availableEndTime: availableEndTime,
                availableDays: Array(selectedDays),
                isCovered: isCovered,
                hasCCTV: hasCCTV,
                hasEVCharging: hasEVCharging,
                photoData: photoData,
                description: listingDescription
            )
        } else {
            // Commercial mode: Real-time, hourly pricing only
            viewModel.addListingWithFullDetails(
                title: title,
                address: selectedAddress,
                coordinates: coordinates,
                slots: numberOfSlots,
                hourlyRate: hourlyRate,
                dailyRate: 0,  // Not used in Commercial MVP
                monthlyRate: 0, // Not used in Commercial MVP
                maxDuration: .unlimited,
                is24x7: true,  // Commercial is always real-time
                availableStartTime: nil,
                availableEndTime: nil,
                availableDays: Array(1...7),  // Always available
                isCovered: isCovered,
                hasCCTV: hasCCTV,
                hasEVCharging: hasEVCharging,
                photoData: photoData,
                description: listingDescription
            )
        }
        
        isSubmitting = false
        dismiss()
    }
}

// MARK: - Step 1: Location

struct LocationStepView: View {
    @Binding var selectedCoordinate: CLLocationCoordinate2D?
    @Binding var selectedAddress: String
    
    @StateObject private var locationManager = LocationManager.shared
    
    // Default location for simulator (Delhi)
    @State private var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090),
        span: MKCoordinateSpan(latitudeDelta: 0.01, longitudeDelta: 0.01)
    )
    
    @State private var hasConfirmedLocation = false
    
    var body: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            // Header
            VStack(spacing: DesignSystem.Spacing.s) {
                Image(systemName: "location.fill")
                    .font(.system(size: 40))
                    .foregroundColor(DesignSystem.Colors.primary)
                
                Text("Confirm Your Location")
                    .font(.title2.bold())
                
                Text(EmulatorDetector.isSimulator ?
                     "Simulator Mode: Using sample Delhi location" :
                     "Your GPS location will be used")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.top, DesignSystem.Spacing.l)
            
            // Map
            Map(coordinateRegion: $region, 
                interactionModes: .all,
                showsUserLocation: !EmulatorDetector.isSimulator)
                .frame(height: 250)
                .cornerRadius(16)
                .overlay(
                    // Center pin
                    Image(systemName: "mappin.circle.fill")
                        .font(.system(size: 40))
                        .foregroundColor(.red)
                )
                .padding(.horizontal)
            
            // Address Display
            if !selectedAddress.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Selected Location")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Text(selectedAddress)
                        .font(.subheadline)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(12)
                }
                .padding(.horizontal)
            }
            
            // Confirm Button
            Button {
                confirmLocation()
            } label: {
                HStack {
                    Image(systemName: hasConfirmedLocation ? "checkmark.circle.fill" : "location.fill")
                    Text(hasConfirmedLocation ? "Location Confirmed" : "Use This Location")
                }
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
                .background(hasConfirmedLocation ? DesignSystem.Colors.success : DesignSystem.Colors.primary)
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .padding(.horizontal)
            .disabled(hasConfirmedLocation)
            
            Spacer()
        }
        .onAppear {
            setupLocation()
        }
    }
    
    private func setupLocation() {
        if EmulatorDetector.isSimulator {
            // Use default Delhi location for simulator
            let delhiLocation = CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090)
            region.center = delhiLocation
            reverseGeocode(coordinate: delhiLocation)
        } else {
            // Use actual GPS location
            locationManager.requestLocationPermission()
            if let userLocation = locationManager.userLocation {
                region.center = userLocation.coordinate
                reverseGeocode(coordinate: userLocation.coordinate)
            }
        }
    }
    
    private func confirmLocation() {
        selectedCoordinate = region.center
        hasConfirmedLocation = true
        
        if selectedAddress.isEmpty {
            reverseGeocode(coordinate: region.center)
        }
    }
    
    private func reverseGeocode(coordinate: CLLocationCoordinate2D) {
        let geocoder = CLGeocoder()
        let location = CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)
        
        geocoder.reverseGeocodeLocation(location) { placemarks, error in
            guard let placemark = placemarks?.first, error == nil else {
                selectedAddress = "Location at \(String(format: "%.4f", coordinate.latitude)), \(String(format: "%.4f", coordinate.longitude))"
                return
            }
            
            var addressParts: [String] = []
            if let name = placemark.name { addressParts.append(name) }
            if let locality = placemark.locality { addressParts.append(locality) }
            if let administrativeArea = placemark.administrativeArea { addressParts.append(administrativeArea) }
            
            selectedAddress = addressParts.joined(separator: ", ")
        }
    }
}

// MARK: - Step 2: Media Capture

struct MediaStepView: View {
    @Binding var capturedPhotos: [UIImage]
    @Binding var hasRecordedVideo: Bool
    
    @State private var showingPhotoCapture = false
    @State private var isRecordingVideo = false
    @State private var videoProgress: Double = 0
    
    var body: some View {
        ScrollView {
            VStack(spacing: DesignSystem.Spacing.l) {
                // Header
                VStack(spacing: DesignSystem.Spacing.s) {
                    Image(systemName: "camera.fill")
                        .font(.system(size: 40))
                        .foregroundColor(DesignSystem.Colors.primary)
                    
                    Text("Capture Photos & Video")
                        .font(.title2.bold())
                    
                    if EmulatorDetector.isSimulator {
                        Text("Simulator Mode: Using placeholder media")
                            .font(.caption)
                            .foregroundColor(.orange)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color.orange.opacity(0.1))
                            .cornerRadius(8)
                    }
                }
                .padding(.top, DesignSystem.Spacing.l)
                
                // Photos Section
                VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
                    HStack {
                        Text("Photos")
                            .font(.headline)
                        
                        Text("(Min 1, Max 5)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        Spacer()
                        
                        Text("\(capturedPhotos.count)/5")
                            .font(.subheadline.bold())
                            .foregroundColor(capturedPhotos.isEmpty ? .red : .green)
                    }
                    
                    // Photo Grid
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 80))], spacing: 12) {
                        ForEach(capturedPhotos.indices, id: \.self) { index in
                            ZStack(alignment: .topTrailing) {
                                Image(uiImage: capturedPhotos[index])
                                    .resizable()
                                    .scaledToFill()
                                    .frame(width: 80, height: 80)
                                    .clipShape(RoundedRectangle(cornerRadius: 8))
                                
                                Button {
                                    capturedPhotos.remove(at: index)
                                } label: {
                                    Image(systemName: "xmark.circle.fill")
                                        .foregroundColor(.red)
                                        .background(Circle().fill(.white))
                                }
                                .offset(x: 5, y: -5)
                            }
                        }
                        
                        if capturedPhotos.count < 5 {
                            Button {
                                capturePhoto()
                            } label: {
                                VStack {
                                    Image(systemName: "plus")
                                        .font(.title2)
                                    Text("Add")
                                        .font(.caption)
                                }
                                .frame(width: 80, height: 80)
                                .background(Color(.secondarySystemBackground))
                                .cornerRadius(8)
                            }
                        }
                    }
                }
                .padding(.horizontal)
                
                Divider()
                    .padding(.horizontal)
                
                // Video Section
                VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
                    HStack {
                        Text("Video")
                            .font(.headline)
                        
                        Text("(10 seconds, required)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        Spacer()
                        
                        if hasRecordedVideo {
                            Label("Recorded", systemImage: "checkmark.circle.fill")
                                .font(.caption.bold())
                                .foregroundColor(.green)
                        }
                    }
                    
                    if isRecordingVideo {
                        VStack(spacing: DesignSystem.Spacing.s) {
                            ProgressView(value: videoProgress, total: 10)
                                .tint(DesignSystem.Colors.primary)
                            
                            Text("Recording... \(Int(videoProgress))/10 seconds")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .padding()
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(12)
                    } else if hasRecordedVideo {
                        HStack {
                            ZStack {
                                RoundedRectangle(cornerRadius: 12)
                                    .fill(Color(.secondarySystemBackground))
                                    .frame(height: 100)
                                
                                VStack {
                                    Image(systemName: "video.fill")
                                        .font(.title)
                                        .foregroundColor(.green)
                                    Text("10s Video")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                            
                            Button {
                                hasRecordedVideo = false
                                videoProgress = 0
                            } label: {
                                Text("Retake")
                                    .font(.subheadline)
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 8)
                                    .background(Color.orange)
                                    .foregroundColor(.white)
                                    .cornerRadius(8)
                            }
                        }
                    } else {
                        Button {
                            recordVideo()
                        } label: {
                            HStack {
                                Image(systemName: "video.fill")
                                Text("Record 10-Second Video")
                            }
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.red.opacity(0.9))
                            .foregroundColor(.white)
                            .cornerRadius(12)
                        }
                    }
                }
                .padding(.horizontal)
                
                Spacer(minLength: 100)
            }
        }
    }
    
    private func capturePhoto() {
        if EmulatorDetector.isSimulator {
            // Generate placeholder image for simulator
            let renderer = UIGraphicsImageRenderer(size: CGSize(width: 200, height: 200))
            let placeholderImage = renderer.image { context in
                UIColor.systemGray5.setFill()
                context.fill(CGRect(origin: .zero, size: CGSize(width: 200, height: 200)))
                
                let text = "Photo \(capturedPhotos.count + 1)"
                let attributes: [NSAttributedString.Key: Any] = [
                    .font: UIFont.boldSystemFont(ofSize: 24),
                    .foregroundColor: UIColor.systemGray
                ]
                let size = text.size(withAttributes: attributes)
                let rect = CGRect(x: 100 - size.width/2, y: 100 - size.height/2, width: size.width, height: size.height)
                text.draw(in: rect, withAttributes: attributes)
            }
            capturedPhotos.append(placeholderImage)
        } else {
            // Real camera capture would go here
            showingPhotoCapture = true
        }
    }
    
    private func recordVideo() {
        isRecordingVideo = true
        videoProgress = 0
        
        // Simulate 10-second recording
        Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { timer in
            videoProgress += 3
            if videoProgress >= 10 {
                timer.invalidate()
                isRecordingVideo = false
                hasRecordedVideo = true
            }
        }
    }
}

// MARK: - Step 3: Details & Schedule

struct DetailsStepView: View {
    @Binding var parkingMode: ParkingMode
    @Binding var title: String
    @Binding var listingDescription: String
    @Binding var numberOfSlots: Int
    @Binding var hourlyRate: Double
    @Binding var availableStartTime: Date
    @Binding var availableEndTime: Date
    @Binding var selectedDays: Set<Int>
    @Binding var isCovered: Bool
    @Binding var hasCCTV: Bool
    @Binding var hasEVCharging: Bool
    
    private let dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    var body: some View {
        Form {
            // MARK: - Mode Selection
            Section {
                Picker("Parking Mode", selection: $parkingMode) {
                    ForEach(ParkingMode.allCases, id: \.self) { mode in
                        Text(mode.displayName).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                
                // Mode description
                if parkingMode == .private_ {
                    Text("Schedule-based parking where you define when it's available")
                        .font(.caption)
                        .foregroundColor(.secondary)
                } else {
                    Text("Real-time parking with live availability tracking")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            // Basic Info
            Section("Basic Information") {
                TextField("Title (e.g., Spacious Driveway)", text: $title)
                
                TextField("Description (optional)", text: $listingDescription, axis: .vertical)
                    .lineLimit(3...5)
                
                HStack {
                    Text("Parking Slots")
                    
                    Spacer()
                    
                    // Minus button
                    Button {
                        if numberOfSlots > 1 {
                            numberOfSlots -= 1
                        }
                    } label: {
                        Image(systemName: "minus.circle.fill")
                            .font(.title2)
                            .foregroundColor(numberOfSlots > 1 ? DesignSystem.Colors.primary : .gray)
                    }
                    .buttonStyle(.plain)
                    .disabled(numberOfSlots <= 1)
                    
                    // Editable number field
                    TextField("1", value: $numberOfSlots, format: .number)
                        .keyboardType(.numberPad)
                        .multilineTextAlignment(.center)
                        .frame(width: 60)
                        .padding(.vertical, 6)
                        .padding(.horizontal, 12)
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(8)
                        .fontWeight(.bold)
                        .foregroundColor(DesignSystem.Colors.primary)
                    
                    // Plus button
                    Button {
                        numberOfSlots += 1
                    } label: {
                        Image(systemName: "plus.circle.fill")
                            .font(.title2)
                            .foregroundColor(DesignSystem.Colors.primary)
                    }
                    .buttonStyle(.plain)
                }
            }
            
            
            // Pricing - Show for both modes
            Section("Pricing") {
                HStack {
                    Text("Hourly Rate")
                    Spacer()
                    Text("₹")
                    TextField("40", value: $hourlyRate, format: .number)
                        .keyboardType(.numberPad)
                        .multilineTextAlignment(.trailing)
                        .frame(width: 80)
                }
            }
            
            // Availability Schedule (Private mode only)
            if parkingMode == .private_ {
                Section("Availability Schedule") {
                    DatePicker("Start Time", selection: $availableStartTime, displayedComponents: .hourAndMinute)
                    
                    DatePicker("End Time", selection: $availableEndTime, displayedComponents: .hourAndMinute)
                    
                    VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
                        Text("Available Days")
                            .font(.subheadline)
                        
                        HStack(spacing: 8) {
                            ForEach(1...7, id: \.self) { day in
                                Button {
                                    // Fixed: Each day toggles independently
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
                                .buttonStyle(.plain)  // Prevent default button behavior
                            }
                        }
                    }
                }
            }
            
            // Amenities
            Section("Amenities") {
                Toggle("Covered Parking", isOn: $isCovered)
                Toggle("CCTV Surveillance", isOn: $hasCCTV)
                Toggle("EV Charging", isOn: $hasEVCharging)
            }
        }
    }
}

// MARK: - Step 4: Review

struct ReviewStepView: View {
    let parkingMode: ParkingMode
    let address: String
    let photoCount: Int
    let hasVideo: Bool
    let title: String
    let slots: Int
    let hourlyRate: Double
    let startTime: Date
    let endTime: Date
    let selectedDays: Set<Int>
    let amenities: (covered: Bool, cctv: Bool, ev: Bool)
    
    private let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter
    }()
    
    var body: some View {
        ScrollView {
            VStack(spacing: DesignSystem.Spacing.l) {
                // Header
                VStack(spacing: DesignSystem.Spacing.s) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 50))
                        .foregroundColor(.green)
                    
                    Text("Review Your Listing")
                        .font(.title2.bold())
                }
                .padding(.top, DesignSystem.Spacing.l)
                
                // Summary Cards
                VStack(spacing: DesignSystem.Spacing.m) {
                    ReviewCard(icon: "building.2.fill", title: "Mode", value: parkingMode.displayName)
                    
                    ReviewCard(icon: "mappin.circle.fill", title: "Location", value: address)
                    
                    ReviewCard(icon: "camera.fill", title: "Media", value: "\(photoCount) photos, \(hasVideo ? "1 video" : "No video")")
                    
                    ReviewCard(icon: "tag.fill", title: "Title", value: title)
                    
                    ReviewCard(icon: "car.fill", title: "Slots", value: "\(slots) parking slot\(slots > 1 ? "s" : "")")
                    
                    // Show pricing only for Commercial mode
                    if parkingMode == .commercial {
                        ReviewCard(icon: "indianrupeesign.circle.fill", title: "Hourly Rate", value: "₹\(Int(hourlyRate))/hour")
                    }
                    
                    // Show availability only for Private mode
                    if parkingMode == .private_ {
                        let dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                        let selectedDayNames = selectedDays.sorted().map { dayNames[$0 - 1] }.joined(separator: ", ")
                        
                        ReviewCard(
                            icon: "clock.fill",
                            title: "Availability",
                            value: "\(timeFormatter.string(from: startTime)) - \(timeFormatter.string(from: endTime))"
                        )
                        
                        ReviewCard(
                            icon: "calendar",
                            title: "Days",
                            value: selectedDayNames.isEmpty ? "No days selected" : selectedDayNames
                        )
                    }
                    
                    // Amenities
                    HStack(spacing: DesignSystem.Spacing.m) {
                        if amenities.covered {
                            AmenityBadge(icon: "umbrella.fill", label: "Covered")
                        }
                        if amenities.cctv {
                            AmenityBadge(icon: "video.fill", label: "CCTV")
                        }
                        if amenities.ev {
                            AmenityBadge(icon: "bolt.fill", label: "EV")
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal)
                }
                .padding(.horizontal)
                
                Spacer(minLength: 100)
            }
        }
    }
}

// MARK: - Helper Views

struct ReviewCard: View {
    let icon: String
    let title: String
    let value: String
    
    var body: some View {
        HStack(spacing: DesignSystem.Spacing.m) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(DesignSystem.Colors.primary)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(value)
                    .font(.subheadline)
            }
            
            Spacer()
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
    }
}

// MARK: - Preview

#Preview {
    AddParkingFlowView()
        .environmentObject(PrivateParkingViewModel())
}
