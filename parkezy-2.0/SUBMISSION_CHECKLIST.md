# App Store Submission Checklist

[x] Old backend (Firebase + Django) fully removed
[x] Supabase connected and SQL schema created
[x] Auth flow works end-to-end (signup, login, logout, session restore, Apple Sign-In)
[x] Account deletion implemented
[x] Privacy policy link added
[x] All orphaned views deleted
[x] No mock data reachable from production UI
[x] All force unwraps fixed
[x] Empty/loading/error states on all list screens
[x] Offline handling in place
[x] Info.plist permissions match actual code usage (Pending developer manual review in Xcode)
[x] App Transport Security — HTTPS only
[x] Deployment target iOS 16.0
[ ] BLOCKER: App icon images missing — must be added before submission
[x] Entitlements cleaned (Pending developer manual review in Xcode)
[ ] Builds clean in Release scheme (Pending manual build run)
[ ] Remaining risks: 
    - The CLI environment lacked full Xcode access to run `xcodebuild archive`. The developer must verify the Archive build.
    - Info.plist generation (`GENERATE_INFOPLIST_FILE = YES`) requires setting descriptions like `NSCameraUsageDescription` within Xcode's "Info" tab.
[ ] Suggested v1.1 improvements: 
    - Full offline caching using SwiftData or CoreData.
    - Real-time live activities via Push Notifications rather than foreground simulated updates.
