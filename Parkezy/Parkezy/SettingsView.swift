//
//  SettingsView.swift
//  ParkEzy
//
//  Settings screen for Host mode with profile, notifications, and app preferences
//

import SwiftUI

struct SettingsView: View {
    // MARK: - Environment
    
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var hostViewModel: HostViewModel
    
    // MARK: - State
    
    @State private var notificationsEnabled = true
    @State private var emailNotifications = true
    @State private var smsNotifications = false
    @State private var autoAcceptBookings = true
    @State private var showEarningsOnWidget = true
    @State private var darkModeEnabled = false
    @State private var biometricLockEnabled = false
    @State private var showLogoutAlert = false
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            List {
                // MARK: - Profile Section
                
                Section {
                    HStack(spacing: DesignSystem.Spacing.m) {
                        // Profile Avatar
                        ZStack {
                            Circle()
                                .fill(
                                    LinearGradient(
                                        colors: [DesignSystem.Colors.primary, DesignSystem.Colors.primary.opacity(0.7)],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                                .frame(width: 60, height: 60)
                            
                            Text(String(hostViewModel.currentHost?.name.prefix(1) ?? "H"))
                                .font(.title.bold())
                                .foregroundColor(.white)
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text(hostViewModel.currentHost?.name ?? "Host")
                                .font(.headline)
                            Text(hostViewModel.currentHost?.email ?? "email@example.com")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        
                        Spacer()
                        
                        Image(systemName: "chevron.right")
                            .foregroundColor(.gray)
                    }
                    .padding(.vertical, DesignSystem.Spacing.s)
                } header: {
                    Text("Profile")
                }
                
                // MARK: - Notifications Section
                
                Section {
                    Toggle(isOn: $notificationsEnabled) {
                        SettingsRow(icon: "bell.fill", title: "Push Notifications", color: .red)
                    }
                    
                    Toggle(isOn: $emailNotifications) {
                        SettingsRow(icon: "envelope.fill", title: "Email Notifications", color: .blue)
                    }
                    
                    Toggle(isOn: $smsNotifications) {
                        SettingsRow(icon: "message.fill", title: "SMS Alerts", color: .green)
                    }
                } header: {
                    Text("Notifications")
                } footer: {
                    Text("Get notified about new bookings, payments, and important updates.")
                }
                
                // MARK: - Booking Preferences Section
                
                Section {
                    Toggle(isOn: $autoAcceptBookings) {
                        SettingsRow(icon: "checkmark.circle.fill", title: "Auto-Accept Bookings", color: .green)
                    }
                    
                    NavigationLink {
                        PricingSettingsView()
                    } label: {
                        SettingsRow(icon: "indianrupeesign.circle.fill", title: "Pricing Settings", color: .orange)
                    }
                    
                    NavigationLink {
                        AvailabilitySettingsView()
                    } label: {
                        SettingsRow(icon: "clock.fill", title: "Availability Hours", color: .purple)
                    }
                } header: {
                    Text("Booking Preferences")
                }
                
                // MARK: - Payment Section
                
                Section {
                    NavigationLink {
                        PaymentSettingsView()
                    } label: {
                        SettingsRow(icon: "creditcard.fill", title: "Payment Methods", color: .blue)
                    }
                    
                    NavigationLink {
                        BankAccountView()
                    } label: {
                        SettingsRow(icon: "building.columns.fill", title: "Bank Account", color: .teal)
                    }
                    
                    NavigationLink {
                        TransactionHistoryView()
                    } label: {
                        SettingsRow(icon: "list.bullet.rectangle.fill", title: "Transaction History", color: .indigo)
                    }
                } header: {
                    Text("Payments")
                }
                
                // MARK: - App Settings Section
                
                Section {
                    Toggle(isOn: $showEarningsOnWidget) {
                        SettingsRow(icon: "square.grid.2x2.fill", title: "Show Earnings on Widget", color: .cyan)
                    }
                    
                    Toggle(isOn: $biometricLockEnabled) {
                        SettingsRow(icon: "faceid", title: "Face ID / Touch ID", color: .green)
                    }
                    
                    NavigationLink {
                        AppearanceSettingsView()
                    } label: {
                        SettingsRow(icon: "paintbrush.fill", title: "Appearance", color: .pink)
                    }
                } header: {
                    Text("App Settings")
                }
                
                // MARK: - Support Section
                
                Section {
                    NavigationLink {
                        HelpCenterView()
                    } label: {
                        SettingsRow(icon: "questionmark.circle.fill", title: "Help Center", color: .blue)
                    }
                    
                    NavigationLink {
                        ContactSupportView()
                    } label: {
                        SettingsRow(icon: "headphones", title: "Contact Support", color: .orange)
                    }
                    
                    Link(destination: URL(string: "https://parkezy.com/terms")!) {
                        SettingsRow(icon: "doc.text.fill", title: "Terms of Service", color: .gray)
                    }
                    
                    Link(destination: URL(string: "https://parkezy.com/privacy")!) {
                        SettingsRow(icon: "hand.raised.fill", title: "Privacy Policy", color: .gray)
                    }
                } header: {
                    Text("Support")
                }
                
                // MARK: - About Section
                
                Section {
                    HStack {
                        SettingsRow(icon: "info.circle.fill", title: "Version", color: .gray)
                        Spacer()
                        Text("2.0.1")
                            .foregroundColor(.secondary)
                    }
                    
                    NavigationLink {
                        AboutAppView()
                    } label: {
                        SettingsRow(icon: "star.fill", title: "Rate ParkEzy", color: .yellow)
                    }
                    
                    Button {
                        shareApp()
                    } label: {
                        SettingsRow(icon: "square.and.arrow.up.fill", title: "Share App", color: .blue)
                    }
                } header: {
                    Text("About")
                }
                
                // MARK: - Logout Section
                
                Section {
                    Button {
                        showLogoutAlert = true
                    } label: {
                        HStack {
                            Spacer()
                            Text("Log Out")
                                .foregroundColor(.red)
                                .fontWeight(.semibold)
                            Spacer()
                        }
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
            .alert("Log Out", isPresented: $showLogoutAlert) {
                Button("Cancel", role: .cancel) { }
                Button("Log Out", role: .destructive) {
                    // Handle logout
                }
            } message: {
                Text("Are you sure you want to log out?")
            }
        }
    }
    
    // MARK: - Methods
    
    private func shareApp() {
        let url = URL(string: "https://apps.apple.com/app/parkezy")!
        let activityVC = UIActivityViewController(activityItems: [url], applicationActivities: nil)
        
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first {
            window.rootViewController?.present(activityVC, animated: true)
        }
    }
}

// MARK: - Settings Row Component

struct SettingsRow: View {
    let icon: String
    let title: String
    let color: Color
    
    var body: some View {
        HStack(spacing: DesignSystem.Spacing.m) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(.white)
                .frame(width: 28, height: 28)
                .background(color)
                .cornerRadius(6)
            
            Text(title)
                .foregroundColor(.primary)
        }
    }
}

// MARK: - Placeholder Views

struct PricingSettingsView: View {
    @State private var hourlyRate: Double = 50
    @State private var dailyRate: Double = 400
    @State private var weeklyRate: Double = 2000
    @State private var dynamicPricingEnabled = true
    
    var body: some View {
        Form {
            Section {
                HStack {
                    Text("Hourly Rate")
                    Spacer()
                    Text("₹\(Int(hourlyRate))")
                        .foregroundColor(.secondary)
                }
                Slider(value: $hourlyRate, in: 20...200, step: 5)
                
                HStack {
                    Text("Daily Rate")
                    Spacer()
                    Text("₹\(Int(dailyRate))")
                        .foregroundColor(.secondary)
                }
                Slider(value: $dailyRate, in: 100...1000, step: 50)
                
                HStack {
                    Text("Weekly Rate")
                    Spacer()
                    Text("₹\(Int(weeklyRate))")
                        .foregroundColor(.secondary)
                }
                Slider(value: $weeklyRate, in: 500...5000, step: 100)
            } header: {
                Text("Base Rates")
            }
            
            Section {
                Toggle("Dynamic Pricing", isOn: $dynamicPricingEnabled)
                if dynamicPricingEnabled {
                    Text("Prices will automatically adjust based on demand. Peak hours may charge up to 1.5x the base rate.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            } header: {
                Text("Smart Pricing")
            }
        }
        .navigationTitle("Pricing")
    }
}

struct AvailabilitySettingsView: View {
    @State private var is24Hours = false
    @State private var openingTime = Date()
    @State private var closingTime = Date()
    @State private var weekendsOnly = false
    
    var body: some View {
        Form {
            Section {
                Toggle("24 Hours", isOn: $is24Hours)
                
                if !is24Hours {
                    DatePicker("Opens At", selection: $openingTime, displayedComponents: .hourAndMinute)
                    DatePicker("Closes At", selection: $closingTime, displayedComponents: .hourAndMinute)
                }
            } header: {
                Text("Operating Hours")
            }
            
            Section {
                Toggle("Weekends Only", isOn: $weekendsOnly)
            } header: {
                Text("Days Available")
            }
        }
        .navigationTitle("Availability")
    }
}

struct PaymentSettingsView: View {
    var body: some View {
        List {
            Section {
                HStack {
                    Image(systemName: "creditcard.fill")
                        .foregroundColor(.blue)
                    VStack(alignment: .leading) {
                        Text("•••• •••• •••• 4532")
                        Text("Expires 12/27")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Text("Default")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.green.opacity(0.2))
                        .foregroundColor(.green)
                        .cornerRadius(4)
                }
            } header: {
                Text("Saved Cards")
            }
            
            Section {
                Button {
                    // Add new card
                } label: {
                    Label("Add New Card", systemImage: "plus.circle.fill")
                }
            }
        }
        .navigationTitle("Payment Methods")
    }
}

struct BankAccountView: View {
    var body: some View {
        Form {
            Section {
                HStack {
                    Text("Bank Name")
                    Spacer()
                    Text("HDFC Bank")
                        .foregroundColor(.secondary)
                }
                HStack {
                    Text("Account Number")
                    Spacer()
                    Text("•••• •••• 7834")
                        .foregroundColor(.secondary)
                }
                HStack {
                    Text("IFSC Code")
                    Spacer()
                    Text("HDFC0001234")
                        .foregroundColor(.secondary)
                }
            } header: {
                Text("Linked Account")
            } footer: {
                Text("Earnings are transferred to this account every Monday.")
            }
            
            Section {
                Button("Update Bank Details") {
                    // Update bank
                }
            }
        }
        .navigationTitle("Bank Account")
    }
}

struct TransactionHistoryView: View {
    var body: some View {
        List {
            ForEach(0..<10) { i in
                HStack {
                    VStack(alignment: .leading) {
                        Text("Booking #\(String(format: "%06d", Int.random(in: 100000...999999)))")
                            .font(.subheadline.bold())
                        Text("\(30 - i) Jan 2026")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Text("+₹\(Int.random(in: 100...500))")
                        .foregroundColor(.green)
                        .fontWeight(.semibold)
                }
            }
        }
        .navigationTitle("Transactions")
    }
}

struct AppearanceSettingsView: View {
    @State private var selectedTheme = 0
    
    var body: some View {
        Form {
            Section {
                Picker("Theme", selection: $selectedTheme) {
                    Text("System").tag(0)
                    Text("Light").tag(1)
                    Text("Dark").tag(2)
                }
                .pickerStyle(.segmented)
            } header: {
                Text("App Theme")
            }
        }
        .navigationTitle("Appearance")
    }
}

struct HelpCenterView: View {
    var body: some View {
        List {
            Section("Popular Topics") {
                NavigationLink("How do bookings work?") { Text("Help article here...") }
                NavigationLink("Setting up your parking spot") { Text("Help article here...") }
                NavigationLink("Managing earnings") { Text("Help article here...") }
                NavigationLink("QR code scanning issues") { Text("Help article here...") }
            }
            
            Section("Account") {
                NavigationLink("Change password") { Text("Help article here...") }
                NavigationLink("Update profile") { Text("Help article here...") }
            }
        }
        .navigationTitle("Help Center")
    }
}

struct ContactSupportView: View {
    @State private var message = ""
    
    var body: some View {
        Form {
            Section {
                TextEditor(text: $message)
                    .frame(height: 150)
            } header: {
                Text("Describe your issue")
            }
            
            Section {
                Button("Submit") {
                    // Submit support ticket
                }
                .frame(maxWidth: .infinity)
            }
            
            Section {
                Link(destination: URL(string: "tel:+911234567890")!) {
                    Label("Call Support", systemImage: "phone.fill")
                }
                Link(destination: URL(string: "mailto:support@parkezy.com")!) {
                    Label("Email Support", systemImage: "envelope.fill")
                }
            } header: {
                Text("Other Ways to Reach Us")
            }
        }
        .navigationTitle("Contact Support")
    }
}

struct AboutAppView: View {
    var body: some View {
        VStack(spacing: DesignSystem.Spacing.xl) {
            Spacer()
            
            Image(systemName: "parkingsign.circle.fill")
                .font(.system(size: 80))
                .foregroundColor(DesignSystem.Colors.primary)
            
            Text("ParkEzy")
                .font(.largeTitle.bold())
            
            Text("Version 2.0.1")
                .foregroundColor(.secondary)
            
            Text("Making parking effortless since 2024")
                .multilineTextAlignment(.center)
                .foregroundColor(.secondary)
                .padding(.horizontal)
            
            Spacer()
            
            Text("Made with ❤️ in India")
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.bottom)
        }
        .navigationTitle("About")
    }
}

// MARK: - Preview

#Preview {
    SettingsView()
        .environmentObject(HostViewModel())
}
