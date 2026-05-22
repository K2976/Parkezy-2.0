//
//  BookingConfirmationView.swift
//  ParkEzy
//
//  Booking confirmation with duration picker and mock Apple Pay
//

import SwiftUI

struct BookingConfirmationView: View {
    // MARK: - Properties
    
    let spot: ParkingSpot
    @Binding var isPresented: Bool
    
    // MARK: - Environment
    
    @EnvironmentObject var bookingViewModel: BookingViewModel
    @Environment(\.dismiss) private var dismiss
    
    // MARK: - State
    
    @State private var selectedDuration: Double = 2.0
    @State private var isProcessingPayment = false
    @State private var paymentSuccess = false
    @State private var showAccessCode = false
    @State private var customDuration: Double = 2.0
    @State private var showCustomSlider = false
    
    // Preset duration options
    private let durationPresets: [Double] = [1.0, 2.0, 3.0, 4.0]
    
    // MARK: - Body
    
    var body: some View {
        ScrollView {
            VStack(spacing: DesignSystem.Spacing.l) {
                // MARK: - Spot Summary
                
                spotSummaryCard
                
                // MARK: - Duration Picker
                
                durationPicker
                
                // MARK: - Cost Breakdown
                
                costBreakdown
                
                // MARK: - Payment Button
                
                paymentButton
                
                // MARK: - Terms
                
                termsText
            }
            .padding(DesignSystem.Spacing.m)
        }
        .navigationTitle("Confirm Booking")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showAccessCode) {
            if spot.type == .mall {
                QRDisplayView(booking: bookingViewModel.activeSession!, isPresented: $showAccessCode) {
                    isPresented = false
                }
            } else {
                PINEntryView(spot: spot, booking: bookingViewModel.activeSession!, isPresented: $showAccessCode) {
                    isPresented = false
                }
            }
        }
        .overlay {
            if isProcessingPayment {
                paymentProcessingOverlay
            }
        }
    }
    
    // MARK: - Spot Summary Card
    
    private var spotSummaryCard: some View {
        HStack(spacing: DesignSystem.Spacing.m) {
            // Icon
            ZStack {
                Circle()
                    .fill(DesignSystem.Colors.primary.opacity(0.1))
                    .frame(width: 60, height: 60)
                
                Image(systemName: spot.type == .mall ? "building.2.fill" : "house.fill")
                    .font(.title2)
                    .foregroundColor(DesignSystem.Colors.primary)
            }
            
            // Details
            VStack(alignment: .leading, spacing: 4) {
                Text(spot.address)
                    .font(.headline)
                    .lineLimit(2)
                
                HStack {
                    Image(systemName: "star.fill")
                        .foregroundColor(.yellow)
                        .font(.caption)
                    Text(String(format: "%.1f", spot.rating))
                        .font(.caption.bold())
                    Text("•")
                        .foregroundColor(.secondary)
                    Text("₹\(Int(spot.pricePerHour))/hr")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            Spacer()
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Duration Picker
    
    private var durationPicker: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Select Duration")
                .font(.headline)
            
            // Preset Buttons
            HStack(spacing: DesignSystem.Spacing.s) {
                ForEach(durationPresets, id: \.self) { duration in
                    DurationButton(
                        hours: duration,
                        isSelected: selectedDuration == duration && !showCustomSlider
                    ) {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                            selectedDuration = duration
                            showCustomSlider = false
                        }
                    }
                }
                
                // Custom Button
                Button {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        showCustomSlider.toggle()
                        if showCustomSlider {
                            selectedDuration = customDuration
                        }
                    }
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: "slider.horizontal.3")
                            .font(.title3)
                        Text("Custom")
                            .font(.caption)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, DesignSystem.Spacing.m)
                    .background(
                        showCustomSlider ? DesignSystem.Colors.primary : Color.gray.opacity(0.1)
                    )
                    .foregroundColor(showCustomSlider ? .white : .primary)
                    .cornerRadius(DesignSystem.Spacing.s)
                }
            }
            
            // Custom Duration Slider
            if showCustomSlider {
                VStack(spacing: DesignSystem.Spacing.s) {
                    HStack {
                        Text("Duration:")
                        Spacer()
                        Text("\(formattedDuration(customDuration))")
                            .font(.headline)
                            .foregroundColor(DesignSystem.Colors.primary)
                    }
                    
                    Slider(value: $customDuration, in: 0.5...12, step: 0.5)
                        .tint(DesignSystem.Colors.primary)
                        .onChange(of: customDuration) { _, newValue in
                            selectedDuration = newValue
                        }
                    
                    HStack {
                        Text("30 min")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Spacer()
                        Text("12 hours")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .padding(DesignSystem.Spacing.m)
                .background(DesignSystem.Colors.primary.opacity(0.05))
                .cornerRadius(DesignSystem.Spacing.s)
                .transition(.opacity.combined(with: .scale(scale: 0.95)))
            }
            
            // Booking Time Summary
            HStack {
                VStack(alignment: .leading) {
                    Text("Start Time")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(formattedTime(Date()))
                        .font(.subheadline.bold())
                }
                
                Spacer()
                
                Image(systemName: "arrow.right")
                    .foregroundColor(.secondary)
                
                Spacer()
                
                VStack(alignment: .trailing) {
                    Text("End Time")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(formattedTime(endTime))
                        .font(.subheadline.bold())
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(Color.gray.opacity(0.05))
            .cornerRadius(DesignSystem.Spacing.s)
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Cost Breakdown
    
    private var costBreakdown: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Cost Breakdown")
                .font(.headline)
            
            VStack(spacing: DesignSystem.Spacing.s) {
                CostRow(
                    title: "Base Price",
                    detail: "₹\(Int(spot.pricePerHour)) × \(formattedDuration(selectedDuration))",
                    amount: baseCost
                )
                
                CostRow(
                    title: "GST",
                    detail: "18%",
                    amount: gstAmount
                )
                
                Divider()
                
                HStack {
                    Text("Total")
                        .font(.headline)
                    Spacer()
                    Text("₹\(Int(totalCost))")
                        .font(.title2.bold())
                        .foregroundColor(DesignSystem.Colors.primary)
                }
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Payment Button
    
    private var paymentButton: some View {
        Button {
            processPayment()
        } label: {
            HStack(spacing: DesignSystem.Spacing.s) {
                Image(systemName: "apple.logo")
                    .font(.title2)
                Text("Pay with Apple Pay")
                    .font(.headline)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.black)
            .foregroundColor(.white)
            .cornerRadius(DesignSystem.Spacing.m)
        }
    }
    
    // MARK: - Terms Text
    
    private var termsText: some View {
        Text("By proceeding, you agree to ParkEzy's Terms of Service and Cancellation Policy. Overstay fees apply at ₹20 per 15 minutes.")
            .font(.caption)
            .foregroundColor(.secondary)
            .multilineTextAlignment(.center)
            .padding(.horizontal)
    }
    
    // MARK: - Payment Processing Overlay
    
    private var paymentProcessingOverlay: some View {
        ZStack {
            Color.black.opacity(0.6)
                .ignoresSafeArea()
            
            VStack(spacing: DesignSystem.Spacing.l) {
                if paymentSuccess {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 80))
                        .foregroundColor(DesignSystem.Colors.success)
                        .transition(.scale.combined(with: .opacity))
                    
                    Text("Payment Successful!")
                        .font(.title2.bold())
                        .foregroundColor(.white)
                    
                    Text("Booking confirmed")
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.7))
                } else {
                    ProgressView()
                        .scaleEffect(2)
                        .tint(.white)
                    
                    Text("Processing Payment...")
                        .font(.headline)
                        .foregroundColor(.white)
                        .padding(.top, DesignSystem.Spacing.m)
                }
            }
            .padding(DesignSystem.Spacing.xl)
            .background(
                RoundedRectangle(cornerRadius: DesignSystem.Spacing.l)
                    .fill(.ultraThinMaterial)
            )
        }
    }
    
    // MARK: - Computed Properties
    
    private var baseCost: Double {
        spot.pricePerHour * selectedDuration
    }
    
    private var gstAmount: Double {
        baseCost * 0.18
    }
    
    private var totalCost: Double {
        baseCost + gstAmount
    }
    
    private var endTime: Date {
        Calendar.current.date(byAdding: .minute, value: Int(selectedDuration * 60), to: Date()) ?? Date()
    }
    
    // MARK: - Methods
    
    private func formattedDuration(_ hours: Double) -> String {
        if hours < 1 {
            return "\(Int(hours * 60)) min"
        } else if hours == Double(Int(hours)) {
            return "\(Int(hours))h"
        } else {
            let wholeHours = Int(hours)
            let minutes = Int((hours - Double(wholeHours)) * 60)
            return "\(wholeHours)h \(minutes)m"
        }
    }
    
    private func formattedTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: date)
    }
    
    private func processPayment() {
        withAnimation {
            isProcessingPayment = true
        }
        
        // Simulate payment processing
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            withAnimation(.spring(response: 0.4, dampingFraction: 0.6)) {
                paymentSuccess = true
            }
            
            // Create booking
            bookingViewModel.createBooking(
                spot: spot,
                duration: selectedDuration,
                totalCost: totalCost
            )
            
            // Show access code after brief delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                isProcessingPayment = false
                showAccessCode = true
                
                // Haptic feedback
                let generator = UINotificationFeedbackGenerator()
                generator.notificationOccurred(.success)
            }
        }
    }
}

// MARK: - Duration Button

struct DurationButton: View {
    let hours: Double
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Text("\(Int(hours))")
                    .font(.title2.bold())
                Text(hours == 1 ? "hour" : "hours")
                    .font(.caption)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, DesignSystem.Spacing.m)
            .background(
                isSelected ? DesignSystem.Colors.primary : Color.gray.opacity(0.1)
            )
            .foregroundColor(isSelected ? .white : .primary)
            .cornerRadius(DesignSystem.Spacing.s)
        }
    }
}

// MARK: - Cost Row

struct CostRow: View {
    let title: String
    let detail: String
    let amount: Double
    
    var body: some View {
        HStack {
            Text(title)
                .foregroundColor(.secondary)
            Text("(\(detail))")
                .font(.caption)
                .foregroundColor(.secondary)
            Spacer()
            Text("₹\(Int(amount))")
                .font(.subheadline.bold())
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        BookingConfirmationView(
            spot: ParkingSpot.mockSpot,
            isPresented: .constant(true)
        )
        .environmentObject(BookingViewModel())
    }
}
