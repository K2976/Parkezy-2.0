# Open Questions (need the owner's decision)

Work that does not depend on these continues; each lists alternatives and consequences. Recommended default in **bold**.

| ID | Question | Alternatives → consequence | Needed by |
|---|---|---|---|
| Q-01 | Will v1 move real money? | **Yes via Razorpay (INR, UPI)** → M-07 scope, compliance, payouts; Stripe → higher India friction; None (ledger only) → simplest, but no revenue and "Apple Pay" UI must be removed | M-04 design |
| Q-02 | Keep the legacy single-spot `parking_spots` model (PIN → timer → overstay)? | **Drop; fold sessions into unified bookings** → one model, less code; Keep → two models forever | M-00 |
| Q-03 | Confirm business rules: GST 18% (who pays/collects), overstay ₹20 per started 15 min, platform commission 12% commercial / 15% private, `priceMultiplier`/`flatDayRate` used? | Rules currently only exist as client constants ([business-rules](../product/business-rules.md)) | M-04 |
| Q-04 | Minimum iOS version? Current target 26.5 | **iOS 17** (Observation, MapKit SwiftUI APIs) widens reach; 26.5 limits to newest devices | M-01 |
| Q-05 | Live Activities / widgets / Siri shortcuts in v1? | **Defer to M-11**; Include → extension targets + push-to-start | M-01 |
| Q-06 | Dispute/admin tooling: Supabase Studio + SQL, simple web admin, or in-app admin role? | **Studio for v1** | M-09 |
| Q-07 | Account deletion policy with active bookings, financial records, retention | Block while active; anonymize ledger | M-08 |
| Q-08 | Commercial onboarding: self-serve or admin-curated? (no UI exists today) | **Admin-curated v1** (insert via SQL/Studio) vs self-serve wizard | M-03 |
| Q-09 | Private pricing: hourly only or also daily/monthly (fields exist, unused)? | **Hourly + optional daily cap** | M-04 |
| Q-10 | Markets/regulation: India only? Host KYC? Vehicle registration capture? | Affects schema (`vehicle_number`) and compliance | M-03 |
| Q-11 | Email confirmation required at sign-up? Apple-only or email+Apple? (Sign in with Apple is already offered; it cannot work without the entitlement) | **Email OTP/confirmation + Apple** | M-01 |
| Q-12 | Is any live data worth migrating? (requires DB access restored) | **Treat as seed data** | M-00 |
| Q-13 | Brand assets (app icon 1024², name casing "Parkezy"/"ParkEzy"), privacy policy and terms URLs | Required for submission | M-11 |
| Q-14 | Ratings/reviews in v1? Columns exist but nothing writes them | **Defer** | M-10+ |
| Q-15 | Rebuild in the existing repo (new target alongside) or a fresh repo? | **Fresh Xcode project in this repo's `main` after archiving legacy under `legacy/` or a tag** | M-01 |
