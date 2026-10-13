# Rebuild Principles

1. **Server is the authority.** Pricing, availability, status transitions, access codes, capabilities and earnings are computed and enforced in Postgres (RLS, constraints, RPCs) or Edge Functions; the app only requests and renders ([ADR-002](../decisions/README.md)).
2. **Schema as code.** Every table, policy, trigger and function is a migration under `supabase/migrations`, reviewed and tested; the live DB is never edited by hand again.
3. **One booking model.** Replace the three booking tables + legacy spot model with a single normalized model (Q-02, ADR-004).
4. **Every write has a visible outcome.** No optimistic success UI without server confirmation; every async call has loading, success, empty and error states.
5. **No demo code in product paths.** No `random`, no simulator branches that skip real flows, no fake latency; test doubles live in test targets.
6. **Reachability = scope.** A screen exists only if a user can navigate to it; features not in the milestone are not merged.
7. **Keep the stack the user chose** — SwiftUI + Supabase — and add nothing (frameworks, DI libraries) that a protocol and an `Environment` value can do.
8. **Config is per environment**, secrets never in source (`.xcconfig`, CI secrets); anon key + URL are the only client-held values.
9. **Test what the server enforces.** RLS/negative tests are written before the screens that depend on them.
10. **Docs move with code.** Update `docs/` in the same change as behavior ([CLAUDE.md](../../CLAUDE.md)).

## Preserve / improve / redesign / remove (summary; per-feature in [feature-inventory](../product/feature-inventory.md))
| Preserve | Improve | Redesign | Remove |
|---|---|---|---|
| Two-sided marketplace concept; map-first discovery; commercial floor/slot grid; wizard-style listing creation; host price suggestion idea; offline banner; design tokens | Auth flows, search/filters, listing edit, notification permission, empty/error states, accessibility | Booking engine, access control (PIN/QR), host analytics, account deletion, settings, slot model, media upload | `MockDataService`, `AppConfig.useSupabase`, `UserRepository` tombstone, `LocationPickerView` duplicate, simulator-only branches, fake delays, random data, `HostTypeSelectionView` orphan |
