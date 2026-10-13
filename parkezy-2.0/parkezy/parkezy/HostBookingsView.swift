
import SwiftUI

struct HostBookingsView: View {
    @EnvironmentObject var viewModel: HostViewModel
    @State private var selectedTab = 0
    @State private var searchText = ""
    
    var body: some View {
        VStack(spacing: 0) {
            // MARK: - Picker
            Picker("Filter", selection: $selectedTab) {
                Text("Active").tag(0)
                Text("History").tag(1)
            }
            .pickerStyle(.segmented)
            .padding()
            
            // MARK: - Search
            if selectedTab == 1 {
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.secondary)
                    TextField("Search booking ID or spot", text: $searchText)
                }
                .padding()
                .background(Color(.secondarySystemBackground))
                .cornerRadius(10)
                .padding(.horizontal)
                .padding(.bottom)
            }
            
            // MARK: - List
            ScrollView {
                LazyVStack(spacing: DesignSystem.Spacing.m) {
                    if currentBookings.isEmpty {
                        emptyState
                    } else {
                        ForEach(currentBookings) { booking in
                            HostBookingRow(booking: booking)
                        }
                    }
                }
                .padding()
            }
        }
        .navigationTitle("All Bookings")
    }
    
    private var currentBookings: [BookingSession] {
        if selectedTab == 0 {
            return viewModel.activeBookings
        } else {
            let history = viewModel.completedBookings
            if searchText.isEmpty {
                return history
            } else {
                return history.filter { booking in
                    booking.id.uuidString.localizedCaseInsensitiveContains(searchText) ||
                    (booking.accessCode ?? "").contains(searchText)
                }
            }
        }
    }
    
    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: selectedTab == 0 ? "car.fill" : "clock.fill")
                .font(.system(size: 48))
                .foregroundColor(.gray.opacity(0.3))
            
            Text(selectedTab == 0 ? "No active bookings" : "No booking history")
                .font(.headline)
                .foregroundColor(.secondary)
        }
        .padding(.top, 60)
    }
}

struct HostBookingRow: View {
    let booking: BookingSession
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("ID: \(booking.id.uuidString.prefix(6).uppercased())")
                    .font(.caption.bold())
                    .foregroundColor(.secondary)
                
                Spacer()
                
                StatusBadge(status: booking.status)
            }
            
            HStack {
                VStack(alignment: .leading) {
                    Label(booking.scheduledStartTime.formatted(date: .abbreviated, time: .shortened), systemImage: "calendar")
                        .font(.subheadline)
                    
                    if let code = booking.accessCode {
                        Label("Access: \(code)", systemImage: "key.fill")
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .padding(.top, 2)
                    }
                }
                
                Spacer()
                
                Text("₹\(Int(booking.totalCost))")
                    .font(.headline)
                    .foregroundColor(DesignSystem.Colors.primary)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.gray.opacity(0.1), lineWidth: 1)
        )
    }
}

struct StatusBadge: View {
    let status: BookingStatus
    
    var body: some View {
        Text(statusText)
            .font(.caption.bold())
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(statusColor.opacity(0.1))
            .foregroundColor(statusColor)
            .cornerRadius(8)
    }
    
    var statusText: String {
        switch status {
        case .active: return "ACTIVE"
        case .completed: return "COMPLETED"
        case .cancelled: return "CANCELLED"
        case .confirmed: return "CONFIRMED"
        case .pending: return "PENDING"
        case .disputed: return "DISPUTED"
        }
    }
    
    var statusColor: Color {
        switch status {
        case .active: return .green
        case .completed: return .blue
        case .cancelled: return .red
        case .confirmed: return .orange
        case .pending: return .yellow
        case .disputed: return .purple
        }
    }
}
