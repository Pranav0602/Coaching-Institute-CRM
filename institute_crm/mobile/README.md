# Graphix Techno CRM — Mobile

React Native (Expo SDK 57) client for the Django REST backend in
`institute_crm/`. Same data, same permissions, same brand — with the things a
handset can do that a browser cannot: push notifications, camera QR scanning,
one-tap WhatsApp, biometric unlock and offline caching.

---

## Running it

```bash
cd institute_crm/mobile
npm install

# Point the app at a backend. Physical handsets need the machine's LAN IP.
#   Android emulator  ->  http://10.0.2.2:8000/api/v1
#   iOS simulator     ->  http://127.0.0.1:8000/api/v1
#   Real device       ->  http://192.168.x.x:8000/api/v1   (backend must bind 0.0.0.0)
$env:EXPO_PUBLIC_API_BASE_URL = "http://10.0.2.2:8000/api/v1"

npm start          # then press a / i / w
npm run android    # or launch directly
npm run ios
npm run web
```

`EXPO_PUBLIC_API_BASE_URL` is inlined at build time by Metro, so it must be set
before `npm start`, not after. Unset, the app targets
`https://coaching-institute-crm.onrender.com/api/v1`.

### Verifying a change

```bash
npm run typecheck              # tsc --noEmit, strict
npm run export                 # metro production bundle (catches missing imports)
npm run check:api              # wire-format + live contract checks
```

`check:api` pins down the two things that fail *silently* in this app: the
envelope unwrap level, and which endpoints are allowed to trigger a token
refresh. Its offline assertions always run; the live ones (login, `/auth/me/`,
refresh rotation, a wrong password, counselor read-only scope) run only when a
backend answers at `/healthz/`. Set `API_BASE_URL` to point it elsewhere.

There is no unit-test runner configured yet. `typecheck` + `export` +
`check:api` is the current gate; Jest + `@testing-library/react-native` is the
natural next step.

### If sign-in "does nothing"

Almost always one of two things, both now visible on the login screen:

1. **The app is pointed at a different database than your credentials.** The login
   screen prints the API host under the error banner. The seeded accounts
   (`counselor` / `Admin@123`) exist only in your *local* Postgres — if the host
   reads `coaching-institute-crm.onrender.com`, you are authenticating against
   production and the credentials cannot possibly match. Set
   `EXPO_PUBLIC_API_BASE_URL` before `npm start`.
2. **A 401 on `/auth/login/` means bad credentials, not an expired session.** The
   response interceptor deliberately excludes the login and password-reset
   endpoints from the refresh-and-retry path, so a wrong password produces a
   message and never silently signs you out of another account.

---

## Backend endpoints this app added

All three are in the plan's section 6, plus one the plan implied but did not name.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/accounts/auth/token/refresh/` | Exchange a refresh token for a new pair. Rotates, and blacklists the token it replaces. |
| `POST /api/v1/accounts/auth/logout/` | Retire the current refresh token. Sign-out is only meaningful because the previous endpoint can rotate. |
| `POST /api/v1/communications/devices/register/` | Bind an Expo push token to the signed-in user. Idempotent; re-registering a token that changed hands reassigns it. |
| `POST /api/v1/communications/devices/{id}/unregister/` | Retire one handset. Scoped to its owner. |
| `POST /api/v1/communications/devices/unregister-all/` | Retire every handset for a user. Called on sign-out so a shared device stops delivering the previous user's alerts. |
| `GET /api/v1/profiles/students/{id}/id-card/` | Everything needed to render or print one ID card, including `qr_payload`. |
| `POST /api/v1/profiles/students/resolve-qr/` | Turn a scanned `graphix://student/<enrollment_no>` into a student record. Staff roles only, branch-scoped. |

`POST /auth/login/` and `GET /auth/me/` additionally return
`access_expires_in` / `refresh_expires_in`, so the client refreshes on a schedule
instead of discovering expiry by eating a visible 401.

**`SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"]` is now `True`** and
`rest_framework_simplejwt.token_blacklist` is installed. Rotating without
blacklisting leaves every superseded refresh token valid forever, which matters
much more now that a mobile session is long-lived by design.

---

## Structure

```
app/                              # Expo Router. Routes only; logic lives in src/.
  _layout.tsx                     # fonts, theme, query cache, session provider
  index.tsx                       # splash, then redirect by role
  (auth)/                         # login, forgot-password
  (app)/
    _layout.tsx                   # session guard + biometric gate
    counsellor/ teacher/ student/ parent/ admin/ accountant/ reception/
      _layout.tsx                 # each declares its own Tabs, delegating chrome
      <tabs>.tsx                  # to PersonaTabs
    assistant.tsx profile.tsx syllabus.tsx new-lead.tsx
    lead/[id].tsx attendance/[lectureId].tsx
src/
  api/
    client.ts                     # axios + SecureStore, 401 refresh replay, envelope
    storage.ts                    # Keychain/Keystore tokens vs AsyncStorage cache
    academics.api.ts domain.api.ts
  components/common/              # Screen, Layout, Primitives, SearchBar
  components/leads/               # LeadCard
  constants/                      # config, roles, theme (brand tokens)
  context/                        # AuthContext, ThemeContext
  hooks/                          # useDebounced, useNetworkStatus, useAsync,
                                  # usePushRegistration
  navigation/PersonaTabs.tsx      # tab config for all seven shells
  screens/MoreScreen.tsx          # shared settings tab
  theme/PaperIcon.tsx
  types/index.ts                  # DRF response shapes
  utils/                          # format, linking, counselling
```

