import os
import time
import hashlib
import threading
import shutil
import base64
import re
import objc
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from Foundation import (
    NSURL, NSURLRequest, NSData, NSOperationQueue, NSTimer,
    NSURLSession, NSURLSessionConfiguration,
    NSURLAuthenticationMethodServerTrust,
    NSURLSessionAuthChallengeUseCredential,
    NSURLCredential,
    NSURLSessionAuthChallengePerformDefaultHandling,
)
from Cocoa import NSObject
from AppKit import NSAlert, NSColor, NSFocusRingTypeNone, NSMakeRect, NSImage
from WebKit import (
    WKNavigationActionPolicyAllow, WKNavigationActionPolicyCancel,
    WKNavigationResponsePolicyAllow, WKNavigationResponsePolicyDownload,
)
from Security import (
    SecTrustEvaluateWithError, SecTrustGetCertificateAtIndex,
    SecCertificateCopySubjectSummary,
)

from .darkelf_pq import darkelf_is_pq_active
from .darkelf_utils import (
    log, darkelf_sha3_bytes, _randomized_filename, _safe_download_dir,
)
from .darkelf_downloads import DownloadProgressView
from .darkelf_theme import load_accent_rgba

HOME_URL = "darkelf://home"
_favicon_cache = {}

# Browser identity policy:
# - YouTube keeps Darkelf's original generic WebKit UA.
# - Other HTTP(S) sites receive a complete Safari-compatible UA for compatibility.
# Locale preference is US English on all main-frame HTTP(S) navigations.
DARKELF_WEBKIT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko)"
)
SAFARI_COMPAT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/27.0.1 Safari/605.1.15"
)
US_ACCEPT_LANGUAGE = "en-US,en;q=0.9"

# Favicon handling: prefer page-context requests (which share WKWebView cookies)
# over independent NSURLSession requests that may receive bot-challenge HTML.
_FAVICON_MAX_BYTES = 1024 * 1024


def _favicon_log(message):
    """Minimal diagnostic output; no cookies or full query strings."""
    if os.environ.get("DARKELF_FAVICON_DEBUG") == "1":
        print(f"[Darkelf Favicon] {message}", flush=True)


