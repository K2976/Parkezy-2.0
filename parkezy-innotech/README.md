# Parkezy — Smart Parking Marketplace & Management Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Expo](https://img.shields.io/badge/Expo-SDK_57-000020?style=flat&logo=expo&logoColor=white)](https://expo.dev)
[![React Native](https://img.shields.io/badge/React_Native-0.74+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactnative.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_+_PostGIS-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.x-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37814A?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)

**Parkezy** is an enterprise-grade, two-sided parking marketplace and real-time bay management platform. It bridges urban drivers searching for guaranteed parking with private homeowners, commercial lots, shopping malls, and corporate garages wanting to monetize vacant parking spaces.

Built with a **zero double-booking mathematical guarantee** (PostgreSQL GiST exclusion constraints), **server-authoritative dynamic pricing & billing**, **double-entry financial ledger**, and a **contactless IoT/QR & PIN access engine**.

---

## Table of Contents
1. [Platform Architecture](#platform-architecture)
2. [End-to-End System Flowcharts](#end-to-end-system-flowcharts)
   - [1. Driver Booking & Parking Lifecycle](#1-driver-booking--parking-lifecycle)
   - [2. Host Listing & Inventory Onboarding](#2-host-listing--inventory-onboarding)
   - [3. Contactless QR / PIN Access & Validation](#3-contactless-qr--pin-access--validation)
   - [4. Double-Entry Accounting & Ledger Reconciliation](#4-double-entry-accounting--ledger-reconciliation)
   - [5. Transactional Outbox & Background Worker Pipeline](#5-transactional-outbox--background-worker-pipeline)
3. [Comprehensive Feature Inventory](#comprehensive-feature-inventory)
   - [Driver Experience](#driver-experience)
   - [Host Management Suite](#host-management-suite)
   - [Commercial Facilities & Garage Operations](#commercial-facilities--garage-operations)
   - [Security, Anti-Abuse & Reliability Engineering](#security-anti-abuse--reliability-engineering)
4. [Data Model & Database Schema](#data-model--database-schema)
5. [Technology Stack](#technology-stack)
6. [Local Development & Setup Guide](#local-development--setup-guide)
7. [Automated Verification, Benchmarks & Load Testing](#automated-verification-benchmarks--load-testing)
   - [Unit & Integration Test Suite (224 Tests)](#1-unit--integration-test-suite-224-tests)
   - [Load & Stress Testing with k6](#2-load--stress-testing-with-k6)
   - [Prometheus & Grafana Real-Time Monitoring](#3-prometheus--grafana-real-time-monitoring)
   - [Sustained Throughput & Capacity Benchmarks](#4-sustained-throughput--capacity-benchmarks)
   - [Concurrency Race & Chaos Engineering](#5-concurrency-race--chaos-engineering)
   - [Mobile Quality Verification](#6-mobile-quality-verification)
8. [Production Deployment](#production-deployment)

---

## Platform Architecture

```mermaid
flowchart TD
    subgraph Client["Client Tier (iOS / Android / Web)"]
        MA["Expo React Native Mobile App"]
        WebPreview["Web Preview / Metro Bundler"]
    end

    subgraph Edge["Ingress & Edge Security"]
        Nginx["Reverse Proxy / SSL Termination"]
        RateLimiter["Redis Sliding-Window Rate Limiter"]
        BloomFilter["Redis Bloom Filter (Webhook De-duplication)"]
    end

    subgraph AppServer["FastAPI Stateless Application Tier"]
        AuthSvc["Auth & Session Service (JWT + Refresh Rotation)"]
        ListingSvc["Geospatial Listing & Inventory Service"]
        BookingSvc["Booking Engine & Concurrency Lock"]
        PricingSvc["Server-Authoritative Pricing & Tax Rules"]
        LedgerSvc["Double-Entry Ledger & Commission Engine"]
        AccessSvc["QR Crypto & Offline PIN Access Manager"]
    end

    subgraph DataStore["Authoritative Data & Cache Tier"]
        PG[("PostgreSQL 16 + PostGIS<br/>• GiST Exclusion Constraints<br/>• Double-Entry Ledger<br/>• Outbox Events Table")]
        RedisDB[("Redis 7.x In-Memory Store<br/>• Spatial Search Cache<br/>• One-Time QR Nonce Store<br/>• Celery Task Broker")]
        S3Storage[("S3-Compatible Object Store<br/>(Backblaze B2 / SeaweedFS)<br/>• Presigned Direct PUT URLs")]
    end

    subgraph WorkerTier["Asynchronous Worker Tier (Celery)"]
        CeleryBeat["Celery Beat Scheduler<br/>(Hold Expiries, Reminders, No-Shows)"]
        CeleryWorkers["Celery Background Workers<br/>(Outbox Event Processors)"]
    end

    subgraph External["External Integrations"]
        Razorpay["Razorpay Payment Gateway"]
        Resend["Resend Transactional Email API"]
        ExpoPush["Expo Push Notification Service"]
        Mailpit["Mailpit Local Dev Mailer"]
    end

    Client --> Nginx
    Nginx --> RateLimiter
    RateLimiter --> AppServer

    AppServer --> PG
    AppServer --> RedisDB
    AppServer -. Presigned PUT .-> S3Storage
    Client -->|Direct Upload| S3Storage

    PG -->|Outbox Events Log| CeleryWorkers
    CeleryBeat --> CeleryWorkers
    CeleryWorkers --> Razorpay
    CeleryWorkers --> Resend
    CeleryWorkers --> ExpoPush
    CeleryWorkers --> Mailpit
```

---

## End-to-End System Flowcharts

### 1. Driver Booking & Parking Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Driver (Mobile App)
    participant API as FastAPI Backend
    participant DB as PostgreSQL + PostGIS
    participant Redis as Redis Cache
    participant Pay as Razorpay / Pay-at-Venue
    actor Host as Host / Gatekeeper

    Driver->>API: GET /v1/listings?lat=...&lng=...&radius=5km&amenities=ev,cctv
    API->>Redis: Check geospatial cache
    Redis-->>API: Cache miss
    API->>DB: ST_DWithin query with GiST spatial index
    DB-->>API: Active listings + slot availability
    API-->>Driver: Return filtered map pins & cards

    Driver->>API: POST /v1/bookings/calculate (slot_id, start_time, end_time)
    API-->>Driver: Server-authoritative breakdown: Base + Peak Surge + 18% GST + Platform Fee

    Driver->>API: POST /v1/bookings (Hold slot & initiate booking)
    API->>DB: INSERT booking (EXCLUDE USING gist slot conflict check)
    Note over API,DB: If overlapping slot exists, DB rejects atomically. Zero double-booking.
    API-->>Driver: 201 Created (Booking Hold valid for 15 mins)

    Driver->>Pay: Complete Payment (Razorpay SDK or Select "Pay at Venue")
    Pay-->>API: Webhook payment.captured (deduplicated via Bloom Filter)
    API->>DB: Update booking to 'confirmed' + create access_grants
    
    Driver->>API: GET /v1/bookings/{id}/pass (Generate dynamic QR)
    API->>Redis: Store single-use nonce (TTL = 120s)
    API-->>Driver: Signed QR Payload + Offline 6-Digit PIN

    Driver->>Host: Arrive at gate & present QR code
    Host->>API: POST /v1/host/scan (Submit scanned QR or PIN)
    API->>Redis: Validate and invalidate one-time nonce
    API->>DB: Update booking to 'active' + checked_in_at timestamp
    API-->>Driver: Push notification: "Checked in successfully! Session running."

    Note over Driver,Host: Live parking session with countdown timer & overstay tracking.

    Driver->>Host: Exit facility & scan out
    Host->>API: POST /v1/host/scan (Check-out)
    API->>DB: Calculate duration & overstay fee (₹20 per 15 min started)
    API->>DB: Set status to 'completed' & trigger balanced ledger entry
    API-->>Driver: Push notification: "Session completed. Digital receipt ready."
```

---

### 2. Host Listing & Inventory Onboarding

```mermaid
flowchart TD
    Start(["Host opens 'Host Mode'"]) --> Step1["Step 1: Location Definition<br/>• Interactive Pin Drop<br/>• Reverse Geocoding<br/>• Address & Landmark"]
    Step1 --> Step2["Step 2: Slot Inventory Configuration<br/>• Multi-slot labels (e.g. A-01, B-02)<br/>• Slot types: Standard, EV, SUV, Accessible<br/>• Covered / Indoor toggles"]
    Step2 --> Step3["Step 3: Facility Amenities & Rules<br/>• CCTV, Security Guard, 24/7 Access<br/>• Wheelchair Ramp, Valet Support<br/>• Height & vehicle dimension limits"]
    Step3 --> Step4["Step 4: Media Uploads<br/>• Client requests Presigned URL<br/>• Direct-to-S3/B2 PUT binary stream<br/>• Zero backend media bottleneck"]
    Step4 --> Step5["Step 5: Smart Pricing & Policy<br/>• Base hourly rate (with ₹40 local avg suggestion)<br/>• Instant Auto-Accept vs Manual Host Review<br/>• Cancellation window & refund policy"]
    Step5 --> Submit["Step 6: Submit & Publish Listing"]
    Submit --> DBInsert[("PostgreSQL:<br/>Insert listings & slots with PostGIS geography point")]
    DBInsert --> CacheInvalidate["Redis:<br/>Evict neighboring geo-search cache cells"]
    CacheInvalidate --> Live(["Listing is immediately discoverable on map"])
```

---

### 3. Contactless QR / PIN Access & Validation

```mermaid
sequenceDiagram
    actor Driver as Driver Phone
    actor Gate as Host / Gatekeeper Scanner
    participant Server as Access Verification Service
    participant Redis as Redis Nonce Cache
    participant DB as Postgres Database

    Note over Driver,Gate: Driver arrives at parking facility
    Driver->>Driver: Open Digital Parking Pass
    Driver->>Server: Request dynamic QR token
    Server->>Redis: Generate crypto-nonce: SETEX qr:{booking_id}:{nonce} 120s
    Server-->>Driver: Return QR payload with timestamp & nonce

    Gate->>Driver: Scan driver's QR code via in-app camera
    Gate->>Server: POST /v1/host/scan {payload, scanner_id}
    Server->>Redis: Verify & atomically DEL qr:{booking_id}:{nonce}
    alt Nonce missing or expired (Replay Attack)
        Redis-->>Server: Key does not exist
        Server-->>Gate: 400 Bad Request: "Expired or already used QR"
    else Nonce valid
        Redis-->>Server: Nonce consumed
        Server->>DB: Query booking status & slot ownership
        alt First Scan (Entry)
            Server->>DB: UPDATE booking SET status='active', checked_in_at=NOW()
            Server-->>Gate: 200 OK: "Access Granted: Entry Approved"
        else Second Scan (Exit)
            Server->>DB: UPDATE booking SET status='completed', checked_out_at=NOW()
            Server-->>Gate: 200 OK: "Access Granted: Exit Approved (Overstay Fee: ₹0)"
        end
    end

    Note over Driver,Gate: Fallback: In offline/no-camera environments, Host enters driver's 6-digit offline PIN.
```

---

### 4. Double-Entry Accounting & Ledger Reconciliation

```mermaid
flowchart LR
    subgraph Transaction["Driver Transaction"]
        Payment["Driver Pays: ₹236.00<br/>(₹200 Base + ₹36 18% GST)"]
    end

    subgraph Split["Platform Fee Engine"]
        HostGross["Gross Host Earnings: ₹200.00"]
        PlatformFee["Platform Commission (15%): ₹30.00"]
        HostNet["Net Host Payout: ₹170.00"]
        GSTCollected["GST Payable to Govt (18%): ₹36.00"]
    end

    subgraph Ledger["Double-Entry Balanced Ledger (Database Trigger Verified)"]
        L1["DR: Cash / Gateway Clearing (₹236.00)"]
        L2["CR: Host Payable Account (₹170.00)"]
        L3["CR: Platform Revenue (₹30.00)"]
        L4["CR: Tax Withholding / GST Liability (₹36.00)"]
    end

    Payment --> Split
    HostGross --> HostNet
    HostGross --> PlatformFee
    Split --> Ledger

    L1 --- BalanceRule{"Sum(Debit) == Sum(Credit)<br/>₹236.00 == ₹236.00"}
    L2 --- BalanceRule
    L3 --- BalanceRule
    L4 --- BalanceRule
    BalanceRule -->|Trigger Verified| BalancedDB[("Immutable ledger_entries Table")]
```

---

### 5. Transactional Outbox & Background Worker Pipeline

```mermaid
flowchart TD
    API["FastAPI Handler (e.g. Booking Created / Cancelled / Completed)"] --> DBTx["BEGIN Database Transaction"]
    DBTx --> WriteBiz["1. Update Business Entity (e.g. bookings table)"]
    WriteBiz --> WriteOutbox["2. INSERT into outbox_events table (Payload, Type, Status=PENDING)"]
    WriteOutbox --> CommitTx["COMMIT Transaction (Atomic: Both or Neither)"]

    subgraph CeleryWorker["Celery Worker Engine"]
        PollOutbox["Celery Worker / Poller<br/>Fetches PENDING outbox_events"]
        LockRow["SELECT ... FOR UPDATE SKIP LOCKED"]
        PollOutbox --> LockRow

        LockRow --> Router{Event Type Router}
        Router -->|booking.confirmed| EmailHandler["Render & Send Booking Receipt Email (Resend)"]
        Router -->|booking.reminder| PushHandler["Send Push Notification: 'Slot reservation in 15m'"]
        Router -->|booking.cancelled| RefundHandler["Call Razorpay Refund API (Idempotent target-based)"]
        Router -->|booking.expired| CleanupHandler["Release Slot Reservation & Mark Booking Expired"]

        EmailHandler --> MarkDone["UPDATE outbox_events SET status='PROCESSED'"]
        PushHandler --> MarkDone
        RefundHandler --> MarkDone
        CleanupHandler --> MarkDone

        EmailHandler -. Failure .-> RetryQueue["Exponential Backoff Retry (Max 5 attempts)"]
        RetryQueue --> MarkDone
    end

    CommitTx -. Celery Task Trigger .-> PollOutbox
```

---

## Comprehensive Feature Inventory

### Driver Experience

| Feature | Description | Architecture / Implementation |
|---|---|---|
| **Interactive Geospatial Map** | Real-time map displaying commercial garages and private driveways with clustering and custom price badges. | Built with `react-native-maps` / Leaflet web fallback. PostGIS `ST_DWithin` spatial bounding queries with GiST index. |
| **Granular Amenity Filtering** | Instantly filter spots by EV Charging, Covered / Indoor, CCTV Surveillance, Security Guard, and Wheelchair Access. | Bitmask / JSONB indexed amenity filtering directly in PostgreSQL queries. |
| **Instant Metro Jump Navigation** | Quick-select buttons for high-density hubs (Delhi NCR / Ghaziabad, Bengaluru, Mumbai, Connaught Place, Cyber City). | Coordinated map camera animations with preset bounding coordinates. |
| **Dynamic Slot Grid & Floor Picker** | Visual floor-by-floor slot layout showing real-time slot statuses (Available, Reserved, Occupied, Maintenance). | Dynamic slot type cards (Compact, Sedan, SUV, EV, Accessible) with price multiplier modifiers. |
| **Flexible Booking Windows** | Choose between "Park Now" (immediate 15-minute start hold) or schedule future arrival dates and hours. | Multi-tier validation against host opening hours and blackout calendar windows. |
| **Server-Authoritative Pricing** | Transparent cost calculation breaking down base rate, peak-hour multiplier, GST (18%), and platform fees. | Computed on FastAPI backend (`/v1/bookings/calculate`); client never manipulates price variables. |
| **Dual Payment Methods** | In-app credit card / UPI / netbanking payment via Razorpay, or cash / offline UPI at venue. | Port-based gateway interface (`PaymentGateway`) supporting both online webhooks and offline settlement. |
| **Dynamic QR & Offline PIN Pass** | Tamper-proof, dynamic rotating QR code with single-use nonce (120s TTL) and backup 6-digit PIN. | In-memory Redis nonce expiration + cryptographically hashed PINs stored in `access_grants`. |
| **Live Session Dashboard & Timer** | Active parking session tracker showing live elapsed time, overstay fee counter, and one-tap extension. | Real-time countdown timer synchronized with server `checked_in_at` and `end_time` timestamps. |
| **Automated Overstay Protection** | Predictable, itemized billing for vehicle owners exceeding their reservation window (₹20 per started 15 min). | Automated overstay fee calculation executed server-side upon gatekeeper exit scan. |
| **Dispute Filing & Evidence** | Drivers can file complaints (blocked spot, hostile host, overcharge) with photo evidence. | Presigned direct S3 image upload with dedicated dispute audit records (`disputes` table). |
| **Digital Receipts & Ledger History** | Searchable history of active, past, and cancelled reservations with complete financial invoices. | PDF/HTML receipts rendered via server templates and downloadable in-app. |
| **In-App Support Ticketing** | Directly submit customer support tickets with automated ticket ID generation and notifications. | Dedicated `support_tickets` persistence with transactional outbox email notification pipeline. |
| **Account Deletion & Data Privacy** | Full user data erasure and session invalidation compliant with DPDP Act 2023 / GDPR. | Cryptographic password re-authentication guard (`/v1/account/delete`) and cascade cleanup. |
| **Cross-Platform OpenStreetMap** | High-performance open-source map view without proprietary API lock-ins. | Native Android/iOS via `react-native-maps` (with positive zIndex tile stacking) and Web via Leaflet iframe bridge. |

---

### Host Management Suite

| Feature | Description | Architecture / Implementation |
|---|---|---|
| **Step-by-Step Listing Wizard** | Intuitive 5-step wizard: Geocoding Pin Drop → Media Upload → Details → Amenities → Review. | Client-side step validation with direct-to-S3 media upload avoiding server memory bottlenecks. |
| **Interactive Map Pin-Drop** | Hosts fine-tune exact driveway or garage entry coordinates on an interactive satellite/vector map. | High-accuracy latitude and longitude captured into PostGIS `geography(Point, 4326)`. |
| **Slot Inventory Configuration** | Multi-slot creation with floor labeling, custom bay names (e.g., G-01, B2-14), and vehicle capability tags. | Relational `slots` table linked via foreign key to parent `listings`, ensuring clean inventory integrity. |
| **Suggested Price Intelligence** | Recommends optimal hourly rates by computing average pricing of neighboring listings within a 2 km radius. | Real-time server-side geospatial spatial averaging endpoint (`/v1/host/suggested-price`). |
| **Instant vs Approval Modes** | Choose between instant auto-accept bookings or manual review of driver booking requests. | Built-in 15-minute timer for manual approvals before unconfirmed holds auto-expire. |
| **Real-Time Earnings Dashboard** | 14-day trailing performance chart, all-time net revenue, occupancy rates, and upcoming arrivals. | Optimized SQL aggregation across completed bookings; resilient empty-state visual tracks. |
| **In-App Camera QR Scanner** | Native camera barcode scanner for hosts and gatekeepers to validate incoming driver passes. | Built with `expo-camera`; decodes payload and calls `/v1/host/scan` with instant audio/haptic feedback. |
| **Offline PIN Verification** | Backup verification input for hosts when lighting is poor or driver camera screen is cracked. | Compares hashed PIN against active `access_grants` row in a constant-time cryptographic check. |
| **Host Booking Manager** | Filter reservations by Upcoming, Active, Completed, and Cancelled with one-tap host check-in/out. | Real-time list updates backed by TanStack Query optimistic invalidation. |

---

### Commercial Facilities & Garage Operations

| Feature | Description | Architecture / Implementation |
|---|---|---|
| **Multi-Floor Garage Layout** | Manage multi-tier garages (Basement 1, Ground, Floor 1, Rooftop) with separate slot quotas. | Hierarchical layout query modeling facilities and slots with floor sorting attributes. |
| **Gatekeeper Fast-Track Mode** | Streamlined check-in/out interface designed for continuous, rapid entry scanning during rush hours. | Sub-100ms API response time powered by Redis-cached active reservation lookups. |
| **Dynamic Surge Pricing Rules** | Configure weekend surcharges, event day multipliers, and commercial peak-hour rates. | Configured via `platform_settings` table and dynamic host pricing multipliers. |

---

### Security, Anti-Abuse & Reliability Engineering

| Feature | Description | Architecture / Implementation |
|---|---|---|
| **Zero Double-Booking Guarantee** | Prevents multiple drivers from reserving the same bay at the same time, even under extreme load. | PostgreSQL GiST exclusion constraint: `EXCLUDE USING gist (slot_id WITH =, period WITH &&)`. |
| **Double-Entry Financial Ledger** | Every financial transaction is recorded with balanced debit and credit entries verified by DB triggers. | `ledger_entries` table ensuring total debits exactly equal total credits at all times. |
| **Transactional Outbox Pattern** | Guarantees reliable delivery of emails, push notifications, and webhooks without lost messages. | Database writes commit entity changes and outbox rows in a single atomic ACID transaction. |
| **Sliding-Window Rate Limiting** | Protects sensitive endpoints (auth, SMS OTP, booking holds) from brute force and denial of service. | Redis-backed sliding-window rate limiter checking caller IP and user token. |
| **Bloom Filter Webhook Idempotency** | Prevents payment replay attacks and duplicate webhook executions from Razorpay. | Redis Bloom filter backed by a unique database constraint on `idempotency_key`. |
| **Rotating Refresh Token Security** | High-security JWT authentication with rotating refresh tokens and automatic reuse detection. | If a used refresh token is presented again, the entire user token family is immediately revoked. |
| **Direct-to-Storage Presigned URLs** | Media files (listing photos, dispute evidence) upload directly from mobile device to S3/B2. | Secure presigned PUT URLs with byte-size and MIME-type restrictions. Zero server upload proxying. |
| **Strict Input Sanitization & NUL Byte Defense** | Immune to PostgreSQL text crashes caused by null character string exploits (`\u0000`). | Strict Pydantic validator rejecting null bytes across all input strings and fields. |
| **Active Booking Archive Protection** | Prevents hosts from deleting or archiving parking bays that have upcoming or active reservations. | Pre-action constraint checks preventing orphaned driver bookings and unfulfilled sessions. |

---

## Data Model & Database Schema

```mermaid
erDiagram
    users ||--o{ listings : "owns"
    users ||--o{ bookings : "creates (as driver)"
    users ||--o{ disputes : "files"
    users ||--o{ refresh_tokens : "holds"
    
    listings ||--|{ slots : "contains"
    listings ||--o{ bookings : "receives"
    
    slots ||--o{ bookings : "reserved in"
    
    bookings ||--|| access_grants : "grants access"
    bookings ||--o{ payments : "paid through"
    bookings ||--o{ ledger_entries : "audited by"
    bookings ||--o{ disputes : "subject of"
    
    outbox_events }|--|| users : "triggered by"

    users {
        uuid id PK
        varchar email UK
        varchar phone
        varchar hashed_password
        varchar full_name
        boolean is_active
        timestamp created_at
    }

    listings {
        uuid id PK
        uuid owner_id FK
        varchar title
        varchar kind
        geography location
        text address
        jsonb amenities
        numeric hourly_rate
        varchar status
    }

    slots {
        uuid id PK
        uuid listing_id FK
        varchar label
        integer floor
        varchar slot_type
        boolean is_active
    }

    bookings {
        uuid id PK
        uuid listing_id FK
        uuid slot_id FK
        uuid driver_id FK
        tstzrange period
        varchar status
        numeric total_amount
        numeric platform_fee
        numeric tax_amount
        timestamp checked_in_at
        timestamp checked_out_at
    }

    access_grants {
        uuid id PK
        uuid booking_id FK
        varchar pin_hash
        varchar qr_secret
        timestamp expires_at
        integer scan_count
    }

    ledger_entries {
        uuid id PK
        uuid booking_id FK
        varchar account_name
        numeric debit_amount
        numeric credit_amount
        timestamp recorded_at
    }

    outbox_events {
        uuid id PK
        varchar event_type
        jsonb payload
        varchar status
        integer retry_count
        timestamp created_at
    }
```

---

## Technology Stack

| Layer | Technologies Used | Key Responsibilities |
|---|---|---|
| **Mobile App (Frontend)** | React Native, Expo SDK 57, Expo Router, TypeScript, TanStack Query, `react-native-reanimated` | Cross-platform iOS/Android app, tab navigation, interactive map, camera QR scanner, responsive layouts. |
| **API Application Tier** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Alembic | Stateless REST API, request validation, business rules, pricing engine, JWT auth, exception handlers. |
| **Geospatial & Storage** | PostgreSQL 16, PostGIS, GiST Indexes | ACID storage, geospatial queries (`ST_DWithin`, `ST_Distance`), native exclusion constraints. |
| **Caching & In-Memory** | Redis 7.x, Redis Bloom Filter | Geospatial query cache, one-time QR nonces, sliding-window rate limiters, Celery task broker. |
| **Asynchronous Engine** | Celery 5.4, Celery Beat | Transactional outbox polling, reservation hold cleanup, overstay monitoring, push and email dispatch. |
| **Object Storage** | S3-Compatible API (Backblaze B2, SeaweedFS) | Secure presigned direct PUT uploads for listing photos and dispute evidence. |
| **Communication & Notifications** | Resend API, Expo Push Service, Mailpit | Transactional receipts, booking status emails, mobile push alerts. |
| **Payment Gateway** | Razorpay SDK, Offline Pay-at-Venue | Card/UPI payment capture, automatic webhook signature verification, target-based refunds. |
| **Testing & Quality** | Pytest (224 full integration tests), k6 (load & stress test suite), Prometheus & Grafana (real-time telemetry), Ruff, TypeScript (`tsc`), Expo Doctor | 224 automated backend tests, production load simulation, live metrics dashboard, static type validation. |

---

## Local Development & Setup Guide

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose
- [Python 3.12+](https://www.python.org/) with [uv](https://docs.astral.sh/uv/) package manager
- [Node.js 20+](https://nodejs.org/) & npm

### 1. Launch Development Infrastructure
Start PostgreSQL with PostGIS, Redis, SeaweedFS S3, and Mailpit email catcher:
```bash
docker compose up -d

# Optional: Launch Prometheus and Grafana for live metrics & load testing
docker compose --profile monitoring up -d
```

Verify services:
- **PostgreSQL / PostGIS**: `localhost:5434`
- **Redis**: `localhost:6380`
- **SeaweedFS S3**: `http://localhost:8333`
- **Mailpit Web Mailbox**: `http://localhost:8025`
- **Prometheus Telemetry**: `http://localhost:9090`
- **Grafana Live Dashboard**: `http://localhost:3000` (admin / admin)

### 2. Backend API & Workers
```bash
cd backend

# Setup environment variables
cp .env.example .env
# Set secure keys in .env:
# JWT_SECRET=your-random-32-char-secret
# ACCESS_CODE_SECRET=your-random-access-secret

# Install dependencies and run migrations
uv sync
uv run alembic upgrade head

# Start FastAPI API Server (Terminal 1)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start Celery Outbox Worker (Terminal 2)
uv run celery -A app.workers.celery_app worker --loglevel=INFO --concurrency=2

# Start Celery Beat Scheduler (Terminal 3)
uv run celery -A app.workers.celery_app beat --loglevel=INFO
```
Interactive API Swagger documentation is available at: **`http://localhost:8000/docs`**

### 3. Mobile Client (Expo React Native)
```bash
cd ../mobile

# Setup environment variables
cp .env.example .env
# For physical phone testing over LAN, set:
# EXPO_PUBLIC_API_URL=http://<YOUR_LOCAL_IP>:8000

# Install dependencies and launch Metro Bundler
npm install
npx expo start
```
- Press `w` to open the Web preview in your browser.
- Scan the printed QR code using the **Expo Go** app on your iOS or Android device.

---

## Automated Verification, Benchmarks & Load Testing

The platform is fortified with multi-tier verification: **243 full integration tests** covering all business rules and failure cases, a **production-like k6 load and stress test pipeline**, **Prometheus & Grafana telemetry**, and **strict mobile static analysis**.

### 1. Unit & Integration Test Suite (243 Tests)

Run the full backend integration test suite against live PostgreSQL (with PostGIS) and Redis:

```bash
cd backend
uv run pytest
```

#### Test Suite Breakdown:

| Test Module | Coverage & Verification Highlights |
|---|---|
| `tests/test_account_and_ops.py` | Account deletion with password confirmation, cascade cleanup, GDPR/DPDP data erasure. |
| `tests/test_admin_users.py` | Admin user controls, permission elevation, role guards. |
| `tests/test_auth.py` | Argon2 hashing, JWT access token issuance, rotating refresh tokens with replay revocation. |
| `tests/test_booking_extension.py` | In-session booking extension, recalculations, gap conflict checks. |
| `tests/test_bookings.py` | Zero double-booking concurrency, GiST constraint rejection, hold timeouts. |
| `tests/test_domain.py` | Domain invariants, time intervals, business rule validations. |
| `tests/test_email.py` | Resend request shape and error classification (mocked API), permanent vs. retryable failures, idempotent replays, webhook ordering/suppression, per-address reset limits. |
| `tests/test_favorites.py` | Driver bookmarking and favorite listing persistence. |
| `tests/test_host_dashboard.py` | Host listing KPIs, 14-day earnings aggregation, safe archive guards. |
| `tests/test_identity_verifier.py` | Verification codes, rate-limited SMS/email OTP attempts. |
| `tests/test_infra.py` | Redis cache, rate limiting, bloom filters, metrics route normalization. |
| `tests/test_listing_delete.py` | Listing deletion restrictions when active or upcoming bookings exist. |
| `tests/test_listings.py` | PostGIS spatial queries (`ST_DWithin`), geocoding, radius & amenity filters. |
| `tests/test_notification_preferences.py` | User notification channel preferences. |
| `tests/test_payments.py` | Razorpay webhook signature verification, payment capture, idempotency. |
| `tests/test_payouts.py` | Host balance payouts, bank account verification, ledger integration. |
| `tests/test_platform.py` | Dynamic platform settings (GST %, commission, overstay rules). |
| `tests/test_receipts.py` | Digital PDF/HTML invoice rendering and calculation accuracy. |
| `tests/test_reliability.py` | 38 adversarial resilience tests: NUL bytes (`\u0000`), huge JSON payloads, malformed tokens, pool recovery. |
| `tests/test_reviews.py` | Driver and host reviews, ratings aggregation, verified stay checks. |
| `tests/test_social_auth.py` | OAuth social login flows and account linkage. |
| `tests/test_support_and_legal.py` | In-app support tickets persistence, notification outbox, dynamic legal policy endpoints. |

---

### 2. Load & Stress Testing with k6

The load test suite runs entirely in Docker via k6, targeting a production-like 4-worker API against an isolated `parkezy_loadtest` database so development data is untouched.

```
 k6 (docker) ──requests──▶ API :8001 (4 workers) ──▶ Postgres / Redis
     │                          │ /metrics
     └─remote write─▶ Prometheus :9090 ◀─scrape─ exporters
                            │
                       Grafana :3000  (dashboard "Parkezy load test")
```

#### Running the Load Test Environment:

```bash
# 1. Start core infra + monitoring stack (Prometheus :9090, Grafana :3000, login: admin / admin)
docker compose up -d
docker compose --profile monitoring up -d

# 2. Launch production-like API & background worker under test (isolated DB, raised limits)
./loadtest/run_api.sh                 # Terminal 1: API on port 8001 (4 workers)
./loadtest/run_worker.sh              # Terminal 2: Celery outbox worker

# 3. Seed test data (500 drivers, 50 hosts, 1,000 listings x 4 slots + race listing)
cd backend && uv run python ../loadtest/seed.py --reset && cd ..

# 4. Execute k6 test suites:
./loadtest/k6.sh search                                  # Smoke test: 2 VUs for 30s
./loadtest/k6.sh search  -e PROFILE=load   -e VUS=100    # Sustained map search (100 VUs)
./loadtest/k6.sh booking -e PROFILE=stress -e VUS=50     # Full driver journey stress (search → book → pay → pass)
./loadtest/k6.sh race    -e RACERS=200                   # 200 drivers racing for the exact same slot
./loadtest/k6.sh auth    -e PROFILE=load   -e VUS=20     # Password hashing & auth throughput
./loadtest/k6.sh everything -e PROFILE=stress -e VUS=15  # Comprehensive sweep across all 89 routes (up to 90 VUs)
```

#### Available Profiles:
- **`smoke`**: 2 VUs for 30s to verify script and route health.
- **`load`**: Ramp to target VUs and sustain for 5 minutes (normal-day traffic).
- **`stress`**: Stepped ramp (VUs → 2× → 4× → 6×) to locate system bending points.
- **`spike`**: Instant 6× surge for 1 minute to test recovery from burst traffic.
- **`soak`**: Extended sustained load (default 1 hour) to detect connection or memory leaks.

---

### 3. Prometheus & Grafana Real-Time Monitoring

When `--profile monitoring` is active:
- **Grafana Dashboard**: Open `http://localhost:3000` (credentials: `admin` / `admin`).
  - Pre-provisioned dashboard: **"Parkezy load test"**.
  - Tracks real-time p50/p95/p99 latency, request rates, HTTP status distribution, active PostgreSQL connections, Redis pool saturation, lock waits, and transactional outbox backlog.
  - Filterable by individual k6 `testid` for before/after comparison.
- **Prometheus Scraper**: Open `http://localhost:9090` to inspect raw `/metrics` scraped from API, Postgres exporter, and Redis exporter.

---

### 4. Sustained Throughput & Capacity Benchmarks

Tested on a 16-core / 13 GB host machine running the 4-worker API against PostgreSQL and Redis:

| Endpoint | Peak Sustained req/s | Latency (p95) | Tested Behaviour |
|---|---|---|---|
| `GET /v1/config` | **1,634 req/s** | < 15 ms | Cached static platform settings |
| `GET /v1/me` | **1,009 req/s** | < 35 ms | Authenticated user session validation |
| `GET /v1/listings` (Search) | **865 req/s** | < 120 ms | Spatial PostGIS `ST_DWithin` bounding query |
| `GET /v1/listings/{id}/reviews` | **663 req/s** | < 45 ms | Paginated review and rating fetch |
| `POST /v1/bookings/quote` | **562 req/s** | < 60 ms | Server-authoritative price breakdown + surge |
| `GET /v1/listings/{id}` | **441 req/s** | < 55 ms | Full listing detail, amenities & host profile |
| `GET /v1/bookings` | **266 req/s** | < 80 ms | Driver booking history query |
| `POST /v1/bookings` | **117 req/s** | < 150 ms | Slot reservation with GiST exclusion check |
| `POST /v1/auth/login` | **23 req/s** | < 650 ms | Secure Argon2 password verification |

#### Correctness Under Load Summary:
- **Total Requests Executed:** **69,424 requests** across all 89 API routes.
- **Completed User Journeys:** **621 full lifecycles** (search → quote → hold → pay → access pass → overstay → check-out).
- **Error Rate:** **0 server errors (5xx)**, **0 wrong answers**.

---

### 5. Concurrency Race & Chaos Engineering

#### Zero Double-Booking Slot Race:
- **Scenario:** 200 concurrent driver Virtual Users (`./loadtest/k6.sh race -e RACERS=200`) attempt to book the exact same single-slot parking space for the exact same time window at the exact same millisecond.
- **Result:** **Exactly 1 driver succeeds (`201 Created`)**; all other 199 drivers are atomically rejected (`409 Conflict`) by PostgreSQL GiST exclusion constraints without deadlocks or double-allocation.

#### Chaos & Worker Resilience:
- **Chaos Injection (`./loadtest/chaos.sh`):** Simulates abrupt API worker crashes (`SIGKILL`) during peak load.
- **Result:** Process supervisor respawns dead workers within seconds. 0 of 1,957 in-flight requests failed; the system cleanly drained and processed the outbox backlog.

#### Hostile Input Probing (`uv run python ../loadtest/probe_edges.py`):
- Probes all routes with NaN, ±Infinity, floating-point overflows (`1e308`), path traversal payloads, NUL bytes (`\u0000`), tampered JWT signatures, and dates outside valid ranges (`0001` to `9999`).
- **Result:** 100% clean 4xx client errors; zero unhandled 500 exceptions.

---

### 6. Mobile Quality Verification

```bash
cd mobile

# Static TypeScript typecheck (strict mode)
npx tsc --noEmit

# Code quality & ESLint validation
npx expo lint

# Diagnose dependency compatibility
npx expo-doctor
```

#### Cross-Platform Map Compatibility:
- **Android & iOS:** Uses `react-native-maps` with `UrlTile` pointed to `https://tile.openstreetmap.de/{z}/{x}/{y}.png` and `zIndex={1}`.
  > [!NOTE]
  > For standalone Android native builds (`npx expo run:android`), set `GOOGLE_MAPS_ANDROID_API_KEY` in `mobile/.env` to authenticate Google Play Services.
- **Web Browser:** Uses responsive Leaflet map inside an iframe with bidirectional message passing, ensuring identical appearance without native SDK requirements.

---

## Production Deployment

| Component | Recommended Free/Cost-Effective Cloud Hosting | Deployment Instructions |
|---|---|---|
| **API Backend** | Render / Fly.io / Railway | Deploy using [`backend/Dockerfile`](./backend/Dockerfile). Set `APP_ENV=production`, `TRUST_FORWARDED_FOR=true`. Migrations run automatically on container startup. |
| **Celery Workers & Beat** | Render Background Worker / Fly.io Machines | Deploy the same container image with command `celery -A app.workers.celery_app worker` and a single instance running `celery -A app.workers.celery_app beat`. |
| **PostgreSQL + PostGIS** | Neon / Supabase (Compute only) | Neon Serverless Postgres (0.5 GB free tier, does not hibernate permanently). |
| **Redis Cache** | Upstash / Redis Cloud | Redis Cloud Essentials (30 MB free tier) or Upstash Serverless Redis. |
| **Object Storage** | Backblaze B2 (S3 API) | 10 GB free tier. Keep bucket private and configure CORS to allow mobile `PUT` uploads. |
| **Mobile App** | EAS Build (Expo Application Services) | Run `npx eas build --platform all` to create standalone `.apk` / `.aab` / `.ipa` builds. |

### Transactional Email (Resend)

Every email (verification and password-reset codes, password-changed alerts, booking, payout, dispute and
support notifications) is written to the transactional outbox in the same database transaction as the
change that caused it, then sent by the **Celery worker** through Resend's HTTP API
(`backend/app/integrations/email.py`). Templates are Jinja files in `backend/app/templates/emails/`
(`.subject`, `.html`, `.txt` plain-text fallback). The API never sends email inline, so a Resend outage
cannot fail a sign-up or booking. **Without a running worker no email is ever sent.** On Render's free
plan (no background workers) `render.yaml` starts [`backend/render-start.sh`](./backend/render-start.sh),
which runs the Celery worker and beat inside the web container next to a single API worker.

| Variable | Value |
|---|---|
| `EMAIL_PROVIDER` | `resend` in staging/production. `smtp` (Mailpit, UI at http://localhost:8025) or `console` locally. `console` logs codes, so it is refused outside `local`/`test`. |
| `EMAIL_FROM` | `Parkezy <noreply@mail.kartik2976.xyz>`. Must be on the verified Resend domain. |
| `RESEND_API_KEY` | Secret, server-side only (Render dashboard / `backend/.env`). Use a *Sending access* key restricted to `mail.kartik2976.xyz`. Never put it in `mobile/` or commit it. The app refuses to boot with `EMAIL_PROVIDER=resend` and no key. |
| `RESEND_WEBHOOK_SECRET` | Optional `whsec_…` signing secret. Without it `/v1/webhooks/resend` rejects every call. |
| `EMAIL_REPLY_TO` | Optional. Leave it empty unless it is a mailbox you read. |
| `RATE_LIMIT_EMAIL_PER_WINDOW` / `_WINDOW_SECONDS` | Reset/verification emails per address across all IPs (default 3 per 15 min). |

**Delivery semantics.** A send is idempotent per event (`email_log.dedupe_key`, also sent as Resend's
`Idempotency-Key`), so retries never email twice. Network errors, 429s, 5xx, 401 and 403 are retried by
the outbox with jittered exponential backoff, up to `OUTBOX_MAX_ATTEMPTS`. Permanent rejections (400/422,
e.g. an invalid recipient) are recorded as `failed` in `email_log` and not retried. `sent` means Resend
*accepted* the message; `delivered`, `bounced`, `complained`, `failed` and `skipped` (suppressed) come from
webhooks. Bounced, complained and suppressed addresses are added to `email_suppressions` and skipped from
then on.

**Webhooks (optional, recommended).** In Resend → Webhooks, add `https://<api-host>/v1/webhooks/resend`
with the events `email.delivered`, `email.bounced`, `email.complained`, `email.failed` and
`email.suppressed`, then set the signing secret as `RESEND_WEBHOOK_SECRET`. Svix signatures are verified
(5-minute tolerance), and duplicate or out-of-order events are harmless because statuses only move forward.

**Testing safely.** `uv run pytest` never reaches Resend (the API is mocked). For a real end-to-end
check, set `EMAIL_PROVIDER=resend` locally and register with an address you own, or with Resend's test
inbox `delivered@resend.dev`. Watch the Resend dashboard's *Emails* log. The free tier allows 100 emails a
day; a `daily_quota_exceeded` 429 is retried for a few hours only, so emails beyond the quota can be lost.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
