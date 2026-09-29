This is an Expo/React Native mobile application. Prioritize mobile-first patterns, performance, and cross-platform compatibility.

## Expo has changed — do not trust your training data

Expo ships breaking changes every SDK release. APIs you remember are likely renamed, moved, or removed. Before writing any code that touches an Expo, EAS, or React Native API:

1. Read the major version of the `expo` package in `package.json`.
2. Fetch the matching versioned docs: `https://docs.expo.dev/versions/v<major>.0.0/`
3. For anything else, fetch https://docs.expo.dev/llms.txt — an index of all Expo docs with corrections to common LLM misconceptions. Follow its links to the specific page you need; never answer from memory.

## Commands

Use `bunx` instead of `npx` if the project uses bun (`bun.lock` present).

```bash
npx expo install <package>  # ALWAYS use instead of npm/yarn/pnpm/bun add — resolves SDK-compatible versions
npx expo start              # start the dev server
npx tsc --noEmit            # typecheck  (this is the real gate; there is no lint script)
npx expo export --platform web --output-dir dist   # production bundle — catches missing imports
npx expo-doctor             # diagnose dependency and config issues
npx expo install --fix      # fix incompatible package versions
```

Run `npx tsc --noEmit` and `npx expo export` before declaring any task done. A
successful typecheck alone does not prove the route tree is reachable.

## Native dependency versions

Expo Go ships a fixed set of native module versions. A JS package built for a
different version has no matching native module and fails at the bridge with
`Native module is null, cannot access legacy storage` — which looks like an app
bug but is a version mismatch. After any `npm install`, run:

```bash
npx expo install --check
```

Install what it reports with `npx expo install <pkg>`, never `npm install <pkg>`.
Do not add a native package unless the app actually uses it: every unused one is
another version that has to stay matched.

## Navigation & Routing

- Use **Expo Router** for all navigation. Routes live in `app/` at the project
  root (not `src/app/`) — every file there is a screen, `_layout.tsx` files define
  navigators. Keep non-route code (components, hooks, utils) in `src/`.
- `package.json` `main` must stay `expo-router/entry`. If it points anywhere
  else, the entire `app/` tree is silently ignored and the app boots whatever
  `App.tsx` happens to contain.
- Import `Link`, `router`, and `useLocalSearchParams` from `expo-router`.
- Docs: https://docs.expo.dev/router/introduction.md

## Icons

Lucide is the icon system. Paper components that take a string icon name go
through `src/theme/PaperIcon.tsx`, which maps those names to Lucide. Pass a
component (`icon={Camera}`) rather than a string wherever possible.

## Building with EAS

Use EAS to build, sign, and submit the app in the cloud (`eas build`, `eas submit`) and to ship over-the-air updates (`eas update`) — no local Xcode or Android Studio required. Run EAS CLI as `bunx eas-cli <command>` in Bun projects, or `npx eas-cli@latest <command>` otherwise; substitute that for bare `eas` in docs examples.
Docs: https://docs.expo.dev/eas/index.md

## Rules

- If `ios/` and `android/` directories do not exist, they are generated (Continuous Native Generation). Never create or edit them by hand — configure native behavior in `app.json` and config plugins.
- Expo Go only includes its bundled native modules. After adding a library with native code, the app needs a development build: `npx expo run:ios|android` locally, or `eas build --profile development`.
- Prefer recommended Expo modules over third-party libraries, and check your available skills before adding dependencies. Docs: https://docs.expo.dev/versions/latest/index.md
