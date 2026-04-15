
import SwiftUI

struct BookingDetailView: View {
    let booking: PrivateBooking
    let listingName: String
    
    var body: some View {
        ScrollView {
            VStack(spacing: DesignSystem.Spacing.l) {
                // MARK: - Header Status
                headerSection
                
                // MARK: - Driver Info
                driverInfoSection
                
                // MARK: - Booking Details
                bookingDetailsSection
                
                // MARK: - Pricing
                pricingSection
                
                // MARK: - Actions
                // Add actions if needed (e.g., call driver, cancel)
            }
            .padding(DesignSystem.Spacing.m)
        }
        .navigationTitle("Booking Details")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    private var headerSection: some View {
        VStack(spacing: DesignSystem.Spacing.s) {
            Circle()
                .fill(booking.status.color.opacity(0.1))
                .frame(width: 80, height: 80)
                .overlay(
                    Image(systemName: booking.status.icon)
                        .font(.system(size: 32))
                        .foregroundColor(booking.status.color)
                )
            
            Text(booking.status.rawValue)
                .font(.title2.bold())
                .foregroundColor(booking.status.color)
            
            Text("Reference ID: \(booking.id.uuidString.prefix(8))")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, DesignSystem.Spacing.l)
    }
    
    private var driverInfoSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Driver Information")
                .font(.headline)
            
            HStack {
                Circle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(width: 50, height: 50)
                    .overlay(
                        Text(String(booking.driverName.prefix(1)))
                            .font(.title2.bold())
                    )
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(booking.driverName)
                        .font(.headline)
                    if let vehicle = booking.vehicleNumber {
                        Text(vehicle)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }
                
                Spacer()
                
                Button {
                    // Call driver
                } label: {
                    Image(systemName: "phone.circle.fill")
                        .font(.system(size: 32))
                        .foregroundColor(.green)
                }
                
                Button {
                    // Message driver
                } label: {
                    Image(systemName: "message.circle.fill")
                        .font(.system(size: 32))
                        .foregroundColor(.blue)
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(Color(.secondarySystemBackground))
            .cornerRadius(12)
        }
    }
    
    private var bookingDetailsSection: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
            Text("Booking Details")
                .font(.headline)
            
            VStack(spacing: DesignSystem.Spacing.s) {
                detailRow(icon: "mappin.and.ellipse", title: "Location", value: listingName)
                Divider()
                detailRow(icon: "calendar", title: "Start Time", value: booking.scheduledStartTime.formatted(date: .abbreviated, time: .shortened))
                Divider()
                detailRow(icon: "clock", title: "Duration", value: "\(Int(booking.estimatedCost/booking.agreedRate)) hours (approx)")
                Divider()
                detailRow(icon: "key", title: "Access PIN", value: booking.accessPIN ?? "N/A")
            }
            .padding(DesignSystem.Spacing.m)
            .background(Color(.secondarySystemBackground))
            .cornerRadius(12)
        }
    }
    
    // Only show pricing if status is NOT rejected or cancelled
    @ViewBuilder
    private var pricingSection: some View {
        if booking.status != .rejected && booking.status != .cancelled {
            VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
                Text("Payment Breakdown")
                    .font(.headline)
                
                VStack(spacing: DesignSystem.Spacing.s) {
                    HStack {
                        Text("Rate per hour")
                        Spacer()
                        Text("₹\(Int(booking.agreedRate))")
                    }
                    Divider()
                    HStack {
                        Text("Total Amount")
                            .fontWeight(.bold)
                        Spacer()
                        Text("₹\(Int(booking.actualCost ?? booking.estimatedCost))")
                            .fontWeight(.bold)
                            .foregroundColor(.green)
                    }
                    
                    if let earnings = booking.hostEarnings {
                        Divider()
                        HStack {
                            Text("Your Earnings")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                            Spacer()
                            Text("₹\(Int(earnings))")
                                .font(.subheadline.bold())
                                .foregroundColor(.green)
                        }
                    }
                }
                .padding(DesignSystem.Spacing.m)
                .background(Color(.secondarySystemBackground))
                .cornerRadius(12)
            }
        }
    }
    
    private func detailRow(icon: String, title: String, value: String) -> some View {
        HStack {
            Image(systemName: icon)
                .frame(width: 24)
                .foregroundColor(.secondary)
            Text(title)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.medium)
        }
    }
}
