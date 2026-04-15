//
//  AuthRepository.swift
//  ParkEzy
//
//  Handles user authentication with Email and Apple Sign-In.
//  Views should use this repository, not Firebase directly.
//

import Foundation
import Combine
import FirebaseAuth
import FirebaseFirestore
import AuthenticationServices
import CryptoKit

/// Errors that can occur during authentication
enum AuthError: LocalizedError {
    case notAuthenticated
    case emailAlreadyInUse
    case weakPassword
    case invalidEmail
    case wrongPassword
    case userNotFound
    case unknown(String)
    
    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "You must be logged in to perform this action"
        case .emailAlreadyInUse:
            return "This email is already registered"
        case .weakPassword:
            return "Password must be at least 6 characters"
        case .invalidEmail:
            return "Please enter a valid email address"
        case .wrongPassword:
            return "Incorrect password"
        case .userNotFound:
            return "No account found with this email"
        case .unknown(let message):
            return message
        }
    }
}

/// Repository for handling authentication
final class AuthRepository: ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = AuthRepository()
    
    // MARK: - Properties
    
    private let firebase = FirebaseManager.shared
    
    // For Apple Sign-In
    private var currentNonce: String?
    
    // MARK: - Initialization
    
    private init() {}
    
    // MARK: - Email Authentication
    
    /// Sign up with email and password
    /// - Parameters:
    ///   - email: User's email address
    ///   - password: Password (minimum 6 characters)
    ///   - name: User's display name
    /// - Returns: The created user's ID
    func signUp(email: String, password: String, name: String) async throws -> String {
        do {
            // Create the Firebase Auth account
            let result = try await firebase.auth.createUser(withEmail: email, password: password)
            let userID = result.user.uid
            
            // Update display name
            let changeRequest = result.user.createProfileChangeRequest()
            changeRequest.displayName = name
            try await changeRequest.commitChanges()
            
            // Create user document in Firestore
            try await createUserDocument(
                id: userID,
                email: email,
                name: name
            )
            
            return userID
        } catch let error as NSError {
            throw mapAuthError(error)
        }
    }
    
    /// Sign in with email and password
    /// - Parameters:
    ///   - email: User's email address
    ///   - password: User's password
    /// - Returns: The signed-in user's ID
    func signIn(email: String, password: String) async throws -> String {
        do {
            let result = try await firebase.auth.signIn(withEmail: email, password: password)
            return result.user.uid
        } catch let error as NSError {
            throw mapAuthError(error)
        }
    }
    
    /// Sign out the current user
    func signOut() throws {
        try firebase.auth.signOut()
    }
    
    /// Send password reset email
    func sendPasswordReset(email: String) async throws {
        try await firebase.auth.sendPasswordReset(withEmail: email)
    }
    
    // MARK: - Apple Sign-In
    
    /// Generate a random nonce for Apple Sign-In security
    func generateNonce() -> String {
        let nonce = randomNonceString()
        currentNonce = nonce
        return sha256(nonce)
    }
    
    /// Handle Apple Sign-In authorization result
    /// - Parameter authorization: The ASAuthorization from Apple
    /// - Returns: The signed-in user's ID
    func handleAppleSignIn(authorization: ASAuthorization) async throws -> String {
        guard let appleIDCredential = authorization.credential as? ASAuthorizationAppleIDCredential,
              let nonce = currentNonce,
              let appleIDToken = appleIDCredential.identityToken,
              let idTokenString = String(data: appleIDToken, encoding: .utf8) else {
            throw AuthError.unknown("Failed to get Apple ID credentials")
        }
        
        // Create Firebase credential with Apple ID token
        let credential = OAuthProvider.appleCredential(
            withIDToken: idTokenString,
            rawNonce: nonce,
            fullName: appleIDCredential.fullName
        )
        
        // Sign in to Firebase with the Apple credential
        let result = try await firebase.auth.signIn(with: credential)
        let userID = result.user.uid
        
        // Get name from Apple (only provided on first sign-in)
        let name = [
            appleIDCredential.fullName?.givenName,
            appleIDCredential.fullName?.familyName
        ].compactMap { $0 }.joined(separator: " ")
        
        // Create or update user document
        let userExists = try await checkUserExists(id: userID)
        if !userExists {
            try await createUserDocument(
                id: userID,
                email: appleIDCredential.email ?? result.user.email ?? "",
                name: name.isEmpty ? "User" : name
            )
        }
        
        currentNonce = nil
        return userID
    }
    
    // MARK: - User Document
    
    /// Create a new user document in Firestore
    private func createUserDocument(id: String, email: String, name: String) async throws {
        let userData: [String: Any] = [
            "id": id,
            "email": email,
            "name": name,
            "phoneNumber": "",
            "profileImageURL": NSNull(),
            "createdAt": FieldValue.serverTimestamp(),
            "capabilities": [
                "canDrive": true,
                "canHostPrivate": false,
                "canHostCommercial": false
            ],
            "stats": [
                "totalBookingsAsDriver": 0,
                "hostRating": NSNull(),
                "totalEarnings": 0.0
            ]
        ]
        
        try await firebase.userDocument(id: id).setData(userData)
    }
    
    /// Check if a user document exists
    private func checkUserExists(id: String) async throws -> Bool {
        let doc = try await firebase.userDocument(id: id).getDocument()
        return doc.exists
    }
    
    // MARK: - Helper Functions
    
    /// Map Firebase Auth errors to our custom AuthError
    private func mapAuthError(_ error: NSError) -> AuthError {
        let code = AuthErrorCode(rawValue: error.code)
        switch code {
        case .emailAlreadyInUse:
            return .emailAlreadyInUse
        case .weakPassword:
            return .weakPassword
        case .invalidEmail:
            return .invalidEmail
        case .wrongPassword:
            return .wrongPassword
        case .userNotFound:
            return .userNotFound
        default:
            return .unknown(error.localizedDescription)
        }
    }
    
    /// Generate a random string for nonce
    private func randomNonceString(length: Int = 32) -> String {
        precondition(length > 0)
        var randomBytes = [UInt8](repeating: 0, count: length)
        let errorCode = SecRandomCopyBytes(kSecRandomDefault, randomBytes.count, &randomBytes)
        if errorCode != errSecSuccess {
            fatalError("Unable to generate nonce")
        }
        
        let charset: [Character] = Array("0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._")
        let nonce = randomBytes.map { byte in
            charset[Int(byte) % charset.count]
        }
        return String(nonce)
    }
    
    /// SHA256 hash of the input string
    private func sha256(_ input: String) -> String {
        let inputData = Data(input.utf8)
        let hashedData = SHA256.hash(data: inputData)
        return hashedData.compactMap { String(format: "%02x", $0) }.joined()
    }
}
