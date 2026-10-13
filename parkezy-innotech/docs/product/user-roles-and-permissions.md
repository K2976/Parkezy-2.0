# User Roles and Permissions

## Role model in code
`AppUser` (`Backend/AppUser.swift`, table `profiles`) carries `capabilities { canDrive, canHostPrivate, canHostCommercial }` and `stats { totalBookingsAsDriver, hostRating?, totalEarnings? }`.

| Concept | Where defined | Enforced? |
|---|---|---|
| Driver | `capabilities.canDrive` | **No** — nothing reads it |
| Private host | `capabilities.canHostPrivate` | **No** — Host Mode is open to everyone via `RoleSelectionView` |
| Commercial host | `capabilities.canHostCommercial` | **No** — and no commercial hosting UI exists (F-49) |
| App "mode" (Driver/Host) | `RoleSelectionView.selectedRole` (`UserRole`) | UI navigation only, not persisted |
| Platform admin / support | — | Absent. Disputes (`disputes` table) have no review UI |

Effective permissions today = whatever Supabase RLS allows. The historical DDL (`git show e72c855:supabase_schema.sql`) shows: `profiles` readable by **everyone**, own-row update with no column restriction (so capabilities are self-grantable); listings/facilities writable by their `owner_id` with no capability check; bookings visible only to the booking's `user_id`. Live policies are unverified (DB unreachable) and three tables have no DDL. The client is the only place roles are "checked", and it does not check them.

## Client-visible permission matrix (what the UI lets a signed-in user do)
| Action | Any user | Notes |
|---|---|---|
| Browse all facilities/listings | Yes | `select()` with no filter |
| Create commercial booking | Yes | `driverID` falls back to a random `UUID()` if no session (`CommercialParkingViewModel.bookSlot`) |
| Create/edit private listing | Yes | Owner resolved from `currentUser?.id` → else `myListings.first?.ownerID` → else random `UUID()` |
| Edit/delete another user's listing | Not exposed in UI | Owner view is detected client-side (`isOwnerView`); historical DDL enforces `owner_id = auth.uid()` (live unverified) |
| Approve private booking | Nobody (no UI) | F-44 |
| Self-grant host capability | **Possible** per historical DDL: `profiles` UPDATE policy has no `WITH CHECK`/column limit | SEC-02 |

## OS-level permissions the code needs
| Permission | Used by | Declared? |
|---|---|---|
| Location When-In-Use | map `UserAnnotation`, `LocationManager`, add-listing location | Not declared (no `INFOPLIST_KEY_NSLocation…` in `project.pbxproj`) |
| Camera | `QRScannerView` (VisionKit, currently unreachable). `MediaStepView` capture is simulated and uses no camera | Not declared (`NSCameraUsageDescription` absent) → crash on first real use (BUG-03, latent until the scanner is wired) |
| Microphone | none today | Not declared |
| Photo library | `NSPhotoLibraryUsageDescription` referenced in docs | Not declared |
| Notifications | `NotificationManager` | Requested nowhere |
| Sign in with Apple | `AuthenticationView` | No entitlements file |

## Rebuild requirements
- Persist role/capabilities **server-side only**; clients may *request* host onboarding, a server function (or admin) grants it. See [ADR-002](../decisions/README.md).
- Ownership checks (`owner_id = auth.uid()`) in RLS for every host-writable table.
- Add an admin/support role for dispute handling (decision Q-06).
