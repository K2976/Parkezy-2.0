//
//  QRCodeService.swift
//  ParkEzy
//
//  QR code generation and validation service
//

import Foundation
import UIKit
import CoreImage.CIFilterBuiltins

class QRCodeService {
    // MARK: - Singleton
    
    static let shared = QRCodeService()
    
    // MARK: - Private Properties
    
    private let context = CIContext()
    
    // MARK: - Initialization
    
    private init() {}
    
    // MARK: - QR Code Generation
    
    /// Generate QR code for a booking
    /// Format: "PARKEZY:<bookingID>:<spotID>"
    func generateQRCode(for booking: BookingSession) -> UIImage? {
        let qrString = "PARKEZY:\(booking.id.uuidString):\(booking.spotID.uuidString)"
        return generateQRImage(from: qrString)
    }
    
    /// Generate QR code from any string
    func generateQRImage(from string: String) -> UIImage? {
        let filter = CIFilter.qrCodeGenerator()
        filter.message = Data(string.utf8)
        filter.correctionLevel = "H" // High error correction
        
        guard let outputImage = filter.outputImage else { return nil }
        
        // Scale up for high resolution
        let scale: CGFloat = 10
        let scaledImage = outputImage.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
        
        guard let cgImage = context.createCGImage(scaledImage, from: scaledImage.extent) else { return nil }
        
        return UIImage(cgImage: cgImage)
    }
    
    // MARK: - QR Code Validation
    
    /// Parse QR code string and extract booking and spot IDs
    /// Expected format: "PARKEZY:<bookingID>:<spotID>"
    func parseQRCode(_ qrString: String) -> (bookingID: UUID, spotID: UUID)? {
        let components = qrString.components(separatedBy: ":")
        
        guard components.count == 3,
              components[0] == "PARKEZY",
              let bookingID = UUID(uuidString: components[1]),
              let spotID = UUID(uuidString: components[2]) else {
            print("❌ Invalid QR code format: \(qrString)")
            return nil
        }
        
        return (bookingID, spotID)
    }
    
    /// Validate if QR code belongs to a valid booking
    func validateQRCode(_ qrString: String, against bookings: [BookingSession]) -> BookingSession? {
        guard let (bookingID, _) = parseQRCode(qrString) else { return nil }
        
        return bookings.first { $0.id == bookingID }
    }
}
