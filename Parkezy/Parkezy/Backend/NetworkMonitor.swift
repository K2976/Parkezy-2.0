//
//  NetworkMonitor.swift
//  ParkEzy
//
//  Monitors network connectivity using NWPathMonitor.
//  Published properties drive UI banners and offline states.
//

import Foundation
import Network
import Combine

@MainActor
final class NetworkMonitor: ObservableObject {
    // MARK: - Singleton
    
    static let shared = NetworkMonitor()
    
    // MARK: - Published State
    
    /// `true` when the device has a usable network path.
    @Published private(set) var isConnected: Bool = true
    
    /// Human-readable description of the current connection type.
    @Published private(set) var connectionType: ConnectionType = .unknown
    
    // MARK: - Types
    
    enum ConnectionType: String {
        case wifi = "Wi-Fi"
        case cellular = "Cellular"
        case wiredEthernet = "Ethernet"
        case unknown = "Unknown"
    }
    
    // MARK: - Private
    
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "com.parkezy.networkMonitor")
    
    // MARK: - Init
    
    private init() {
        startMonitoring()
    }
    
    deinit {
        monitor.cancel()
    }
    
    // MARK: - Monitoring
    
    private func startMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in
                self?.isConnected = (path.status == .satisfied)
                self?.connectionType = self?.mapConnectionType(path) ?? .unknown
            }
        }
        monitor.start(queue: monitorQueue)
    }
    
    private func mapConnectionType(_ path: NWPath) -> ConnectionType {
        if path.usesInterfaceType(.wifi) {
            return .wifi
        } else if path.usesInterfaceType(.cellular) {
            return .cellular
        } else if path.usesInterfaceType(.wiredEthernet) {
            return .wiredEthernet
        }
        return .unknown
    }
}
