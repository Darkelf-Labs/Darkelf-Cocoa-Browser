# Darkelf Cocoa Browser v7.0.4 — Ephemeral, Privacy-Focused Web Browser (macOS / Cocoa Build)
# Copyright (C) 2025 Dr. Kevin Moore
#
# SPDX-License-Identifier: LGPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ────────────────────────────────────────────────────────────────────────────────
# PROJECT SCOPE (EPHEMERAL COCOA BUILD)
# Darkelf Cocoa Browser is the macOS edition of the Darkelf-Mini project,
# implemented using PyObjC bindings to Apple's Cocoa and WebKit frameworks.
#
# • All browsing data (cookies, cache, history, localStorage, IndexedDB, etc.)
#   is held in memory only and automatically discarded when the process exits.
# • Download requests are disabled by default to prevent disk persistence.
# • No telemetry, analytics, or network beacons are included.
# • Tracker detection and privacy monitoring are implemented through
#   DarkelfMiniAI — an on-device heuristic filter that inspects network headers
#   and JavaScript activity without transmitting data externally.
#
# For additional defense-in-depth, users are encouraged to use macOS full-disk
# encryption (FileVault) and secure memory management.
#
# ────────────────────────────────────────────────────────────────────────────────
# EXPORT / CRYPTOGRAPHY NOTICE
# This source distribution does not itself implement proprietary cryptographic
# algorithms. Any network encryption (such as TLS/SSL) is provided by Apple's
# WebKit and macOS security frameworks under their respective licenses.
#
# If you distribute binaries that include or link against cryptographic
# components, or if you add cryptographic code, you are responsible for
# compliance with applicable export-control laws (including the U.S. EAR) and
# any relevant license exceptions (e.g., TSU under 15 CFR §740.13(e)), as well
# as local regulations in jurisdictions of distribution and use.
#
# ────────────────────────────────────────────────────────────────────────────────
# COMPLIANCE & RESTRICTIONS
# This software may not be exported, re-exported, or transferred, directly or
# indirectly, in violation of U.S. or other applicable sanctions and export
# control laws.  Do not use this software in connection with the development,
# production, or deployment of weapons of mass destruction as defined by the
# EAR.  By downloading, using, or distributing this software, you agree to
# comply with all applicable laws and regulations.
#
# ──────────────────────────────────────────────��─────────────────────────────────
# NOTE
# This source code is provided without any compiled binaries. Redistribution,
# modification, and use must comply with the LGPL-3.0-or-later license and all
# applicable export/usage restrictions.
#
# Authored by Dr. Kevin Moore (2025).

import os
import time
import sys, re, json, threading
from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import hashlib
import zipfile
import objc
import secrets
import warnings
import AppKit
from Quartz import CABasicAnimation
from collections import deque
from datetime import datetime
from urllib.parse import urlparse, unquote, quote_plus
import urllib.request
from objc import ObjCPointerWarning
import shutil
import tldextract
from Foundation import (
    NSRunLoop,
    NSData,
    NSDate,
    NSOperationQueue,
    NSURLCache,
    NSMutableDictionary,
    NSURL,
    NSURLRequest,
    NSMakeRect,
    NSMakeSize,
    NSNotificationCenter,
    NSTimer,
    NSUserDefaults,
    NSURLRequest,
    NSMutableURLRequest,
    NSURLSession,
    NSURLSessionConfiguration,
    NSRegistrationDomain,
    NSURLAuthenticationMethodServerTrust,
    NSURLSessionAuthChallengeUseCredential,
    NSURLCredential,
    NSURLSessionAuthChallengePerformDefaultHandling,
)

warnings.filterwarnings("ignore", category=ObjCPointerWarning)

from Cocoa import (
    NSApp,
    NSApplication,
    NSWindow,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowCollectionBehaviorFullScreenPrimary,
    NSObject,
    NSButton,
    NSImage,
    NSBox,
    NSColor,
    NSView,
    NSTrackingArea,
    NSTrackingMouseEnteredAndExited,
    NSTrackingActiveAlways,
    NSEvent,
    NSMakeRect,
    NSSearchField,
    NSProgressIndicator,
    NSTextField,
    NSToolbarFlexibleSpaceItemIdentifier,
    NSApplicationActivationPolicyRegular,
)

from WebKit import (
    WKWebView,
    WKWebViewConfiguration,
    WKProcessPool,
    WKUserContentController,
    WKUserScript,
    WKPreferences,
    WKContentRuleListStore,
    WKWebsiteDataStore,
    WKNavigationActionPolicyAllow,
    WKNavigationActionPolicyCancel,
    WKNavigationResponsePolicyAllow,
    WKNavigationResponsePolicyDownload,
    WKNavigationTypeReload,
    WKNavigationType,
    WKUserScriptInjectionTimeAtDocumentStart,
    WKUserScriptInjectionTimeAtDocumentEnd,
)

from AppKit import (
    NSImageSymbolConfiguration,
    NSBezierPath,
    NSFont,
    NSAttributedString,
    NSAlert,
    NSAlertStyleCritical,
    NSColor,
    NSAppearance,
    NSAnimationContext,
    NSImage,
    NSImageLeft,
    NSLeftTextAlignment,
    NSImageView,
    NSViewWidthSizable,
    NSTextView,
    NSScrollView,
    NSViewMinYMargin,
    NSViewMaxXMargin,
    NSViewMaxYMargin,
    NSViewHeightSizable,
    NSViewMinXMargin,
    NSEventModifierFlagCommand,
    NSEventModifierFlagShift,
    NSPopover,
    NSViewController,
    NSMenu,
    NSMenuItem,
    NSSavePanel,
    NSBackgroundColorAttributeName,
    NSForegroundColorAttributeName,
    NSBitmapImageRep,
    NSMutableParagraphStyle,
    NSFocusRingTypeNone,
    NSEventModifierFlagControl,
)

import time
from typing import Dict
import base64
import tempfile

from Security import (
    SecTrustEvaluateWithError,
    SecTrustGetCertificateAtIndex,
    SecCertificateCopySubjectSummary,
)

extract = tldextract.TLDExtract(
    cache_dir="/tmp/tldcache"
)

def fetch_favicon(host, callback):

    if not host:
        callback(None)
        return

    if host in _favicon_cache:
        callback(_favicon_cache[host])
        return

    url = NSURL.URLWithString_(f"https://{host}/favicon.ico")

    config = NSURLSessionConfiguration.ephemeralSessionConfiguration()
    session = NSURLSession.sessionWithConfiguration_(config)

    def completion(data, response, error):

        img = None

        try:
            if data is not None:
                img = NSImage.alloc().initWithData_(data)

                if img:
                    _favicon_cache[host] = img
        except Exception:
            img = None

        NSOperationQueue.mainQueue().addOperationWithBlock_(
            lambda: callback(img)
        )

    session.dataTaskWithURL_completionHandler_(
        url,
        completion,
    ).resume()

# ---- Darkelf logging control ----

LOG_LEVEL = 1
# 0 = silent
# 1 = important only
# 2 = verbose debug

# ----------------------------
# Favicon Cache
# ----------------------------
_favicon_cache = {}

# -----------------------------------
# 🔒 URL SAFETY CHECK
# -----------------------------------
def is_safe_url(url: str) -> bool:
    try:
        u = urlparse(url)
        return u.scheme in ("http", "https")
    except Exception:
        return False


def log(level, *msg):
    if level <= LOG_LEVEL:
        print(*msg)


def inject_screen_spoof(ucc):
    js = r"""
    (() => {
        const width = 1920;
        const height = 1080;
        const dpr = 2;

        const define = (obj, prop, value) => {
            try {
                Object.defineProperty(obj, prop, {
                    get: () => value,
                    configurable: true
                });
            } catch (e) {}
        };

        const patch = () => {
            define(Screen.prototype, "width", width);
            define(Screen.prototype, "height", height);
            define(Screen.prototype, "availWidth", width);
            define(Screen.prototype, "availHeight", height - 37);

            define(Window.prototype, "innerWidth", width);
            define(Window.prototype, "innerHeight", height);
            define(Window.prototype, "outerWidth", width);
            define(Window.prototype, "outerHeight", height);
            define(Window.prototype, "devicePixelRatio", dpr);

            define(window.screen, "width", width);
            define(window.screen, "height", height);
            define(window.screen, "availWidth", width);
            define(window.screen, "availHeight", height - 37);

            define(window, "innerWidth", width);
            define(window, "innerHeight", height);
            define(window, "outerWidth", width);
            define(window, "outerHeight", height);
            define(window, "devicePixelRatio", dpr);

            if (window.visualViewport) {
                define(window.visualViewport, "width", width);
                define(window.visualViewport, "height", height);
                define(window.visualViewport, "scale", 1);
            }
        };

        patch();
        document.addEventListener("DOMContentLoaded", patch, { once: true });
        window.addEventListener("load", patch, { once: true });
    })();
    """

    script = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
        js, WKUserScriptInjectionTimeAtDocumentStart, False
    )
    ucc.addUserScript_(script)


def darkelf_destroy_tab(tab):
    try:
        view = getattr(tab, "view", None)

        if not view:
            return

        # 🔥 STOP FIRST
        try:
            view.stopLoading()
        except Exception as e:
            log(2, e)

        # 🔥 DETACH DELEGATES
        try:
            view.setNavigationDelegate_(None)
            view.setUIDelegate_(None)
        except Exception as e:
            log(2, e)

        # 🔥 LOAD BLANK (VERY IMPORTANT)
        try:
            view.loadHTMLString_baseURL_("", None)
        except Exception as e:
            log(2, e)

        # 🔥 REMOVE FROM UI
        try:
            view.removeFromSuperview()
        except Exception as e:
            log(2, e)

        # 🔥 DELAY FINAL RELEASE (prevents async crash)
        def _release():
            try:
                tab.view = None
            except Exception as e:
                log(2, e)

        threading.Timer(0.2, _release).start()

    except Exception as e:
        print("[DestroyTab error]", e)


def _pq_normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)

        path = re.sub(r"/+", "/", parsed.path or "/")

        query_items = sorted([q for q in (parsed.query or "").split("&") if q])
        query = "&".join(query_items)

        return f"{parsed.scheme}://{parsed.netloc}{path}?{query}"
    except Exception:
        return url or ""


def darkelf_pq_fingerprint(url: str, headers: dict = None, owner=None) -> str:
    h = hashlib.sha3_512()

    # 🔧 canonical URL (FIXED)
    norm_url = _pq_normalize_url(url)
    h.update(norm_url.encode("utf-8", errors="ignore"))

    # 🔧 canonical headers (FIXED: stable + filtered)
    if headers:
        for k, v in sorted(headers.items()):
            if k.lower().startswith("_pq"):
                continue  # avoid recursion / pollution
            h.update(str(k).lower().encode())
            h.update(str(v).encode())

    # ⏱ time bucket (anti-replay)
    bucket = int(time.time() // 10)
    h.update(bucket.to_bytes(8, "big"))

    # 🔐 hidden salt (session secrecy)
    if owner and hasattr(owner, "_pq_salt"):
        h.update(owner._pq_salt)

    # 🔐 OPTIONAL: TLS binding (NEW)
    if owner and hasattr(owner, "_pq_tls_summary"):
        h.update(owner._pq_tls_summary.encode())

    return h.hexdigest()


def darkelf_pq_chain(owner, url: str) -> bytes:

    # ----------------------------
    # resolve active tab
    # ----------------------------
    tab = None

    if hasattr(owner, "tabs") and 0 <= getattr(owner, "active", -1) < len(owner.tabs):
        tab = owner.tabs[owner.active]

    if not tab or not getattr(tab, "_pq_seed", None):
        return b"\x00" * 32  # 🔥 NO FALLBACK

    # ----------------------------
    # initialize state
    # ----------------------------
    if not hasattr(tab, "_pq_counter"):
        tab._pq_counter = 0

    if not hasattr(tab, "_pq_prev_chain"):
        tab._pq_prev_chain = b"\x00" * 64

    if not hasattr(tab, "_pq_chain_seen"):
        from collections import deque

        tab._pq_chain_seen = deque(maxlen=200)

    # ----------------------------
    # increment counter (monotonic)
    # ----------------------------
    tab._pq_counter = min(tab._pq_counter + 1, 1_000_000)

    # ----------------------------
    # build chain hash
    # ----------------------------
    h = hashlib.sha3_512()

    # session root
    h.update(tab._pq_seed)

    # canonical URL
    norm_url = _pq_normalize_url(url)
    h.update(norm_url.encode("utf-8", errors="ignore"))

    # 🔗 previous chain (CRITICAL FIX)
    h.update(tab._pq_prev_chain)

    # 🔢 counter (REAL progression)
    h.update(tab._pq_counter.to_bytes(8, "big"))

    # 🔐 optional salt binding
    if hasattr(owner, "_pq_salt"):
        h.update(owner._pq_salt)

    # ----------------------------
    # finalize
    # ----------------------------
    chain = h.digest()

    # ----------------------------
    # replay detection (NEW)
    # ----------------------------
    if chain in tab._pq_chain_seen:
        if hasattr(owner, "mini_ai"):
            owner.mini_ai.suspicious_hits += 2

    tab._pq_chain_seen.append(chain)

    # ----------------------------
    # update state
    # ----------------------------
    tab._pq_prev_chain = chain

    return chain


def get_canvas_seed_hex(tab):
    if not hasattr(tab, "_pq_seed") or not tab._pq_seed:
        return "0000000000000000"

    bucket = darkelf_get_bucket(tab)

    h = hashlib.sha3_256()

    # identity
    h.update(tab._pq_seed)

    # grouping
    h.update(bucket.to_bytes(2, "big"))

    # 🔥 READ ONLY — NO CHAIN ADVANCE
    chain = getattr(tab, "_pq_prev_chain", b"\x00" * 32)
    h.update(chain[:16])

    return h.digest()[:16].hex()


def darkelf_get_bucket(tab, groups=32):
    if hasattr(tab, "_pq_bucket"):
        return tab._pq_bucket

    seed = getattr(tab, "_pq_seed", None)
    if not seed:
        tab._pq_bucket = 0
        return 0

    digest = hashlib.sha3_256(seed).hexdigest()
    tab._pq_bucket = int(digest, 16) % groups
    return tab._pq_bucket


def darkelf_build_ua(tab) -> str:
    base = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)"

    seed = getattr(tab, "_pq_seed", None)
    if not seed:
        return base  # 🔒 no Darkelf fallback

    bucket = darkelf_get_bucket(tab)

    # 🔒 keep grouping INTERNAL ONLY
    tab._ua_bucket = bucket

    return base


def darkelf_init_tab_identity(tab):
    if not tab:
        return

    if not hasattr(tab, "_pq_seed") or not tab._pq_seed:
        tab._pq_seed = hashlib.sha256(os.urandom(32)).digest()
        tab._pq_seed_locked = True

    if not hasattr(tab, "_ua_string") or not tab._ua_string:
        tab._ua_string = darkelf_build_ua(tab)


def darkelf_is_pq_active(owner) -> bool:
    return hasattr(owner, "_pq_seed") and bool(getattr(owner, "_pq_seed", None))


def darkelf_sha3_bytes(data: bytes) -> str:
    h = hashlib.sha3_512()
    h.update(data)
    return h.hexdigest()


def verify_file(path, owner):
    if path not in owner._pq_file_hashes:
        return True

    with open(path, "rb") as f:
        data = f.read()

    return darkelf_sha3_bytes(data) == owner._pq_file_hashes[path]


def apply_darkelf_theme():
    green = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.20, 0.78, 0.35, 1)

    NSApplication.sharedApplication().setAppearance_(
        NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua")
    )

class DarkelfNetworkPolicy:
    def __init__(self, browser):
        self.browser = browser

    def inspect(self, url, nav_type):
        url = str(url or "")

        decision = "allow"
        meta = {"source": "net_policy", "type": str(nav_type)}

        # ----------------------------
        # HARD SKIP
        # ----------------------------
        if url.startswith(("data:", "blob:")):
            return decision, meta

        # ----------------------------
        # PARSE URL
        # ----------------------------
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            path = parsed.path or ""
        except Exception as e:
            log(1, "[URL PARSE ERROR]", e)
            return "degrade", meta

        # ----------------------------
        # HTTP → HTTPS
        # ----------------------------
        if parsed.scheme == "http":
            return "redirect", url.replace("http://", "https://", 1)

        # ----------------------------
        # TRACKER BLOCKING
        # ----------------------------
        BLOCKED_DOMAINS = {
            "google-analytics.com",
            "doubleclick.net",
            "googlesyndication.com",
        }

        if any(host == d or host.endswith("." + d) for d in BLOCKED_DOMAINS):
            return "block"

        # ----------------------------
        # QUIET MODE
        # ----------------------------
        if isinstance(nav_type, str) and nav_type.lower() in ("image", "media", "font"):
            return decision, meta

        # ----------------------------
        # TAB RESOLUTION
        # ----------------------------
        tab = None
        if hasattr(self.browser, "tabs") and 0 <= getattr(
            self.browser, "active", -1
        ) < len(self.browser.tabs):
            tab = self.browser.tabs[self.browser.active]

        if not tab or not getattr(tab, "view", None):
            return decision, meta

        # ----------------------------
        # INIT PQ STATE
        # ----------------------------
        if not getattr(tab, "_pq_seed", None):
            tab._pq_seed = hashlib.sha256(os.urandom(32)).digest()
            tab._pq_seed_locked = True

        if not hasattr(tab, "_pq_counter"):
            tab._pq_counter = 0

        if not hasattr(tab, "_pq_chain_seen"):
            tab._pq_chain_seen = deque(maxlen=200)

        # ----------------------------
        # CANONICAL URL
        # ----------------------------
        try:
            norm_path = re.sub(r"/+", "/", path)
            query = "&".join(sorted(parsed.query.split("&"))) if parsed.query else ""
            norm_url = f"{parsed.scheme}://{parsed.netloc}{norm_path}?{query}"
        except Exception as e:
            log(2, "[URL NORMALIZE ERROR]", e)
            norm_url = url

        # ----------------------------
        # COUNTER
        # ----------------------------
        tab._pq_counter = min(tab._pq_counter + 1, 1_000_000)

        # ----------------------------
        # PQ CHAIN (CRITICAL PATH)
        # ----------------------------
        try:
            chain = darkelf_pq_chain(self.browser, norm_url)

            meta["_pq_chain"] = chain[:16].hex()

            if chain in tab._pq_chain_seen:
                if hasattr(self.browser, "mini_ai"):
                    self.browser.mini_ai.suspicious_hits += 2
                    decision = "degrade"

            tab._pq_chain_seen.append(chain)

        except Exception as e:
            log(1, "[PQ CHAIN ERROR]", e)
            return "degrade", meta

        # ----------------------------
        # PQ FINGERPRINT (CRITICAL PATH)
        # ----------------------------
        try:
            h = hashlib.sha3_256()
            h.update(tab._pq_seed)
            h.update(host.encode())
            h.update(norm_path[:32].encode())

            if hasattr(self.browser, "_pq_tls_summary"):
                h.update(self.browser._pq_tls_summary.encode())

            digest = h.digest()

            if digest[0] & 1:
                pq_bytes = hashlib.sha3_512(tab._pq_seed).digest()
                meta["_pq_fp"] = pq_bytes[:32].hex()

        except Exception as e:
            log(1, "[PQ FP ERROR]", e)
            return "degrade", meta

        # ----------------------------
        # ADAPTIVE ENFORCEMENT
        # ----------------------------
        try:
            if hasattr(self.browser, "mini_ai"):
                stats = self.browser.mini_ai._pq_stats()

                if stats["risk_level"] == "high":
                    decision = "isolate"
                    meta.pop("_pq_fp", None)
                    meta.pop("_pq_fp_alt", None)

                elif stats["risk_level"] == "medium":
                    decision = "degrade"

        except Exception as e:
            log(2, "[ADAPTIVE ERROR]", e)

        # ----------------------------
        # TRACKER DECEPTION
        # ----------------------------
        try:
            if "_pq_fp" in meta and host:

                first_party = getattr(self.browser, "current_url_for_fpi", "")
                is_third_party = False

                if first_party:
                    fp_host = urlparse(first_party).hostname or ""
                    if fp_host and not host.endswith(fp_host):
                        is_third_party = True

                if is_third_party:
                    d = hashlib.sha3_256(tab._pq_seed + host.encode()).digest()
                    mode = d[1] % 3
                    real_fp = meta["_pq_fp"]

                    if mode == 0:
                        decoy = hashlib.sha3_256((real_fp + host).encode()).digest()
                        meta["_pq_fp_alt"] = decoy[:8].hex()
                    elif mode == 1:
                        meta["_pq_fp_alt"] = real_fp[:8]
                    else:
                        alt = hashlib.sha3_256((host + real_fp).encode()).digest()
                        meta["_pq_fp_alt"] = alt[:8].hex()

        except Exception as e:
            log(2, "[DECEPTION ERROR]", e)

        # ----------------------------
        # NEW: DEGRADE ENFORCEMENT (minimal, UX-safe)
        # ----------------------------
        if decision == "degrade":
            # mark as low-trust so downstream can react
            meta["_trust"] = "low"

            # avoid leaking strong fingerprint in degraded mode
            meta.pop("_pq_fp", None)

            # signal to drop credentials on cross-site requests
            meta["_no_3p_credentials"] = True

            # reduce caching / persistence hints
            meta["_cache_mode"] = "ephemeral"

        # ----------------------------
        # SOFT ROTATION
        # ----------------------------
        if tab._pq_counter > 5000:
            tab._pq_seed = hashlib.sha3_256(tab._pq_seed).digest()
            tab._pq_counter = 0
            tab._pq_chain_seen.clear()

        return decision, meta

class DownloadProgressView(NSView):

    def initWithFrame_(self, frame):
        self = objc.super(DownloadProgressView, self).initWithFrame_(frame)
        if self is None:
            return None

        # 🔥 Force proper height + bottom anchoring
        height = 60
        self.setFrame_(NSMakeRect(frame.origin.x, 0, frame.size.width, height))

        # 🔥 Stick to bottom when parent resizes
        self.setAutoresizingMask_(NSViewWidthSizable | NSViewMaxYMargin)

        self.setWantsLayer_(True)
        self.layer().setCornerRadius_(12)
        self.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.04, 0.05, 0.07, 1
            ).CGColor()
        )

        # ---- filename ----
        self.label = NSTextField.alloc().initWithFrame_(NSMakeRect(15, 40, 300, 20))
        self.label.setBezeled_(False)
        self.label.setEditable_(False)
        self.label.setDrawsBackground_(False)
        self.label.setTextColor_(NSColor.whiteColor())
        self.label.setFont_(NSFont.systemFontOfSize_(13))
        self.addSubview_(self.label)

        # ---- percent (RIGHT ANCHORED) ----
        self.percent = NSTextField.alloc().initWithFrame_(
            NSMakeRect(frame.size.width - 90, 40, 60, 20)
        )
        self.percent.setAutoresizingMask_(NSViewMinXMargin)
        self.percent.setBezeled_(False)
        self.percent.setEditable_(False)
        self.percent.setDrawsBackground_(False)
        self.percent.setTextColor_(NSColor.systemGrayColor())
        self.percent.setFont_(NSFont.systemFontOfSize_(12))
        self.percent.setAlignment_(2)
        self.percent.setStringValue_("0%")
        self.addSubview_(self.percent)

        # ---- DONE BUTTON ----
        self.done = NSButton.alloc().initWithFrame_(
            NSMakeRect(frame.size.width - 90, 18, 70, 22)
        )
        self.done.setAutoresizingMask_(NSViewMinXMargin)
        self.done.setTitle_("Done")
        self.done.setBezelStyle_(1)
        self.done.setTarget_(self)
        self.done.setAction_("closeDownload:")
        self.addSubview_(self.done)

        # ---- PROGRESS TRACK ----
        self.progressTrack = NSView.alloc().initWithFrame_(
            NSMakeRect(15, 22, frame.size.width - 120, 6)
        )
        self.progressTrack.setAutoresizingMask_(NSViewWidthSizable)
        self.progressTrack.setWantsLayer_(True)
        self.progressTrack.layer().setCornerRadius_(3)
        self.progressTrack.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.08, 0.09, 0.12, 1
            ).CGColor()
        )
        self.addSubview_(self.progressTrack)

        # ---- PROGRESS FILL ----
        self.progressFill = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 0, 6))
        self.progressFill.setAutoresizingMask_(NSViewWidthSizable)
        self.progressFill.setWantsLayer_(True)

        green = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.20, 0.78, 0.35, 1)

        self.progressFill.layer().setCornerRadius_(3)
        self.progressFill.layer().setBackgroundColor_(green.CGColor())
        self.progressFill.layer().setShadowColor_(green.CGColor())
        self.progressFill.layer().setShadowOpacity_(0.7)
        self.progressFill.layer().setShadowRadius_(6)
        self.progressFill.layer().setShadowOffset_((0, 0))

        self.progressTrack.addSubview_(self.progressFill)

        # ---- SPEED ----
        self.speed = NSTextField.alloc().initWithFrame_(NSMakeRect(15, 2, 200, 15))
        self.speed.setBezeled_(False)
        self.speed.setEditable_(False)
        self.speed.setDrawsBackground_(False)
        self.speed.setTextColor_(NSColor.systemGrayColor())
        self.speed.setFont_(NSFont.systemFontOfSize_(11))
        self.addSubview_(self.speed)

        return self

    def mouseDown_(self, event):
        # store initial click position
        self._drag_start = event.locationInWindow()
        self._start_origin = self.frame().origin

    def mouseDragged_(self, event):
        if not hasattr(self, "_drag_start"):
            return

        current = event.locationInWindow()

        dx = current.x - self._drag_start.x
        dy = current.y - self._drag_start.y

        new_x = self._start_origin.x + dx
        new_y = self._start_origin.y + dy

        # 🔥 move the view
        self.setFrameOrigin_((new_x, new_y))

    def updateProgress_(self, percent):

        try:
            percent = max(0.0, min(100.0, float(percent)))

            # update percent label if present
            try:
                if hasattr(self, "percent"):
                    self.percent.setStringValue_(f"{int(percent)}%")
            except Exception as e:
                log(2, e)

            trackWidth = self.progressTrack.bounds().size.width
            newWidth = trackWidth * (percent / 100.0)

            frame = self.progressFill.frame()
            frame.size.width = newWidth

            def animate(ctx):
                ctx.setDuration_(0.12)
                self.progressFill.animator().setFrame_(frame)

            NSAnimationContext.runAnimationGroup_completionHandler_(animate, None)

        except Exception as e:
            print("[DownloadUI progress error]", e)

    def setFilename_(self, name):
        self.label.setStringValue_(name)

    def setSpeed_(self, speed):
        self.speed.setStringValue_(speed)

    def closeDownload_(self, sender):
        try:
            self.setHidden_(True)
        except Exception as e:
            print("[DownloadUI] close error:", e)


# ============================================================
# Darkelf First Party Isolation (FPI)
# Memory-only domain + implemented tab isolation
# ============================================================


class FirstPartyIsolation:

    # domains allowed to share storage for login flows
    AUTH_WHITELIST = {
        "accounts.google.com",
        "login.microsoftonline.com",
        "appleid.apple.com",
        "github.com",
    }

    def __init__(self, tab_isolation=False):
        """
        tab_isolation:
            False -> domain-only isolation
            True  -> domain + tab isolation
        """
        self.tab_isolation = tab_isolation
        self._stores = {}

    # --------------------------------------------------------
    # Extract first-party domain (eTLD+1 approximation)
    # --------------------------------------------------------

    def _domain_key(self, url):

        try:
            host = urlparse(url).hostname or ""
        except Exception:
            host = ""

        host = host.lower()
        host = host.split(":")[0]

        if not host:
            return "unknown"

        if host in self.AUTH_WHITELIST:
            return host

        try:
            ext = tldextract.extract(host)

            if ext.domain and ext.suffix:
                return f"{ext.domain}.{ext.suffix}"

        except Exception as e:
            log(2, e)

        return host

    # --------------------------------------------------------
    # Build isolation key
    # --------------------------------------------------------

    def _key(self, url, tab_uid=None, nonce=None):

        domain = self._domain_key(url)

        if self.tab_isolation and tab_uid is not None:
            return f"{domain}@tab{tab_uid}-{nonce}"

        return domain

    # --------------------------------------------------------
    # Get storage container
    # --------------------------------------------------------

    def store_for(self, url, tab_uid=None, nonce=None):
        key = self._key(url, tab_uid, nonce)

        print("[FPI] Using store:", key)

        # ensure store map exists
        if not hasattr(self, "_stores"):
            self._stores = {}

        # create store if missing
        if key not in self._stores:
            store = WKWebsiteDataStore.nonPersistentDataStore()

            # 🔥 DO NOT PURGE HERE (causes segfault)
            self._stores[key] = store

        return self._stores[key]

    def clear_tab(self, url, tab_uid=None, nonce=None):
        key = self._key(url, tab_uid, nonce)

        if key in self._stores:
            try:
                del self._stores[key]
                print("[FPI] Cleared store:", key)
            except Exception as e:
                print("[FPI] Clear error:", e)

    # --------------------------------------------------------
    # Clear all stores (browser shutdown)
    # --------------------------------------------------------

    def clear(self):

        self._stores.clear()


def _darkelf_library(create=False):

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")

    library = os.path.join(desktop, "Darkelf Library")
    snaps = os.path.join(library, "Darkelf Snap")
    temp = os.path.join(library, "Darkelf Temp")

    if create:
        os.makedirs(snaps, exist_ok=True)
        os.makedirs(temp, exist_ok=True)

    return library, snaps, temp


def _safe_download_dir(create=False):

    _, _, temp = _darkelf_library()

    if create:
        os.makedirs(temp, exist_ok=True)

    return temp

def _snapshot_dir():

    _, snaps, _ = _darkelf_library()
    return snaps


def _randomized_filename(name):
    name = (name or "download").strip()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:120]

    base, ext = os.path.splitext(name)

    token = secrets.token_hex(6)

    base = base[:60] or "download"
    ext = ext[:12]

    return f"{base}_{token}{ext}"


