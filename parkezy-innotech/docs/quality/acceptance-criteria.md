# Acceptance Criteria (rebuild)

Global definition of done for any milestone: builds clean on CI; unit + RLS tests green; no new `print` logging; accessibility labels on interactive elements; docs updated; no secrets committed.

| Req | Acceptance criteria |
|---|---|
| Auth (F-01–F-07) | A user can sign up/in/out with email and Apple; sessions persist across launches; signing out clears all in-memory data; password reset completes via deep link; delete-account removes the auth identity and personal data, verified by a test (T-05) |
| Discovery (F-20–F-22) | Map loads only viewport-relevant supply with loading/empty/error states; search re-centers and re-queries; EV/type/price filters work server-side |
| Commercial booking (F-24) | Price is computed server-side and equals the displayed total; concurrent bookings of one slot cannot both succeed (T-12); driver sees the booking in "My bookings" and can cancel per policy; access QR/code is server-signed |
| Private booking (F-26, F-44) | Driver request → host notification → approve/reject → driver sees result; auto-accept path is instant; PIN visible to driver only after approval |
| Access control (F-46) | Host scan validates entry/exit against the server; replayed/forged/expired tokens are rejected (T-21); state change persisted |
| Host listings (F-41–F-43) | Photos/video upload to storage with progress/retry; listing validates per BR rules; owner can edit/delete own listings only (T-31) |
| Host analytics (F-40, F-48) | Earnings equal sum of `host_earnings` of completed bookings (after platform fee), no random data |
| Payments (new) | Payment intent created server-side; booking confirmed only after provider confirmation webhook; refunds per policy |
| Security | All RLS tests T-30..T-32 pass; no client-writable privileged columns; secrets not in repo |
| Platform | Live Activity/widget run from real extension targets (if retained, Q-05); notifications permission requested in context |
| Quality | ≥ 80% unit coverage of pricing/validation/state logic; UI tests cover J-01, J-02, J-03/J-08, J-04 |
