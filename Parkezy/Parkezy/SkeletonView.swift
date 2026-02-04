//
//  SkeletonView.swift
//  ParkEzy
//
//  Loading skeleton component with shimmer effect
//

import SwiftUI

// MARK: - Shimmer Effect Modifier

struct ShimmerEffect: ViewModifier {
    @State private var phase: CGFloat = -1
    var duration: Double = 1.5
    var bounce: Bool = false

    func body(content: Content) -> some View {
        content
            .overlay(
                GeometryReader { geometry in
                    LinearGradient(
                        gradient: Gradient(colors: [
                            .clear,
                            .white.opacity(0.4),
                            .clear
                        ]),
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                    .frame(width: geometry.size.width * 2)
                    .offset(x: phase * geometry.size.width)
                }
            )
            .mask(content)
            .onAppear {
                withAnimation(Animation.linear(duration: duration).repeatForever(autoreverses: false)) {
                    phase = 1.5
                }
            }
    }
}

extension View {
    func shimmer() -> some View {
        modifier(ShimmerEffect())
    }
}

// MARK: - Skeleton Components

struct SkeletonBlock: View {
    var width: CGFloat? = nil
    var height: CGFloat
    var cornerRadius: CGFloat = 8
    
    var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius)
            .fill(Color.gray.opacity(0.3))
            .frame(width: width, height: height)
            .shimmer()
    }
}

struct SkeletonCircle: View {
    var size: CGFloat
    
    var body: some View {
        Circle()
            .fill(Color.gray.opacity(0.3))
            .frame(width: size, height: size)
            .shimmer()
    }
}

// MARK: - Previews

#Preview {
    VStack(alignment: .leading, spacing: 16) {
        // Hero
        SkeletonBlock(height: 200, cornerRadius: 16)
        
        // Header
        HStack {
            SkeletonCircle(size: 60)
            VStack(alignment: .leading, spacing: 8) {
                SkeletonBlock(width: 150, height: 20)
                SkeletonBlock(width: 100, height: 16)
            }
        }
        
        // Content
        ForEach(0..<3) { _ in
            SkeletonBlock(height: 100, cornerRadius: 12)
        }
    }
    .padding()
}