### Why the settings screen is not duplicated

All seven persona shells end with a "More" tab, and what a user can change about
their own account does not depend on their job. Each persona's `more.tsx` is a
one-line re-export of `src/screens/MoreScreen.tsx`. Seven copies would drift.

### Why a shared API client

`src/api/client.ts` owns the `{ success, message, data }` envelope, the bearer
token, and the refresh-on-401 replay. Two details worth knowing:

* **Refresh is de-duplicated.** Four queries failing at once produce one rotation,
  not four. With rotation on, four concurrent refreshes would invalidate each
  other's tokens and sign the user out.
* **Refresh is proactive.** The login response reports `access_expires_in`, and
  the request interceptor refreshes 60s before expiry rather than after a 401.

---

## Deviations from the plan, and why

**NativeWind was dropped.** The plan specified React Native Paper *plus* NativeWind
v4. Two styling systems layered on the same views double the Babel/Metro transform
surface for no functional gain — Paper already provides MD3 components and full
theming, which is the entire reason the plan chose it. NativeWind v4 on RN 0.86 +
New Architecture is also not a combination that is guaranteed to build. Styling is
Paper theme tokens and `StyleSheet`. If utility classes are wanted later, add
NativeWind as the *only* system rather than alongside Paper.

**Five persona shells, not eight.** Super Admin and Branch Admin see the same
screens, so they share one shell (`src/constants/navigation.ts`). Splitting them
would duplicate navigation code to produce identical UI.

**The RAG assistant is a full screen, not a bottom sheet.** The plan specified
`@gorhom/bottom-sheet`, but the answers are long (module lists, fee tables, refund
policy) and a sheet fights the keyboard on a phone. The FAB opens
`/(app)/assistant`, and the bottom-sheet dependency was removed rather than left
installed-but-unused.

**Markdown is split, not parsed.** The syllabus documents have a known, narrow
`##`/`-` shape, so `app/(app)/syllabus.tsx` splits on `^##` and renders sections
as text. A markdown library is ~40KB for a format we control.

**Fonts are imported per weight.** The root of `@expo-google-fonts/plus-jakarta-sans`
re-exports 14 faces (every weight plus every italic). `app/_layout.tsx` imports the
five weights actually used via their per-weight subpaths, saving ~1MB of typeface.

**Dependency versions are pinned to what Expo Go bundles.** This is not optional.
Expo Go ships a fixed set of native module versions; a JS package that expects a
different one has no matching native module and fails at the bridge with
`Native module is null`. Run `npx expo install --check` after any dependency
change — it prints the version Expo expects for this SDK. Unused native packages
(`@shopify/flash-list`, `@gorhom/bottom-sheet`, `expo-sharing`, `expo-file-system`)
were removed rather than carried, precisely to shrink that surface.

**`expo-notifications` is loaded with a runtime `require`, not a top-level import.**
It throws on import inside Expo Go on Android (remote push was removed at SDK 53),
and a throw at module scope takes down every screen that transitively imports it.
`src/hooks/usePushRegistration.ts` checks the runtime first and returns
`needs-dev-build` instead.

**Route files must contain a real `export default`.** Expo Router builds its route
manifest with a Babel pass that does not see `export { default } from '...'`. The
seven `more.tsx` files import the shared screen and then `export default` it.

---

## What is not built yet

* **Push delivery on the server side.** `DeviceToken` and the register endpoint
  exist and the app registers on every cold start, but nothing yet *sends* through
  Expo's push service. `Communications.send_batch_notification` still only creates
  in-app rows, email and SMS. A dispatcher that fans an out to
  `ExponentPushToken` handles is the missing piece.
* **Assignment submission from a camera.** `Submission.file_url` is a `URLField`,
  not a `FileField`, so there is no multipart upload to post a photo to — the
  client would need somewhere to PUT the file first (S3 presigned, or a new
  endpoint). The plan's "upload homework photo" is not achievable without that.
* **Receipt PDFs.** `Receipt.pdf_url` is a constructed S3 path written as a literal
  string by `FinanceService.record_payment`; no PDF is ever generated. The Fees
  screen opens the link when present and disables the button when it is not, but
  nothing is at the other end.
* **Offline attendance queue.** `useNetworkStatus` shows a banner and TanStack
  Query serves its cache, but marking attendance in a basement still needs a
  connection. Queuing marks and replaying them is not implemented.
* **App store assets.** `assets/` still holds the Expo template icons.