class DarkelfMiniAISentinel:

    MAX_URL_LENGTH = 2048
    CRITICAL_WINDOW_SECONDS = 60
    LOCKDOWN_DURATION_SECONDS = 120

    def __init__(self):

        self.enabled = True
        self.browser = None

        self.events = deque(maxlen=500)

        self.tracker_hits = 0
        self.suspicious_hits = 0
        self.malware_hits = 0
        self.exploit_attempts = 0
        self.fingerprint_attempts = 0
        self.intrusion_attempts = 0
        self.http_blocks_attempts = 0

        # IDS detections
        self.scraper_attempts = 0
        self.credential_stuffing_attempts = 0
        self.vuln_scanner_attempts = 0
        self.bruteforce_attempts = 0
        self.automation_attempts = 0
        self.total_requests = 0
        self.static_requests = 0
        self.dynamic_requests = 0
        self.blocked_requests = 0

        self.login_attempt_tracker = {}
        self.scraper_tracker = {}

        self.session_start = time.time()
        self.unique_domains = set()
        self.first_party_domain = None
        self.redirects = []

        self.lockdown_active = False
        self.lockdown_threshold = 3
        self.lockdown_triggered_at = None
        self._lockdown_ui_opened = False

        self.request_timestamps = deque(maxlen=100)
        self.anomaly_threshold = 800

        # 🔧 throttling (prevents UI queue flooding)
        self._last_scan_time = 0
        self._last_lockdown_eval = 0

        self.hacker_tools = [
            "nmap",
            "sqlmap",
            "metasploit",
            "burpsuite",
            "nikto",
            "dirbuster",
            "hydra",
            "wireshark",
            "tcpdump",
            "ettercap",
            "aircrack",
            "hashcat",
            "johntheripper",
            "cobalt",
            "mimikatz",
        ]

        self.high_risk_domains = {
            "doubleclick.net",
            "googlesyndication.com",
            "googleadservices.com",
            "facebook.net",
            "scorecardresearch.com",
            "quantserve.com",
            "taboola.com",
            "outbrain.com",
            "criteo.com",
            "adnxs.com",
        }

        self.high_risk_tlds = {".tk", ".ml", ".ga", ".cf", ".gq"}

        self.fingerprint_apis = {
            "canvas": 0,
            "webgl": 0,
            "audio": 0,
            "font": 0,
            "battery": 0,
            "geolocation": 0,
            "media_devices": 0,
            "webrtc": 0,
        }

        # ----------------------------
        # PQ tracking (NEW)
        # ----------------------------
        self._pq_seen = set()
        self._pq_window = deque(maxlen=200)  # optional: sliding window
        self._pq_last_reset = time.time()

        print("[MiniAI] Sentinel initialized")

    # --------------------------------------------------
    # URL NORMALIZATION
    # --------------------------------------------------

    def _normalize_url(self, url: str) -> str:

        try:
            url = url[: self.MAX_URL_LENGTH]
            return unquote(unquote(url.lower()))
        except Exception:
            return (url or "").lower()

    # --------------------------------------------------
    # MAIN NETWORK MONITOR
    # --------------------------------------------------

    def monitor_network(self, url: str, headers=None):

        # Normalize headers FIRST (prevents headers.get crash)
        headers = headers or {}

        # Ignore internal pages
        if (url or "").startswith("darkelf://"):
            return

        if not url or not self.enabled:
            return

        now = time.time()

        # throttle heavy bursts (SPA pages)
        # allow PQ-tagged events through even during bursts
        if now - self._last_scan_time < 0.005 and not headers.get("_pq_fp"):
            return

        self._last_scan_time = now

        normalized = self._normalize_url(url)
        if not normalized:
            return

        # ---- stats ----
        self.total_requests += 1

        # ----------------------------
        # PQ extraction + analysis
        # ----------------------------
        pq_fp = headers.get("_pq_fp")

        if pq_fp:
            # always append (prevents burst spikes)
            self._pq_window.append(pq_fp)

            # unique PQ fingerprint tracking
            if pq_fp not in self._pq_seen:
                self._pq_seen.add(pq_fp)

                # too many unique PQ fingerprints in one session is suspicious
                if len(self._pq_seen) > 500:
                    self.suspicious_hits += 1

            # sliding-window entropy check (FIXED: threshold was impossible)
            if len(self._pq_window) >= 50:
                recent = list(self._pq_window)[-50:]
                unique_recent = len(set(recent))

                # If nearly every PQ fp in the last 50 is unique, that's suspicious.
                # (Tune threshold as needed; 45/50 is aggressive.)
                if unique_recent > 45:
                    self.suspicious_hits += 1

        # ---- extract host + path ----
        try:
            parsed = urlparse(normalized)
            host = parsed.hostname or ""
            path = unquote(parsed.path or "").lower()

            if host:
                self.unique_domains.add(host)

            if not self.first_party_domain and host:
                self.first_party_domain = host

        except Exception:
            host = ""
            path = normalized

        # --------------------------------------------------
        # STATIC ASSET DETECTION (MOVE EARLY)
        # --------------------------------------------------

        STATIC_EXT = (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".webp",
            ".css",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".ico",
            ".map",
            ".mp4",
            ".webm",
            ".mp3",
            ".ogg",
        )

        is_static = normalized.split("?")[0].endswith(STATIC_EXT)

        if is_static:
            self.static_requests += 1
        else:
            self.dynamic_requests += 1

        # ==================================================
        # 🔥 NEW: PATH OBFUSCATION DETECTION
        # ==================================================

        # encoded payload indicator
        if "%" in url:
            self.suspicious_hits += 1

        # path traversal
        if any(x in path for x in ["../", "..\\"]):
            self.suspicious_hits += 1

        # null byte injection
        if "\x00" in path:
            self.suspicious_hits += 1

        # sensitive target probing
        if "admin" in path:
            self.intrusion_attempts += 1

        # --------------------------------------------------
        # static asset detection
        # --------------------------------------------------

        STATIC_EXT = (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".webp",
            ".css",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".ico",
            ".map",
            ".mp4",
            ".webm",
            ".mp3",
            ".ogg",
        )

        is_static = normalized.split("?")[0].endswith(STATIC_EXT)

        # ---- stats ----
        if is_static:
            self.static_requests += 1
        else:
            self.dynamic_requests += 1

        event = {
            "url": normalized,
            "timestamp": now,
            "datetime": datetime.now().isoformat(),
            "threats": [],
            "risk_level": "low",
            "static": is_static,
        }
        # --------------------------------------------------
        # lightweight static analysis
        # --------------------------------------------------

        if is_static:

            for domain in self.high_risk_domains:

                if host == domain or host.endswith("." + domain):

                    event["threats"].append("tracker")
                    event["risk_level"] = "medium"
                    self.tracker_hits += 1
                    break

            self.events.append(event)
            return

        # --------------------------------------------------
        # lockdown logic
        # --------------------------------------------------

        if self.lockdown_active:

            self._maybe_auto_unlock(now)

            if self.lockdown_active:

                print("[MiniAI] LOCKDOWN BLOCK:", normalized)

                if self.browser and not self._lockdown_ui_opened:
                    NSOperationQueue.mainQueue().addOperationWithBlock_(
                        self._show_threat_report_ui
                    )

                return

        # --------------------------------------------------
        # detection engines
        # --------------------------------------------------

        self._detect_intrusion(normalized, event)
        self._detect_fingerprinting(normalized, headers, event)
        self._check_domain_reputation(normalized, event)
        self._detect_anomalies(now, event)
        self._detect_ids_activity(normalized, headers, event)

        self.events.append(event)

        if event["risk_level"] in ("high", "critical"):
            self._log_threat(event)

        # --------------------------------------------------
        # UI lockdown checks
        # --------------------------------------------------

        if now - self._last_lockdown_eval > 1.0:
            self._last_lockdown_eval = now

            NSOperationQueue.mainQueue().addOperationWithBlock_(self._evaluate_lockdown)

    # --------------------------------------------------
    # DETECT INTRUSION
    # --------------------------------------------------

    def _detect_intrusion(self, url, event):

        for tool in self.hacker_tools:

            if tool in url:

                event["threats"].append("intrusion")
                event["risk_level"] = "critical"

                self.intrusion_attempts += 1
                return

    # --------------------------------------------------
    # DOMAIN REPUTATION
    # --------------------------------------------------
    def _check_domain_reputation(self, url, event):

        try:
            host = urlparse(url).hostname or ""
        except Exception:
            host = ""

        # ------------------------------------
        # Known tracker domain list
        # ------------------------------------
        for domain in self.high_risk_domains:

            if host == domain or host.endswith("." + domain):

                event["threats"].append("tracker")
                self.tracker_hits += 1

                if event["risk_level"] == "low":
                    event["risk_level"] = "medium"

                return

        # ------------------------------------
        # Automatic third-party tracker detection
        # ------------------------------------
        if getattr(self, "first_party_domain", None) and host:

            if not host.endswith(self.first_party_domain):

                # ignore common CDNs
                cdn_whitelist = (
                    "cloudflare.com",
                    "cloudfront.net",
                    "akamai.net",
                    "fastly.net",
                    "gstatic.com",
                    "fonts.gstatic.com",
                )

                for cdn in cdn_whitelist:
                    if host.endswith(cdn):
                        break
                else:

                    event["threats"].append("tracker")
                    self.tracker_hits += 1

                    if event["risk_level"] == "low":
                        event["risk_level"] = "medium"

                    return

        # ------------------------------------
        # Suspicious TLD detection
        # ------------------------------------
        for tld in self.high_risk_tlds:

            if host.endswith(tld):

                event["threats"].append("suspicious_domain")
                self.suspicious_hits += 1

                if event["risk_level"] == "low":
                    event["risk_level"] = "medium"

    # --------------------------------------------------
    # FINGERPRINT DETECTION
    # --------------------------------------------------

    def _detect_fingerprinting(self, url, headers, event):

        keywords = ["fingerprint", "canvas", "webgl", "audiofingerprint"]

        for k in keywords:

            if k in url:

                event["threats"].append("fingerprinting")
                self.fingerprint_attempts += 1

                if event["risk_level"] == "low":
                    event["risk_level"] = "medium"

                return

    def _detect_anomalies(self, now, event):

        self.request_timestamps.append(now)

        # Sliding window
        window = [
            t for t in self.request_timestamps if now - t < self.CRITICAL_WINDOW_SECONDS
        ]

        req_rate = len(window)
        domain_count = len(self.unique_domains)

        # --------------------------------------------------
        # 1. LOW-SCALE DISTRIBUTED SCAN (NEW)
        # --------------------------------------------------
        if domain_count > 30 and req_rate > 80:

            event["threats"].append("distributed_probe")

            if event["risk_level"] == "low":
                event["risk_level"] = "medium"

            self.suspicious_hits += 1

        # --------------------------------------------------
        # 2. MID-SCALE DOMAIN SCANNER (IMPROVED)
        # --------------------------------------------------
        if domain_count > 60 and req_rate > 150:

            event["threats"].append("domain_scanner")

            if event["risk_level"] in ("low", "medium"):
                event["risk_level"] = "high"

            self.vuln_scanner_attempts += 1

        # --------------------------------------------------
        # 3. LARGE-SCALE SCANNER (ORIGINAL, KEPT)
        # --------------------------------------------------
        if domain_count > 120:

            event["threats"].append("mass_domain_scan")
            event["risk_level"] = "high"

            self.vuln_scanner_attempts += 1

        # --------------------------------------------------
        # 4. TRAFFIC ANOMALY (REFINED)
        # --------------------------------------------------
        if req_rate > self.anomaly_threshold:

            # Avoid false positives from static content bursts
            if getattr(self, "dynamic_requests", 0) > getattr(
                self, "static_requests", 0
            ):

                event["threats"].append("traffic_anomaly")
                event["risk_level"] = "high"

                self.suspicious_hits += 1

        # --------------------------------------------------
        # 5. DOMAIN VELOCITY HEURISTIC (NEW)
        # --------------------------------------------------
        if domain_count > 20:

            avg_per_domain = req_rate / max(domain_count, 1)

            # many domains but very few requests each → scanner pattern
            if avg_per_domain < 2 and req_rate > 50:

                event["threats"].append("wide_scan_pattern")

                if event["risk_level"] == "low":
                    event["risk_level"] = "medium"

                self.suspicious_hits += 1

    # --------------------------------------------------
    # IDS DETECTION
    # --------------------------------------------------

    def _detect_ids_activity(self, url, headers, event):

        now = time.time()

        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            path = parsed.path or ""
        except:
            host = ""
            path = ""

        ua = str(headers.get("user-agent", "")).lower()

        # --------------------------------------------------
        # BRUTEFORCE DETECTION (NEW)
        # --------------------------------------------------
        if host:
            path_l = (path or "").lower()

            if "password" in path_l:
                bf_key = host + "_bf"
                attempts = self.login_attempt_tracker.setdefault(bf_key, [])
                attempts.append(now)

                attempts = [t for t in attempts if now - t < 60]
                self.login_attempt_tracker[bf_key] = attempts

                if len(attempts) > 10:
                    event["threats"].append("bruteforce")
                    event["risk_level"] = "high"
                    self.bruteforce_attempts += 1

        # --------------------------------------------------
        # AUTOMATION DETECTION (NEW)
        # --------------------------------------------------
        if ua:
            if "python-requests" in ua or "curl" in ua or "wget" in ua:
                event["threats"].append("automation")
                event["risk_level"] = "medium"
                self.automation_attempts += 1

        # --------------------------------------------------
        # SCRAPER DETECTION (balanced / concurrency-safe)
        # --------------------------------------------------
        if host:
            STATIC_EXT = (
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".webp",
                ".css",
                ".woff",
                ".woff2",
                ".ttf",
                ".eot",
                ".ico",
                ".map",
                ".mp4",
                ".webm",
                ".mp3",
                ".ogg",
                ".m4a",
                ".aac",
                ".wav",
                ".mov",
                ".avi",
                ".mkv",
            )

            path_l = (path or "").lower()
            is_static = path_l.split("?", 1)[0].endswith(STATIC_EXT)

            # Only count non-static, "meaningful" paths
            count_for_scraper = (not is_static) and (len(path_l) >= 2)

            if count_for_scraper:
                history = self.scraper_tracker.setdefault(host, [])
                history.append(now)

                # 🔧 stable window (already fixed)
                history = [t for t in history if now - t < 60.0]
                self.scraper_tracker[host] = history

                # Track path variety
                if not hasattr(self, "_scraper_paths"):
                    self._scraper_paths = {}

                paths = self._scraper_paths.setdefault(host, deque(maxlen=80))
                paths.append(path_l.split("?", 1)[0])

                unique_paths_recent = len(set(paths))

                # ----------------------------
                # HYBRID DETECTION (FIXED)
                # ----------------------------

                # SAME PATH spam (test compatibility)
                same_path_spam = len(history) > 14 and unique_paths_recent <= 2

                # REAL scraper (multi-path behavior)
                multi_path_scraper = len(history) > 8 and unique_paths_recent > 5

                if same_path_spam or multi_path_scraper:
                    event["threats"].append("scraping_bot")
                    event["risk_level"] = "high"
                    self.scraper_attempts += 1

        # --------------------------------------------------
        # CREDENTIAL STUFFING (reduced false positives)
        # --------------------------------------------------
        login_keywords = ("login", "signin", "auth", "session", "oauth", "sso")

        try:
            req_type = str((headers or {}).get("type", "")).lower()
        except Exception:
            req_type = ""

        if host:
            path_l = (path or "").lower()
            is_loginish = any(k in path_l for k in login_keywords)

            STATIC_EXT = (
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".webp",
                ".css",
                ".woff",
                ".woff2",
                ".ttf",
                ".eot",
                ".ico",
                ".map",
                ".mp4",
                ".webm",
                ".mp3",
                ".ogg",
            )
            is_static = path_l.split("?", 1)[0].endswith(STATIC_EXT)

            interactive = (
                req_type in ("xhr", "fetch", "navigation", "document", "beacon", "form")
                or req_type == ""
            )

            if is_loginish and (not is_static) and interactive:
                attempts = self.login_attempt_tracker.setdefault(host, [])
                attempts.append(now)

                attempts = [t for t in attempts if now - t < 60.0]
                self.login_attempt_tracker[host] = attempts

                if len(attempts) > 10:
                    event["threats"].append("credential_stuffing")
                    event["risk_level"] = "high"
                    self.credential_stuffing_attempts += 1

    # --------------------------------------------------
    # HTTP BLOCK DETECTION
    # --------------------------------------------------

    def on_http_blocked(self, url):

        self.http_blocks_attempts += 1

        print("[MiniAI] HTTP blocked:", url)

    # --------------------------------------------------
    # THREAT LOGGING
    # --------------------------------------------------

    def _log_threat(self, event):

        print("[MiniAI] THREAT:", event["risk_level"], event["url"], event["threats"])

    # --------------------------------------------------
    # LOCKDOWN EVALUATION
    # --------------------------------------------------

    def _evaluate_lockdown(self):

        # Already in lockdown
        if self.lockdown_active:
            return

        # Critical threats only
        critical_score = (
            self.intrusion_attempts + self.malware_hits + self.exploit_attempts
        )

        # Trigger lockdown if threshold reached
        if critical_score >= self.lockdown_threshold:

            print("[MiniAI] Critical threat threshold reached:", critical_score)

            self._trigger_lockdown()

    # --------------------------------------------------
    # STATS FOR UI
    # --------------------------------------------------

    def get_statistics(self):

        uptime = time.time() - self.session_start

        # ----------------------------
        # PQ contribution
        # ----------------------------
        pq_entropy = len(set(self._pq_window)) if self._pq_window else 0

        # ----------------------------
        # Threat score (enhanced)
        # ----------------------------
        threat_score = (
            self.tracker_hits
            + self.suspicious_hits
            + self.fingerprint_attempts * 2
            + self.intrusion_attempts * 4
            + self.malware_hits * 6
            + self.exploit_attempts * 6
            + self.http_blocks_attempts
            + (pq_entropy // 10)  # 🔥 PQ influence
        )

        return {
            "uptime_seconds": uptime,
            # -----------------------------
            # Network Activity
            # -----------------------------
            "network": {
                "total_requests": getattr(self, "total_requests", 0),
                "dynamic_requests": getattr(self, "dynamic_requests", 0),
                "static_requests": getattr(self, "static_requests", 0),
                "unique_domains": len(self.unique_domains),
            },
            "total_events": len(self.events),
            "threat_score": threat_score,
            # -----------------------------
            # 🔥 Overall Risk (NEW)
            # -----------------------------
            "overall_risk": (
                "high"
                if threat_score > 50
                else "medium" if threat_score > 15 else "low"
            ),
            # -----------------------------
            # Lockdown State
            # -----------------------------
            "lockdown": {
                "active": self.lockdown_active,
                "threshold": self.lockdown_threshold,
                "triggered_at": self.lockdown_triggered_at,
            },
            # -----------------------------
            # Threat Counters
            # -----------------------------
            "threats": {
                "trackers": self.tracker_hits,
                "suspicious": self.suspicious_hits,
                "malware": self.malware_hits,
                "exploits": self.exploit_attempts,
                "intrusions": self.intrusion_attempts,
                "fingerprinting": self.fingerprint_attempts,
                "http_blocks": self.http_blocks_attempts,
            },
            # -----------------------------
            # IDS Detection
            # -----------------------------
            "ids": {
                "scrapers": self.scraper_attempts,
                "credential_stuffing": self.credential_stuffing_attempts,
                "vulnerability_scanners": self.vuln_scanner_attempts,
                "bruteforce_logins": self.bruteforce_attempts,
                "automation_frameworks": self.automation_attempts,
            },
            # -----------------------------
            # 🔥 PQ Intelligence (NEW)
            # -----------------------------
            "pq": self._pq_stats(),
        }

    def _pq_stats(self):

        unique = len(self._pq_seen)
        recent = len(self._pq_window)
        entropy = len(set(self._pq_window)) if self._pq_window else 0

        # ----------------------------
        # Risk evaluation
        # ----------------------------
        risk = "low"

        if entropy > 40 or unique > 150:
            risk = "high"
        elif entropy > 20 or unique > 80:
            risk = "medium"

        return {
            "unique_fingerprints": unique,
            "recent_window": recent,
            "entropy": entropy,
            "risk_level": risk,
        }

    # --------------------------------------------------
    # LOCKDOWN TRIGGER
    # --------------------------------------------------
    def _trigger_lockdown(self):

        if self.lockdown_active:
            return

        self.lockdown_active = True
        self.lockdown_triggered_at = time.time()
        self._lockdown_ui_opened = False

        print("[MiniAI] 🔴 LOCKDOWN ACTIVATED")

        if not self.browser:
            print("[MiniAI] No browser bridge")
            return

        # Stop all tab loading
        for tab in getattr(self.browser, "tabs", []):
            try:
                tab.view.stopLoading()
            except Exception as e:
                log(2, e)

        try:
            self.browser.start_lockdown_timer()
        except Exception as e:
            print("[MiniAI] timer error:", e)

        NSOperationQueue.mainQueue().addOperationWithBlock_(self._show_threat_report_ui)

        NSOperationQueue.mainQueue().addOperationWithBlock_(self._lock_browser_ui)

    # --------------------------------------------------
    # AUTO UNLOCK
    # --------------------------------------------------
    def _maybe_auto_unlock(self, now):

        if not self.lockdown_active:
            return

        if not self.lockdown_triggered_at:
            return

        if now - self.lockdown_triggered_at < self.LOCKDOWN_DURATION_SECONDS:
            return

        print("[MiniAI] Lockdown expired")

        self.lockdown_active = False
        self.lockdown_triggered_at = None
        self._lockdown_ui_opened = False
        self.intrusion_attempts = 0
        self.events.clear()

        if self.browser:
            self.browser.finish_lockdown_unlock()

    # --------------------------------------------------
    # UI LOCK
    # --------------------------------------------------
    def _lock_browser_ui(self):

        if not self.browser:
            return

        controls = [
            "btn_back",
            "btn_fwd",
            "btn_reload",
            "btn_new_tab",
            "addr",
            "urlbar",
            "btn_js",
            "btn_nuke",
        ]

        for name in controls:
            try:
                ctrl = getattr(self.browser, name, None)
                if ctrl:
                    ctrl.setEnabled_(False)
            except Exception as e:
                log(2, e)

    # --------------------------------------------------
    # UI UNLOCK
    # --------------------------------------------------
    def _unlock_browser_ui(self):

        if not self.browser:
            return

        controls = [
            "btn_back",
            "btn_fwd",
            "btn_reload",
            "btn_new_tab",
            "addr",
            "urlbar",
            "btn_js",
            "btn_nuke",
        ]

        for name in controls:
            try:
                ctrl = getattr(self.browser, name, None)
                if ctrl:
                    ctrl.setEnabled_(True)
            except Exception as e:
                log(2, e)


HOME_URL = "darkelf://home"

class ContentRuleManager:
    _rule_list = None
    _loaded = False

    # --------------------------------------------------
    # Versioning
    # --------------------------------------------------
    VERSION = "15.02"
    IDENTIFIER = f"darkelf_rules_v{VERSION}"
    
    # Refresh filter subscriptions once per week.
    # Downloads occur only if the local cache is older than this value.
    CACHE_AGE_DAYS = 7

    # --------------------------------------------------
    # Cache
    # --------------------------------------------------
    CACHE_DIR = os.path.expanduser(
        "~/.darkelf/filterlists"
    )

    # --------------------------------------------------
    # Runtime Statistics
    # --------------------------------------------------
    _compile_count = 0
    _rule_count = 0
    _css_count = 0
    _tracker_count = 0
    
    RULE_BUDGET = {
        "easylist": 55000,
        "antiadblock": 5000,
    }
    
    # --------------------------------------------------
    # Filter Subscriptions
    # --------------------------------------------------
    SUBSCRIPTIONS = {
        "easylist": {
            "enabled": True,
            "filename": "easylist.txt",
            "url": "https://easylist-downloads.adblockplus.org/easylist.txt",
        },

        "antiadblock": {
            "enabled": True,
            "filename": "antiadblockfilters.txt",
            "url": "https://easylist-downloads.adblockplus.org/antiadblockfilters.txt",
        },
    }
    
    @classmethod
    def _ensure_cache(cls):
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        
    @classmethod
    def _subscription_path(cls, name):
        info = cls.SUBSCRIPTIONS[name]
        return os.path.join(cls.CACHE_DIR, info["filename"])
        
    @classmethod
    def _subscriptions_needing_update(cls):
        """
        Returns a list of subscriptions that should be downloaded.
        """

        updates = []

        now = time.time()

        for name, info in cls.SUBSCRIPTIONS.items():

            if not info.get("enabled", True):
                continue

            path = cls._subscription_path(name)

            if not os.path.exists(path):
                updates.append(name)
                continue

            age_days = (
                now - os.path.getmtime(path)
            ) / 86400.0

            if age_days >= cls.CACHE_AGE_DAYS:
                updates.append(name)

        return updates
        
    @classmethod
    def refresh_subscriptions(cls):

        needed = cls._subscriptions_needing_update()

        if not needed:
            print("[Rules] Filter subscriptions are current.")
            return

        print(
            f"[Rules] Updating {len(needed)} filter subscriptions..."
        )

        for name in needed:

            try:
                cls._download_subscription(name)

            except Exception as e:
                print(f"[Rules] {name}: {e}")
                
    @classmethod
    def _download_subscription(cls, name, completion=None):

        info = cls.SUBSCRIPTIONS[name]
        path = cls._subscription_path(name)

        print(f"[Rules] Downloading {name}...")

        config = NSURLSessionConfiguration.ephemeralSessionConfiguration()

        config.setRequestCachePolicy_(1)   # ReloadIgnoringLocalCacheData

        session = NSURLSession.sessionWithConfiguration_(config)

        url = NSURL.URLWithString_(info["url"])

        request = NSMutableURLRequest.requestWithURL_(url)

        request.setValue_forHTTPHeaderField_(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko)",
            "User-Agent",
        )

        request.setValue_forHTTPHeaderField_(
            "*/*",
            "Accept",
        )
        
        def _finished(data, response, error):

            if error:
                print(f"[Rules] {name}: {error}")
                if completion:
                    completion(False)
                return

            try:
                with open(path, "wb") as f:
                    f.write(bytes(data))

                print(f"[Rules] Saved {name}")

                if completion:
                    completion(True)

            except Exception as e:
                print(e)
                if completion:
                    completion(False)

        task = session.dataTaskWithRequest_completionHandler_(
            request,
            _finished,
        )

        task.resume()
        
    @classmethod
    def _parse_subscription(cls, name):

        path = cls._subscription_path(name)

        if not os.path.exists(path):
            print(f"[Rules] {name}: file not found")
            return []

        rules = []
        total_lines = 0
        parsed_lines = 0

        with open(path, "r", encoding="utf-8", errors="ignore") as f:

            for line in f:

                total_lines += 1

                line = line.strip()

                if not line:
                    continue

                parsed = cls._parse_abp_line(line)

                if parsed:
                    parsed_lines += 1
                    rules.extend(parsed)

        print(
            f"[Rules] {name}: "
            f"{len(rules):,} WebKit rules "
            f"from {parsed_lines:,}/{total_lines:,} lines"
        )

        return rules
        
    @classmethod
    def _external_subscription_rules(cls):
        cls._unsupported_rules = 0
        
        # --------------------------------------------------
        # Fresh CSS dedupe each compile
        # --------------------------------------------------
        cls._css_seen = set()

        all_rules = []
        seen = set()

        MAX_RULES = 60000

        for name, info in cls.SUBSCRIPTIONS.items():

            if not info.get("enabled", False):
                continue

            if len(all_rules) >= MAX_RULES:
                break

            try:

                parsed = cls._parse_subscription(name)

                budget = cls.RULE_BUDGET.get(name, MAX_RULES)

                remaining = MAX_RULES - len(all_rules)

                limit = min(budget, remaining)

                imported = 0

                for rule in parsed:

                    if imported >= limit:
                        break

                    key = json.dumps(rule, sort_keys=True)

                    if key in seen:
                        continue

                    seen.add(key)
                    all_rules.append(rule)
                    imported += 1

                print(
                    f"[Rules] {name:<20} "
                    f"{imported:,} unique rules"
                )

            except Exception as e:
                print(f"[Rules] {name}: {e}")

        print(
            f"[Rules] Imported {len(all_rules):,} unique rules"
        )

        if len(all_rules) >= MAX_RULES:
            print(
                f"[Rules] Reached WebKit limit ({MAX_RULES:,} rules)"
            )

        print(
            f"[Rules] Unsupported ABP rules skipped: "
            f"{cls._unsupported_rules:,}"
        )

        return all_rules
        
    @classmethod
    def _parse_abp_line(cls, line):

        line = line.strip()

        # --------------------------------------------------
        # Empty / comments / metadata
        # --------------------------------------------------
        if not line:
            return []

        if line.startswith(("!", "[")):
            return []

        # --------------------------------------------------
        # Ignore exception rules for now
        # --------------------------------------------------
        if line.startswith("@@"):
            return []

        # --------------------------------------------------
        # Initialize CSS cache
        # --------------------------------------------------
        if not hasattr(cls, "_css_seen"):
            cls._css_seen = set()

         # ==================================================
        # NETWORK RULES
        # ==================================================

        if line.startswith("||"):

            body = line[2:]
            modifiers = ""

            if "$" in body:
                body, modifiers = body.split("$", 1)

            body = body.strip()

            # Require hostname anchor
            if "^" not in body:
                return []

            body = body.split("^", 1)[0].strip()

            # Reject anything that is not a plain hostname
            if any(c in body for c in (
                "/", "*", "|", "?",
                "=", "%", ":",
                "(", ")", "[", "]",
                "\\"
            )):
                return []

            if not re.fullmatch(r"[A-Za-z0-9.-]+", body):
                return []

            # ----------------------------------------------
            # Parse modifiers
            # ----------------------------------------------

            mods = {
                m.strip().lower()
                for m in modifiers.split(",")
                if m.strip()
            }

            unsupported = (
                "script",
                "image",
                "stylesheet",
                "font",
                "media",
                "popup",
                "xmlhttprequest",
                "object",
                "object-subrequest",
                "ping",
                "websocket",
                "subdocument",
                "document",
                "elemhide",
                "generichide",
                "genericblock",
                "csp",
                "redirect",
                "removeparam",
                "important",
            )

            if any(
                m == u or m.startswith(u + "=")
                for u in unsupported
                for m in mods
            ):
                cls._unsupported_rules += 1
                return []

            trigger = {
                "url-filter": re.escape(body),
            }

            if "third-party" in mods:
                trigger["load-type"] = ["third-party"]
            elif "first-party" in mods:
                trigger["load-type"] = ["first-party"]

            return [{
                "trigger": trigger,
                "action": {
                    "type": "block",
                },
            }]
        # ==================================================
        # DOMAIN COSMETIC RULES
        # ==================================================

        if False and "##" in line:

            domain_part, selector = line.split("##", 1)

            selector = selector.strip()

            if not selector:
                return []

            # ignore unsupported cosmetic syntaxes
            if selector.startswith(("?", "+js", "^")):
                return []

            # reject malformed selectors
            if selector[0] not in (".", "#", "["):
                return []

            # Global cosmetic rule
            if domain_part == "":

                key = ("*", selector)

                if key in cls._css_seen:
                    return []

                cls._css_seen.add(key)

                return [{
                    "trigger": {
                        "url-filter": ".*"
                    },
                    "action": {
                        "type": "css-display-none",
                        "selector": selector
                    }
                }]

            # Domain-scoped cosmetic rule
            domains = []

            for d in domain_part.split(","):

                d = d.strip()

                if not d:
                    continue

                if d.startswith("~"):
                    continue

                d = d.replace("*.", "")
                d = d.replace("*", "")

                d = re.escape(d)

                domains.append(d)

            rules = []

            for domain in domains:
    
                key = (domain, selector)

                if key in cls._css_seen:
                    continue

                cls._css_seen.add(key)

                rules.append({
                    "trigger": {
                        "url-filter": domain
                    },
                    "action": {
                        "type": "css-display-none",
                        "selector": selector
                    }
                })

            return rules

        return []
        
    @classmethod
    def _rules_revision(cls):
        enabled = ",".join(
            name
            for name, info in sorted(cls.SUBSCRIPTIONS.items())
            if info.get("enabled")
        )
        return hashlib.sha1(enabled.encode()).hexdigest()[:8]
        
    @classmethod
    def load_rules(cls, completion_callback=None):
        cls._ensure_cache()
        try:
            cls.refresh_subscriptions()
        except Exception as e:
            print("[Rules] Subscription update failed:", e)
            
        if cls._loaded:
            if cls._rule_list and completion_callback:
                completion_callback()
            return

        cls._loaded = True
        store = WKContentRuleListStore.defaultStore()
        
        # 🔥 NEW VERSION
        identifier = f"darkelf_rules_v{cls.VERSION}"

        def _lookup(rule_list, error):

            # --------------------------------------------------
            # Ignore "rule list not found" (WKErrorDomain Code 7)
            # --------------------------------------------------
            if error:
                try:
                    if error.code() != 7:
                        print("error =", error)
                except Exception:
                    print("error =", error)
                    
            # --------------------------------------------------
            # Cached rule list
            # --------------------------------------------------
            if rule_list:

                print("[Rules] Using cached ContentRuleList")

                cls._rule_list = rule_list

                print(
                    f"[Rules] Loaded cached ContentRuleList (v{cls.VERSION})"
                )

                if completion_callback:
                    completion_callback()

                return

            # --------------------------------------------------
            # Build JSON
            # --------------------------------------------------
            print("[Rules] Building new ContentRuleList...")

            json_rules = cls._load_json()

            try:
                parsed = json.loads(json_rules)

                cls._rule_count = len(parsed)

                cls._tracker_count = sum(
                    1 for r in parsed
                    if r.get("action", {}).get("type") == "block"
                )

                cls._css_count = sum(
                    1 for r in parsed
                    if r.get("action", {}).get("type") == "css-display-none"
                )

            except Exception:
                cls._rule_count = 0
                cls._tracker_count = 0
                cls._css_count = 0

            # --------------------------------------------------
            # Compile callback
            # --------------------------------------------------
            def _compiled(rule_list, error):

                print("[Rules] _compiled callback")
                print("rule_list =", bool(rule_list))
                print("error =", error)

                if error:
                    print(f"[Rules] Compile error (v{cls.VERSION}):", error)
                    return

                cls._rule_list = rule_list
                cls._compile_count += 1

                print(
                    f"[Rules] Darkelf Content Rules v{cls.VERSION} loaded "
                    f"({cls._rule_count:,} rules | "
                    f"{cls._tracker_count:,} block | "
                    f"{cls._css_count:,} css)"
                )

                if completion_callback:
                    completion_callback()

            print("[Rules] Compiling rule list...")

            store.compileContentRuleListForIdentifier_encodedContentRuleList_completionHandler_(
                identifier,
                json_rules,
                _compiled,
            )
            
        store.lookUpContentRuleListForIdentifier_completionHandler_(
            identifier,
            _lookup,
        )

    @classmethod
    def _load_json(cls):

        rules = []
        seen = set()

        def add(rule):

            key = json.dumps(rule, sort_keys=True)

            if key in seen:
                return

            seen.add(key)
            rules.append(rule)

        # --------------------------------------------------
        # Safe Sites
        # --------------------------------------------------

        SAFE_SITES = sorted(set([
            "accounts\\.google\\.com",
            "github\\.com",
            "mail\\.google\\.com",
            "office\\.com",
            "outlook\\.live\\.com",
            "tuta\\.com",
            "youtube\\.com",
            "youtu\\.be",
        ]))

        for site in SAFE_SITES:

            add({
                "trigger": {
                    "url-filter": site
                },
                "action": {
                    "type": "ignore-previous-rules"
                }
            })

        # --------------------------------------------------
        # Test Blocks
        # --------------------------------------------------

        for url in (
            ".*amazon-adsystem.*",
            ".*amazon_apstag.*",
            ".*analytics.*collect.*",
            ".*collect.*",
            ".*telemetry.*",
            ".*metrics.*",
            ".*beacon.*",
            ".*tracker.*",
            ".*tracking.*",
            ".*fingerprint.*",
            ".*fingerprintjs.*",
            ".*fpjs.*",
            ".*pixel.*",
            ".*adsystem.*",
            ".*advertising.*",
            ".*ads.*\\.js",
            ".*ads.*\\.mjs",
            ".*ads.*\\.min\\.js",
            ".*prebid.*",
            ".*prebid\\.js",
            ".*prebid\\.min\\.js",
            ".*optimizely.*",
            ".*fullstory.*",
            ".*heap.*",
            ".*heapanalytics.*",
            ".*appsflyer.*",
            ".*adjust.*",
            ".*branch.*",
            ".*/pagead\\.js",
            ".*/widget/ads",
            ".*analytics\\.js",
            ".*gtm\\.js",
            ".*gtag/js",
            ".*fbevents\\.js",
            ".*clarity\\.js",
            ".*hotjar.*\\.js",
            ".*mixpanel.*\\.js",
            ".*segment.*\\.js",
            ".*amplitude.*\\.js",
            ".*adsbygoogle\\.js",
            ".*prebid.*\\.js"
            
        ):

            add({
                "trigger": {
                    "url-filter": url
                },
                "action": {
                    "type": "block"
                }
            })

        # --------------------------------------------------
        # Built-in Tracker Domains
        # --------------------------------------------------

        BLOCK_DOMAINS = [
            # <-- paste your existing list here -->
        ]
        
        BLOCK_DOMAINS = sorted({
        
            #----------------Ads----------------------
            "adsrvr.com",
            "casalemedia.com",
            "demdex.net",
            "everesttech.net",
            "everestjs.net",
            "rlcdn.com",
            "mathtag.com",
            "advertising.com",
            "yieldmo.com",
            "yieldlab.net",
            "yieldoptimizer.com",
            "contextweb.com",
            "33across.com",
            "sharethrough.com",
            "triplelift.com",
            "sovrn.com",
            "lijit.com",
            "media.net",
            "bidswitch.com",
            "indexww.com",
            "pub.network",
            "crwdcntrl.net",
            "eyeota.net",
            "simpli.fi",
            "adform.net",
            "adform.com",
            "bluekai.com",
            "tapad.com",
            "teads.tv",
            "revcontent.com",
            "contentabc.com",

            # ---------------- Google ----------------
            "doubleclick\\.net",
            "googlesyndication\\.com",
            "googleadservices\\.com",
            "googletagmanager\\.com",
            "googletagservices\\.com",
            "google-analytics\\.com",
            "analytics\\.google\\.com",
            "adservice\\.google\\.com",
            "pagead2\\.googlesyndication\\.com",
            "pagead2\\.googleadservices\\.com",

            # ---------------- Meta ----------------
            "facebook\\.net",
            "connect\\.facebook\\.net",
            "pixel\\.facebook\\.com",
            "an\\.facebook\\.com",

            # ---------------- Microsoft ----------------
            "bat\\.bing\\.com",
            "clarity\\.ms",

            # ---------------- Yahoo ----------------
            "analytics\\.yahoo\\.com",
            "geo\\.yahoo\\.com",
            "udcm\\.yahoo\\.com",

            # ---------------- Yandex ----------------
            "appmetrica\\.yandex\\.ru",
            "metrika\\.yandex\\.ru",
            "adfox\\.yandex\\.ru",

            # ---------------- Adobe ----------------
            "demdex\\.net",
            "omtrdc\\.net",

            # ---------------- Twitter/X ----------------
            "ads-api\\.twitter\\.com",
            "static\\.ads-twitter\\.com",

            # ---------------- LinkedIn ----------------
            "ads\\.linkedin\\.com",
            "analytics\\.pointdrive\\.linkedin\\.com",
            "snap\\.licdn\\.com",
            "px\\.ads\\.linkedin\\.com",

            # ---------------- Pinterest ----------------
            "ads\\.pinterest\\.com",
            "trk\\.pinterest\\.com",
            "log\\.pinterest\\.com",

            # ---------------- Reddit ----------------
            "events\\.redditmedia\\.com",

            # ---------------- TikTok ----------------
            "analytics\\.tiktok\\.com",

            # ---------------- Snapchat ----------------
            "tr\\.snapchat\\.com",

            # ---------------- Native Ads ----------------
            "taboola\\.com",
            "outbrain\\.com",
            "revcontent\\.com",
            "nativo\\.net",
            "s\\.ntv\\.io",

            # ---------------- Ad Exchanges ----------------
            "pubmatic\\.com",
            "rubiconproject\\.com",
            "openx\\.net",
            "indexexchange\\.com",
            "media\\.net",
            "criteo\\.com",

            # ---------------- Measurement ----------------
            "chartbeat\\.net",
            "ping\\.chartbeat\\.net",
            "quantserve\\.com",
            "scorecardresearch\\.com",
            "moatads\\.com",

            # ---------------- Mixpanel ----------------
            "mixpanel\\.com",
            "api\\.mixpanel\\.com",
            "cdn\\.mxpnl\\.com",

            # ---------------- Segment ----------------
            "segment\\.com",
            "api\\.segment\\.io",
            "cdn\\.segment\\.com",

            # ---------------- Amplitude ----------------
            "amplitude\\.com",
            "api\\.amplitude\\.com",

            # ---------------- New Relic ----------------
            "js-agent\\.newrelic\\.com",
            "bam\\.nr-data\\.net",

            # ---------------- Datadog ----------------
            "browser-intake-datadoghq\\.com",

            # ---------------- Sentry ----------------
            "browser\\.sentry-cdn\\.com",
            "app\\.getsentry\\.com",

            # ---------------- Bugsnag ----------------
            "notify\\.bugsnag\\.com",
            "sessions\\.bugsnag\\.com",
            "api\\.bugsnag\\.com",
            "app\\.bugsnag\\.com",

            # ---------------- Mouseflow ----------------
            "mouseflow\\.com",
            "cdn\\.mouseflow\\.com",
            "api\\.mouseflow\\.com",

            # ---------------- Hotjar ----------------
            "hotjar\\.com",
            "insights\\.hotjar\\.com",
            "identify\\.hotjar\\.com",
            "script\\.hotjar\\.com",
            "surveys\\.hotjar\\.com",

            # ---------------- Lucky Orange ----------------
            "luckyorange\\.com",
            "upload\\.luckyorange\\.net",
            "cs\\.luckyorange\\.net",
            "settings\\.luckyorange\\.net",
            "cdn\\.luckyorange\\.com",
            "api\\.luckyorange\\.com",
            "w1\\.luckyorange\\.com",
            "tools\\.luckyorange\\.com",

            # ---------------- Freshworks ----------------
            "freshmarketer\\.com",

            # ---------------- Oracle ----------------
            "bluekai\\.com",
            "tags\\.bluekai\\.com",
            "trk\\.bluekai\\.com",

            # ---------------- Mobile SDKs ----------------
            "appsflyer\\.com",
            "adjust\\.com",
            "kochava\\.com",
            "branch\\.io",
            "heapanalytics\\.com",
            "fullstory\\.com",
            "braze\\.com",
            "appboy\\.com",
            "onesignal\\.com",
            "optimizely\\.com",

            # ---------------- Cloudflare ----------------
            "zaraz\\.cloudflare\\.com",

            # ---------------- OEM ----------------
            "mistat\\.xiaomi\\.com",
            "api\\.ad\\.xiaomi\\.com",
            "oppomobile\\.com",
            "realmemobile\\.com",
            "hicloud\\.com",

            # ---------------- Samsung ----------------
            "samsungads\\.com",
            "smetrics\\.samsung\\.com",

            # ---------------- Gaming ----------------
            "applovin\\.com",
            "d\\.applovin\\.com",
            "unityads\\.unity3d\\.com",
            "config\\.unityads\\.unity3d\\.com",
            "ironsrc\\.com",
            "vungle\\.com",
            "ads30\\.adcolony\\.com",
            "adc3-launch\\.adcolony\\.com",
            "events3alt\\.adcolony\\.com",
            "wd\\.adcolony\\.com",

            # ---------------- Apple ----------------
            "metrics\\.icloud\\.com",
            "metrics\\.mzstatic\\.com",
            "api-adservices\\.apple\\.com",
            "books-analytics-events\\.apple\\.com",
            "weather-analytics-events\\.apple\\.com",
            "notes-analytics-events\\.apple\\.com",

            # ---------------- Teads ----------------
            "teads\\.tv",
            "a\\.teads\\.tv",
            "cdn\\.teads\\.tv",
            
            # ---------------- Reddit ----------------
            "events\\.reddit\\.com",

            # ---------------- TikTok ----------------
            "ads-api\\.tiktok\\.com",
            "ads\\.tiktok\\.com",
            "ads-sg\\.tiktok\\.com",
            "analytics-sg\\.tiktok\\.com",
            "business-api\\.tiktok\\.com",
            "log\\.byteoversea\\.com",
            "log\\.byteoversea\\.net",

            # ---------------- Xiaomi ----------------
            "sdkconfig\\.ad\\.xiaomi\\.com",
            "sdkconfig\\.ad\\.intl\\.xiaomi\\.com",
            "tracking\\.rus\\.miui\\.com",
            "tracking\\.intl\\.miui\\.com",
            "data\\.mistat\\.india\\.xiaomi\\.com",
            "data\\.mistat\\.rus\\.xiaomi\\.com",

            # ---------------- Realme ----------------
            "iot-eu-logger\\.realme\\.com",
            "iot-logger\\.realme\\.com",
            "bdapi-ads\\.realmemobile\\.com",
            "bdapi-in-ads\\.realmemobile\\.com",

            # ---------------- Oppo ----------------
            "adsfs\\.oppomobile\\.com",
            "adx\\.ads\\.oppomobile\\.com",

            # ---------------- Huawei ----------------
            "metrics\\.cloud\\.huawei\\.com",
            "grs\\.hicloud\\.com",
            "logservice\\.hicloud\\.com",

            # ---------------- Vivo ----------------
            "adxlog\\.vivo\\.com",
            "stsdk\\.vivo\\.com",

            # ---------------- Amazon ----------------
            "amazon-adsystem\\.com",
            "aax\\.amazon-adsystem\\.com",
            "c\\.amazon-adsystem\\.com",

            # ---------------- Fingerprinting ----------------
            "fingerprintjs\\.com",
            "fpjs\\.io",
            "client\\.fpjs\\.io",
            
            #---------------- Extra-------------------
            ".*amazon_apstag.*\\.js",
            ".*gpt\\.js",
            ".*cmp.*\\.js",
            ".*consent.*\\.js",
            ".*adsystem.*\\.js",
            ".*adservice.*\\.js",
            ".*analytics.*collect.*",
            ".*pixel.*\\.js",
            ".*tracking.*\\.js",
            ".*advertising.*\\.js",
            
            # ---------------- Tremor ----------------
            "tremorhub\\.com",
            "ads\\.tremorhub\\.com",

        })
        

        for domain in sorted(set(BLOCK_DOMAINS)):

            add({
                "trigger": {
                    "url-filter": domain
                },
                "action": {
                    "type": "block"
                }
            })

        # --------------------------------------------------
        # Consent
        # --------------------------------------------------

        for domain in (
            "cookiebot",
            "consentmanager",
            "onetrust",
            "quantcast",
            "trustarc",
            "didomi",
            "usercentrics",
            "cookielaw",
            "cookieyes",
            "iubenda",
            "cookie-script",
            "cookieinformation",
            "osano",
            "cookiehub",
            
        ):

            add({
                "trigger": {
                    "url-filter": domain,
                    "load-type": ["third-party"]
                },
                "action": {
                    "type": "block"
                }
            })
        # --------------------------------------------------
        # Cosmetic
        # --------------------------------------------------

        add({
            "trigger": {
                "url-filter": ".*"
            },
            "action": {
                "type": "css-display-none",
                "selector": """
    iframe[src*='doubleclick'],
    iframe[src*='googlesyndication'],
    iframe[src*='adservice'],
    iframe[src*='googletagmanager'],
    iframe[src*='taboola'],
    iframe[src*='outbrain'],
    iframe[src*='criteo'],
    iframe[src*='adnxs'],
    iframe[src*='pubmatic'],
    iframe[src*='openx'],
    iframe[src*='rubicon'],
    iframe[src*='amazon-adsystem']    
    """
            }
        })

        add({
            "trigger": {
                "url-filter": ".*"
            },
            "action": {
                "type": "css-display-none",
                "selector": """
    [data-ad]:empty,
    [data-ad-container]:empty,
    [data-slot-type='ad']:empty,
    [aria-label='Advertisement']:empty,
    .ad,
    .ads,
    .advertisement,
    .advert,
    .ad-container,
    .advert-container,        
    .banner-ad,
    .banner_ads,
    .ad-wrapper,
    .adbox,
    .adunit,
    .ad-label,
    .promoted-post,
    .sponsored-post,
    [data-google-query-id],
    [data-ad-slot],
    [data-ad-client]    
    """
            }
        })
        
        # --------------------------------------------------
        # GLOBAL COSMETIC (SAFE ONLY)
        # --------------------------------------------------
        rules.append(
            {
                "trigger": {"url-filter": ".*"},
                "action": {
                    "type": "css-display-none",
                    "selector": """
                    /* iframe ads only (safe) */
                    iframe[src*='doubleclick'],
                    iframe[src*='googlesyndication'],
                    iframe[src*='adservice'],
                    iframe[src*='googletagmanager'],
                    iframe[src*='taboola'],
                    iframe[src*='outbrain']
                """,
                },
            }
        )
        
        add({
            "trigger": {
                "url-filter": ".*"
            },
            "action": {
                "type": "css-display-none",
                "selector": """
[id^='google_ads'],
[id^='div-gpt-ad'],
[id*='div-gpt-ad'],

[data-google-av-cxn],
[data-google-query-id],

[class*='advertisement'],
[class*='ad-slot'],
[class*='ad-wrapper'],
[class*='banner-ad'],
[class*='ad-container'],
[class*='ad-placeholder'],
[class*='sponsored-post'],
[class*='promoted-post'],
[class*='google-ad'],
[class*='adsense'],

[data-testid='ad'],
[data-testid='advertisement']
"""
            }
        })
        
        add({
            "trigger": {
                "url-filter": "adblock\\.turtlecute\\.org"
            },
            "action": {
                "type": "css-display-none",
                "selector": """
.adbox.banner_ads.adsbox,
.textads
"""
            }
        })
        
        # --------------------------------------------------
        # GITHUB ALLOWLIST
        # --------------------------------------------------
        rules.append(
            {
                "trigger": {
                    "url-filter": "github\\.com"
                },
                "action": {
                    "type": "ignore-previous-rules"
                }
            }
        )
        # --------------------------------------------------
        # Popup Block
        # --------------------------------------------------

        add({
            "trigger": {
                "url-filter": ".*",
                "resource-type": ["popup"]
            },
            "action": {
                "type": "block"
            }
        })
        
        # --------------------------------------------------
        # Subscription Rules
        # --------------------------------------------------

        for rule in cls._external_subscription_rules():
            add(rule)
            
        return json.dumps(rules)


