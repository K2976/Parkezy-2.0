//
//  PINEntryView.swift
//  ParkEzy
//
//  6-digit PIN verification for private parking spots
//

import SwiftUI

struct PINEntryView: View {
    // MARK: - Properties
    
    let spot: ParkingSpot
    let booking: BookingSession
    @Binding var isPresented: Bool
    let onComplete: () -> Void
    
    // MARK: - Environment
    
    @EnvironmentObject var bookingViewModel: BookingViewModel
    
    // MARK: - State
    
    @State private var enteredPIN: String = ""
    @State private var isVerifying = false
    @State private var verificationSuccess = false
    @State private var showError = false
    @State private var attempts = 0
    
    private let pinLength = 6
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            VStack(spacing: DesignSystem.Spacing.xl) {
                Spacer()
                
                // MARK: - Header
                
                VStack(spacing: DesignSystem.Spacing.m) {
                    ZStack {
                        Circle()
                            .fill(DesignSystem.Colors.primary.opacity(0.1))
                            .frame(width: 100, height: 100)
                        
                        Image(systemName: verificationSuccess ? "checkmark.circle.fill" : "key.fill")
                            .font(.system(size: 48))
                            .foregroundColor(verificationSuccess ? DesignSystem.Colors.success : DesignSystem.Colors.primary)
                    }
                    
                    Text(verificationSuccess ? "Access Granted!" : "Enter Access PIN")
                        .font(.title.bold())
                    
                    Text(verificationSuccess ? "Your parking session has started" : "Enter the 6-digit PIN to start your session")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                
                // MARK: - PIN Display
                
                if !verificationSuccess {
                    HStack(spacing: DesignSystem.Spacing.m) {
                        ForEach(0..<pinLength, id: \.self) { index in
                            PINDigitView(
                                digit: digitAt(index),
                                isFilled: index < enteredPIN.count,
                                isError: showError
                            )
                        }
                    }
                    .shake(showError)
                }
                
                // MARK: - Error Message
                
                if showError {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                        Text("Incorrect PIN. \(3 - attempts) attempts remaining.")
                    }
                    .font(.subheadline)
                    .foregroundColor(DesignSystem.Colors.error)
                    .transition(.opacity.combined(with: .move(edge: .top)))
                }
                
                // MARK: - Hint Card
                
                if !verificationSuccess {
                    VStack(spacing: DesignSystem.Spacing.s) {
                        HStack {
                            Image(systemName: "info.circle.fill")
                                .foregroundColor(DesignSystem.Colors.primary)
                            Text("Demo PIN: \(booking.accessCode ?? "428915")")
                                .font(.subheadline)
                        }
                        Text("In production, the PIN is sent via SMS to the host")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(DesignSystem.Spacing.m)
                    .background(DesignSystem.Colors.primary.opacity(0.05))
                    .cornerRadius(DesignSystem.Spacing.s)
                }
                
                Spacer()
                
                // MARK: - Keypad
                
                if !verificationSuccess {
                    numericKeypad
                }
                
                // MARK: - Continue Button (after success)
                
                if verificationSuccess {
                    Button {
                        isPresented = false
                        onComplete()
                    } label: {
                        HStack {
                            Image(systemName: "car.fill")
                            Text("Start Parking")
                                .font(.headline)
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(DesignSystem.Colors.success)
                        .foregroundColor(.white)
                        .cornerRadius(DesignSystem.Spacing.m)
                    }
                    .padding(.horizontal, DesignSystem.Spacing.l)
                }
            }
            .padding(DesignSystem.Spacing.m)
            .navigationTitle("Verify Access")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        isPresented = false
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.gray)
                    }
                }
            }
        }
        .presentationDetents([.large])
        .presentationDragIndicator(.visible)
        .interactiveDismissDisabled(verificationSuccess)
    }
    
    // MARK: - Numeric Keypad
    
    private var numericKeypad: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            ForEach(0..<3) { row in
                HStack(spacing: DesignSystem.Spacing.m) {
                    ForEach(1...3, id: \.self) { col in
                        let number = row * 3 + col
                        KeypadButton(title: "\(number)") {
                            appendDigit("\(number)")
                        }
                    }
                }
            }
            
            HStack(spacing: DesignSystem.Spacing.m) {
                // Empty space
                Color.clear
                    .frame(width: 80, height: 60)
                
                KeypadButton(title: "0") {
                    appendDigit("0")
                }
                
                KeypadButton(title: "⌫", isDestructive: true) {
                    deleteDigit()
                }
            }
        }
        .padding(.bottom, DesignSystem.Spacing.l)
    }
    
    // MARK: - Methods
    
    private func digitAt(_ index: Int) -> String {
        guard index < enteredPIN.count else { return "" }
        let stringIndex = enteredPIN.index(enteredPIN.startIndex, offsetBy: index)
        return String(enteredPIN[stringIndex])
    }
    
    private func appendDigit(_ digit: String) {
        guard enteredPIN.count < pinLength else { return }
        
        withAnimation(.spring(response: 0.2, dampingFraction: 0.6)) {
            enteredPIN += digit
            showError = false
        }
        
        // Haptic feedback
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
        
        // Auto-verify when complete
        if enteredPIN.count == pinLength {
            verifyPIN()
        }
    }
    
    private func deleteDigit() {
        guard !enteredPIN.isEmpty else { return }
        
        withAnimation(.spring(response: 0.2, dampingFraction: 0.6)) {
            enteredPIN.removeLast()
            showError = false
        }
        
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
    }
    
    private func verifyPIN() {
        isVerifying = true
        
        // Simulate verification delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            let correctPIN = booking.accessCode ?? "428915"
            
            if enteredPIN == correctPIN {
                // Success
                withAnimation(.spring(response: 0.4, dampingFraction: 0.6)) {
                    verificationSuccess = true
                }
                
                // Start the session
                bookingViewModel.startSession()
                
                // Haptic feedback
                UINotificationFeedbackGenerator().notificationOccurred(.success)
            } else {
                // Failure
                attempts += 1
                
                withAnimation(.spring(response: 0.3, dampingFraction: 0.5)) {
                    showError = true
                    enteredPIN = ""
                }
                
                // Haptic feedback
                UINotificationFeedbackGenerator().notificationOccurred(.error)
                
                // Lock after 3 attempts
                if attempts >= 3 {
                    // In production, lock the booking
                }
            }
            
            isVerifying = false
        }
    }
}

