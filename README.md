# 🧿 Darkelf Cocoa Browser

[![PyPI Version](https://img.shields.io/pypi/v/darkelf-cocoa?label=PyPI&color=blue)](https://pypi.org/project/darkelf-cocoa/)
[![Python Versions](https://img.shields.io/pypi/pyversions/darkelf-cocoa)](https://pypi.org/project/darkelf-cocoa/)
[![PyPI Downloads](https://static.pepy.tech/badge/darkelf-cocoa)](https://pepy.tech/projects/darkelf-cocoa)
[![Monthly Downloads](https://static.pepy.tech/badge/darkelf-cocoa/month)](https://pepy.tech/projects/darkelf-cocoa)

**Native macOS browsing. Privacy by design.**

Darkelf Cocoa is a privacy-focused browser powered by **Python, PyObjC, and Apple WebKit**. It pairs ephemeral browsing with fingerprinting defenses, native content blocking, local MiniAI Sentinel monitoring, and a customizable Cocoa interface.

**Current release: v7.1.2** · macOS · DMG distribution

## ✨ What's New in 7.1.2

- **Video compatibility restored:** ESPN, NBA, and NHL video playback confirmed working in developer testing with content filtering enabled.
- **Adblocking maintained:** **100/100 on Adblock Tester** in the same development configuration. This is a test result, not a guarantee of universal blocking.
- **Smarter media compatibility:** Refined WebKit content-rule exceptions to reduce disruption to supported video players.
- **Polished Cocoa experience:** Retains Darkelf-styled context menus, accent-aware Find Bar, customizable themes, and the compact **Move & Resize** window popover introduced in 7.1.1.

## 🛡️ Privacy Features

- Ephemeral WebKit browsing and privacy-oriented session controls
- Canvas and WebGL fingerprinting defenses
- WebRTC restrictions and permission controls
- Native WebKit ad/tracker filtering and conservative cosmetic cleanup
- Local **MiniAI Sentinel** for privacy-relevant activity monitoring

Privacy protections are best-effort; no browser can guarantee anonymity or block every tracker.

## 🪟 Native macOS Experience

Tabs, bookmarks, integrated address/search bar, keyboard shortcuts, customizable accent colors, Darkelf Home backgrounds, fullscreen support, and native window arrangement controls.

## 📦 Install

1. Visit [Darkelf Cocoa GitHub Releases](https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser/releases).
2. Select **v7.1.2** and download its macOS DMG **when published**.
3. Open the DMG, drag Darkelf Cocoa to Applications, and launch.

The signed and notarized distribution build should be verified before publication.

## ⌨️ Useful Shortcuts

| Shortcut | Action |
|---|---|
| `⌘T` / `⌘W` | New / close tab |
| `⌘L` / `⌘R` | Address bar / reload |
| `⌘F` | Find in page |
| `⇧⌘C` | Copy page URL |
| `⌃⌘F` | Toggle fullscreen |

## 🧪 Compatibility

Developer testing confirms ESPN, NBA, and NHL video playback, alongside a **100/100 Adblock Tester** result. Other streaming services and individual playback flows may behave differently; report reproducible issues with URLs and logs.

## 📜 License

**LGPL-3.0-or-later** · See repository license and third-party notices.

© 2025–2026 Darkelf Labs / Dr. Kevin Moore.

