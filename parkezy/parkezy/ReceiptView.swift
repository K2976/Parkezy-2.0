//
//  ReceiptView.swift
//  ParkEzy
//
//  Final receipt with invoice breakdown and rating UI
//

import SwiftUI

struct ReceiptView: View {
    // MARK: - Properties
    
    let session: BookingSession
    @Binding var isPresented: Bool
    
    // MARK: - Environment
    
    @EnvironmentObject var bookingViewModel: BookingViewModel
    @EnvironmentObject var mapViewModel: MapViewModel
    
    // MARK: - State
    
    @State private var rating: Int = 0
    @State private var feedbackText = ""
    @State private var isSubmittingRating = false
    @State private var showThankYou = false
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignSystem.Spacing.l) {
                    // MARK: - Success Header
                    
                    successHeader
                    
                    // MARK: - Receipt Card
                    
                    receiptCard
                    
                    // MARK: - Time Breakdown
                    
                    timeBreakdown
                    
                    // MARK: - Rating Section
                    
                    ratingSection
                    
                    // MARK: - Action Buttons
                    
                    actionButtons
                }
                .padding(DesignSystem.Spacing.m)
            }
            .navigationTitle("Receipt")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        isPresented = false
                    } label: {
                        Text("Done")
                            .bold()
                    }
                }
            }
        }
    }
    
    // MARK: - Success Header
    
    private var successHeader: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            ZStack {
                Circle()
                    .fill(DesignSystem.Colors.success.opacity(0.1))
                    .frame(width: 100, height: 100)
                
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 60))
                    .foregroundColor(DesignSystem.Colors.success)
            }
            
            Text("Session Complete!")
                .font(.title.bold())
            
            Text("Thank you for parking with ParkEzy")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .padding(.bottom, DesignSystem.Spacing.m)
    }
    
    // MARK: - Receipt Card
    
    private var receiptCard: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading) {
                    Text("ParkEzy")
                        .font(.headline)
                        .foregroundColor(.white)
                    Text("Parking Receipt")
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
                // Receipt ID
                HStack {
                    Text("Receipt #")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(session.id.uuidString.prefix(8).uppercased())
                        .font(.caption.monospaced())
                }
                
                Divider()
                
                // Location
                if let spot = currentSpot {
                    HStack(alignment: .top) {
                        Image(systemName: "location.fill")
                            .foregroundColor(DesignSystem.Colors.primary)
                        Text(spot.address)
                            .font(.subheadline)
                        Spacer()
                    }
                }
                
                Divider()
                
                // Cost Breakdown
                VStack(spacing: DesignSystem.Spacing.s) {
                    ReceiptRow(title: "Base Parking", value: "₹\(Int(baseCost))")
                    ReceiptRow(title: "GST (18%)", value: "₹\(Int(gstAmount))")
                    
                    if overstayFee > 0 {
                        ReceiptRow(
                            title: "Overstay Fee",
                            value: "+₹\(Int(overstayFee))",
                            isHighlighted: true
                        )
                    }
                }
                
                // Dashed Divider
                DashedDivider()
                
                // Total
                HStack {
                    Text("TOTAL PAID")
                        .font(.headline)
                    Spacer()
                    Text("₹\(Int(session.totalCost))")
                        .font(.title.bold())
                        .foregroundColor(DesignSystem.Colors.primary)
                }
                
                // Payment Method
                HStack {
                    Image(systemName: "apple.logo")
                    Text("Apple Pay •••• 4242")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("Paid")
                        .font(.caption.bold())
                        .foregroundColor(DesignSystem.Colors.success)
                }
                .padding(.top, DesignSystem.Spacing.s)
            }
            .padding()
        }
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 5)
    }
    
    // MARK: - Time Breakdown
    
    private var timeBreakdown: some View {
        HStack {
            TimeCard(
                icon: "play.circle.fill",
                title: "Started",
                value: formattedTime(session.actualStartTime ?? session.scheduledStartTime),
                color: DesignSystem.Colors.success
            )
            
            TimeCard(
                icon: "stop.circle.fill",
                title: "Ended",
                value: formattedTime(session.actualEndTime ?? Date()),
                color: DesignSystem.Colors.error
            )
            
            TimeCard(
                icon: "clock.fill",
                title: "Duration",
                value: formattedDuration,
                color: DesignSystem.Colors.primary
            )
        }
    }
    
    // MARK: - Rating Section
    
    private var ratingSection: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            Text("Rate Your Experience")
                .font(.headline)
            
            // Star Rating
            HStack(spacing: DesignSystem.Spacing.m) {
                ForEach(1...5, id: \.self) { star in
                    Button {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) {
                            rating = star
                        }
                        UIImpactFeedbackGenerator(style: .light).impactOccurred()
                    } label: {
                        Image(systemName: star <= rating ? "star.fill" : "star")
                            .font(.title)
                            .foregroundColor(star <= rating ? .yellow : .gray)
                    }
                }
            }
            
            // Rating Label
            if rating > 0 {
                Text(ratingLabel)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .transition(.opacity.combined(with: .scale))
            }
            
            // Feedback Text (optional)
            if rating > 0 {
                TextField("Add a comment (optional)", text: $feedbackText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(3...5)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
            
            // Submit Rating Button
            if rating > 0 && !showThankYou {
                Button {
                    submitRating()
                } label: {
                    if isSubmittingRating {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Text("Submit Rating")
                    }
                }
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
                .background(DesignSystem.Colors.primary)
                .foregroundColor(.white)
                .cornerRadius(DesignSystem.Spacing.s)
                .transition(.opacity.combined(with: .move(edge: .bottom)))
            }
            
            // Thank You Message
            if showThankYou {
                HStack {
                    Image(systemName: "heart.fill")
                        .foregroundColor(DesignSystem.Colors.error)
                    Text("Thank you for your feedback!")
                        .foregroundColor(.secondary)
                }
                .transition(.opacity.combined(with: .scale))
            }
        }
        .padding(DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.m)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
        .animation(.spring(response: 0.4, dampingFraction: 0.7), value: rating)
        .animation(.spring(response: 0.4, dampingFraction: 0.7), value: showThankYou)
    }
    
    // MARK: - Action Buttons
    
    private var actionButtons: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            // Share Receipt
            Button {
                shareReceipt()
            } label: {
                HStack {
                    Image(systemName: "square.and.arrow.up")
                    Text("Share Receipt")
                }
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.gray.opacity(0.1))
                .foregroundColor(.primary)
                .cornerRadius(DesignSystem.Spacing.m)
            }
            
            // Book Again
            Button {
                isPresented = false
            } label: {
                HStack {
                    Image(systemName: "arrow.counterclockwise")
                    Text("Book Again")
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
    
    // MARK: - Computed Properties
    
    private var currentSpot: ParkingSpot? {
        mapViewModel.spots.first { $0.id == session.spotID }
    }
    
    private var baseCost: Double {
        session.totalCost / 1.18 - overstayFee
    }
    
    private var gstAmount: Double {
        baseCost * 0.18
    }
    
    private var overstayFee: Double {
        session.overstayFee ?? 0
    }
    
    private var formattedDuration: String {
        guard let start = session.actualStartTime,
              let end = session.actualEndTime else {
            return "\(Int(session.duration))h"
        }
        
        let duration = end.timeIntervalSince(start)
        let hours = Int(duration) / 3600
        let minutes = (Int(duration) % 3600) / 60
        
        if hours > 0 && minutes > 0 {
            return "\(hours)h \(minutes)m"
        } else if hours > 0 {
            return "\(hours)h"
        } else {
            return "\(minutes)m"
        }
    }
    
    private var ratingLabel: String {
        switch rating {
        case 1: return "Poor"
        case 2: return "Fair"
        case 3: return "Good"
        case 4: return "Great"
        case 5: return "Excellent!"
        default: return ""
        }
    }
    
    // MARK: - Methods
    
    private func formattedTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: date)
    }
    
    private func submitRating() {
        isSubmittingRating = true
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            isSubmittingRating = false
            
            withAnimation {
                showThankYou = true
            }
            
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        }
    }
    
    private func shareReceipt() {
        // In production, generate PDF or share text
        let text = """
        ParkEzy Receipt
        ================
        Receipt #: \(session.id.uuidString.prefix(8).uppercased())
        Location: \(currentSpot?.address ?? "N/A")
        Duration: \(formattedDuration)
        Total: ₹\(Int(session.totalCost))
        
        Thank you for using ParkEzy!
        """
        
        print("Share: \(text)")
    }
}

