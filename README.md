# 🍫 Darkelf Cocoa Browser

**A native macOS browser built with PyObjC and WebKit, designed for private, streamlined browsing.**

[![PyPI version](https://img.shields.io/pypi/v/darkelf-cocoa.svg)](https://pypi.org/project/darkelf-cocoa/)
[![Python versions](https://img.shields.io/pypi/pyversions/darkelf-cocoa.svg)](https://pypi.org/project/darkelf-cocoa/)
[![PyPI downloads](https://img.shields.io/pypi/dm/darkelf-cocoa.svg)](https://pypi.org/project/darkelf-cocoa/)

**Current release: v7.1.7** · **Platform: macOS** · **Engine: Apple WebKit**

[Website](https://darkelfbrowser.com) · [Releases](https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser/releases) · [Source code](https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser)

## About Darkelf Cocoa

Darkelf Cocoa is a macOS-native browser built using Python, PyObjC, AppKit, and Apple's WebKit framework. Its interface combines familiar browser navigation with built-in privacy controls, an ephemeral browsing approach, and customizable appearance.

Darkelf Cocoa is a separate implementation from Darkelf Shadow CE. It uses the system WebKit engine rather than QtWebEngine.

## Highlights

### 🛡️ Privacy-first browsing

- Ephemeral browsing design that avoids maintaining a conventional persistent browsing-history database.
- Built-in tracker and advertising content-rule defenses.
- Site-aware protection policies, including trusted, protected, and standard handling where supported.
- First-party/tab isolation architecture.
- Privacy monitoring and a MiniAI status interface.
- Session cleanup controls.

Privacy defenses reduce exposure; they do not guarantee anonymity, block every tracker, or eliminate every possible macOS forensic artifact.

### 🔒 Browser Lock — v7.1.7

An **optional Browser Lock** adds a local access check to the browser:

- Authenticate at startup when Browser Lock is enabled.
- Re-lock after approximately **10 minutes of browser inactivity**.
- Re-lock when the browser window is minimized to the Dock.
- Unlock using the macOS authentication dialog, which can offer **Touch ID or the Mac account password**, depending on the device and its configuration.
- Manage Browser Lock in **Privacy & Security**.

Darkelf Cocoa delegates authentication to macOS **LocalAuthentication**. It does not collect or store fingerprint data or your Mac password. Browser Lock is an application-level access feature, **not disk or memory encryption**.

### 🎨 Native macOS interface

- AppKit-based navigation, tabs, menus, and keyboard shortcuts.
- Accent-color presets and background themes.
- Accent-aware application/Dock icon and in-app Darkelf shield branding.
- Native macOS appearance and window controls.
- Integrated Find in Page, bookmarks, and download UI.

### ⌨️ Address bar and shortcuts

- Right-click editing controls: **Cut**, **Copy**, **Paste**, **Paste and Go**, and **Select All**.
- **⇧⌘V** — Paste and Go: navigate to a copied address or search the copied text using the existing address-bar behavior.
- **⌘L** — Focus address bar.
- **⌘T** — New tab; **⌘W** — Close tab.
- **⌘R** — Reload; **⌘F** — Find in page.
- Built-in Keyboard Shortcuts reference in the browser menu.

## What's new in v7.1.7

- Added opt-in Browser Lock with native macOS owner authentication.
- Added startup, inactivity, and Dock-minimization lock triggers.
- Added a dedicated Browser Lock information view in Privacy & Security.
- Improved accent-color consistency across Darkelf shield branding and the native interface.
- Added **Paste and Go** to the address-bar context menu and shortcut reference (**⇧⌘V**).
- Continued interface and stability refinements.

See the [v7.1.7 release notes](https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser/releases) for the release overview.

## Get Darkelf Cocoa

Download the macOS build from [GitHub Releases](https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser/releases).

A Python package is also available on [PyPI](https://pypi.org/project/darkelf-cocoa/). For a source/package installation, use an appropriate supported macOS Python environment and consult the repository's installation instructions and dependencies.

```bash
python3.11 -m pip install darkelf-cocoa
```

The packaged macOS application and Python-launched development environment may display different application names in native system authentication prompts.

## Architecture

Darkelf Cocoa uses **PyObjC + AppKit** for the native interface and **WKWebView/WebKit** for page rendering. Browser components are separated across modules for UI, tabs, policies, content rules, first-party isolation, monitoring, branding, and themes.

It relies on the WebKit functionality provided by macOS; support for particular media formats, DRM systems, and websites may vary with the operating system and WebKit implementation.

## Security and limitations

Darkelf Cocoa is a privacy-oriented browser, not a promise of complete anonymity or forensic resistance. Browser Lock protects access through the running app but does not replace macOS FileVault, a secure account password, or device-level security controls. Some websites may require compatibility adjustments, and blocking behavior can vary by site.

## License

Licensed under **LGPL-3.0-or-later**. See the repository's license and third-party notices for the applicable terms.

---

**Darkelf Labs** · [darkelfbrowser.com](https://darkelfbrowser.com)
