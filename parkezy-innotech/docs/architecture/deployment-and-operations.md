# Deployment and Operations

| Aspect | Current state (evidence) |
|---|---|
| Build system | Xcode project `parkezy/parkezy.xcodeproj`; one app target `parkezy`; Swift 5.0 language mode; `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor`; `SWIFT_APPROACHABLE_CONCURRENCY = YES` |
| Deployment target | **iOS 26.5** (`IPHONEOS_DEPLOYMENT_TARGET`); legacy docs claim iOS 16.0 — wrong. Devices: iPhone + iPad (`TARGETED_DEVICE_FAMILY = "1,2"`) |
| Dependencies | `supabase-swift` (upToNextMajor from 2.5.1, pinned 2.46.0 in `Package.resolved`) |
| Info.plist | Generated (`GENERATE_INFOPLIST_FILE`); only scene manifest, launch screen, indirect input, orientation keys. **No usage-description strings, no `NSSupportsLiveActivities`** |
| Entitlements | None (no `CODE_SIGN_ENTITLEMENTS`) → no Sign in with Apple capability, no push, no App Groups |
| Signing | Automatic; development team not recorded in repo |
| Assets | `AppIcon` set contains **no image files** (App Store blocker) |
| CI/CD | None (no `.github`, fastlane or Xcode Cloud config) |
| Backend hosting | Supabase project (region ap-northeast-2, Postgres 17, status was *ACTIVE_HEALTHY* then *hibernated*, i.e. free-tier auto-pause). No Edge Functions, no scheduled jobs known |
| Environments | One only (production-like, hard-coded) |
| Observability | `print` only; no crash reporting/analytics; Supabase logs/advisors not reviewed (unreachable) |
| Backups | Unknown (Supabase plan dependent) |
| Build verification | **Not performed**: `xcodebuild` is unavailable (`xcode-select` points at CommandLineTools). Known probable compile error: `AuthViewModel.swift:154` |

## Commands
Verified to exist, **not executed**: `open parkezy/parkezy.xcodeproj` (Xcode) or `xcodebuild -project parkezy/parkezy.xcodeproj -scheme parkezy build` (scheme name inferred from target; no shared scheme file is committed — only `xcuserdata` scheme management was ignored). No test command exists.

## Operational risks
Free-tier project pause breaks the app; no staging DB; schema is not reproducible from the repo (R-01).
