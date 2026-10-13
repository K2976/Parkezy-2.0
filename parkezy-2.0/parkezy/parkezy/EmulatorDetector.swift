//
//  EmulatorDetector.swift
//  ParkEzy
//
//  Utility to detect if running on iOS Simulator for demo purposes
//

import Foundation

struct EmulatorDetector {
    /// Returns true if running on iOS Simulator
    static var isSimulator: Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }
    
    /// Returns true if running on physical device
    static var isDevice: Bool {
        !isSimulator
    }
}
