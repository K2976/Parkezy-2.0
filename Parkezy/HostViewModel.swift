//
//  HostViewModel.swift
//  ParkEzy
//
//  Manages host dashboard state, earnings, QR scanning, and chart data
//

import SwiftUI
import CoreLocation
import Combine

@MainActor
class HostViewModel: ObservableObject {
    // MARK: - Published Properties
    
    /// Current user in host mode
    @Published var currentHost: User?
    
    /// All parking spots owned by this host
    @Published var ownedSpots: [ParkingSpot] = []
    
    /// Active bookings for host's spots
    @Published var activeBookings: [BookingSession] = []
    
    /// Completed bookings history
    @Published var completedBookings: [BookingSession] = []
    
    /// Today's earnings (₹)
    @Published var todayEarnings: Double = 0
    
    /// Total lifetime earnings (₹)
    @Published var totalEarnings: Double = 0
    
    /// Number of active bookings right now
    @Published var activeBookingCount: Int = 0
    
    /// Last 7 days revenue data for line chart
    @Published var revenueData: [RevenueData] = []
    
    /// Peak hours booking distribution for bar chart
    @Published var peakHoursData: [PeakHourData] = []
    
    /// Booking type distribution for donut chart
    @Published var bookingDistribution: [BookingTypeData] = []
    
    /// QR scanner state
    @Published var isScanningQR: Bool = false
    @Published var lastScannedQR: String?
    @Published var scanResult: ScanResult?
    
    // MARK: - Private Properties
    
    private var cancellables = Set<AnyCancellable>()
    
    // MARK: - Initialization
    
    init() {
        loadMockHostData()
        generateChartData()
    }
    
    // MARK: - Data Loading
    
    /// Load mock host data for demo
    private func loadMockHostData() {
        // Create mock host user
        currentHost = User(
            id: UUID(),
            name: "Rohit Sharma",
            email: "rohit@parkezy.com",
            phoneNumber: "+91 98765 43210",
            profileImageURL: nil,
            isHost: true,
            hostRating: 4.8,
            totalBookings: 456
        )
        
        // Load owned spots from MockDataService (8 spots for this host)
        ownedSpots = Array(MockDataService.shared.parkingSpots.prefix(8))
        
        // Generate mock active bookings
        generateMockBookings()
        
        // Calculate earnings
        calculateEarnings()
    }
    
    /// Generate mock bookings for demo
    private func generateMockBookings() {
        let calendar = Calendar.current
        let now = Date()
        
        // 6 Active bookings (currently parked)
        for i in 0..<6 {
            let spot = ownedSpots[i % ownedSpots.count]
            let hoursAgo = Double.random(in: 0.5...3.0)
            let startTime = calendar.date(byAdding: .minute, value: -Int(hoursAgo * 60), to: now)!
            let duration = Double.random(in: 1.0...4.0)
            let endTime = calendar.date(byAdding: .hour, value: Int(duration), to: startTime)!
            
            let booking = BookingSession(
                id: UUID(),
                spotID: spot.id,
                userID: UUID(),
                bookingTime: calendar.date(byAdding: .hour, value: -1, to: startTime)!,
                scheduledStartTime: startTime,
                actualStartTime: startTime,
                scheduledEndTime: endTime,
                actualEndTime: nil,
                duration: duration,
                totalCost: spot.pricePerHour * duration * 1.18, // Including GST
                status: .active,
                accessCode: String(format: "%06d", Int.random(in: 100000...999999))
            )
            
            activeBookings.append(booking)
        }
        
        // 75 Completed bookings for history (spread across last 30 days)
        for i in 0..<75 {
            let spot = ownedSpots[i % ownedSpots.count]
            let daysAgo = Int.random(in: 0...30)
            let hour = Int.random(in: 8...20)
            var components = calendar.dateComponents([.year, .month, .day], from: calendar.date(byAdding: .day, value: -daysAgo, to: now)!)
            components.hour = hour
            components.minute = Int.random(in: 0...59)
            let startTime = calendar.date(from: components) ?? now
            let duration = Double.random(in: 0.5...6.0)
            let endTime = calendar.date(byAdding: .minute, value: Int(duration * 60), to: startTime)!
            
            let booking = BookingSession(
                id: UUID(),
                spotID: spot.id,
                userID: UUID(),
                bookingTime: calendar.date(byAdding: .hour, value: -2, to: startTime)!,
                scheduledStartTime: startTime,
                actualStartTime: startTime,
                scheduledEndTime: endTime,
                actualEndTime: endTime,
                duration: duration,
                totalCost: spot.pricePerHour * duration * 1.18,
                status: .completed,
                accessCode: String(format: "%06d", Int.random(in: 100000...999999))
            )
            
            completedBookings.append(booking)
        }
        
        activeBookingCount = activeBookings.count
    }
    
