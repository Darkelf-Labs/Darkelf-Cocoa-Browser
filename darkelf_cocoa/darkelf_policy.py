# Darkelf local response-policy configuration.
# Extracted from current browser.py.

DARKELF_DISABLE_COOKIE_SCRUBBER = False

DARKELF_DISABLE_JS_HANDLERS = False

DARKELF_DISABLE_RESIZE_HANDLER = False

ENABLE_LOCAL_CSP = False

LOCAL_CSP_VALUE = (
    "worker-src 'self' blob:; manifest-src 'self'; form-action 'self' https:;"
)

ENABLE_LOCAL_HSTS = True

LOCAL_HSTS_VALUE = "max-age=63072000; includeSubDomains; preload"

ENABLE_LOCAL_REFERRER_POLICY = True

LOCAL_REFERRER_POLICY_VALUE = "strict-origin-when-cross-origin"

ENABLE_LOCAL_WEBSOCKET_POLICY = True

LOCAL_WEBSOCKET_POLICY_VALUE = (
    "connect-src 'self' https: wss: "
    "https://*.googlevideo.com "
    "https://youtubei.googleapis.com "
    "https://*.youtube.com "
    "https://i.ytimg.com "
    "https://www.youtube.com;"
)

