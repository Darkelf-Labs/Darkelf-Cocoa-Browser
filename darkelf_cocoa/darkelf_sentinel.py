import time
from datetime import datetime

from collections import deque
from urllib.parse import (
    urlparse,
    unquote,
)

from Foundation import (
    NSOperationQueue, NSURL,
)

from .darkelf_utils import log

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
    # UI ACTIONS (via Browser)
    # --------------------------------------------------
    def _show_threat_report_ui(self):

        if self._lockdown_ui_opened:
            return

        if not self.browser:
            return

        try:

            report_idx = -1

            for i, tab in enumerate(self.browser.tabs):
                if getattr(tab, "url", "") == "darkelf://report":
                    report_idx = i
                    break

            if report_idx >= 0:

                tab = self.browser.tabs[report_idx]
                html = self.browser._build_threat_report_html()

                # tab.view.loadHTMLString_baseURL_(html, None)
                tab.view.loadHTMLString_baseURL_(
                    html, NSURL.URLWithString_("darkelf://report")
                )

                tab.url = "darkelf://report"
                tab.host = "Darkelf MiniAI Console"

                self.browser.active = report_idx
                self.browser._update_tab_buttons()
                self.browser._sync_addr()

            else:

                self.browser.openThreatReport_(None)

        except Exception as e:
            print("[MiniAI] threat report error:", e)

        self._lockdown_ui_opened = True

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
            "btn_home",
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
            "btn_home",
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
