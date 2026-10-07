# 🧿 Darkelf Cocoa Browser [![PyPI Downloads](https://static.pepy.tech/personalized-badge/darkelf-cocoa?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/darkelf-cocoa)

## Darkelf Cocoa 7.0.22 — 2026

### Ephemeral • Privacy-First • Post-Quantum Integrity • Native macOS Cocoa

Darkelf Cocoa is a privacy-focused macOS browser built with **PyObjC + WebKit**. It combines ephemeral browsing, first-party isolation, deterministic privacy defenses, a Post-Quantum Integrity Layer (PQ), content filtering, and the on-device **MiniAI Sentinel** security engine.

> **Current release:** 7.0.22  
> **Platform:** macOS  
> **Interface:** Native Cocoa / WebKit  
> **Release year:** 2026

---

## ✨ What's New in 7.0.22

### 🌐 Compatibility

- Improved Cloudflare and verification-flow compatibility.
- FshareTV verification now works without disabling Darkelf's normal first-party defenses.
- Improved **EFF Cover Your Tracks** compatibility so its fingerprinting test can complete normally.
- Verification/challenge frames receive narrowly scoped compatibility handling instead of globally weakening browser protections.
- Refined site compatibility while retaining Darkelf's ephemeral architecture.

### 🎯 Content Rules 15.04

- Updated the WebKit content-rule engine to **15.04**.
- Improved compatibility-focused rule handling.
- Anti-adblock subscription remains disabled to reduce challenge and verification breakage.
- Network-level ad/tracker blocking remains active.
- Cosmetic filtering is handled conservatively to reduce page-layout regressions.
- Added CNN-safe cosmetic-filter handling while preserving network blocking.

### 🎨 Cocoa Interface & Accent Handling

- Removed legacy forced-green native Cocoa accent behavior.
- Darkelf's selected accent now propagates across its custom interface.
- Tabs, URL bar, borders, icons, menu elements, and the Darkelf home page follow the selected Darkelf accent.
- Native macOS controls respect the user's actual macOS system accent.
- Custom Darkelf theming no longer permanently overrides the user's system Accent Color.
- Improved theme refresh behavior during live accent changes.

### 🛡️ Fingerprint & Browser Defenses

Darkelf retains its unified privacy-defense layer for normal browsing, including:

- Canvas readback protection and deterministic noise.
- WebGL parameter/readback protection.
- WebGPU adapter, limit, and mapped-buffer defenses.
- Audio fingerprint perturbation.
- WebRTC hard blocking.
- Battery API normalization.
- Timezone and locale normalization.
- PQ-linked deterministic entropy.
- Per-origin and per-tab privacy state.
- Compatibility guards for verification/challenge contexts.

---

## 🔐 Post-Quantum Integrity Layer

Darkelf's PQ layer maintains stateful integrity information during browsing.

Core components include:

- Per-session cryptographic seed.
- Hidden session salt.
- Per-tab identity state.
- Stateful request chaining.
- Replay-anomaly detection.
- Deterministic privacy seeds derived from PQ state.
- Isolation between browsing contexts.

The PQ system is designed as an integrity and privacy mechanism inside Darkelf; it does not replace HTTPS/TLS.

---

## 🕶️ Ephemeral Browsing

Darkelf is designed around nonpersistent browsing sessions.

- Nonpersistent WebKit website data stores.
- First-party isolation.
- Tab/container isolation.
- No intentional cross-session browsing identity.
- Controlled user-initiated downloads.
- Session cleanup on exit.
- Reduced persistent browser state.

---

## 🧠 MiniAI Sentinel

MiniAI Sentinel is Darkelf's local behavioral security engine.

It monitors browser activity for signals such as:

- Tracker activity.
- Fingerprinting behavior.
- Suspicious request patterns.
- Replay anomalies.
- Scraping/enumeration behavior.
- Elevated navigation risk.

MiniAI works locally with Darkelf's network and PQ systems and does not require telemetry to provide its browser-side detection functions.

---

## 🛡️ Network Policy Engine

Darkelf's network layer provides:

- HTTP → HTTPS upgrading where applicable.
- Tracker/domain blocking.
- Adaptive trust handling.
- PQ-aware request state.
- Controlled download handling.
- MiniAI integration.
- Compatibility handling for verification services.

When suspicious behavior is detected, Darkelf can reduce trust and restrict selected capabilities rather than immediately breaking the browsing session.

---

## ⬇️ Downloads

Downloads are user initiated and policy controlled.

- No intentional silent background downloads.
- Manual save workflow.
- Temporary download handling.
- Filename sanitization/randomization where applicable.
- Risk-aware handling through the network/security layer.

---

## 🎨 Darkelf Interface

Darkelf Cocoa uses a native macOS interface with:

- Native Cocoa window and controls.
- Custom tab bar.
- Integrated URL/search field.
- Darkelf Home page.
- Configurable Darkelf accent colors.
- Bookmarks.
- Keyboard shortcuts.
- Movable Find bar.
- MiniAI report.
- Session nuke control.
- JavaScript control.
- Fullscreen support.

Darkelf's custom accent and the user's native macOS Accent Color are intentionally treated separately where macOS controls require the system appearance.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `⌘T` | New Tab |
| `⌘W` | Close Tab |
| `⌘R` | Reload |
| `⌘L` | Focus Address Bar |
| `⌘F` | Find in Page |
| `ESC` | Close Find Bar |
| `⌃⌘F` | Toggle Fullscreen |
| `⌘+` | Zoom In |
| `⌘-` | Zoom Out |
| `⇧⌘X` | Exit Darkelf |

---

## 🧩 Architecture

Darkelf Cocoa is organized into dedicated modules for:

- Application lifecycle and native Cocoa UI.
- WebKit content rules.
- Network policy.
- First-party isolation.
- Post-Quantum integrity state.
- MiniAI Sentinel.
- Fingerprint/privacy defenses.
- Spoofing and compatibility handling.
- Downloads.
- Tabs and delegates.
- Theme and branding.
- Internal Darkelf pages.

This modular architecture keeps browser UI, privacy policy, network enforcement, and security analysis separated.

---

## 🔏 Privacy Principles

Darkelf 7.0.22 is built around these principles:

- Ephemeral by default.
- No telemetry.
- No persistent cross-session browser identity by design.
- First-party isolation.
- Per-tab privacy state.
- Tracker and advertising-domain blocking.
- Fingerprint-surface hardening.
- WebRTC leakage prevention.
- Narrow compatibility exceptions instead of globally disabling protections.
- User-controlled data egress.

---

## 📦 Distribution

Darkelf Cocoa 7.0.22 is distributed as a native **macOS DMG** release.

The release source is prepared for the current native Cocoa/DMG distribution workflow.

---

## 🧪 7.0.22 Release Validation

Before publishing a release build, the project should be checked with:

- Python syntax/compile checks.
- Ruff linting.
- Bandit security analysis.
- GitHub CodeQL analysis.
- macOS code signing verification.
- Apple notarization verification.
- DMG checksum verification.
- Browser compatibility tests.
- Privacy/fingerprinting tests.

---

## ⚠️ Compatibility Notes

Privacy hardening can conflict with websites that rely on exact browser fingerprint, layout, media, or verification behavior. Darkelf 7.0.22 uses targeted compatibility handling where possible rather than disabling privacy protections globally.

CNN currently has a known top-header/layout compatibility issue under investigation. Network-level filtering and the broader browser privacy stack remain enabled.

---

## 📜 License

**LGPL-3.0-or-later**

© Dr. Kevin Moore (2025–2026)
