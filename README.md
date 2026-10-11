# 🧿 Darkelf Cocoa Browser

[![PyPI Version](https://img.shields.io/pypi/v/darkelf-cocoa?label=PyPI&color=blue)](https://pypi.org/project/darkelf-cocoa/)
[![Python Versions](https://img.shields.io/pypi/pyversions/darkelf-cocoa)](https://pypi.org/project/darkelf-cocoa/)
[![PyPI Downloads](https://static.pepy.tech/badge/darkelf-cocoa)](https://pepy.tech/projects/darkelf-cocoa)
[![Monthly Downloads](https://static.pepy.tech/badge/darkelf-cocoa/month)](https://pepy.tech/projects/darkelf-cocoa)

## Darkelf Cocoa v7.1.1 — Stable Release

**Ephemeral • Privacy-First • Native macOS Cocoa / WebKit**

Darkelf Cocoa is a privacy-focused browser for macOS built with **Python, PyObjC, and Apple's WebKit**. It combines an ephemeral browsing architecture, fingerprinting defenses, native content blocking, local MiniAI Sentinel monitoring, and a customizable Cocoa interface.

> **Version:** 7.1.1  
> **Release date:** October 11, 2026  
> **Channel:** Stable  
> **Platform:** macOS  
> **Distribution:** DMG

## ✨ What's New in v7.1.1

### 🪟 Native Window Management and Darkelf Popover

- Added a compact, Darkelf-themed **Move & Resize** popover associated with the macOS green window button.
- Provided window positioning and arrangement controls, including left/right/top/bottom placement, fill options, and multi-window layouts.
- Added a distinct four-window arrangement control and refined its icon to better match familiar macOS window tiling visuals.
- Improved popover anchoring in regular and fullscreen window states, with further fixes to prevent the panel appearing at the bottom of the screen or obscuring the traffic-light controls.
- Refined window-action keyboard handling to avoid stray Reload tooltips and accidental menu activation.
- Kept accent-aware styling synchronized with Darkelf's selected interface color.
- Window arrangement of **other applications** depends on macOS accessibility and automation permissions. Availability and behavior can vary by app and window state.

### 🧪 v7.1.1 Development Validation

- The latest development screenshots show Darkelf Cocoa arranged alongside Firefox and Terminal, with the custom popover visible.
- The developer reported that the prior permission warning no longer appeared in the tested configuration; this does **not** guarantee permission-free operation for all users or other applications.
- Final signed-DMG testing remains recommended before publishing.


### 🖱️ Darkelf-Styled Context Menus

- Introduced accent-aware, dark-themed context menus for the address bar and general webpage actions.
- Kept address-bar **Cut, Copy, Paste, and Select All** actions and their standard macOS shortcuts.
- Added general webpage actions including **Back, Forward, Reload, Copy Page URL, and Find in Page** where applicable.
- Removed the experimental **Passwords / Autofill** menu action and its shortcut.
- Improved context-menu handling to avoid the native macOS menu appearing alongside Darkelf's custom menu.
- Link-specific and image-specific webpage actions are not yet implemented.

### ⌨️ Keyboard Shortcuts and Native UI

- Connected context-menu actions to their corresponding keyboard handlers and updated the in-app Keyboard Shortcuts panel.
- Added **⇧⌘C** for Copy Page URL, alongside standard macOS text-editing shortcuts.
- Replaced the native **Clear All Browsing Data?** alert with an accent-aware Darkelf confirmation panel while retaining its confirmation-before-wipe behavior.
- Updated the Find Bar close button to follow live accent-color changes.

### 🧬 Fingerprinting Protection

- Preserved the original PQ-seeded fingerprinting defenses after testing experimental consistency changes.
- Development tests of EFF Cover Your Tracks reported randomized fingerprint behavior in successful runs; results can vary and do not guarantee anonymity.


### 🛡️ Improved Ad and Tracker Blocking

- Updated the content-filtering implementation to **Content Rules v15.15**.
- Expanded integration of supported EasyList network-filter rules with WebKit's native content-rule compilation.
- Improved cosmetic filtering to hide more empty advertising containers and leftover page elements.
- Improved content-rule installation handling when asynchronous compilation completes, including content controllers for existing tabs.
- Preserved compatibility-oriented exceptions and conservative cosmetic-filtering behavior.
- **Previous AdBlock Tester result:** 93/100 in an earlier reported test; this is not a new v7.1.1 benchmark. Scores vary with test conditions.

### 🧹 Dynamic Cosmetic Ad Cleanup

- Added conservative, dynamic cleanup of empty ad-slot containers after pages load.
- Improved removal of leftover advertising spaces on sites such as CNN and GameSpot while retaining safeguards for legitimate page elements.
- Kept compatibility-conscious WebKit content filtering and existing site exceptions.

### 🧭 Earlier Address-Bar Context Menu Fixes

- Retained removal of Safari-opening search actions and the unwanted macOS Services submenu.
- Preserved familiar text-editing actions in the updated Darkelf-styled menu.

### 🎨 Accent Synchronization Across Home Tabs

- Fixed a theme synchronization issue where existing **Darkelf Home** tabs retained an older accent after changing colors on an external webpage.
- Accent changes now refresh all open Darkelf Home tabs, not only the active tab.
- External websites remain untouched by the homepage theme refresh.
- Homepage background selections continue to use the current theme settings.

### 🎨 Native Interface Refinements

- Refined menu label and icon colors for improved readability.
- Fixed hover behavior in the homepage background-theme picker.
- Retained the streamlined native Cocoa menu and navigation design.
- Continued support for configurable accent colors and Darkelf Home backgrounds.
- Preserved improvements to bookmarks, Privacy & Security, MiniAI, and About panels.

### 💿 Branded DMG Volume

- Added support in the release workflow for a custom Darkelf Cocoa icon on the mounted DMG volume.
- The mounted-volume icon is a packaging enhancement and does not change browser privacy behavior.

## 🔒 Privacy & Security

Darkelf Cocoa is designed around:

- Ephemeral WebKit website data stores.
- Browsing isolation and privacy-oriented session management.
- Canvas, WebGL, and other fingerprinting defenses.
- WebRTC restriction and privacy-oriented permission handling.
- Native WebKit content rules for advertising and tracker blocking.
- Cosmetic filtering for advertising placeholders.
- HTTPS-oriented navigation behavior where supported.
- Local MiniAI Sentinel monitoring.
- Session controls and privacy-focused browser defaults.

Protection is best-effort: websites, browser APIs, and filtering techniques change. Darkelf Cocoa does not claim complete anonymity or universal ad blocking.

## 🧠 MiniAI Sentinel

MiniAI Sentinel is a local browser-security feature intended to surface suspicious browsing signals, tracker activity, fingerprinting attempts, and other privacy-relevant events.

## 🎨 Browser Interface

The native Cocoa interface includes:

- Tabs and an integrated address/search field.
- Bookmarks and browsing controls.
- Find in Page and keyboard shortcuts.
- Configurable accent colors and homepage backgrounds.
- Privacy & Security and MiniAI panels.
- Fullscreen support, accent-aware Move & Resize popover, window arrangement controls, and session controls.

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `⌘X` / `⌘C` / `⌘V` / `⌘A` | Cut / Copy / Paste / Select All in text fields |
| `⇧⌘C` | Copy page URL |
| `⌘T` | New tab |
| `⌘W` | Close tab |
| `⌘R` | Reload |
| `⌘L` | Focus address bar |
| `⌘F` | Find in page |
| `Esc` | Close Find bar |
| `⌃⌘F` | Toggle fullscreen |
| `⌘+` / `⌘-` | Zoom in / out |
| `⇧⌘X` | Exit Darkelf |

## 📦 Installation

1. Open the **v7.1.1** release on the [Darkelf Cocoa Browser GitHub repository](https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser/releases).
2. Download the macOS DMG asset when published.
3. Open the DMG and install the app using the instructions included with the release.
4. Launch Darkelf Cocoa.

**Note:** Verify code-signing, notarization, and distribution status against the published release; this README does not assert that those steps have already passed.

## 🧪 Testing & Compatibility

The retained cosmetic cleanup and Content Rules v15.15 aim to reduce leftover ad spaces while minimizing disruption to ordinary browsing. Before distribution, regression-test websites with video, logins, verification challenges, images, and interactive content.

The previously reported **93/100 AdBlock Tester** result is historical and is not a new v7.1.1 benchmark or a comprehensive measure of browser security, compatibility, or privacy.

## 📜 License

**LGPL-3.0-or-later**. See the repository's license and third-party notices for details.

© 2025–2026 Darkelf Labs / Dr. Kevin Moore.
