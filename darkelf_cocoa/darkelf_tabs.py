from Cocoa import *
from AppKit import *
from Foundation import *
from WebKit import WKWebView, WKWebsiteDataStore
import threading
from dataclasses import dataclass

def log(level, *msg):
    if level <= 1:
        print(*msg)

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

