//
//  AuthViewModel.swift
//  ParkEzy
//
//  ViewModel for authentication state and user management.
//  Views use this to check auth state and trigger login/logout.
//

import SwiftUI
import FirebaseAuth
import AuthenticationServices
import Combine

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
    
    // MARK: - Dependencies
    
    private let authRepo = AuthRepository.shared
    private let userRepo = UserRepository.shared
    private let firebase = FirebaseManager.shared
    
    private var authStateListener: AuthStateDidChangeListenerHandle?
    private var userListener: AnyCancellable?
    
    // MARK: - Initialization
    
    init() {
        setupAuthStateListener()
    }
    
    deinit {
        if let handle = authStateListener {
            firebase.auth.removeStateDidChangeListener(handle)
        }
    }
    
    // MARK: - Auth State Listener
    
    /// Listen to auth state changes (login/logout)
    private func setupAuthStateListener() {
        authStateListener = firebase.auth.addStateDidChangeListener { [weak self] _, user in
            Task { @MainActor in
                self?.isAuthenticated = user != nil
                
                if let userID = user?.uid {
                    await self?.loadCurrentUser(id: userID)
                } else {
                    self?.currentUser = nil
                }
            }
        }
    }
    
    /// Load current user profile
    private func loadCurrentUser(id: String) async {
        do {
            currentUser = try await userRepo.getUser(id: id)
        } catch {
            // User might not have a profile yet, create one
            print("Could not load user: \(error.localizedDescription)")
        }
    }
    
    // MARK: - Email Authentication
    
    /// Sign up with email and password
    func signUp(email: String, password: String, name: String) async {
        isLoading = true
        errorMessage = nil
        
        do {
            let userID = try await authRepo.signUp(email: email, password: password, name: name)
            await loadCurrentUser(id: userID)
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
            let userID = try await authRepo.signIn(email: email, password: password)
            await loadCurrentUser(id: userID)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        
        isLoading = false
    }
    
    /// Sign out
    func signOut() {
        do {
            try authRepo.signOut()
            currentUser = nil
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
    
    /// Send password reset email
    func sendPasswordReset(email: String) async {
        isLoading = true
        
        do {
            try await authRepo.sendPasswordReset(email: email)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        
        isLoading = false
    }
    
    // MARK: - Apple Sign-In
    
    /// Generate nonce for Apple Sign-In
    func generateAppleNonce() -> String {
        authRepo.generateNonce()
    }
    
    /// Handle Apple Sign-In authorization
    func handleAppleSignIn(_ result: Result<ASAuthorization, Error>) async {
        isLoading = true
        errorMessage = nil
        
        switch result {
        case .success(let authorization):
            do {
                let userID = try await authRepo.handleAppleSignIn(authorization: authorization)
                await loadCurrentUser(id: userID)
            } catch {
                errorMessage = error.localizedDescription
                showError = true
            }
            
        case .failure(let error):
            // User cancelled or error occurred
            if (error as NSError).code != ASAuthorizationError.canceled.rawValue {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
        
        isLoading = false
    }
    
    // MARK: - User Updates
    
    /// Enable private hosting capability
    func enablePrivateHosting() async {
        guard let userID = firebase.currentUserID else { return }
        
        do {
            try await userRepo.enableCapability(.canHostPrivate, for: userID)
            currentUser?.capabilities.canHostPrivate = true
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
    
    /// Enable commercial hosting capability
    func enableCommercialHosting() async {
        guard let userID = firebase.currentUserID else { return }
        
        do {
            try await userRepo.enableCapability(.canHostCommercial, for: userID)
            currentUser?.capabilities.canHostCommercial = true
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
    
    /// Update user profile
    func updateProfile(name: String, phone: String) async {
        guard var user = currentUser else { return }
        
        user.name = name
        user.phoneNumber = phone
        
        do {
            try await userRepo.updateUser(user)
            currentUser = user
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}
