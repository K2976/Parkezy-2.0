//
//  AuthenticationView.swift
//  ParkEzy
//
//  Login and signup screen with Email and Apple Sign-In.
//

import SwiftUI
import AuthenticationServices

struct AuthenticationView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    
    // MARK: - State
    
    @State private var isSignUp = false
    @State private var name = ""
    @State private var email = ""
    @State private var password = ""
    @State private var showForgotPassword = false
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignSystem.Spacing.xl) {
                    // Logo and Title
                    headerSection
                    
                    // Form Fields
                    formSection
                    
                    // Auth Buttons
                    buttonSection
                    
                    // Divider
                    dividerSection
                    
                    // Apple Sign-In
                    appleSignInButton
                    
                    // Quick Test Login (Development Only)
                    #if DEBUG
                    testLoginButton
                    #endif
                    
                    // Toggle Sign Up / Sign In
                    toggleSection
                }
                .padding(DesignSystem.Spacing.l)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle(isSignUp ? "Create Account" : "Welcome Back")
            .navigationBarTitleDisplayMode(.large)
            .alert("Error", isPresented: $authViewModel.showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(authViewModel.errorMessage ?? "An error occurred")
            }
            .sheet(isPresented: $showForgotPassword) {
                ForgotPasswordSheet(email: email, authViewModel: authViewModel)
            }
            .disabled(authViewModel.isLoading)
        }
    }
    
    // MARK: - Header
    
    private var headerSection: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            // App Icon
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [DesignSystem.Colors.primary, DesignSystem.Colors.primary.opacity(0.7)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 100, height: 100)
                
                Image(systemName: "parkingsign.circle.fill")
                    .font(.system(size: 50))
                    .foregroundColor(.white)
            }
            
            Text("ParkEzy")
                .font(.largeTitle.bold())
                .foregroundColor(DesignSystem.Colors.primary)
            
            Text(isSignUp ? "Create your account to get started" : "Sign in to continue")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .padding(.top, DesignSystem.Spacing.xl)
    }
    
    // MARK: - Form
    
    private var formSection: some View {
        VStack(spacing: DesignSystem.Spacing.m) {
            // Name field (sign up only)
            if isSignUp {
                HStack {
                    Image(systemName: "person.fill")
                        .foregroundColor(.gray)
                    TextField("Full Name", text: $name)
                        .textContentType(.name)
                        .autocapitalization(.words)
                }
                .padding()
                .background(Color(.systemBackground))
                .cornerRadius(DesignSystem.Spacing.s)
            }
            
            // Email field
            HStack {
                Image(systemName: "envelope.fill")
                    .foregroundColor(.gray)
                TextField("Email", text: $email)
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .autocapitalization(.none)
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(DesignSystem.Spacing.s)
            
            // Password field
            HStack {
                Image(systemName: "lock.fill")
                    .foregroundColor(.gray)
                SecureField("Password", text: $password)
                    .textContentType(isSignUp ? .newPassword : .password)
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(DesignSystem.Spacing.s)
            
            // Forgot password (sign in only)
            if !isSignUp {
                HStack {
                    Spacer()
                    Button("Forgot Password?") {
                        showForgotPassword = true
                    }
                    .font(.footnote)
                    .foregroundColor(DesignSystem.Colors.primary)
                }
            }
        }
    }
    
    // MARK: - Buttons
    
    private var buttonSection: some View {
        Button {
            Task {
                if isSignUp {
                    await authViewModel.signUp(email: email, password: password, name: name)
                } else {
                    await authViewModel.signIn(email: email, password: password)
                }
            }
        } label: {
            if authViewModel.isLoading {
                ProgressView()
                    .tint(.white)
            } else {
                Text(isSignUp ? "Create Account" : "Sign In")
                    .font(.headline)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(DesignSystem.Colors.primary)
        .foregroundColor(.white)
        .cornerRadius(DesignSystem.Spacing.m)
        .disabled(!isFormValid)
        .opacity(isFormValid ? 1 : 0.6)
    }
    
    // MARK: - Divider
    
    private var dividerSection: some View {
        HStack {
            Rectangle()
                .fill(Color.gray.opacity(0.3))
                .frame(height: 1)
            
            Text("or")
                .font(.footnote)
                .foregroundColor(.secondary)
            
            Rectangle()
                .fill(Color.gray.opacity(0.3))
                .frame(height: 1)
        }
    }
    
    // MARK: - Apple Sign-In
    
    private var appleSignInButton: some View {
        SignInWithAppleButton(
            .signIn,
            onRequest: { request in
                request.requestedScopes = [.fullName, .email]
                request.nonce = authViewModel.generateAppleNonce()
            },
            onCompletion: { result in
                Task {
                    await authViewModel.handleAppleSignIn(result)
                }
            }
        )
        .signInWithAppleButtonStyle(.black)
        .frame(height: 50)
        .cornerRadius(DesignSystem.Spacing.m)
    }
    
    // MARK: - Toggle
    
    private var toggleSection: some View {
        HStack {
            Text(isSignUp ? "Already have an account?" : "Don't have an account?")
                .foregroundColor(.secondary)
            
            Button(isSignUp ? "Sign In" : "Sign Up") {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    isSignUp.toggle()
                    // Clear fields when switching
                    name = ""
                    password = ""
                }
            }
            .foregroundColor(DesignSystem.Colors.primary)
            .fontWeight(.semibold)
        }
        .font(.footnote)
    }
    
    // MARK: - Test Login (Development)
    
    private var testLoginButton: some View {
        Button {
            email = "test@parkezy.com"
            password = "test123"
            Task {
                await authViewModel.signIn(email: email, password: password)
            }
        } label: {
            HStack {
                Image(systemName: "hammer.fill")
                Text("Quick Test Login")
            }
            .font(.footnote)
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.orange.opacity(0.2))
            .foregroundColor(.orange)
            .cornerRadius(DesignSystem.Spacing.m)
            .overlay(
                RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
                    .stroke(Color.orange, lineWidth: 1)
            )
        }
    }
    
    // MARK: - Validation
    
    private var isFormValid: Bool {
        let emailValid = email.contains("@") && email.contains(".")
        let passwordValid = password.count >= 6
        let nameValid = !isSignUp || name.count >= 2
        
        return emailValid && passwordValid && nameValid
    }
}

// MARK: - Forgot Password Sheet

struct ForgotPasswordSheet: View {
    @State var email: String
    @ObservedObject var authViewModel: AuthViewModel
    @Environment(\.dismiss) var dismiss
    @State private var sent = false
    
    var body: some View {
        NavigationStack {
            VStack(spacing: DesignSystem.Spacing.l) {
                if sent {
                    // Success state
                    Image(systemName: "envelope.badge.fill")
                        .font(.system(size: 60))
                        .foregroundColor(DesignSystem.Colors.success)
                    
                    Text("Email Sent!")
                        .font(.title2.bold())
                    
                    Text("Check your inbox for password reset instructions")
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    
                    Button("Done") {
                        dismiss()
                    }
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(DesignSystem.Colors.primary)
                    .foregroundColor(.white)
                    .cornerRadius(DesignSystem.Spacing.m)
                    
                } else {
                    // Input state
                    Text("Enter your email and we'll send you a link to reset your password")
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                        .padding()
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(DesignSystem.Spacing.s)
                    
                    Button {
                        Task {
                            await authViewModel.sendPasswordReset(email: email)
                            sent = true
                        }
                    } label: {
                        if authViewModel.isLoading {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text("Send Reset Link")
                                .font(.headline)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(DesignSystem.Colors.primary)
                    .foregroundColor(.white)
                    .cornerRadius(DesignSystem.Spacing.m)
                    .disabled(email.isEmpty)
                }
                
                Spacer()
            }
            .padding(DesignSystem.Spacing.l)
            .navigationTitle("Reset Password")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }
}

// MARK: - Preview

#Preview {
    AuthenticationView()
        .environmentObject(AuthViewModel())
}
