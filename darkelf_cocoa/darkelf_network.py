import os
import re
import time
import hashlib

from collections import deque
from urllib.parse import urlparse

from .darkelf_pq import (
    darkelf_pq_chain,
)

from .darkelf_utils import (
    _pq_normalize_url,
)


# ============================================================
# Darkelf Network Policy
# ============================================================

class DarkelfNetworkPolicy:

    def __init__(self, browser):

        self.browser = browser

    # --------------------------------------------------------
    # Main inspection
    # --------------------------------------------------------

    def inspect(
        self,
        url,
        nav_type
    ):

        url = str(url or "")

        decision = "allow"

        meta = {
            "source": "net_policy",
            "type": str(nav_type),
        }

        # ------------------------------------------------
        # HARD SKIP
        # ------------------------------------------------

        if url.startswith(("data:", "blob:")):
            return decision, meta

        # ------------------------------------------------
        # Parse URL
        # ------------------------------------------------

        try:

            parsed = urlparse(url)

            host = parsed.hostname or ""
            path = parsed.path or ""

        except Exception as e:

            print("[URL PARSE ERROR]", e)

            return "degrade", meta

        # ------------------------------------------------
        # VERIFICATION / CHALLENGE COMPATIBILITY
        # ------------------------------------------------
        # These requests must remain untouched by PQ replay/degrade logic.
        # Content rules still control ordinary ads/trackers; this bypass is
        # deliberately limited to challenge infrastructure.
        challenge_hosts = (
            "challenges.cloudflare.com",
            "hcaptcha.com",
            "www.hcaptcha.com",
            "newassets.hcaptcha.com",
            "imgs.hcaptcha.com",
            "www.google.com",
            "www.gstatic.com",
        )

        is_challenge_host = (
            host in challenge_hosts
            or host.endswith(".hcaptcha.com")
        )

        is_challenge_path = (
            path.startswith("/cdn-cgi/challenge-platform/")
            or path.startswith("/cdn-cgi/turnstile/")
            or path.startswith("/cdn-cgi/challenge/")
            or path.startswith("/recaptcha/")
        )

        if is_challenge_host or is_challenge_path:
            meta["challenge_passthrough"] = True
            return "allow", meta

        # ------------------------------------------------
        # HTTP → HTTPS upgrade
        # ------------------------------------------------

        if parsed.scheme == "http":

            return (
                "redirect",
                url.replace(
                    "http://",
                    "https://",
                    1
                ),
            )

        # ------------------------------------------------
        # Tracker blocking
        # ------------------------------------------------

        BLOCKED_DOMAINS = {
            "google-analytics.com",
            "doubleclick.net",
            "googlesyndication.com",
        }

        if any(
            host == d or host.endswith("." + d)
            for d in BLOCKED_DOMAINS
        ):

            return "block"

        # ------------------------------------------------
        # Quiet mode
        # ------------------------------------------------

        if (
            isinstance(nav_type, str)
            and nav_type.lower()
            in (
                "image",
                "media",
                "font",
            )
        ):

            return decision, meta

        # ------------------------------------------------
        # Resolve active tab
        # ------------------------------------------------

        tab = None

        if (
            hasattr(self.browser, "tabs")
            and 0 <= getattr(
                self.browser,
                "active",
                -1
            ) < len(self.browser.tabs)
        ):

            tab = self.browser.tabs[self.browser.active]

        if not tab or not getattr(tab, "view", None):

            return decision, meta

        # ------------------------------------------------
        # Initialize PQ state
        # ------------------------------------------------

        if not getattr(tab, "_pq_seed", None):

            tab._pq_seed = hashlib.sha256(
                os.urandom(32)
            ).digest()

            tab._pq_seed_locked = True

        if not hasattr(tab, "_pq_counter"):
            tab._pq_counter = 0

        if not hasattr(tab, "_pq_chain_seen"):

            tab._pq_chain_seen = deque(maxlen=200)

        # ------------------------------------------------
        # Canonical URL
        # ------------------------------------------------

        try:

            norm_path = re.sub(
                r"/+",
                "/",
                path
            )

            query = (
                "&".join(
                    sorted(parsed.query.split("&"))
                )
                if parsed.query
                else ""
            )

            norm_url = (
                f"{parsed.scheme}://"
                f"{parsed.netloc}"
                f"{norm_path}?{query}"
            )

        except Exception:

            norm_url = url

        # ------------------------------------------------
        # Counter
        # ------------------------------------------------

        tab._pq_counter = min(
            tab._pq_counter + 1,
            1_000_000
        )

        # ------------------------------------------------
        # PQ Chain
        # ------------------------------------------------

        try:

            chain = darkelf_pq_chain(
                self.browser,
                norm_url
            )

            meta["_pq_chain"] = (
                chain[:16].hex()
            )

            if chain in tab._pq_chain_seen:

                if hasattr(self.browser, "miniAI"):

                    self.browser.miniAI.suspicious_hits += 2

                    decision = "degrade"

            tab._pq_chain_seen.append(chain)

        except Exception as e:

            print("[PQ CHAIN ERROR]", e)

            return "degrade", meta

        # ------------------------------------------------
        # PQ Fingerprint
        # ------------------------------------------------

        try:

            h = hashlib.sha3_256()

            h.update(tab._pq_seed)

            h.update(host.encode())

            h.update(norm_path[:32].encode())

            if hasattr(
                self.browser,
                "_pq_tls_summary"
            ):

                h.update(
                    self.browser._pq_tls_summary.encode()
                )

            digest = h.digest()

            if digest[0] & 1:

                pq_bytes = hashlib.sha3_512(
                    tab._pq_seed
                ).digest()

                meta["_pq_fp"] = (
                    pq_bytes[:32].hex()
                )

        except Exception as e:

            print("[PQ FP ERROR]", e)

            return "degrade", meta

        # ------------------------------------------------
        # Adaptive enforcement
        # ------------------------------------------------

        try:

            if hasattr(self.browser, "miniAI"):

                stats = (
                    self.browser.miniAI._pq_stats()
                )

                if stats["risk_level"] == "high":

                    decision = "isolate"

                    meta.pop("_pq_fp", None)
                    meta.pop("_pq_fp_alt", None)

                elif stats["risk_level"] == "medium":

                    decision = "degrade"

        except Exception as e:

            print("[ADAPTIVE ERROR]", e)

        # ------------------------------------------------
        # Tracker deception
        # ------------------------------------------------

        try:

            if "_pq_fp" in meta and host:

                first_party = getattr(
                    self.browser,
                    "current_url_for_fpi",
                    "",
                )

                is_third_party = False

                if first_party:

                    fp_host = (
                        urlparse(first_party).hostname
                        or ""
                    )

                    if (
                        fp_host
                        and not host.endswith(fp_host)
                    ):

                        is_third_party = True

                if is_third_party:

                    d = hashlib.sha3_256(
                        tab._pq_seed
                        + host.encode()
                    ).digest()

                    mode = d[1] % 3

                    real_fp = meta["_pq_fp"]

                    # decoy
                    if mode == 0:

                        decoy = hashlib.sha3_256(
                            (
                                real_fp + host
                            ).encode()
                        ).digest()

                        meta["_pq_fp_alt"] = (
                            decoy[:8].hex()
                        )

                    # partial real
                    elif mode == 1:

                        meta["_pq_fp_alt"] = (
                            real_fp[:8]
                        )

                    # alternate
                    else:

                        alt = hashlib.sha3_256(
                            (
                                host + real_fp
                            ).encode()
                        ).digest()

                        meta["_pq_fp_alt"] = (
                            alt[:8].hex()
                        )

        except Exception as e:

            print("[DECEPTION ERROR]", e)

        # ------------------------------------------------
        # Degraded mode
        # ------------------------------------------------

        if decision == "degrade":

            meta["_trust"] = "low"

            meta.pop("_pq_fp", None)

            meta["_no_3p_credentials"] = True

            meta["_cache_mode"] = "ephemeral"

        # ------------------------------------------------
        # Soft rotation
        # ------------------------------------------------

        if tab._pq_counter > 5000:

            tab._pq_seed = hashlib.sha3_256(
                tab._pq_seed
            ).digest()

            tab._pq_counter = 0

            tab._pq_chain_seen.clear()

        return decision, meta