def _favicon_from_bytes(data):
    """Decode only recognized raster image data, never challenge HTML."""
    if data is None:
        _favicon_log("decode: no data")
        return None
    raw = bytes(data)
    if not raw or len(raw) > _FAVICON_MAX_BYTES:
        _favicon_log(f"decode: invalid size ({len(raw)} bytes)")
        return None
    recognized = (raw.startswith(b"\x89PNG\r\n\x1a\n")
                  or raw.startswith(b"\x00\x00\x01\x00")
                  or raw.startswith(b"GIF8")
                  or raw.startswith(b"\xff\xd8\xff")
                  or (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"))
    if not recognized:
        _favicon_log(f"decode: unsupported image signature ({len(raw)} bytes)")
        return None
    try:
        nsdata = NSData.dataWithBytes_length_(raw, len(raw))
        icon = NSImage.alloc().initWithData_(nsdata)
        if icon is None or not icon.isValid():
            _favicon_log("decode: NSImage rejected image")
            return None
        _favicon_log(f"decode: success ({len(raw)} bytes)")
        return icon
    except Exception as exc:
        _favicon_log(f"decode: exception {type(exc).__name__}: {exc}")
        return None


def fetch_favicon(host, callback):
    """Legacy HTTPS /favicon.ico fallback, with strict image validation."""
    if not host:
        callback(None)
        return
    if host in _favicon_cache:
        callback(_favicon_cache[host])
        return
    fetch_favicon_url(f"https://{host}/favicon.ico", host, callback)


def fetch_favicon_url(url, expected_host, callback):
    """Retrieve a same-site HTTPS icon using an ephemeral native request."""
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        expected = (expected_host or "").lower()
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or not expected or not (host == expected or host.endswith("." + expected))):
            _favicon_log(f"native: rejected icon origin for {expected_host}")
            callback(None)
            return
        nsurl = NSURL.URLWithString_(url)
        if nsurl is None:
            callback(None)
            return
        session = NSURLSession.sessionWithConfiguration_(
            NSURLSessionConfiguration.ephemeralSessionConfiguration()
        )

        def done(data, response, error):
            icon = None
            try:
                status = int(response.statusCode()) if response else 0
                mime = str(response.MIMEType() or "").lower() if response else ""
                _favicon_log(f"native: host={expected_host} status={status} mime={mime} error={bool(error)}")
                if error is None and status == 200 and (mime.startswith("image/") or mime == "application/octet-stream"):
                    icon = _favicon_from_bytes(data)
            except Exception as exc:
                _favicon_log(f"native: exception {type(exc).__name__}: {exc}")
            NSOperationQueue.mainQueue().addOperationWithBlock_(lambda: callback(icon))

        session.dataTaskWithURL_completionHandler_(nsurl, done).resume()
    except Exception:
        callback(None)


def fetch_favicon_in_page(webview, expected_host, callback):
    """Diagnose and load favicon in WKWebView's current first-party session.

    No new cross-origin network requests are made. Logs show icon candidates,
    HTTP failures, decoding failures, and JavaScript callback errors.
    """
    js = r"""
    (function () {
      window.__darkelfFaviconProbe = {state:"pending"};
      (async function () {
      const MAX = 1048576;
      const report = {status:'none', candidates:[], attempts:[], data:''};
      try {
        const page = new URL(location.href);
        if (page.protocol !== 'https:') {report.status='not-https'; return report;}
        const links = [...document.querySelectorAll('link[rel][href]')]
          .filter(el => /(^|\s)(icon|apple-touch-icon)(\s|$)/i.test(el.rel))
          .map(el => ({url: el.href, type: (el.type || '').toLowerCase(),
                       sizes: (el.sizes && el.sizes.value) || ''}));
        links.sort((a,b) => {
          const rank = x => (x.type.includes('png') ? 0 :
            x.type.includes('icon') ? 1 : x.type.includes('svg') ? 3 : 2);
          return rank(a)-rank(b);
        });
        links.push({url: new URL('/favicon.ico', page).href, type: ''});
        report.candidates = links.slice(0, 12).map(x => {
          try {const u=new URL(x.url); return u.origin+u.pathname+' ('+x.type+')';}
          catch(_) {return 'invalid-url';}
        });
        for (const item of links.slice(0, 12)) {
          let url;
          try {url = new URL(item.url);} catch (_) {continue;}
          const label = url.origin + url.pathname;
          if (url.protocol !== 'https:' || url.origin !== page.origin) {
            report.attempts.push(label + ': skipped-cross-origin');
            continue;
          }
          try {
            const response = await fetch(url.href, {
              credentials: 'same-origin', mode: 'same-origin',
              cache: 'force-cache', redirect: 'follow'
            });
            const mime = (response.headers.get('content-type') || '').toLowerCase();
            if (!response.ok) {
              report.attempts.push(label + ': HTTP ' + response.status); continue;
            }
            if (!(mime.startsWith('image/') || mime.startsWith('application/octet-stream'))) {
              report.attempts.push(label + ': wrong MIME ' + mime); continue;
            }
            if (mime.includes('svg')) {
              report.attempts.push(label + ': SVG not decoded'); continue;
            }
            const blob = await response.blob();
            if (!blob.size || blob.size > MAX) {
              report.attempts.push(label + ': invalid size ' + blob.size); continue;
            }
            const data = await new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onload = () => resolve(reader.result);
              reader.onerror = () => reject(new Error('FileReader failed'));
              reader.readAsDataURL(blob);
            });
            report.data = data;
            report.status = 'image-found';
            report.attempts.push(label + ': fetched ' + blob.size + ' bytes');
            return report;
          } catch (err) {
            report.attempts.push(label + ': ' + String(err).slice(0, 90));
          }
        }
        report.status = 'no-decodable-same-origin-icon';
      } catch (err) {report.status='exception: '+String(err).slice(0,120);}
      return report;
      })().then(result => { window.__darkelfFaviconProbe = {state:"done", result:result}; })
          .catch(err => { window.__darkelfFaviconProbe = {state:"error", error:String(err)}; });
      return "started";
    })()
    """

    # WKWebView.evaluateJavaScript does not reliably marshal Promises into
    # Objective-C. Start the asynchronous operation in-page, then poll for a
    # JSON *string* (not a Promise or JavaScript object).
    import json

    def finish_result(value):
        icon = None
        try:
            result = value.get("result") or {}
            _favicon_log(f"page: {expected_host} status={result.get('status')}")
            for candidate in (result.get('candidates') or [])[:12]:
                _favicon_log(f"candidate: {candidate}")
            for attempt in (result.get('attempts') or [])[:12]:
                _favicon_log(f"attempt: {attempt}")
            data = result.get('data', '')
            if isinstance(data, str) and (data.startswith('data:image/') or
                                          data.startswith('data:application/octet-stream;')):
                encoded = data.partition(',')[2]
                if len(encoded) <= ((_FAVICON_MAX_BYTES * 4 // 3) + 100):
                    icon = _favicon_from_bytes(base64.b64decode(encoded, validate=True))
        except Exception as exc:
            _favicon_log(f"page: decode exception {type(exc).__name__}: {exc}")
        callback(icon)

    poll_js = "JSON.stringify(window.__darkelfFaviconProbe || {state:'missing'})"

    def poll(attempt=0):
        def checked(value, error):
            if error:
                _favicon_log(f"page: polling error for {expected_host}: {error}")
                callback(None)
                return
            try:
                result = json.loads(str(value))
            except Exception as exc:
                _favicon_log(f"page: invalid polling result: {exc}")
                callback(None)
                return
            state = result.get('state')
            if state == 'done':
                finish_result(result)
            elif state == 'error':
                _favicon_log(f"page: script error: {result.get('error')}")
                callback(None)
            elif attempt >= 24 or state == 'missing':
                _favicon_log(f"page: timed out or navigated away for {expected_host}")
                callback(None)
            else:
                def schedule():
                    NSOperationQueue.mainQueue().addOperationWithBlock_(lambda: poll(attempt + 1))
                timer = threading.Timer(0.25, schedule)
                timer.daemon = True
                timer.start()
        try:
            webview.evaluateJavaScript_completionHandler_(poll_js, checked)
        except Exception as exc:
            _favicon_log(f"page: polling exception: {exc}")
            callback(None)

    def started(value, error):
        if error:
            _favicon_log(f"page: JS start error for {expected_host}: {error}")
            callback(None)
        else:
            poll()

    try:
        _favicon_log(f"page: starting favicon discovery for {expected_host}")
        webview.evaluateJavaScript_completionHandler_(js, started)
    except Exception as exc:
        _favicon_log(f"page: evaluation exception {type(exc).__name__}: {exc}")
        callback(None)


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

# ============================================================
# UI Delegate
# ============================================================

class _UIDelegate(NSObject):

    # --------------------------------------------------------
    # Init
    # --------------------------------------------------------

    def initWithOwner_(self, owner):

        self = (
            objc.super(
                _UIDelegate,
                self
            ).init()
        )

        if self is None:
            return None

        self.owner = owner

        return self

    # --------------------------------------------------------
    # Popup handling
    # --------------------------------------------------------

    def webView_createWebViewWithConfiguration_forNavigationAction_windowFeatures_(
        self,
        webView,
        configuration,
        navigationAction,
        windowFeatures
    ):

        try:

            req = navigationAction.request()

            if req:

                print(
                    "[UIDelegate] Popup redirected to same tab"
                )

                webView.loadRequest_(req)

        except Exception as e:

            print(
                "[UIDelegate] Popup handling error:",
                e
            )

        return None

    # --------------------------------------------------------
    # JS Alert
    # --------------------------------------------------------

    def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_completionHandler_(
        self,
        webView,
        message,
        frame,
        completionHandler
    ):

        try:

            print(f"[JS Alert] {message}")

            alert = NSAlert.alloc().init()

            alert.setMessageText_(
                "JavaScript Alert"
            )

            alert.setInformativeText_(
                str(message)
            )

            alert.addButtonWithTitle_("OK")

            alert.runModal()

        finally:

            completionHandler()

    # --------------------------------------------------------
    # JS Confirm
    # --------------------------------------------------------

    def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_completionHandler_(
        self,
        webView,
        message,
        frame,
        completionHandler
    ):

        try:

            print(f"[JS Confirm] {message}")

            alert = NSAlert.alloc().init()

            alert.setMessageText_("Confirm")

            alert.setInformativeText_(
                str(message)
            )

            alert.addButtonWithTitle_("OK")

            alert.addButtonWithTitle_("Cancel")

            result = alert.runModal()

            completionHandler(result == 1000)

        except Exception as e:

            print(
                "[JS Confirm] Error:",
                e
            )

            completionHandler(False)

    # --------------------------------------------------------
    # JS Prompt
    # --------------------------------------------------------

    def webView_runJavaScriptTextInputPanelWithPrompt_defaultText_initiatedByFrame_completionHandler_(
        self,
        webView,
        prompt,
        defaultText,
        frame,
        completionHandler
    ):

        try:

            print(f"[JS Prompt] {prompt}")

            completionHandler(None)

        except Exception as e:

            print(
                "[JS Prompt] Error:",
                e
            )

            completionHandler(None)

    # --------------------------------------------------------
    # Media permissions
    # --------------------------------------------------------

    def webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_(
        self,
        webView,
        origin,
        frame,
        type,
        decisionHandler
    ):

        try:

            print(
                f"[Media] 🔒 Denied media capture for: {origin}"
            )

            decisionHandler(0)

        except Exception:
            pass

    # --------------------------------------------------------
    # Fullscreen enter
    # --------------------------------------------------------

    def webView_enterFullScreenForFrame_completionHandler_(
        self,
        webView,
        frame,
        completionHandler
    ):

        try:

            print(
                "[UIDelegate] WebKit video fullscreen"
            )

            webView.setFrame_(
                webView.window().contentView().bounds()
            )

            webView.setAutoresizingMask_(18)

        except Exception as e:

            print(
                "[UIDelegate] fullscreen error:",
                e
            )

        completionHandler(True)

    # --------------------------------------------------------
    # Fullscreen exit
    # --------------------------------------------------------

    def webView_exitFullScreenForFrame_completionHandler_(
        self,
        webView,
        frame,
        completionHandler
    ):

        print(
            "[UIDelegate] exit video fullscreen"
        )

        completionHandler(True)


# ============================================================
# Navigation Delegate
# ============================================================

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
                            # Resolve icon inside the actual WKWebView first:
                            # page cookies/session can satisfy protected sites.
                            requested_host = str(tab.host)
                            if scheme == "https" and requested_host and requested_host != tab.favicon_host:
                                # Prevent repeated parallel lookups on a single tab.
                                if getattr(tab, "_favicon_pending_host", None) != requested_host:
                                    tab._favicon_pending_host = requested_host

                                    def icon_ready(icon, tab=tab, browser=browser, host=requested_host):
                                        if getattr(tab, "_favicon_pending_host", None) == host:
                                            tab._favicon_pending_host = None
                                        if str(getattr(tab, "host", "")) != host:
                                            return
                                        _favicon_log(f"tab: {host} result={'success' if icon is not None else 'missing'}")
                                        if icon is not None:
                                            tab.favicon = icon
                                            tab.favicon_host = host
                                            _favicon_cache[host] = icon
                                            browser._update_tab_buttons()

                                    if requested_host in _favicon_cache:
                                        icon_ready(_favicon_cache[requested_host])
                                    else:
                                        def page_icon_ready(icon, tab=tab, host=requested_host):
                                            if icon is not None:
                                                icon_ready(icon)
                                            elif str(getattr(tab, "host", "")) == host:
                                                # A native request is a last resort; it
                                                # may be challenged by Cloudflare.
                                                fetch_favicon(host, icon_ready)

                                        fetch_favicon_in_page(tab.view, requested_host, page_icon_ready)

                    break

            browser._update_tab_buttons()
            browser._sync_addr()
            browser.refreshBookmarkButton()
            browser._update_navigation_button_states()

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
            accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(
                *load_accent_rgba()
            )
            browser.addr.layer().setBorderColor_(accent.CGColor())
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
            if message.name() == "darkelfLinkPreview":
                owner = getattr(self, "owner", None)
                if owner is not None:
                    owner._show_link_preview(message.body(), message.webView())
                return


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

                file_hasher = hashlib.sha3_512()
                with open(self._download_path, "rb") as f:
                    while True:
                        chunk = f.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break
                        file_hasher.update(chunk)

                base_hash = file_hasher.hexdigest()
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
            # Browser identity + global US-English locale
            # -------------------------------------------------
            # YouTube deliberately keeps Darkelf's original generic WebKit UA.
            # Other HTTP(S) main-frame navigations use a complete Safari-style UA
            # for sites that reject incomplete/unknown WebKit identities.
            #
            # Accept-Language is applied to every HTTP(S) main-frame request.
            # Google/YouTube additionally keep their existing hl/gl URL hints.
            try:
                target_frame = navAction.targetFrame()
                is_main_frame = bool(target_frame and target_frame.isMainFrame())
            except Exception:
                is_main_frame = False

            if is_main_frame and scheme in ("http", "https"):
                try:
                    parsed = urlsplit(url_str)
                    host_l = (parsed.hostname or "").lower()
                    is_youtube = host_l == "youtube.com" or host_l.endswith(".youtube.com")
                    desired_ua = DARKELF_WEBKIT_UA if is_youtube else SAFARI_COMPAT_UA

                    # WKWebView's UA is view-wide. Change it only when the destination
                    # requires a different identity, so YouTube <-> other-site
                    # navigation cannot leave the previous site's UA behind.
                    current_ua = getattr(webView, "_darkelf_effective_ua", None)
                    if current_ua != desired_ua:
                        webView.setCustomUserAgent_(desired_ua)
                        try:
                            webView._darkelf_effective_ua = desired_ua
                        except Exception:
                            pass

                    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
                    changed_url = False

                    if is_youtube:
                        if query.get("hl") != "en":
                            query["hl"] = "en"
                            changed_url = True
                        if query.get("gl") != "US":
                            query["gl"] = "US"
                            changed_url = True
                    elif (
                        host_l in ("google.com", "www.google.com")
                        and parsed.path in ("", "/", "/search", "/webhp")
                    ):
                        if query.get("hl") != "en":
                            query["hl"] = "en"
                            changed_url = True
                        if query.get("gl") != "us":
                            query["gl"] = "us"
                            changed_url = True

                    current_language = req.valueForHTTPHeaderField_("Accept-Language")
                    needs_language = str(current_language or "") != US_ACCEPT_LANGUAGE

                    # One replacement request handles both locale URL normalization
                    # and the global main-frame Accept-Language header. Restrict the
                    # replacement to GET/HEAD so form submissions are never replayed.
                    method = str(req.HTTPMethod() or "GET").upper()
                    if (changed_url or needs_language) and method in ("GET", "HEAD"):
                        localized_request = req.mutableCopy()
                        if changed_url:
                            localized_url = urlunsplit((
                                parsed.scheme,
                                parsed.netloc,
                                parsed.path,
                                urlencode(query),
                                parsed.fragment,
                            ))
                            localized_request.setURL_(NSURL.URLWithString_(localized_url))
                        localized_request.setValue_forHTTPHeaderField_(
                            US_ACCEPT_LANGUAGE, "Accept-Language"
                        )
                        webView.loadRequest_(localized_request)
                        decisionHandler(WKNavigationActionPolicyCancel)
                        return
                except Exception as e:
                    log(2, "[Identity/Locale] main-frame normalization:", e)

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