// MARK: - Receipt Row

struct ReceiptRow: View {
    let title: String
    let value: String
    var isHighlighted: Bool = false
    
    var body: some View {
        HStack {
            Text(title)
                .foregroundColor(isHighlighted ? DesignSystem.Colors.error : .secondary)
            Spacer()
            Text(value)
                .font(.subheadline.bold())
                .foregroundColor(isHighlighted ? DesignSystem.Colors.error : .primary)
        }
    }
}

// MARK: - Time Card

struct TimeCard: View {
    let icon: String
    let title: String
    let value: String
    let color: Color
    
    var body: some View {
        VStack(spacing: DesignSystem.Spacing.xs) {
            Image(systemName: icon)
                .foregroundColor(color)
            
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
            
            Text(value)
                .font(.subheadline.bold())
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, DesignSystem.Spacing.m)
        .background(Color(.systemBackground))
        .cornerRadius(DesignSystem.Spacing.s)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

// MARK: - Dashed Divider

struct DashedDivider: View {
    var body: some View {
        GeometryReader { geometry in
            Path { path in
                path.move(to: CGPoint(x: 0, y: 0))
                path.addLine(to: CGPoint(x: geometry.size.width, y: 0))
            }
            .stroke(style: StrokeStyle(lineWidth: 1, dash: [5]))
            .foregroundColor(.gray.opacity(0.3))
        }
        .frame(height: 1)
    }
}

// MARK: - Preview

#Preview {
    ReceiptView(
        session: BookingSession.mockSession,
        isPresented: .constant(true)
    )
    .environmentObject(BookingViewModel())
    .environmentObject(MapViewModel())
}
