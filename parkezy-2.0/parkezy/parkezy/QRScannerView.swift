//
//  QRScannerView.swift
//  ParkEzy
//
//  QR code scanner for host entry/exit verification
//

import SwiftUI
import VisionKit

struct QRScannerView: View {
    // MARK: - Properties
    
    @Binding var isPresented: Bool
    
    // MARK: - Environment
    
    @EnvironmentObject var hostViewModel: HostViewModel
    
    // MARK: - State
    
    @State private var scannedCode: String?
    @State private var showResult = false
    @State private var isProcessing = false
    @State private var showManualEntry = false
    @State private var manualCode = ""
    
    // Check if device supports camera scanning
    private var isScannerAvailable: Bool {
        DataScannerViewController.isSupported && DataScannerViewController.isAvailable
    }
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            ZStack {
                if isScannerAvailable {
                    // Real Scanner (only works on physical device)
                    DataScannerViewRepresentable(
                        recognizedTypes: Set([.barcode()]),
                        onScan: handleScan
                    )
                    .ignoresSafeArea()
                } else {
                    // Mock Scanner View (for Simulator)
                    mockScannerView
                }
                
                // Overlay
                scannerOverlay
                
                // Result Sheet
                if showResult {
                    resultSheet
                }
            }
            .navigationTitle("Scan QR Code")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") {
                        isPresented = false
                    }
                }
                
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showManualEntry = true
                    } label: {
                        Image(systemName: "keyboard")
                    }
                }
            }
            .sheet(isPresented: $showManualEntry) {
                manualEntrySheet
            }
        }
    }
    
    // MARK: - Mock Scanner View
    
    private var mockScannerView: some View {
        ZStack {
            Color.black
            
            VStack(spacing: DesignSystem.Spacing.xl) {
                Image(systemName: "camera.viewfinder")
                    .font(.system(size: 80))
                    .foregroundColor(.white.opacity(0.5))
                
                Text("Camera not available in Simulator")
                    .font(.headline)
                    .foregroundColor(.white)
                
                Text("Use the demo button below to simulate a scan")
                    .font(.subheadline)
                    .foregroundColor(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                
                // Demo Scan Buttons
                VStack(spacing: DesignSystem.Spacing.m) {
                    Button {
                        simulateScan(type: .entry)
                    } label: {
                        HStack {
                            Image(systemName: "arrow.down.to.line")
                            Text("Simulate Entry Scan")
                        }
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(DesignSystem.Colors.success)
                        .foregroundColor(.white)
                        .cornerRadius(DesignSystem.Spacing.m)
                    }
                    
                    Button {
                        simulateScan(type: .exit)
                    } label: {
                        HStack {
                            Image(systemName: "arrow.up.to.line")
                            Text("Simulate Exit Scan")
                        }
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(DesignSystem.Colors.primary)
                        .foregroundColor(.white)
                        .cornerRadius(DesignSystem.Spacing.m)
                    }
                }
                .padding(.horizontal, DesignSystem.Spacing.xl)
                .padding(.top, DesignSystem.Spacing.l)
            }
        }
    }
    
    // MARK: - Scanner Overlay
    
    private var scannerOverlay: some View {
        VStack {
            Spacer()
            
            // Scanning Frame
            ZStack {
                // Corner brackets
                RoundedRectangle(cornerRadius: 20)
                    .stroke(Color.white, lineWidth: 3)
                    .frame(width: 250, height: 250)
                
                // Scanning line animation
                if !showResult {
                    Rectangle()
                        .fill(DesignSystem.Colors.primary)
                        .frame(width: 230, height: 2)
                        .offset(y: -100)
                        .animation(
                            .linear(duration: 2.0)
                            .repeatForever(autoreverses: true),
                            value: UUID()
                        )
                }
            }
            
            Spacer()
            
            // Instructions
            if !showResult {
                VStack(spacing: DesignSystem.Spacing.s) {
                    Text("Position the QR code within the frame")
                        .font(.subheadline)
                        .foregroundColor(.white)
                    
                    Text("The code will be scanned automatically")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.7))
                }
                .padding()
                .background(.ultraThinMaterial)
                .cornerRadius(DesignSystem.Spacing.m)
                .padding(.bottom, DesignSystem.Spacing.xl)
            }
        }
    }
    
    // MARK: - Result Sheet
    
    private var resultSheet: some View {
        VStack(spacing: 0) {
            Spacer()
            
            VStack(spacing: DesignSystem.Spacing.l) {
                // Result Header
                if let result = hostViewModel.scanResult {
                    resultHeader(for: result)
                }
                
                // Booking Details
                if case .validEntry(let booking) = hostViewModel.scanResult {
                    bookingDetailsCard(booking: booking, isEntry: true)
                } else if case .validExit(let booking) = hostViewModel.scanResult {
                    bookingDetailsCard(booking: booking, isEntry: false)
                }
                
                // Action Buttons
                resultActionButtons
            }
            .padding(DesignSystem.Spacing.l)
            .background(Color(.systemBackground))
            .cornerRadius(DesignSystem.Spacing.l, corners: [.topLeft, .topRight])
            .shadow(color: .black.opacity(0.2), radius: 20, x: 0, y: -10)
        }
        .ignoresSafeArea()
        .transition(.move(edge: .bottom).combined(with: .opacity))
    }
    
    // MARK: - Result Header
    
    @ViewBuilder
    private func resultHeader(for result: ScanResult) -> some View {
        switch result {
        case .validEntry, .validExit:
            VStack(spacing: DesignSystem.Spacing.s) {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 60))
                    .foregroundColor(DesignSystem.Colors.success)
                
                Text(result.message)
                    .font(.headline)
                    .foregroundColor(DesignSystem.Colors.success)
            }
            
        case .invalid, .notFound, .wrongHost:
            VStack(spacing: DesignSystem.Spacing.s) {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 60))
                    .foregroundColor(DesignSystem.Colors.error)
                
                Text(result.message)
                    .font(.headline)
                    .foregroundColor(DesignSystem.Colors.error)
            }
        }
    }
    
    // MARK: - Booking Details Card
    
    private func bookingDetailsCard(booking: BookingSession, isEntry: Bool) -> some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Booking ID")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("#\(booking.id.uuidString.prefix(8).uppercased())")
                        .font(.subheadline.bold().monospaced())
                }
                
                Spacer()
                
                VStack(alignment: .trailing) {
                    Text(isEntry ? "Entry Time" : "Exit Time")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(formatTime(Date()))
                        .font(.subheadline.bold())
                }
            }
            
            Divider()
            
            HStack {
                VStack(alignment: .leading) {
                    Text("Duration")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("\(Int(booking.duration)) hours")
                        .font(.subheadline.bold())
                }
                
                Spacer()
                
                VStack(alignment: .trailing) {
                    Text("Total")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("₹\(Int(booking.totalCost))")
                        .font(.title3.bold())
                        .foregroundColor(DesignSystem.Colors.primary)
                }
            }
            
            if !isEntry {
                // Show overstay info for exit
                if let overstay = calculateOverstay(booking: booking), overstay > 0 {
                    Divider()
                    
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.orange)
                        
                        Text("Overstay: \(overstay) min")
                            .font(.subheadline)
                        
                        Spacer()
                        
                        Text("+₹\(Int(ceil(Double(overstay) / 15.0) * 20))")
                            .font(.subheadline.bold())
                            .foregroundColor(.orange)
                    }
                    .padding(DesignSystem.Spacing.s)
                    .background(Color.orange.opacity(0.1))
                    .cornerRadius(DesignSystem.Spacing.s)
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.secondarySystemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
    }
    
    // MARK: - Action Buttons
    
    private var resultActionButtons: some View {
        HStack(spacing: DesignSystem.Spacing.m) {
            // Cancel Button
            Button {
                withAnimation {
                    showResult = false
                    scannedCode = nil
                    hostViewModel.scanResult = nil
                }
            } label: {
                Text("Cancel")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.gray.opacity(0.2))
                    .foregroundColor(.primary)
                    .cornerRadius(DesignSystem.Spacing.m)
            }
            
            // Confirm Button
            if case .validEntry(let booking) = hostViewModel.scanResult {
                Button {
                    confirmAction(booking: booking, isEntry: true)
                } label: {
                    if isProcessing {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Text("Confirm Entry")
                    }
                }
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
                .background(DesignSystem.Colors.success)
                .foregroundColor(.white)
                .cornerRadius(DesignSystem.Spacing.m)
                .disabled(isProcessing)
            } else if case .validExit(let booking) = hostViewModel.scanResult {
                Button {
                    confirmAction(booking: booking, isEntry: false)
                } label: {
                    if isProcessing {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Text("Confirm Exit")
                    }
                }
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
                .background(DesignSystem.Colors.primary)
                .foregroundColor(.white)
                .cornerRadius(DesignSystem.Spacing.m)
                .disabled(isProcessing)
            }
        }
    }
    
    // MARK: - Manual Entry Sheet
    
    private var manualEntrySheet: some View {
        NavigationStack {
            VStack(spacing: DesignSystem.Spacing.l) {
                Text("Enter Booking Code")
                    .font(.headline)
                
                TextField("Booking ID or Access Code", text: $manualCode)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(.body, design: .monospaced))
                    .textInputAutocapitalization(.characters)
                
                Button {
                    if !manualCode.isEmpty {
                        handleManualEntry()
                    }
                } label: {
                    Text("Verify")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(DesignSystem.Colors.primary)
                        .foregroundColor(.white)
                        .cornerRadius(DesignSystem.Spacing.m)
                }
                .disabled(manualCode.isEmpty)
                
                Spacer()
            }
            .padding()
            .navigationTitle("Manual Entry")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Cancel") {
                        showManualEntry = false
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }
    
    // MARK: - Methods
    
    private func handleScan(code: String) {
        guard scannedCode == nil else { return }
        
        scannedCode = code
        hostViewModel.validateQRCode(code)
        
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        
        withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
            showResult = true
        }
    }
    
    private func simulateScan(type: ScanType) {
        // Get a mock booking for demo
        if let booking = hostViewModel.activeBookings.first {
            let mockQR = "PARKEZY:\(booking.id.uuidString):\(booking.spotID.uuidString)"
            
            if type == .exit {
                // For exit, pretend this is a completed booking
                hostViewModel.scanResult = .validExit(booking: booking)
            } else {
                hostViewModel.scanResult = .validEntry(booking: booking)
            }
            
            UIImpactFeedbackGenerator(style: .medium).impactOccurred()
            
            withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
                showResult = true
            }
        } else {
            // No active bookings - show error
            hostViewModel.scanResult = .notFound
            
            withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
                showResult = true
            }
        }
    }
    
    private func handleManualEntry() {
        showManualEntry = false
        
        // In production, validate the manual code
        // For demo, just show not found
        hostViewModel.scanResult = .notFound
        
        withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
            showResult = true
        }
    }
    
    private func confirmAction(booking: BookingSession, isEntry: Bool) {
        isProcessing = true
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            if isEntry {
                hostViewModel.confirmEntry(booking: booking)
            } else {
                hostViewModel.confirmExit(booking: booking)
            }
            
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            
            isProcessing = false
            isPresented = false
        }
    }
    
    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: date)
    }
    
    private func calculateOverstay(booking: BookingSession) -> Int? {
        let now = Date()
        if now > booking.scheduledEndTime {
            return Int(now.timeIntervalSince(booking.scheduledEndTime) / 60)
        }
        return nil
    }
}

