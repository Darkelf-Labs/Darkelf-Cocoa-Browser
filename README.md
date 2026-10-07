# 🧿 Darkelf Cocoa Browser [![PyPI Downloads](https://static.pepy.tech/personalized-badge/darkelf-cocoa?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/darkelf-cocoa)

## Darkelf Cocoa 7.0.23 — 2026

**Ephemeral • Privacy-First • Post-Quantum Integrity • Native macOS Cocoa**

Darkelf Cocoa is a privacy-focused macOS browser built with **PyObjC + WebKit**. It combines ephemeral browsing, first-party isolation, fingerprinting defenses, content filtering, Post-Quantum integrity state, and the local **MiniAI Sentinel** security engine.

> **Current release:** 7.0.23  
> **Platform:** macOS  
> **Interface:** Native Cocoa / WebKit  
> **Distribution:** DMG

## ✨ What's New in 7.0.23

- Added an integrated **Background** settings panel.
- Added nine Darkelf Home backgrounds: **Darkelf Glow, Midnight, Aurora, Nebula, Carbon, Pure Black, Deep Ocean, Crimson Eclipse, and Emerald Matrix**.
- Background selection now updates the Darkelf Home page immediately.
- Improved **Accent Color** navigation with an integrated in-panel selector.
- Refined menu panel sizing, navigation, and Back-button behavior.
- Fixed Background controls appearing in unrelated **MiniAI** and **About** views.
- Improved MiniAI report spacing and panel layout.
- Refined tab hover behavior to avoid obscuring tab titles.

## 🛡️ Privacy & Security

Darkelf Cocoa includes:

- Ephemeral WebKit website data stores.
- First-party and tab/container isolation.
- Canvas, WebGL, WebGPU, and audio fingerprint defenses.
- WebRTC blocking.
- Battery, timezone, and locale normalization.
- Tracker and advertising-domain blocking.
- HTTP → HTTPS upgrading where applicable.
- Per-session Post-Quantum integrity state.
- Local MiniAI behavioral security monitoring.
- Targeted compatibility handling for verification/challenge flows.
- No telemetry.

The Post-Quantum Integrity Layer supplements Darkelf's browser privacy and integrity mechanisms; it does **not** replace HTTPS/TLS.

## 🧠 MiniAI Sentinel

MiniAI operates locally and monitors signals including tracker activity, fingerprinting, suspicious requests, replay anomalies, scraping/enumeration behavior, and navigation risk.

## 🎨 Native Cocoa Interface

Darkelf Cocoa provides a native macOS interface with a custom tab bar, integrated URL/search field, bookmarks, keyboard shortcuts, Find bar, MiniAI report, session nuke control, JavaScript control, configurable accents, configurable backgrounds, and fullscreen support.

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

Darkelf Cocoa 7.0.23 is distributed as a native **macOS DMG**.

Release builds should pass Python compile checks, lint/security analysis, macOS code-signing verification, Apple notarization, checksum verification, browser compatibility testing, and privacy/fingerprinting testing.

## 📜 License

**LGPL-3.0-or-later**

© Dr. Kevin Moore (2025–2026)