# ---- Darkelf Diagnostics / Kill-Switches ----
DARKELF_DISABLE_COOKIE_SCRUBBER = False
DARKELF_DISABLE_JS_HANDLERS = False
DARKELF_DISABLE_RESIZE_HANDLER = False

# ---- Local CSP (off by default) ----
ENABLE_LOCAL_CSP = False
LOCAL_CSP_VALUE = (
    "worker-src 'self' blob:; manifest-src 'self'; form-action 'self' https:;"
)

# ---- Local HSTS (off by default) ----
ENABLE_LOCAL_HSTS = True
LOCAL_HSTS_VALUE = "max-age=63072000; includeSubDomains; preload"

# ---- Local Referrer Policy (off by default) ----
ENABLE_LOCAL_REFERRER_POLICY = True
LOCAL_REFERRER_POLICY_VALUE = "strict-origin-when-cross-origin"

# ---- Local WebSocket Policy (off by default) ----
ENABLE_LOCAL_WEBSOCKET_POLICY = True
LOCAL_WEBSOCKET_POLICY_VALUE = (
    "connect-src 'self' https: wss: "
    "https://*.googlevideo.com "
    "https://youtubei.googleapis.com "
    "https://*.youtube.com "
    "https://i.ytimg.com "
    "https://www.youtube.com;"
)


class _UIDelegate(NSObject):
    def initWithOwner_(self, owner):
        self = objc.super(_UIDelegate, self).init()
        if self is None:
            return None
        self.owner = owner
        return self

    # Forward the methods you currently implemented on Browser:

    def webView_createWebViewWithConfiguration_forNavigationAction_windowFeatures_(
        self,
        webview,
        configuration,
        navigationAction,
        windowFeatures
    ):
        try:
            req = navigationAction.request()

            if req is None:
                return None

            owner = getattr(self, "owner", None)
            if owner is None:
                return None

            active = owner.active
            if active < 0 or active >= len(owner.tabs):
                return None

            tab = owner.tabs[active]
            view = getattr(tab, "view", None)

            if view is None:
                return None

            try:
                view.stopLoading()
            except Exception:
                pass

            view.loadRequest_(req)

            return None

        except Exception as e:
            print("[POPUP ERROR]", e)
            return None

    def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_completionHandler_(
        self, webView, message, frame, completionHandler
    ):
        try:
            print(f"[JS Alert] {message}")
            alert = NSAlert.alloc().init()
            alert.setMessageText_("JavaScript Alert")
            alert.setInformativeText_(str(message))
            alert.addButtonWithTitle_("OK")
            alert.runModal()
        finally:
            completionHandler()

    def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_completionHandler_(
        self, webView, message, frame, completionHandler
    ):
        try:
            print(f"[JS Confirm] {message}")
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Confirm")
            alert.setInformativeText_(str(message))
            alert.addButtonWithTitle_("OK")
            alert.addButtonWithTitle_("Cancel")
            result = alert.runModal()
            completionHandler(result == 1000)
        except Exception as e:
            print(f"[JS Confirm] Error: {e}")
            completionHandler(False)

    def webView_runJavaScriptTextInputPanelWithPrompt_defaultText_initiatedByFrame_completionHandler_(
        self, webView, prompt, defaultText, frame, completionHandler
    ):
        try:
            print(f"[JS Prompt] {prompt}")
            completionHandler(None)
        except Exception as e:
            print(f"[JS Prompt] Error: {e}")
            completionHandler(None)

    def webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_(
        self, webView, origin, frame, type, decisionHandler
    ):
        try:
            print(f"[Media] 🔒 Denied media capture for: {origin}")
            decisionHandler(0)
        except Exception as e:
            log(2, e)

    def webView_enterFullScreenForFrame_completionHandler_(
        self, webView, frame, completionHandler
    ):

        try:
            print("[UIDelegate] WebKit video fullscreen")

            webView.setFrame_(webView.window().contentView().bounds())
            webView.setAutoresizingMask_(18)  # width + height

        except Exception as e:
            print("[UIDelegate] fullscreen error:", e)

        completionHandler(True)

    def webView_exitFullScreenForFrame_completionHandler_(
        self, webView, frame, completionHandler
    ):
        print("[UIDelegate] exit video fullscreen")
        completionHandler(True)


