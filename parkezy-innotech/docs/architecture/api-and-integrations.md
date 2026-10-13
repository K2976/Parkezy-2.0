# API and Integration Contracts

The app has **no first-party API**. All calls are PostgREST requests made by `SupabaseService` (`Backend/SupabaseService.swift`) or Supabase Auth calls made by `AuthViewModel`. Authentication for every call: `apikey` = anon key + `Authorization: Bearer <user JWT>` when signed in. Authorization is whatever RLS allows (historical DDL for 5 tables; live unverified). Error contract: **none** — every method returns `nil`/`[]`/`false` and logs; auth errors are detected by substring.

## Data service (PostgREST)
| Method | Table / op | Filter | Returns | Callers |
|---|---|---|---|---|
| `getUserProfile(id)` | `profiles` select single | `id = :id` | `AppUser?` | `AuthViewModel`, `PrivateParkingViewModel`, `HostViewModel` |
| `updateUserProfile(user)` | `profiles` update | `id` | Bool | `AuthViewModel` (unreachable callers) |
| `getAllPrivateListings()` | `private_listings` select | **none** | `[PrivateParkingListing]` | `PrivateParkingViewModel.refresh…` |
| `getMyPrivateListings(ownerID)` | select | `owner_id` | list | 0 callers |
| `createPrivateListing` / `updatePrivateListing` / `deletePrivateListing` | insert / update / delete | `id` | listing? / Bool | `PrivateParkingViewModel` (delete: no UI) |
| `getNearbyFacilities(location, radiusKm)` | `commercial_facilities` select | **none** (params ignored) | list | 0 callers |
| `getAllCommercialFacilities()` | select | none | list | `CommercialParkingViewModel` |
| `getPrivateBookings(userID)` | `bookings` select | `user_id`, `type='private'` | `[BookingSession]` | `HostViewModel` |
| `requestPrivateBooking` | `bookings` insert | — | session? | 0 callers |
| `getBookingSessions(userID)` | `bookings` select | `user_id` | list | 0 callers |
| `createBookingSession` / `updateBookingSession` | `bookings` insert / update | `id` | session? / Bool | `BookingViewModel` |
| `getParkingSpots()` | `parking_spots` select | none | `[ParkingSpot]` | `MapViewModel` |
| `updateParkingSpotOccupancy(id,isOccupied)` | `parking_spots` update | `id` | Bool | `BookingViewModel.endSession` |
| `getPrivateBookingRequests(hostID)` | `private_bookings` select | `host_id` | list | `PrivateParkingViewModel` |
| `createPrivateBookingRequest` / `updatePrivateBookingRequest` | insert / update | `id` | booking? / Bool | `requestBooking`, `approve/reject` |
| `getCommercialBookings(driverID)` | `commercial_bookings` select | `driver_id` | list | `CommercialParkingViewModel` |
| `createCommercialBooking` | insert | — | booking? | `bookSlot` (result ignored) |
| `createDispute` | `disputes` insert | — | dispute? | `DisputeView` |

Gaps: no pagination, no viewport query, no server-side search, no cancel-booking, no review/rating submission, no host listing of commercial bookings, no driver listing of private bookings.

## Supabase Auth calls (`AuthViewModel`)
`auth.session`, `auth.signUp(email,password,data:{name,phone_number:""})`, `auth.signIn(email,password)`, `auth.signOut()`, `auth.signInWithIdToken(.apple, idToken, nonce)`, `auth.resetPasswordForEmail`. **Not used:** admin delete user (needs service role / RPC), MFA, OTP, refresh handling beyond SDK defaults.

## Platform integrations
| Integration | Use | Status |
|---|---|---|
| MapKit (SwiftUI `Map`, `MKLocalSearch`) | Map, annotations, location picker | Working (picker unreachable) |
| CoreLocation | Updates (10 m filter), geofence region monitoring (50 m default) (`LocationManager.geofenceRadius`), reverse geocode | Permission never requested on driver path |
| UserNotifications | Local reminders | Not authorized |
| AuthenticationServices + CryptoKit | Apple nonce/SHA256 | No entitlement |
| VisionKit `DataScannerViewController` | Host QR scan | Unreachable; no camera usage string |
| ActivityKit / WidgetKit / AppIntents | Live Activity, widget, Siri | Inert |
| Network (`NWPathMonitor`) | Offline banner | Working |

## Not integrated (needed by product claims)
Payments (Stripe/Razorpay/UPI), push notifications (APNs), SMS for PINs, image/video storage, maps routing/navigation, analytics/crash reporting.
