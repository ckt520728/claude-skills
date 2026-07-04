---
name: design-deploy-ios-app
description: Design a mobile app (Expo/React Native) and get it running on real iPhones/iPads — audience-first design, scaffold, quality gates, Expo Go device testing (with the SDK-version trap), and the EAS/TestFlight/App Store path. Distilled from the NeuroPlay 腦力訓練 project (2026-07). Use when the user wants to build an app for iPhone/iPad, test an Expo app on a physical device, or plan an App Store release.
---

# Design & Deploy an App to iPhone / iPad

Battle-tested workflow from shipping NeuroPlay v1.0 (elderly-focused
cognitive-training app) from empty folder to running on physical iPhones.

## Phase 1 — Design before code

1. **Audience decides the design system, not aesthetics.** Encode the
   audience as tokens in one file (`src/theme/tokens.ts`): tap-target
   minimum, smallest body size, contrast-checked palette. For elderly
   users: ≥64pt targets, ≥18pt text, WCAG-AA+. Every screen imports
   tokens; no raw hex/sizes in screens — this is what makes later
   appearance upgrades cheap.
2. **Data model first.** Decide what a "result" is before writing a
   screen (e.g. trial-level metrics, not one score). Put the domain
   guardrails in the types file's top comment so every future session
   sees them.
3. **One storage seam** (`src/storage/store.ts`): AsyncStorage native +
   localStorage web fallback. Screens never touch storage APIs directly.
4. If the domain is regulated/sensitive (health!), write the
   framing/wording guardrails into CLAUDE.md on day one — they must
   later extend to App Store metadata (Apple guideline 1.4 punishes
   diagnostic claims).

## Phase 2 — Scaffold

Stack: **Expo + expo-router + TypeScript strict**. One codebase covers
iPhone, iPad, Android, web.

⚠️ **Before picking the SDK version, check what Expo Go supports:**

```powershell
(Invoke-RestMethod https://api.expo.dev/v2/versions/latest).data.expoGoSdkVersion
```

The App Store Expo Go supports exactly ONE SDK. Scaffolding on a newer
SDK ⇒ "Project is incompatible with this version of Expo Go" on every
real phone, and the only fixes are downgrading the whole project or
paying for EAS dev builds. (NeuroPlay had to downgrade 57→54.)

`app.json` essentials for iPad: `"ios": {"supportsTablet": true,
"bundleIdentifier": "com.yourname.app"}`.

## Phase 3 — Quality gates (cheap, run constantly)

1. `npm run typecheck` (`tsc --noEmit`).
2. Headless render smoke test: start `npx expo start --web`, drive every
   route with Playwright, collect `console` errors — pass = all routes
   render, **zero console errors**. Catches runtime breaks typecheck
   can't. (Metro's "Error while reading cache… full crawl" warning is
   non-fatal; ignore it.)
3. Commit at every working milestone; tag releases (`v1.0.0`).

## Phase 4 — Real-device testing with Expo Go

- Same Wi-Fi: `npx expo start` → scan QR. Router blocks it (AP
  isolation)? → `npx expo start --tunnel` — works from ANY network,
  even cellular.
- Tunnel gotchas: put `@expo/ngrok` in devDependencies FIRST (the
  interactive install prompt kills non-interactive runs); "remote gone
  away"/"session closed" at startup is transient — **just retry**;
  tunnel URL readable from `http://127.0.0.1:4040/api/tunnels`.
- **"找不到可用資料" / camera does nothing on someone's phone** = that
  phone has no Expo Go installed; `exp://` scheme is only registered by
  the app. Install Expo Go → rescan → works.
- **The QR/URL is a pointer to your running dev server, not an app.**
  Saved QR photos die the moment the server stops. Anything "works
  without the dev PC" requires Phase 5.
- Generate a scannable QR yourself when the terminal one isn't visible:
  `npx`-install `qrcode`, render the `exp://` URL to SVG/HTML, open in
  browser, scan off the monitor.

## Phase 5 — Ship: EAS → TestFlight → App Store

Requires Apple Developer Program (US$99/yr). No Mac needed — EAS builds
in the cloud:

```
npm i -g eas-cli && eas login
eas build:configure
eas build --platform ios --profile production
eas submit --platform ios     # → App Store Connect → TestFlight testers
```

- EAS builds don't depend on Expo Go — this is the point where you can
  move back to the newest SDK.
- iPad screenshots are mandatory in App Store Connect when
  `supportsTablet` is on.
- Local-only data ⇒ App Privacy = "Data Not Collected" (strong selling
  point; keep it true).
- Health-adjacent apps: keep store name/subtitle/keywords/screenshots
  free of diagnostic claims; "training + trend tracking, see a
  clinician" framing passes where "detects Alzheimer's" gets rejected.

## Pitfall quick reference

| Symptom | Cause | Fix |
|---|---|---|
| "Project is incompatible with this version of Expo Go" | Project SDK ≠ Expo Go's single supported SDK | Check `expoGoSdkVersion` first; else downgrade: set package.json versions, delete node_modules + lockfile, clean install (running `expo install --fix` on a half-migrated tree throws ERESOLVE) |
| Phone can't reach dev server on same Wi-Fi | AP isolation / wired-vs-wireless split | `--tunnel` |
| "找不到可用資料" scanning QR | No Expo Go on that phone | Install Expo Go first |
| Saved QR stops working later | QR points at a dev server that's no longer running | Expected; use TestFlight for standalone use |
| Tunnel "remote gone away" at start | Transient ngrok hiccup | Retry once or twice |
| Tunnel prompt hangs headless runs | @expo/ngrok interactive install prompt | Pre-add to devDependencies |
| Tools installed with `npm --no-save` vanish | Next `npm install` prunes them | Save real dev tools to devDependencies |
| Timed metrics not comparable after difficulty changes | Timer starts at stimulus onset | Measure RT from response-unlock; record difficulty level per session |
