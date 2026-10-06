# 🧿 Darkelf Cocoa Browser [![PyPI Downloads](https://static.pepy.tech/personalized-badge/darkelf-cocoa?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/darkelf-cocoa)

**Current Release: 7.0.21**

Darkelf Cocoa is a privacy-focused native macOS browser built with Python, PyObjC, and Apple WebKit.

## Features

- Native macOS WebKit browser
- Ephemeral browsing sessions
- First-party isolation
- Tracker and domain blocking
- HTTP → HTTPS upgrading
- Canvas and fingerprinting defenses
- WebRTC privacy protection
- Media permission controls
- TLS trust monitoring
- Darkelf MiniAI security monitoring
- PQ session integrity protections
- Automatic security lockdown
- Content Rule List filtering
- Native tabs, downloads, bookmarks, and keyboard shortcuts

## MiniAI Security

Darkelf MiniAI monitors browser activity for:

- Trackers and suspicious domains
- Fingerprinting attempts
- Automated scanners and scraping
- Brute-force and credential-stuffing patterns
- Traffic and domain anomalies
- Suspicious URL and path activity

### Automatic Lockdown

When critical activity exceeds the configured threshold, Darkelf:

- Stops loading across active tabs
- Temporarily disables navigation controls
- Maintains the lockdown for the configured duration
- Automatically restores browser controls when lockdown expires

## Privacy Architecture

Darkelf Cocoa uses:

- Ephemeral WebKit data storage
- Isolated browsing state
- Restricted media permissions
- JavaScript and WebKit policy controls
- Network inspection and tracker blocking
- Session-scoped privacy protections

Browsing data is designed to remain temporary rather than persist between private sessions.

## Installation

Requires macOS and Python 3.11 or newer.

### Install with pip

```bash
python3.11 -m pip install darkelf-cocoa
```

Run Darkelf:

```bash
darkelf
```

## Source Installation

Clone the repository:

```bash
git clone https://github.com/Darkelf-Labs/Darkelf-Cocoa-Browser.git
cd Darkelf-Cocoa-Browser
```

Install:

```bash
python3.11 -m pip install .
```

Run:

```bash
darkelf
```

## Security Audit

Darkelf Cocoa uses **Darkelf SecureAudit** to inspect WebKit and PyObjC security-sensitive code.

The repository security workflow generates SARIF results for GitHub Code Scanning.

The audit checks for security-sensitive patterns including:

- Dynamic JavaScript execution
- Tainted JavaScript input
- Dynamic HTML loading
- WebKit configuration
- WKUserScript usage
- WebKit KVC settings
- Local file access
- Navigation and UI delegates
- Media permission handling

Security audit findings should be reviewed in context. Informational and positive security-control detections are not vulnerabilities.

## Automatic Security Lockdown

Darkelf MiniAI can activate lockdown when critical activity reaches the configured threshold.

During lockdown:

1. Active WebKit loading is stopped.
2. Browser navigation controls are temporarily disabled.
3. The lockdown timer begins.
4. Network activity remains subject to Darkelf security policy.
5. Browser controls are automatically restored when the lockdown expires.

The previous internal HTML threat-report console is no longer used.

## Network Security

Darkelf provides native network-policy controls including:

- HTTP → HTTPS upgrading
- Suspicious protocol blocking
- Tracker-domain blocking
- URL inspection
- First-party context monitoring
- Session-level network metadata
- PQ integrity metadata
- Adaptive security decisions

Dangerous navigation schemes such as `file:`, `ftp:`, and `javascript:` are restricted by the browser navigation policy.

## Fingerprinting Protection

Darkelf includes defenses for common browser fingerprinting surfaces, including:

- Canvas
- WebGL
- Audio
- Fonts
- Battery information
- Geolocation
- Media devices
- WebRTC

Protections may use blocking, isolation, spoofing, or controlled responses depending on the browser component and context.

## First-Party Isolation

Darkelf maintains browsing context information on a per-tab and first-party basis.

This helps reduce unwanted state sharing between unrelated sites and supports Darkelf's privacy and network-policy systems.

## PQ Session Integrity

Darkelf includes experimental session-level PQ integrity mechanisms.

These protections use session-specific cryptographic state to assist with:

- Session integrity monitoring
- Per-tab security state
- Network-event correlation
- Trust-change detection
- Adaptive MiniAI analysis

PQ metadata is maintained within the Darkelf security architecture and is not intended to replace standard TLS.

## TLS Security

Darkelf uses WebKit and macOS security APIs for HTTPS certificate handling and trust evaluation.

The browser can monitor server-trust state and surface trust changes through its security interface.

## Ephemeral Browsing

Darkelf is designed around temporary browsing state.

WebKit ephemeral storage and Darkelf session isolation reduce persistent browser data between private browsing sessions.

## Content Filtering

Darkelf uses WebKit Content Rule Lists and native policy controls to reduce unwanted network activity.

Filtering is designed to complement the browser's privacy and security protections rather than replace WebKit's built-in security model.

## Media Permissions

Darkelf applies explicit WebKit media-permission handling.

Camera, microphone, and related browser permissions are controlled through the browser's native WebKit delegate architecture.

## Native macOS Architecture

Darkelf Cocoa is built around native Apple technologies:

- macOS
- Apple WebKit
- Cocoa
- Foundation
- AppKit
- Security framework
- Python
- PyObjC

Darkelf Cocoa does not require Chromium or QtWebEngine.

## Requirements

- macOS
- Python 3.11+
- PyObjC
- Apple WebKit

## Repository Structure

```text
darkelf_cocoa/
├── application.py
├── browser.py
├── darkelf_branding.py
├── darkelf_content_rules.py
├── darkelf_delegates.py
├── darkelf_downloads.py
├── darkelf_icons.py
├── darkelf_isolation.py
├── darkelf_network.py
├── darkelf_pages.py
├── darkelf_policy.py
├── darkelf_pq.py
├── darkelf_sentinel.py
├── darkelf_spoofing.py
├── darkelf_tabs.py
├── darkelf_theme.py
├── darkelf_ui.py
├── darkelf_utils.py
└── main.py
```

## Development

Run Darkelf directly from the repository:

```bash
python3.11 -m darkelf_cocoa.main
```

Install the local package:

```bash
python3.11 -m pip install .
```

## Security Scanning

Darkelf Cocoa is scanned with the Darkelf SecureAudit project.

The GitHub Actions security workflow scans the `darkelf_cocoa` package and uploads SARIF output to GitHub Code Scanning.

Security findings are categorized as:

| Category | Meaning |
| --- | --- |
| HIGH | Potential security-sensitive issue requiring review |
| MEDIUM | Potentially unsafe or unusual implementation requiring review |
| INFO | Security-relevant implementation detected |
| GOOD | Positive security control detected |

A scanner finding does not by itself establish that a vulnerability is exploitable.

## Release

### 7.0.20

Current Cocoa release.

This release includes the current native macOS browser architecture, MiniAI monitoring, privacy protections, WebKit security controls, PQ session integrity features, and automated security auditing.

## License

Darkelf Cocoa Browser is licensed under the **GNU Lesser General Public License v3.0 or later (LGPL-3.0-or-later)**.

See the repository license for the complete terms.

## Darkelf Labs

Developed by **Dr. Kevin Moore / Darkelf Labs**.

Darkelf Cocoa focuses on native macOS browsing, privacy isolation, fingerprinting resistance, and lightweight browser security monitoring.
