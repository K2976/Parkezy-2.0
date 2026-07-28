//
//  DisputeView.swift
//  ParkEzy
//
//  Report issue view with photo capture and reason picker
//

import SwiftUI
import PhotosUI

struct DisputeView: View {
    // MARK: - Properties
    
    @Binding var isPresented: Bool
    
    // MARK: - Environment
    
    @EnvironmentObject var bookingViewModel: BookingViewModel
    
    // MARK: - State
    
    @State private var selectedReason: DisputeReason = .spotUnavailable
    @State private var additionalDetails = ""
    @State private var selectedPhotos: [PhotosPickerItem] = []
    @State private var capturedImages: [UIImage] = []
    @State private var isSubmitting = false
    @State private var showSuccess = false
    @State private var showCamera = false
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignSystem.Spacing.l) {
                    // MARK: - Header
                    
                    VStack(spacing: DesignSystem.Spacing.s) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 48))
                            .foregroundColor(.orange)
                        
                        Text("Report an Issue")
                            .font(.title.bold())
                        
                        Text("We're sorry you're experiencing problems. Please describe the issue below.")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding(.bottom, DesignSystem.Spacing.m)
                    
                    // MARK: - Reason Picker
                    
                    VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
                        Text("What's the issue?")
                            .font(.headline)
                        
                        ForEach(DisputeReason.allCases, id: \.self) { reason in
                            ReasonRow(
                                reason: reason,
                                isSelected: selectedReason == reason
                            ) {
                                withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                                    selectedReason = reason
                                }
                            }
                        }
                    }
                    .padding(DesignSystem.Spacing.m)
                    .background(Color(.systemBackground))
                    .cornerRadius(DesignSystem.Spacing.m)
                    .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
                    
                    // MARK: - Photo Evidence
                    
                    VStack(alignment: .leading, spacing: DesignSystem.Spacing.m) {
                        HStack {
                            Text("Add Photo Evidence")
                                .font(.headline)
                            
                            Spacer()
                            
                            Text("Optional")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        
                        // Photo Grid
                        LazyVGrid(columns: [
                            GridItem(.flexible()),
                            GridItem(.flexible()),
                            GridItem(.flexible())
                        ], spacing: DesignSystem.Spacing.s) {
                            // Camera Button
                            Button {
                                showCamera = true
                            } label: {
                                VStack {
                                    Image(systemName: "camera.fill")
                                        .font(.title2)
                                    Text("Camera")
                                        .font(.caption2)
                                }
                                .foregroundColor(DesignSystem.Colors.primary)
                                .frame(maxWidth: .infinity)
                                .frame(height: 80)
                                .background(DesignSystem.Colors.primary.opacity(0.1))
                                .cornerRadius(DesignSystem.Spacing.s)
                            }
                            
                            // Photo Picker
                            PhotosPicker(
                                selection: $selectedPhotos,
                                maxSelectionCount: 3,
                                matching: .images
                            ) {
                                VStack {
                                    Image(systemName: "photo.on.rectangle")
                                        .font(.title2)
                                    Text("Gallery")
                                        .font(.caption2)
                                }
                                .foregroundColor(DesignSystem.Colors.primary)
                                .frame(maxWidth: .infinity)
                                .frame(height: 80)
                                .background(DesignSystem.Colors.primary.opacity(0.1))
                                .cornerRadius(DesignSystem.Spacing.s)
                            }
                            
                            // Captured Images
                            ForEach(capturedImages.indices, id: \.self) { index in
                                ZStack(alignment: .topTrailing) {
                                    Image(uiImage: capturedImages[index])
                                        .resizable()
                                        .scaledToFill()
                                        .frame(height: 80)
                                        .clipped()
                                        .cornerRadius(DesignSystem.Spacing.s)
                                    
                                    Button {
                                        capturedImages.remove(at: index)
                                    } label: {
                                        Image(systemName: "xmark.circle.fill")
                                            .foregroundColor(.white)
                                            .background(Circle().fill(Color.black.opacity(0.5)))
                                    }
                                    .padding(4)
                                }
                            }
                        }
                        
                        Text("Photos help us resolve issues faster")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(DesignSystem.Spacing.m)
                    .background(Color(.systemBackground))
                    .cornerRadius(DesignSystem.Spacing.m)
                    .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
                    
                    // MARK: - Additional Details
                    
                    VStack(alignment: .leading, spacing: DesignSystem.Spacing.s) {
                        Text("Additional Details")
                            .font(.headline)
                        
                        TextEditor(text: $additionalDetails)
                            .frame(minHeight: 100)
                            .padding(DesignSystem.Spacing.s)
                            .background(Color.gray.opacity(0.1))
                            .cornerRadius(DesignSystem.Spacing.s)
                            .overlay(
                                RoundedRectangle(cornerRadius: DesignSystem.Spacing.s)
                                    .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                            )
                        
                        Text("\(additionalDetails.count)/500")
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .frame(maxWidth: .infinity, alignment: .trailing)
                    }
                    .padding(DesignSystem.Spacing.m)
                    .background(Color(.systemBackground))
                    .cornerRadius(DesignSystem.Spacing.m)
                    .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
                    
                    // MARK: - Submit Button
                    
                    Button {
                        submitDispute()
                    } label: {
                        if isSubmitting {
                            ProgressView()
                                .tint(.white)
                        } else {
                            HStack {
                                Image(systemName: "paperplane.fill")
                                Text("Submit Report")
                            }
                        }
                    }
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(DesignSystem.Colors.primary)
                    .foregroundColor(.white)
                    .cornerRadius(DesignSystem.Spacing.m)
                    .disabled(isSubmitting)
                }
                .padding(DesignSystem.Spacing.m)
            }
            .navigationTitle("Report Issue")
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
            .alert("Report Submitted", isPresented: $showSuccess) {
                Button("OK") {
                    isPresented = false
                }
            } message: {
                Text("Thank you for reporting this issue. Our team will review it and get back to you within 24 hours.")
            }
            .sheet(isPresented: $showCamera) {
                MockCameraView { image in
                    if let image = image {
                        capturedImages.append(image)
                    }
                    showCamera = false
                }
            }
            .onChange(of: selectedPhotos) { _, items in
                Task {
                    for item in items {
                        if let data = try? await item.loadTransferable(type: Data.self),
                           let image = UIImage(data: data) {
                            capturedImages.append(image)
                        }
                    }
                    selectedPhotos = []
                }
            }
        }
        .presentationDetents([.large])
        .presentationDragIndicator(.visible)
    }
    
    // MARK: - Methods
    
    private func submitDispute() {
        isSubmitting = true
        
        // Simulate API call
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            // Create dispute report
            if let session = bookingViewModel.activeSession {
                let dispute = DisputeReport(
                    id: UUID(),
                    bookingID: session.id,
                    reason: selectedReason.rawValue,
                    description: additionalDetails,
                    photoURLs: [],
                    status: .pending,
                    createdAt: Date()
                )
                
                // In production, submit to backend
                print("Dispute submitted: \(dispute)")
            }
            
            isSubmitting = false
            showSuccess = true
            
            // Haptic feedback
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        }
    }
}

