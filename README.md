# 🧿 Darkelf Cocoa Browser [![PyPI Downloads](https://static.pepy.tech/personalized-badge/darkelf-cocoa?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/darkelf-cocoa)

## Darkelf Cocoa 7.0.24 — 2026

**Ephemeral • Privacy-First • Post-Quantum Integrity • Native macOS Cocoa**

Darkelf Cocoa is a privacy-focused macOS browser built with **PyObjC + WebKit**. It combines ephemeral browsing, per-tab isolation, fingerprinting defenses, content filtering, Post-Quantum integrity state, and the local **MiniAI Sentinel** security engine.

> **Current release:** 7.0.24  
> **Platform:** macOS  
> **Interface:** Native Cocoa / WebKit  
> **Distribution:** DMG

## ✨ What's New in 7.0.24

- Strengthened **per-tab ephemeral isolation** and container lifecycle management.
- Added deterministic cleanup of each tab's isolated WebKit data-store references when the tab closes.
- Unified tab identity around a persistent per-tab **UID + container nonce** for the lifetime of the tab.
- Improved cleanup of per-tab **Post-Quantum identity state** when tabs are destroyed.
- Improved isolated WebKit container bookkeeping to prevent stale container references after tab closure.
- Preserved independent ephemeral browsing identities between tabs.
- Updated the general compatibility identity to **Safari 27.0.1**.
- Preserved Darkelf's dedicated generic **WebKit identity for YouTube compatibility**.
- Expanded the **US-English locale preference** across HTTP/HTTPS main-frame navigation.
- Retained Google and YouTube US locale hints for improved regional consistency.
- Continued compatibility improvements for modern WebKit-dependent websites.

## 🔒 Per-Tab Ephemeral Isolation

Darkelf Cocoa uses a tab-oriented ephemeral browsing architecture.

Each tab maintains its own isolated identity and browsing context, including:

- Unique tab UID.
- Unique container nonce.
- Non-persistent WebKit website data store.
- Isolated WebKit process context.
- Per-tab Post-Quantum identity state.
- Per-tab fingerprint-defense state.

When a tab closes, Darkelf explicitly releases its associated container references, WebKit data-store reference, WebView, and ephemeral identity state.

This provides stable behavior during the lifetime of a tab while reducing persistent state and cross-tab correlation.

## 🛡️ Privacy & Security

Darkelf Cocoa includes:

- Ephemeral WebKit website data stores.
- Per-tab browsing/container isolation.
- Deterministic ephemeral container cleanup.
- Canvas, WebGL, WebGPU, and audio fingerprint defenses.
- Per-tab randomized fingerprint-defense state.
- WebRTC blocking.
- Media-device privacy controls.
- Battery, timezone, and locale normalization.
- Tracker and advertising-domain blocking.
- HTTP → HTTPS upgrading where applicable.
- Per-session and per-tab Post-Quantum integrity state.
- Local MiniAI behavioral security monitoring.
- Targeted compatibility handling for verification and challenge flows.
- No telemetry.

The Post-Quantum Integrity Layer supplements Darkelf's browser privacy and integrity mechanisms; it does **not** replace HTTPS/TLS.

## 🌐 WebKit Compatibility

Darkelf Cocoa uses site-aware WebKit compatibility handling.

General HTTP/HTTPS browsing uses a modern Safari-compatible identity:

`Version/27.0.1 Safari/605.1.15`

YouTube retains Darkelf's generic WebKit identity to preserve the browser's existing YouTube compatibility behavior.

Darkelf also advertises a global US-English language preference:

`en-US,en;q=0.9`

Google and YouTube additionally receive their respective US locale URL hints where applicable.

These compatibility mechanisms affect browser presentation and site behavior; they do not conceal the geographic location of the user's network connection.

## 🧠 MiniAI Sentinel

MiniAI operates locally and monitors signals including tracker activity, fingerprinting, suspicious requests, replay anomalies, scraping/enumeration behavior, and navigation risk.

## 🎨 Native Cocoa Interface

Darkelf Cocoa provides a native macOS interface with:

- Custom tab bar.
- Integrated URL/search field.
- Bookmarks.
- Keyboard shortcuts.
- Find bar.
- MiniAI report.
- Session nuke control.
- JavaScript control.
- Configurable accent colors.
- Nine configurable Darkelf Home backgrounds.
- Fullscreen support.

### Darkelf Home Backgrounds

Darkelf Cocoa includes:

- Darkelf Glow
- Midnight
- Aurora
- Nebula
- Carbon
- Pure Black
- Deep Ocean
- Crimson Eclipse
- Emerald Matrix

## ⌨️ Shortcuts

| Shortcut | Action |
|---|---|
| `⌘T` | New Tab |
| `⌘W` | Close Tab |
| `⌘R` | Reload |
| `⌘L` | Focus Address Bar |
| `⌘F` | Find in Page |
| `ESC` | Close Find Bar |
| `⌃⌘F` | Toggle Fullscreen |
| `⌘+` / `⌘-` | Zoom In / Out |
| `⇧⌘X` | Exit Darkelf |

## 📦 Distribution

Darkelf Cocoa **7.0.24** is distributed as a native **macOS DMG**.

Release builds should pass:

- Python compile checks.
- Lint and security analysis.
- macOS Developer ID code-signing verification.
- Apple notarization and stapling.
- Checksum verification.
- Browser compatibility testing.
- Privacy and fingerprinting testing.
- Per-tab isolation and cleanup testing.

## 📜 License

**LGPL-3.0-or-later**

© Dr. Kevin Moore (2025–2026)
