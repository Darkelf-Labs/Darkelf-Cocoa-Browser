import tldextract

from urllib.parse import urlparse

from WebKit import WKWebsiteDataStore


# ============================================================
# Darkelf First Party Isolation (FPI)
# ============================================================

class FirstPartyIsolation:

    # domains allowed to share storage
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
    # Extract first-party domain
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

        # auth passthrough
        if host in self.AUTH_WHITELIST:
            return host

        try:

            ext = tldextract.extract(host)

            if ext.domain and ext.suffix:

                return f"{ext.domain}.{ext.suffix}"

        except Exception:
            pass

        return host

    # --------------------------------------------------------
    # Build isolation key
    # --------------------------------------------------------

    def _key(
        self,
        url,
        tab_uid=None,
        nonce=None
    ):

        domain = self._domain_key(url)

        if (
            self.tab_isolation
            and tab_uid is not None
        ):

            return f"{domain}@tab{tab_uid}-{nonce}"

        return domain

    # --------------------------------------------------------
    # Get storage container
    # --------------------------------------------------------

    def store_for(
        self,
        url,
        tab_uid=None,
        nonce=None
    ):

        key = self._key(
            url,
            tab_uid,
            nonce
        )

        print("[FPI] Using store:", key)

        # ensure store map exists
        if not hasattr(self, "_stores"):
            self._stores = {}

        # create store if missing
        if key not in self._stores:

            store = WKWebsiteDataStore.nonPersistentDataStore()

            # IMPORTANT:
            # Do NOT purge here
            # WebKit can segfault if aggressively purged
            self._stores[key] = store

        return self._stores[key]

    # --------------------------------------------------------
    # Clear one tab/domain store
    # --------------------------------------------------------

    def clear_tab(
        self,
        url,
        tab_uid=None,
        nonce=None
    ):

        key = self._key(
            url,
            tab_uid,
            nonce
        )

        if key in self._stores:

            try:

                del self._stores[key]

                print("[FPI] Cleared store:", key)

            except Exception as e:

                print("[FPI] Clear error:", e)

    # --------------------------------------------------------
    # Clear an exact store key
    # --------------------------------------------------------

    def clear_key(self, key):

        if key and key in self._stores:
            try:
                del self._stores[key]
                print("[FPI] Cleared exact store:", key)
            except Exception as e:
                print("[FPI] Clear exact-key error:", e)

    # --------------------------------------------------------
    # Clear all stores
    # --------------------------------------------------------

    def clear(self):

        self._stores.clear()