    /// Calculate earnings from bookings
    private func calculateEarnings() {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        
        // Commission rates
        let mallCommission = 0.12 // 12%
        let privateCommission = 0.15 // 15%
        
        // Calculate today's earnings
        let todayBookings = completedBookings.filter {
            guard let endTime = $0.actualEndTime else { return false }
            return calendar.isDate(endTime, inSameDayAs: today)
        }
        
        todayEarnings = todayBookings.reduce(0) { sum, booking in
            let spot = ownedSpots.first(where: { $0.id == booking.spotID })
            let commission = spot?.type == .mall ? mallCommission : privateCommission
            return sum + (booking.totalCost * commission)
        }
        
        // Calculate total earnings
        totalEarnings = completedBookings.reduce(0) { sum, booking in
            let spot = ownedSpots.first(where: { $0.id == booking.spotID })
            let commission = spot?.type == .mall ? mallCommission : privateCommission
            return sum + (booking.totalCost * commission)
        }
    }
    
    // MARK: - Chart Data Generation
    
    /// Generate all chart data for dashboard
    private func generateChartData() {
        generateRevenueData()
        generatePeakHoursData()
        generateBookingDistribution()
    }
    
    /// Generate last 7 days revenue for line chart
    private func generateRevenueData() {
        let calendar = Calendar.current
        let today = Date()
        
        revenueData = (0..<7).reversed().map { daysAgo in
            let date = calendar.date(byAdding: .day, value: -daysAgo, to: today)!
            
            // Get bookings for this day
            let dayBookings = completedBookings.filter {
                guard let endTime = $0.actualEndTime else { return false }
                return calendar.isDate(endTime, inSameDayAs: date)
            }
            
            // Calculate revenue
            let revenue = dayBookings.reduce(0.0) { sum, booking in
                let spot = ownedSpots.first(where: { $0.id == booking.spotID })
                let commission = spot?.type == .mall ? 0.12 : 0.15
                return sum + (booking.totalCost * commission)
            }
            
            return RevenueData(date: date, amount: revenue)
        }
    }
    
    /// Generate peak hours booking count for bar chart
    private func generatePeakHoursData() {
        // Group bookings by hour of day (0-23)
        var hourCounts: [Int: Int] = [:]
        
        for booking in completedBookings {
            let hour = Calendar.current.component(.hour, from: booking.scheduledStartTime)
            hourCounts[hour, default: 0] += 1
        }
        
        // Create data for each hour (show only busy hours 8-22)
        peakHoursData = (8...22).map { hour in
            PeakHourData(
                hour: hour,
                count: hourCounts[hour] ?? 0,
                displayTime: String(format: "%02d:00", hour)
            )
        }
    }
    
    /// Generate booking type distribution for donut chart
    private func generateBookingDistribution() {
        let mallCount = completedBookings.filter { booking in
            let spot = ownedSpots.first { spot in
                spot.id == booking.spotID
            }
            return spot?.type == .mall
        }.count

        let total = completedBookings.count
        let privateCount = total - mallCount

        bookingDistribution = [
            BookingTypeData(
                type: "Mall Parking",
                count: mallCount,
                percentage: total > 0
                    ? Int(Double(mallCount) / Double(total) * 100)
                    : 0,
                color: .blue
            ),
            BookingTypeData(
                type: "Private Driveway",
                count: privateCount,
                percentage: total > 0
                    ? Int(Double(privateCount) / Double(total) * 100)
                    : 0,
                color: .green
            )
        ]
    }
    
    // MARK: - QR Code Validation
    
