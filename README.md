
# 🧿 Darkelf Cocoa Browser

[![Monthly Downloads](https://img.shields.io/pypi/dm/darkelf-cocoa?label=Monthly%20Downloads&color=brightgreen)](https://pypistats.org/packages/darkelf-cocoa)

[![Weekly Downloads](https://img.shields.io/pypi/dw/darkelf-cocoa?label=Weekly%20Downloads&color=brightgreen)](https://pypistats.org/packages/darkelf-cocoa)

[![Daily Downloads](https://img.shields.io/pypi/dd/darkelf-cocoa?label=Daily%20Downloads&color=brightgreen)](https://pypistats.org/packages/darkelf-cocoa)


## Darkelf Cocoa v7.0.26 — Stable Release

**Ephemeral • Privacy-First • Native macOS Cocoa / WebKit**

Darkelf Cocoa is a privacy-focused browser for macOS built with **Python, PyObjC, and Apple's WebKit**. It combines an ephemeral browsing architecture, fingerprinting defenses, native content blocking, local MiniAI Sentinel monitoring, and a customizable Cocoa interface.

> **Version:** 7.0.26  
> **Release date:** October 9, 2026  
> **Channel:** Stable  
> **Platform:** macOS  
> **Distribution:** DMG

## ✨ What's New in v7.0.26

### 🛡️ Improved Ad and Tracker Blocking

- Updated the content-filtering implementation to **Content Rules v15.08**.
- Expanded integration of supported EasyList network-filter rules with WebKit's native content-rule compilation.
- Improved cosmetic filtering to hide more empty advertising containers and leftover page elements.
- Improved content-rule installation handling when asynchronous compilation completes, including content controllers for existing tabs.
- Preserved compatibility-oriented exceptions and conservative cosmetic-filtering behavior.
- **AdBlock Tester result:** 93/100 in a reported test of this development build. Scores vary with test conditions and do not guarantee identical blocking on every website.

### 🧭 Address-Bar Context Menu Fixes

- Removed DuckDuckGo search actions from the address-bar right-click menu.
- Prevented address-bar context-menu search actions from opening Safari.
- Removed the macOS Services submenu from the Darkelf-controlled address-bar menu.
- Retained the familiar **Cut, Copy, Paste, and Select All** actions.

### 🎨 Native Interface Refinements

- Retained the streamlined native Cocoa menu and navigation design.
- Continued support for configurable accent colors and Darkelf Home backgrounds.
- Preserved improvements to bookmarks, Privacy & Security, MiniAI, and About panels.

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
- Fullscreen support and session controls.

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
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

1. Open the **v7.0.26** release on the [Darkelf Cocoa Browser GitHub repository](https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser/releases).
2. Download the macOS DMG asset when published.
3. Open the DMG and install the app using the instructions included with the release.
4. Launch Darkelf Cocoa.

**Note:** Verify code-signing, notarization, and distribution status against the published release; this README does not assert that those steps have already passed.

## 🧪 Testing & Compatibility

The v7.0.26 filtering changes are designed to strengthen blocking while minimizing disruption to ordinary browsing. Before distribution, regression-test websites with video, logins, verification challenges, images, and interactive content.

The reported **93/100 AdBlock Tester** result is a single benchmark result, not a comprehensive measure of browser security, compatibility, or privacy.

## 📜 License

**LGPL-3.0-or-later**. See the repository's license and third-party notices for details.

© 2025–2026 Darkelf Labs / Dr. Kevin Moore.
