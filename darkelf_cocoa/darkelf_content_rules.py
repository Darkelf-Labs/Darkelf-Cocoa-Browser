import time
import os
import json
import re
import hashlib

from WebKit import WKContentRuleListStore
from PyObjCTools import AppHelper
from Foundation import (NSURL, NSMutableURLRequest, NSURLSession, NSURLSessionConfiguration)


class ContentRuleManager:
    _rule_list = None
    _loaded = False
    _pending_controllers = []
    _completion_callbacks = []

    # --------------------------------------------------
    # Versioning
    # --------------------------------------------------
    VERSION = "15.33"
    IDENTIFIER = f"darkelf_rules_v{VERSION}"
    
    # Static, top-level-site adblocking protection profiles.
    # TRUSTED bypasses compiled content rules for compatibility.
    # PROTECTED retains EasyList plus the application's ad-slot cleanup.
    # STANDARD retains the existing global rule behavior.
    SITE_PROTECTION = {
        "dw.com": "TRUSTED",
        "cnn.com": "PROTECTED",
        "gamespot.com": "PROTECTED",
    }

    @classmethod
    def protection_mode(cls, hostname):
        host = (hostname or "").lower().rstrip(".")
        for domain, mode in cls.SITE_PROTECTION.items():
            if host == domain or host.endswith("." + domain):
                return mode
        return "STANDARD"

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
        "antiadblock": 0,
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
            # Disabled for compatibility. This list is designed to fight
            # anti-adblock scripts and is much more likely to interfere with
            # challenge/verification flows than the core EasyList network set.
            "enabled": False,
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

                cosmetic_imported = 0
                for rule in parsed:

                    if rule.get("action", {}).get("type") == "css-display-none":
                        if cosmetic_imported >= 1200:
                            continue

                    if imported >= limit:
                        break

                    key = json.dumps(rule, sort_keys=True)

                    if key in seen:
                        continue

                    seen.add(key)
                    all_rules.append(rule)
                    imported += 1
                    if rule.get("action", {}).get("type") == "css-display-none":
                        cosmetic_imported += 1

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
                f"[Rules] Reached configured import budget ({MAX_RULES:,} rules)"
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

            # A script-specific ABP rule is a network block for JavaScript
            # resources, not a request to disable JavaScript for the page.
            # Negated script rules need ABP exclusion semantics that this
            # intentionally conservative parser does not implement.
            if "~script" in mods:
                cls._unsupported_rules += 1
                return []

            # Match the hostname at the URL authority boundary. A plain
            # substring could also match an unrelated site's path or host.
            trigger = {
                "url-filter": (
                    r"^https?://([^/?#]+\.)?" + re.escape(body)
                    + r"([:/?#].*)?$"
                ),
            }

            if "script" in mods:
                trigger["resource-type"] = ["script"]

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

        # Only domain-scoped cosmetic rules are safe to import automatically.
        # Generic EasyList selectors can hide unrelated site controls.
        if "##" in line and not line.startswith("#"):


            domain_part, selector = line.split("##", 1)

            selector = selector.strip()

            if not selector:
                return []

            # ignore unsupported cosmetic syntaxes
            if selector.startswith(("?", "+js", "^")):
                return []

            # Reject procedural, pseudo-class and complex selector syntax.
            # Restrict to simple class/id/attribute selectors to avoid
            # accidentally hiding structural site elements.
            if not re.fullmatch(r"(?:[.#][A-Za-z_][\w-]*|\[(?:id|class|data-ad-slot|data-ad-unit|data-testid|aria-label)[\^*$~|]?=['\"]?[A-Za-z0-9_ -]+['\"]?\])", selector):
                return []

            # Do not import global cosmetics or domain-exclusion syntax.
            # Both require additional ABP semantics to implement correctly.
            if not domain_part or "~" in domain_part:
                return []

            # CNN is not globally exempt: only explicitly ad-related selectors
            # pass the allowlist below, preserving video and navigation UI.

            # Import only recognizable advertising slots, not arbitrary UI.
            if not re.search(r"(?i)(?:ad[-_]?slot|ad[-_]?container|ad[-_]?unit|adwrapper|adsbygoogle|banner[-_]?ad|div-gpt-ad|google_ads_iframe)", selector):
                return []

            # Global cosmetic rule (unreachable by design).
            if domain_part == "":

                key = ("*", selector)

                if key in cls._css_seen:
                    return []

                cls._css_seen.add(key)

                return [{
                    "trigger": {"url-filter": ".*", "unless-domain": ["*cnn.com"]},
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

                if not re.fullmatch(r"[A-Za-z0-9.-]+", d):
                    continue

                # Anchor to the document host, not a substring of any URL.
                domains.append(r"^https?://([^/]+\.)?" + re.escape(d) + r"(:[0-9]+)?/")

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
    def attach_to_controller(cls, controller):
        """Attach immediately if ready, otherwise install on compile completion."""
        # Diagnostic only: launch with DARKELF_DIAG_NO_CONTENT_RULES=1 to
        # isolate WKContentRuleList interference with embedded video players.
        # Default behavior is unchanged; no persistent preference is written.
        if os.environ.get("DARKELF_DIAG_NO_CONTENT_RULES") == "1":
            print("[Rules][Diagnostic] Content rules NOT attached for this run", flush=True)
            return
        if cls._rule_list is not None:
            try:
                controller.addContentRuleList_(cls._rule_list)
            except Exception as exc:
                print("[Rules] Immediate content-rule attachment failed:", exc, flush=True)
                raise
        elif controller not in cls._pending_controllers:
            cls._pending_controllers.append(controller)

    @classmethod
    def _notify_ready(cls):
        """WKUserContentController changes must run on AppKit's main thread."""
        if os.environ.get("DARKELF_DIAG_NO_CONTENT_RULES") == "1":
            cls._pending_controllers.clear()
            callbacks, cls._completion_callbacks = cls._completion_callbacks, []
            for callback in callbacks:
                AppHelper.callAfter(callback)
            return
        def install():
            pending, cls._pending_controllers = cls._pending_controllers, []
            for controller in pending:
                try:
                    controller.addContentRuleList_(cls._rule_list)
                except Exception as exc:
                    print('[Rules] Could not attach content rules:', exc, flush=True)
            callbacks, cls._completion_callbacks = cls._completion_callbacks, []
            for callback in callbacks:
                try:
                    callback()
                except Exception as exc:
                    print('[Rules] Ready callback failed:', exc)
        AppHelper.callAfter(install)

    @classmethod
    def load_rules(cls, completion_callback=None):
        cls._ensure_cache()
        try:
            cls.refresh_subscriptions()
        except Exception as e:
            print("[Rules] Subscription update failed:", e)
            
        if completion_callback:
            if cls._rule_list is not None:
                AppHelper.callAfter(completion_callback)
            else:
                cls._completion_callbacks.append(completion_callback)
        if cls._loaded:
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


                cls._rule_list = rule_list


                cls._notify_ready()
                return

            # --------------------------------------------------
            # Build JSON
            # --------------------------------------------------

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

                cls._notify_ready()


            store.compileContentRuleListForIdentifier_encodedContentRuleList_completionHandler_(
                identifier,
                json_rules,
                _compiled,
            )
            
        store.lookUpContentRuleListForIdentifier_completionHandler_(
            identifier,
            _lookup,
        )

    # Site-scoped playback compatibility. WebKit content rules cannot observe
    # HTMLMediaElement play/error events or dynamically switch rule lists.
    # These exceptions are therefore scoped to the TOP-LEVEL document host.
    # Normal adblocking remains active everywhere else.
    MEDIA_COMPAT_HOSTS = (
        "espn.com", "nba.com", "nhl.com", "aetv.com",
        "history.com", "lifetime.com", "ae.com",
    )

    @classmethod
    def _media_compat_domains(cls):
        # WebKit if-domain accepts a leading * wildcard for subdomains.
        return [host for domain in cls.MEDIA_COMPAT_HOSTS
                for host in (domain, "*" + domain)]

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
                    "url-filter": url,
                    **({"unless-domain": ["reddit.com", "*reddit.com"]}
                       if url in (
                           ".*collect.*", ".*telemetry.*", ".*metrics.*",
                           ".*beacon.*", ".*tracker.*", ".*tracking.*",
                           ".*pixel.*", ".*analytics.*collect.*",
                       ) else {}),
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
            # v15.30: narrowly scoped advertising hosts. Preserve the
            # original v15.28 rule structure and ordering. These are simple
            # escaped host fragments, like the existing built-in entries.
            # Avoid blocking the main social/media application domains.
            "criteo\\.net",
            "adsrvr\\.org",
            "chartboost\\.com",
            "inmobi\\.com",
            "mintegral\\.com",
            "mintegral\\.net",
            "tritondigital\\.com",
            "tritonadvertising\\.com",
            "pixel\\.quora\\.com",
            "ct\\.pinterest\\.com",

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
            # Yandex.Metrica script and collection endpoints.
            # Host-specific patterns avoid blocking unrelated Yandex services.
            r"^https?://mc\.yandex\.ru[/?:#]",
            r"^https?://mc\.yandex\.com[/?:#]",
            r"^https?://mc\.yandex\.by[/?:#]",
            r"^https?://mc\.yandex\.kz[/?:#]",
            r"^https?://mc\.yandex\.uz[/?:#]",
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
            "js\\.sentry-cdn\\.com",
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
            "trigger": {"url-filter": ".*", "unless-domain": ["*cnn.com"]},
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
            "trigger": {"url-filter": ".*", "unless-domain": ["*cnn.com"]},
            "action": {
                "type": "css-display-none",
                "selector": """
    iframe[src*='doubleclick.net'],
    iframe[src*='googlesyndication.com'],
    iframe[src*='amazon-adsystem.com'],
    [id^='google_ads_iframe_'],
    [id^='div-gpt-ad-']:empty,
    [aria-label='Advertisement']:empty
    """
            }
        })
        
        # Hide recognizable ad SLOT wrappers, not just blocked iframes.
        # Exclude CNN until its video/layout behavior is verified.
        add({
            "trigger": {"url-filter": ".*", "unless-domain": ["*cnn.com"]},
            "action": {
                "type": "css-display-none",
                "selector": """
                    [id^='div-gpt-ad-'],
                    [id^='google_ads_iframe_'],
                    ins.adsbygoogle,
                    [data-ad-slot][data-ad-client],
                    [data-testid='ad-container'],
                    [aria-label='Advertisement']:not(a):not(button),
                    .ad-slot[data-ad-unit],
                    .ad-container[data-ad-unit]
                """
            }
        })

        # --------------------------------------------------
        # GLOBAL COSMETIC (SAFE ONLY)
        # --------------------------------------------------
        rules.append(
            {
                "trigger": {"url-filter": ".*", "unless-domain": ["*cnn.com"]},
                "action": {
                    "type": "css-display-none",
                    "selector": """
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
            "trigger": {"url-filter": ".*", "unless-domain": ["*cnn.com"]},
            "action": {
                "type": "css-display-none",
                "selector": """
[id^='google_ads_iframe_'],
[id^='div-gpt-ad-']:empty,
iframe[src*='doubleclick.net'],
iframe[src*='googlesyndication.com']
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
        # Site-scoped ad placeholders (not video/player containers)
        # --------------------------------------------------
        # These selectors target recognizable ad inventory rather than generic
        # layout classes. Do not hide arbitrary empty divs or iframe wrappers.
        for host, selectors in (
            (
                "cnn.com",
                (
                    "[id^='div-gpt-ad-']",
                    "[id^='google_ads_iframe_']",
                    "ins.adsbygoogle",
                    "[data-ad-slot][data-ad-client]",
                    "[data-testid='ad-container']",
                ),
            ),
            (
                "gamespot.com",
                (
                    "[id^='div-gpt-ad-']",
                    "[id^='google_ads_iframe_']",
                    "ins.adsbygoogle",
                    "[data-ad-slot][data-ad-client]",
                    "[data-testid='ad-container']",
                ),
            ),
        ):
            add({
                "trigger": {
                    "url-filter": r"^https?://([^/]+\.)?" + re.escape(host) + r"(:[0-9]+)?/"
                },
                "action": {
                    "type": "css-display-none",
                    "selector": ", ".join(selectors),
                },
            })

        # --------------------------------------------------
        # EMPTY AD-CONTAINER CLEANUP (restored from older Cocoa)
        # --------------------------------------------------
        # Cosmetic-only: does not change network blocking, subscriptions,
        # player requests, or the existing adblock-tester rules.
        # Scope the legacy selectors to news/gaming sites to avoid hiding
        # unrelated page content across the entire web.
        for host in ("cnn.com", "gamespot.com", "euronews.com"):
            add({
                "trigger": {
                    "url-filter": ".*",
                    "if-domain": [host, "*" + host]
                },
                "action": {
                    "type": "css-display-none",
                    "selector": ", ".join((
                        ".ad-slot",
                        ".ad-container",
                        ".banner-ad",
                        ".container__ads",
                        ".zn-body__ad",
                        ".pg-rail__ad",
                        ".l-container--ads",
                        ".ad-placeholder",
                        "[id*='ad-slot']",
                        "[class*='ad-slot']",
                        "div:empty[class*='ad']",
                        "div:empty[id*='ad']",
                        "[data-testid='ad-slot']",
                        "[data-testid='ad-wrapper']",
                        "[data-ad-container]",
                        ".ad-wrapper",
                        ".ad-unit",
                        ".advertisement-container",
                        ".advertisement-wrapper",
                        ".advertisement-placeholder",
                        "[id^='div-gpt-ad-']",
                    )),
                },
            })

        # Imported subscriptions must precede late compatibility exceptions.
        # They were previously parsed by a helper that was never called.
        for external_rule in cls._external_subscription_rules():
            add(external_rule)

        # --------------------------------------------------
        # SECURITY / BOT-CHALLENGE COMPATIBILITY
        # --------------------------------------------------
        # Keep these rules LATE. "ignore-previous-rules" cancels blockers
        # already matched for the challenge request itself, while leaving the
        # rest of the site's ad/tracker filtering enabled.
        #
        # Do NOT add the protected site itself here. This is deliberately
        # limited to verification infrastructure.
        for challenge_filter in (
            # Cloudflare Turnstile / managed challenge resources.
            r"^https?://challenges\.cloudflare\.com/",
            # First-party Cloudflare challenge endpoints on protected sites.
            r"^https?://[^/]+/cdn-cgi/challenge-platform/",
            r"^https?://[^/]+/cdn-cgi/turnstile/",
            r"^https?://[^/]+/cdn-cgi/challenge/",
            # Common CAPTCHA infrastructure used by verification pages.
            r"^https?://www\.google\.com/recaptcha/",
            r"^https?://www\.gstatic\.com/recaptcha/",
            r"^https?://hcaptcha\.com/",
            r"^https?://[^/]+\.hcaptcha\.com/",
        ):
            add({
                "trigger": {
                    "url-filter": challenge_filter
                },
                "action": {
                    "type": "ignore-previous-rules"
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
        # PRIVACY TEST SITE COMPATIBILITY
        # --------------------------------------------------
        # Keep these late in the rule list. WebKit's
        # ignore-previous-rules action only cancels matching rules
        # that were added before this point. This allows privacy
        # test pages to complete without weakening filtering globally.

        for site in (
            "amiunique\\.org",
            "coveryourtracks\\.eff\\.org",
        ):
            add({
                "trigger": {
                    "url-filter": site
                },
                "action": {
                    "type": "ignore-previous-rules"
                }
            })

        # --------------------------------------------------
        # Automatic compatibility for known video-heavy publishers.
        # IMPORTANT: This is a site-scoped fallback, not real-time detection.
        # ignore-previous-rules cancels prior blocking actions for requests
        # made by these documents. This preserves filtering on other sites,
        # including adblock-tester.com, but relaxes it on these publishers.
        # Must appear AFTER imported EasyList and built-in block rules.
        # --------------------------------------------------
        add({
            "trigger": {
                "url-filter": ".*",
                "if-domain": cls._media_compat_domains(),
            },
            "action": {"type": "ignore-previous-rules"},
        })

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
        # Yandex.Metrica hard blocks (v15.15)
        # --------------------------------------------------
        # Keep these after all compatibility exceptions so an earlier
        # ignore-previous-rules action cannot cancel these blocks.
        # Simple literal-host patterns avoid WebKit regex disjunctions.
        # These match the exact hosts seen in adblock-tester diagnostics.
        for yandex_host in (
            r"mc\.yandex\.ru/",
            r"mc\.yandex\.com/",
            r"mc\.yandex\.by/",
            r"mc\.yandex\.kz/",
            r"mc\.yandex\.uz/",
            r"an\.yandex\.ru/",
        ):
            add({
                "trigger": {"url-filter": yandex_host},
                "action": {"type": "block"},
            })

        # DW compatibility: retain every network block and all other sites'
        # cosmetic rules, but prevent cosmetic CSS from targeting DW pages.
        # This runs after built-in and imported EasyList rules are assembled.
        for rule in rules:
            if rule.get("action", {}).get("type") != "css-display-none":
                continue
            trigger = rule.get("trigger", {})
            # WebKit allows only ONE of if-domain/unless-domain/
            # if-top-url/unless-top-url per trigger. A domain-scoped
            # cosmetic rule already has its own condition: never add another.
            if any(key in trigger for key in ("if-domain", "if-top-url", "unless-top-url")):
                continue
            excluded = list(trigger.get("unless-domain", []))
            for domain in ("dw.com", "*dw.com"):
                if domain not in excluded:
                    excluded.append(domain)
            trigger["unless-domain"] = excluded

        # Site protection: TRUSTED is a deliberate compatibility bypass.
        # This must be the LAST compiled rule: WebKit's ignore-previous-rules
        # cancels preceding network and cosmetic actions on DW documents.
        # Other sites (including CNN and GameSpot) remain unchanged.
        trusted_domains = [
            domain
            for domain, mode in cls.SITE_PROTECTION.items()
            if mode == "TRUSTED"
        ]
        if trusted_domains:
            add({
                "trigger": {
                    "url-filter": ".*",
                    "if-domain": [
                        item for domain in trusted_domains
                        for item in (domain, "*" + domain)
                    ],
                },
                "action": {"type": "ignore-previous-rules"},
            })
            print("[Rules] TRUSTED compatibility bypass: " + ", ".join(trusted_domains), flush=True)

        # Fail early with a precise error rather than passing an invalid
        # rule list to WebKit (which would disable the entire adblocker).
        conditions = ("if-domain", "unless-domain", "if-top-url", "unless-top-url")
        for index, rule in enumerate(rules):
            trigger = rule.get("trigger", {})
            present = [key for key in conditions if key in trigger]
            if len(present) > 1:
                raise ValueError(f"Invalid WebKit rule {index}: conflicting trigger conditions {present}")

        return json.dumps(rules)