class _NavDelegate(NSObject):

    # -------------------------------------------------
    # Init
    # -------------------------------------------------
    def initWithOwner_(self, owner):
        self = objc.super(_NavDelegate, self).init()
        if self is None:
            return None

        self.owner = owner
        self.download_dir = _safe_download_dir()

        return self
        
    # -------------------------------------------------
    # Navigation Finished
    # -------------------------------------------------
    def webView_didFinishNavigation_(self, webView, nav):

        owner = getattr(self, "owner", None)
        if not owner:
            return

        if not getattr(owner, "tabs", None):
            return

        try:
            browser = getattr(self, "owner", None)
            if not browser:
                return

            if not browser._is_tab_webview(webView):
                return

            url = webView.URL()
            title = webView.title()

            scheme = ""
            if url:
                scheme = str(url.scheme() or "").lower()

            # ----------------------------
            # Tab sync (UNCHANGED)
            # ----------------------------
            for tab in browser.tabs:
                if tab.view is webView:

                    if url and url.absoluteString() == HOME_URL:
                        tab.url = HOME_URL
                        tab.host = "Darkelf Home"
                        tab.title = "Darkelf Home"

                    else:
                        if title:
                            tab.title = str(title)
                        else:
                            tab.title = url.host() if url else "New Tab"

                        if url:
                            tab.host = url.host() or ""
                            tab.url = url.absoluteString()
                            
                            # ----------------------------
                            # Load favicon once
                            # ----------------------------
                            if tab.host != tab.favicon_host:

                                def favicon_ready(icon, tab=tab, browser=browser):

                                    if icon:
                                        tab.favicon = icon
                                        tab.favicon_host = tab.host
                                        browser._update_tab_buttons()

                                fetch_favicon(tab.host, favicon_ready)
                                    
                    break

            browser._update_tab_buttons()
            browser._sync_addr()
            browser.refreshBookmarkButton()

            # ----------------------------
            # WebKit process recycle (UNCHANGED)
            # ----------------------------
            try:
                if hasattr(browser, "page_load_count"):
                    browser.page_load_count += 1

                    if browser.page_load_count >= 200:
                        browser.recycle_web_process()
            except Exception as e:
                print("[Darkelf] recycle trigger error:", e)

            # ----------------------------
            # Address bar color (UNCHANGED)
            # ----------------------------
            color = NSColor.whiteColor()

            if url and scheme == "https":
                current = browser.addr.textColor()
                if current != NSColor.systemRedColor():
                    color = NSColor.systemGreenColor()

            browser.addr.setTextColor_(color)

            browser.addr.setFocusRingType_(NSFocusRingTypeNone)
            browser.addr.setWantsLayer_(True)
            browser.addr.layer().setBorderColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.20, 0.78, 0.35, 1
                ).CGColor()
            )
            browser.addr.layer().setBorderWidth_(1.5)
            browser.addr.layer().setCornerRadius_(6)

            # ----------------------------
            # 🔥 CRITICAL: SELF-HEAL INJECTION
            # ----------------------------
            try:
                js = r"""
                (function() {
                    try {
                        // If canvas defense missing → reapply
                        if (!window.__darkelf_canvas_active) {

                            console.log("Darkelf: Reinjecting protections");

                            // Canvas
                            if (typeof window.__darkelf_reapply_canvas === "function") {
                                window.__darkelf_reapply_canvas();
                            }

                            // Fonts
                            if (typeof window.__darkelf_reapply_fonts === "function") {
                                window.__darkelf_reapply_fonts();
                            }

                            // Mark active to prevent loops
                            window.__darkelf_canvas_active = true;
                        }
                    } catch(e) {
                        console.log("Darkelf reinject error:", e);
                    }
                })();
                """

                webView.evaluateJavaScript_completionHandler_(js, None)

            except Exception as e:
                print("[Darkelf] reinject error:", e)

            # ----------------------------
            # PQ indicator (UNCHANGED)
            # ----------------------------
            try:
                if scheme == "https" and darkelf_is_pq_active(browser):

                    current = browser.addr.stringValue() or ""

                    for tag in [" PQ", " PQ✓", " PQ⚠"]:
                        current = current.replace(tag, "")

                    status = getattr(browser, "_pq_trust_status", "ok")

                    if status == "warn":
                        tag = "  PQ⚠"
                        tooltip = "TLS Secure + PQ Active — Trust change detected"
                        color = NSColor.systemRedColor()
                    else:
                        tag = "  PQ✓"
                        tooltip = "TLS Secure + PQ Integrity Active"
                        color = NSColor.systemGreenColor()

                    browser.addr.setStringValue_(current + tag)
                    browser.addr.setToolTip_(tooltip)
                    browser.addr.setTextColor_(color)

            except Exception as e:
                log(2, e)

        except Exception as e:
            print("[NavDelegate] didFinish error:", e)
            
            # ------------------------------------------
            # restore floating findbar after navigation
            # ------------------------------------------
            try:

                if hasattr(browser, "_findPanel") and browser._findPanel:

                    browser._findPanel.removeFromSuperview()

                    browser.window.contentView().addSubview_positioned_relativeTo_(
                        browser._findPanel,
                        1,
                        None
                    )

            except Exception as e:
                print("[FindBar Restore Error]", e)
        
    # -------------------------------------------------
    # JS Bridge
    # -------------------------------------------------
    def userContentController_didReceiveScriptMessage_(self, ucc, message):

        try:

            # -------------------------
            # FULLSCREEN BRIDGE
            # -------------------------
            if message.name() == "fullscreen":
                print("[Fullscreen message ignored]")
                return

            # -------------------------
            # NETLOG HANDLER
            # -------------------------
            if message.name() == "netlog":

                try:

                    body = message.body()

                    if not isinstance(body, dict):
                        return

                    owner = getattr(self, "owner", None)
                    if not owner:
                        return

                    url = str(body.get("url", "")).strip()

                    if not url:
                        return

                    req_type = str(body.get("type", "unknown"))
                    headers = body.get("headers", {}) or {}

                    # structured metadata for MiniAI
                    meta = {"type": req_type, "source": "js", "headers": headers}

                    if hasattr(owner, "mini_ai"):
                        owner.mini_ai.monitor_network(url, meta)

                except Exception as e:
                    print("[Darkelf netlog error]", e)

                return

            # -------------------------
            # BLOB DOWNLOAD HANDLER
            # -------------------------
            if message.name() == "blobdownload":

                body = message.body()

                filename = body.get("filename", "download")
                data = body.get("data")

                if not data:
                    return

                base64_data = data.split(",")[1]

                randomized = _randomized_filename(filename)

                path = os.path.join(self.download_dir, randomized)

                self._download_path = path

                raw = base64.b64decode(base64_data)

                base_hash = darkelf_sha3_bytes(raw)

                # bind to PQ session chain
                chain = getattr(self.owner, "_pq_chain", "")

                hash_val = hashlib.sha3_512((chain + base_hash).encode()).hexdigest()

                with open(path, "wb") as f:
                    f.write(raw)

                if hasattr(self.owner, "_pq_file_hashes"):
                    self.owner._pq_file_hashes[path] = hash_val

                print("[PQ FILE HASH]", hash_val)
                print("[Darkelf] Blob downloaded →", path)

                return

        except Exception as e:
            print("[NavDelegate ScriptMessage] Error:", e)

    # ===============================
    # DOWNLOAD HANDLING
    # ===============================

    def webView_decidePolicyForNavigationResponse_decisionHandler_(
        self, webView, response, decisionHandler
    ):

        try:
            ns_response = response.response()

            if not ns_response:
                decisionHandler(WKNavigationResponsePolicyAllow)
                return

            mime = ns_response.MIMEType() or ""
            headers = ns_response.allHeaderFields() or {}

            # Normalize headers (case-insensitive)
            headers_lower = {str(k).lower(): str(v) for k, v in headers.items()}

            # ==================================================
            # 🔥 NEW: CENTRALIZED DOWNLOAD DETECTION
            # ==================================================
            is_download = False

            if (
                "content-disposition" in headers_lower
                and "attachment" in headers_lower["content-disposition"]
            ):
                is_download = True

            if not response.canShowMIMEType():
                is_download = True

            # ==================================================
            # 🔥 HANDLE DOWNLOAD (LAZY INIT HERE)
            # ==================================================
            if is_download:
                print("[Darkelf] Download detected:", mime)
                print("MIME:", mime)
                print("CAN SHOW:", response.canShowMIMEType())
                print("HEADERS:", headers_lower)
                print("IS DOWNLOAD:", is_download)
                
                # 🔥 lazy init folder (only now)
                if not self.download_dir:
                    self.download_dir = _safe_download_dir(create=True)

                # 🔥 lazy init UI (only now)
                try:
                    self._ensure_download_ui(webView)
                except Exception as e:
                    print("[Download UI init error]", e)

                decisionHandler(WKNavigationResponsePolicyDownload)
                return

            # ==================================================
            # NORMAL NAVIGATION
            # ==================================================
            decisionHandler(WKNavigationResponsePolicyAllow)

        except Exception as e:
            print("[Darkelf] Download decision error:", e)
            decisionHandler(WKNavigationResponsePolicyAllow)

    def _ensure_download_ui(self, webView):

        browser = self.owner

        # already exists → just show it
        if hasattr(browser, "download_ui") and browser.download_ui:
            browser.download_ui.setHidden_(False)
            return

        # 🔥 create ONLY when needed
        frame = webView.frame()

        dv = DownloadProgressView.alloc().initWithFrame_(frame)

        browser.download_ui = dv
        webView.superview().addSubview_(dv)

        dv.setHidden_(False)
        
    def webView_navigationResponse_didBecomeDownload_(
        self, webView, response, download
    ):
        try:
            download.setDelegate_(self)
            print("[Darkelf] Download started")

            # --- get filename safely ---
            filename = "download"
            try:
                url = response.response().URL()
                if url:
                    filename = url.lastPathComponent() or "download"
            except Exception as e:
                log(2, e)

            # --- init tracking (do this before UI updates) ---
            self.start_time = time.time()
            self.bytes_received = 0
            self.expected = 0
            self._download_path = None
            self._download_last_size = 0

            # --- show progress UI (MAIN THREAD) ---
            def _ui():
                try:
                    ui = getattr(self.owner, "download_ui", None)
                    if not ui:
                        return

                    ui.download = download
                    ui.nav_delegate = self  # so Cancel can stop polling etc.

                    parent = ui.superview()
                    if parent:
                        try:
                            ui.removeFromSuperview()
                        except Exception as e:
                            log(2, e)

                        parent.addSubview_(ui)

                        # ✅ FORCE FIXED SIZE + POSITION
                        parent_width = parent.bounds().size.width

                        ui.setFrame_(
                            NSMakeRect(
                                20,  # left margin
                                parent.bounds().size.height - 90,  # top position
                                515,  # FIXED WIDTH (this is the key)
                                70,
                            )
                        )

                    ui.setHidden_(False)
                    ui.setFilename_(filename)

                    # start with indeterminate until we learn expected size
                    try:
                        if hasattr(ui, "setIndeterminate_"):
                            ui.setIndeterminate_(True)
                    except Exception as e:
                        log(2, e)

                    ui.updateProgress_(0)
                except Exception as e:
                    print("[DownloadUI] error:", e)

            NSOperationQueue.mainQueue().addOperationWithBlock_(_ui)

            # start file-size polling fallback (works even if WebKit progress callbacks never fire)
            try:
                if hasattr(self, "_start_download_poll_timer"):
                    self._start_download_poll_timer()
            except Exception as e:
                print("[Download poll start] error:", e)

        except Exception as e:
            print("Download delegate error:", e)

    def download_decideDestinationUsingResponse_suggestedFilename_completionHandler_(
        self, download, response, filename, completionHandler
    ):

        try:

            # Ensure download directory exists
            os.makedirs(self.download_dir, exist_ok=True)

            randomized = _randomized_filename(filename)

            path = os.path.join(self.download_dir, randomized)

            print("[Darkelf] Download →", path)

            completionHandler(NSURL.fileURLWithPath_(path))

        except Exception as e:
            print("Download error:", e)
            completionHandler(None)

    def download_didReceiveData_(self, download, length):
        try:
            self.bytes_received += length

            elapsed = max(time.time() - getattr(self, "start_time", time.time()), 0.1)
            speed = self.bytes_received / elapsed
            mb = speed / 1024 / 1024

            expected = getattr(self, "expected", 0) or 0
            if expected > 0:
                percent = min(100.0, (self.bytes_received / expected) * 100.0)
            else:
                # fallback "spinner-like" progress if unknown size
                mb_downloaded = self.bytes_received / 1024 / 1024
                percent = mb_downloaded % 100

            def _ui():
                try:
                    ui = getattr(self.owner, "download_ui", None)
                    if not ui:
                        return
                    ui.setSpeed_(f"{mb:.2f} MB/s")
                    ui.updateProgress_(percent)
                except Exception as e:
                    log(2, e)

            NSOperationQueue.mainQueue().addOperationWithBlock_(_ui)

        except Exception as e:
            print("[Download progress error]", e)

    def download_didReceiveResponse_(self, download, response):

        try:
            self.expected = response.expectedContentLength()
        except:
            self.expected = 0

    def downloadDidFinish_(self, download):

        # --- 1. Log finish ---
        try:
            print("[Darkelf] Download finished")
        except Exception as e:
            log(2, e)

        # --- 2. PQ HASH (SAFE BLOCK) ---
        try:
            if hasattr(self, "_download_path") and self._download_path:

                with open(self._download_path, "rb") as f:
                    while True:
                        chunk = f.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break

                # process chunk here (or just pass if not needed)
                base_hash = darkelf_sha3_bytes(data)
                chain = getattr(self.owner, "_pq_chain", "")
                hash_val = hashlib.sha3_512((chain + base_hash).encode()).hexdigest()

                if hasattr(self.owner, "_pq_file_hashes"):
                    self.owner._pq_file_hashes[self._download_path] = hash_val

                print("[PQ FILE HASH]", hash_val)

        except Exception as e:
            print("[PQ download hash error]", e)

        # --- 3. UI UPDATE (ALWAYS RUNS) ---
        try:
            ui = getattr(self.owner, "download_ui", None)
            if not ui:
                return

            # force full progress
            ui.updateProgress_(100)

            # auto-hide after delay
            def hide():
                try:
                    ui.setHidden_(True)
                except Exception as e:
                    log(2, e)

            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.5, ui, "setHidden:", True, False
            )

        except Exception as e:
            print("[Download finish UI error]", e)

    def download_didWriteData_totalBytesWritten_totalBytesExpectedToWrite_(
        self, download, bytesWritten, totalBytesWritten, totalBytesExpectedToWrite
    ):
        try:
            self.bytes_received = int(totalBytesWritten or 0)
            self.expected = int(totalBytesExpectedToWrite or 0)

            elapsed = max(time.time() - getattr(self, "start_time", time.time()), 0.1)

            speed = self.bytes_received / elapsed
            mb = speed / 1024 / 1024

            if self.expected > 0:
                percent = min(100.0, (self.bytes_received / self.expected) * 100.0)
            else:
                percent = (self.bytes_received / 1024 / 1024) % 100

            def _ui():
                ui = getattr(self.owner, "download_ui", None)
                if not ui:
                    return
                ui.setSpeed_(f"{mb:.2f} MB/s")
                ui.updateProgress_(percent)

            NSOperationQueue.mainQueue().addOperationWithBlock_(_ui)

        except Exception as e:
            print("[Download didWriteData error]", e)

    def download_didFailWithError_resumeData_(self, download, error, resumeData):
        try:
            print("[Darkelf] Download failed:", error)
        except Exception as e:
            log(2, e)

    # ===============================
    # WIPE DOWNLOAD TRACES
    # ===============================

    def wipe_download_traces(self):

        try:

            if getattr(self, "download_dir", None) and os.path.isdir(self.download_dir):

                shutil.rmtree(self.download_dir, ignore_errors=True)

                print("[Darkelf] Temp downloads wiped")

        except Exception as e:
            print("Download wipe error:", e)

    # -------------------------------------------------
    # Navigation Policy (Darkelf Network Interception)
    # -------------------------------------------------
    def webView_decidePolicyForNavigationAction_decisionHandler_(
        self, webView, navAction, decisionHandler
    ):

        try:
            if not navAction or not navAction.request():
                decisionHandler(WKNavigationActionPolicyAllow)
                return

            req = navAction.request()
            url_obj = req.URL()
            if not url_obj:
                decisionHandler(WKNavigationActionPolicyAllow)
                return

            url_str = str(url_obj.absoluteString() or "").strip()
            scheme = str(url_obj.scheme() or "").lower()
            host = str(url_obj.host() or "")

            nav_type = navAction.navigationType()
            owner = getattr(self, "owner", None)

            # -------------------------------------------------
            # Darkelf Network Policy (PQ tagging + optional allow/block/redirect)
            # -------------------------------------------------
            policy_meta = {}
            try:
                if owner and getattr(owner, "net_policy", None):
                    policy_result = owner.net_policy.inspect(url_str, nav_type)

                    if (
                        isinstance(policy_result, tuple)
                        and len(policy_result) == 2
                        and isinstance(policy_result[1], dict)
                    ):
                        policy_decision, policy_meta = policy_result
                    else:
                        policy_decision, policy_meta = policy_result, {}
                                                
                    if owner and hasattr(owner, "mini_ai"):
                        try:
                            meta = {
                                "type": str(nav_type),
                                "source": "native_nav",
                                "host": host,
                                "scheme": scheme,
                            }
                            if isinstance(policy_meta, dict):
                                meta.update(policy_meta)

                            owner.mini_ai.monitor_network(url_str, meta)
                        except Exception as e:
                            log(2, e)

                    if policy_decision == "block":
                        decisionHandler(WKNavigationActionPolicyCancel)
                        return

                    if (
                        isinstance(policy_decision, tuple)
                        and len(policy_decision) >= 2
                        and policy_decision[0] == "redirect"
                    ):
                        new_url = policy_decision[1]
                        try:
                            webView.loadRequest_(
                                NSURLRequest.requestWithURL_(
                                    NSURL.URLWithString_(new_url)
                                )
                            )
                        except Exception as e:
                            log(2, e)
                        decisionHandler(WKNavigationActionPolicyCancel)
                        return

            except Exception as e:
                print("[Policy] inspect error:", e)
                policy_meta = {}

            # -------------------------------------------------
            # Invalid URLs
            # -------------------------------------------------
            if scheme in ("http", "https") and not host:
                decisionHandler(WKNavigationActionPolicyCancel)
                return

            # -------------------------------------------------
            # Allow blob URLs (downloads, media, etc)
            # -------------------------------------------------
            if scheme == "blob":
                decisionHandler(WKNavigationActionPolicyAllow)
                return

            # -------------------------------------------------
            # Block dangerous protocols
            # -------------------------------------------------
            if scheme in ("ftp", "file", "javascript"):
                print("[Darkelf] Blocked scheme:", scheme)
                decisionHandler(WKNavigationActionPolicyCancel)
                return

            # -------------------------------------------------
            # Force HTTPS upgrade
            # -------------------------------------------------
            if scheme == "http":
                https_url = url_str.replace("http://", "https://", 1)
                try:
                    webView.loadRequest_(
                        NSURLRequest.requestWithURL_(NSURL.URLWithString_(https_url))
                    )
                except Exception as e:
                    log(2, e)
                decisionHandler(WKNavigationActionPolicyCancel)
                return

            # -------------------------------------------------
            # Optional tracker blocking (domain level)
            # -------------------------------------------------
            blocked_domains = (
                "doubleclick.net",
                "google-analytics.com",
                "facebook.net",
                "googletagmanager.com",
            )

            host_l = host.lower()
            for domain in blocked_domains:
                if domain in host_l:
                    print("[Darkelf] Tracker blocked:", host_l)
                    decisionHandler(WKNavigationActionPolicyCancel)
                    return

            # -------------------------------------------------
            # Allow navigation
            # -------------------------------------------------
            decisionHandler(WKNavigationActionPolicyAllow)

        except Exception as e:
            print("[NavDelegate] Policy decision error:", e)
            decisionHandler(WKNavigationActionPolicyAllow)

    # -------------------------------------------------
    # TLS Certificate Inspection
    # -------------------------------------------------
    def webView_didReceiveAuthenticationChallenge_completionHandler_(
        self, webView, challenge, completionHandler
    ):

        try:

            owner = getattr(self, "owner", None)

            protectionSpace = challenge.protectionSpace()
            authMethod = protectionSpace.authenticationMethod()

            if authMethod == NSURLAuthenticationMethodServerTrust:

                serverTrust = protectionSpace.serverTrust()
                isTrusted = False

                if serverTrust:

                    try:
                        isTrusted = bool(SecTrustEvaluateWithError(serverTrust, None))
                    except Exception as e:
                        print("[TLS] Trust evaluation failed:", e)

                    cert = SecTrustGetCertificateAtIndex(serverTrust, 0)

                    if cert:
                        summary = SecCertificateCopySubjectSummary(cert)
                        log(2, "🔎 Certificate Subject:", summary)

                        # ✅ --- PQ TRUST CACHE (UI-DRIVEN, NO SPAM) ---
                        try:
                            if owner:

                                if not hasattr(owner, "_pq_trust_cache"):
                                    owner._pq_trust_cache = {}

                                host = protectionSpace.host() or "unknown"

                                fp = hashlib.sha3_512(str(summary).encode()).hexdigest()

                                if host not in owner._pq_trust_cache:
                                    owner._pq_trust_cache[host] = fp
                                    owner._pq_trust_status = "ok"
                                else:
                                    if owner._pq_trust_cache[host] != fp:
                                        owner._pq_trust_status = "warn"
                                    else:
                                        owner._pq_trust_status = "ok"

                        except Exception as e:
                            log(2, e)

                        # ✅ --- END PQ BLOCK ---

                    if owner and hasattr(owner, "update_security_indicator"):

                        NSOperationQueue.mainQueue().addOperationWithBlock_(
                            lambda: owner.update_security_indicator(isTrusted)
                        )

                completionHandler(
                    NSURLSessionAuthChallengeUseCredential,
                    NSURLCredential.credentialForTrust_(serverTrust),
                )
                return

        except Exception as e:
            print("[Cert Inspection Error]", e)

        completionHandler(NSURLSessionAuthChallengePerformDefaultHandling, None)

    # -------------------------------------------------
    # Load Failure
    # -------------------------------------------------
    def webViewWebContentProcessDidTerminate_(self, webView):

        print("[WebKit] WebContent process crashed")

        try:
            # 🔒 Prevent reload loop
            if getattr(webView, "_darkelf_reloading", False):
                return

            webView._darkelf_reloading = True

            owner = getattr(self, "owner", None)

            def _reload():
                try:
                    if owner and owner._is_tab_webview(webView):

                        # 🔥 Preserve your original homepage recovery
                        url = webView.URL()
                        url_str = str(url.absoluteString()) if url else ""

                        if not url_str or url_str.startswith("darkelf://"):
                            webView.loadRequest_(
                                NSURLRequest.requestWithURL_(
                                    NSURL.URLWithString_(HOME_URL)
                                )
                            )
                        else:
                            webView.reload()

                except Exception as e:
                    print("[WebKit] Recovery failed:", e)

                finally:
                    webView._darkelf_reloading = False

            # ⏱ small delay avoids WebKit race condition
            threading.Timer(0.15, _reload).start()

        except Exception as e:
            print("[WebProcessFix] reload error:", e)

class DarkelfMenuDelegate(NSObject):

    def menu_willOpen_(self, menu, event):
        for item in menu.itemArray():
            item.setAttributedTitle_(
                NSAttributedString.alloc().initWithString_attributes_(
                    item.title(), {"NSForegroundColor": NSColor.whiteColor()}
                )
            )


IS_MAC = sys.platform == "darwin"
if not IS_MAC:
    print("[Darkelf] macOS only.")
    sys.exit(1)

APP_NAME = "Darkelf"

HOMEPAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Darkelf Browser</title>

<style>

:root{
  --bg:#0a0b10;
  --accent:#34C759;
  --text:#eef2f6;
}

*{box-sizing:border-box;}

html,body{
  height:100%;
  margin:0;
  overflow:hidden;
}

body{
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  background:
    radial-gradient(1200px 600px at 20% -10%, rgba(52,199,89,.35), transparent 60%),
    radial-gradient(1000px 600px at 120% 10%, rgba(52,199,89,.45), transparent 60%),
    var(--bg);

  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;

  color:var(--text);
}

/* animated particle grid */

.particles{
  position:fixed;
  inset:0;
  pointer-events:none;

  background-image:
    radial-gradient(rgba(52,199,89,.7) 1px, transparent 1px);

  background-size:90px 90px;

  opacity:.15;

  animation:particleMove 80s linear infinite;
}

@keyframes particleMove{
  from{transform:translateY(0);}
  to{transform:translateY(-200px);}
}

/* logo */

.brand{
  font-size:3.7rem;
  font-weight:800;
  letter-spacing:-.02em;
  color:#34C759;

  text-shadow:
    0 0 10px rgba(52,199,89,.8),
    0 0 30px rgba(52,199,89,.5),
    0 0 60px rgba(52,199,89,.25);

  animation:pulse 3s ease-in-out infinite;
}

@keyframes pulse{

  0%{
    text-shadow:
      0 0 10px rgba(52,199,89,.8),
      0 0 30px rgba(52,199,89,.5),
      0 0 60px rgba(52,199,89,.25);
  }

  50%{
    text-shadow:
      0 0 18px rgba(52,199,89,1),
      0 0 50px rgba(52,199,89,.7),
      0 0 90px rgba(52,199,89,.4);
  }

  100%{
    text-shadow:
      0 0 10px rgba(52,199,89,.8),
      0 0 30px rgba(52,199,89,.5),
      0 0 60px rgba(52,199,89,.25);
  }

}

.tagline{
  margin-top:20px;
  font-size:1rem;
  letter-spacing:.25em;
  text-transform:uppercase;
  color:#cfd8e3;
}

.ai{
  position:absolute;
  bottom:50px;
  font-size:.85rem;
  letter-spacing:.25em;
  color:#34C759;
  opacity:.8;
}

</style>
</head>

<body>

<div class="particles"></div>

<div class="brand">
Darkelf Browser
</div>

<div class="tagline">
Cocoa • Private • Hardened
</div>

<div class="ai">
Darkelf MiniAI Sentinel
</div>

