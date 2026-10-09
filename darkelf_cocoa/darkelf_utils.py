import os
import re
import time
import hashlib
import secrets

from urllib.parse import urlparse, unquote

LOG_LEVEL = 1

def log(level, *msg):
    if level <= LOG_LEVEL:
        print(*msg)


# -----------------------------------
# 🔒 URL SAFETY CHECK
# -----------------------------------

def is_safe_url(url: str) -> bool:
    try:
        u = urlparse(url)
        return u.scheme in ("http", "https")
    except Exception:
        return False


# ============================================================
# PQ URL NORMALIZATION
# ============================================================

def _pq_normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)

        path = re.sub(r"/+", "/", parsed.path or "/")

        query_items = sorted(
            [q for q in (parsed.query or "").split("&") if q]
        )

        query = "&".join(query_items)

        return f"{parsed.scheme}://{parsed.netloc}{path}?{query}"

    except Exception:
        return url or ""


# ============================================================
# HASH HELPERS
# ============================================================

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


# ============================================================
# DARKELF LIBRARY PATHS
# ============================================================

def _darkelf_library(create=False):

    desktop = os.path.join(
        os.path.expanduser("~"),
        "Desktop"
    )

    library = os.path.join(
        desktop,
        "Darkelf Library"
    )

    snaps = os.path.join(
        library,
        "Darkelf Snap"
    )

    temp = os.path.join(
        library,
        "Darkelf Temp"
    )

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


# ============================================================
# RANDOMIZED DOWNLOAD NAME
# ============================================================

def _randomized_filename(name):

    name = (name or "download").strip()

    name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        name
    )[:120]

    base, ext = os.path.splitext(name)

    token = secrets.token_hex(6)

    base = base[:60] or "download"
    ext = ext[:12]

    return f"{base}_{token}{ext}"
