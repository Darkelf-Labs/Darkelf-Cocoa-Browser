# 🧿 Darkelf Cocoa Browser

[![PyPI Version](https://img.shields.io/pypi/v/darkelf-cocoa?label=PyPI&color=blue)](https://pypi.org/project/darkelf-cocoa/)
[![Python Versions](https://img.shields.io/pypi/pyversions/darkelf-cocoa)](https://pypi.org/project/darkelf-cocoa/)
[![PyPI Downloads](https://static.pepy.tech/badge/darkelf-cocoa)](https://pepy.tech/projects/darkelf-cocoa)
[![Monthly Downloads](https://static.pepy.tech/badge/darkelf-cocoa/month)](https://pepy.tech/projects/darkelf-cocoa)

**Native macOS browsing. Privacy by design.**

Darkelf Cocoa is a privacy-focused browser powered by **Python, PyObjC, and Apple WebKit**. It pairs ephemeral browsing with fingerprinting defenses, native content blocking, local MiniAI Sentinel monitoring, and a customizable Cocoa interface.

**Current release: v7.1.4** · macOS · DMG distribution

## ✨ What's New in 7.1.4

- **Native Darkelf Cocoa application menu:** About, License & Attribution, PyPI, and GitHub links open in Darkelf tabs, alongside standard Hide, Hide Others, and Quit actions.
- **Menu hover-state fix:** Prevents multiple application-menu rows from remaining highlighted at once; only the active hovered row uses the selected accent color.
- **Link destination preview:** Hover over a webpage link to see its URL in a compact, bottom-left, accent-bordered overlay; the preview hides when the pointer leaves.
- **Expanded shortcut reference:** The in-app Keyboard Shortcuts menu now includes `⌘H` (Hide Darkelf Cocoa), `⌥⌘H` (Hide Others), and `⌘Q` (Quit).
- **Site-based adblocking modes (Content Rules v15.28):** DW uses a compatibility-first **TRUSTED** profile; CNN and GameSpot use **PROTECTED** profiles with network blocking and existing cosmetic cleanup; other sites use **STANDARD** blocking. TRUSTED mode relaxes protection on DW to improve compatibility.
- **CNN and GameSpot layout improvements:** Developer testing found the large black ad boxes removed; some empty ad containers or reserved whitespace still remain. DW loaded in the same test configuration.
- **7.1.2 compatibility improvements retained:** ESPN, NBA, and NHL video playback was confirmed in developer testing; Adblock Tester scored **100/100** in that tested configuration. Results are not universal guarantees.

## 🛡️ Privacy Features

- Ephemeral WebKit browsing and privacy-oriented session controls
- Canvas and WebGL fingerprinting defenses
- WebRTC restrictions and permission controls
- Native WebKit ad/tracker filtering, EasyList network rules, site-based TRUSTED / PROTECTED / STANDARD compatibility profiles, and conservative cosmetic cleanup
- Local **MiniAI Sentinel** for privacy-relevant activity monitoring

Privacy protections are best-effort; no browser can guarantee anonymity or block every tracker.

## 🪟 Native macOS Experience

Tabs, bookmarks, integrated address/search bar, keyboard shortcuts, customizable accent colors, Darkelf Home backgrounds, fullscreen support, native window arrangement controls, an accent-aware macOS application menu, and an unobtrusive link destination preview.

## 📦 Install

1. Visit [Darkelf Cocoa GitHub Releases](https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser/releases).
2. Select **v7.1.4** and download its macOS DMG **when published**.
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
| `⌘H` / `⌥⌘H` | Hide Darkelf Cocoa / Hide Others |
| `⌘Q` | Quit Darkelf Cocoa |

## 🧪 Compatibility

Earlier developer testing confirmed ESPN, NBA, and NHL video playback, alongside a **100/100 Adblock Tester** result in an earlier tested configuration. In the current v15.28 content-rule test, DW, CNN, and GameSpot loaded; CNN and GameSpot no longer displayed the large black ad boxes, although some empty ad containers remained. TRUSTED mode on DW prioritizes compatibility over full ad/tracker blocking. These observations are not guarantees for all websites or release builds; report reproducible issues with URLs and logs.

## 📜 License

**LGPL-3.0-or-later** · See repository license and third-party notices.

© 2025–2026 Darkelf Labs / Dr. Kevin Moore.
