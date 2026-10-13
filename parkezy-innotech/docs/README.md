# Parkezy Documentation Index

Single source of truth for understanding and rebuilding Parkezy. Produced by a **static, read-only investigation** on 2026-10-13 of commit `64c4240`. Nothing was compiled or run (Xcode is not installed in the analysis environment) and the live Supabase database could not be inspected (see [state/current-state.md](state/current-state.md)).

## Source-of-truth hierarchy (highest wins)
1. Running backend (Supabase schema + RLS) — *unreachable during this investigation*; the only committed copy is the May-2026 `supabase_schema.sql` in git history (`e72c855`), covering 5 of 8 tables
2. Swift source under `parkezy/parkezy/`
3. This `docs/` tree
4. Legacy root docs (`README.md` history, `parkezy_audit_report.md`, `PARKEZY_CHANGELOG.md`, `SUBMISSION_CHECKLIST.md`) — **known stale/inaccurate**, see [state/current-state.md](state/current-state.md#legacy-documentation-discrepancies)

## Status legend
| Tag | Meaning |
|---|---|
| **Implemented** | Code exists, is reachable from the app root, and its logic is complete by static reading (not runtime-tested) |
| **Partial** | Reachable but missing pieces, simulated steps, or wrong data source |
| **Unreachable** | Code exists but no navigation path reaches it from `parkezyApp` |
| **Broken** | Static evidence it fails (compile error, missing permission, wrong query) |
| **Stub** | Placeholder UI/text only |
| **Absent** | Expected by the product model but no code |
| **Inferred** | Derived from code, not confirmed against live system |

## Contents
**Product** — [overview](product/product-overview.md) · [feature inventory](product/feature-inventory.md) · [roles & permissions](product/user-roles-and-permissions.md) · [UI/UX inventory](product/ui-ux-inventory.md) · [user journeys](product/user-journeys.md) · [business rules](product/business-rules.md)

**Architecture** — [system overview](architecture/system-overview.md) · [component architecture](architecture/component-architecture.md) · [codebase map](architecture/codebase-map.md) · [data architecture](architecture/data-architecture.md) · [API & integrations](architecture/api-and-integrations.md) · [security & trust boundaries](architecture/security-and-trust-boundaries.md) · [deployment & operations](architecture/deployment-and-operations.md)

**Quality** — [audit findings](quality/audit-findings.md) · [testing strategy](quality/testing-strategy.md) · [acceptance criteria](quality/acceptance-criteria.md)

**Rebuild** — [principles](rebuild/rebuild-principles.md) · [target architecture](rebuild/target-architecture.md) · [roadmap](rebuild/implementation-roadmap.md) · [open questions](rebuild/open-questions.md) · [risk register](rebuild/risk-register.md) · [decisions (ADRs)](decisions/README.md)

**State** — [current state & investigation checklist](state/current-state.md) · handoff: [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md)

## ID conventions
`F-xx` feature · `S-xx` screen · `J-xx` journey · `BR-xx` business rule · `SEC-/BUG-/DEBT-xx` audit finding · `T-xx` test · `M-xx` milestone · `ADR-xxx` decision · `Q-xx` open question · `R-xx` risk · `C-xx` component.

## Maintenance rule
Any change to behavior, architecture or requirements must update the relevant doc in the same change. Do not record secrets or the backend project identifier here; refer to `Backend/SupabaseConfig.swift`.
