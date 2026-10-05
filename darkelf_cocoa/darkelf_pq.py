import os
import re
import time
import hashlib

from collections import deque
from urllib.parse import urlparse

from darkelf_utils import _pq_normalize_url


# ============================================================
# PQ FINGERPRINT
# ============================================================

def darkelf_pq_fingerprint(
    url: str,
    headers: dict = None,
    owner=None
) -> str:

    h = hashlib.sha3_512()

    # canonical URL
    norm_url = _pq_normalize_url(url)

    h.update(
        norm_url.encode(
            "utf-8",
            errors="ignore"
        )
    )

    # canonical headers
    if headers:

        for k, v in sorted(headers.items()):

            if k.lower().startswith("_pq"):
                continue

            h.update(str(k).lower().encode())
            h.update(str(v).encode())

    # anti-replay bucket
    bucket = int(time.time() // 10)

    h.update(
        bucket.to_bytes(8, "big")
    )

    # session salt
    if owner and hasattr(owner, "_pq_salt"):

        h.update(owner._pq_salt)

    # TLS binding
    if owner and hasattr(owner, "_pq_tls_summary"):

        h.update(
            owner._pq_tls_summary.encode()
        )

    return h.hexdigest()


# ============================================================
# PQ CHAIN
# ============================================================

def darkelf_pq_chain(owner, url: str) -> bytes:

    # ------------------------------------------------
    # resolve active tab
    # ------------------------------------------------

    tab = None

    if (
        hasattr(owner, "tabs")
        and 0 <= getattr(owner, "active", -1) < len(owner.tabs)
    ):
        tab = owner.tabs[owner.active]

    # no identity
    if not tab or not getattr(tab, "_pq_seed", None):

        return b"\x00" * 32

    # ------------------------------------------------
    # initialize state
    # ------------------------------------------------

    if not hasattr(tab, "_pq_counter"):
        tab._pq_counter = 0

    if not hasattr(tab, "_pq_prev_chain"):
        tab._pq_prev_chain = b"\x00" * 64

    if not hasattr(tab, "_pq_chain_seen"):
        tab._pq_chain_seen = deque(maxlen=200)

    # ------------------------------------------------
    # increment counter
    # ------------------------------------------------

    tab._pq_counter = min(
        tab._pq_counter + 1,
        1_000_000
    )

    # ------------------------------------------------
    # build chain hash
    # ------------------------------------------------

    h = hashlib.sha3_512()

    # session root
    h.update(tab._pq_seed)

    # canonical URL
    norm_url = _pq_normalize_url(url)

    h.update(
        norm_url.encode(
            "utf-8",
            errors="ignore"
        )
    )

    # previous chain
    h.update(tab._pq_prev_chain)

    # counter
    h.update(
        tab._pq_counter.to_bytes(8, "big")
    )

    # optional salt binding
    if hasattr(owner, "_pq_salt"):

        h.update(owner._pq_salt)

    # ------------------------------------------------
    # finalize
    # ------------------------------------------------

    chain = h.digest()

    # ------------------------------------------------
    # replay detection
    # ------------------------------------------------

    if chain in tab._pq_chain_seen:

        if hasattr(owner, "miniAI"):
            owner.miniAI.suspicious_hits += 2

    tab._pq_chain_seen.append(chain)

    # ------------------------------------------------
    # update state
    # ------------------------------------------------

    tab._pq_prev_chain = chain

    return chain


# ============================================================
# CANVAS SEED
# ============================================================

def get_canvas_seed_hex(tab):

    if not hasattr(tab, "_pq_seed") or not tab._pq_seed:
        return "0000000000000000"

    bucket = darkelf_get_bucket(tab)

    h = hashlib.sha3_256()

    # identity
    h.update(tab._pq_seed)

    # grouping
    h.update(
        bucket.to_bytes(2, "big")
    )

    # read-only chain
    chain = getattr(
        tab,
        "_pq_prev_chain",
        b"\x00" * 32
    )

    h.update(chain[:16])

    return h.digest()[:16].hex()


# ============================================================
# BUCKETING
# ============================================================

def darkelf_get_bucket(
    tab,
    groups=32
):

    if hasattr(tab, "_pq_bucket"):
        return tab._pq_bucket

    seed = getattr(tab, "_pq_seed", None)

    if not seed:
        tab._pq_bucket = 0
        return 0

    digest = hashlib.sha3_256(seed).hexdigest()

    tab._pq_bucket = int(digest, 16) % groups

    return tab._pq_bucket


# ============================================================
# USER AGENT
# ============================================================

def darkelf_build_ua(tab) -> str:

    base = (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 "
        "(KHTML, like Gecko)"
    )

    seed = getattr(tab, "_pq_seed", None)

    if not seed:
        return base

    bucket = darkelf_get_bucket(tab)

    # internal grouping only
    tab._ua_bucket = bucket

    return base


# ============================================================
# TAB IDENTITY
# ============================================================

def darkelf_init_tab_identity(tab):

    if not tab:
        return

    # session seed
    if (
        not hasattr(tab, "_pq_seed")
        or not tab._pq_seed
    ):

        tab._pq_seed = hashlib.sha256(
            os.urandom(32)
        ).digest()

        tab._pq_seed_locked = True

    # user-agent
    if (
        not hasattr(tab, "_ua_string")
        or not tab._ua_string
    ):

        tab._ua_string = darkelf_build_ua(tab)


# ============================================================
# PQ STATUS
# ============================================================

def darkelf_is_pq_active(owner) -> bool:

    return (
        hasattr(owner, "_pq_seed")
        and bool(getattr(owner, "_pq_seed", None))
    )
