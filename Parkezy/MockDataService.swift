//
//  MockDataService.swift
//  ParkEzy
//
//  Provides mock data for 10 Delhi NCR parking locations
//

import Foundation
import CoreLocation

class MockDataService {
    // MARK: - Singleton
    
    static let shared = MockDataService()
    
    // MARK: - Properties
    
    var parkingSpots: [ParkingSpot] = []
    
    // MARK: - Initialization
    
    private init() {
        generateMockSpots()
    }
    
    // MARK: - Mock Data Generation
    
    private func generateMockSpots() {
        parkingSpots = [
            // Mall Parking
            ParkingSpot(
                id: UUID(),
                address: "Select Citywalk, Saket",
                coordinates: CLLocationCoordinate2D(latitude: 28.5285, longitude: 77.2182),
                type: .mall,
                pricePerHour: 60,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.7,
                reviewCount: 342
            ),
            ParkingSpot(
                id: UUID(),
                address: "DLF Promenade, Vasant Kunj",
                coordinates: CLLocationCoordinate2D(latitude: 28.5398, longitude: 77.1546),
                type: .mall,
                pricePerHour: 80,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.8,
                reviewCount: 521
            ),
            ParkingSpot(
                id: UUID(),
                address: "Ambience Mall, Gurugram",
                coordinates: CLLocationCoordinate2D(latitude: 28.5040, longitude: 77.0968),
                type: .mall,
                pricePerHour: 100,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: true,
                rating: 4.6,
                reviewCount: 687
            ),
            ParkingSpot(
                id: UUID(),
                address: "Palika Bazaar, Connaught Place",
                coordinates: CLLocationCoordinate2D(latitude: 28.6304, longitude: 77.2177),
                type: .mall,
                pricePerHour: 40,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: false,
                hasInsurance: false,
                isOccupied: false,
                rating: 3.9,
                reviewCount: 156
            ),
            
            // Private Driveways
            ParkingSpot(
                id: UUID(),
                address: "Greater Kailash I, Block M",
                coordinates: CLLocationCoordinate2D(latitude: 28.5494, longitude: 77.2344),
                type: .privateDriveway,
                pricePerHour: 50,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.5,
                reviewCount: 89,
                accessPIN: "428915"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Defence Colony, A Block",
                coordinates: CLLocationCoordinate2D(latitude: 28.5742, longitude: 77.2310),
                type: .privateDriveway,
                pricePerHour: 45,
                hasCCTV: true,
                isCovered: false,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.3,
                reviewCount: 67,
                accessPIN: "753162"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Hauz Khas Village",
                coordinates: CLLocationCoordinate2D(latitude: 28.5494, longitude: 77.2001),
                type: .privateDriveway,
                pricePerHour: 35,
                hasCCTV: false,
                isCovered: false,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: false,
                hasInsurance: false,
                isOccupied: true,
                rating: 4.1,
                reviewCount: 45,
                accessPIN: "291847"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Lajpat Nagar II",
                coordinates: CLLocationCoordinate2D(latitude: 28.5680, longitude: 77.2408),
                type: .privateDriveway,
                pricePerHour: 30,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.4,
                reviewCount: 112,
                accessPIN: "584739"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Sector 18, Noida",
                coordinates: CLLocationCoordinate2D(latitude: 28.5706, longitude: 77.3219),
                type: .privateDriveway,
                pricePerHour: 40,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.6,
                reviewCount: 203,
                accessPIN: "637291"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Cyber Hub, Gurugram",
                coordinates: CLLocationCoordinate2D(latitude: 28.4949, longitude: 77.0884),
                type: .mall,
                pricePerHour: 70,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.9,
                reviewCount: 892
            ),
            
            // Additional Mall Parking
            ParkingSpot(
                id: UUID(),
                address: "Pacific Mall, Subhash Nagar",
                coordinates: CLLocationCoordinate2D(latitude: 28.6391, longitude: 77.1098),
                type: .mall,
                pricePerHour: 50,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.2,
                reviewCount: 234
            ),
            ParkingSpot(
                id: UUID(),
                address: "Vegas Mall, Dwarka",
                coordinates: CLLocationCoordinate2D(latitude: 28.5921, longitude: 77.0460),
                type: .mall,
                pricePerHour: 55,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.4,
                reviewCount: 178
            ),
            ParkingSpot(
                id: UUID(),
                address: "The Great India Place, Noida",
                coordinates: CLLocationCoordinate2D(latitude: 28.5675, longitude: 77.3260),
                type: .mall,
                pricePerHour: 65,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: true,
                rating: 4.5,
                reviewCount: 456
            ),
            ParkingSpot(
                id: UUID(),
                address: "Ansal Plaza, Andrews Ganj",
                coordinates: CLLocationCoordinate2D(latitude: 28.5710, longitude: 77.2280),
                type: .mall,
                pricePerHour: 45,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: false,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.0,
                reviewCount: 123
            ),
            
            // Additional Private Driveways
            ParkingSpot(
                id: UUID(),
                address: "Vasant Vihar, C Block",
                coordinates: CLLocationCoordinate2D(latitude: 28.5612, longitude: 77.1598),
                type: .privateDriveway,
                pricePerHour: 55,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.7,
                reviewCount: 98,
                accessPIN: "847293"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Green Park Extension",
                coordinates: CLLocationCoordinate2D(latitude: 28.5598, longitude: 77.2089),
                type: .privateDriveway,
                pricePerHour: 40,
                hasCCTV: true,
                isCovered: false,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.2,
                reviewCount: 56,
                accessPIN: "192837"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Mayur Vihar Phase 1",
                coordinates: CLLocationCoordinate2D(latitude: 28.6075, longitude: 77.2935),
                type: .privateDriveway,
                pricePerHour: 25,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: false,
                isOccupied: false,
                rating: 4.0,
                reviewCount: 78,
                accessPIN: "564738"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Pitampura, Block D",
                coordinates: CLLocationCoordinate2D(latitude: 28.7041, longitude: 77.1319),
                type: .privateDriveway,
                pricePerHour: 30,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.3,
                reviewCount: 42,
                accessPIN: "928374"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Rohini Sector 9",
                coordinates: CLLocationCoordinate2D(latitude: 28.7258, longitude: 77.1108),
                type: .privateDriveway,
                pricePerHour: 20,
                hasCCTV: false,
                isCovered: false,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: false,
                hasInsurance: false,
                isOccupied: false,
                rating: 3.8,
                reviewCount: 23,
                accessPIN: "746291"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Janakpuri C Block",
                coordinates: CLLocationCoordinate2D(latitude: 28.6219, longitude: 77.0880),
                type: .privateDriveway,
                pricePerHour: 35,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.5,
                reviewCount: 67,
                accessPIN: "381927"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Indirapuram, Ghaziabad",
                coordinates: CLLocationCoordinate2D(latitude: 28.6412, longitude: 77.3587),
                type: .privateDriveway,
                pricePerHour: 30,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.4,
                reviewCount: 89,
                accessPIN: "529184"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Karol Bagh, WEA Block",
                coordinates: CLLocationCoordinate2D(latitude: 28.6517, longitude: 77.1896),
                type: .privateDriveway,
                pricePerHour: 40,
                hasCCTV: true,
                isCovered: false,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: true,
                rating: 4.1,
                reviewCount: 34,
                accessPIN: "617293"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Rajouri Garden Main Market",
                coordinates: CLLocationCoordinate2D(latitude: 28.6467, longitude: 77.1234),
                type: .privateDriveway,
                pricePerHour: 45,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: false,
                isAccessible: true,
                is24Hours: false,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.3,
                reviewCount: 56,
                accessPIN: "839472"
            ),
            ParkingSpot(
                id: UUID(),
                address: "Sector 62, Noida",
                coordinates: CLLocationCoordinate2D(latitude: 28.6273, longitude: 77.3649),
                type: .privateDriveway,
                pricePerHour: 35,
                hasCCTV: true,
                isCovered: true,
                hasEVCharging: true,
                isAccessible: true,
                is24Hours: true,
                hasInsurance: true,
                isOccupied: false,
                rating: 4.6,
                reviewCount: 112,
                accessPIN: "472918"
            )
        ]
    }
    
    // MARK: - Data Access
    
    func getAvailableSpots() -> [ParkingSpot] {
        parkingSpots.filter { !$0.isOccupied }
    }
    
    func getSpot(by id: UUID) -> ParkingSpot? {
        parkingSpots.first { $0.id == id }
    }
    
    func updateSpotOccupancy(id: UUID, isOccupied: Bool) {
        if let index = parkingSpots.firstIndex(where: { $0.id == id }) {
            parkingSpots[index].isOccupied = isOccupied
        }
    }
}
