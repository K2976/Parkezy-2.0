//
//  PricingIntelligenceView.swift
//  ParkEzy
//
//  Host-facing view showing suggested pricing based on nearby listings
//

import SwiftUI
import CoreLocation

struct PricingIntelligenceView: View {
    let listing: PrivateParkingListing
    @State private var currentHourlyRate: Double
    @State private var showSaveConfirmation = false
    
    init(listing: PrivateParkingListing) {
        self.listing = listing
        _currentHourlyRate = State(initialValue: listing.hourlyRate)
    }
    
    var body: some View {
        List {
            // MARK: - Market Analysis
            Section {
                marketAnalysisCard
            } header: {
                Text("Market Analysis")
            }
            
            // MARK: - Your Pricing
            Section {
                pricingSlider(
                    label: "Hourly Rate",
                    value: $currentHourlyRate,
                    range: 20...100,
                    icon: "clock.fill"
                )
            } header: {
                Text("Your Pricing")
            } footer: {
                Text("Adjusting price affects your visibility in search results. Competitive prices rank higher.")
            }
            
            // MARK: - Recommendations
            Section {
                recommendationRow
            } header: {
                Text("AI Recommendations")
            }
            
            // MARK: - Earnings Projection
            Section {
                earningsProjection
            } header: {
                Text("Earnings Projection")
            }
            
            // MARK: - Save Button
            Section {
                Button {
                    savePricing()
                } label: {
                    HStack {
                        Spacer()
                        Text("Save Changes")
                            .fontWeight(.semibold)
                        Spacer()
                    }
                }
            }
        }
        .navigationTitle("Pricing Intelligence")
        .alert("Pricing Saved", isPresented: $showSaveConfirmation) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("Your new pricing has been updated and is now live.")
        }
    }
    
    // MARK: - Market Analysis Card
    
    private var marketAnalysisCard: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Area Average")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    if let suggested = listing.suggestedHourlyRate {
                        Text("₹\(Int(suggested))/hr")
                            .font(.title.bold())
                            .foregroundColor(DesignSystem.Colors.primary)
                    } else {
                        Text("Calculating...")
                            .font(.headline)
                            .foregroundColor(.secondary)
                    }
                }
                
                Spacer()
                
                // Competitiveness badge
                VStack(alignment: .trailing, spacing: 4) {
                    Text("Your Status")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Label(competitiveness.rawValue, systemImage: competitiveness.icon)
                        .font(.subheadline.bold())
                        .foregroundColor(competitiveness.color)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(competitiveness.color.opacity(0.15))
                        .cornerRadius(20)
                }
            }
            
            Divider()
            
            // Comparison chart
            HStack(spacing: DesignSystem.Spacing.xl) {
                comparisonBar(label: "You", value: currentHourlyRate, color: .green)
                comparisonBar(label: "Area Avg", value: listing.suggestedHourlyRate ?? 40, color: .orange)
            }
        }
        .padding(.vertical, DesignSystem.Spacing.s)
    }
    
    private var competitiveness: PriceCompetitiveness {
        guard let suggested = listing.suggestedHourlyRate, suggested > 0 else {
            return .unknown
        }
        let ratio = currentHourlyRate / suggested
        if ratio <= 0.9 { return .competitive }
        else if ratio <= 1.1 { return .fair }
        else if ratio <= 1.3 { return .high }
        else { return .tooExpensive }
    }
    
    private func comparisonBar(label: String, value: Double, color: Color) -> some View {
        VStack(spacing: 4) {
            Text("₹\(Int(value))")
                .font(.caption.bold())
            
            RoundedRectangle(cornerRadius: 4)
                .fill(color)
                .frame(width: 40, height: CGFloat(value) / 1.5)
            
            Text(label)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
    }
    
    // MARK: - Pricing Slider
    
    private func pricingSlider(label: String, value: Binding<Double>, range: ClosedRange<Double>, icon: String) -> some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(DesignSystem.Colors.primary)
                Text(label)
                Spacer()
                Text("₹\(Int(value.wrappedValue))")
                    .font(.headline)
                    .foregroundColor(DesignSystem.Colors.primary)
            }
            
            Slider(value: value, in: range, step: 5)
                .tint(DesignSystem.Colors.primary)
            
            HStack {
                Text("₹\(Int(range.lowerBound))")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                Spacer()
                Text("₹\(Int(range.upperBound))")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, DesignSystem.Spacing.s)
    }
    
    // MARK: - Recommendation Row
    
    private var recommendationRow: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
            HStack {
                Image(systemName: "sparkles")
                    .foregroundColor(.orange)
                Text("Smart Pricing Tip")
                    .font(.subheadline.bold())
            }
            
            if competitiveness == .tooExpensive {
                Text("Your price is 30%+ above the area average. Consider lowering to ₹\(Int((listing.suggestedHourlyRate ?? 40) * 1.1))/hr to improve bookings.")
            } else if competitiveness == .competitive {
                Text("Great pricing! You're below average which means you'll appear higher in search results.")
            } else {
                Text("Your pricing is fair. You can stay competitive by adding more amenities or improving your listing description.")
            }
        }
        .font(.subheadline)
        .foregroundColor(.secondary)
    }
    
    // MARK: - Earnings Projection
    
    private var earningsProjection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Weekly Projection")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("₹\(Int(currentHourlyRate * 4 * 7))") // 4 hrs/day avg
                        .font(.title2.bold())
                }
                
                Spacer()
                
                VStack(alignment: .trailing) {
                    Text("Monthly Projection")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("₹\(Int(currentHourlyRate * 4 * 30))")
                        .font(.title2.bold())
                        .foregroundColor(.green)
                }
            }
            
            Text("Based on 4 hours average daily occupancy")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.vertical, DesignSystem.Spacing.s)
    }
    
    // MARK: - Save
    
    private func savePricing() {
        // In a real app, this would update the listing
        showSaveConfirmation = true
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        PricingIntelligenceView(
            listing: PrivateParkingListing(
                id: UUID(),
                ownerID: UUID(),
                ownerName: "Test Host",
                title: "Sample Listing",
                address: "123 Test Street",
                coordinates: .init(latitude: 28.5, longitude: 77.2),
                listingDescription: "A nice parking spot",
                slots: [],
                hourlyRate: 45,
                dailyRate: 300,
                monthlyRate: 3000,
                flatFullBookingRate: nil,
                autoAcceptBookings: false,
                instantBookingDiscount: nil,
                hasCCTV: true, isCovered: true, hasEVCharging: true, hasSecurityGuard: true, hasWaterAccess: false, is24Hours: true,
                availableFrom: nil, availableTo: nil, availableDays: [1,2,3,4,5,6,7],
                rating: 4.5, reviewCount: 50,
                imageURLs: [],
                capturedPhotoData: nil,
                capturedVideoURL: nil,
                maxBookingDuration: .unlimited,
                suggestedHourlyRate: 42
            )
        )
    }
}
