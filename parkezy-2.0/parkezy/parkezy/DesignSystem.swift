//
//  DesignSystem.swift
//  ParkEzy
//
//  Design tokens and utilities for consistent UI
//

import SwiftUI

enum DesignSystem {
    // MARK: - Colors
    
    enum Colors {
        /// Primary brand color (iOS Blue)
        static let primary = Color(hex: "007AFF")
        
        /// Success color (Green - available spots)
        static let success = Color(hex: "34C759")
        
        /// Error color (Red - occupied spots, warnings)
        static let error = Color(hex: "FF3B30")
        
        /// Warning color (Orange)
        static let warning = Color(hex: "FF9500")
        
        /// Secondary text color
        static let secondaryText = Color.secondary
        
        /// Background colors
        static let background = Color(.systemBackground)
        static let secondaryBackground = Color(.secondarySystemBackground)
        
        /// Gradient for primary actions
        static var primaryGradient: LinearGradient {
            LinearGradient(
                colors: [primary, primary.opacity(0.7)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
        
        /// Gradient for success states
        static var successGradient: LinearGradient {
            LinearGradient(
                colors: [success, success.opacity(0.7)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
    }
    
    // MARK: - Spacing
    
    enum Spacing {
        /// Extra small: 4pt
        static let xs: CGFloat = 4
        
        /// Small: 8pt
        static let s: CGFloat = 8
        
        /// Medium: 16pt (standard padding)
        static let m: CGFloat = 16
        
        /// Large: 24pt
        static let l: CGFloat = 24
        
        /// Extra large: 32pt
        static let xl: CGFloat = 32
        
        /// Extra extra large: 48pt
        static let xxl: CGFloat = 48
    }
    
    // MARK: - Typography
    
    enum Typography {
        static let largeTitle = Font.system(size: 34, weight: .bold, design: .rounded)
        static let title = Font.system(size: 28, weight: .bold, design: .rounded)
        static let title2 = Font.system(size: 22, weight: .bold, design: .rounded)
        static let headline = Font.system(size: 17, weight: .semibold)
        static let body = Font.system(size: 17, weight: .regular)
        static let callout = Font.system(size: 16, weight: .regular)
        static let subheadline = Font.system(size: 15, weight: .regular)
        static let footnote = Font.system(size: 13, weight: .regular)
        static let caption = Font.system(size: 12, weight: .regular)
        static let caption2 = Font.system(size: 11, weight: .regular)
        
        // Monospaced for codes/numbers
        static let mono = Font.system(size: 17, weight: .regular, design: .monospaced)
        static let monoLarge = Font.system(size: 24, weight: .bold, design: .monospaced)
    }
    
    // MARK: - Shadows
    
    enum Shadows {
        static let small = Shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
        static let medium = Shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 5)
        static let large = Shadow(color: .black.opacity(0.15), radius: 20, x: 0, y: 10)
    }
    
    // MARK: - Animation
    
    enum Animation {
        static let quick = SwiftUI.Animation.spring(response: 0.3, dampingFraction: 0.7)
        static let standard = SwiftUI.Animation.spring(response: 0.4, dampingFraction: 0.7)
        static let slow = SwiftUI.Animation.spring(response: 0.6, dampingFraction: 0.7)
        
        static let easeOut = SwiftUI.Animation.easeOut(duration: 0.3)
        static let easeInOut = SwiftUI.Animation.easeInOut(duration: 0.4)
    }
    
    // MARK: - Icons (SF Symbols)
    
    enum Icons {
        // Navigation
        static let home = "house.fill"
        static let map = "map.fill"
        static let profile = "person.fill"
        static let settings = "gearshape.fill"
        
        // Parking
        static let parking = "parkingsign"
        static let parkingCircle = "parkingsign.circle.fill"
        static let car = "car.fill"
        static let location = "location.fill"
        
        // Actions
        static let scan = "qrcode.viewfinder"
        static let qrCode = "qrcode"
        static let timer = "timer"
        static let extend = "arrow.clockwise"
        static let stop = "stop.fill"
        
        // Status
        static let success = "checkmark.circle.fill"
        static let error = "xmark.circle.fill"
        static let warning = "exclamationmark.triangle.fill"
        static let info = "info.circle.fill"
        
        // Features
        static let cctv = "video.fill"
        static let covered = "umbrella.fill"
        static let ev = "bolt.car.fill"
        static let accessible = "figure.walk"
        static let hours24 = "24.circle.fill"
        static let insurance = "shield.fill"
        
        // Payments
        static let wallet = "wallet.pass.fill"
        static let applePay = "apple.logo"
        static let rupee = "indianrupeesign.circle.fill"
    }
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Shadow Struct

struct Shadow {
    let color: Color
    let radius: CGFloat
    let x: CGFloat
    let y: CGFloat
}

// MARK: - View Extensions

extension View {
    func cardStyle() -> some View {
        self
            .padding(DesignSystem.Spacing.m)
            .background(Color(.systemBackground))
            .cornerRadius(DesignSystem.Spacing.m)
            .shadow(
                color: .black.opacity(0.05),
                radius: 10,
                x: 0,
                y: 5
            )
    }
    
    func primaryButtonStyle() -> some View {
        self
            .font(.headline)
            .frame(maxWidth: .infinity)
            .padding()
            .background(DesignSystem.Colors.primary)
            .foregroundColor(.white)
            .cornerRadius(DesignSystem.Spacing.m)
    }
    
    func secondaryButtonStyle() -> some View {
        self
            .font(.headline)
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.gray.opacity(0.1))
            .foregroundColor(.primary)
            .cornerRadius(DesignSystem.Spacing.m)
    }
}
