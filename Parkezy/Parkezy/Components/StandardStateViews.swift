//
//  StandardStateViews.swift
//  ParkEzy
//
//  Reusable Loading / Empty / Error / Offline state views.
//  Drop these into any screen to provide consistent user feedback.
//

import SwiftUI

// MARK: - Loading State

struct LoadingStateView: View {
    var message: String = "Loading…"
    
    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)
                .tint(DesignSystem.Colors.primary)
            
            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

// MARK: - Empty State

struct EmptyStateView: View {
    var icon: String = "tray"
    var title: String = "Nothing here yet"
    var message: String = "Items will appear here once available."
    var actionTitle: String? = nil
    var action: (() -> Void)? = nil
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: icon)
                .font(.system(size: 56))
                .foregroundStyle(
                    LinearGradient(
                        colors: [DesignSystem.Colors.primary.opacity(0.6), DesignSystem.Colors.primary.opacity(0.2)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
            
            VStack(spacing: 8) {
                Text(title)
                    .font(.title3.bold())
                
                Text(message)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }
            
            if let actionTitle, let action {
                Button(action: action) {
                    Text(actionTitle)
                        .font(.subheadline.bold())
                        .padding(.horizontal, 24)
                        .padding(.vertical, 12)
                        .background(DesignSystem.Colors.primary)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

// MARK: - Error State

struct ErrorStateView: View {
    var message: String = "Something went wrong."
    var retryAction: (() -> Void)? = nil
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 48))
                .foregroundColor(.orange)
            
            VStack(spacing: 8) {
                Text("Error")
                    .font(.title3.bold())
                
                Text(message)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }
            
            if let retryAction {
                Button(action: retryAction) {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.clockwise")
                        Text("Retry")
                    }
                    .font(.subheadline.bold())
                    .padding(.horizontal, 24)
                    .padding(.vertical, 12)
                    .background(DesignSystem.Colors.primary)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

// MARK: - Offline Banner

struct OfflineBannerView: View {
    @ObservedObject private var networkMonitor = NetworkMonitor.shared
    
    var body: some View {
        if !networkMonitor.isConnected {
            HStack(spacing: 8) {
                Image(systemName: "wifi.slash")
                    .font(.subheadline)
                Text("You're offline")
                    .font(.subheadline.bold())
                Spacer()
                Text("Some features may be unavailable")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.8))
            }
            .foregroundColor(.white)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(Color.red.opacity(0.85))
            .transition(.move(edge: .top).combined(with: .opacity))
        }
    }
}

// MARK: - Previews

#Preview("Loading") {
    LoadingStateView()
}

#Preview("Empty") {
    EmptyStateView(
        icon: "car.fill",
        title: "No Bookings",
        message: "You haven't made any bookings yet.",
        actionTitle: "Find Parking"
    ) {
        print("Tapped")
    }
}

#Preview("Error") {
    ErrorStateView(message: "Failed to load data.") {
        print("Retry")
    }
}

#Preview("Offline Banner") {
    VStack {
        OfflineBannerView()
        Spacer()
    }
}
