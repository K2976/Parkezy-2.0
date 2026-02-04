//
//  QRDisplayView.swift
//  ParkEzy
//
//  Displays QR code for mall parking check-in/out
//

import SwiftUI
import CoreImage.CIFilterBuiltins

struct QRDisplayView: View {
    // MARK: - Properties
    
    let booking: BookingSession
    @Binding var isPresented: Bool
    let onComplete: () -> Void
    
    // MARK: - Environment
    
    @EnvironmentObject var bookingViewModel: BookingViewModel
    
    // MARK: - State
    
    @State private var sessionStarted = false
    @State private var showingAddToWallet = false
    @State private var brightness: CGFloat = UIScreen.main.brightness
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignSystem.Spacing.xl) {
                    // MARK: - Header
                    
                    VStack(spacing: DesignSystem.Spacing.s) {
                        Image(systemName: "qrcode")
                            .font(.system(size: 40))
                            .foregroundColor(DesignSystem.Colors.primary)
                        
                        Text("Show to Caretaker")
                            .font(.title.bold())
                        
                        Text("Present this QR code at the parking entrance")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    
                    // MARK: - QR Code
                    
                    VStack(spacing: DesignSystem.Spacing.m) {
                        if let qrImage = generateQRCode() {
                            Image(uiImage: qrImage)
                                .interpolation(.none)
                                .resizable()
                                .scaledToFit()
                                .frame(width: 250, height: 250)
                                .padding(DesignSystem.Spacing.l)
                                .background(Color.white)
                                .cornerRadius(DesignSystem.Spacing.m)
                                .shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 5)
                        } else {
                            RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
                                .fill(Color.gray.opacity(0.2))
                                .frame(width: 280, height: 280)
                                .overlay {
                                    ProgressView()
                                }
                        }
                        
                        // Booking ID
                        Text("Booking: \(booking.id.uuidString.prefix(8).uppercased())")
                            .font(.caption.monospaced())
                            .foregroundColor(.secondary)
                    }
                    
                    // MARK: - Booking Details
                    
                    VStack(spacing: DesignSystem.Spacing.m) {
                        DetailRow(icon: "clock.fill", title: "Duration", value: formattedDuration)
                        DetailRow(icon: "indianrupeesign.circle.fill", title: "Total Cost", value: "₹\(Int(booking.totalCost))")
                        DetailRow(icon: "calendar", title: "Valid Until", value: formattedEndTime)
                    }
                    .padding(DesignSystem.Spacing.m)
                    .background(Color(.systemBackground))
                    .cornerRadius(DesignSystem.Spacing.m)
                    .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
                    
                    // MARK: - Action Buttons
                    
                    VStack(spacing: DesignSystem.Spacing.m) {
                        // Add to Wallet Button
                        Button {
                            showingAddToWallet = true
                        } label: {
                            HStack {
                                Image(systemName: "wallet.pass.fill")
                                Text("Add to Apple Wallet")
                            }
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.black)
                            .foregroundColor(.white)
                            .cornerRadius(DesignSystem.Spacing.m)
                        }
                        
                        // Start Session Button (Demo)
                        if !sessionStarted {
                            Button {
                                startSession()
                            } label: {
                                HStack {
                                    Image(systemName: "play.fill")
                                    Text("Simulate: Caretaker Scanned")
                                }
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(DesignSystem.Colors.success)
                                .foregroundColor(.white)
                                .cornerRadius(DesignSystem.Spacing.m)
                            }
                        } else {
                            Button {
                                isPresented = false
                                onComplete()
                            } label: {
                                HStack {
                                    Image(systemName: "car.fill")
                                    Text("Go to Active Session")
                                }
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(DesignSystem.Colors.primary)
                                .foregroundColor(.white)
                                .cornerRadius(DesignSystem.Spacing.m)
                            }
                        }
                    }
                    .padding(.horizontal, DesignSystem.Spacing.s)
                    
                    // MARK: - Instructions
                    
                    VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
                        Text("Instructions")
                            .font(.headline)
                        
                        InstructionRow(number: 1, text: "Show this QR code to the parking caretaker")
                        InstructionRow(number: 2, text: "They will scan it to verify your booking")
                        InstructionRow(number: 3, text: "Your session timer will start automatically")
                        InstructionRow(number: 4, text: "Show QR again when exiting to end session")
                    }
                    .padding(DesignSystem.Spacing.m)
                    .background(DesignSystem.Colors.primary.opacity(0.05))
                    .cornerRadius(DesignSystem.Spacing.m)
                }
                .padding(DesignSystem.Spacing.m)
            }
            .navigationTitle("Entry Pass")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        isPresented = false
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.gray)
                    }
                }
            }
            .sheet(isPresented: $showingAddToWallet) {
                WalletPassMockView(booking: booking)
            }
        }
        .presentationDetents([.large])
        .presentationDragIndicator(.visible)
        .onAppear {
            // Increase brightness for easier scanning
            if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene {
                brightness = windowScene.screen.brightness
                windowScene.screen.brightness = 1.0
            } else {
                // Fallback for older iOS or if scene not found
                brightness = UIScreen.main.brightness
                UIScreen.main.brightness = 1.0
            }
        }
        .onDisappear {
            // Restore brightness
            if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene {
                windowScene.screen.brightness = brightness
            } else {
                UIScreen.main.brightness = brightness
            }
        }
    }
    
    // MARK: - Computed Properties
    
    private var formattedDuration: String {
        let hours = Int(booking.duration)
        let minutes = Int((booking.duration - Double(hours)) * 60)
        if minutes > 0 {
            return "\(hours)h \(minutes)m"
        }
        return "\(hours) hour\(hours > 1 ? "s" : "")"
    }
    
    private var formattedEndTime: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a, MMM d"
        return formatter.string(from: booking.scheduledEndTime)
    }
    
    // MARK: - Methods
    
    private func generateQRCode() -> UIImage? {
        let context = CIContext()
        let filter = CIFilter.qrCodeGenerator()
        
        // Generate QR string in format: PARKEZY:<bookingID>:<spotID>
        let qrString = "PARKEZY:\(booking.id.uuidString):\(booking.spotID.uuidString)"
        filter.message = Data(qrString.utf8)
        filter.correctionLevel = "H"
        
        guard let outputImage = filter.outputImage else { return nil }
        
        // Scale up for high resolution
        let scale = 10.0
        let scaledImage = outputImage.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
        
        guard let cgImage = context.createCGImage(scaledImage, from: scaledImage.extent) else { return nil }
        
        return UIImage(cgImage: cgImage)
    }
    
    private func startSession() {
        withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
            sessionStarted = true
        }
        
        // Start the booking session
        bookingViewModel.startSession()
        
        // Haptic feedback
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }
}

