# 🧿 Darkelf Cocoa Browser 4.3.7 [![PyPI Downloads](https://static.pepy.tech/personalized-badge/darkelf-cocoa?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/darkelf-cocoa)
### Ephemeral, Privacy‑First macOS Browser (PyObjC + WebKit)

A hardened, **memory‑only** macOS browser designed for **zero persistence**, **tracker resistance**, **real‑time threat detection**, and **post‑quantum integrity awareness** — installable via `pip` with a full native GUI.

> **Core promise:** Darkelf Cocoa aims to keep browsing state **in RAM only** (cookies, cache, history, local storage, IndexedDB, etc.) and discard it when the process exits, while applying defense‑in‑depth protections against tracking and hostile automation.

---

## Table of Contents
- [Why Darkelf Cocoa](#why-darkelf-cocoa)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Security Model](#security-model)
- [Post‑Quantum Integrity Layer (PQ)](#post-quantum-integrity-layer-pq)
- [MiniAI Sentinel (On‑Device IDS)](#miniai-sentinel-on-device-ids)
- [First‑Party & Tab Isolation](#first-party--tab-isolation)
- [Downloads & File Integrity](#downloads--file-integrity)
- [User Indicators](#user-indicators)
- [Platform Support](#platform-support)
- [License](#license)
- [Author](#author)
- [Disclaimer](#disclaimer)

---

## Why Darkelf Cocoa
Darkelf Cocoa Browser is the macOS edition of the Darkelf‑Mini project, implemented with **PyObjC** bindings to Apple’s **Cocoa** + **WebKit** frameworks.

It’s built for users who want:
- **Ephemeral browsing** (no retained session artifacts)
- **Aggressive tracking resistance**
- **Local-only security monitoring** (no telemetry)
- **Integrity signaling** and session-bound consistency checks
- **Enhanced error handling**
- **Memory chunking**
- **Safe url handling**

---

## Features

### 🔒 Zero‑Persistence Runtime (RAM‑Only)
- No disk-backed cookies/cache/history/local storage
- Uses **non‑persistent WebKit data stores**
- Designed to discard browsing data automatically when the app exits

### 🚫 Tracker & Telemetry Resistance
- Built‑in content blocking rules (WebKit Content Rule Lists)
- Additional DOM/CSS suppression for common banners/ads and nuisance overlays
- Optional protocol/scheme restrictions (blocks risky schemes like `file:`, `ftp:`, `javascript:`)

### 🧬 Isolation by Design
- **First‑Party Isolation (FPI)**: compartmentalized storage by site
- Optional **tab‑level isolation** for stronger separation
- Reduces cross‑site correlation and session leakage risk

### 🧠 On‑Device Threat Detection (MiniAI Sentinel)
- Local intrusion/abuse heuristics
- Tracks suspicious navigation patterns, scanners, credential stuffing behaviors, and fingerprinting indicators
- Automatic **lockdown mode** when critical threat thresholds are met
- No external reporting or analytics

### 🔗 Post‑Quantum Integrity Awareness (PQ Layer)
- Deterministic, session‑bound request integrity signals using **SHA3**
- Behavioral anomaly checks and entropy scoring
- Trust-change awareness via TLS certificate tracking (TOFU‑style)

---

## Installation

```bash
pip install darkelf-cocoa
```

---

## Quick Start

```bash
darkelf
```

---

## Security Model

Darkelf Cocoa uses a defense‑in‑depth approach:
1. **Ephemeral storage** (RAM-only browsing state)
2. **Isolation** (site/tab compartmentalization)
3. **Content blocking** (known tracker patterns + nuisance suppression)
4. **On-device monitoring** (MiniAI Sentinel)
5. **Integrity awareness** (PQ layer + TLS trust consistency)

---

## Post-Quantum Integrity Layer (PQ)

Darkelf implements a **post-quantum–aware integrity and behavioral verification system** using **SHA3-512 / SHA3-256** primitives.  
This layer provides **tamper-evident, session-bound consistency signals** *without modifying network traffic* and is fully **deterministic per session/tab context**.

---

### ✅ What PQ is (in Darkelf)

- **Deterministic request fingerprinting** bound to:
  - URL
  - normalized metadata (where available)
  - **per-tab session seed (`_pq_seed`)**
  - **hidden salt (`_pq_salt`) for secrecy**
  - time bucket (anti-replay, ~10s window)

- Uses:
  - **SHA3-512** → high-entropy identity + integrity binding  
  - **SHA3-256** → lightweight deterministic decision logic

- Designed to be:
  - stable within session context  
  - non-replayable across time buckets  
  - non-correlatable across tabs  

---

### 🔁 PQ Chaining

- **Per-tab seeded chain progression**
  - `_pq_seed` → root identity (secure, locked per tab)
  - `_pq_counter` → monotonic progression (bounded, no randomness)
  - `darkelf_pq_chain` → request-bound continuity signal

- Properties:
  - deterministic evolution (no per-request randomness)
  - zero fallback behavior (prevents weak entropy states)
  - low-noise progression safe for rendering environments

- Purpose:
  - detect replay patterns  
  - detect navigation inconsistencies  
  - enforce **session continuity integrity**

---

### 🎨 Canvas PQ Seed Integration (NEW)

- Canvas entropy is **bound to PQ identity** via:
  - `get_canvas_seed(tab)` → derived from `_pq_seed`

- Behavior:
  - deterministic per tab/session
  - stable rendering output within session
  - isolated across tabs

- Security effect:
  - prevents cross-site canvas fingerprint correlation  
  - preserves entropy while eliminating global fingerprinting vectors  
  - aligns rendering layer with PQ integrity model  

---

### 🕵️ Minimal Deception Layer (Third-Party Contexts)

- Applies only in **third-party** situations
- Triggered only when PQ fingerprint is present
- **Fully deterministic (no randomness)**

- Mechanism:
  - derives alternate signal (`_pq_fp_alt`) from PQ state + host
  - extremely low activation frequency (bit-gated)

- Purpose:
  - reduce tracker confidence
  - degrade correlation accuracy
  - avoid detectable noise patterns

---

### 🧠 PQ Behavioral Intelligence

- Sliding window tracking (`_pq_window`)
- Unique fingerprint tracking (`_pq_seen`)
- Entropy-based anomaly scoring (realistic thresholds)

- Detection signals:
  - excessive uniqueness → suspicious session behavior  
  - high short-window entropy → automation / replay patterns  

- PQ contributes to:
  - `suspicious_hits`
  - overall threat score
  - **PQ-specific risk indicator**

---

### 🔐 TLS Trust Awareness (TOFU-Style)

- Tracks server certificate subject summaries per host
- Detects trust changes within a session (TOFU model)

- Integration:
  - combined with PQ session continuity signals
  - feeds UI trust indicators

- UI behavior:
  - stable trust → normal PQ indicator  
  - changed trust → warning indicator  

---

### 🆕 PQ Canonicalization (NEW)

- All PQ inputs are normalized before hashing:
  - path normalization (`// → /`)
  - sorted query parameters
  - header normalization (excluding `_pq_*` fields)

- Purpose:
  - eliminate attacker-controlled entropy variance  
  - ensure stable identity across equivalent requests  

---

### 🆕 PQ Replay Memory (NEW)

- Maintains a bounded sliding window of recent chain values (`_pq_chain_seen`)
- Detects:
  - repeated chain states (replay)
  - duplicated request flows

- Effect:
  - increases `suspicious_hits`
  - contributes to anomaly scoring

---

### 🆕 Adaptive PQ Enforcement (NEW)

PQ signals influence request handling indirectly:

- medium PQ risk → degraded identity signals  
- high PQ risk → PQ identity stripped (isolation behavior)

- Purpose:
  - reduce tracking reliability under suspicious conditions  
  - prevent stable identity exposure during anomalies  

---

### 🆕 Multi-Mode Deception (NEW)

- Third-party deception supports multiple deterministic modes:
  - slight mutation (hash-derived)
  - truncated identity
  - namespace-shifted identity

- Purpose:
  - prevent tracker adaptation  
  - avoid consistent fingerprint reconstruction  

---

### 🆕 Identity Rotation (NEW)

- Long sessions trigger deterministic seed rotation:
  - `_pq_seed → SHA3-256(_pq_seed)`
  - resets `_pq_counter`

- Purpose:
  - limit long-term correlation  
  - preserve short-term session continuity  

---

### 🆕 Observable Effects (User-Level)

While PQ operates internally, its effects may be visible:

- fingerprinting tests may produce inconsistent results  
- cross-site tracking may fail or reset  
- different tabs behave as isolated identities  
- unusual activity may trigger degraded or restricted behavior  
- TLS trust changes may surface as warnings  

---

### 🧠 PQ Summary Model (Updated)

PQ operates as a unified system combining:

- **Integrity Layer** → tamper-evident request binding  
- **Continuity Layer** → per-tab chain progression  
- **Anti-Correlation Layer** → deterministic third-party signal degradation  
- **Behavioral Intelligence Layer** → entropy-based anomaly detection  
- **Rendering Isolation Layer** → canvas bound to PQ seed  
- **Trust Awareness Layer** → TLS consistency monitoring  
- **Canonicalization Layer** → stable input normalization  
- **Replay Protection Layer** → duplicate chain detection  
- **Adaptive Layer** → risk-driven signal degradation  

---

## MiniAI Sentinel (On-Device IDS)

### Detects (heuristic signals)
- Trackers and third-party correlation attempts
- Fingerprinting indicators (canvas/webgl/audio keywords & patterns)
- Scraping/bot-like navigation patterns
- Credential stuffing-like bursts against login endpoints
- Scanner-like domain velocity patterns
- Suspicious URL encodings / traversal probes

### Automatic Lockdown Mode
When critical threats exceed threshold:
- Stops loading across tabs
- Opens an internal report console (`darkelf://report`)
- Temporarily disables navigation controls
- Auto-unlocks after a defined duration (configurable)

> MiniAI runs locally. No telemetry, analytics, or network beacons are included.

---

## First‑Party & Tab Isolation
- Storage is separated by an eTLD+1 approximation (with an auth whitelist for common login flows)
- Optional tab-level compartmentalization for stricter isolation
- Designed to prevent cross-site storage reuse and reduce tracking surface

---

## Downloads & File Integrity

### Safe-by-default behavior
- Download routing can be restricted to avoid persistence
- Temporary download directories can be wiped

### File integrity protection
- Downloads can be hashed with **SHA3** and bound to the session PQ chain
- In-memory hash registry enables within-session integrity checks for downloaded artifacts

---

## User Indicators
- `PQ✓` → TLS secure + PQ integrity active (stable)
- `PQ⚠` → trust anomaly detected (e.g., TLS trust change during session)

---

## 🎨 Fingerprint System (Enhanced)

### PQ-Based Identity

Each tab now uses a **deterministic, hidden identity** derived from an internal PQ seed:

- Stable within a tab session  
- Independent across tabs  
- Not exposed to websites  

### Rotation Model

- Fingerprints remain stable on reload  
- New tabs receive distinct identities  
- Gradual variation over time and navigation  

### Result

- Prevents cross-tab tracking  
- Avoids unstable or overly-random behavior  

---

## 🧩 Fingerprint Coherence

- Canvas, WebGL, and font signals are now aligned  
- Eliminated inconsistent or conflicting fingerprint traits  

### Result

- Coherent, realistic device fingerprint  
- Reduced detection via cross-surface mismatch  

---

## 🕶️ User-Agent Stealth

- Removed all Darkelf identifiers from the User-Agent  

### Result

- Appears as a standard WebKit/macOS client  
- Internal identity system remains fully hidden  

---

## 🔐 Internal Improvements

- Hidden identity grouping (not externally visible)  
- Navigation-based entropy (no JS-driven mutation)  
- Stable, non-reactive fingerprint behavior  

## ⚙️ JavaScript Hardening (PQ Unified)

* All JS privacy surfaces aligned under PQ-seeded entropy
* Consistent spoofing across:

  * Canvas
  * WebGL
  * Font fingerprinting

---

## 🔁 Fingerprint Isolation

### Per-Tab Identity Model

* 🔁 Deterministic per-tab identity
* Group-based identity distribution (bucketed)
* No cross-tab fingerprint reuse

### Result

* Eliminates cross-tab correlation vectors
* Prevents long-session fingerprint linking
* Creates overlapping identity clusters (crowd blending)

## License
**LGPL-3.0-or-later**

---

## Author
Dr. Kevin Moore (2025)

---

## Disclaimer
This project is security-focused software provided **without warranty**.  
If you distribute binaries or integrate cryptographic components beyond Apple’s platform frameworks, you are responsible for applicable compliance (export controls, local regulations, etc.).