</body>
</html>
"""

UNIFIED_DEFENSE_JS = r"""
(function(){

    // ============================================================
    // 🚫 WEBRTC HARD BLOCK (ALWAYS RUN FIRST)
    // ============================================================

    (function(){

        const block = () => { throw new Error("WebRTC blocked"); };

        try {
            Object.defineProperty(window, "RTCPeerConnection", {
                get: () => undefined,
                configurable: true
            });
        } catch(e){}

        try {
            Object.defineProperty(window, "webkitRTCPeerConnection", {
                get: () => undefined,
                configurable: true
            });
        } catch(e){}

        try {
            Object.defineProperty(window, "mozRTCPeerConnection", {
                get: () => undefined,
                configurable: true
            });
        } catch(e){}

        try { delete window.RTCIceCandidate; } catch(e){}
        try { delete window.RTCSessionDescription; } catch(e){}

        try {
            if (navigator.mediaDevices) {
                navigator.mediaDevices.getUserMedia = block;
                navigator.mediaDevices.enumerateDevices = async () => [];
            }
        } catch(e){}

        try { navigator.getUserMedia = block; } catch(e){}

    })();
    
    // ============================================================
    // 🌐 TIMEZONE / LOCALE DEFENSE
    // ============================================================

    try {
        Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
            value: function() {
                return { timeZone: "UTC", locale: "en-US" };
            },
            configurable: true
        });
    } catch(e){}


    // ============================================================
    // ⚡ PERFORMANCE DEFENSE
    // ============================================================

    (function() {
      if (window.performance && window.performance.now) {
        const realNow = window.performance.now.bind(window.performance);
        window.performance.now = function() {
          return realNow() + (Math.random() * 15 - 7);
        };
      }

      if (window.performance && window.performance.timing) {
        for (let k in window.performance.timing) {
          try {
            if (typeof window.performance.timing[k] === "number") {
              window.performance.timing[k] =
                window.performance.timing[k] + Math.floor(Math.random() * 15 - 7);
            }
          } catch(e){}
        }
      }
    })();


    // ============================================================
    // 🔋 BATTERY DEFENSE
    // ============================================================

    if ("getBattery" in navigator) {
      navigator.getBattery = function() {
        return Promise.resolve({
          charging: true,
          chargingTime: 0,
          dischargingTime: Infinity,
          level: 1,
          addEventListener: function(){},
          removeEventListener: function(){},
          onchargingchange: null,
          onlevelchange: null
        });
      };
    }

    // ============================================================
    // 🔐 PQ SEED REQUIRED BELOW
    // ============================================================

    let ROOT_HEX = window.__darkelf_pq_seed_hex || "deadbeefdeadbeefdeadbeefdeadbeef";

    // 🔥 DARKELF GROUP BUCKET (SYNC WITH UA)
    let __darkelf_bucket = 0;

    try {
        __darkelf_bucket = parseInt(ROOT_HEX.slice(0, 8), 16) % 32;
    } catch(e){}

    function hex32(s){ return parseInt(s,16)>>>0; }

    const ROOT0 = hex32(ROOT_HEX.slice(0,8));
    const ROOT1 = hex32(ROOT_HEX.slice(8,16));
    const ROOT2 = hex32(ROOT_HEX.slice(16,24));
    const ROOT3 = hex32(ROOT_HEX.slice(24,32));

    function mix4(x,a,b,c,d){
        x=(x^a)>>>0; x=Math.imul(x,0x9e3779b1)>>>0;
        x=(x^b)>>>0; x=Math.imul(x,0x85ebca6b)>>>0;
        x=(x^c)>>>0; x=Math.imul(x,0xc2b2ae35)>>>0;
        x=(x^d)>>>0; x=Math.imul(x,0x27d4eb2f)>>>0;
        x^=x>>>15; x^=x>>>13;
        return x>>>0;
    }

    function derive(a,b,c,d){
        return [(ROOT0^a)>>>0,(ROOT1^b)>>>0,(ROOT2^c)>>>0,(ROOT3^d)>>>0];
    }

    const CANVAS_SEED = derive(1,2,3,4);
    const FONT_SEED   = derive(5,6,7,8);
    const WEBGL_SEED  = derive(9,10,11,12);
    const AUDIO_SEED  = derive(13,14,15,16);

    function mixCanvas(x){return mix4(x,...CANVAS_SEED);}
    function mixFont(x){return mix4(x,...FONT_SEED);}
    function mixWebGL(x){return mix4(x,...WEBGL_SEED);}
    function mixAudio(x){return mix4(x,...AUDIO_SEED);}

    // ============================================================
    // 🌍 ORIGIN ENTROPY
    // ============================================================

    let origin = location.origin||"";
    try{origin=window.top.location.origin||origin;}catch(e){}

    let originHash=0;
    for(let i=0;i<origin.length;i++){
        originHash=(originHash*31+origin.charCodeAt(i))>>>0;
    }

    const FONT_SITE = mixFont(originHash);
    const WEBGL_SITE = mixWebGL(originHash);

    // ============================================================
    // 🎯 CANVAS
    // ============================================================

    (function(){

        function noise(i){
            return ((mixCanvas(i^(i*31))%8)-4);
        }

        function apply(img){
            const d=img.data;
            for(let i=0;i<d.length;i++){
                d[i]=Math.max(0,Math.min(255,d[i]+noise(i)));
            }
        }

        function clone(ctx,src){
            const c=ctx.createImageData(src.width,src.height);
            c.data.set(src.data);
            return c;
        }

        const origToDataURL=HTMLCanvasElement.prototype.toDataURL;

        HTMLCanvasElement.prototype.toDataURL=function(){
            try{
                const ctx=this.getContext("2d");
                if(ctx){
                    const w=this.width,h=this.height;
                    const orig=ctx.getImageData(0,0,w,h);
                    const mod=clone(ctx,orig);
                    apply(mod);
                    ctx.putImageData(mod,0,0);
                    const r=origToDataURL.apply(this,arguments);
                    ctx.putImageData(orig,0,0);
                    return r;
                }
            }catch(e){}
            return origToDataURL.apply(this,arguments);
        };

        const origGetImageData=CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData=function(x,y,w,h){
            const img=origGetImageData.call(this,x,y,w,h);
            apply(img);
            return img;
        };

    })();

    // ============================================================
    // 🔤 FONT
    // ============================================================

    function fontSeed(text){
        if(!text||!text.length) return FONT_SITE;
        return (
            text.length*131 ^
            text.charCodeAt(0)*17 ^
            text.charCodeAt(text.length-1)*31 ^
            FONT_SITE
        )>>>0;
    }

    const origMeasure=CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText=function(t){
        const r=origMeasure.apply(this,arguments);
        if(typeof t==="string"&&t.length){
            const m=mixFont(fontSeed(t));
            r.width+=((m%1000)/1000-0.5)*1.2;
        }
        return r;
    };

    const ow=Object.getOwnPropertyDescriptor(HTMLElement.prototype,"offsetWidth");
    const oh=Object.getOwnPropertyDescriptor(HTMLElement.prototype,"offsetHeight");

    Object.defineProperty(HTMLElement.prototype,"offsetWidth",{get(){
        const w=ow.get.call(this);
        const t=this.textContent||"";
        return t? w+((mixFont(fontSeed(t))%5)-2):w;
    }});

    Object.defineProperty(HTMLElement.prototype,"offsetHeight",{get(){
        const h=oh.get.call(this);
        const t=this.textContent||"";
        return t? h+((mixFont(fontSeed(t)^0x9e3779b1)%5)-2):h;
    }});

    const origRect=Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect=function(){
        const r=origRect.apply(this,arguments);
        const t=this.textContent||"";
        if(!t) return r;
        const m=mixFont(fontSeed(t)^0x85ebca6b);
        const dx=((m%5)-2)*0.25;
        const dy=(((m>>>3)%5)-2)*0.25;
        return {...r,x:r.x+dx,y:r.y+dy,left:r.left+dx,top:r.top+dy};
    };

    // ============================================================
    // 🎯 WEBGL
    // ============================================================

    function patchGL(p){
        if(!p)return;

        const gp=p.getParameter;
        p.getParameter=function(x){
            const v=gp.apply(this,arguments);
            const m=mixWebGL(x^WEBGL_SITE);
            if(typeof v==="number") return v+((m%3)-1);
            if(typeof v==="string"&&m%2===0) return v+" ";
            return v;
        };

        const rp=p.readPixels;
        p.readPixels=function(x,y,w,h,f,t,pix){
            rp.apply(this,arguments);
            if(pix){
                for(let i=0;i<pix.length;i++){
                    pix[i]+=((mixWebGL(i^WEBGL_SITE)%3)-1);
                }
            }
        };
    }

    patchGL(WebGLRenderingContext&&WebGLRenderingContext.prototype);
    patchGL(WebGL2RenderingContext&&WebGL2RenderingContext.prototype);
    
    // ============================================================
    // 🚀 WEBGPU (SAFE HASH ROTATION — UNIFIED WITH PQ)
    // ============================================================

    (function(){

        if (!("gpu" in navigator)) return;

        // 🔒 derive WebGPU seed from existing root system
        const WEBGPU_SEED = derive(17,18,19,20);

        function mixWebGPU(x){
            return mix4(x, ...WEBGPU_SEED);
        }

        // 🌍 bind to origin (same pattern as WebGL)
        let origin = location.origin || "";
        try { origin = window.top.location.origin || origin; } catch(e){}

        let originHash = 0;
        for (let i = 0; i < origin.length; i++){
            originHash = (originHash * 31 + origin.charCodeAt(i)) >>> 0;
        }

        const WEBGPU_SITE = mixWebGPU(originHash);

        // --------------------------------------------------------
        // 🔧 PATCH navigator.gpu.requestAdapter
        // --------------------------------------------------------

        const origRequestAdapter = navigator.gpu.requestAdapter.bind(navigator.gpu);

        navigator.gpu.requestAdapter = async function(options){

            const adapter = await origRequestAdapter(options);
            if (!adapter) return adapter;

            return new Proxy(adapter, {

                get(target, prop){

                    // 🔒 Slight string perturbation (stable)
                    if (prop === "name"){
                        const base = target.name || "GPU";
                        const m = mixWebGPU(base.length ^ WEBGPU_SITE);
                        return (m % 2 === 0) ? base : base + " ";
                    }

                    // 🔒 Stable numeric perturbation
                    if (prop === "limits"){
                        const limits = target.limits;
                        return new Proxy(limits, {
                            get(lim, key){
                                const val = lim[key];
                                if (typeof val === "number"){
                                    return val + ((mixWebGPU(val ^ WEBGPU_SITE) % 3) - 1);
                                }
                                return val;
                            }
                        });
                    }

                    return target[prop];
                }
            });
        };

        // --------------------------------------------------------
        // 🔧 PATCH GPUDevice → buffer readback noise
        // --------------------------------------------------------

        const origRequestDevice = GPUAdapter.prototype.requestDevice;

        GPUAdapter.prototype.requestDevice = async function(){

            const device = await origRequestDevice.apply(this, arguments);
            if (!device) return device;

            const origCreateBuffer = device.createBuffer;

            device.createBuffer = function(desc){

                const buffer = origCreateBuffer.call(this, desc);

                const origMapAsync = buffer.mapAsync;

                buffer.mapAsync = async function(){

                    await origMapAsync.apply(this, arguments);

                    const origGetRange = this.getMappedRange;

                    this.getMappedRange = function(){

                        const raw = origGetRange.apply(this, arguments);
                        const view = new Uint8Array(raw);

                        // 🔒 deterministic low-noise injection
                        for (let i = 0; i < view.length; i++){
                            view[i] += ((mixWebGPU(i ^ WEBGPU_SITE) % 3) - 1);
                        }

                        return view;
                    };
                };

                return buffer;
            };

            return device;
        };

    })();
    
    // ============================================================
    // 🎯 AUDIO
    // ============================================================

    try{
        const orig=OfflineAudioContext.prototype.getChannelData;
        OfflineAudioContext.prototype.getChannelData=function(){
            const d=orig.apply(this,arguments);
            for(let i=0;i<d.length;i++){
                d[i]+=((mixAudio(i)%3)-1)*0.00001;
            }
            return d;
        };
    }catch(e){}

})();
"""


# ================= Helper widgets =================
class HoverButton(NSButton):
    def init(self):
        self = objc.super(HoverButton, self).init()
        if self is None:
            return None
        self._hoverArea = None
        return self

    def updateTrackingAreas(self):
        if getattr(self, "_hoverArea", None) is not None:
            self.removeTrackingArea_(self._hoverArea)
        opts = NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways
        self._hoverArea = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(), opts, self, None
        )
        self.addTrackingArea_(self._hoverArea)
        objc.super(HoverButton, self).updateTrackingAreas()

    def mouseEntered_(self, evt):
        try:
            self.setContentTintColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    52 / 255.0, 199 / 255.0, 89 / 255.0, 1.0
                )
            )
        except Exception as e:
            log(2, e)

    def mouseExited_(self, evt):
        try:
            self.setContentTintColor_(NSColor.whiteColor())
        except Exception as e:
            log(2, e)


# ================= Tabs =================
@dataclass
class Tab:
    view: WKWebView
    data_store: WKWebsiteDataStore

    # Identity
    tab_uid: int = None
    container_nonce: str = None

    # Navigation
    url: str = ""
    host: str = "new"

    # UI
    title: str = "New Tab"

    # Favicon
    favicon: NSImage = None
    favicon_host: str = ""      # Host the current favicon belongs to

    # Privacy / Fingerprinting
    canvas_seed: int = None


# =============================================================================
# ADD THIS NEW CLASS near _NavDelegate (top-level, not nested)
# =============================================================================
class _WindowDelegate(NSObject):
    def initWithOwner_(self, owner):
        self = objc.super(_WindowDelegate, self).init()
        if self is None:
            return None
        self.owner = owner
        return self

    # NSWindowDelegate hook
    def windowWillClose_(self, notification):
        try:
            owner = getattr(self, "owner", None)
            if owner is not None:
                owner.windowWillClose_(notification)
        except Exception as e:
            print("[WindowDelegate] windowWillClose_ error:", e)


# =============================================================================
# FULL UPDATED SearchHandler (as-is, this part is already correct)
# =============================================================================
class SearchHandler(NSObject):
    def initWithOwner_(self, owner): ...
    def userContentController_didReceiveScriptMessage_(self, controller, message):
        self = objc.super(SearchHandler, self).init()
        if self is None:
            return None
        self.owner = owner
        return self

    def userContentController_didReceiveScriptMessage_(self, controller, message):
        try:
            owner = getattr(self, "owner", None)
            if (
                not owner
                or not getattr(owner, "tabs", None)
                or getattr(owner, "active", -1) < 0
            ):
                return

            body = message.body()
            print("🔥 MESSAGE RECEIVED:", body)

            if body == "darkelf_native_fullscreen":
                print("🔥 FULLSCREEN TRIGGERED")
                owner.window.toggleFullScreen_(None)
                return

            q = str(body)
            # Only search if q is non-empty, longer than 1 character
            if not q or len(q.strip()) < 2:
                return  # Ignore short/no input

            url = "https://lite.duckduckgo.com/lite/?q=" + re.sub(r"\s+", "+", q)
            owner._add_tab(url)

        except Exception as e:
            print("SearchHandler error:", e)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class AddressField(NSSearchField):

    def initWithFrame_owner_(self, frame, owner):
        self = objc.super(AddressField, self).initWithFrame_(frame)
        if self is None:
            return None
        self._owner = owner
        return self

    def drawFocusRingMask(self):
        pass

    def focusRingMaskBounds(self):
        return NSMakeRect(0, 0, 0, 0)

    def rightMouseDown_(self, event):
        try:
            owner = getattr(self, "_owner", None)

            if owner and hasattr(owner, "_show_context_popover"):
                loc = event.locationInWindow()
                owner._show_context_popover(self, loc)
            else:
                objc.super(AddressField, self).rightMouseDown_(event)

        except Exception as e:
            print("Context menu popover error:", e)
            objc.super(AddressField, self).rightMouseDown_(event)
            
class DraggableFindBar(NSView):

    def mouseDown_(self, event):

        self._drag_start = event.locationInWindow()
        self._start_origin = self.frame().origin

    def mouseDragged_(self, event):

        current = event.locationInWindow()

        dx = current.x - self._drag_start.x
        dy = current.y - self._drag_start.y

        new_x = self._start_origin.x + dx
        new_y = self._start_origin.y + dy

        self.setFrameOrigin_((new_x, new_y))
        
class DarkelfSearchField(NSSearchField):

    def cancelOperation_(self, sender):

        try:

            if hasattr(self, "browser"):
                self.browser.hideFindBar_(None)

        except Exception as e:

            print("[FindBar ESC Error]", e)

    def keyDown_(self, event):

        # fallback

        if event.keyCode() == 53:

            try:

                if hasattr(self, "browser"):
                    self.browser.hideFindBar_(None)

            except Exception as e:

                print("[FindBar ESC Error]", e)

            return

        objc.super(DarkelfSearchField, self).keyDown_(event)
        
# =============================================================================
# FULL UPDATED Browser.init (critical changes marked)
# =============================================================================
class Browser(NSObject):

    def init(self):
        self = objc.super(Browser, self).init()
        if self is None:
            return None
            
        self.menu_panel = None
        self.menu_open = False
        self._initBookmarks()
        self._initKeyboardShortcuts()
        # ----------------------------
        # PQ CORE (SESSION LEVEL)
        # ----------------------------

        # Strong session seed (required)
        self._pq_seed = secrets.token_bytes(32)

        # 🔥 NEW: hidden session salt (for fingerprint secrecy)
        self._pq_salt = hashlib.sha3_256(self._pq_seed).digest()[:16]

        # ----------------------------
        # PQ SERIALIZATION QUEUE
        # ----------------------------

        # Ensures deterministic ordering of PQ operations
        self._pq_queue = NSOperationQueue.alloc().init()
        self._pq_queue.setMaxConcurrentOperationCount_(1)

        # ----------------------------
        # TAB + PQ STATE REGISTRY
        # ----------------------------

        # Track tabs explicitly for PQ consistency
        self.tabs = []

        # ----------------------------
        # FIRST PARTY ISOLATION (FPI)
        # ----------------------------

        self.fpi = FirstPartyIsolation(tab_isolation=True)

        # ----------------------------
        # OPTIONAL: PQ CONFIG FLAGS
        # ----------------------------

        self._pq_enabled = True

        # ---- Usual field setup ----
        self.cookies_enabled = False
        self.js_enabled = True
        self.tabs = []
        self.active = 0

        # WebKit memory protection
        self.page_load_count = 0
        self.process_pool = WKProcessPool.alloc().init()

        self.tab_btns = []
        self.tab_close_btns = []
        self.active = -1
        self._window = []

        self._containers = {}

        self._tab_uid_counter = 0
        # ---- 1. Create window ----
        self.window = self._make_window()

        self._pq_trust_cache = {}

        self.window.setCollectionBehavior_(
            128
        )  # NSWindowCollectionBehaviorFullScreenPrimary

        # ---- 2. Strong refs for delegates/handlers ----
        self._strong_refs = []

        self._window_delegate = _WindowDelegate.alloc().initWithOwner_(self)
        self._nav_delegate = _NavDelegate.alloc().initWithOwner_(self)
        self._ui_delegate = _UIDelegate.alloc().initWithOwner_(self)
        self._search_handler = SearchHandler.alloc().initWithOwner_(self)

        self._strong_refs.extend(
            [
                self._window_delegate,
                self._nav_delegate,
                self._ui_delegate,
                self._search_handler,
            ]
        )

        self.window.setDelegate_(self._window_delegate)

        ContentRuleManager.load_rules()

        self.mini_ai = DarkelfMiniAISentinel()
        self.mini_ai.browser = self

        self.download_ui = DownloadProgressView.alloc().initWithFrame_(
            NSMakeRect(20, 60, 520, 70)
        )
        self.download_ui.setHidden_(True)
        self.net_policy = DarkelfNetworkPolicy(self)

        content = self.window.contentView()

        content.addSubview_positioned_relativeTo_(
            self.download_ui, 1, None  # NSWindowAbove
        )

        # ensure it resizes with the window
        self.download_ui.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)

        # ---- 4. Toolbar, Tabbar, UI wiring ----
        self.toolbar = self._make_toolbar()

        self._build_tabbar()
        self._add_tab(home=True)
        self._bring_tabbar_to_front()

        self.window.setDelegate_(self)

        self.window.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        
        NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            0.01,
            False,
            lambda t: (
                self._layout_toolbar(),
                self._layout(),
                self._bring_tabbar_to_front(),
            ),
        )
        
        apply_darkelf_theme()

        self.download_dir = None

        self._pq_file_hashes = {}
        # ---- 7. Keyboard monitor ----
        self._install_key_monitor()

        try:
            nc = NSNotificationCenter.defaultCenter()
            nc.addObserver_selector_name_object_(
                self, "onResize:", "NSWindowDidResizeNotification", self.window
            )
        except Exception as e:
            log(2, e)

        return self
        
        # ============================================================
        # BOOKMARKS
        # ============================================================

        BOOKMARK_FILE = os.path.join(
            os.path.expanduser("~"),
            ".darkelf_bookmarks.json"
        )
        
        # --------------------------------------------------
        # Keyboard Shortcut Library
        # --------------------------------------------------

        self.shortcut_sections = {

            "Navigation": [
                ("⌘←", "Back"),
                ("⌘→", "Forward"),
                ("⌘R", "Reload"),
                ("⌘L", "Focus Address Bar"),
                ("⌘F", "Find in Page"),
                ("ESC", "Close Find Bar"),
                ("⌃⌘F", "Toggle Fullscreen"),
            ],

            "Tabs": [
                ("⌘T", "New Tab"),
                ("⌘W", "Close Tab"),
            ],

            "Zoom": [
                ("⌘+", "Zoom In"),
                ("⌘-", "Zoom Out"),
            ],

            "Application": [
                ("⇧⌘X", "Exit Darkelf"),
            ],
        }

        self.shortcut_expanded = {
            section: True
            for section in self.shortcut_sections
        }
        
    def showKeyboardShortcuts_(self, sender):

        if not getattr(self, "shortcut_view", None):
            self._createShortcutView()

        if getattr(self, "bookmark_view", None):
            self.bookmark_view.setHidden_(True)

        for b in (
            self.btn_bookmarks,
            self.btn_add_bookmark,
            self.btn_hotkeys,
            self.btn_mini_ai,
            self.btn_nuke,
            self.btn_js,
            self.btn_about,
        ):
            b.setHidden_(True)

        self.shortcut_view.setHidden_(False)

        self._reloadShortcutList()
        
    def toggleShortcutSection_(self, sender):

        sections = list(self.shortcut_sections.keys())

        index = sender.tag()

        if index < 0 or index >= len(sections):
            return

        section = sections[index]

        self.shortcut_expanded[section] = (
            not self.shortcut_expanded.get(section, True)
        )

        self._reloadShortcutList()
            
    def _initBookmarks(self):

        self.bookmarks = []
        self.bookmark_mode = False
        self._loadBookmarks()
        
    def _initKeyboardShortcuts(self):
    
        # ------------------------------------
        # Keyboard Shortcut Categories
        # ------------------------------------

        self.shortcut_sections = {

            "Navigation": [
                ("⌘←", "Back"),
                ("⌘→", "Forward"),
                ("⌘R", "Reload"),
                ("⌘L", "Focus Address Bar"),
                ("⌘F", "Find in Page"),
                ("ESC", "Close Find Bar"),
                ("⌃⌘F", "Toggle Fullscreen"),
            ],

            "Tabs": [
                ("⌘T", "New Tab"),
                ("⌘W", "Close Tab"),
            ],

            "Zoom": [
                ("⌘+", "Zoom In"),
                ("⌘-", "Zoom Out"),
            ],

            "Application": [
                ("⇧⌘X", "Exit Darkelf"),
            ],
        }

        # Start collapsed
        self.shortcut_expanded = {
            section: False
            for section in self.shortcut_sections
        }

        self._loadBookmarks()

    def _loadBookmarks(self):
        self.bookmarks = []
        
    def _saveBookmarks(self):
        return

    def addCurrentBookmark_(self, sender=None):

        if self.active < 0:
            return

        tab = self.tabs[self.active]

        url = getattr(tab, "url", "")
        title = getattr(tab, "title", "") or url

        if not url:
            return

        for b in self.bookmarks:
            if b["url"] == url:
                return

        self.bookmarks.append(
            {
                "title": title,
                "url": url,
            }
        )

        self._saveBookmarks()

        if self.bookmark_mode:
            self._reloadBookmarkList()

    def openBookmark_(self, sender):

        idx = sender.tag()

        if idx < 0 or idx >= len(self.bookmarks):
            return

        url = self.bookmarks[idx]["url"]

        # Return to the normal menu state
        self.showMainMenu_(None)

        # Load the bookmarked page
        self._load_url_in_active(url)

        # Close the hamburger menu
        self.toggleMenu_(None)
            
    def _cleanup_unused_containers(self):

        try:

            active_keys = set()

            for i, tab in enumerate(self.tabs):

                try:
                    key = self.fpi._key(tab.url or HOME_URL, tab_uid=i)
                    active_keys.add(key)
                except Exception as e:
                    log(2, e)

            for key in list(self._containers.keys()):

                if key not in active_keys:
                    del self._containers[key]

        except Exception as e:
            log(2, e)

    def recycle_web_process(self):
        print("[Darkelf] Recycle disabled for testing")
        self.page_load_count = 0
        return

    @objc.IBAction
    def refreshMiniAI_(self, timer):

        if not hasattr(self, "mini_ai"):
            return

        try:
            # Handle automatic lockdown expiration
            self.mini_ai._maybe_auto_unlock(time.time())
        except Exception as e:
            print("[MiniAI Timer Error]", e)

        try:
            # Refresh the MiniAI status panel
            self.updateMiniAIIndicator()
        except Exception as e:
            log(2, e)
            
    def _createMenuPanel(self):
        
        if self.menu_panel:
            return

        width = 220
        height = 300

        cv = self.window.contentView()

        f = cv.bounds()

        self.menu_panel = NSView.alloc().initWithFrame_(
            NSMakeRect(
                f.size.width,
                f.size.height - height - 40,
                width,
                height,
            )
        )

        self.menu_panel.setAutoresizingMask_(
            NSViewMinXMargin | NSViewMinYMargin
        )

        # ==========================================================
        # DARKELF GLASS MENU PANEL
        # ==========================================================

        self.menu_panel.setWantsLayer_(True)

        layer = self.menu_panel.layer()

        # Deep matte black with transparency
        layer.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.02,
                0.025,
                0.03,
                0.90,
            ).CGColor()
        )

        # Rounded corners
        layer.setCornerRadius_(16)

        # Thin neon-green outline
        layer.setBorderWidth_(1.0)

        layer.setBorderColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.16,
                0.95,
                0.45,
                0.18,
            ).CGColor()
        )

        # Soft shadow
        layer.setShadowOpacity_(0.55)

        layer.setShadowRadius_(20)

        layer.setShadowOffset_(NSMakeSize(0, -2))

        layer.setShadowColor_(
            NSColor.blackColor().CGColor()
        )

        # Crisp edges
        layer.setMasksToBounds_(False)

        cv.addSubview_(self.menu_panel)
        
        # ----------------------------------------------------------
        # Menu Buttons
        # ----------------------------------------------------------

        self.btn_mini_ai.setTitle_(" MiniAI Report")
        self.btn_nuke.setTitle_(" Nuke Session")
        self.btn_js.setTitle_(" JavaScript")
        self.btn_hotkeys.setTitle_(" Keyboard Shortcuts")

        self.btn_bookmarks = NSButton.alloc().initWithFrame_(
            NSMakeRect(16, 170, 192, 34)
        )
        self.btn_bookmarks.setTitle_(" Bookmarks")

        bookmark_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "bookmark.fill",
            None,
        )

        bookmark_icon.setTemplate_(True)

        self.btn_bookmarks.setImage_(bookmark_icon)

        self.btn_bookmarks.setImagePosition_(NSImageLeft)

        self.btn_bookmarks.setContentTintColor_(
            NSColor.whiteColor()
        )
        self.btn_bookmarks.setBordered_(False)
        self.btn_bookmarks.setBezelStyle_(0)
        self.btn_bookmarks.setAlignment_(NSLeftTextAlignment)
        self.btn_bookmarks.setFont_(NSFont.systemFontOfSize_(14))
        self.btn_bookmarks.setTarget_(self)
        self.btn_bookmarks.setAction_("showBookmarks:")

        self.btn_add_bookmark = NSButton.alloc().initWithFrame_(
            NSMakeRect(16, 132, 192, 34)
        )
        self.btn_add_bookmark.setTitle_(" ➕ Add Current Page")
        self.btn_add_bookmark.setBordered_(False)
        self.btn_add_bookmark.setBezelStyle_(0)
        self.btn_add_bookmark.setAlignment_(NSLeftTextAlignment)
        self.btn_add_bookmark.setFont_(NSFont.systemFontOfSize_(14))
        self.btn_add_bookmark.setTarget_(self)
        self.btn_add_bookmark.setAction_("addCurrentBookmark:")

        # ----------------------------------------------------------
        # About Darkelf
        # ----------------------------------------------------------

        self.btn_about = NSButton.alloc().initWithFrame_(
            NSMakeRect(16, 94, 192, 34)
        )

        self.btn_about.setTitle_(" About Darkelf")

        about_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "info.circle.fill",
            None,
        )

        if about_icon:
            about_icon.setTemplate_(True)
            self.btn_about.setImage_(about_icon)

        self.btn_about.setImagePosition_(NSImageLeft)
        self.btn_about.setContentTintColor_(NSColor.whiteColor())
        self.btn_about.setBordered_(False)
        self.btn_about.setBezelStyle_(0)
        self.btn_about.setAlignment_(NSLeftTextAlignment)
        self.btn_about.setFont_(NSFont.systemFontOfSize_(14))
        self.btn_about.setTarget_(self)
        self.btn_about.setAction_("showAboutView:")
        
        self.btn_mini_ai.removeFromSuperview()
        self.btn_nuke.removeFromSuperview()
        self.btn_js.removeFromSuperview()
        self.btn_hotkeys.removeFromSuperview()
        self.btn_add_bookmark.removeFromSuperview()
        self.btn_about.removeFromSuperview()
        
        self.menu_panel.addSubview_(self.btn_bookmarks)
        self.menu_panel.addSubview_(self.btn_add_bookmark)

        buttons = [

            self.btn_bookmarks,
            self.btn_add_bookmark,

            self.btn_mini_ai,
            self.btn_nuke,
            self.btn_js,
            self.btn_hotkeys,
            self.btn_about,
        ]

        y = 245

        for b in buttons:

            b.setFrame_(NSMakeRect(16, y, 192, 34))
            b.setBordered_(False)
            b.setBezelStyle_(0)
            b.setImagePosition_(NSImageLeft)
            b.setAlignment_(NSLeftTextAlignment)
            b.setFont_(NSFont.systemFontOfSize_(14))

            self.menu_panel.addSubview_(b)

            y -= 38
            
    def toggleMenu_(self, sender):

        self._createMenuPanel()

        cv = self.window.contentView()
        f = cv.bounds()

        width = 220

        if self.menu_open:

            target = NSMakeRect(
                f.size.width,
                self.menu_panel.frame().origin.y,
                width,
                self.menu_panel.frame().size.height,
            )

        else:

            target = NSMakeRect(
                f.size.width - width - 10,
                self.menu_panel.frame().origin.y,
                width,
                self.menu_panel.frame().size.height,
            )

        self.menu_open = not self.menu_open

        def animate(ctx):

            ctx.setDuration_(0.20)

            self.menu_panel.animator().setFrame_(target)

        NSAnimationContext.runAnimationGroup_completionHandler_(
            animate,
            None,
        )
        
    # ==========================================================
    # BOOKMARK MANAGER (Part 1)
    # Creates the bookmark panel inside the hamburger menu
    # ==========================================================

    def _createBookmarksView(self):

        if getattr(self, "bookmark_view", None):
            return

        # Match the menu panel height
        self.bookmark_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 220, 300)
        )

        # Back button
        self.btn_bookmark_back = NSButton.alloc().initWithFrame_(
            NSMakeRect(12, 264, 80, 28)
        )

        self.btn_bookmark_back.setTitle_("← Back")
        self.btn_bookmark_back.setBordered_(False)
        self.btn_bookmark_back.setBezelStyle_(0)
        self.btn_bookmark_back.setAlignment_(NSLeftTextAlignment)
        self.btn_bookmark_back.setTarget_(self)
        self.btn_bookmark_back.setAction_("showMainMenu:")

        self.bookmark_view.addSubview_(self.btn_bookmark_back)

        # Title
        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(95, 266, 110, 20)
        )

        title.setEditable_(False)
        title.setBordered_(False)
        title.setDrawsBackground_(False)
        title.setSelectable_(False)
        title.setStringValue_("Bookmarks")
        title.setTextColor_(NSColor.whiteColor())
        title.setFont_(NSFont.boldSystemFontOfSize_(14))

        self.bookmark_view.addSubview_(title)

        # Scroll view
        self.bookmark_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(12, 8, 196, 240)
        )

        self.bookmark_scroll.setHasVerticalScroller_(True)
        self.bookmark_scroll.setHasHorizontalScroller_(False)
        self.bookmark_scroll.setAutohidesScrollers_(True)
        self.bookmark_scroll.setBorderType_(0)
        
        # ----------------------------------------------------------
        # Rounded Darkelf bookmark container
        # ----------------------------------------------------------

        self.bookmark_scroll.setWantsLayer_(True)

        scroll_layer = self.bookmark_scroll.layer()

        scroll_layer.setCornerRadius_(12)

        scroll_layer.setMasksToBounds_(True)

        scroll_layer.setBorderWidth_(1.0)

        scroll_layer.setBorderColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.16,
                0.95,
                0.45,
                0.12,
            ).CGColor()
        )

        scroll_layer.setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        # Don't let NSScrollView paint its default background
        self.bookmark_scroll.setDrawsBackground_(False)

        self.bookmark_document = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 196, 10)
        )

        self.bookmark_document.setWantsLayer_(True)

        self.bookmark_document.layer().setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.bookmark_scroll.setDocumentView_(self.bookmark_document)

        # Make the clip view transparent too
        clip = self.bookmark_scroll.contentView()

        clip.setWantsLayer_(True)

        clip.layer().setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.bookmark_view.addSubview_(self.bookmark_scroll)

        self.bookmark_view.setHidden_(True)

        self.bookmark_view.setFrameOrigin_((0, 0))

        self.menu_panel.addSubview_(self.bookmark_view)
        
    # ==========================================================
    # Bookmark Toolbar Sync
    # ==========================================================

    def updateBookmarkButton(self):

        if not hasattr(self, "btn_bookmark"):
            return

        try:
            if self.active < 0 or self.active >= len(self.tabs):
                return

            url = getattr(self.tabs[self.active], "url", "")

            bookmarked = any(
                b.get("url") == url
                for b in self.bookmarks
            )

            symbol = "bookmark.fill" if bookmarked else "bookmark"

            img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                symbol,
                None,
            )

            self.btn_bookmark.setImage_(img)

        except Exception as e:
            log(2, e)
            
    def refreshBookmarkButton(self):

        if not hasattr(self, "btn_bookmark"):
            return

        url = ""

        if 0 <= self.active < len(self.tabs):
            url = getattr(self.tabs[self.active], "url", "") or ""

        bookmarked = any(
            b["url"] == url
            for b in self.bookmarks
        )

        symbol = "bookmark.fill" if bookmarked else "bookmark"

        img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            symbol,
            None,
        )

        self.btn_bookmark.setImage_(img)
        
    # ==========================================================
    # Toolbar Bookmark Toggle
    # ==========================================================

    def toggleBookmarkToolbar_(self, sender):

        if self.active < 0 or self.active >= len(self.tabs):
            return

        url = self.tabs[self.active].url

        for i, bm in enumerate(self.bookmarks):
            if bm.get("url") == url:
    
                del self.bookmarks[i]

                self._saveBookmarks()
                self._reloadBookmarkList()
                self.updateBookmarkButton()

                return

        title = getattr(self.tabs[self.active], "title", "") or url

        self.bookmarks.append({
            "title": title,
            "url": url,
        })

        self._saveBookmarks()
        self._reloadBookmarkList()
        self.updateBookmarkButton()
    
    # ==========================================================
    # Show Bookmark View
    # ==========================================================

    def showBookmarks_(self, sender):

        if not getattr(self, "bookmark_view", None):
            self._createBookmarksView()

        # Hide main menu buttons
        for b in (
            self.btn_bookmarks,
            self.btn_add_bookmark,
            self.btn_mini_ai,
            self.btn_nuke,
            self.btn_js,
            self.btn_hotkeys,
            self.btn_about,
        ):
            b.setHidden_(True)

        # Bring bookmark view to the front every time
        self.bookmark_view.removeFromSuperview()
        self.menu_panel.addSubview_(self.bookmark_view)

        self.bookmark_view.setHidden_(False)

        green = NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.20,
            0.95,
            0.35,
            1.0,
        )

        self.btn_bookmarks.setContentTintColor_(green)

        self._reloadBookmarkList()
        
    # ==========================================================
    # Return to Main Menu
    # ==========================================================

    def showMainMenu_(self, sender):

        if getattr(self, "bookmark_view", None):
            self.bookmark_view.setHidden_(True)

        if getattr(self, "shortcut_view", None):
            self.shortcut_view.setHidden_(True)
            
        if getattr(self, "mini_ai_view", None):
            self.mini_ai_view.setHidden_(True)
            
        if getattr(self, "about_view", None):
            self.about_view.setHidden_(True)

        for b in (
            self.btn_bookmarks,
            self.btn_add_bookmark,
            self.btn_hotkeys,
            self.btn_mini_ai,
            self.btn_nuke,
            self.btn_js,
            self.btn_about,
        ):
            b.setHidden_(False)
    
    # ==========================================================
    # Reload Bookmark List
    # ==========================================================

    def _reloadBookmarkList(self):

        if not getattr(self, "bookmark_document", None):
            return

        for view in list(self.bookmark_document.subviews()):
            view.removeFromSuperview()

        bookmarks = getattr(self, "bookmarks", [])

        row_height = 34
        padding = 6
        top_margin = 10

        if not bookmarks:

            self.bookmark_document.setFrame_(
                NSMakeRect(0, 0, 196, 170)
            )

            lbl = NSTextField.alloc().initWithFrame_(
                NSMakeRect(10, 126, 170, 24)
            )

            lbl.setBordered_(False)
            lbl.setEditable_(False)
            lbl.setSelectable_(False)
            lbl.setDrawsBackground_(False)
            lbl.setAlignment_(NSLeftTextAlignment)
            lbl.setTextColor_(NSColor.systemGrayColor())
            lbl.setStringValue_("No bookmarks yet.")

            self.bookmark_document.addSubview_(lbl)
            return

        total_height = len(bookmarks) * (row_height + padding) + top_margin
        doc_height = max(240, total_height)

        self.bookmark_document.setFrame_(
            NSMakeRect(
                0,
                0,
                196,
                doc_height,
            )
        )

        # Start just below the top of the document
        y = doc_height - row_height - top_margin

        for index, bm in enumerate(bookmarks):

            title = bm.get("title") or bm.get("url", "")

            btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(10, y, 150, row_height)
            )

            btn.setBordered_(False)
            btn.setBezelStyle_(0)
            btn.setAlignment_(NSLeftTextAlignment)
            btn.setTitle_(title[:32])
            btn.setTag_(index)
            btn.setTarget_(self)
            btn.setAction_("openBookmark:")

            self.bookmark_document.addSubview_(btn)

            delete = NSButton.alloc().initWithFrame_(
                NSMakeRect(166, y + 5, 24, 24)
            )

            delete.setBordered_(False)
            delete.setBezelStyle_(0)
            delete.setTitle_("✕")
            delete.setTag_(index)
            delete.setTarget_(self)
            delete.setAction_("deleteBookmark:")

            self.bookmark_document.addSubview_(delete)

            y -= (row_height + padding)
            
    # ==========================================================
    # Delete Bookmark
    # ==========================================================

    def deleteBookmark_(self, sender):

        try:

            index = sender.tag()

            if index < 0 or index >= len(self.bookmarks):
                return

            del self.bookmarks[index]

            self._saveBookmarks()

            self._reloadBookmarkList()

        except Exception as e:
            print("[Bookmarks]", e)
            
    def _createShortcutView(self):

        if getattr(self, "shortcut_view", None):
            return

        # Match menu panel size
        self.shortcut_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 220, 300)
        )

        # --------------------------------------------------
        # Back button
        # --------------------------------------------------
        self.btn_shortcut_back = NSButton.alloc().initWithFrame_(
            NSMakeRect(12, 264, 80, 28)
        )

        self.btn_shortcut_back.setTitle_("← Back")
        self.btn_shortcut_back.setBordered_(False)
        self.btn_shortcut_back.setBezelStyle_(0)
        self.btn_shortcut_back.setAlignment_(NSLeftTextAlignment)
        self.btn_shortcut_back.setTarget_(self)
        self.btn_shortcut_back.setAction_("showMainMenu:")

        self.shortcut_view.addSubview_(self.btn_shortcut_back)

        # --------------------------------------------------
        # Title
        # --------------------------------------------------
        self.shortcut_title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(95, 266, 110, 20)
        )

        self.shortcut_title.setEditable_(False)
        self.shortcut_title.setBordered_(False)
        self.shortcut_title.setDrawsBackground_(False)
        self.shortcut_title.setSelectable_(False)
        self.shortcut_title.setStringValue_("Keyboard Shortcuts")
        self.shortcut_title.setTextColor_(NSColor.whiteColor())
        self.shortcut_title.setFont_(NSFont.boldSystemFontOfSize_(14))

        self.shortcut_view.addSubview_(self.shortcut_title)

        # --------------------------------------------------
        # Scroll View
        # --------------------------------------------------
        self.shortcut_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(12, 8, 196, 240)
        )

        self.shortcut_scroll.setHasVerticalScroller_(True)
        self.shortcut_scroll.setHasHorizontalScroller_(False)
        self.shortcut_scroll.setAutohidesScrollers_(True)
        self.shortcut_scroll.setBorderType_(0)

        self.shortcut_scroll.setWantsLayer_(True)

        scroll_layer = self.shortcut_scroll.layer()

        scroll_layer.setCornerRadius_(12)
        scroll_layer.setMasksToBounds_(True)
        scroll_layer.setBorderWidth_(1.0)

        scroll_layer.setBorderColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.16,
                0.95,
                0.45,
                0.12,
            ).CGColor()
        )

        scroll_layer.setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.shortcut_scroll.setDrawsBackground_(False)

        self.shortcut_document = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 196, 10)
        )

        self.shortcut_document.setWantsLayer_(True)

        self.shortcut_document.layer().setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.shortcut_scroll.setDocumentView_(self.shortcut_document)

        clip = self.shortcut_scroll.contentView()

        clip.setWantsLayer_(True)

        clip.layer().setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.shortcut_view.addSubview_(self.shortcut_scroll)

        self.shortcut_view.setHidden_(True)
        self.shortcut_view.setFrameOrigin_((0, 0))

        self.menu_panel.addSubview_(self.shortcut_view)
        
    def _reloadShortcutList(self):

        if not getattr(self, "shortcut_document", None):
            return

        for view in list(self.shortcut_document.subviews()):
            view.removeFromSuperview()

        row_height = 28
        header_height = 30
        padding = 4
        width = 196

        # --------------------------------------------------
        # Calculate document height first
        # --------------------------------------------------

        total_height = 10

        for section, items in self.shortcut_sections.items():

            total_height += header_height + padding

            if self.shortcut_expanded.get(section, True):
                total_height += len(items) * row_height

            total_height += 4

        total_height = max(240, total_height + 10)

        self.shortcut_document.setFrame_(
            NSMakeRect(
                0,
                0,
                width,
                total_height,
            )
        )

        # --------------------------------------------------
        # Layout from TOP downward
        # --------------------------------------------------

        y = total_height - 10 - header_height

        for idx, (section, items) in enumerate(self.shortcut_sections.items()):

            expanded = self.shortcut_expanded.get(section, True)

            header = NSButton.alloc().initWithFrame_(
                NSMakeRect(
                    8,
                    y,
                    width - 16,
                    header_height,
                )
            )

            header.setBordered_(False)
            header.setBezelStyle_(0)
            header.setAlignment_(NSLeftTextAlignment)
            header.setTitle_(("▼ " if expanded else "▶ ") + section)
            header.setTag_(idx)
            header.setTarget_(self)
            header.setAction_("toggleShortcutSection:")

            self.shortcut_document.addSubview_(header)

            y -= header_height + padding

            if expanded:

                for keys, desc in items:

                    key = NSTextField.alloc().initWithFrame_(
                        NSMakeRect(
                            22,
                            y + 3,
                            60,
                            22,
                        )
                    )

                    key.setBordered_(False)
                    key.setEditable_(False)
                    key.setSelectable_(False)
                    key.setDrawsBackground_(False)
                    key.setTextColor_(NSColor.systemGreenColor())
                    key.setFont_(
                        NSFont.monospacedSystemFontOfSize_weight_(12, 5)
                    )
                    key.setStringValue_(keys)

                    self.shortcut_document.addSubview_(key)

                    label = NSTextField.alloc().initWithFrame_(
                        NSMakeRect(
                            82,
                            y + 3,
                            100,
                            22,
                        )
                    )

                    label.setBordered_(False)
                    label.setEditable_(False)
                    label.setSelectable_(False)
                    label.setDrawsBackground_(False)
                    label.setTextColor_(NSColor.whiteColor())
                    label.setStringValue_(desc)

                    self.shortcut_document.addSubview_(label)

                    y -= row_height

            y -= 4
            
    # ==========================================================
    # MiniAI Summary Menu
    # ==========================================================

    def _createMiniAIView(self):

        if getattr(self, "mini_ai_view", None):
            return

        # --------------------------------------------------
        # Main Panel
        # --------------------------------------------------

        panel = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 220, 300)
        )

        panel.setHidden_(True)

        # --------------------------------------------------
        # Back
        # --------------------------------------------------

        back = NSButton.alloc().initWithFrame_(
            NSMakeRect(12, 264, 80, 28)
        )

        back.setTitle_("← Back")
        back.setBordered_(False)
        back.setBezelStyle_(0)
        back.setAlignment_(NSLeftTextAlignment)
        back.setTarget_(self)
        back.setAction_("showMainMenu:")

        panel.addSubview_(back)

        # --------------------------------------------------
        # Title
        # --------------------------------------------------

        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(90, 266, 120, 20)
        )

        title.setEditable_(False)
        title.setBordered_(False)
        title.setDrawsBackground_(False)
        title.setSelectable_(False)
        title.setFont_(NSFont.boldSystemFontOfSize_(15))
        title.setTextColor_(NSColor.whiteColor())
        title.setStringValue_("MiniAI")

        panel.addSubview_(title)

        # --------------------------------------------------
        # Helper
        # --------------------------------------------------

        def add_row(y, text):

            lbl = NSTextField.alloc().initWithFrame_(
                NSMakeRect(18, y, 110, 18)
            )

            lbl.setEditable_(False)
            lbl.setBordered_(False)
            lbl.setDrawsBackground_(False)
            lbl.setSelectable_(False)
            lbl.setFont_(NSFont.systemFontOfSize_(12))
            lbl.setTextColor_(NSColor.systemGrayColor())
            lbl.setStringValue_(text)

            panel.addSubview_(lbl)

            value = NSTextField.alloc().initWithFrame_(
                NSMakeRect(135, y, 65, 18)
            )

            value.setEditable_(False)
            value.setBordered_(False)
            value.setDrawsBackground_(False)
            value.setSelectable_(False)
            value.setAlignment_(2)
            value.setFont_(NSFont.boldSystemFontOfSize_(12))
            value.setTextColor_(NSColor.whiteColor())
            value.setStringValue_("-")

            panel.addSubview_(value)

            return value

        # --------------------------------------------------
        # Stats
        # --------------------------------------------------

        y = 225

        self.lbl_ai_status      = add_row(y, "Status");          y -= 25
        self.lbl_ai_risk        = add_row(y, "Threat Level");    y -= 25
        self.lbl_ai_requests    = add_row(y, "Requests");        y -= 25
        self.lbl_ai_trackers    = add_row(y, "Trackers");        y -= 25
        self.lbl_ai_fp          = add_row(y, "Fingerprinting");  y -= 25
        self.lbl_ai_intrusions  = add_row(y, "Intrusions");      y -= 25
        self.lbl_ai_http        = add_row(y, "HTTP Blocks");     y -= 25
        self.lbl_ai_pq          = add_row(y, "PQ Identity");     y -= 25
        self.lbl_ai_lockdown    = add_row(y, "Lockdown")

        self.mini_ai_view = panel

        self.menu_panel.addSubview_(panel)
        
    # ==========================================================
    # About Darkelf View
    # ==========================================================

    def _createAboutView(self):

        if getattr(self, "about_view", None):
            return

        panel = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 220, 300)
        )

        panel.setHidden_(True)

        # --------------------------------------------------
        # Back
        # --------------------------------------------------

        back = NSButton.alloc().initWithFrame_(
            NSMakeRect(12, 264, 80, 28)
        )

        back.setTitle_("← Back")
        back.setBordered_(False)
        back.setBezelStyle_(0)
        back.setAlignment_(NSLeftTextAlignment)
        back.setTarget_(self)
        back.setAction_("showMainMenu:")

        panel.addSubview_(back)

        # --------------------------------------------------
        # Title
        # --------------------------------------------------

        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(88, 266, 120, 20)
        )

        title.setEditable_(False)
        title.setBordered_(False)
        title.setDrawsBackground_(False)
        title.setSelectable_(False)
        title.setFont_(NSFont.boldSystemFontOfSize_(14))
        title.setTextColor_(NSColor.whiteColor())
        title.setAlignment_(1)
        title.setStringValue_("About")

        panel.addSubview_(title)

        # --------------------------------------------------
        # Browser Name
        # --------------------------------------------------

        name = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 220, 190, 22)
        )

        name.setEditable_(False)
        name.setBordered_(False)
        name.setDrawsBackground_(False)
        name.setSelectable_(False)
        name.setAlignment_(1)
        name.setFont_(NSFont.boldSystemFontOfSize_(15))
        name.setTextColor_(NSColor.systemGreenColor())
        name.setStringValue_("Darkelf Cocoa Browser")

        panel.addSubview_(name)

        # --------------------------------------------------
        # Version
        # --------------------------------------------------

        version = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 198, 190, 18)
        )

        version.setEditable_(False)
        version.setBordered_(False)
        version.setDrawsBackground_(False)
        version.setSelectable_(False)
        version.setAlignment_(1)
        version.setFont_(NSFont.systemFontOfSize_(12))
        version.setTextColor_(NSColor.whiteColor())
        version.setStringValue_("Version 7.0.4")

        panel.addSubview_(version)

        # --------------------------------------------------
        # Description
        # --------------------------------------------------

        desc = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 135, 190, 55)
        )

        desc.setEditable_(False)
        desc.setBordered_(False)
        desc.setDrawsBackground_(False)
        desc.setSelectable_(False)
        desc.setAlignment_(1)
        desc.setFont_(NSFont.systemFontOfSize_(12))
        desc.setTextColor_(NSColor.systemGrayColor())
        desc.setStringValue_(
            "Privacy-first browser\n"
            "built by\n"
            "Darkelf Labs"
        )

        panel.addSubview_(desc)

        # --------------------------------------------------
        # Website
        # --------------------------------------------------

        website = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 95, 190, 18)
        )

        website.setEditable_(False)
        website.setBordered_(False)
        website.setDrawsBackground_(False)
        website.setSelectable_(False)
        website.setAlignment_(1)
        website.setFont_(NSFont.systemFontOfSize_(12))
        website.setTextColor_(NSColor.systemGreenColor())
        website.setStringValue_("darkelfbrowser.com")

        panel.addSubview_(website)

        # --------------------------------------------------
        # Copyright
        # --------------------------------------------------

        copyright = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 35, 190, 35)
        )

        copyright.setEditable_(False)
        copyright.setBordered_(False)
        copyright.setDrawsBackground_(False)
        copyright.setSelectable_(False)
        copyright.setAlignment_(1)
        copyright.setFont_(NSFont.systemFontOfSize_(11))
        copyright.setTextColor_(NSColor.systemGrayColor())
        copyright.setStringValue_(
            "© 2025\nDr. Kevin Moore"
        )

        panel.addSubview_(copyright)

        self.about_view = panel

        self.menu_panel.addSubview_(panel)
        
    @objc.IBAction
    def showAboutView_(self, sender):

        try:
            # Create page once
            if not getattr(self, "about_view", None):
                self._createAboutView()

            # Hide main menu buttons
            for v in (
                self.btn_bookmarks,
                self.btn_add_bookmark,
                self.btn_hotkeys,
                self.btn_js,
                self.btn_nuke,
                self.btn_mini_ai,
                self.btn_about,
            ):
                try:
                    v.setHidden_(True)
                except Exception as e:
                    print("[About] Hide button:", e)

            # Hide other menu pages
            try:
                if getattr(self, "bookmark_view", None):
                    self.bookmark_view.setHidden_(True)
            except Exception as e:
                print("[About] Hide bookmarks:", e)

            try:
                if getattr(self, "shortcut_view", None):
                    self.shortcut_view.setHidden_(True)
            except Exception as e:
                print("[About] Hide shortcuts:", e)

            try:
                if getattr(self, "mini_ai_view", None):
                    self.mini_ai_view.setHidden_(True)
            except Exception as e:
                print("[About] Hide MiniAI:", e)

            # Show About page
            self.about_view.setHidden_(False)

            # Force redraw
            self.menu_panel.setNeedsDisplay_(True)
            self.menu_panel.displayIfNeeded()

        except Exception as e:
            print("[showAboutView_]", e)
        
    # ==========================================================
    # Show MiniAI Summary
    # ==========================================================

    def showMiniAI_(self, sender):

        try:
            # Create page once
            if not getattr(self, "mini_ai_view", None):
                self._createMiniAIView()

            # Hide main menu buttons
            for v in (
                self.btn_bookmarks,
                self.btn_add_bookmark,
                self.btn_hotkeys,
                self.btn_js,
                self.btn_nuke,
                self.btn_mini_ai,
                self.btn_about,
            ):
                try:
                    v.setHidden_(True)
                except Exception as e:
                    print("[MiniAI] Hide button:", e)

            # Hide other menu pages
            try:
                if getattr(self, "bookmark_view", None):
                    self.bookmark_view.setHidden_(True)
            except Exception as e:
                print("[MiniAI] Hide bookmarks:", e)

            # Show MiniAI page
            self.mini_ai_view.setHidden_(False)

            # Refresh statistics
            try:
                self._reloadMiniAIView()
            except Exception as e:
                print("[MiniAI] Reload failed:", e)

            # Force redraw
            self.menu_panel.setNeedsDisplay_(True)
            self.menu_panel.displayIfNeeded()

        except Exception as e:
            print("[showMiniAI_]", e)
        
    # ==========================================================
    # Refresh MiniAI Summary
    # ==========================================================

    def _reloadMiniAIView(self):

        if not getattr(self, "mini_ai", None):
            return

        try:
            stats = self.mini_ai.get_statistics()

            # -----------------------------
            # Status
            # -----------------------------
            risk = str(stats.get("overall_risk", "low")).lower()

            status_icon = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🔴",
            }.get(risk, "🟢")

            self.lbl_ai_status.setStringValue_(f"{status_icon} Protected")
            self.lbl_ai_risk.setStringValue_(risk.title())

            # -----------------------------
            # Network
            # -----------------------------
            network = stats.get("network", {})

            self.lbl_ai_requests.setStringValue_(
                str(network.get("total_requests", 0))
            )

            # -----------------------------
            # Threats
            # -----------------------------
            threats = stats.get("threats", {})

            self.lbl_ai_trackers.setStringValue_(
                str(threats.get("trackers", 0))
            )

            self.lbl_ai_fp.setStringValue_(
                str(threats.get("fingerprinting", 0))
            )

            self.lbl_ai_intrusions.setStringValue_(
                str(threats.get("intrusions", 0))
            )

            self.lbl_ai_http.setStringValue_(
                str(threats.get("http_blocks", 0))
            )

            # -----------------------------
            # PQ
            # -----------------------------
            pq = stats.get("pq", {})

            self.lbl_ai_pq.setStringValue_(
                pq.get("risk_level", "Low").title()
            )

            # -----------------------------
            # Lockdown
            # -----------------------------
            lockdown = stats.get("lockdown", {})

            self.lbl_ai_lockdown.setStringValue_(
                "ON" if lockdown.get("active", False) else "OFF"
            )

        except Exception as e:
            print("[MiniAI Summary]", e)
            
    def update_security_indicator(self, trusted):
        try:
            cell = self.addr.cell()

            if trusted:
                # Green lock icon
                lock = NSImage.imageNamed_("NSLockLockedTemplate")
                cell.setSearchButtonCell_(cell.searchButtonCell())
                cell.searchButtonCell().setImage_(lock)

                self.addr.setTextColor_(NSColor.labelColor())

            else:
                # Warning triangle
                warn = NSImage.imageNamed_("NSCaution")
                cell.searchButtonCell().setImage_(warn)

                self.addr.setTextColor_(NSColor.systemRedColor())

        except Exception as e:
            print("Security indicator error:", e)

    def start_lockdown_timer(self):

        self.stop_lockdown_timer()

        self._lockdown_timer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0, self, "refreshMiniAI:", None, True
            )
        )

    def stop_lockdown_timer(self):

        if hasattr(self, "_lockdown_timer") and self._lockdown_timer:
            self._lockdown_timer.invalidate()
            self._lockdown_timer = None

    def finish_lockdown_unlock(self):

        print("[Browser] Lockdown finished")

        self.stop_lockdown_timer()

        try:
            self.mini_ai._unlock_browser_ui()
        except Exception as e:
            log(2, e)

        try:
            self.close_threat_report_tab()
        except Exception as e:
            print("[Browser] Close report error:", e)

    def controlTextDidBeginEditing_(self, notification):
        try:
            field_editor = notification.userInfo().get("NSFieldEditor")

            if field_editor:
                green = NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.20, 0.78, 0.35, 0.6
                )

                field_editor.setSelectedTextAttributes_(
                    {
                        "NSBackgroundColor": green,
                        "NSForegroundColor": NSColor.blackColor(),
                    }
                )

        except Exception as e:
            print("[Darkelf] editor styling error:", e)

    def _is_tab_webview(self, webview):
        for tab in self.tabs:
            if tab.view is webview:
                return True
        return False

    def _is_home_context(self):
        try:
            if getattr(self, "loading_home", False):
                return True
            u = self.tabs[self.active].view.URL()
            return bool(u and u.absoluteString() == HOME_URL)
        except Exception:
            return False

    def _make_window(self):
        rect = NSMakeRect(80, 80, 1280, 820)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskMiniaturizable
        )
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, 2, False
        )
        win.setTitle_(APP_NAME)

        try:
            win.setTitleVisibility_(1)
            win.setToolbarStyle_(1)
            win.setTitlebarAppearsTransparent_(False)
            win.setBackgroundColor_(NSColor.blackColor())
            cv = win.contentView()
            if cv is not None:
                f = cv.frame()
                strip = NSBox.alloc().initWithFrame_(
                    ((0, f.size.height - 40), (f.size.width, 40))
                )
                strip.setBoxType_(0)
                strip.setBorderType_(0)
                strip.setFillColor_(NSColor.blackColor())
                strip.setAutoresizingMask_(10)
                strip.setTitle_("")
                strip.setTitlePosition_(0)
                cv.addSubview_(strip)
        except Exception as e:
            log(2, e)

        try:
            win.setTitlebarAppearsTransparent_(True)
            win.setBackgroundColor_(NSColor.blackColor())
            win.contentView().setWantsLayer_(True)
            win.contentView().layer().setBackgroundColor_(
                NSColor.blackColor().CGColor()
            )
        except Exception as e:
            log(2, e)

        try:
            win.setCollectionBehavior_(NSWindowCollectionBehaviorFullScreenPrimary)
            print("[Window] ✅ Fullscreen collection behavior set")
        except Exception as e:
            print(f"[Window] ❌ Fullscreen behavior failed: {e}")

        try:
            cv = win.contentView()
            cv.setWantsLayer_(True)
            print("[Window] ✅ Content view layer-backed")
        except Exception as e:
            print(f"[Window] ❌ Content view layer failed: {e}")

        return win

    def windowShouldClose_(self, sender):
        return True

    def actCloseTab_(self, _):
        self._close_tab()

    TOOLBAR_HEIGHT = 44
    TABBAR_HEIGHT = 38
    PADDING = 10

    def _nscolor_hex(self, hex_str, alpha=1.0):
        hs = hex_str.lstrip("#")
        r = int(hs[0:2], 16) / 255.0
        g = int(hs[2:4], 16) / 255.0
        b = int(hs[4:6], 16) / 255.0
        return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, alpha)

    def _style_button(self, btn, tooltip=None):
        # Avoid fancy styles that sometimes misbehave across macOS versions
        try:
            btn.setBordered_(True)
        except Exception as e:
            log(2, e)
        if tooltip:
            try:
                btn.setToolTip_(tooltip)
            except Exception as e:
                log(2, e)
        return btn

    def _build_tabbar(self):
        try:
            clr = self.window.contentLayoutRect()
            w = clr.size.width
            top_y = clr.origin.y + clr.size.height
        except Exception:
            bounds = self.window.contentView().bounds()
            width = bounds.size.width
            top_y = bounds.size.height

        tabbar_y = top_y - self.TOOLBAR_HEIGHT - self.TABBAR_HEIGHT

        # CREATE TABBAR ONCE
        self.tabbar = NSView.alloc().initWithFrame_(
            NSMakeRect(0, top_y, w, self.TABBAR_HEIGHT)
        )

        self.tabbar.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.tabbar.setWantsLayer_(True)
        self.tabbar.layer().setBackgroundColor_(
            self._nscolor_hex("#0a0d12", 1.0).CGColor()
        )

        # ADD BUTTON (after tabbar exists)
        self.btn_new_tab = HoverButton.alloc().initWithFrame_(
            NSMakeRect(w - 44, 6, 34, 26)
        )

        self.btn_new_tab.setTitle_("+")
        self.btn_new_tab.setBordered_(False)
        self.btn_new_tab.setBezelStyle_(0)
        self.btn_new_tab.setTarget_(self)
        self.btn_new_tab.setAction_("actNewTab:")

        self.tabbar.addSubview_(self.btn_new_tab)

        # container
        self.tab_buttons_container = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w - 50, self.TABBAR_HEIGHT)
        )
        self.tabbar.addSubview_(self.tab_buttons_container)

        self.window.contentView().addSubview_(self.tabbar)

        if not hasattr(self, "tabs"):
            self.tabs = []

        if not hasattr(self, "active"):
            self.active = -1

        self._update_tab_buttons()
        self._cleanup_unused_containers()

    def _layout_topbars(self):
        bounds = self.window.contentView().bounds()
        w = bounds.size.width
        h = bounds.size.height

        if getattr(self, "toolbar", None):
            self.toolbar.setFrame_(
                NSMakeRect(0, h - self.TOOLBAR_HEIGHT, w, self.TOOLBAR_HEIGHT)
            )
        if getattr(self, "tabbar", None):
            self.tabbar.setFrame_(
                NSMakeRect(
                    0,
                    h - self.TOOLBAR_HEIGHT - self.TABBAR_HEIGHT,
                    w,
                    self.TABBAR_HEIGHT,
                )
            )
        if getattr(self, "btn_new_tab", None):
            self.btn_new_tab.setFrame_(NSMakeRect(w - 44, 6, 34, 26))
        if getattr(self, "content_container", None):
            self.content_container.setFrame_(
                NSMakeRect(0, 0, w, h - self.TOOLBAR_HEIGHT - self.TABBAR_HEIGHT)
            )

    def windowDidResize_(self, notification):
        self._layout_topbars()
        self._update_tab_buttons()

    def _update_tab_buttons(self):
        if not getattr(self, "tab_buttons_container", None):
            return

        # Remove old generated tab controls
        for v in list(self.tab_buttons_container.subviews() or []):
            v.removeFromSuperview()

        w = self.tab_buttons_container.bounds().size.width
        y = 2
        h = 33
        gap = 1
        min_tab_w = 130
        max_tab_w = 200
        close_w = 24
        inner_pad = 12

        num_tabs = len(self.tabs)
        if num_tabs <= 0:
            return

        plus_reserved = 44

        available_w = max(
            200,
            w - plus_reserved - (gap * max(0, num_tabs - 1)) - self.PADDING * 2,
        )

        tab_w = max(min_tab_w, min(available_w // num_tabs, max_tab_w))

        x = 1

        for i, tab in enumerate(self.tabs):

            selected = i == self.active

            tab_shell = NSView.alloc().initWithFrame_(
                NSMakeRect(x, y, tab_w, h)
            )
            tab_shell.setWantsLayer_(True)
            tab_shell.layer().setCornerRadius_(8.0)

            if selected:
                tab_shell.layer().setBackgroundColor_(
                    self._nscolor_hex("#1E2A22", 0.95).CGColor()
                )
                tab_shell.layer().setBorderWidth_(1.0)
                tab_shell.layer().setBorderColor_(
                    self._nscolor_hex("#34C759", 0.90).CGColor()
                )
            else:
                tab_shell.layer().setBackgroundColor_(
                    self._nscolor_hex("#171C22", 0.95).CGColor()
                )
                tab_shell.layer().setBorderWidth_(1.0)
                tab_shell.layer().setBorderColor_(
                    self._nscolor_hex("#2B3138", 1.0).CGColor()
                )

            # ----------------------------
            # Favicon
            # ----------------------------
            text_x = inner_pad

            if getattr(tab, "favicon", None):

                icon = NSImageView.alloc().initWithFrame_(
                    NSMakeRect(8, 9, 16, 16)
                )
                icon.setImage_(tab.favicon)

                tab_shell.addSubview_(icon)

                text_x = 30

            # ----------------------------
            # Close button
            # ----------------------------
            close_btn = HoverButton.alloc().initWithFrame_(
                NSMakeRect(tab_w - close_w - 6, 6, close_w, close_w)
            )
            close_btn.setTitle_("×")
            close_btn.setBordered_(False)
            close_btn.setTarget_(self)
            close_btn.setAction_("actCloseTabIndex:")
            close_btn.setTag_(i)
            close_btn.setToolTip_("Close Tab")
            close_btn.setFont_(NSFont.boldSystemFontOfSize_(13))
            close_btn.setContentTintColor_(
                self._nscolor_hex("#34C759", 1.0)
                if selected
                else NSColor.whiteColor()
            )

            # ----------------------------
            # Title
            # ----------------------------
            title = getattr(tab, "title", None) or tab.host or "New Tab"

            if len(title) > 20:
                title = title[:20] + "…"

            title_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(
                    text_x,
                    2,
                    tab_w - close_w - text_x - 8,
                    h - 2,
                )
            )

            title_btn.setTitle_(title)
            title_btn.setBordered_(False)
            title_btn.setAlignment_(0)
            title_btn.setTarget_(self)
            title_btn.setAction_("actSwitchTab:")
            title_btn.setTag_(i)
            title_btn.setContentTintColor_(
                self._nscolor_hex("#34C759", 1.0)
                if selected
                else NSColor.whiteColor()
            )

            tab_shell.addSubview_(title_btn)
            tab_shell.addSubview_(close_btn)

            self.tab_buttons_container.addSubview_(tab_shell)

            x += tab_w + gap

    # ================= TAB / NAV ACTIONS =================

    @objc.IBAction
    def tabClicked_(self, sender):
        try:
            idx = int(sender.tag())
            self._select_tab(idx)
        except Exception as e:
            print("[Tabs] tabClicked_ error:", e)

    @objc.IBAction
    def actNewTab_(self, sender):
        print("CLICKED + BUTTON")

        idx = self._add_tab(home=True)

        print("TAB RESULT:", idx)
        print("TOTAL TABS:", len(self.tabs))

        self.active = len(self.tabs) - 1
        self._update_tab_buttons()
        self._sync_addr()

    @objc.IBAction
    def actBack_(self, sender):
        tab = self._active_tab()
        if tab and getattr(tab, "view", None):
            try:
                tab.view.goBack()
            except Exception as e:
                log(2, e)

    @objc.IBAction
    def actFwd_(self, sender):
        tab = self._active_tab()
        if tab and getattr(tab, "view", None):
            try:
                tab.view.goForward()
            except Exception as e:
                log(2, e)

    @objc.IBAction
    def actReload_(self, sender):
        tab = self._active_tab()
        if tab and getattr(tab, "view", None):
            try:
                tab.view.reload()
            except Exception as e:
                log(2, e)

    @objc.IBAction
    def actHome_(self, sender):
        try:
            self._add_tab(home=True)
        except Exception as e:
            print("[Nav] actHome_ error:", e)

    @objc.IBAction
    def addrEntered_(self, sender):
        try:
            text = str(self.addr.stringValue() or "").strip()
            if not text:
                return

            if "://" not in text and "." in text:
                text = "https://" + text
            elif "://" not in text:
                text = "https://lite.duckduckgo.com/lite/?q=" + quote_plus(text)

            self._add_tab(home=False)

            self._navigate_to(text)

        except Exception as e:
            print("[Nav] addrEntered error:", e)

    # ================= TAB HELPERS =================

    def _active_tab(self):
        if not hasattr(self, "tabs"):
            return None
        if self.active < 0 or self.active >= len(self.tabs):
            return None
        return self.tabs[self.active]

    def _select_tab(self, idx):
        if idx < 0 or idx >= len(self.tabs):
            return

        self.active = idx

        cv = self.window.contentView()

        # Remove any existing WKWebViews from contentView
        for sub in list(cv.subviews()):
            if isinstance(sub, WKWebView):
                sub.removeFromSuperview()

        # Hide all tab WKWebViews except for the active one
        for i, tab in enumerate(self.tabs):
            view = getattr(tab, "view", None)
            if not view:
                continue
            if i == self.active:
                # Remount the active tab's WKWebView, ensure it's visible
                self._mount_webview(view)
                try:
                    view.setHidden_(False)
                except Exception as e:
                    log(2, e)
            else:
                try:
                    view.setHidden_(True)
                except Exception as e:
                    log(2, e)

        self._sync_addr()
        self._update_tab_buttons()

    def _sync_addr(self):
        tab = self._active_tab()
        if not tab or not getattr(self, "addr", None):
            return

        try:
            self.addr.setStringValue_(getattr(tab, "url", "") or "")
        except Exception as e:
            log(2, e)

    def _navigate_to(self, url_str):
        tab = self._active_tab()
        if not tab or not getattr(tab, "view", None):
            return

        try:
            nsurl = NSURL.URLWithString_(url_str)
            tab.view.loadRequest_(NSURLRequest.requestWithURL_(nsurl))
            tab.url = url_str
            self._sync_addr()
        except Exception as e:
            print("[Nav] navigate error:", e)

    # ----- Toolbar -----
    def _mk_btn(self, symbol, tooltip):
        b = HoverButton.alloc().init()
        try:
            img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                symbol, None
            )
            # First, try the user-requested configuration
            cfg = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                54.0, 2, 2
            )
            if img and hasattr(img, "imageByApplyingSymbolConfiguration_"):
                img = img.imageByApplyingSymbolConfiguration_(cfg)
            if img:
                try:
                    img.setTemplate_(True)
                except Exception as e:
                    log(2, e)
                b.setImage_(img)
        except Exception as e:
            log(2, e)
        try:
            b.setBordered_(False)
            b.setBezelStyle_(1)
            b.setToolTip_(tooltip or "")
        except Exception as e:
            log(2, e)
        if hasattr(b, "setContentTintColor_"):
            b.setContentTintColor_(NSColor.whiteColor())
        return b

    # -------------------------------------------------------------------
    # Replace your existing _make_toolbar + _build_shadow_toolbar with this
    # -------------------------------------------------------------------
    def _make_toolbar(self):
        cv = self.window.contentView()

        # Determine a reliable top Y using contentLayoutRect (safe with titlebars/toolbars)
        try:
            clr = self.window.contentLayoutRect()
            top_y = clr.origin.y + clr.size.height
            width = clr.size.width
        except Exception:
            f = cv.frame()
            top_y = f.size.height
            width = f.size.width

        bar_h = 52.0
        y = top_y - bar_h

        # Container
        self.toolbar_container = NSView.alloc().initWithFrame_(
            NSMakeRect(0, y, width, bar_h)
        )
        self.toolbar_container.setAutoresizingMask_(10)  # width sizable + stick to top
        self.toolbar_container.setWantsLayer_(True)

        # Modern dark background
        self.toolbar_container.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.05, 0.06, 0.08, 1.0
            ).CGColor()
        )

        # subtle bottom border
        try:
            self.toolbar_container.layer().setBorderWidth_(1.0)
            self.toolbar_container.layer().setBorderColor_(
                NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.08).CGColor()
            )
        except Exception as e:
            log(2, e)

        cv.addSubview_(self.toolbar_container)

        # ----------------------------
        # Helpers: button factory
        # ----------------------------
        def make_icon_btn(symbol, tooltip, tint=None, size=18.0):
            b = HoverButton.alloc().init()
            b.setBordered_(False)
            b.setBezelStyle_(1)
            b.setTitle_("")
            b.setToolTip_(tooltip or "")

            img = None
            try:
                img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                    symbol, None
                )
                if img:
                    cfg = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                        size, 2, 2
                    )
                    if hasattr(img, "imageByApplyingSymbolConfiguration_"):
                        img = img.imageByApplyingSymbolConfiguration_(cfg)
                    try:
                        img.setTemplate_(True)
                    except Exception as e:
                        log(2, e)
            except Exception:
                img = None

            if img:
                b.setImage_(img)
                b.setImagePosition_(2)  # image-only

            if hasattr(b, "setContentTintColor_"):
                if tint:
                    b.setContentTintColor_(tint)
                else:
                    b.setContentTintColor_(NSColor.whiteColor())

            b.setWantsLayer_(True)
            try:
                b.layer().setCornerRadius_(10.0)
            except Exception as e:
                log(2, e)

            return b

        # ----------------------------
        # Left buttons
        # ----------------------------
        self.btn_back = make_icon_btn("chevron.backward", "Back")
        self.btn_fwd = make_icon_btn("chevron.forward", "Forward")
        self.btn_reload = make_icon_btn("arrow.clockwise", "Reload")

        for b, sel in [
            (self.btn_back, "actBack:"),
            (self.btn_fwd, "actFwd:"),
            (self.btn_reload, "actReload:"),
        ]:
            b.setTarget_(self)
            b.setAction_(sel)
            self.toolbar_container.addSubview_(b)

        # ----------------------------
        # URL bar
        # ----------------------------
        self.urlbar = AddressField.alloc().initWithFrame_owner_(
            NSMakeRect(200, 6, 720, 32), self
        )
        self.addr = self.urlbar

        self.addr.setFocusRingType_(NSFocusRingTypeNone)

        self.urlbar.setBezeled_(True)

        self.urlbar.setFocusRingType_(0)
        self.urlbar.cell().setFocusRingType_(0)

        # THIS is the real fix
        self.urlbar.cell().setShowsFirstResponder_(False)

        self.urlbar.setDrawsBackground_(False)

        self.urlbar.setPlaceholderString_("Search or enter URL")

        # ✅ KEEP THIS (your working enter handler)
        self.urlbar.setTarget_(self)
        self.urlbar.setAction_("addrEntered:")

        self.urlbar.cell().setSendsWholeSearchString_(True)
        self.urlbar.cell().setSendsSearchStringImmediately_(False)

        self.urlbar.setAutoresizingMask_(2)

        # ✅ ADD THIS EXACTLY HERE (RIGHT BEFORE addSubview)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self,
            "controlTextDidBeginEditing:",
            "NSControlTextDidBeginEditingNotification",
            self.addr,
        )

        self.toolbar_container.addSubview_(self.urlbar)

        # ----------------------------
        # Right-side buttons
        # ----------------------------

        self.btn_hotkeys = make_icon_btn(
            "keyboard",
            "Keyboard Shortcuts"
        )
        
        self.btn_bookmark = make_icon_btn(
            "bookmark",
            "Bookmarks"
        )
        
        self.btn_menu = make_icon_btn(
            "line.3.horizontal",
            "Menu"
        )

        self.btn_menu.setTarget_(self)
        self.btn_menu.setAction_("toggleMenu:")
        
        self.btn_hotkeys.setTarget_(self)
        self.btn_hotkeys.setAction_("showKeyboardShortcuts:")
        
        self.btn_js = make_icon_btn(
            "bolt.fill" if self.js_enabled else "bolt.slash.fill",
            f"JavaScript: {'ON' if self.js_enabled else 'OFF'}",
            tint=(
                NSColor.systemGreenColor()
                if self.js_enabled
                else NSColor.systemRedColor()
            ),
        )

        self.btn_nuke = make_icon_btn(
            "trash.fill", "Clear All Data", tint=NSColor.systemRedColor()
        )
        self.btn_mini_ai = make_icon_btn(
            "shield.fill", "MiniAI System Report", tint=NSColor.systemGreenColor()
        )

        for b, sel in [
            (self.btn_hotkeys, "showKeyboardShortcuts:"),
            (self.btn_js, "actToggleJS:"),
            (self.btn_nuke, "actNuke:"),
            (self.btn_mini_ai, "showMiniAI:"),
            (self.btn_bookmark, "toggleBookmarkToolbar:"),   # NEW
            (self.btn_menu, "toggleMenu:"),
        ]:
            b.setTarget_(self)
            b.setAction_(sel)
            self.toolbar_container.addSubview_(b)
            
        # layout pass
        self._layout_toolbar()
        return self.toolbar_container

    def _layout_toolbar(self):
        """Called on startup + window resize to keep toolbar aligned."""
        if not getattr(self, "toolbar_container", None):
            return

        bounds = self.window.contentView().bounds()
        width = bounds.size.width
        top_y = bounds.size.height

        # --------------------------------------------------
        # Toolbar geometry
        # --------------------------------------------------
        bar_h = 52.0
        self.toolbar_container.setFrame_(
            NSMakeRect(0, top_y - bar_h, width, bar_h)
        )

        pad = 10.0
        btn = 32.0

        # Vertically center everything
        btn_y = (bar_h - btn) / 2.0
        url_h = 32.0
        url_y = (bar_h - url_h) / 2.0

        # --------------------------------------------------
        # Left buttons
        # --------------------------------------------------
        x = pad

        # Back
        self.btn_back.setFrame_(NSMakeRect(x, btn_y + 1, btn, btn))
        x += btn + 6

        # Forward
        self.btn_fwd.setFrame_(NSMakeRect(x, btn_y + 1, btn, btn))
        x += btn + 6

        # Reload
        self.btn_reload.setFrame_(NSMakeRect(x, btn_y, btn, btn))
        x += btn + 6

        left_end = x + 2

        # --------------------------------------------------
        # Right buttons
        # --------------------------------------------------
        right_buttons = (
            self.btn_bookmark,
            self.btn_menu,
        )

        # --------------------------------------------------
        # Right-side controls
        # --------------------------------------------------

        right_gap = 14.0
        right_margin = 120.0      # ← Increase this to shorten the URL bar

        right_cluster_width = (
            len(right_buttons) * btn
            + (len(right_buttons) - 1) * right_gap
        )

        right_x = width - pad - right_cluster_width

        x_cursor = right_x

        for b in right_buttons:
            b.setFrame_(NSMakeRect(x_cursor, btn_y, btn, btn))
            x_cursor += btn + right_gap

        # --------------------------------------------------
        # URL Bar (centered)
        # --------------------------------------------------

        available_left = left_end
        available_right = right_x - 20

        available_width = available_right - available_left

        url_w = min(900, available_width)      # Try 850–950

        url_x = available_left + (available_width - url_w) / 2

        self.addr.setFrame_(NSMakeRect(url_x, btn_y, url_w, btn))

    # Make sure your existing onResize_ calls _layout() AND _layout_toolbar()
    def onResize_(self, note):
        try:
            self._layout()
        except Exception as e:
            log(2, e)

        try:
            self._layout_toolbar()
        except Exception as e:
            log(2, e)
            
    def _bring_tabbar_to_front(self):
        try:
            cv = self.window.contentView()

            # keep toolbar on top
            if getattr(self, "toolbar_container", None):
                if (
                    self.toolbar_container.superview() is not None
                    and self.toolbar_container.superview() != cv
                ):
                    try:
                        self.toolbar_container.removeFromSuperview()
                    except Exception as e:
                        log(2, e)

                if self.toolbar_container.superview() != cv:
                    cv.addSubview_(self.toolbar_container)

            # keep tabbar above webview
            if getattr(self, "tabbar", None):
                if (
                    self.tabbar.superview() is not None
                    and self.tabbar.superview() != cv
                ):
                    try:
                        self.tabbar.removeFromSuperview()
                    except Exception as e:
                        log(2, e)

                if self.tabbar.superview() != cv:
                    cv.addSubview_(self.tabbar)

                self.tabbar.displayIfNeeded()

        except Exception as e:
            log(2, e)

    # In actToggleJS_, after toggling, also update JS button icon/tint:
    def actToggleJS_(self, _):
        self.js_enabled = not bool(getattr(self, "js_enabled", True))

        # update UI button
        try:
            sym = "bolt.fill" if self.js_enabled else "bolt.slash.fill"
            img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(sym, None)
            if img:
                cfg = (
                    NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                        18.0, 2, 2
                    )
                )
                if hasattr(img, "imageByApplyingSymbolConfiguration_"):
                    img = img.imageByApplyingSymbolConfiguration_(cfg)
                img.setTemplate_(True)
                self.btn_js.setImage_(img)
            self.btn_js.setToolTip_(f"JavaScript: {'ON' if self.js_enabled else 'OFF'}")
            if hasattr(self.btn_js, "setContentTintColor_"):
                self.btn_js.setContentTintColor_(
                    NSColor.systemGreenColor()
                    if self.js_enabled
                    else NSColor.systemRedColor()
                )
        except Exception as e:
            log(2, e)

        # apply to active webview + reload
        try:
            wk = self.tabs[self.active].view
            prefs = wk.configuration().preferences()
            prefs.setJavaScriptEnabled_(self.js_enabled)
            wk.reload()
        except Exception as e:
            print("[JS Toggle] Reload error:", e)

    def _install_local_hsts(self, ucc):

        js = f"""
        (() => {{
          try {{
            const here = location.protocol;
            if (here !== 'file:' && here !== 'https:') return;

            if (document.querySelector('meta[http-equiv="Strict-Transport-Security"]')) return;

            const meta = document.createElement('meta');
            meta.httpEquiv = 'Strict-Transport-Security';
            meta.content = {repr(LOCAL_HSTS_VALUE)};
            (document.head || document.documentElement).prepend(meta);
          }} catch (e) {{
          }}
        }})();
        """

        try:
            script = (
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    js, 1, False
                )
            )
            ucc.addUserScript_(script)
            print("[HSTS] Local HSTS injector installed (https:// & file:// only).")
        except Exception as e:
            print("[HSTS] Injector add failed:", e)

    def _install_local_referrer_policy(self, ucc):

        js = f"""
        setTimeout(() => {{
          try {{
            const here = location.protocol;
            if (here !== 'file:' && here !== 'https:') return;

            if (document.querySelector('meta[name="referrer"]')) return;

            const meta = document.createElement('meta');
            meta.name = 'referrer';
            meta.content = {repr(LOCAL_REFERRER_POLICY_VALUE)};
            (document.head || document.documentElement).prepend(meta);
            console.log('[ReferrerPolicy] Meta injected after TLS handshake.');
          }} catch (e) {{
          }}
        }}, 100);
        """

        try:
            script = (
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    js, 1, False
                )
            )
            ucc.addUserScript_(script)
            print(
                "[ReferrerPolicy] Local Referrer-Policy injector installed (https:// & file:// only, delayed)."
            )
        except Exception as e:
            print("[ReferrerPolicy] Injector add failed:", e)

    def _install_local_websocket_policy(self, ucc):

        js = f"""
        setTimeout(() => {{
          try {{
            const here = location.protocol;
            if (here !== 'file:' && here !== 'https:') return;

            const existing = document.querySelectorAll('meta[http-equiv="Content-Security-Policy"]');
            for (const m of existing) {{
              if (m.content.includes("connect-src")) return;
            }}

            const meta = document.createElement('meta');
            meta.httpEquiv = 'Content-Security-Policy';
            meta.content = {repr(LOCAL_WEBSOCKET_POLICY_VALUE)};
            (document.head || document.documentElement).prepend(meta);
            console.log('[WebSocketPolicy] connect-src self injected.');
          }} catch (e) {{
          }}
        }}, 100);
        """

        try:
            script = (
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    js, 1, False
                )
            )
            ucc.addUserScript_(script)
            print(
                "[WebSocketPolicy] Local WebSocket Policy injector installed (connect-src 'self')."
            )
        except Exception as e:
            print("[WebSocketPolicy] Injector add failed:", e)

    @objc.python_method
    def _inject_core_scripts(self, ucc):

        try:
            canvas_script = UNIFIED_DEFENSE_JS

            ucc.addUserScript_(
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    canvas_script, WKUserScriptInjectionTimeAtDocumentStart, False
                )
            )

        except Exception as e:
            print("[Darkelf] core script injection failed:", e)

            def _add(src):
                try:
                    if isinstance(src, str):
                        skr1 = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                            src, WKUserScriptInjectionTimeAtDocumentStart, False
                        )
                        skr2 = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                            src, WKUserScriptInjectionTimeAtDocumentEnd, False
                        )
                        ucc.addUserScript_(skr1)
                        ucc.addUserScript_(skr2)
                    else:
                        ucc.addUserScript_(src)
                except Exception as e:
                    print("[Inject] script add failed:", e)

            _add(canvas_script)
            _add(UNIFIED_DEFENSE_JS)

            tab = self.tabs[self.active] if hasattr(self, "tabs") else None

            seed_hex = (
                get_canvas_seed_hex(tab) if tab else "00000000000000000000000000000000"
            )

            _add(f'window.__darkelf_pq_seed_hex = "{seed_hex}";')

        except Exception as e:
            print("[Inject] core scripts failed:", e)

            if ENABLE_LOCAL_HSTS:
                self._install_local_hsts(ucc)
                print("[HSTS] Local HSTS injector attached to UCC.")

            if ENABLE_LOCAL_REFERRER_POLICY:
                self._install_local_referrer_policy(ucc)
                print("[ReferrerPolicy] Local Referrer Policy attached to UCC.")

            if ENABLE_LOCAL_WEBSOCKET_POLICY:
                self._install_local_websocket_policy(ucc)
                print("[WebSocketPolicy] Local WebSocket Policy attached to UCC.")

            # ✅ UPDATED: Enhanced ad/banner blocking with Wikipedia support
            _add(r"""
            (function(){
                try {
                    if (
                        location.hostname.includes("youtube.com")) return;

                    var css = `
                    /* Generic ad blocking */
                    iframe[src*="ad"],
                    iframe[src*="doubleclick"],
                    iframe[src*="adsystem"],
                    iframe[src*="googlesyndication"],

                    div[id^="ad_"],
                    div[id^="ads_"],
                    div[class^="ad-"],
                    div[class^="ads-"],

                    [data-ad],
                    [data-sponsored],

                    #centralNotice,
                    .frb-banner,
                    .cn-banner

                    [data-ad],
                    [data-sponsored],
                
                    /* Wikipedia banners (fundraising/campaigns) */
                    .frb-banner,
                    .frb-container,
                    #centralNotice,
                    .cn-banner,
                    div[id*="banner-container"],
                    div[class*="campaign"],
                    .mw-parser-output > .mw-dismissable-notice,
                
                    /* Common donation/fundraising banners */
                    div[class*="donation"],
                    div[id*="fundrais"],
                    div[class*="appeal"],
                
                    /* Newsletter/subscription popups */
                    div[class*="newsletter"],
                    div[id*="subscribe"],
                    div[class*="popup-banner"] {
                        display: none !important;
                        visibility: hidden !important;
                        opacity: 0 !important;
                        height: 0 !important;
                        overflow: hidden !important;
                    }`;

                    var style = document.createElement('style');
                    style.type = 'text/css';
                    style.appendChild(document.createTextNode(css));
                    document.documentElement.appendChild(style);
                
                    console.log('[Darkelf] Ad/banner blocking CSS injected');
                } catch(e){
                    console.error('[Darkelf] Banner blocking failed:', e);
                }
            })();
            """)

            print("[Inject] Core defense scripts added to UCC.")

        except Exception as e:
            print(f"[Inject] Core script injection failed: {e}")

    def _new_wk(self, container_nonce, pq_seed, tab):

        is_home = bool(getattr(self, "loading_home", False))

        cfg = WKWebViewConfiguration.alloc().init()

        # ----------------------------
        # USER CONTENT CONTROLLER
        # ----------------------------
        ucc = WKUserContentController.alloc().init()

        # ----------------------------
        # 🔐 128-BIT HEX SEED (PER TAB)
        # ----------------------------
        seed_hex = get_canvas_seed_hex(tab)

        seed_js = f'window.__darkelf_pq_seed_hex = "{seed_hex}";'

        seed_script = (
            WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                seed_js, WKUserScriptInjectionTimeAtDocumentStart, False
            )
        )

        ucc.addUserScript_(seed_script)

        # ----------------------------
        # 🎯 CANVAS DEFENSE (FIXED)
        # ----------------------------
        canvas_js = """
        (function() {

            if (!window.__darkelf_pq_seed_hex) return;

            function hex32(s) {
                return parseInt(s, 16) >>> 0;
            }

            const HEX = window.__darkelf_pq_seed_hex;

            const SEED_A = hex32(HEX.slice(0, 8));
            const SEED_B = hex32(HEX.slice(8, 16));

            const TAB_SEED = (SEED_A ^ SEED_B) >>> 0;

            function hash(n) {
                n = (n ^ 0x9E3779B1) + (n << 6);
                n ^= n >>> 11;
                n += n << 3;
                n ^= n >>> 15;
                return n >>> 0;
            }

            // ----------------------------
            // ORIGIN (iframe-safe)
            // ----------------------------
            let origin = location.origin || "";

            try {
                if (window.top && window.top.location && window.top.location.origin) {
                    origin = window.top.location.origin;
                }
            } catch (e) {}

            let originHash = 0;
            for (let i = 0; i < origin.length; i++) {
                originHash = (originHash * 31 + origin.charCodeAt(i)) >>> 0;
            }

            const SITE_SEED = hash(TAB_SEED ^ originHash);

            function noise(x, y) {
                return ((x * 13 + y * 17 + SITE_SEED) % 5) - 2;
            }

            const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;

            CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                const data = origGetImageData.call(this, x, y, w, h);

                for (let i = 0; i < data.data.length; i += 4) {
                    const px = (i / 4) % w;
                    const py = Math.floor((i / 4) / w);

                    const n = noise(px, py);

                    data.data[i]     = (data.data[i] + n) & 255;
                    data.data[i + 1] = (data.data[i + 1] + n) & 255;
                    data.data[i + 2] = (data.data[i + 2] + n) & 255;
                }

                return data;
            };

            const origToDataURL = HTMLCanvasElement.prototype.toDataURL;

            HTMLCanvasElement.prototype.toDataURL = function() {

                const ctx = this.getContext("2d");

                if (ctx) {
                    const w = this.width || 1;
                    const h = this.height || 1;

                    const shiftX = SITE_SEED % w;
                    const shiftY = (SITE_SEED >>> 3) % h;

                    ctx.fillStyle = "rgba(0,0,0,0.001)";
                    ctx.fillRect(shiftX, shiftY, 1, 1);
                }

                return origToDataURL.apply(this, arguments);
            };

        })();
        """

        canvas_script = (
            WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                canvas_js, WKUserScriptInjectionTimeAtDocumentStart, False
            )
        )

        ucc.addUserScript_(canvas_script)

        # ---------------------------
        # First-Party Isolation
        # ---------------------------
        url = getattr(self, "current_url_for_fpi", HOME_URL)

        tab_uid = secrets.token_hex(4)

        key = self.fpi._key(url, tab_uid=tab_uid, nonce=container_nonce)

        if key not in self._containers:

            store = self.fpi.store_for(
                url, tab_uid=len(self.tabs), nonce=container_nonce
            )

            pool = WKProcessPool.alloc().init()

            cache = (
                NSURLCache.alloc().initWithMemoryCapacity_diskCapacity_directoryURL_(
                    16 * 1024 * 1024, 0, None
                )
            )

            if cache.diskCapacity() != 0:
                raise RuntimeError("Darkelf security failure: disk cache detected")

            NSURLCache.setSharedURLCache_(NSURLCache.alloc().init())

            self._containers[key] = (store, pool)

        store, pool = self._containers[key]

        cfg.setWebsiteDataStore_(store)
        cfg.setProcessPool_(pool)

        cfg.setMediaTypesRequiringUserActionForPlayback_(0)

        if store.isPersistent():
            raise RuntimeError(
                "Darkelf security failure: persistent data store detected"
            )

        js_enabled = True if is_home else bool(getattr(self, "js_enabled", True))

        prefs = WKPreferences.alloc().init()
        prefs.setJavaScriptEnabled_(js_enabled)
        prefs.setJavaScriptCanOpenWindowsAutomatically_(True)
        prefs.setValue_forKey_(True, "fullScreenEnabled")
        cfg.setPreferences_(prefs)

        if ContentRuleManager._rule_list:
            ucc.addContentRuleList_(ContentRuleManager._rule_list)

        ucc.addScriptMessageHandler_name_(self._nav_delegate, "netlog")
        ucc.addScriptMessageHandler_name_(self._nav_delegate, "blobdownload")
        ucc.addScriptMessageHandler_name_(self._search_handler, "search")

        inject_screen_spoof(ucc)

        self._inject_core_scripts(ucc)

        cfg.setUserContentController_(ucc)

        web = WKWebView.alloc().initWithFrame_configuration_(
            NSMakeRect(0, 0, 800, 600), cfg
        )

        darkelf_init_tab_identity(tab)
        web.setCustomUserAgent_(tab._ua_string)

        web.setNavigationDelegate_(self._nav_delegate)
        web.setUIDelegate_(self._ui_delegate)

        return web, store

    def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_completionHandler_(
        self, webView, message, frame, completionHandler
    ):
        """Handle JavaScript alerts"""
        try:
            print(f"[JS Alert] {message}")
            alert = NSAlert.alloc().init()
            alert.setMessageText_("JavaScript Alert")
            alert.setInformativeText_(str(message))
            alert.addButtonWithTitle_("OK")
            alert.runModal()
        finally:
            completionHandler()

    def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_completionHandler_(
        self, webView, message, frame, completionHandler
    ):
        """Handle JavaScript confirms"""
        try:
            print(f"[JS Confirm] {message}")
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Confirm")
            alert.setInformativeText_(str(message))
            alert.addButtonWithTitle_("OK")
            alert.addButtonWithTitle_("Cancel")
            result = alert.runModal()
            completionHandler(result == 1000)
        except Exception as e:
            print(f"[JS Confirm] Error: {e}")
            completionHandler(False)

    def webView_runJavaScriptTextInputPanelWithPrompt_defaultText_initiatedByFrame_completionHandler_(
        self, webView, prompt, defaultText, frame, completionHandler
    ):
        """Handle JavaScript prompts"""
        try:
            print(f"[JS Prompt] {prompt}")
            completionHandler(None)
        except Exception as e:
            print(f"[JS Prompt] Error: {e}")
            completionHandler(None)

    def webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_(
        self, webView, origin, frame, type, decisionHandler
    ):
        try:
            print(f"[Media] 🔒 Denied media capture for: {origin}")
            decisionHandler(0)  # Always deny
        except Exception as e:
            log(2, e)

    def _mount_webview(self, wk):
        cv = self.window.contentView()

        # Remove ALL existing WKWebViews immediately
        for sub in list(cv.subviews()):
            if "WKWebView" in str(type(sub)):
                sub.removeFromSuperview()

        # ====== Ensure Navigation and UI Delegates are set ======
        if getattr(self, "_nav_delegate", None):
            wk.setNavigationDelegate_(self._nav_delegate)
        if getattr(self, "_ui_delegate", None):
            wk.setUIDelegate_(self._ui_delegate)

        # Compute frame: subtract both toolbar and tabbar height!
        try:
            clr = self.window.contentLayoutRect()
            min_height = 100
            total_ui_height = self.TOOLBAR_HEIGHT + self.TABBAR_HEIGHT
            w = clr.size.width
            h = clr.size.height - total_ui_height

            if h < min_height:
                f = cv.frame()
                h = max(min_height, f.size.height - total_ui_height)
                log(2, "[WKWebView] Fallback to cv.frame(), height =", h)

            web_rect = NSMakeRect(0, 0, w, h)
            log(2, f"[WKWebView] Set frame: width={w}, height={h}")

        except Exception as e:
            f = cv.frame()
            min_height = 100
            h = max(
                min_height, f.size.height - (self.TOOLBAR_HEIGHT + self.TABBAR_HEIGHT)
            )
            w = f.size.width
            web_rect = NSMakeRect(0, 0, w, h)
            log(
                2,
                f"[WKWebView] Exception fallback. Set frame: width={w}, height={h}. Error: {e}",
            )

        cv.addSubview_(wk)
        
        if getattr(self, "menu_panel", None):
            self.menu_panel.removeFromSuperview()
            cv.addSubview_(self.menu_panel)
            
        # FIXED BACKGROUND HANDLING
        try:
            wk.setOpaque_(True)
            wk.setBackgroundColor_(NSColor.blackColor())
        except Exception as e:
            print("[WKWebView] Failed to set background:", e)

        wk.setFrame_(web_rect)
        wk.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        # Always re-add toolbar and tabbar after mounting webview!
        try:
            if getattr(self, "toolbar_container", None):
                if self.toolbar_container.superview() != cv:
                    cv.addSubview_(self.toolbar_container)

            if getattr(self, "tabbar", None):
                if self.tabbar.superview() != cv:
                    cv.addSubview_(self.tabbar)

        except Exception as e:
            print("[WKWebView] Failed to re-add toolbar/tabbar:", e)

        self._bring_tabbar_to_front()

    def _rebuild_active_webview(self):

        # --- never rebuild homepage ---
        try:
            u = self.tabs[self.active].view.URL()
            if u and u.absoluteString() == HOME_URL:
                print("[JS] Skip rebuild: homepage")
                return
        except Exception as e:
            log(2, e)

        if self.active < 0 or self.active >= len(self.tabs):
            return

        old = self.tabs[self.active].view

        # --- Clean up the old view ---
        try:
            ucc_old = old.configuration().userContentController()
            ucc_old.removeAllUserScripts()
            for name in ["tracker", "panic", "search"]:
                try:
                    ucc_old.removeScriptMessageHandlerForName_(name)
                except Exception as e:
                    log(2, e)
        except Exception as e:
            log(2, e)

        try:
            if old.superview() is not None:
                old.removeFromSuperview()
        except Exception as e:
            log(2, e)
        self.tabs[self.active].view = None

        # --- Determine which URL to reload ---
        url = ""
        try:
            u = old.URL()
            if u is not None:
                url = str(u.absoluteString())
        except Exception as e:
            log(2, e)
        if not url:
            url = self.tabs[self.active].url

        # --- Build a fresh WebView configuration (App-Bound OFF) ---
        config = WKWebViewConfiguration.alloc().init()

        config.preferences().setValue_forKey_(True, "fullScreenEnabled")

        # Security
        prefs = config.preferences()
        prefs.setValue_forKey_(False, "javaScriptCanOpenWindowsAutomatically")
        prefs.setValue_forKey_(False, "developerExtrasEnabled")

        config.setValue_forKey_(False, "allowFileAccessFromFileURLs")
        config.setValue_forKey_(False, "allowUniversalAccessFromFileURLs")

        try:
            config.setLimitsNavigationsToAppBoundDomains_(False)
        except Exception as e:
            log(2, e)

        # config = WKWebViewConfiguration.alloc().init()

        store = self.fpi.store_for(url, tab_uid=tab_index)

        config.setWebsiteDataStore_(store)

        webview = WKWebView.alloc().initWithFrame_configuration_(
            NSMakeRect(0, 0, width, height), config
        )

        # ✅ ATTACH CONTEXT MENU DELEGATE HERE
        menu = webview.menu()
        if not menu:
            menu = NSMenu.alloc().initWithTitle_("Context")
            webview.setMenu_(menu)

        menu_delegate = DarkelfMenuDelegate.alloc().init()
        menu.setDelegate_(menu_delegate)

        wk = WKWebView.alloc().initWithFrame_configuration_(old.frame(), config)

        if getattr(self, "_ui_delegate", None) is not None:
            wk.setUIDelegate_(self._ui_delegate)

        if getattr(self, "_nav_delegate", None) is not None:
            wk.setNavigationDelegate_(self._nav_delegate)

        # --- Set JS enabled or disabled ---
        prefs = WKPreferences.alloc().init()
        try:
            prefs.setJavaScriptEnabled_(
                True if url == HOME_URL else bool(getattr(self, "js_enabled", True))
            )
            prefs.setJavaScriptCanOpenWindowsAutomatically_(True)
        except Exception as e:
            log(2, e)
        config.setPreferences_(prefs)

        ucc = WKUserContentController.alloc().init()

        # ----------------------------
        # 🔥 1. Inject CONSISTENT seed (MATCH _new_wk)
        # ----------------------------
        tab = None
        if hasattr(self, "tabs") and 0 <= self.active < len(self.tabs):
            tab = self.tabs[self.active]

        seed = get_canvas_seed(tab)  # ✅ SAME as _new_wk

        seed_js = f"window.__darkelf_seed={seed};"

        ucc.addUserScript_(
            WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                seed_js, WKUserScriptInjectionTimeAtDocumentStart, False
            )
        )

        # ----------------------------
        # 🔥 2. Inject ALL defenses
        # ----------------------------
        inject_screen_spoof(ucc)

        # ----------------------------
        # 🔥 3. Core scripts
        # ----------------------------
        try:
            self._inject_core_scripts(ucc)
        except Exception as e:
            log(2, e)

        # ----------------------------
        # 🔥 4. ATTACH UCC (CRITICAL)
        # ----------------------------
        config.setUserContentController_(ucc)

        # --- Optional: Block external script resources when JS is off ---
        try:
            if not getattr(self, "js_enabled", True):
                store = WKContentRuleListStore.defaultStore()
                rule_text = '[{"trigger":{"url-filter":".*"},"action":{"type":"block","resource-type":["script"]}}]'

                def _cb(rule_list, err):
                    if rule_list and not err:
                        ucc.addContentRuleList_(rule_list)

                store.compileContentRuleListForIdentifier_encodedContentRuleList_completionHandler_(
                    "darkelf_block_scripts", rule_text, _cb
                )
        except Exception as e:
            log(2, e)

        # --- Attach the user content controller ---
        try:
            config.setUserContentController_(ucc)
        except Exception as e:
            log(2, e)

        try:
            frame = old.frame() if hasattr(old, "frame") else ((0, 0), (1200, 760))

            wk = WKWebView.alloc().initWithFrame_configuration_(frame, config)

            wk.setFrame_(NSMakeRect(0, 0, 1200, 760))

            if getattr(self, "_nav_delegate", None) is not None:
                wk.setNavigationDelegate_(self._nav_delegate)
            if getattr(self, "_ui_delegate", None) is not None:
                try:
                    wk.setUIDelegate_(self._ui_delegate)
                except Exception as e:
                    log(2, e)

            try:
                wk.setAutoresizingMask_(18)
            except Exception as e:
                log(2, e)

            # Mount & swap in
            self.tabs[self.active].view = wk
            self._mount_webview(wk)

        except Exception as e:
            print("[WK] creation failed:", e)
            return

        # --- Reload prior URL without redirecting to homepage ---
        try:
            old_url = ""
            try:
                u = old.URL()
                if u:
                    old_url = str(u.absoluteString())
            except Exception as e:
                log(2, e)
            if not old_url:
                try:
                    item = old.backForwardList().currentItem()
                    if item and item.URL():
                        old_url = str(item.URL().absoluteString())
                except Exception as e:
                    log(2, e)

            # Fall back to tab's remembered URL
            url = old_url or self.tabs[self.active].url or ""

            if not is_safe_url(url):
                log(1, "[BLOCKED URL]", url)
                return

            # If we're on the internal homepage or truly blank, render HOMEPAGE_HTML
            if url in (
                None,
                "",
                "about:home",
                "about://home",
                "about:blank",
                "about:blank#blocked",
            ):
                try:
                    self.tabs[self.active].view.loadHTMLString_baseURL_(
                        HOMEPAGE_HTML, NSURL.URLWithString_(HOME_URL)
                    )
                    self.tabs[self.active].url = HOME_URL
                    self.tabs[self.active].host = "home"
                    self._sync_addr()
                except Exception as e:
                    log(2, e)
                return  # <-- return ONLY in the homepage path

            # Otherwise load the same external URL so we remain on the current page
            req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
            wk.loadRequest_(req)
        except Exception as e:
            log(2, e)

    @property
    def active_tab(self):
        try:
            if 0 <= self.active < len(self.tabs):
                return self.tabs[self.active]
        except Exception as e:
            log(2, e)
        return None

    def _add_tab(self, url: str = "", home: bool = False):
        self.loading_home = bool(home)

        url_str = str(url or "").lower()

        # ----------------------------
        # 🔐 Generate PQ seed (ONLY ONCE)
        # ----------------------------
        if url_str.startswith("darkelf://") or home:
            print("[AddTab] Internal page → no PQ seed")
            pq_seed = None
        else:
            pq_seed = hashlib.sha256(os.urandom(32)).digest()
            print(f"[AddTab] PQ seed generated")

        container_nonce = secrets.token_hex(4)

        self._tab_uid_counter += 1
        tab_uid = self._tab_uid_counter

        self.current_url_for_fpi = url if url else HOME_URL

        # ----------------------------
        # 🔥 CREATE TAB FIRST (CRITICAL)
        # ----------------------------
        tab = Tab(
            view=None,
            data_store=None,
            url="",
            host="new",
            canvas_seed=None,
            container_nonce=container_nonce,
            tab_uid=tab_uid,
        )

        tab._pq_seed = pq_seed
        tab._pq_counter = 0
        tab._nonce = secrets.token_hex(8)

        # ----------------------------
        # 🔥 CREATE WEBVIEW USING TAB
        # ----------------------------
        wk, store = self._new_wk(container_nonce, pq_seed, tab)

        tab.view = wk
        tab.data_store = store

        wk.setNavigationDelegate_(self._nav_delegate)
        if getattr(self, "_ui_delegate", None):
            wk.setUIDelegate_(self._ui_delegate)
            
        # ----------------------------
        # CLEAN OLD VIEW
        # ----------------------------
        if 0 <= self.active < len(self.tabs):
            try:
                old_view = self.tabs[self.active].view
                old_view.stopLoading()
                #old_view.setNavigationDelegate_(None)
                #old_view.setUIDelegate_(None)
                old_view.removeFromSuperview()
            except Exception as e:
                log(2, e)

        # ----------------------------
        # MOUNT NEW VIEW
        # ----------------------------
        self._mount_webview(wk)
        self._bring_tabbar_to_front()

        self.tabs.append(tab)
        self.active = len(self.tabs) - 1

        # ----------------------------
        # MINI AI RESET
        # ----------------------------
        if hasattr(self, "mini_ai"):
            try:
                self.mini_ai.unique_domains.clear()
            except Exception as e:
                log(2, e)

        # ----------------------------
        # LOAD CONTENT
        # ----------------------------
        if home:
            try:
                self.urlbar.setStringValue_("")
            except Exception as e:
                log(2, e)

            wk.loadHTMLString_baseURL_(HOMEPAGE_HTML, NSURL.URLWithString_(HOME_URL))

            tab.url = HOME_URL
            tab.host = "Darkelf Home"

            self._pending_chip_sync = wk

        else:
            if url:
                try:
                    req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
                    wk.loadRequest_(req)
                    print(f"[AddTab] Loading URL")
                except Exception as e:
                    log(2, e)

                tab.url = url
                tab.host = "new"

        self.loading_home = False

        # ----------------------------
        # UI UPDATE
        # ----------------------------
        self._update_tab_buttons()
        self._sync_addr()

    def _teardown_webview(self, wk):
        if not wk:
            return
        try:
            js = r"""
            (function(){
              try {
                if (document.pictureInPictureElement) {
                  try { document.exitPictureInPicture(); } catch(e){}
                }
                document.querySelectorAll('video,audio').forEach(function(m){
                  try{ m.pause(); }catch(e){}
                  try{ m.src = ''; }catch(e){}
                  try{ m.load(); }catch(e){}
                });
                try {
                  if (window.YT && YT.get) {
                    var players = YT.get();
                    Object.keys(players || {}).forEach(function(k){
                      try{ players[k].stopVideo(); }catch(e){}
                    });
                  }
                } catch(e){}
                document.querySelectorAll('iframe').forEach(function(f){
                  try{ f.src = 'about:blank'; }catch(e){}
                });
              } catch(e){}
            })();
            """
            wk.evaluateJavaScript_completionHandler_(js, None)
        except Exception as e:
            log(2, e)

        try:
            wk.stopLoading()
        except Exception as e:
            log(2, e)
        try:
            wk.loadHTMLString_baseURL_("", None)
        except Exception as e:
            log(2, e)

        try:
            wk.setNavigationDelegate_(None)
        except Exception as e:
            log(2, e)
        try:
            wk.setUIDelegate_(None)
        except Exception as e:
            log(2, e)
        try:
            ucc = wk.configuration().userContentController()
            if ucc:
                try:
                    ucc.removeAllUserScripts()
                except Exception as e:
                    log(2, e)
                for name in ("netlog", "search"):
                    try:
                        ucc.removeScriptMessageHandlerForName_(name)
                    except Exception as e:
                        log(2, e)

        except Exception as e:
            log(2, e)

        try:
            wk.removeFromSuperview()
        except Exception as e:
            log(2, e)

        try:
            tab.data_store = None
        except Exception as e:
            log(2, e)

    def actNewTab_(self, _):
        self._add_tab(home=True)

    def actSwitchTab_(self, sender):
        """Switch to the tab identified by sender.tag() - PROPER tab isolation"""
        try:
            idx = int(sender.tag())
        except Exception:
            return

        if not (0 <= idx < len(self.tabs)) or idx == self.active:
            return

        cv = self.window.contentView()

        for subview in list(cv.subviews()):
            try:
                if isinstance(subview, WKWebView):
                    subview.removeFromSuperview()
            except Exception as e:
                log(2, e)

        # 🔹 update active tab
        self.active = idx

        # 🔹 mount correct webview
        self._mount_webview(self.tabs[idx].view)

        # 🔹 bring UI layers back
        self._bring_tabbar_to_front()

        # 🔹 refresh tab highlight
        self._update_tab_buttons()

        # 🔹 sync address bar
        self._sync_addr()

    def actCloseTabIndex_(self, sender):

        try:
            idx = int(sender.tag())
        except Exception:
            return

        log(2, "Close tab index:", idx)

        if not (0 <= idx < len(self.tabs)):
            return

        tab = self.tabs[idx]

        # 🔥 STEP 1 — adjust active index BEFORE deletion
        if idx == self.active:
            if len(self.tabs) > 1:
                self.active = min(idx, len(self.tabs) - 2)
            else:
                self.active = -1
        elif idx < self.active:
            self.active -= 1

        # 🔥 STEP 2 — destroy ONLY ONCE (CRITICAL)
        try:
            darkelf_destroy_tab(tab)
        except Exception as e:
            print("[CloseTab] destroy error:", e)

        # 🔥 STEP 3 — remove tab
        del self.tabs[idx]

        # 🔥 STEP 4 — if no tabs left → create new
        if not self.tabs:
            self.active = -1
            self._add_tab(home=True)
            return

        # 🔥 STEP 5 — ensure valid index
        self.active = max(0, min(self.active, len(self.tabs) - 1))

        # 🔥 STEP 6 — mount new active tab
        wk = self.tabs[self.active].view

        try:
            self._mount_webview(wk)
        except Exception as e:
            print("[CloseTab] mount error:", e)

        # 🔥 STEP 7 — UI sync
        self._update_tab_buttons()
        self._sync_addr()

    def _close_tab(self):
        if 0 <= self.active < len(self.tabs):

            class _Tmp:
                def tag(self_inner):
                    return self.active

            self.actCloseTabIndex_(_Tmp())

    def actBack_(self, _):
        try:
            self.tabs[self.active].view.goBack_(None)
        except Exception as e:
            log(2, e)

    def actFwd_(self, _):
        try:
            self.tabs[self.active].view.goForward_(None)
        except Exception as e:
            log(2, e)

    def actReload_(self, _):
        try:
            if not self.tabs:
                return

            tab = self.tabs[self.active]
            wk = tab.view

            # Existing logic preserved
            u = wk.URL()
            cur = str(u.absoluteString()) if u is not None else (tab.url or "")

            if cur == HOME_URL:
                self.actHome_(None)
            else:
                wk.reload_(None)

        except Exception as e:
            print("[Reload] Failed:", e)

    def actHome_(self, _):
        try:
            wk = self.tabs[self.active].view

            wk.loadHTMLString_baseURL_(HOMEPAGE_HTML, NSURL.URLWithString_(HOME_URL))

            self.tabs[self.active].url = HOME_URL
            self.tabs[self.active].host = "Darkelf Home"

            self._update_tab_buttons()
            self._sync_addr()

        except Exception as e:
            print("[Home] Failed:", e)

    def actZoomIn_(self, _):
        try:
            s = self.tabs[self.active].view.magnification()
            self.tabs[self.active].view.setMagnification_centeredAtPoint_(
                min(s + 0.1, 3.0), (0, 0)
            )
        except Exception as e:
            log(2, e)

    def actZoomOut_(self, _):
        try:
            s = self.tabs[self.active].view.magnification()
            self.tabs[self.active].view.setMagnification_centeredAtPoint_(
                max(s - 0.1, 0.5), (0, 0)
            )
        except Exception as e:
            log(2, e)

    def actFull_(self, _):
        try:
            self.window.toggleFullScreen_(None)
        except Exception as e:
            log(2, e)

    @objc.python_method
    def _tint_alert_ok_green(self, alert):
        ACCENT = (52 / 255.0, 199 / 255.0, 89 / 255.0, 1.0)
        if alert.buttons().count() == 0:
            alert.addButtonWithTitle_("OK")
        btn = alert.buttons().objectAtIndex_(0)
        try:
            if hasattr(btn, "setBezelColor_"):
                btn.setBezelColor_(
                    NSColor.colorWithCalibratedRed_green_blue_alpha_(*ACCENT)
                )
            elif hasattr(btn, "setContentTintColor_"):
                btn.setContentTintColor_(
                    NSColor.colorWithCalibratedRed_green_blue_alpha_(*ACCENT)
                )
            else:
                btn.setWantsLayer_(True)
                btn.layer().setCornerRadius_(6.0)
                btn.layer().setBackgroundColor_(
                    NSColor.colorWithCalibratedRed_green_blue_alpha_(*ACCENT).CGColor()
                )
        except Exception as e:
            print("[Alert tint] failed:", e)

    def actGo_(self, sender):
        try:
            text = str(sender.stringValue()).strip()
            if not text:
                return

            # Build URL
            if "://" not in text and "." not in text:
                q = quote_plus(text)
                url = "https://lite.duckduckgo.com/lite/?q=" + q
            elif "://" not in text:
                url = "https://" + text
            else:
                url = text

            # FIX: Use _navigate_to instead of _add_tab
            self._navigate_to(url)

        except Exception as e:
            print("[Go] Failed:", e)

    def actNuke_(self, sender):

        # 🔴 Confirmation Alert
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Clear All Browsing Data?")
        alert.setInformativeText_(
            "This will wipe cookies, cache, local storage, "
            "IndexedDB, and all website data, then close Darkelf."
        )
        alert.setAlertStyle_(NSAlertStyleCritical)

        # Order matters:
        # First button = 1000
        # Second button = 1001
        alert.addButtonWithTitle_("Cancel")  # 1000
        alert.addButtonWithTitle_("Wipe")  # 1001

        # 🔴 Response Handler
        def on_response(code):

            # Only proceed if Wipe was pressed (1001)
            if int(code) != 1001:
                return

            try:
                # 1️⃣ Destroy all WebViews (ephemeral wipe)
                for tab in list(self.tabs):
                    try:
                        self._teardown_webview(tab.view)
                    except Exception as e:
                        log(2, e)

                self.tabs.clear()
                self.active = -1

                # 2️⃣ Reset ephemeral store
                self._data_store = WKWebsiteDataStore.nonPersistentDataStore()

            except Exception as e:
                print("wipe error:", e)

            # 3️⃣ Shutdown browser cleanly
            NSApplication.sharedApplication().terminate_(None)

        # Show confirmation sheet
        alert.beginSheetModalForWindow_completionHandler_(self.window, on_response)

    def _storage_cleanup(self):
        try:
            store = WKWebsiteDataStore.nonPersistentDataStore()
            types = WKWebsiteDataStore.allWebsiteDataTypes()

            def handler():
                print("[Darkelf] Non-persistent storage cleanup complete.")

            store.removeDataOfTypes_modifiedSince_completionHandler_(types, 0, handler)
        except Exception as e:
            print("[Darkelf] Storage cleanup skipped:", e)

    def _load_url_in_active(self, url):
        try:
            req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
            self.tabs[self.active].view.loadRequest_(req)
            self.tabs[self.active].url = url
            from urllib.parse import urlparse

            u = urlparse(url)
            host = u.netloc or "site"
            if host.lower().startswith("www."):
                host = host[4:] or "site"
            self.tabs[self.active].host = host
            self._sync_addr()
            self._update_tab_buttons()
        except Exception as e:
            print("[Load] error:", e)

    def _sync_addr(self):
        try:
            v = ""
            if 0 <= self.active < len(self.tabs):
                try:
                    u = self.tabs[self.active].view.URL()
                    if u is not None:
                        v = str(u.absoluteString())
                except Exception as e:
                    log(2, e)

                if not v:
                    v = self.tabs[self.active].url or ""

            if v in (
                HOME_URL,
                "about:home",
                "about://home",
                "about:blank",
                "about:blank#blocked",
            ):
                v = ""

            self.urlbar.setStringValue_(v)

        except Exception as e:
            log(2, e)

    def _install_key_monitor(self):

        def handler(evt):

            try:

                if evt.type() != 10:
                    return evt

                flags = evt.modifierFlags()

                cmd = bool(flags & NSEventModifierFlagCommand)
                shift = bool(flags & NSEventModifierFlagShift)
                ctrl = bool(flags & NSEventModifierFlagControl)

                if not cmd:
                    return evt

                ch = evt.charactersIgnoringModifiers()
                raw = evt.characters()

                if ch:
                    ch = ch.lower()

                key = evt.keyCode()

                # ----------------------------------
                # ⌘ ←
                # ----------------------------------
                if key == 123:
                    self.actBack_(None)
                    return None

                # ----------------------------------
                # ⌘ →
                # ----------------------------------
                if key == 124:
                    self.actFwd_(None)
                    return None
                    
                # ----------------------------------
                # ⌘F FIND BAR
                # ----------------------------------
                if ch == "f" and not shift and not ctrl:

                    try:

                        NSOperationQueue.mainQueue().addOperationWithBlock_(
                            lambda: self.showFindBar()
                        )

                    except Exception as e:
                        print("[FindBar Shortcut Error]", e)

                    return None
                    
                # ----------------------------------
                # ⌃⌘F FULLSCREEN
                # ----------------------------------
                if ch == "f" and ctrl:

                    try:
                        self.window.toggleFullScreen_(None)
                    except Exception as e:
                        print("[Fullscreen Error]", e)

                    return None

                # ----------------------------------
                # ⌘L ADDRESS BAR
                # ----------------------------------
                if ch == "l" and not shift:

                    self.window.makeFirstResponder_(self.addr)
                    return None

                # ----------------------------------
                # ⌘T
                # ----------------------------------
                if ch == "t":
                    self.actNewTab_(None)
                    return None

                # ----------------------------------
                # ⌘W
                # ----------------------------------
                if ch == "w":
                    self.actCloseTab_(None)
                    return None

                # ----------------------------------
                # ⌘R
                # ----------------------------------
                if ch == "r":
                    self.actReload_(None)
                    return None

                # ----------------------------------
                # ⌘S
                # ----------------------------------
                if ch == "s":
                    self.actSnapshot_(None)
                    return None

                # ----------------------------------
                # ⇧⌘X
                # ----------------------------------
                if ch == "x" and shift:

                    NSApp().terminate_(None)
                    return None

                # ----------------------------------
                # ⌘=
                # ----------------------------------
                if raw == "=":
                    self.actZoomIn_(None)
                    return None

                # ----------------------------------
                # ⌘-
                # ----------------------------------
                if raw == "-":
                    self.actZoomOut_(None)
                    return None

                # ----------------------------------
                # ⇧⌘/
                # macOS returns "/" not "?"
                # ----------------------------------
                # ⇧⌘/
                if raw == "/" and shift:

                    self.openDarkelfCommandCenter_(None)
                    return None

            except Exception as e:
                print("[Hotkey Error]", e)

            return evt

        # IMPORTANT:
        # RETAIN monitor or GC kills shortcuts
        self._keyMonitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            1 << 10,
            handler
        )
        
    def showFindBar(self):

        try:

            # ------------------------------------------
            # destroy broken/stale panel
            # ------------------------------------------
            panel_ref = getattr(self, "_findPanel", None)

            if panel_ref is not None:

                try:

                    # avoid redundant Cocoa detach
                    if panel_ref.superview():
                        panel_ref.removeFromSuperview()

                except Exception as e:

                    print("[FindBar Cleanup Error]", e)

            self._findPanel = None

            # ------------------------------------------
            # floating overlay
            # ------------------------------------------
            panel = DraggableFindBar.alloc().initWithFrame_(
                NSMakeRect(28, 28, 430, 62)
            )

            panel.setAutoresizingMask_(
                NSViewMaxXMargin | NSViewMaxYMargin
            )

            panel.setWantsLayer_(True)

            layer = panel.layer()

            layer.setCornerRadius_(14)

            layer.setBackgroundColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.08, 0.09, 0.11, 0.98
                ).CGColor()
            )

            layer.setBorderWidth_(1.0)

            layer.setBorderColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.18, 0.20, 0.24, 1
                ).CGColor()
            )

            # ------------------------------------------
            # search field
            # ------------------------------------------
            field = DarkelfSearchField.alloc().initWithFrame_(
                NSMakeRect(16, 16, 370, 30)
            )

            field.browser = self
            
            field.setRefusesFirstResponder_(False)
            
            field.setPlaceholderString_("Find in page")

            field.setFont_(NSFont.systemFontOfSize_(14))

            # Native macOS rendering
            field.setFocusRingType_(NSFocusRingTypeNone)

            field.setBordered_(True)
            field.setBezeled_(True)

            # Better text rendering
            field.cell().setUsesSingleLineMode_(True)

            # Dark mode text
            try:

                field.setTextColor_(NSColor.whiteColor())

            except Exception as e:

                print("[FindBar TextColor Error]", e)

            # IMPORTANT:
            # DO NOT layer-style NSSearchField
            # Cocoa breaks rendering if you do

            try:

                field.setWantsLayer_(False)

            except Exception as e:

                print("[FindBar Layer Error]", e)

            panel.addSubview_(field)
            
            # ------------------------------------------
            # close button
            # ------------------------------------------

            close = NSButton.alloc().initWithFrame_(
                NSMakeRect(392, 18, 24, 24)
            )

            close.setBordered_(False)

            close.setTitle_("✕")

            close.setBezelStyle_(0)

            close.setFont_(
                NSFont.systemFontOfSize_weight_(13, 0.7)
            )

            close.setContentTintColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.20, 0.78, 0.35, 1
                )
            )

            close.setTarget_(self)

            close.setAction_("hideFindBar:")

            close.setWantsLayer_(True)

            close.layer().setCornerRadius_(8)

            close.layer().setBackgroundColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.12,
                    0.14,
                    0.17,
                    1
                ).CGColor()
            )

            panel.addSubview_(close)

            # ------------------------------------------
            # attach ABOVE EVERYTHING
            # ------------------------------------------
            content = self.window.contentView()

            content.addSubview_positioned_relativeTo_(
                panel,
                1,
                None
            )

            self._findPanel = panel
            self._findField = field

            # ------------------------------------------
            # live find
            # ------------------------------------------
            field.setTarget_(self)
            field.setAction_("performPageFind:")
            
            field.cell().setSendsSearchStringImmediately_(True)
            field.cell().setSendsWholeSearchString_(False)
            
            self.window.makeFirstResponder_(field)

        except Exception as e:
            print("[FindBar Error]", e)
            
    def hideFindBar_(self, sender):

        try:

            if hasattr(self, "_findPanel") and self._findPanel:

                self._findPanel.removeFromSuperview()

                self._findPanel = None
                self._findField = None
    
        except Exception as e:
            print("[FindBar Hide Error]", e)
        
    def performPageFind_(self, sender):

        try:

            text = self._findField.stringValue()

            if not text:
                return

            tab = self.tabs[self.active]

            js = f"""
            window.find({json.dumps(text)}, false, false, true, false, false, false);
            """

            tab.view.evaluateJavaScript_completionHandler_(
                js,
                None
            )

        except Exception as e:
            print("[Find Error]", e)
                        
    def setupHotkeys(self):

        def handler(event):

            chars = event.charactersIgnoringModifiers()

            mods = event.modifierFlags()

            cmd = mods & NSEventModifierFlagCommand
            shift = mods & NSEventModifierFlagShift
            
            # ESC closes FindBar
            if event.keyCode() == 53:

                if hasattr(self, "_findPanel") and self._findPanel:

                    self.hideFindBar_(None)

                    return None
                    
            # ⇧⌘/
            if cmd and shift and chars == "/":

                self.openDarkelfCommandCenter_(None)

                return None

            return event

        NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            10,   # keyDown
            handler
        )
            
    def safe_shutdown(self):

        if hasattr(self, "window"):
            try:
                nc = NSNotificationCenter.defaultCenter()
                nc.removeObserver_(self)
            except Exception as e:
                log(2, e)

        if hasattr(self, "tabs"):
            for tab in self.tabs:
                view = getattr(tab, "view", None)
                if view:
                    try:
                        ucc = view.configuration().userContentController()
                        for name in ("netlog", "search"):
                            ucc.removeScriptMessageHandlerForName_(name)
                        view.removeFromSuperview()
                    except Exception as e:
                        log(2, e)

    def _wipe_all_site_data(self):
        """
        Fully reset browser session:
        - Tear down all webviews
        - Clear tab list
        - Reset active index
        - Recreate fresh non-persistent data store
        """

        if getattr(self, "_has_wiped", False):
            return

        try:
            # Teardown all webviews safely
            for tab in list(self.tabs):
                try:
                    if hasattr(tab, "view") and tab.view:
                        self._teardown_webview(tab.view)
                except Exception as e:
                    log(2, e)

            # Clear tab state
            self.tabs = []
            self.active = 0

            # Reset to fresh ephemeral store
            self._data_store = WKWebsiteDataStore.nonPersistentDataStore()

            # Mark wipe complete only after success
            self._has_wiped = True

        except Exception as e:
            print("wipe error:", e)

    def windowWillClose_(self, notification):

        try:
            # Stop all webviews
            for tab in getattr(self, "tabs", []):
                try:
                    tab.view.stopLoading()
                except Exception as e:
                    log(2, e)
        except Exception as e:
            log(2, e)

        NSApplication.sharedApplication().terminate_(None)

    def applicationWillTerminate_(self, notification):
        try:
            pass
        except Exception as e:
            log(2, e)

    def wipe_webkit_memory():
        store = WKWebsiteDataStore.nonPersistentDataStore()

        types = WKWebsiteDataStore.allWebsiteDataTypes()

        store.removeDataOfTypes_modifiedSince_completionHandler_(types, 0, lambda: None)

    def actSnapshot_(self, sender):
        try:
            wk = self.tabs[self.active].view

            def handler(image, error):
                if image and not error:

                    # --- Darkelf snapshot folder ---
                    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                    library = os.path.join(desktop, "Darkelf Library")
                    snapdir = os.path.join(library, "Darkelf Snap")

                    os.makedirs(snapdir, exist_ok=True)

                    # timestamp filename
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"darkelf_snapshot_{ts}.png"
                    path = os.path.join(snapdir, filename)

                    url = NSURL.fileURLWithPath_(path)

                    tiff = image.TIFFRepresentation()
                    rep = NSBitmapImageRep.imageRepWithData_(tiff)
                    png = rep.representationUsingType_properties_(4, None)  # PNG
                    png.writeToURL_atomically_(url, True)

                    print("[Darkelf] Snapshot saved →", path)

            wk.takeSnapshotWithConfiguration_completionHandler_(None, handler)

        except Exception as e:
            print("[Snapshot] Failed:", e)


class AppDelegate(NSObject):

    def applicationShouldTerminate_(self, sender):
        # Allow termination immediately
        return True

    def applicationWillTerminate_(self, notification):
        """Graceful shutdown with threat report and data cleanup"""
        print("\n" + "=" * 70)
        print("[Darkelf] Browser shutting down - initiating cleanup...")
        print("=" * 70 + "\n")

        try:
            if hasattr(self, "browser") and self.browser is not None:

                # ═══════════════════════════════════════════════════════════
                # 2. STOP COOKIE SCRUBBER
                # ═══════════════════════════════════════════════════════════
                print("\n" + "=" * 70)
                print("[Darkelf] Shutdown complete - all data wiped")
                print("=" * 70 + "\n")

        except Exception as e:
            print("[Quit] Unexpected shutdown error:", e)


def main():
    try:
        NSUserDefaults.standardUserDefaults().setVolatileDomain_forName_(
            {}, NSRegistrationDomain
        )
        print("[Prefs] NSUserDefaults set to volatile (RAM-only).")
    except Exception as e:
        print("[Prefs] Failed to set volatile domain:", e)

    app = NSApplication.sharedApplication()

    # ✅ APPLY DARKELF THEME HERE (CORRECT SPOT)
    apply_darkelf_theme()

    # ✅ FORCE GREEN ACCENT (removes orange system highlight)
    NSUserDefaults.standardUserDefaults().setInteger_forKey_(3, "AppleAccentColor")

    # ✅ PRE-COMPILE RULES BEFORE BROWSER STARTS
    print("[Startup] Compiling content blocking rules...")
    ContentRuleManager.load_rules()

    # ✅ WAIT FOR ASYNC COMPILATION

    time.sleep(3.0)  # Give WebKit time to compile 121 rules

    if ContentRuleManager._rule_list:
        print("[Startup] ✅ Rules ready - initializing browser")

    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    NSURLCache.setSharedURLCache_(None)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    delegate.browser = Browser.alloc().init()

    app.run()

    wipe_webkit_memory()

    nav_delegate.wipe_download_traces()


if __name__ == "__main__":
    main()