// MARK: - Detail Row

struct DetailRow: View {
    let icon: String
    let title: String
    let value: String
    
    var body: some View {
        HStack {
            Image(systemName: icon)
                .foregroundColor(DesignSystem.Colors.primary)
                .frame(width: 24)
            
            Text(title)
                .foregroundColor(.secondary)
            
            Spacer()
            
            Text(value)
                .font(.subheadline.bold())
        }
    }
}

// MARK: - Instruction Row

struct InstructionRow: View {
    let number: Int
    let text: String
    
    var body: some View {
        HStack(alignment: .top, spacing: DesignSystem.Spacing.s) {
            Text("\(number)")
                .font(.caption.bold())
                .foregroundColor(.white)
                .frame(width: 20, height: 20)
                .background(DesignSystem.Colors.primary)
                .clipShape(Circle())
            
            Text(text)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
    }
}

// MARK: - Wallet Pass Mock View

struct WalletPassMockView: View {
    let booking: BookingSession
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(spacing: DesignSystem.Spacing.l) {
                // Mock Wallet Pass UI
                VStack(spacing: 0) {
                    // Header
                    HStack {
                        VStack(alignment: .leading) {
                            Text("ParkEzy")
                                .font(.headline)
                                .foregroundColor(.white)
                            Text("Parking Pass")
                                .font(.caption)
                                .foregroundColor(.white.opacity(0.7))
                        }
                        
                        Spacer()
                        
                        Image(systemName: "parkingsign.circle.fill")
                            .font(.title)
                            .foregroundColor(.white)
                    }
                    .padding()
                    .background(DesignSystem.Colors.primary)
                    
                    // Content
                    VStack(spacing: DesignSystem.Spacing.m) {
                        // QR Code
                        Image(systemName: "qrcode")
                            .font(.system(size: 80))
                            .foregroundColor(.black)
                            .padding()
                        
                        Divider()
                        
                        HStack {
                            VStack(alignment: .leading) {
                                Text("VALID UNTIL")
                                    .font(.caption2)
                                    .foregroundColor(.secondary)
                                Text(formatDate(booking.scheduledEndTime))
                                    .font(.subheadline.bold())
                            }
                            
                            Spacer()
                            
                            VStack(alignment: .trailing) {
                                Text("TOTAL")
                                    .font(.caption2)
                                    .foregroundColor(.secondary)
                                Text("₹\(Int(booking.totalCost))")
                                    .font(.subheadline.bold())
                            }
                        }
                        .padding(.horizontal)
                        .padding(.bottom)
                    }
                    .background(Color.white)
                }
                .cornerRadius(12)
                .shadow(color: .black.opacity(0.2), radius: 10, x: 0, y: 5)
                .padding()
                
                // Note
                VStack(spacing: DesignSystem.Spacing.s) {
                    Image(systemName: "info.circle.fill")
                        .font(.title2)
                        .foregroundColor(DesignSystem.Colors.primary)
                    
                    Text("Apple Wallet Integration")
                        .font(.headline)
                    
                    Text("In production, this would be a real Apple Wallet pass. Adding passes requires Apple Developer Program enrollment and server-side pass signing.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding()
                
                Spacer()
            }
            .navigationTitle("Add to Wallet")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
    
    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, h:mm a"
        return formatter.string(from: date)
    }
}

// MARK: - Preview

#Preview {
    QRDisplayView(
        booking: BookingSession.mockSession,
        isPresented: .constant(true),
        onComplete: {}
    )
    .environmentObject(BookingViewModel())
}
