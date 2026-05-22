//
//  AuthViewModel.swift
//  ParkEzy
//
//  ViewModel for authentication state and user management.
//  Views use this to check auth state and trigger login/logout.
//  Powered by Supabase Auth.
//

import SwiftUI
import AuthenticationServices
import Combine
import Supabase
import CryptoKit

/// Main view model for authentication
@MainActor
final class AuthViewModel: ObservableObject {
    
    // MARK: - Published Properties
    
    /// Whether user is authenticated
    @Published var isAuthenticated = false
    
    /// Current user profile (nil if not logged in)
    @Published var currentUser: AppUser?
    
    /// Loading state during auth operations
    @Published var isLoading = false
    
    /// Error message to display
    @Published var errorMessage: String?
    
    /// Show error alert
    @Published var showError = false
    
    /// Session expired flag — observed by views to force redirect
    @Published var sessionExpired = false
    
    // MARK: - Private Properties
    
    private let client = SupabaseConfig.client
    
    /// Stored nonce for Apple Sign-In verification
    private var currentNonce: String?
    
    // MARK: - Initialization
    
    init() {
        // Session will be restored via restoreSession() called from ParkezyApp
        NotificationCenter.default.addObserver(forName: SupabaseService.sessionExpiredNotification, object: nil, queue: .main) { [weak self] _ in
            self?.handleSessionExpired()
        }
    }
    
    // MARK: - Session Management
    
    /// Restore existing Supabase session on app launch
    func restoreSession() async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            let session = try await client.auth.session
            isAuthenticated = true
            await loadUserProfile(id: session.user.id.uuidString)
        } catch {
            // No valid session — user needs to log in
            isAuthenticated = false
            currentUser = nil
        }
    }
    
    // MARK: - Email Authentication
    
    /// Sign up with email and password
    func signUp(email: String, password: String, name: String) async {
        isLoading = true
        errorMessage = nil
        
        do {
            let response = try await client.auth.signUp(
                email: email,
                password: password,
                data: [
                    "name": .string(name),
                    "phone_number": .string("")
                ]
            )
            
            // Profile row is auto-created by the DB trigger.
            // Fetch the profile to populate currentUser.
            isAuthenticated = true
            await loadUserProfile(id: response.user.id.uuidString)
            
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        
        isLoading = false
    }
    
    /// Sign in with email and password
    func signIn(email: String, password: String) async {
        isLoading = true
        errorMessage = nil
        
        do {
            let session = try await client.auth.signIn(
                email: email,
                password: password
            )
            
            isAuthenticated = true
            await loadUserProfile(id: session.user.id.uuidString)
            
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        
        isLoading = false
    }
    
    /// Sign out
    func signOut() {
        isLoading = true
        
        Task {
            do {
                try await client.auth.signOut()
            } catch {
                print("Sign out error: \(error.localizedDescription)")
            }
            
            isAuthenticated = false
            currentUser = nil
            sessionExpired = false
            isLoading = false
        }
    }
    
    /// Delete user account
    func deleteAccount() async {
        isLoading = true
        errorMessage = nil
        
        do {
            // Wait, we need to try to delete the auth user or the profile.
            // For now, we'll try to delete the profile, which could trigger auth user deletion if set up that way,
            // or call an RPC. The exact method depends on the backend.
            if let user = currentUser {
                try await client.database.from("profiles").delete().eq("id", value: user.id.uuidString).execute()
            }
            try await client.auth.signOut()
            
            isAuthenticated = false
            currentUser = nil
            sessionExpired = false
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        
        isLoading = false
    }
    
    /// Send password reset email
    func sendPasswordReset(email: String) async {
        isLoading = true
        
        do {
            try await client.auth.resetPasswordForEmail(email)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        
        isLoading = false
    }
    
    // MARK: - Apple Sign-In
    
    /// Generate a cryptographic nonce for Apple Sign-In
    func generateAppleNonce() -> String {
        let nonce = randomNonceString()
        currentNonce = nonce
        return sha256(nonce)
    }
    
    /// Handle Apple Sign-In authorization result
    func handleAppleSignIn(_ result: Result<ASAuthorization, Error>) async {
        isLoading = true
        errorMessage = nil
        
        switch result {
        case .success(let authorization):
            guard let appleIDCredential = authorization.credential as? ASAuthorizationAppleIDCredential,
                  let identityTokenData = appleIDCredential.identityToken,
                  let idToken = String(data: identityTokenData, encoding: .utf8),
                  let nonce = currentNonce else {
                errorMessage = "Apple Sign-In failed: missing credential data"
                showError = true
                isLoading = false
                return
            }
            
            do {
                let session = try await client.auth.signInWithIdToken(
                    credentials: .init(
                        provider: .apple,
                        idToken: idToken,
                        nonce: nonce
                    )
                )
                
                isAuthenticated = true
                await loadUserProfile(id: session.user.id.uuidString)
                
            } catch {
                errorMessage = error.localizedDescription
                showError = true
            }
            
        case .failure(let error):
            // Don't show error if user cancelled
            if (error as NSError).code != ASAuthorizationError.canceled.rawValue {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
        
        isLoading = false
    }
    
    // MARK: - User Profile Updates
    
    /// Enable private hosting capability
    func enablePrivateHosting() async {
        guard var user = currentUser else { return }
        user.capabilities.canHostPrivate = true
        let success = await SupabaseService.shared.updateUserProfile(user)
        if success { currentUser = user }
    }
    
    /// Enable commercial hosting capability
    func enableCommercialHosting() async {
        guard var user = currentUser else { return }
        user.capabilities.canHostCommercial = true
        let success = await SupabaseService.shared.updateUserProfile(user)
        if success { currentUser = user }
    }
    
    /// Update user profile
    func updateProfile(name: String, phone: String) async {
        guard var user = currentUser else { return }
        user.name = name
        user.phoneNumber = phone
        let success = await SupabaseService.shared.updateUserProfile(user)
        if success { currentUser = user }
    }
    
    // MARK: - Session Expiry (called by SupabaseService on auth errors)
    
    /// Called when an API call fails due to expired/invalid session
    func handleSessionExpired() {
        isAuthenticated = false
        currentUser = nil
        sessionExpired = true
        errorMessage = "Session expired, please log in again"
        showError = true
    }
    
    // MARK: - Private Helpers
    
    /// Load user profile from the profiles table
    private func loadUserProfile(id: String) async {
        currentUser = await SupabaseService.shared.getUserProfile(id: id)
    }
    
    /// Generate a random nonce string
    private func randomNonceString(length: Int = 32) -> String {
        precondition(length > 0)
        var randomBytes = [UInt8](repeating: 0, count: length)
        let errorCode = SecRandomCopyBytes(kSecRandomDefault, randomBytes.count, &randomBytes)
        guard errorCode == errSecSuccess else {
            // Fallback to arc4random if SecRandom fails
            return (0..<length).map { _ in
                String(format: "%02x", arc4random_uniform(256))
            }.joined()
        }
        let charset: [Character] = Array("0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._")
        return String(randomBytes.map { charset[Int($0) % charset.count] })
    }
    
    /// SHA256 hash of a string
    private func sha256(_ input: String) -> String {
        let inputData = Data(input.utf8)
        let hashedData = SHA256.hash(data: inputData)
        return hashedData.compactMap { String(format: "%02x", $0) }.joined()
    }
}
