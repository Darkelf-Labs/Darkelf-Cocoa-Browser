
# 🛡️ Darkelf Cocoa Browser

[![PyPI Downloads](https://static.pepy.tech/personalized-badge/darkelf-cocoa?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/darkelf-cocoa)

## Darkelf Cocoa 7.0.25 — 2026

**Ephemeral • Privacy-First • Post-Quantum Integrity • Native macOS Cocoa**

Darkelf Cocoa is a privacy-focused macOS browser built with **PyObjC + Apple WebKit**. It combines ephemeral browsing, per-tab isolation, fingerprinting defenses, content filtering, Post-Quantum integrity state, and the local **MiniAI Sentinel** security engine.

Designed for users who prefer a lightweight, native browser experience, Darkelf Cocoa provides advanced privacy protections without the complexity of a traditional browser settings interface.

> **Current release:** 7.0.25  
> **Platform:** macOS  
> **Browser engine:** Apple WebKit (WKWebView)  
> **Interface:** Native Cocoa / PyObjC  
> **Distribution:** DMG  
> **License:** LGPL-3.0-or-later

---

## ✨ What's New in 7.0.25

Version **7.0.25** focuses on native interface refinements, improved menu usability, privacy transparency, and expanded personalization while preserving Darkelf's existing security architecture.

### 🛡️ New Privacy & Security Interface

- Added a dedicated **Privacy & Security** section to the native Cocoa menu.
- Introduced three organized privacy information submenus:
  - **Privacy Protection**
  - **Website Exceptions**
  - **Site Permissions**
- Added a read-only display of the current **Strict** protection configuration.
- Added clear information about tracker blocking, fingerprint defenses, WebRTC restrictions, and ephemeral tab isolation.
- Added visibility into the browser's current website-exception capabilities.
- Added read-only site-permission information for WebRTC, camera, microphone, location, and notifications.
- Preserved existing default-deny media-capture behavior.
- Preserved WebRTC blocking without introducing user-facing override switches.
- Improved submenu navigation and Back-button behavior.
- Prevented Privacy & Security menu items from appearing in unrelated panels.

**Privacy & Security is informational in 7.0.25.** Standard/Strict switching, configurable website exceptions, and permission overrides are not exposed.

### 🎨 Expanded Appearance Customization

- Expanded the accent-color collection to **12 selectable colors**.
- Added **Arctic Frost**, bringing the Darkelf Home background collection to **10 presets**.
- Improved accent and background selection layouts.
- Preserved the native dark interface and color-coordinated menu appearance.
- Improved visual consistency between customization panels.

### 🖥️ Native Cocoa Menu Redesign

- Standardized the menu system around a **280 × 400-point panel**.
- Increased menu typography for improved readability.
- Improved spacing, alignment, and visual hierarchy.
- Refined the Privacy Protection panel's headings and status descriptions.
- Adjusted the Strict protection label to better match surrounding typography.
- Improved the MiniAI information panel with more consistent label/value alignment.
- Refined Keyboard Shortcuts category placement and expanded-content presentation.
- Improved Bookmarks list positioning and row alignment.
- Refined the About Darkelf panel with an expanded browser description and updated copyright information.
- Preserved the lightweight, integrated native macOS menu experience.

### 🔖 Bookmarks Improvements

- Adjusted bookmark positioning so saved items appear near the top of the panel.
- Improved bookmark row spacing and label readability.
- Refined bookmark removal-button alignment.
- Improved use of the expanded menu width.

### 🧠 MiniAI Interface Improvements

- Refined MiniAI Sentinel status presentation.
- Improved the alignment of security metrics and their values.
- Updated typography for better consistency with other Cocoa submenus.
- Preserved the existing local monitoring architecture.

### 🔐 Security and Compatibility Preservation

- Retained per-tab ephemeral WebKit browsing contexts.
- Retained deterministic isolated-container cleanup.
- Preserved fingerprinting-defense scripts and tracker filtering.
- Preserved WebRTC restrictions and media-capture denial.
- Preserved the existing Post-Quantum integrity state management.
- Maintained the browser's site-aware Safari/WebKit compatibility behavior.

---

## 🔒 Per-Tab Ephemeral Isolation

Darkelf Cocoa uses a tab-oriented ephemeral browsing architecture designed to reduce persistent browsing state and cross-tab correlation.

Each tab maintains its own browsing identity and context, including:

- Unique tab UID.
- Unique container nonce.
- Non-persistent WebKit website data store.
- Isolated WebKit process context.
- Per-tab Post-Quantum identity state.
- Per-tab fingerprint-defense state.

When a tab closes, Darkelf explicitly releases associated container references, WebKit data-store references, WebViews, and ephemeral identity state.

The browser maintains stable tab identity during each tab's lifetime while reducing unnecessary state retention after closure.

---

## 🛡️ Privacy & Security

Darkelf Cocoa includes multiple layers of privacy protection:

- Ephemeral WebKit website data stores.
- Per-tab browsing and container isolation.
- Deterministic ephemeral container cleanup.
- Canvas fingerprinting defenses.
- WebGL and WebGPU fingerprinting protections.
- Audio fingerprinting defenses.
- Per-tab randomized fingerprint-defense state.
- WebRTC blocking.
- Media-device privacy restrictions.
- Battery, timezone, and locale normalization.
- Tracker and advertising-domain blocking.
- WebKit content-rule filtering.
- HTTP-to-HTTPS upgrading where applicable.
- Per-session and per-tab Post-Quantum integrity state.
- Local MiniAI behavioral security monitoring.
- Targeted compatibility handling for website verification and challenge flows.
- No browser telemetry.

The **Post-Quantum Integrity Layer** supplements Darkelf's browser privacy and integrity mechanisms. It does **not** replace HTTPS/TLS or independently establish post-quantum-secure network connections.

### Privacy Protection Status

The native Privacy Protection submenu displays the current built-in security configuration.

| Protection | Current configuration |
|---|---|
| Privacy level | Strict |
| Tracker blocking | WebKit content rules |
| Fingerprint defenses | Built-in script protections |
| WebRTC | Blocked by Darkelf policy |
| Tab isolation | Ephemeral browsing |
| Website exceptions | No user-configurable overrides |
| Media capture | Denied by browser delegate |

These displays are read-only and do not modify the browser's underlying security policies.

### Site Permissions

The Site Permissions submenu provides an informational overview of the browser's current permission handling.

- **WebRTC:** Blocked by Darkelf policy.
- **Camera and microphone:** Media-capture requests denied by the existing delegate.
- **Location:** No user-facing permission switch.
- **Notifications:** No user-facing permission switch.

The absence of a permission switch is not a guarantee that every underlying WebKit API is unavailable. The panel reports the controls and restrictions implemented by Darkelf.

---

## 🌐 WebKit Compatibility

Darkelf Cocoa uses site-aware WebKit compatibility handling.

General HTTP/HTTPS browsing uses a Safari-compatible user-agent identity:

`Version/27.0.1 Safari/605.1.15`

YouTube retains Darkelf's generic WebKit identity to preserve the browser's established YouTube compatibility behavior.

Darkelf also advertises a US-English language preference:

`en-US,en;q=0.9`

Google and YouTube additionally receive US locale URL hints where applicable.

These mechanisms affect browser presentation and website compatibility. They do not conceal the geographic location of the user's network connection or guarantee identical behavior to Safari.

---

## 🧠 MiniAI Sentinel

MiniAI Sentinel is Darkelf's local behavioral security-monitoring component.

It observes signals including:

- Tracker activity.
- Fingerprinting attempts.
- Suspicious network requests.
- Replay anomalies.
- Scraping and enumeration behavior.
- Navigation risk.
- HTTP blocking activity.
- Intrusion-related indicators.
- Post-Quantum identity state.

The native MiniAI panel presents available session metrics and security indicators without requiring a separate browser extension.

Version 7.0.25 refines the MiniAI panel's typography, metric alignment, and overall presentation.

---

## 🎨 Native Cocoa Interface

Darkelf Cocoa provides a native macOS interface with:

- Custom tab bar.
- Integrated URL and search field.
- Bookmarks management.
- Keyboard shortcuts.
- Find-in-page bar.
- MiniAI Sentinel report.
- Session nuke control.
- JavaScript control.
- Privacy & Security information panels.
- Configurable accent colors.
- Ten Darkelf Home background presets.
- Fullscreen support.
- Native Cocoa navigation and menu controls.

### Accent Colors

Darkelf Cocoa includes 12 accent-color options:

1. Green
2. Blue
3. Purple
4. Orange
5. Red
6. Teal
7. Cyan
8. Gold
9. Pink
10. Magenta
11. Amber
12. Silver

### Darkelf Home Backgrounds

Darkelf Cocoa includes 10 background presets:

1. Darkelf Glow
2. Midnight
3. Aurora
4. Nebula
5. Carbon
6. Pure Black
7. Deep Ocean
8. Crimson Eclipse
9. Emerald Matrix
10. Arctic Frost

The appearance system combines native Cocoa controls with customizable Darkelf Home styling.

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
| `⌘+` / `⌘-` | Zoom In / Out |
| `⇧⌘X` | Exit Darkelf |

The Keyboard Shortcuts panel organizes available commands into Navigation, Tabs, Zoom, and Application categories.

---

## 📦 Distribution

Darkelf Cocoa **7.0.25** is distributed as a native macOS DMG.

**Release artifact:**

`Darkelf-Cocoa-7.0.25.dmg`

**Checksum artifact:**

`Darkelf-Cocoa-7.0.25.dmg.sha256`

Release builds should pass:

- Python syntax compilation.
- Lint and security analysis.
- macOS Developer ID code-signing verification.
- Apple notarization and stapling.
- SHA-256 checksum verification.
- Browser compatibility testing.
- Privacy and fingerprinting testing.
- Per-tab isolation and cleanup testing.
- Native Cocoa menu layout and navigation testing.
- MiniAI, Bookmarks, and Keyboard Shortcuts functionality testing.

### Installation

1. Download the latest Darkelf Cocoa DMG from the project's GitHub Releases page.
2. Open the DMG.
3. Drag Darkelf Cocoa into Applications.
4. Launch the application on a supported macOS system.

---

## 📜 License

**LGPL-3.0-or-later**

Darkelf Cocoa is developed by **Darkelf Labs**.

© 2025–2026 Dr. Kevin Moore.

**Darkelf Cocoa — Native macOS browsing with privacy at its core.**