// MARK: - Scan Type

enum ScanType {
    case entry
    case exit
}

// MARK: - DataScanner Representable

struct DataScannerViewRepresentable: UIViewControllerRepresentable {
    let recognizedTypes: Set<DataScannerViewController.RecognizedDataType>
    let onScan: (String) -> Void
    
    func makeUIViewController(context: Context) -> DataScannerViewController {
        let scanner = DataScannerViewController(
            recognizedDataTypes: recognizedTypes,
            qualityLevel: .balanced,
            recognizesMultipleItems: false,
            isHighFrameRateTrackingEnabled: true,
            isPinchToZoomEnabled: true,
            isGuidanceEnabled: true,
            isHighlightingEnabled: true
        )
        scanner.delegate = context.coordinator
        try? scanner.startScanning()
        return scanner
    }
    
    func updateUIViewController(_ uiViewController: DataScannerViewController, context: Context) {}
    
    func makeCoordinator() -> Coordinator {
        Coordinator(onScan: onScan)
    }
}
    
    class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let onScan: (String) -> Void
        
        init(onScan: @escaping (String) -> Void) {
            self.onScan = onScan
        }
        
        func dataScanner(_ dataScanner: DataScannerViewController, didTapOn item: RecognizedItem) {
            if case .barcode(let barcode) = item {
                if let value = barcode.payloadStringValue {
                    onScan(value)
                }
            }
        }
    }

// MARK: - Corner Radius Extension

extension View {
    func cornerRadius(_ radius: CGFloat, corners: UIRectCorner) -> some View {
        clipShape(RoundedCorner(radius: radius, corners: corners))
    }
}

struct RoundedCorner: Shape {
    var radius: CGFloat = .infinity
    var corners: UIRectCorner = .allCorners
    
    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(
            roundedRect: rect,
            byRoundingCorners: corners,
            cornerRadii: CGSize(width: radius, height: radius)
        )
        return Path(path.cgPath)
    }
}

// MARK: - Preview

#Preview {
    QRScannerView(isPresented: .constant(true))
        .environmentObject(HostViewModel())
}