    /// Validate scanned QR code
    func validateQRCode(_ qrString: String) {
        lastScannedQR = qrString
        
        // Parse QR code format: "PARKEZY:<bookingID>:<spotID>"
        guard let (bookingID, spotID) = QRCodeService.shared.parseQRCode(qrString) else {
            scanResult = .invalid
            return
        }
        
        // Check if booking exists in active bookings
        if let booking = activeBookings.first(where: { $0.id == bookingID }) {
            // Verify spot belongs to this host
            if ownedSpots.contains(where: { $0.id == spotID }) {
                scanResult = .validEntry(booking: booking)
            } else {
                scanResult = .wrongHost
            }
        } else if let booking = completedBookings.first(where: { $0.id == bookingID }) {
            // This is an exit scan
            scanResult = .validExit(booking: booking)
        } else {
            scanResult = .notFound
        }
    }
    
    /// Confirm entry after QR scan
    func confirmEntry(booking: BookingSession) {
        // Update booking to started
        if let index = activeBookings.firstIndex(where: { $0.id == booking.id }) {
            activeBookings[index].actualStartTime = Date()
            NotificationManager.shared.scheduleNotification(
                title: "Entry Confirmed",
                body: "Booking started for \(booking.accessCode ?? "N/A")",
                delay: 0.1
            )
        }
    }
    
    /// Confirm exit after QR scan
    func confirmExit(booking: BookingSession) {
        // Move from active to completed
        if let index = activeBookings.firstIndex(where: { $0.id == booking.id }) {
            var completedBooking = activeBookings[index]
            completedBooking.actualEndTime = Date()
            completedBooking.status = .completed
            
            activeBookings.remove(at: index)
            completedBookings.append(completedBooking)
            activeBookingCount -= 1
            
            // Recalculate earnings
            calculateEarnings()
            generateChartData()
            
            NotificationManager.shared.scheduleNotification(
                title: "Exit Confirmed",
                body: "Booking completed. Earnings updated!",
                delay: 0.1
            )
        }
    }
    
    // MARK: - Refresh Data
    
    /// Update revenue data based on selected time range
    func updateRevenueData(for range: TimeRange) {
        let calendar = Calendar.current
        let today = Date()
        
        switch range {
        case .week:
            // Show last 7 days
            revenueData = (0..<7).reversed().map { daysAgo in
                let date = calendar.date(byAdding: .day, value: -daysAgo, to: today)!
                let amount = Double.random(in: 50...300)
                return RevenueData(date: date, amount: amount)
            }
            
        case .month:
            // Show last 4 weeks (aggregated by week)
            revenueData = (0..<4).reversed().map { weeksAgo in
                let date = calendar.date(byAdding: .weekOfYear, value: -weeksAgo, to: today)!
                let amount = Double.random(in: 500...2000)
                return RevenueData(date: date, amount: amount)
            }
            
        case .year:
            // Show last 12 months
            revenueData = (0..<12).reversed().map { monthsAgo in
                let date = calendar.date(byAdding: .month, value: -monthsAgo, to: today)!
                let amount = Double.random(in: 2000...10000)
                return RevenueData(date: date, amount: amount)
            }
        }
    }
    
    /// Refresh all dashboard data
    func refreshDashboard() {
        calculateEarnings()
        generateChartData()
        activeBookingCount = activeBookings.count
    }
}

// MARK: - Chart Data Models

/// Revenue data point for line chart
struct RevenueData: Identifiable {
    let id = UUID()
    let date: Date
    let amount: Double
    
    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d"
        return formatter.string(from: date)
    }
    
    var formattedAmount: String {
        return String(format: "₹%.0f", amount)
    }
}

/// Peak hour data for bar chart
struct PeakHourData: Identifiable {
    let id = UUID()
    let hour: Int
    let count: Int
    let displayTime: String
}

/// Booking type distribution for donut chart
struct BookingTypeData: Identifiable {
    let id = UUID()
    let type: String
    let count: Int
    let percentage: Int
    let color: Color
}

// MARK: - Time Range Enum

/// Time range options for revenue chart filtering
enum TimeRange {
    case week
    case month
    case year
}

// MARK: - Scan Result Enum

enum ScanResult {
    case validEntry(booking: BookingSession)
    case validExit(booking: BookingSession)
    case invalid
    case notFound
    case wrongHost
    
    var message: String {
        switch self {
        case .validEntry:
            return "✅ Valid Entry - Confirm to start session"
        case .validExit:
            return "✅ Valid Exit - Confirm to end session"
        case .invalid:
            return "❌ Invalid QR Code"
        case .notFound:
            return "❌ Booking Not Found"
        case .wrongHost:
            return "❌ This spot doesn't belong to you"
        }
    }
}