// MARK: - PIN Digit View

struct PINDigitView: View {
    let digit: String
    let isFilled: Bool
    let isError: Bool
    
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: DesignSystem.Spacing.s)
                .stroke(
                    isError ? DesignSystem.Colors.error : (isFilled ? DesignSystem.Colors.primary : Color.gray.opacity(0.3)),
                    lineWidth: 2
                )
                .frame(width: 45, height: 55)
                .background(
                    RoundedRectangle(cornerRadius: DesignSystem.Spacing.s)
                        .fill(isFilled ? DesignSystem.Colors.primary.opacity(0.05) : Color.clear)
                )
            
            if isFilled {
                Circle()
                    .fill(DesignSystem.Colors.primary)
                    .frame(width: 12, height: 12)
                    .transition(.scale.combined(with: .opacity))
            }
        }
        .animation(.spring(response: 0.2, dampingFraction: 0.6), value: isFilled)
    }
}

// MARK: - Keypad Button

struct KeypadButton: View {
    let title: String
    var isDestructive: Bool = false
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.title)
                .frame(width: 80, height: 60)
                .background(isDestructive ? Color.gray.opacity(0.1) : Color.gray.opacity(0.1))
                .foregroundColor(isDestructive ? DesignSystem.Colors.error : .primary)
                .cornerRadius(DesignSystem.Spacing.s)
        }
    }
}

// MARK: - Shake Effect

struct ShakeEffect: GeometryEffect {
    var amount: CGFloat = 10
    var shakesPerUnit = 3
    var animatableData: CGFloat
    
    func effectValue(size: CGSize) -> ProjectionTransform {
        ProjectionTransform(CGAffineTransform(translationX:
            amount * sin(animatableData * .pi * CGFloat(shakesPerUnit)),
            y: 0))
    }
}

extension View {
    func shake(_ trigger: Bool) -> some View {
        modifier(ShakeModifier(trigger: trigger))
    }
}

struct ShakeModifier: ViewModifier {
    let trigger: Bool
    @State private var shake: CGFloat = 0
    
    func body(content: Content) -> some View {
        content
            .modifier(ShakeEffect(animatableData: shake))
            .onChange(of: trigger) { _, newValue in
                if newValue {
                    withAnimation(.default) {
                        shake = 1
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                        shake = 0
                    }
                }
            }
    }
}

// MARK: - Preview

#Preview {
    PINEntryView(
        spot: ParkingSpot.mockSpot,
        booking: BookingSession.mockSession,
        isPresented: .constant(true),
        onComplete: {}
    )
    .environmentObject(BookingViewModel())
}
