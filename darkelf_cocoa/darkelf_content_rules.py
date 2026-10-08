import time
import os
import json
import re
import hashlib

from WebKit import WKContentRuleListStore
from Foundation import (NSURL, NSMutableURLRequest, NSURLSession, NSURLSessionConfiguration)


class ContentRuleManager:
    _rule_list = None
    _loaded = False

    # --------------------------------------------------
    # Versioning
    # --------------------------------------------------
    VERSION = "15.05"
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
    /* Conservative generic cosmetics: avoid broad class/data selectors
       that can hide legitimate layout, navigation, and challenge UI. */
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

        return json.dumps(rules)
