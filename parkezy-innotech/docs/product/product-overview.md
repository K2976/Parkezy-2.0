# Product Overview

## What it is
**Parkezy** (bundle id `K2976.parkezy`, display "ParkEzy") is a native iOS (SwiftUI) marketplace for parking. One account can act as a **driver** (find and book parking) or a **host** (list parking). Supply comes in two kinds:

| Kind | Who lists | Booking model (intended) | Data type |
|---|---|---|---|
| **Private** | Individuals with a driveway/garage | Driver *requests*; host approves unless `autoAcceptBookings` | `PrivateParkingListing` (+ embedded slots) |
| **Commercial** | Malls, offices, hospitals, airports… | Instant, auto-approved, slot-level on a floor grid | `CommercialParkingFacility` (+ embedded slots) |

A third, **legacy "parking spot" model** (`ParkingSpot`, table `parking_spots`) drives a single-session flow (pay → QR/PIN → timer → overstay → receipt → dispute) that is **no longer reachable** from the UI (see F-27).

Currency is INR (₹); 18% GST is applied client-side; sample geography is Delhi NCR.

## Problem statement (inferred from code)
Drivers in dense Indian cities struggle to find and pre-book parking; owners of idle driveways and operators of lots lack a shared channel. Parkezy provides map discovery, slot-level booking, access control (PIN/QR) and host earnings tracking.

## Target users
- **Driver** — default capability (`canDrive` capability; its default comes from an unseen DB trigger (*inferred*) and no code gates on it).
- **Private host** — enables `canHostPrivate`.
- **Commercial host** — enables `canHostCommercial` (no UI to onboard or manage a facility exists).
- Platform admin/support — no admin features exist in the app.

## Core value proposition
Map-based discovery of both private and commercial supply in one view, slot-level availability, host-set pricing with a nearby-average price hint.

## Main journeys (see [user-journeys.md](user-journeys.md))
J-01 sign-up/sign-in · J-02 browse & book commercial slot · J-03 browse private listing (booking is a stub for drivers) · J-04 host creates listing · J-05 legacy session flow (unreachable) · J-06 host QR scan (unreachable) · J-07 dispute (unreachable)

## Boundaries and limitations (verified)
- No real payments: "Pay with Apple Pay", "Amount Paid" and the "4242" card are simulated UI. There is no payment SDK.
- No server-side business logic: no Edge Functions exist (verified via the Supabase management API: empty list), and prices, PINs, occupancy and totals are computed by the client.
- Private-booking approval has no UI. Driver private booking is a stub.
- Photos/videos captured when listing are never uploaded.
- Live Activities / widgets / Siri intents are compiled into the app target but there is no extension target, so they are inert.

## Honest product status
The app compiles to a *demo-grade vertical slice*: authentication, map browsing of real DB rows, commercial booking write, private listing create/edit. Most of the end-to-end marketplace loop (approval, access, session, payment, payout) is absent or unreachable. See [feature-inventory.md](feature-inventory.md).