// MARK: - Dispute Reason Enum

enum DisputeReason: String, CaseIterable {
    case spotUnavailable = "Spot was not available"
    case wrongLocation = "Wrong location/address"
    case overcharged = "I was overcharged"
    case vehicleDamage = "Vehicle was damaged"
    case unsafeArea = "Area felt unsafe"
    case poorCondition = "Poor spot condition"
    case hostIssue = "Issue with host/caretaker"
    case other = "Other issue"
    
    var icon: String {
        switch self {
        case .spotUnavailable: return "nosign"
        case .wrongLocation: return "location.slash"
        case .overcharged: return "creditcard.trianglebadge.exclamationmark"
        case .vehicleDamage: return "car.side.rear.and.collision.and.car.side.front"
        case .unsafeArea: return "exclamationmark.shield"
        case .poorCondition: return "wrench.and.screwdriver"
        case .hostIssue: return "person.crop.circle.badge.exclamationmark"
        case .other: return "questionmark.circle"
        }
    }
}

// MARK: - Reason Row

struct ReasonRow: View {
    let reason: DisputeReason
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: DesignSystem.Spacing.m) {
                Image(systemName: reason.icon)
                    .font(.title3)
                    .foregroundColor(isSelected ? DesignSystem.Colors.primary : .gray)
                    .frame(width: 30)
                
                Text(reason.rawValue)
                    .font(.subheadline)
                    .foregroundColor(.primary)
                
                Spacer()
                
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(DesignSystem.Colors.primary)
                }
            }
            .padding(DesignSystem.Spacing.m)
            .background(
                RoundedRectangle(cornerRadius: DesignSystem.Spacing.s)
                    .fill(isSelected ? DesignSystem.Colors.primary.opacity(0.1) : Color.gray.opacity(0.05))
            )
            .overlay(
                RoundedRectangle(cornerRadius: DesignSystem.Spacing.s)
                    .stroke(isSelected ? DesignSystem.Colors.primary : Color.clear, lineWidth: 2)
            )
        }
    }
}

// MARK: - Mock Camera View

struct MockCameraView: View {
    let onCapture: (UIImage?) -> Void
    
    var body: some View {
        VStack(spacing: DesignSystem.Spacing.xl) {
            Spacer()
            
            // Mock Camera Preview
            ZStack {
                RoundedRectangle(cornerRadius: DesignSystem.Spacing.m)
                    .fill(Color.black)
                    .frame(height: 300)
                
                VStack(spacing: DesignSystem.Spacing.m) {
                    Image(systemName: "camera.viewfinder")
                        .font(.system(size: 60))
                        .foregroundColor(.white.opacity(0.5))
                    
                    Text("Camera Preview")
                        .foregroundColor(.white.opacity(0.5))
                    
                    Text("(Mock - Real camera requires device)")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.3))
                }
            }
            .padding()
            
            // Capture Button
            Button {
                // Return a placeholder image
                onCapture(createMockImage())
            } label: {
                Circle()
                    .fill(Color.white)
                    .frame(width: 70, height: 70)
                    .overlay(
                        Circle()
                            .stroke(Color.gray, lineWidth: 3)
                            .frame(width: 60, height: 60)
                    )
            }
            
            Spacer()
            
            // Cancel Button
            Button("Cancel") {
                onCapture(nil)
            }
            .padding()
        }
        .background(Color.black)
    }
    
    private func createMockImage() -> UIImage {
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: 200, height: 200))
        return renderer.image { context in
            UIColor.systemGray5.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 200, height: 200))
            
            UIColor.systemGray3.setFill()
            let paragraphStyle = NSMutableParagraphStyle()
            paragraphStyle.alignment = .center
            
            let attributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 14),
                .foregroundColor: UIColor.gray,
                .paragraphStyle: paragraphStyle
            ]
            
            let text = "Mock Photo"
            text.draw(in: CGRect(x: 0, y: 90, width: 200, height: 20), withAttributes: attributes)
        }
    }
}

// MARK: - Preview

#Preview {
    DisputeView(isPresented: .constant(true))
        .environmentObject(BookingViewModel())
}
