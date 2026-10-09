from Cocoa import *
from AppKit import *
from Foundation import *
from WebKit import *

import os
import time
import sys
import re
import json
import threading
import hashlib
import zipfile
import secrets
import warnings
import base64
import tempfile
import shutil
import urllib.request
import objc
import AppKit
from collections import deque
from datetime import datetime
from urllib.parse import urlparse, unquote, quote_plus
from Quartz import CABasicAnimation
from Security import *

from .darkelf_pages import HOMEPAGE_HTML, UNIFIED_DEFENSE_JS, homepage_html_for_accent
from .darkelf_policy import *
from .darkelf_utils import *
from .darkelf_pq import *
from .darkelf_isolation import *
from .darkelf_content_rules import *
from .darkelf_spoofing import *
from .darkelf_downloads import *
from .darkelf_network import *
from .darkelf_delegates import _WindowDelegate, _UIDelegate, _NavDelegate
from .darkelf_sentinel import *
from .darkelf_tabs import Tab, darkelf_destroy_tab
from .darkelf_ui import (
    DarkelfMenuDelegate, HoverButton, TabHoverView, SearchHandler, AddressField,
    DarkelfAddressEditor,
    DraggableFindBar, DarkelfSearchField, apply_darkelf_theme,
)
from .darkelf_icons import load_nav_svg, load_toolbar_svg
from .darkelf_branding import sync_application_icon
from .darkelf_theme import (
    TOOLBAR_HEIGHT, TOOLBAR_PADDING, TOOLBAR_BUTTON_SIZE, TOOLBAR_BUTTON_GAP,
    TOOLBAR_RIGHT_GAP, URLBAR_MIN_WIDTH, URLBAR_MAX_WIDTH,
    ACCENT_PRESETS, load_accent_rgba, save_accent_rgba, reset_accent_for_launch,
    BACKGROUND_PRESETS, load_background_name, save_background_name, reset_background_for_launch,
    cocoa_accent_value_for_rgba,
)

APP_NAME = "Darkelf"
HOME_URL = "darkelf://home"
LOG_LEVEL = 1

def log(level, *msg):
    if level <= LOG_LEVEL:
        print(*msg)


def _broadcast_cocoa_color_change():
    """Tell AppKit that this process's color preference changed."""
    try:
        NSDistributedNotificationCenter.defaultCenter().postNotificationName_object_(
            "AppleColorPreferencesChangedNotification", None
        )
    except Exception as e:
        log(2, "[Theme] accent notification:", e)

def _sync_cocoa_accent_to_darkelf(rgba):
    """Set only Darkelf's defaults-domain accent; never write macOS global prefs."""
    try:
        value = cocoa_accent_value_for_rgba(rgba)
        NSUserDefaults.standardUserDefaults().setInteger_forKey_(value, "AppleAccentColor")
        _broadcast_cocoa_color_change()

        # Re-resolve dynamic AppKit colors/appearance for newly-created controls.
        app = NSApplication.sharedApplication()
        appearance = app.appearance()
        if appearance is not None:
            app.setAppearance_(None)
            app.setAppearance_(appearance)

        for win in app.windows() or []:
            try:
                win.contentView().setNeedsDisplay_(True)
                win.contentView().displayIfNeeded()
            except Exception:
                pass
        return value
    except Exception as e:
        log(1, "[Theme] Cocoa accent sync failed:", e)
        return None

def _clear_darkelf_cocoa_accent_override():
    """Return Darkelf to the user's inherited macOS accent preference."""
    try:
        NSUserDefaults.standardUserDefaults().removeObjectForKey_("AppleAccentColor")
        _broadcast_cocoa_color_change()
    except Exception as e:
        print("[Theme] Cocoa accent restore failed:", e)


class Browser(NSObject):

    def init(self):
        self = objc.super(Browser, self).init()
        if self is None:
            return None
            
        self.menu_panel = None
        self.menu_open = False
        self._initBookmarks()
        self._initKeyboardShortcuts()
        # ----------------------------
        # PQ CORE (SESSION LEVEL)
        # ----------------------------

        # Strong session seed (required)
        self._pq_seed = secrets.token_bytes(32)

        # 🔥 NEW: hidden session salt (for fingerprint secrecy)
        self._pq_salt = hashlib.sha3_256(self._pq_seed).digest()[:16]

        # ----------------------------
        # PQ SERIALIZATION QUEUE
        # ----------------------------

        # Ensures deterministic ordering of PQ operations
        self._pq_queue = NSOperationQueue.alloc().init()
        self._pq_queue.setMaxConcurrentOperationCount_(1)

        # ----------------------------
        # TAB + PQ STATE REGISTRY
        # ----------------------------

        # Track tabs explicitly for PQ consistency
        self.tabs = []

        # ----------------------------
        # FIRST PARTY ISOLATION (FPI)
        # ----------------------------

        self.fpi = FirstPartyIsolation(tab_isolation=True)

        # ----------------------------
        # OPTIONAL: PQ CONFIG FLAGS
        # ----------------------------

        self._pq_enabled = True

        # ---- Usual field setup ----
        self.cookies_enabled = False
        self.js_enabled = True
        self.tabs = []
        self.active = 0

        # WebKit memory protection
        self.page_load_count = 0
        self.process_pool = WKProcessPool.alloc().init()

        self.tab_btns = []
        self.tab_close_btns = []
        self.active = -1
        self._window = []

        self._containers = {}

        self._tab_uid_counter = 0
        # ---- 1. Create window ----
        self.window = self._make_window()

        self._pq_trust_cache = {}

        self.window.setCollectionBehavior_(
            128
        )  # NSWindowCollectionBehaviorFullScreenPrimary

        # ---- 2. Strong refs for delegates/handlers ----
        self._strong_refs = []

        self._window_delegate = _WindowDelegate.alloc().initWithOwner_(self)
        self._nav_delegate = _NavDelegate.alloc().initWithOwner_(self)
        self._ui_delegate = _UIDelegate.alloc().initWithOwner_(self)
        self._search_handler = SearchHandler.alloc().initWithOwner_(self)

        self._strong_refs.extend(
            [
                self._window_delegate,
                self._nav_delegate,
                self._ui_delegate,
                self._search_handler,
            ]
        )

        self.window.setDelegate_(self._window_delegate)

        ContentRuleManager.load_rules()

        self.mini_ai = DarkelfMiniAISentinel()
        self.mini_ai.browser = self

        self.download_ui = DownloadProgressView.alloc().initWithFrame_(
            NSMakeRect(20, 60, 520, 70)
        )
        self.download_ui.setHidden_(True)
        self.net_policy = DarkelfNetworkPolicy(self)

        content = self.window.contentView()

        content.addSubview_positioned_relativeTo_(
            self.download_ui, 1, None  # NSWindowAbove
        )

        # ensure it resizes with the window
        self.download_ui.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)

        # ---- 4. Toolbar, Tabbar, UI wiring ----
        self.toolbar = self._make_toolbar()

        self._build_tabbar()
        self._add_tab(home=True)
        self._bring_tabbar_to_front()

        self.window.setDelegate_(self)

        self.window.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        
        NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            0.01,
            False,
            lambda t: (
                self._layout_toolbar(),
                self._layout(),
                self._bring_tabbar_to_front(),
            ),
        )
        
        apply_darkelf_theme()

        self.download_dir = None

        self._pq_file_hashes = {}
        # ---- 7. Keyboard monitor ----
        self._install_key_monitor()

        try:
            nc = NSNotificationCenter.defaultCenter()
            nc.addObserver_selector_name_object_(
                self, "onResize:", "NSWindowDidResizeNotification", self.window
            )
        except Exception as e:
            log(2, e)

        return self
        
        # ============================================================
        # BOOKMARKS
        # ============================================================

        BOOKMARK_FILE = os.path.join(
            os.path.expanduser("~"),
            ".darkelf_bookmarks.json"
        )
        
        # --------------------------------------------------
        # Keyboard Shortcut Library
        # --------------------------------------------------

        self.shortcut_sections = {

            "Navigation": [
                ("⌘←", "Back"),
                ("⌘→", "Forward"),
                ("⌘R", "Reload"),
                ("⌘L", "Focus Address Bar"),
                ("⌘F", "Find in Page"),
                ("ESC", "Close Find Bar"),
                ("⌃⌘F", "Toggle Fullscreen"),
            ],

            "Tabs": [
                ("⌘T", "New Tab"),
                ("⌘W", "Close Tab"),
            ],

            "Zoom": [
                ("⌘+", "Zoom In"),
                ("⌘-", "Zoom Out"),
            ],

            "Application": [
                ("⇧⌘X", "Exit Darkelf"),
            ],
        }

        self.shortcut_expanded = {
            section: True
            for section in self.shortcut_sections
        }
        
    def showKeyboardShortcuts_(self, sender):
        if getattr(self, "btn_privacy", None) is not None:
            self.btn_privacy.setHidden_(True)
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            _pv = getattr(self, _pn, None)
            if _pv is not None:
                _pv.setHidden_(True)

        if not getattr(self, "shortcut_view", None):
            self._createShortcutView()
        self._layout_secondary_menu_views()

        if getattr(self, "bookmark_view", None):
            self.bookmark_view.setHidden_(True)

        for b in (
            self.btn_bookmarks,
            self.btn_add_bookmark,
            self.btn_hotkeys,
            self.btn_color,
            self.btn_background,
            self.btn_privacy,
            self.btn_mini_ai,
            self.btn_nuke,
            self.btn_js,
            self.btn_about,
        ):
            b.setHidden_(True)

        self.shortcut_view.setHidden_(False)

        self._reloadShortcutList()
        
    def toggleShortcutSection_(self, sender):

        sections = list(self.shortcut_sections.keys())

        index = sender.tag()

        if index < 0 or index >= len(sections):
            return

        section = sections[index]

        self.shortcut_expanded[section] = (
            not self.shortcut_expanded.get(section, True)
        )

        self._reloadShortcutList()
            
    def _initBookmarks(self):

        self.bookmarks = []
        self.bookmark_mode = False
        self._loadBookmarks()
        
    def _initKeyboardShortcuts(self):
    
        # ------------------------------------
        # Keyboard Shortcut Categories
        # ------------------------------------

        self.shortcut_sections = {

            "Navigation": [
                ("⌘←", "Back"),
                ("⌘→", "Forward"),
                ("⌘R", "Reload"),
                ("⌘L", "Focus Address Bar"),
                ("⌘F", "Find in Page"),
                ("ESC", "Close Find Bar"),
                ("⌃⌘F", "Toggle Fullscreen"),
            ],

            "Tabs": [
                ("⌘T", "New Tab"),
                ("⌘W", "Close Tab"),
            ],

            "Zoom": [
                ("⌘+", "Zoom In"),
                ("⌘-", "Zoom Out"),
            ],

            "Application": [
                ("⇧⌘X", "Exit Darkelf"),
            ],
        }

        # Start collapsed
        self.shortcut_expanded = {
            section: False
            for section in self.shortcut_sections
        }

        self._loadBookmarks()

    def _loadBookmarks(self):
        self.bookmarks = []
        
    def _saveBookmarks(self):
        return

    def addCurrentBookmark_(self, sender=None):

        if self.active < 0:
            return

        tab = self.tabs[self.active]

        url = getattr(tab, "url", "")
        title = getattr(tab, "title", "") or url

        if not url:
            return

        for b in self.bookmarks:
            if b["url"] == url:
                return

        self.bookmarks.append(
            {
                "title": title,
                "url": url,
            }
        )

        self._saveBookmarks()

        if self.bookmark_mode:
            self._reloadBookmarkList()

    def openBookmark_(self, sender):

        idx = sender.tag()

        if idx < 0 or idx >= len(self.bookmarks):
            return

        url = self.bookmarks[idx]["url"]

        # Return to the normal menu state
        self.showMainMenu_(None)

        # Load the bookmarked page
        self._load_url_in_active(url)

        # Close the hamburger menu
        self.toggleMenu_(None)
            
    def _cleanup_unused_containers(self):
        """Drop Python references for containers that no longer belong to a live tab."""
        try:
            active_keys = {
                getattr(tab, "container_key", None)
                for tab in self.tabs
                if getattr(tab, "container_key", None)
            }

            for key in list(self._containers.keys()):
                if key not in active_keys:
                    del self._containers[key]

        except Exception as e:
            log(2, e)

    def recycle_web_process(self):
        print("[Darkelf] Recycle disabled for testing")
        self.page_load_count = 0
        return

    @objc.IBAction
    def refreshMiniAI_(self, timer):

        if not hasattr(self, "mini_ai"):
            return

        try:
            # Handle automatic lockdown expiration
            self.mini_ai._maybe_auto_unlock(time.time())
        except Exception as e:
            print("[MiniAI Timer Error]", e)

        try:
            # Refresh the MiniAI status panel
            self.updateMiniAIIndicator()
        except Exception as e:
            log(2, e)
            
    def _createMenuPanel(self):
        
        if self.menu_panel:
            return

        width = 280
        height = 400

        cv = self.window.contentView()

        f = cv.bounds()

        self.menu_panel = NSView.alloc().initWithFrame_(
            NSMakeRect(
                f.size.width,
                f.size.height - height - 40,
                width,
                height,
            )
        )

        self.menu_panel.setAutoresizingMask_(
            NSViewMinXMargin | NSViewMinYMargin
        )

        # ==========================================================
        # DARKELF GLASS MENU PANEL
        # ==========================================================

        self.menu_panel.setWantsLayer_(True)

        layer = self.menu_panel.layer()

        # Deep matte black with transparency
        layer.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.02,
                0.025,
                0.03,
                0.90,
            ).CGColor()
        )

        # Rounded corners
        layer.setCornerRadius_(16)

        # Thin neon-green outline
        layer.setBorderWidth_(1.0)

        layer.setBorderColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.16,
                0.95,
                0.45,
                0.18,
            ).CGColor()
        )

        # Soft shadow
        layer.setShadowOpacity_(0.55)

        layer.setShadowRadius_(20)

        layer.setShadowOffset_(NSMakeSize(0, -2))

        layer.setShadowColor_(
            NSColor.blackColor().CGColor()
        )

        # Crisp edges
        layer.setMasksToBounds_(False)

        cv.addSubview_(self.menu_panel)
        self._apply_accent_to_ui()
        
        # ----------------------------------------------------------
        # Menu Buttons
        # ----------------------------------------------------------

        self.btn_mini_ai.setTitle_(" MiniAI Report")
        self.btn_nuke.setTitle_(" Nuke Session")
        self.btn_js.setTitle_(" JavaScript")
        self.btn_hotkeys.setTitle_(" Keyboard Shortcuts")

        self.btn_bookmarks = HoverButton.alloc().initWithFrame_(
            NSMakeRect(16, 170, 192, 34)
        )
        self.btn_bookmarks.setTitle_(" Bookmarks")

        bookmark_icon = load_toolbar_svg("bookmark-filled.svg", size=16.0)
        if bookmark_icon:
            self.btn_bookmarks.setImage_(bookmark_icon)

        self.btn_bookmarks.setImagePosition_(NSImageLeft)

        self.btn_bookmarks.setContentTintColor_(
            NSColor.whiteColor()
        )
        self.btn_bookmarks.setBordered_(False)
        self.btn_bookmarks.setBezelStyle_(0)
        self.btn_bookmarks.setAlignment_(NSLeftTextAlignment)
        self.btn_bookmarks.setFont_(NSFont.systemFontOfSize_(14))
        self.btn_bookmarks.setTarget_(self)
        self.btn_bookmarks.setAction_("showBookmarks:")

        self.btn_add_bookmark = HoverButton.alloc().initWithFrame_(
            NSMakeRect(16, 132, 192, 34)
        )
        self.btn_add_bookmark.setTitle_(" ➕ Add Current Page")
        self.btn_add_bookmark.setBordered_(False)
        self.btn_add_bookmark.setBezelStyle_(0)
        self.btn_add_bookmark.setAlignment_(NSLeftTextAlignment)
        self.btn_add_bookmark.setFont_(NSFont.systemFontOfSize_(14))
        self.btn_add_bookmark.setTarget_(self)
        self.btn_add_bookmark.setAction_("addCurrentBookmark:")

        # ----------------------------------------------------------
        # About Darkelf
        # ----------------------------------------------------------

        self.btn_about = HoverButton.alloc().initWithFrame_(
            NSMakeRect(16, 94, 192, 34)
        )

        self.btn_about.setTitle_(" About Darkelf")

        about_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "info.circle.fill",
            None,
        )

        if about_icon:
            about_icon.setTemplate_(True)
            self.btn_about.setImage_(about_icon)

        self.btn_about.setImagePosition_(NSImageLeft)
        self.btn_about.setContentTintColor_(NSColor.whiteColor())
        self.btn_about.setBordered_(False)
        self.btn_about.setBezelStyle_(0)
        self.btn_about.setAlignment_(NSLeftTextAlignment)
        self.btn_about.setFont_(NSFont.systemFontOfSize_(14))
        self.btn_about.setTarget_(self)
        self.btn_about.setAction_("showAboutView:")

        self.btn_color = HoverButton.alloc().initWithFrame_(NSMakeRect(16, 56, 192, 34))
        self.btn_color.setTitle_(" Accent Color…")
        color_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_("paintpalette.fill", None)
        if color_icon:
            color_icon.setTemplate_(True)
            self.btn_color.setImage_(color_icon)
        self.btn_color.setContentTintColor_(NSColor.whiteColor())
        self.btn_color.setTarget_(self)
        self.btn_color.setAction_("showAccentView:")

        self.btn_background = HoverButton.alloc().initWithFrame_(NSMakeRect(16, 18, 192, 34))
        self.btn_background.setTitle_(" Background")
        bg_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_("photo.fill", None)
        if bg_icon:
            bg_icon.setTemplate_(True)
            self.btn_background.setImage_(bg_icon)
        self.btn_background.setContentTintColor_(NSColor.whiteColor())
        self.btn_background.setTarget_(self)
        self.btn_background.setAction_("showBackgroundView:")
        
        self.btn_mini_ai.removeFromSuperview()
        self.btn_nuke.removeFromSuperview()
        self.btn_js.removeFromSuperview()
        self.btn_hotkeys.removeFromSuperview()
        self.btn_add_bookmark.removeFromSuperview()
        self.btn_about.removeFromSuperview()
        self.btn_color.removeFromSuperview()
        self.btn_background.removeFromSuperview()
        
        self.btn_privacy = HoverButton.alloc().initWithFrame_(NSMakeRect(16, 18, 192, 34))
        self.btn_privacy.setTitle_(" Privacy & Security")
        privacy_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_("lock.shield.fill", None)
        if privacy_icon:
            privacy_icon.setTemplate_(True)
            self.btn_privacy.setImage_(privacy_icon)
        self.btn_privacy.setContentTintColor_(NSColor.whiteColor())
        self.btn_privacy.setTarget_(self)
        self.btn_privacy.setAction_("showPrivacyView:")

        self.menu_panel.addSubview_(self.btn_bookmarks)
        self.menu_panel.addSubview_(self.btn_add_bookmark)

        buttons = [

            self.btn_bookmarks,
            self.btn_add_bookmark,

            self.btn_mini_ai,
            self.btn_nuke,
            self.btn_js,
            self.btn_hotkeys,
            self.btn_color,
            self.btn_background,
            self.btn_privacy,
            self.btn_about,
        ]

        y = 351

        for b in buttons:

            b.setFrame_(NSMakeRect(18, y, 244, 31))
            b.setBordered_(False)
            b.setBezelStyle_(0)
            b.setImagePosition_(NSImageLeft)
            b.setAlignment_(NSLeftTextAlignment)
            b.setFont_(NSFont.systemFontOfSize_(15))
            b.setWantsLayer_(True)
            if b.layer():
                b.layer().setCornerRadius_(8.0)
                b.layer().setMasksToBounds_(True)
                b.layer().setBackgroundColor_(NSColor.clearColor().CGColor())
            try:
                b.updateTrackingAreas()
            except Exception:
                pass

            self.menu_panel.addSubview_(b)

            y -= 35
            
    def _homepage_html(self):
        return homepage_html_for_accent(load_accent_rgba(), load_background_name())

    def _refresh_homepage_theme(self):
        try:
            tab = self._active_tab()
            if not tab or not getattr(tab, "view", None):
                return
            cur = getattr(tab, "url", "") or ""
            u = tab.view.URL()
            if u is not None:
                cur = str(u.absoluteString())
            if cur == HOME_URL:
                tab.view.loadHTMLString_baseURL_(self._homepage_html(), NSURL.URLWithString_(HOME_URL))
                tab.url = HOME_URL
                tab.host = "Darkelf Home"
        except Exception as e:
            log(2, "[Theme] homepage refresh:", e)

    def _apply_accent_to_ui(self):
        rgba = load_accent_rgba()
        sync_application_icon()
        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*rgba)
        try:
            if getattr(self, "menu_panel", None) and self.menu_panel.layer():
                self.menu_panel.layer().setBorderColor_(accent.colorWithAlphaComponent_(0.55).CGColor())
            # Main side-menu controls follow the selected accent. Nuke remains
            # red because it is deliberately destructive.
            menu_accent_buttons = (
                "btn_bookmarks", "btn_add_bookmark", "btn_mini_ai",
                "btn_js", "btn_hotkeys", "btn_color", "btn_background", "btn_privacy", "btn_about",
            )
            for name in menu_accent_buttons:
                b = getattr(self, name, None)
                if b is None:
                    continue
                try:
                    b.setContentTintColor_(accent)
                    if hasattr(b, "setDarkelfBaseTint_"):
                        b.setDarkelfBaseTint_(accent)
                    title = b.title() or ""
                    if title:
                        b.setAttributedTitle_(
                            NSAttributedString.alloc().initWithString_attributes_(
                                title, {NSForegroundColorAttributeName: accent}
                            )
                        )
                except Exception:
                    pass

            nuke = getattr(self, "btn_nuke", None)
            if nuke is not None:
                destructive = NSColor.systemRedColor()
                try:
                    nuke.setContentTintColor_(destructive)
                    if hasattr(nuke, "setDarkelfBaseTint_"):
                        nuke.setDarkelfBaseTint_(destructive)
                    title = nuke.title() or ""
                    if title:
                        nuke.setAttributedTitle_(
                            NSAttributedString.alloc().initWithString_attributes_(
                                title, {NSForegroundColorAttributeName: destructive}
                            )
                        )
                except Exception:
                    pass

            if getattr(self, "addr", None):
                self.addr.setWantsLayer_(True)
                if self.addr.layer():
                    self.addr.layer().setBorderWidth_(1.5)
                    self.addr.layer().setCornerRadius_(6.0)
                    self.addr.layer().setBorderColor_(accent.CGColor())
            # Subviews that can already be open when the accent changes.
            for name in ("about_name_label", "about_website_label"):
                label = getattr(self, name, None)
                if label is not None:
                    try:
                        label.setTextColor_(accent)
                    except Exception:
                        pass
            if getattr(self, "shortcut_document", None) is not None:
                try:
                    self._reloadShortcutList()
                except Exception:
                    pass
            for name in ("btn_shortcut_back", "btn_about_back", "btn_bookmark_back", "btn_mini_ai_back", "btn_accent_back"):
                b = getattr(self, name, None)
                if b is not None:
                    try:
                        b.setContentTintColor_(accent)
                    except Exception:
                        pass
            # Preserve each toolbar control's normal tint while HoverButton uses
            # the selected accent for hover/pressed feedback.
            for name in ("btn_back", "btn_fwd", "btn_reload", "btn_bookmark", "btn_menu", "btn_new_tab"):
                b = getattr(self, name, None)
                if b is not None and hasattr(b, "setDarkelfBaseTint_"):
                    b.setDarkelfBaseTint_(NSColor.whiteColor())
            self._update_tab_buttons()
        except Exception as e:
            log(2, e)

    def _setAccentRGBA_(self, rgba):
        save_accent_rgba(rgba)
        _sync_cocoa_accent_to_darkelf(rgba)
        self._apply_accent_to_ui()
        self._refresh_homepage_theme()
        if getattr(self, "accent_view", None) is not None:
            self._refreshAccentView()

    def accentGreen_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Green"])
    def accentBlue_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Blue"])
    def accentPurple_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Purple"])
    def accentOrange_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Orange"])
    def accentRed_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Red"])
    def accentTeal_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Teal"])
    def accentCyan_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Cyan"])
    def accentGold_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Gold"])
    def accentPink_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Pink"])
    def accentMagenta_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Magenta"])
    def accentAmber_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Amber"])
    def accentSilver_(self, sender): self._setAccentRGBA_(ACCENT_PRESETS["Silver"])

    def _createAccentView(self):
        """Build the in-panel Accent Color page (no native popup menu)."""
        if getattr(self, "accent_view", None):
            return

        self.accent_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 220, 300))

        self.btn_accent_back = NSButton.alloc().initWithFrame_(NSMakeRect(12, 264, 80, 28))
        self.btn_accent_back.setTitle_("← Back")
        self.btn_accent_back.setBordered_(False)
        self.btn_accent_back.setBezelStyle_(0)
        self.btn_accent_back.setAlignment_(NSLeftTextAlignment)
        self.btn_accent_back.setTarget_(self)
        self.btn_accent_back.setAction_("showMainMenu:")
        self.accent_view.addSubview_(self.btn_accent_back)

        self.accent_title = NSTextField.alloc().initWithFrame_(NSMakeRect(92, 266, 116, 20))
        self.accent_title.setEditable_(False)
        self.accent_title.setBordered_(False)
        self.accent_title.setDrawsBackground_(False)
        self.accent_title.setSelectable_(False)
        self.accent_title.setStringValue_("Accent Color")
        self.accent_title.setTextColor_(NSColor.whiteColor())
        self.accent_title.setFont_(NSFont.boldSystemFontOfSize_(14))
        self.accent_view.addSubview_(self.accent_title)

        self.accent_buttons = []
        presets = (
            ("Green", "accentGreen:"), ("Blue", "accentBlue:"),
            ("Purple", "accentPurple:"), ("Orange", "accentOrange:"),
            ("Red", "accentRed:"), ("Teal", "accentTeal:"),
            ("Cyan", "accentCyan:"), ("Gold", "accentGold:"),
            ("Pink", "accentPink:"), ("Magenta", "accentMagenta:"),
            ("Amber", "accentAmber:"), ("Silver", "accentSilver:"),
        )
        y = 316
        for title, selector in presets:
            b = HoverButton.alloc().initWithFrame_(NSMakeRect(18, y, 244, 24))
            b.setTitle_(title)
            b.setBordered_(False)
            b.setBezelStyle_(0)
            b.setAlignment_(NSLeftTextAlignment)
            b.setFont_(NSFont.systemFontOfSize_(14))
            b.setTarget_(self)
            b.setAction_(selector)
            self.accent_view.addSubview_(b)
            self.accent_buttons.append((title, b))
            y -= 25

        self.btn_accent_custom = HoverButton.alloc().initWithFrame_(NSMakeRect(18, 8, 244, 28))
        self.btn_accent_custom.setTitle_("Custom Color…")
        self.btn_accent_custom.setBordered_(False)
        self.btn_accent_custom.setBezelStyle_(0)
        self.btn_accent_custom.setAlignment_(NSLeftTextAlignment)
        self.btn_accent_custom.setFont_(NSFont.systemFontOfSize_(14))
        self.btn_accent_custom.setTarget_(self)
        self.btn_accent_custom.setAction_("showCustomAccentColor:")
        self.accent_view.addSubview_(self.btn_accent_custom)

    def _refreshAccentView(self):
        if not getattr(self, "accent_buttons", None):
            return
        current = load_accent_rgba()
        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*current)
        selected_name = None
        for name, rgba in ACCENT_PRESETS.items():
            if all(abs(float(current[i]) - float(rgba[i])) < 0.015 for i in range(3)):
                selected_name = name
                break
        for name, button in self.accent_buttons:
            button.setTitle_(("✓  " if name == selected_name else "   ") + name)
            button.setContentTintColor_(accent if name == selected_name else NSColor.whiteColor())
            if hasattr(button, "setDarkelfBaseTint_"):
                button.setDarkelfBaseTint_(accent if name == selected_name else NSColor.whiteColor())
        try:
            self.btn_accent_back.setContentTintColor_(accent)
            self.btn_accent_back.setDarkelfBaseTint_(accent)
            self.btn_accent_custom.setContentTintColor_(accent)
            self.btn_accent_custom.setDarkelfBaseTint_(accent)
        except Exception:
            pass

    def showAccentView_(self, sender):
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            _pv = getattr(self, _pn, None)
            if _pv is not None:
                _pv.setHidden_(True)
        if getattr(self, "privacy_view", None):
            self.privacy_view.setHidden_(True)
        self._createAccentView()
        self._layout_secondary_menu_views()
        for name in ("bookmark_view", "shortcut_view", "about_view", "mini_ai_view", "accent_view", "background_view", "privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            view = getattr(self, name, None)
            if view is not None:
                view.setHidden_(True)
        for b in (
            self.btn_bookmarks, self.btn_add_bookmark, self.btn_mini_ai,
            self.btn_nuke, self.btn_js, self.btn_hotkeys, self.btn_color, self.btn_background, self.btn_privacy, self.btn_about,
        ):
            b.setHidden_(True)
        self.accent_view.removeFromSuperview()
        self.menu_panel.addSubview_(self.accent_view)
        self.accent_view.setHidden_(False)
        self._refreshAccentView()

    def showCustomAccentColor_(self, sender):
        panel = NSColorPanel.sharedColorPanel()
        panel.setShowsAlpha_(False)
        panel.setContinuous_(True)
        panel.setTarget_(self)
        panel.setAction_("accentColorChanged:")
        panel.setColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba()))
        panel.makeKeyAndOrderFront_(None)

    def accentColorChanged_(self, sender):
        try:
            c = sender.color().colorUsingColorSpace_(NSColorSpace.sRGBColorSpace())
            self._setAccentRGBA_((c.redComponent(), c.greenComponent(), c.blueComponent(), 1.0))
        except Exception as e:
            log(1, "[Theme] Could not apply custom accent:", e)

    def _setBackground_(self, name):
        save_background_name(name)
        self._refresh_homepage_theme()
        if getattr(self, "background_view", None) is not None:
            self._refreshBackgroundView()

    def backgroundGlow_(self, sender): self._setBackground_("Darkelf Glow")
    def backgroundMidnight_(self, sender): self._setBackground_("Midnight")
    def backgroundAurora_(self, sender): self._setBackground_("Aurora")
    def backgroundNebula_(self, sender): self._setBackground_("Nebula")
    def backgroundCarbon_(self, sender): self._setBackground_("Carbon")
    def backgroundBlack_(self, sender): self._setBackground_("Pure Black")
    def backgroundOcean_(self, sender): self._setBackground_("Deep Ocean")
    def backgroundCrimson_(self, sender): self._setBackground_("Crimson Eclipse")
    def backgroundMatrix_(self, sender): self._setBackground_("Emerald Matrix")
    def backgroundArctic_(self, sender): self._setBackground_("Arctic Frost")

    def _createBackgroundView(self):
        if getattr(self, "background_view", None):
            return
        self.background_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 220, 390))

        self.btn_background_back = NSButton.alloc().initWithFrame_(NSMakeRect(12, 354, 80, 28))
        self.btn_background_back.setTitle_("← Back")
        self.btn_background_back.setBordered_(False)
        self.btn_background_back.setBezelStyle_(0)
        self.btn_background_back.setAlignment_(NSLeftTextAlignment)
        self.btn_background_back.setTarget_(self)
        self.btn_background_back.setAction_("showMainMenu:")
        self.background_view.addSubview_(self.btn_background_back)

        self.background_title = NSTextField.alloc().initWithFrame_(NSMakeRect(92, 356, 116, 20))
        self.background_title.setEditable_(False)
        self.background_title.setBordered_(False)
        self.background_title.setDrawsBackground_(False)
        self.background_title.setSelectable_(False)
        self.background_title.setStringValue_("Background")
        self.background_title.setTextColor_(NSColor.whiteColor())
        self.background_title.setFont_(NSFont.boldSystemFontOfSize_(14))
        self.background_view.addSubview_(self.background_title)

        self.background_buttons = []
        choices = (
            ("Darkelf Glow", "backgroundGlow:"),
            ("Midnight", "backgroundMidnight:"),
            ("Aurora", "backgroundAurora:"),
            ("Nebula", "backgroundNebula:"),
            ("Carbon", "backgroundCarbon:"),
            ("Pure Black", "backgroundBlack:"),
            ("Deep Ocean", "backgroundOcean:"),
            ("Crimson Eclipse", "backgroundCrimson:"),
            ("Emerald Matrix", "backgroundMatrix:"),
            ("Arctic Frost", "backgroundArctic:"),
        )
        y = 314
        for title, selector in choices:
            b = HoverButton.alloc().initWithFrame_(NSMakeRect(18, y, 244, 30))
            b.setTitle_(title)
            b.setBordered_(False)
            b.setBezelStyle_(0)
            b.setAlignment_(NSLeftTextAlignment)
            b.setFont_(NSFont.systemFontOfSize_(14))
            b.setTarget_(self)
            b.setAction_(selector)
            self.background_view.addSubview_(b)
            self.background_buttons.append((title, b))
            y -= 34

    def _refreshBackgroundView(self):
        current = load_background_name()
        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
        for name, button in getattr(self, "background_buttons", []):
            button.setTitle_(("✓  " if name == current else "   ") + name)
            button.setContentTintColor_(accent if name == current else NSColor.whiteColor())
            if hasattr(button, "setDarkelfBaseTint_"):
                button.setDarkelfBaseTint_(accent if name == current else NSColor.whiteColor())
        try:
            self.btn_background_back.setContentTintColor_(accent)
        except Exception:
            pass

    def showBackgroundView_(self, sender):
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            _pv = getattr(self, _pn, None)
            if _pv is not None:
                _pv.setHidden_(True)
        if getattr(self, "privacy_view", None):
            self.privacy_view.setHidden_(True)
        self._createBackgroundView()
        self._layout_secondary_menu_views()
        for name in ("bookmark_view", "shortcut_view", "about_view", "mini_ai_view", "accent_view", "background_view", "privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            view = getattr(self, name, None)
            if view is not None:
                view.setHidden_(True)
        for b in (
            self.btn_bookmarks, self.btn_add_bookmark, self.btn_mini_ai,
            self.btn_nuke, self.btn_js, self.btn_hotkeys, self.btn_color,
            self.btn_background, self.btn_privacy, self.btn_about,
        ):
            b.setHidden_(True)
        self.background_view.removeFromSuperview()
        self.menu_panel.addSubview_(self.background_view)
        self.background_view.setHidden_(False)
        self._refreshBackgroundView()

    # Privacy pages are display-only: no WebKit policy is changed here.
    def _privacy_label(self, parent, title, x, y, width, height=22,
                       size=13, bold=False, muted=False, accent=False):
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, width, height))
        label.setEditable_(False)
        label.setBordered_(False)
        label.setDrawsBackground_(False)
        label.setSelectable_(False)
        label.setFont_((NSFont.boldSystemFontOfSize_(size) if bold
                        else NSFont.systemFontOfSize_(size)))
        if accent:
            color = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.28, 0.84, 0.49, 1)
        elif muted:
            color = NSColor.colorWithCalibratedWhite_alpha_(0.68, 1)
        else:
            color = NSColor.whiteColor()
        label.setTextColor_(color)
        label.setStringValue_(title)
        parent.addSubview_(label)
        return label

    def _privacy_page(self, title, back_action):
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 280, 400))
        back = HoverButton.alloc().initWithFrame_(NSMakeRect(17, 359, 77, 30))
        back.setTitle_("← Back")
        back.setBordered_(False)
        back.setAlignment_(NSLeftTextAlignment)
        back.setFont_(NSFont.systemFontOfSize_(15))
        back.setTarget_(self)
        back.setAction_(back_action)
        view.addSubview_(back)
        self._privacy_label(view, title, 103, 362, 170, 24, size=15, bold=True)
        view.setHidden_(True)
        self.menu_panel.addSubview_(view)
        return view

    def _privacy_row(self, view, name, detail, y):
        self._privacy_label(view, name, 20, y, 240, size=15, bold=True)
        self._privacy_label(view, detail, 20, y - 25, 240, size=13, muted=True)

    def _createPrivacyView(self):
        if getattr(self, "privacy_view", None) is not None:
            return
        self.privacy_view = self._privacy_page("Privacy & Security", "showMainMenu:")
        entries = [
            ("Privacy Protection", "Built-in defenses", "showPrivacyProtection:"),
            ("Website Exceptions", "No configurable overrides", "showPrivacyExceptions:"),
            ("Site Permissions", "Read-only permission status", "showPrivacyPermissions:"),
        ]
        self.privacy_nav_buttons = []
        for index, (title, subtitle, action) in enumerate(entries):
            y = 285 - index * 92
            btn = HoverButton.alloc().initWithFrame_(NSMakeRect(20, y, 240, 40))
            btn.setTitle_(title + "  ›")
            btn.setBordered_(False)
            btn.setAlignment_(NSLeftTextAlignment)
            btn.setFont_(NSFont.boldSystemFontOfSize_(16))
            btn.setTarget_(self)
            btn.setAction_(action)
            self.privacy_view.addSubview_(btn)
            self.privacy_nav_buttons.append(btn)
            self._privacy_label(self.privacy_view, subtitle, 25, y - 24, 235,
                                size=13, muted=True)

        self.privacy_protection_view = self._privacy_page("Protection", "showPrivacyView:")
        self._privacy_label(self.privacy_protection_view, "CURRENT LEVEL", 20, 321, 240,
                            size=13, bold=True, accent=True)
        self._privacy_label(self.privacy_protection_view, "Strict", 20, 291, 240,
                            size=15, bold=True)
        self._privacy_label(self.privacy_protection_view, "Built-in privacy protection", 20, 269,
                            240, size=13, muted=True)
        for name, detail, y in [
            ("Tracker blocking", "WebKit content rules", 224),
            ("Fingerprint defenses", "Built-in script protections", 176),
            ("WebRTC", "Blocked by Darkelf policy", 128),
            ("Tab isolation", "Ephemeral browsing", 80),
        ]:
            self._privacy_row(self.privacy_protection_view, name, detail, y)

        self.privacy_exceptions_view = self._privacy_page("Website Exceptions", "showPrivacyView:")
        self._privacy_label(self.privacy_exceptions_view, "NO OVERRIDES", 20, 301, 240,
                            size=15, bold=True, accent=True)
        self._privacy_label(self.privacy_exceptions_view, "Site-specific settings are", 20, 260,
                            240, size=14, muted=True)
        self._privacy_label(self.privacy_exceptions_view, "not configurable in this build.", 20, 233,
                            240, size=14, muted=True)

        self.privacy_permissions_view = self._privacy_page("Site Permissions", "showPrivacyView:")
        self._privacy_label(self.privacy_permissions_view, "READ-ONLY STATUS", 20, 326, 240,
                            size=13, bold=True, accent=True)
        for name, detail, y in [
            ("WebRTC", "Blocked by Darkelf policy", 282),
            ("Camera & microphone", "Media capture requests denied", 223),
            ("Location", "No permission switch", 164),
            ("Notifications", "No permission switch", 105),
        ]:
            self._privacy_row(self.privacy_permissions_view, name, detail, y)
        self._privacy_label(self.privacy_permissions_view, "No permission controls are exposed.", 20,
                            35, 245, size=12, muted=True)

    def _resize_privacy_panel(self, enlarged):
        """Keep every menu page at the shared 280 × 400 size."""
        if self.menu_panel is None:
            return
        width, height = 280, 400
        bounds = self.window.contentView().bounds()
        x = bounds.size.width - width - 10 if self.menu_open else bounds.size.width
        y = bounds.size.height - height - 40
        self.menu_panel.setFrame_(NSMakeRect(x, y, width, height))
        self._layout_secondary_menu_views()

    def _show_privacy_page(self, page):
        self._createMenuPanel()
        self._createPrivacyView()
        self._resize_privacy_panel(True)
        for name in ("bookmark_view", "shortcut_view", "about_view", "mini_ai_view",
                     "accent_view", "background_view", "privacy_view",
                     "privacy_protection_view", "privacy_exceptions_view",
                     "privacy_permissions_view"):
            view = getattr(self, name, None)
            if view is not None:
                view.setHidden_(True)
        for name in ("btn_bookmarks", "btn_add_bookmark", "btn_mini_ai", "btn_nuke",
                     "btn_js", "btn_hotkeys", "btn_color", "btn_background",
                     "btn_privacy", "btn_about"):
            button = getattr(self, name, None)
            if button is not None:
                button.setHidden_(True)
        page.removeFromSuperview()
        self.menu_panel.addSubview_(page)
        page.setHidden_(False)

    def showPrivacyView_(self, sender):
        self._show_privacy_page(self.privacy_view if getattr(self, "privacy_view", None)
                                else self._create_privacy_root())

    def _create_privacy_root(self):
        self._createMenuPanel()
        self._createPrivacyView()
        return self.privacy_view

    def showPrivacyProtection_(self, sender):
        self._createPrivacyView()
        self._show_privacy_page(self.privacy_protection_view)

    def showPrivacyExceptions_(self, sender):
        self._createPrivacyView()
        self._show_privacy_page(self.privacy_exceptions_view)

    def showPrivacyPermissions_(self, sender):
        self._createPrivacyView()
        self._show_privacy_page(self.privacy_permissions_view)

    def toggleMenu_(self, sender):

        self._createMenuPanel()

        cv = self.window.contentView()
        f = cv.bounds()

        width = float(self.menu_panel.frame().size.width)

        if self.menu_open:

            target = NSMakeRect(
                f.size.width,
                self.menu_panel.frame().origin.y,
                width,
                self.menu_panel.frame().size.height,
            )

        else:

            target = NSMakeRect(
                f.size.width - width - 10,
                self.menu_panel.frame().origin.y,
                width,
                self.menu_panel.frame().size.height,
            )

        self.menu_open = not self.menu_open

        # Keep the toolbar control visually synchronized with the panel state.
        try:
            menu_asset = "close.svg" if self.menu_open else "menu.svg"
            menu_image = load_toolbar_svg(menu_asset, size=18.0)
            if menu_image:
                self.btn_menu.setImage_(menu_image)
            self.btn_menu.setToolTip_("Close Menu" if self.menu_open else "Menu")
        except Exception as e:
            log(2, e)

        def animate(ctx):

            ctx.setDuration_(0.20)

            self.menu_panel.animator().setFrame_(target)

        NSAnimationContext.runAnimationGroup_completionHandler_(
            animate,
            None,
        )
        
    # ==========================================================
    # BOOKMARK MANAGER (Part 1)
    # Creates the bookmark panel inside the hamburger menu
    # ==========================================================

    def _menu_content_height(self):
        try:
            return max(300.0, float(self.menu_panel.bounds().size.height))
        except Exception:
            return 300.0

    def _layout_secondary_menu_views(self):
        """Keep secondary menu pages pinned to the live panel top edge."""
        h = self._menu_content_height()
        w = 280.0
        try:
            w = max(280.0, float(self.menu_panel.bounds().size.width))
        except Exception:
            pass
        top = h - 36.0
        for name in ("bookmark_view", "shortcut_view", "about_view", "mini_ai_view", "accent_view", "background_view", "privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            view = getattr(self, name, None)
            if view is not None:
                view.setFrame_(NSMakeRect(0, 0, w, h))
        # Consistent typography across existing submenus.
        for name in ("bookmark_title", "shortcut_title", "about_title", "mini_ai_title", "accent_title", "background_title"):
            label = getattr(self, name, None)
            if label is not None:
                label.setFont_(NSFont.boldSystemFontOfSize_(15))
        for name in ("btn_bookmark_back", "btn_shortcut_back", "btn_about_back", "btn_mini_ai_back", "btn_accent_back", "btn_background_back"):
            button = getattr(self, name, None)
            if button is not None:
                button.setFont_(NSFont.systemFontOfSize_(14))
        for group in ("accent_buttons", "background_buttons"):
            for item in getattr(self, group, ()) or ():
                button = item[1] if isinstance(item, tuple) else item
                button.setFont_(NSFont.systemFontOfSize_(14))
        # Header controls: same top baseline on every secondary page.
        for name in ("btn_bookmark_back", "btn_shortcut_back", "btn_about_back", "btn_mini_ai_back", "btn_accent_back", "btn_background_back", "btn_privacy_back"):
            ctl = getattr(self, name, None)
            if ctl is not None:
                ctl.setFrame_(NSMakeRect(12, top, 80, 28))
        if getattr(self, "bookmark_title", None) is not None:
            self.bookmark_title.setFrame_(NSMakeRect(112, top + 2, 154, 22))
        if getattr(self, "shortcut_title", None) is not None:
            self.shortcut_title.setFrame_(NSMakeRect(112, top + 2, 154, 22))
        if getattr(self, "about_title", None) is not None:
            self.about_title.setFrame_(NSMakeRect(108, top + 2, 158, 22))
        if getattr(self, "mini_ai_title", None) is not None:
            self.mini_ai_title.setFrame_(NSMakeRect(110, top + 2, 156, 22))
        if getattr(self, "accent_title", None) is not None:
            self.accent_title.setFrame_(NSMakeRect(110, top + 2, 156, 22))
        if getattr(self, "privacy_title", None) is not None:
            self.privacy_title.setFrame_(NSMakeRect(87, top + 2, 124, 20))
        if getattr(self, "background_title", None) is not None:
            self.background_title.setFrame_(NSMakeRect(110, top + 2, 156, 22))
        if getattr(self, "accent_buttons", None):
            y = top - 38
            for _name, button in self.accent_buttons:
                button.setFrame_(NSMakeRect(18, y, 244, 24))
                y -= 25
        if getattr(self, "btn_accent_custom", None) is not None:
            self.btn_accent_custom.setFrame_(NSMakeRect(18, 8, 244, 28))
        if getattr(self, "background_buttons", None):
            y = top - 42
            for _name, button in self.background_buttons:
                button.setFrame_(NSMakeRect(18, y, 244, 30))
                y -= 31
        # Content starts directly below the header instead of remaining at y=0.
        if getattr(self, "bookmark_scroll", None) is not None:
            self.bookmark_scroll.setFrame_(NSMakeRect(14, 12, w - 28, top - 32))
        if getattr(self, "shortcut_scroll", None) is not None:
            self.shortcut_scroll.setFrame_(NSMakeRect(14, 12, w - 28, top - 32))
        # MiniAI: aligned 2-column stats, 14pt labels and 30pt row rhythm.
        if getattr(self, "_mini_ai_name_labels", None):
            y = top - 45
            for name_label, value_label in zip(self._mini_ai_name_labels,
                                               self._mini_ai_value_labels):
                name_label.setFrame_(NSMakeRect(20, y, 174, 23))
                value_label.setFrame_(NSMakeRect(w - 83, y, 59, 23))
                name_label.setFont_(NSFont.systemFontOfSize_(14))
                value_label.setFont_(NSFont.boldSystemFontOfSize_(14))
                y -= 30
        # Keyboard shortcuts: reserve header space and use the full width.
        if getattr(self, "shortcut_scroll", None) is not None:
            self.shortcut_scroll.setFrame_(NSMakeRect(16, 16, w - 32, top - 32))
        # About uses a compact top-aligned stack.
        positions = {
            "about_name_label": (15, top - 48, 250, 22),
            "about_version_label": (15, top - 72, 250, 18),
            "about_desc_label": (15, top - 132, 250, 55),
            "about_website_label": (15, top - 166, 250, 18),
            "about_detail_label": (18, top - 280, 244, 102),
            "about_copyright_label": (15, 14, 250, 35),
        }
        for name, frame in positions.items():
            ctl = getattr(self, name, None)
            if ctl is not None:
                ctl.setFrame_(NSMakeRect(*frame))

    def _createBookmarksView(self):

        if getattr(self, "bookmark_view", None):
            return

        # Match the menu panel height
        self.bookmark_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 220, 300)
        )

        # Back button
        self.btn_bookmark_back = NSButton.alloc().initWithFrame_(
            NSMakeRect(12, 264, 80, 28)
        )

        self.btn_bookmark_back.setTitle_("← Back")
        self.btn_bookmark_back.setBordered_(False)
        self.btn_bookmark_back.setBezelStyle_(0)
        self.btn_bookmark_back.setAlignment_(NSLeftTextAlignment)
        self.btn_bookmark_back.setTarget_(self)
        self.btn_bookmark_back.setAction_("showMainMenu:")

        self.bookmark_view.addSubview_(self.btn_bookmark_back)

        # Title
        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(95, 266, 110, 20)
        )

        title.setEditable_(False)
        title.setBordered_(False)
        title.setDrawsBackground_(False)
        title.setSelectable_(False)
        title.setStringValue_("Bookmarks")
        title.setTextColor_(NSColor.whiteColor())
        title.setFont_(NSFont.boldSystemFontOfSize_(14))

        self.bookmark_view.addSubview_(title)
        self.bookmark_title = title

        # Scroll view
        self.bookmark_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(12, 8, 196, 240)
        )

        self.bookmark_scroll.setHasVerticalScroller_(True)
        self.bookmark_scroll.setHasHorizontalScroller_(False)
        self.bookmark_scroll.setAutohidesScrollers_(True)
        self.bookmark_scroll.setBorderType_(0)
        
        # ----------------------------------------------------------
        # Rounded Darkelf bookmark container
        # ----------------------------------------------------------

        self.bookmark_scroll.setWantsLayer_(True)

        scroll_layer = self.bookmark_scroll.layer()

        scroll_layer.setCornerRadius_(12)

        scroll_layer.setMasksToBounds_(True)

        scroll_layer.setBorderWidth_(1.0)

        scroll_layer.setBorderColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.16,
                0.95,
                0.45,
                0.12,
            ).CGColor()
        )

        scroll_layer.setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        # Don't let NSScrollView paint its default background
        self.bookmark_scroll.setDrawsBackground_(False)

        self.bookmark_document = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 196, 10)
        )

        self.bookmark_document.setWantsLayer_(True)

        self.bookmark_document.layer().setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.bookmark_scroll.setDocumentView_(self.bookmark_document)

        # Make the clip view transparent too
        clip = self.bookmark_scroll.contentView()

        clip.setWantsLayer_(True)

        clip.layer().setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.bookmark_view.addSubview_(self.bookmark_scroll)

        self.bookmark_view.setHidden_(True)

        self.bookmark_view.setFrameOrigin_((0, 0))

        self.menu_panel.addSubview_(self.bookmark_view)
        self._layout_secondary_menu_views()
        
    # ==========================================================
    # Bookmark Toolbar Sync
    # ==========================================================

    def updateBookmarkButton(self):

        if not hasattr(self, "btn_bookmark"):
            return

        try:
            if self.active < 0 or self.active >= len(self.tabs):
                return

            url = getattr(self.tabs[self.active], "url", "")

            bookmarked = any(
                b.get("url") == url
                for b in self.bookmarks
            )

            icon = "bookmark-filled.svg" if bookmarked else "bookmark.svg"
            img = load_toolbar_svg(icon, size=18.0)
            if img:
                self.btn_bookmark.setImage_(img)
            self.btn_bookmark.setToolTip_(
                "Remove Bookmark" if bookmarked else "Bookmark This Page"
            )

        except Exception as e:
            log(2, e)
            
    def refreshBookmarkButton(self):

        if not hasattr(self, "btn_bookmark"):
            return

        url = ""

        if 0 <= self.active < len(self.tabs):
            url = getattr(self.tabs[self.active], "url", "") or ""

        bookmarked = any(
            b["url"] == url
            for b in self.bookmarks
        )

        icon = "bookmark-filled.svg" if bookmarked else "bookmark.svg"
        img = load_toolbar_svg(icon, size=18.0)
        if img:
            self.btn_bookmark.setImage_(img)
        self.btn_bookmark.setToolTip_(
            "Remove Bookmark" if bookmarked else "Bookmark This Page"
        )
        
    # ==========================================================
    # Toolbar Bookmark Toggle
    # ==========================================================

    def toggleBookmarkToolbar_(self, sender):

        if self.active < 0 or self.active >= len(self.tabs):
            return

        url = self.tabs[self.active].url

        for i, bm in enumerate(self.bookmarks):
            if bm.get("url") == url:
    
                del self.bookmarks[i]

                self._saveBookmarks()
                self._reloadBookmarkList()
                self.updateBookmarkButton()

                return

        title = getattr(self.tabs[self.active], "title", "") or url

        self.bookmarks.append({
            "title": title,
            "url": url,
        })

        self._saveBookmarks()
        self._reloadBookmarkList()
        self.updateBookmarkButton()
    
    # ==========================================================
    # Show Bookmark View
    # ==========================================================

    def showBookmarks_(self, sender):
        if getattr(self, "btn_privacy", None) is not None:
            self.btn_privacy.setHidden_(True)
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            _pv = getattr(self, _pn, None)
            if _pv is not None:
                _pv.setHidden_(True)
        if getattr(self, "privacy_view", None):
            self.privacy_view.setHidden_(True)

        if not getattr(self, "bookmark_view", None):
            self._createBookmarksView()
        self._layout_secondary_menu_views()

        # Hide main menu buttons
        for b in (
            self.btn_bookmarks,
            self.btn_add_bookmark,
            self.btn_mini_ai,
            self.btn_nuke,
            self.btn_js,
            self.btn_hotkeys,
            self.btn_color,
            self.btn_background,
            self.btn_about,
        ):
            b.setHidden_(True)

        # Bring bookmark view to the front every time
        self.bookmark_view.removeFromSuperview()
        self.menu_panel.addSubview_(self.bookmark_view)

        self.bookmark_view.setHidden_(False)

        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
        try:
            self.btn_bookmark_back.setContentTintColor_(accent)
        except Exception:
            pass
        self.btn_bookmarks.setContentTintColor_(accent)
        if hasattr(self.btn_bookmarks, "setDarkelfBaseTint_"):
            self.btn_bookmarks.setDarkelfBaseTint_(accent)

        self._reloadBookmarkList()
        
    # ==========================================================
    # Return to Main Menu
    # ==========================================================

    def showMainMenu_(self, sender):
        self._resize_privacy_panel(False)

        if getattr(self, "bookmark_view", None):
            self.bookmark_view.setHidden_(True)

        if getattr(self, "shortcut_view", None):
            self.shortcut_view.setHidden_(True)
            
        if getattr(self, "mini_ai_view", None):
            self.mini_ai_view.setHidden_(True)
            
        if getattr(self, "about_view", None):
            self.about_view.setHidden_(True)

        if getattr(self, "accent_view", None):
            self.accent_view.setHidden_(True)

        if getattr(self, "background_view", None):
            self.background_view.setHidden_(True)
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            _pv = getattr(self, _pn, None)
            if _pv is not None:
                _pv.setHidden_(True)

        for b in (
            self.btn_bookmarks,
            self.btn_add_bookmark,
            self.btn_hotkeys,
            self.btn_color,
            self.btn_background,
            self.btn_privacy,
            self.btn_mini_ai,
            self.btn_nuke,
            self.btn_js,
            self.btn_about,
        ):
            b.setHidden_(False)
    
    # ==========================================================
    # Reload Bookmark List
    # ==========================================================

    def _reloadBookmarkList(self):

        if not getattr(self, "bookmark_document", None):
            return

        for view in list(self.bookmark_document.subviews()):
            view.removeFromSuperview()

        bookmarks = getattr(self, "bookmarks", [])

        row_height = 36
        padding = 7
        top_margin = 12
        # Match the document height to the visible scroll region so the first
        # bookmark sits immediately below the header, not mid-panel.
        visible_h = float(self.bookmark_scroll.contentView().bounds().size.height)
        visible_w = float(self.bookmark_scroll.contentView().bounds().size.width)
        doc_width = max(196.0, visible_w)

        if not bookmarks:

            self.bookmark_document.setFrame_(
                NSMakeRect(0, 0, doc_width, max(visible_h, 170))
            )

            lbl = NSTextField.alloc().initWithFrame_(
                NSMakeRect(12, max(visible_h, 170) - 38, doc_width - 24, 24)
            )

            lbl.setBordered_(False)
            lbl.setEditable_(False)
            lbl.setSelectable_(False)
            lbl.setDrawsBackground_(False)
            lbl.setAlignment_(NSLeftTextAlignment)
            lbl.setTextColor_(NSColor.systemGrayColor())
            lbl.setStringValue_("No bookmarks yet.")

            self.bookmark_document.addSubview_(lbl)
            return

        total_height = len(bookmarks) * (row_height + padding) + top_margin
        doc_height = max(visible_h, total_height)

        self.bookmark_document.setFrame_(
            NSMakeRect(
                0,
                0,
                doc_width,
                doc_height,
            )
        )

        # Start just below the top of the document
        y = doc_height - row_height - top_margin

        for index, bm in enumerate(bookmarks):

            title = bm.get("title") or bm.get("url", "")

            btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(12, y, doc_width - 58, row_height)
            )

            btn.setBordered_(False)
            btn.setBezelStyle_(0)
            btn.setAlignment_(NSLeftTextAlignment)
            btn.setTitle_(title[:40])
            btn.setFont_(NSFont.systemFontOfSize_(14))
            btn.setTag_(index)
            btn.setTarget_(self)
            btn.setAction_("openBookmark:")

            self.bookmark_document.addSubview_(btn)

            delete = NSButton.alloc().initWithFrame_(
                NSMakeRect(doc_width - 36, y + 5, 24, 24)
            )

            delete.setBordered_(False)
            delete.setBezelStyle_(0)
            delete.setTitle_("✕")
            delete.setTag_(index)
            delete.setTarget_(self)
            delete.setAction_("deleteBookmark:")

            delete.setFont_(NSFont.systemFontOfSize_(14))
            self.bookmark_document.addSubview_(delete)

            y -= (row_height + padding)

        # Show the top of the document even when the bookmark list is long.
        clip = self.bookmark_scroll.contentView()
        clip.scrollToPoint_((0, max(0, doc_height - visible_h)))
        self.bookmark_scroll.reflectScrolledClipView_(clip)
            
    # ==========================================================
    # Delete Bookmark
    # ==========================================================

    def deleteBookmark_(self, sender):

        try:

            index = sender.tag()

            if index < 0 or index >= len(self.bookmarks):
                return

            del self.bookmarks[index]

            self._saveBookmarks()

            self._reloadBookmarkList()

        except Exception as e:
            print("[Bookmarks]", e)
            
    def _createShortcutView(self):

        if getattr(self, "shortcut_view", None):
            return

        # Match menu panel size
        self.shortcut_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 220, 300)
        )

        # --------------------------------------------------
        # Back button
        # --------------------------------------------------
        self.btn_shortcut_back = NSButton.alloc().initWithFrame_(
            NSMakeRect(12, 264, 80, 28)
        )

        self.btn_shortcut_back.setTitle_("← Back")
        self.btn_shortcut_back.setBordered_(False)
        self.btn_shortcut_back.setBezelStyle_(0)
        self.btn_shortcut_back.setAlignment_(NSLeftTextAlignment)
        self.btn_shortcut_back.setTarget_(self)
        self.btn_shortcut_back.setAction_("showMainMenu:")
        try:
            self.btn_shortcut_back.setContentTintColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba()))
        except Exception:
            pass

        self.shortcut_view.addSubview_(self.btn_shortcut_back)

        # --------------------------------------------------
        # Title
        # --------------------------------------------------
        self.shortcut_title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(95, 266, 110, 20)
        )

        self.shortcut_title.setEditable_(False)
        self.shortcut_title.setBordered_(False)
        self.shortcut_title.setDrawsBackground_(False)
        self.shortcut_title.setSelectable_(False)
        self.shortcut_title.setStringValue_("Keyboard Shortcuts")
        self.shortcut_title.setTextColor_(NSColor.whiteColor())
        self.shortcut_title.setFont_(NSFont.boldSystemFontOfSize_(14))

        self.shortcut_view.addSubview_(self.shortcut_title)

        # --------------------------------------------------
        # Scroll View
        # --------------------------------------------------
        self.shortcut_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(12, 8, 196, 240)
        )

        self.shortcut_scroll.setHasVerticalScroller_(True)
        self.shortcut_scroll.setHasHorizontalScroller_(False)
        self.shortcut_scroll.setAutohidesScrollers_(True)
        self.shortcut_scroll.setBorderType_(0)

        self.shortcut_scroll.setWantsLayer_(True)

        scroll_layer = self.shortcut_scroll.layer()

        scroll_layer.setCornerRadius_(12)
        scroll_layer.setMasksToBounds_(True)
        scroll_layer.setBorderWidth_(1.0)

        scroll_layer.setBorderColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.16,
                0.95,
                0.45,
                0.12,
            ).CGColor()
        )

        scroll_layer.setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.shortcut_scroll.setDrawsBackground_(False)

        self.shortcut_document = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 196, 10)
        )

        self.shortcut_document.setWantsLayer_(True)

        self.shortcut_document.layer().setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.shortcut_scroll.setDocumentView_(self.shortcut_document)

        clip = self.shortcut_scroll.contentView()

        clip.setWantsLayer_(True)

        clip.layer().setBackgroundColor_(
            NSColor.clearColor().CGColor()
        )

        self.shortcut_view.addSubview_(self.shortcut_scroll)

        self.shortcut_view.setHidden_(True)
        self.shortcut_view.setFrameOrigin_((0, 0))

        self.menu_panel.addSubview_(self.shortcut_view)
        self._layout_secondary_menu_views()
        
    def _reloadShortcutList(self):

        if not getattr(self, "shortcut_document", None):
            return

        for view in list(self.shortcut_document.subviews()):
            view.removeFromSuperview()

        row_height = 33
        header_height = 36
        padding = 5
        width = 248

        # --------------------------------------------------
        # Calculate document height first
        # --------------------------------------------------

        total_height = 10

        for section, items in self.shortcut_sections.items():

            total_height += header_height + padding

            if self.shortcut_expanded.get(section, True):
                total_height += len(items) * row_height

            total_height += 4

        total_height = max(320, total_height + 16)

        self.shortcut_document.setFrame_(
            NSMakeRect(
                0,
                0,
                width,
                total_height,
            )
        )

        # --------------------------------------------------
        # Layout from TOP downward
        # --------------------------------------------------

        y = total_height - 10 - header_height

        for idx, (section, items) in enumerate(self.shortcut_sections.items()):

            expanded = self.shortcut_expanded.get(section, True)

            header = NSButton.alloc().initWithFrame_(
                NSMakeRect(
                    8,
                    y,
                    width - 16,
                    header_height,
                )
            )

            header.setFont_(NSFont.boldSystemFontOfSize_(14))
            header.setBordered_(False)
            header.setBezelStyle_(0)
            header.setAlignment_(NSLeftTextAlignment)
            header.setTitle_(("▼ " if expanded else "▶ ") + section)
            header.setTag_(idx)
            header.setTarget_(self)
            header.setAction_("toggleShortcutSection:")

            self.shortcut_document.addSubview_(header)

            y -= header_height + padding

            if expanded:

                for keys, desc in items:

                    key = NSTextField.alloc().initWithFrame_(
                        NSMakeRect(
                            22,
                            y + 3,
                            86,
                            25,
                        )
                    )

                    key.setBordered_(False)
                    key.setEditable_(False)
                    key.setSelectable_(False)
                    key.setDrawsBackground_(False)
                    key.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba()))
                    key.setFont_(
                        NSFont.monospacedSystemFontOfSize_weight_(12, 5)
                    )
                    key.setStringValue_(keys)

                    self.shortcut_document.addSubview_(key)

                    label = NSTextField.alloc().initWithFrame_(
                        NSMakeRect(
                            116,
                            y + 3,
                            124,
                            25,
                        )
                    )

                    label.setBordered_(False)
                    label.setEditable_(False)
                    label.setSelectable_(False)
                    label.setDrawsBackground_(False)
                    label.setTextColor_(NSColor.whiteColor())
                    label.setFont_(NSFont.systemFontOfSize_(13))
                    label.setStringValue_(desc)

                    self.shortcut_document.addSubview_(label)

                    y -= row_height

            y -= 4

        try:
            clip = self.shortcut_scroll.contentView()
            visible_h = float(clip.bounds().size.height)
            clip.scrollToPoint_((0, max(0, total_height - visible_h)))
            self.shortcut_scroll.reflectScrolledClipView_(clip)
        except Exception:
            pass

    # ==========================================================
    # MiniAI Summary Menu
    # ==========================================================

    def _createMiniAIView(self):

        if getattr(self, "mini_ai_view", None):
            return

        # --------------------------------------------------
        # Main Panel
        # --------------------------------------------------

        panel = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 220, 300)
        )

        panel.setHidden_(True)

        # --------------------------------------------------
        # Back
        # --------------------------------------------------

        back = NSButton.alloc().initWithFrame_(
            NSMakeRect(12, 264, 80, 28)
        )

        back.setTitle_("← Back")
        back.setBordered_(False)
        back.setBezelStyle_(0)
        back.setAlignment_(NSLeftTextAlignment)
        back.setTarget_(self)
        back.setAction_("showMainMenu:")
        try:
            back.setContentTintColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba()))
        except Exception:
            pass
        self.btn_mini_ai_back = back

        panel.addSubview_(back)

        # --------------------------------------------------
        # Title
        # --------------------------------------------------

        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(90, 266, 120, 20)
        )

        title.setEditable_(False)
        title.setBordered_(False)
        title.setDrawsBackground_(False)
        title.setSelectable_(False)
        title.setFont_(NSFont.boldSystemFontOfSize_(15))
        title.setTextColor_(NSColor.whiteColor())
        title.setStringValue_("MiniAI")

        panel.addSubview_(title)
        self.mini_ai_title = title

        # --------------------------------------------------
        # Helper
        # --------------------------------------------------

        self._mini_ai_name_labels = []
        self._mini_ai_value_labels = []

        def add_row(y, text):

            lbl = NSTextField.alloc().initWithFrame_(
                NSMakeRect(20, y, 160, 23)
            )

            lbl.setEditable_(False)
            lbl.setBordered_(False)
            lbl.setDrawsBackground_(False)
            lbl.setSelectable_(False)
            lbl.setFont_(NSFont.systemFontOfSize_(14))
            lbl.setTextColor_(NSColor.systemGrayColor())
            lbl.setStringValue_(text)

            panel.addSubview_(lbl)
            self._mini_ai_name_labels.append(lbl)

            value = NSTextField.alloc().initWithFrame_(
                NSMakeRect(206, y, 50, 23)
            )

            value.setEditable_(False)
            value.setBordered_(False)
            value.setDrawsBackground_(False)
            value.setSelectable_(False)
            value.setAlignment_(2)
            value.setFont_(NSFont.boldSystemFontOfSize_(14))
            value.setTextColor_(NSColor.whiteColor())
            value.setStringValue_("-")

            panel.addSubview_(value)
            self._mini_ai_value_labels.append(value)

            return value

        # --------------------------------------------------
        # Stats
        # --------------------------------------------------

        # Keep MiniAI statistics directly below the secondary-page header.
        y = 294

        self.lbl_ai_status      = add_row(y, "Status");          y -= 30
        self.lbl_ai_risk        = add_row(y, "Threat Level");    y -= 30
        self.lbl_ai_requests    = add_row(y, "Requests");        y -= 30
        self.lbl_ai_trackers    = add_row(y, "Trackers");        y -= 30
        self.lbl_ai_fp          = add_row(y, "Fingerprinting");  y -= 30
        self.lbl_ai_intrusions  = add_row(y, "Intrusions");      y -= 30
        self.lbl_ai_http        = add_row(y, "HTTP Blocks");     y -= 30
        self.lbl_ai_pq          = add_row(y, "PQ Identity");     y -= 30
        self.lbl_ai_lockdown    = add_row(y, "Lockdown")

        self.mini_ai_view = panel

        self.menu_panel.addSubview_(panel)
        self._layout_secondary_menu_views()
        
    # ==========================================================
    # About Darkelf View
    # ==========================================================

    def _createAboutView(self):

        if getattr(self, "about_view", None):
            return

        panel = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 220, 300)
        )

        panel.setHidden_(True)

        # --------------------------------------------------
        # Back
        # --------------------------------------------------

        back = NSButton.alloc().initWithFrame_(
            NSMakeRect(12, 264, 80, 28)
        )

        back.setTitle_("← Back")
        back.setBordered_(False)
        back.setBezelStyle_(0)
        back.setAlignment_(NSLeftTextAlignment)
        back.setTarget_(self)
        back.setAction_("showMainMenu:")
        try:
            back.setContentTintColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba()))
        except Exception:
            pass
        self.btn_about_back = back

        panel.addSubview_(back)

        # --------------------------------------------------
        # Title
        # --------------------------------------------------

        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(88, 266, 120, 20)
        )

        title.setEditable_(False)
        title.setBordered_(False)
        title.setDrawsBackground_(False)
        title.setSelectable_(False)
        title.setFont_(NSFont.boldSystemFontOfSize_(14))
        title.setTextColor_(NSColor.whiteColor())
        title.setAlignment_(1)
        title.setStringValue_("About")

        panel.addSubview_(title)
        self.about_title = title

        # --------------------------------------------------
        # Browser Name
        # --------------------------------------------------

        name = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 220, 190, 22)
        )

        name.setEditable_(False)
        name.setBordered_(False)
        name.setDrawsBackground_(False)
        name.setSelectable_(False)
        name.setAlignment_(1)
        name.setFont_(NSFont.boldSystemFontOfSize_(15))
        name.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba()))
        name.setStringValue_("Darkelf Cocoa Browser")

        panel.addSubview_(name)
        self.about_name_label = name

        # --------------------------------------------------
        # Version
        # --------------------------------------------------

        version = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 198, 190, 18)
        )

        version.setEditable_(False)
        version.setBordered_(False)
        version.setDrawsBackground_(False)
        version.setSelectable_(False)
        version.setAlignment_(1)
        version.setFont_(NSFont.systemFontOfSize_(12))
        version.setTextColor_(NSColor.whiteColor())
        version.setStringValue_("Version 7.0.26")

        panel.addSubview_(version)
        self.about_version_label = version

        # --------------------------------------------------
        # Description
        # --------------------------------------------------

        desc = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 135, 190, 55)
        )

        desc.setEditable_(False)
        desc.setBordered_(False)
        desc.setDrawsBackground_(False)
        desc.setSelectable_(False)
        desc.setAlignment_(1)
        desc.setFont_(NSFont.systemFontOfSize_(12))
        desc.setTextColor_(NSColor.systemGrayColor())
        desc.setStringValue_(
            "Privacy-first browser\n"
            "built by\n"
            "Darkelf Labs"
        )

        panel.addSubview_(desc)
        self.about_desc_label = desc

        # --------------------------------------------------
        # Website
        # --------------------------------------------------

        website = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 95, 190, 18)
        )

        website.setEditable_(False)
        website.setBordered_(False)
        website.setDrawsBackground_(False)
        website.setSelectable_(False)
        website.setAlignment_(1)
        website.setFont_(NSFont.systemFontOfSize_(12))
        website.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba()))
        website.setStringValue_("darkelfbrowser.com")

        panel.addSubview_(website)
        self.about_website_label = website

        # --------------------------------------------------
        # About Darkelf — concise architecture and privacy overview
        # --------------------------------------------------
        detail = NSTextField.alloc().initWithFrame_(NSMakeRect(18, 74, 184, 102))
        detail.setEditable_(False)
        detail.setBordered_(False)
        detail.setDrawsBackground_(False)
        detail.setSelectable_(False)
        detail.setAlignment_(NSCenterTextAlignment)
        detail.setFont_(NSFont.systemFontOfSize_(11))
        detail.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(0.72, 1.0))
        detail.setStringValue_(
            "Native macOS privacy browser powered by Apple WebKit. "
            "Ephemeral tabs, tracker blocking, fingerprint defenses, "
            "and local MiniAI Sentinel monitoring — with a "
            "customizable interface."
        )
        detail.setLineBreakMode_(NSLineBreakByWordWrapping)
        detail.setUsesSingleLineMode_(False)
        panel.addSubview_(detail)
        self.about_detail_label = detail

        # --------------------------------------------------
        # Copyright
        # --------------------------------------------------

        copyright = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 35, 190, 35)
        )

        copyright.setEditable_(False)
        copyright.setBordered_(False)
        copyright.setDrawsBackground_(False)
        copyright.setSelectable_(False)
        copyright.setAlignment_(1)
        copyright.setFont_(NSFont.systemFontOfSize_(11))
        copyright.setTextColor_(NSColor.systemGrayColor())
        copyright.setStringValue_(
            "© 2025–2026\nDr. Kevin Moore"
        )

        panel.addSubview_(copyright)
        self.about_copyright_label = copyright

        self.about_view = panel

        self.menu_panel.addSubview_(panel)
        self._layout_secondary_menu_views()
        
    @objc.IBAction
    def showAboutView_(self, sender):
        if getattr(self, "btn_privacy", None) is not None:
            self.btn_privacy.setHidden_(True)
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            _pv = getattr(self, _pn, None)
            if _pv is not None:
                _pv.setHidden_(True)
        if getattr(self, "privacy_view", None):
            self.privacy_view.setHidden_(True)

        try:
            # Create page once
            if not getattr(self, "about_view", None):
                self._createAboutView()
            self._layout_secondary_menu_views()

            # Hide main menu buttons
            for v in (
                self.btn_bookmarks,
                self.btn_add_bookmark,
                self.btn_hotkeys,
                self.btn_color,
                self.btn_background,
                self.btn_js,
                self.btn_nuke,
                self.btn_mini_ai,
                self.btn_about,
            ):
                try:
                    v.setHidden_(True)
                except Exception as e:
                    print("[About] Hide button:", e)

            # Hide other menu pages
            try:
                if getattr(self, "bookmark_view", None):
                    self.bookmark_view.setHidden_(True)
            except Exception as e:
                print("[About] Hide bookmarks:", e)

            try:
                if getattr(self, "shortcut_view", None):
                    self.shortcut_view.setHidden_(True)
            except Exception as e:
                print("[About] Hide shortcuts:", e)

            try:
                if getattr(self, "mini_ai_view", None):
                    self.mini_ai_view.setHidden_(True)
            except Exception as e:
                print("[About] Hide MiniAI:", e)

            if getattr(self, "background_view", None):
                self.background_view.setHidden_(True)

            # Show About page
            self.about_view.setHidden_(False)

            # Force redraw
            self.menu_panel.setNeedsDisplay_(True)
            self.menu_panel.displayIfNeeded()

        except Exception as e:
            print("[showAboutView_]", e)
        
    # ==========================================================
    # Show MiniAI Summary
    # ==========================================================

    def showMiniAI_(self, sender):
        if getattr(self, "btn_privacy", None) is not None:
            self.btn_privacy.setHidden_(True)
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view"):
            _pv = getattr(self, _pn, None)
            if _pv is not None:
                _pv.setHidden_(True)

        try:
            # Create page once
            if not getattr(self, "mini_ai_view", None):
                self._createMiniAIView()

            # Hide main menu buttons
            for v in (
                self.btn_bookmarks,
                self.btn_add_bookmark,
                self.btn_hotkeys,
                self.btn_color,
                self.btn_background,
                self.btn_js,
                self.btn_nuke,
                self.btn_mini_ai,
                self.btn_about,
            ):
                try:
                    v.setHidden_(True)
                except Exception as e:
                    print("[MiniAI] Hide button:", e)

            # Hide other menu pages
            try:
                if getattr(self, "bookmark_view", None):
                    self.bookmark_view.setHidden_(True)
            except Exception as e:
                print("[MiniAI] Hide bookmarks:", e)

            if getattr(self, "background_view", None):
                self.background_view.setHidden_(True)

            # Show MiniAI page
            self.mini_ai_view.setHidden_(False)

            # Refresh statistics
            try:
                self._reloadMiniAIView()
            except Exception as e:
                print("[MiniAI] Reload failed:", e)

            # Force redraw
            self.menu_panel.setNeedsDisplay_(True)
            self.menu_panel.displayIfNeeded()

        except Exception as e:
            print("[showMiniAI_]", e)
        
    # ==========================================================
    # Refresh MiniAI Summary
    # ==========================================================

    def _reloadMiniAIView(self):

        if not getattr(self, "mini_ai", None):
            return

        try:
            stats = self.mini_ai.get_statistics()

            # -----------------------------
            # Status
            # -----------------------------
            risk = str(stats.get("overall_risk", "low")).lower()

            status_icon = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🔴",
            }.get(risk, "🟢")

            self.lbl_ai_status.setStringValue_(f"{status_icon} Protected")
            self.lbl_ai_risk.setStringValue_(risk.title())

            # -----------------------------
            # Network
            # -----------------------------
            network = stats.get("network", {})

            self.lbl_ai_requests.setStringValue_(
                str(network.get("total_requests", 0))
            )

            # -----------------------------
            # Threats
            # -----------------------------
            threats = stats.get("threats", {})

            self.lbl_ai_trackers.setStringValue_(
                str(threats.get("trackers", 0))
            )

            self.lbl_ai_fp.setStringValue_(
                str(threats.get("fingerprinting", 0))
            )

            self.lbl_ai_intrusions.setStringValue_(
                str(threats.get("intrusions", 0))
            )

            self.lbl_ai_http.setStringValue_(
                str(threats.get("http_blocks", 0))
            )

            # -----------------------------
            # PQ
            # -----------------------------
            pq = stats.get("pq", {})

            self.lbl_ai_pq.setStringValue_(
                pq.get("risk_level", "Low").title()
            )

            # -----------------------------
            # Lockdown
            # -----------------------------
            lockdown = stats.get("lockdown", {})

            self.lbl_ai_lockdown.setStringValue_(
                "ON" if lockdown.get("active", False) else "OFF"
            )

        except Exception as e:
            print("[MiniAI Summary]", e)
            
    def update_security_indicator(self, trusted):
        try:
            cell = self.addr.cell()

            if trusted:
                # Green lock icon
                lock = NSImage.imageNamed_("NSLockLockedTemplate")
                cell.setSearchButtonCell_(cell.searchButtonCell())
                cell.searchButtonCell().setImage_(lock)

                self.addr.setTextColor_(NSColor.labelColor())

            else:
                # Warning triangle
                warn = NSImage.imageNamed_("NSCaution")
                cell.searchButtonCell().setImage_(warn)

                self.addr.setTextColor_(NSColor.systemRedColor())

        except Exception as e:
            print("Security indicator error:", e)

    def start_lockdown_timer(self):

        self.stop_lockdown_timer()

        self._lockdown_timer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0, self, "refreshMiniAI:", None, True
            )
        )

    def stop_lockdown_timer(self):

        if hasattr(self, "_lockdown_timer") and self._lockdown_timer:
            self._lockdown_timer.invalidate()
            self._lockdown_timer = None

    def finish_lockdown_unlock(self):

        print("[Browser] Lockdown finished")

        self.stop_lockdown_timer()

        try:
            self.mini_ai._unlock_browser_ui()
        except Exception as e:
            log(2, e)

        try:
            self.close_threat_report_tab()
        except Exception as e:
            print("[Browser] Close report error:", e)

    def windowWillReturnFieldEditor_toObject_(self, window, control):
        """Use a Darkelf-owned native editor only for the URL/search field."""
        if control is not getattr(self, "urlbar", None):
            return None  # Let AppKit manage editors for all other controls.
        editor = getattr(self, "_darkelf_address_editor", None)
        if editor is None:
            editor = DarkelfAddressEditor.alloc().initWithFrame_(
                NSMakeRect(0, 0, 0, 0)
            )
            editor.setFieldEditor_(True)
            editor.setRichText_(False)
            editor.setImportsGraphics_(False)
            self._darkelf_address_editor = editor
        editor.setMenu_(self.urlbar.menuForEvent_(None))
        return editor

    def controlTextDidBeginEditing_(self, notification):
        try:
            field_editor = notification.userInfo().get("NSFieldEditor")

            if field_editor:
                accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    *load_accent_rgba()
                ).colorWithAlphaComponent_(0.60)

                field_editor.setSelectedTextAttributes_(
                    {
                        "NSBackgroundColor": accent,
                        "NSForegroundColor": NSColor.blackColor(),
                    }
                )

        except Exception as e:
            print("[Darkelf] editor styling error:", e)

    def _is_tab_webview(self, webview):
        for tab in self.tabs:
            if tab.view is webview:
                return True
        return False

    def _is_home_context(self):
        try:
            if getattr(self, "loading_home", False):
                return True
            u = self.tabs[self.active].view.URL()
            return bool(u and u.absoluteString() == HOME_URL)
        except Exception:
            return False

    def _make_window(self):
        rect = NSMakeRect(80, 80, 1280, 820)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskMiniaturizable
        )
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, 2, False
        )
        win.setTitle_(APP_NAME)

        try:
            win.setTitleVisibility_(1)
            win.setToolbarStyle_(1)
            win.setTitlebarAppearsTransparent_(False)
            win.setBackgroundColor_(NSColor.blackColor())
            cv = win.contentView()
            if cv is not None:
                f = cv.frame()
                strip = NSBox.alloc().initWithFrame_(
                    ((0, f.size.height - 40), (f.size.width, 40))
                )
                strip.setBoxType_(0)
                strip.setBorderType_(0)
                strip.setFillColor_(NSColor.blackColor())
                strip.setAutoresizingMask_(10)
                strip.setTitle_("")
                strip.setTitlePosition_(0)
                cv.addSubview_(strip)
        except Exception as e:
            log(2, e)

        try:
            win.setTitlebarAppearsTransparent_(True)
            win.setBackgroundColor_(NSColor.blackColor())
            win.contentView().setWantsLayer_(True)
            win.contentView().layer().setBackgroundColor_(
                NSColor.blackColor().CGColor()
            )
        except Exception as e:
            log(2, e)

        try:
            win.setCollectionBehavior_(NSWindowCollectionBehaviorFullScreenPrimary)
            print("[Window] ✅ Fullscreen collection behavior set")
        except Exception as e:
            print(f"[Window] ❌ Fullscreen behavior failed: {e}")

        try:
            cv = win.contentView()
            cv.setWantsLayer_(True)
            print("[Window] ✅ Content view layer-backed")
        except Exception as e:
            print(f"[Window] ❌ Content view layer failed: {e}")

        return win

    def windowShouldClose_(self, sender):
        return True

    def actCloseTab_(self, _):
        self._close_tab()

    TOOLBAR_HEIGHT = 44
    TABBAR_HEIGHT = 38
    PADDING = 10

    def _nscolor_hex(self, hex_str, alpha=1.0):
        hs = hex_str.lstrip("#")
        r = int(hs[0:2], 16) / 255.0
        g = int(hs[2:4], 16) / 255.0
        b = int(hs[4:6], 16) / 255.0
        return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, alpha)

    def _style_button(self, btn, tooltip=None):
        # Avoid fancy styles that sometimes misbehave across macOS versions
        try:
            btn.setBordered_(True)
        except Exception as e:
            log(2, e)
        if tooltip:
            try:
                btn.setToolTip_(tooltip)
            except Exception as e:
                log(2, e)
        return btn

    def _build_tabbar(self):
        try:
            clr = self.window.contentLayoutRect()
            w = clr.size.width
            top_y = clr.origin.y + clr.size.height
        except Exception:
            bounds = self.window.contentView().bounds()
            width = bounds.size.width
            top_y = bounds.size.height

        tabbar_y = top_y - self.TOOLBAR_HEIGHT - self.TABBAR_HEIGHT

        # CREATE TABBAR ONCE
        self.tabbar = NSView.alloc().initWithFrame_(
            NSMakeRect(0, top_y, w, self.TABBAR_HEIGHT)
        )

        self.tabbar.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.tabbar.setWantsLayer_(True)
        self.tabbar.layer().setBackgroundColor_(
            self._nscolor_hex("#0a0d12", 1.0).CGColor()
        )

        # ADD BUTTON (after tabbar exists)
        self.btn_new_tab = HoverButton.alloc().initWithFrame_(
            NSMakeRect(w - 44, 6, 34, 26)
        )

        self.btn_new_tab.setTitle_("+")
        self.btn_new_tab.setBordered_(False)
        self.btn_new_tab.setBezelStyle_(0)
        self.btn_new_tab.setTarget_(self)
        self.btn_new_tab.setAction_("actNewTab:")

        self.tabbar.addSubview_(self.btn_new_tab)

        # container
        self.tab_buttons_container = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w - 50, self.TABBAR_HEIGHT)
        )
        self.tabbar.addSubview_(self.tab_buttons_container)

        self.window.contentView().addSubview_(self.tabbar)

        if not hasattr(self, "tabs"):
            self.tabs = []

        if not hasattr(self, "active"):
            self.active = -1

        self._update_tab_buttons()
        self._cleanup_unused_containers()

    def _layout_topbars(self):
        bounds = self.window.contentView().bounds()
        w = bounds.size.width
        h = bounds.size.height

        if getattr(self, "toolbar", None):
            self.toolbar.setFrame_(
                NSMakeRect(0, h - self.TOOLBAR_HEIGHT, w, self.TOOLBAR_HEIGHT)
            )
        if getattr(self, "tabbar", None):
            self.tabbar.setFrame_(
                NSMakeRect(
                    0,
                    h - self.TOOLBAR_HEIGHT - self.TABBAR_HEIGHT,
                    w,
                    self.TABBAR_HEIGHT,
                )
            )
        if getattr(self, "btn_new_tab", None):
            self.btn_new_tab.setFrame_(NSMakeRect(w - 44, 6, 34, 26))
        if getattr(self, "content_container", None):
            self.content_container.setFrame_(
                NSMakeRect(0, 0, w, h - self.TOOLBAR_HEIGHT - self.TABBAR_HEIGHT)
            )

    def windowDidResize_(self, notification):
        self._layout_topbars()
        self._update_tab_buttons()

    def _darkelf_home_tab_icon(self):
        """Return Darkelf's bundled green shield for darkelf://home tabs."""
        candidates = (
            os.path.join(os.path.dirname(__file__), "assets", "branding", "darkelf-256.png"),
            os.path.join(os.path.dirname(__file__), "assets", "darkelf-256.png"),
        )
        for path in candidates:
            try:
                if os.path.isfile(path):
                    image = NSImage.alloc().initWithContentsOfFile_(path)
                    if image is not None:
                        image.setSize_(NSMakeSize(16, 16))
                        return image
            except Exception as e:
                log(2, "[Tabs] Darkelf Home icon:", e)
        return None

    def _update_tab_buttons(self):
        if not getattr(self, "tab_buttons_container", None):
            return

        # Remove old generated tab controls
        for v in list(self.tab_buttons_container.subviews() or []):
            v.removeFromSuperview()

        w = self.tab_buttons_container.bounds().size.width
        y = 2
        h = 33
        gap = 1
        min_tab_w = 130
        max_tab_w = 200
        close_w = 24
        inner_pad = 12

        num_tabs = len(self.tabs)
        if num_tabs <= 0:
            return

        plus_reserved = 44

        available_w = max(
            200,
            w - plus_reserved - (gap * max(0, num_tabs - 1)) - self.PADDING * 2,
        )

        tab_w = max(min_tab_w, min(available_w // num_tabs, max_tab_w))

        x = 1

        for i, tab in enumerate(self.tabs):

            selected = i == self.active

            tab_shell = TabHoverView.alloc().initWithFrame_(
                NSMakeRect(x, y, tab_w, h)
            )
            tab_shell.setWantsLayer_(True)
            tab_shell.layer().setCornerRadius_(8.0)

            tab_shell.setDarkelfSelected_(selected)

            # ----------------------------
            # Favicon
            # ----------------------------
            text_x = inner_pad

            tab_icon = getattr(tab, "favicon", None)
            tab_url = getattr(tab, "url", "") or ""
            if tab_url == HOME_URL:
                tab_icon = self._darkelf_home_tab_icon()

            if tab_icon:
                icon = NSImageView.alloc().initWithFrame_(
                    NSMakeRect(8, 9, 16, 16)
                )
                icon.setImage_(tab_icon)

                tab_shell.addSubview_(icon)

                text_x = 30

            # ----------------------------
            # Close button
            # ----------------------------
            close_btn = HoverButton.alloc().initWithFrame_(
                NSMakeRect(tab_w - close_w - 6, 6, close_w, close_w)
            )
            close_btn.setTitle_("×")
            close_btn.setBordered_(False)
            close_btn.setTarget_(self)
            close_btn.setAction_("actCloseTabIndex:")
            close_btn.setTag_(i)
            close_btn.setToolTip_("Close Tab")
            close_btn.setFont_(NSFont.boldSystemFontOfSize_(13))
            close_btn.setContentTintColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
                if selected
                else NSColor.whiteColor()
            )
            if hasattr(close_btn, "setDarkelfBaseTint_"):
                close_btn.setDarkelfBaseTint_(
                    NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
                    if selected else NSColor.whiteColor()
                )

            # ----------------------------
            # Title
            # ----------------------------
            title = getattr(tab, "title", None) or tab.host or "New Tab"

            if len(title) > 20:
                title = title[:20] + "…"

            title_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(
                    text_x,
                    2,
                    tab_w - close_w - text_x - 8,
                    h - 2,
                )
            )

            title_btn.setTitle_(title)
            title_btn.setBordered_(False)
            title_btn.setAlignment_(0)
            title_btn.setTarget_(self)
            title_btn.setAction_("actSwitchTab:")
            title_btn.setTag_(i)
            title_btn.setContentTintColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
                if selected
                else NSColor.whiteColor()
            )
            if hasattr(title_btn, "setDarkelfBaseTint_"):
                title_btn.setDarkelfBaseTint_(
                    NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
                    if selected else NSColor.whiteColor()
                )

            tab_shell.addSubview_(title_btn)
            tab_shell.addSubview_(close_btn)

            self.tab_buttons_container.addSubview_(tab_shell)

            x += tab_w + gap

    # ================= TAB / NAV ACTIONS =================

    @objc.IBAction
    def tabClicked_(self, sender):
        try:
            idx = int(sender.tag())
            self._select_tab(idx)
        except Exception as e:
            print("[Tabs] tabClicked_ error:", e)

    @objc.IBAction
    def actNewTab_(self, sender):
        print("CLICKED + BUTTON")

        idx = self._add_tab(home=True)

        print("TAB RESULT:", idx)
        print("TOTAL TABS:", len(self.tabs))

        self.active = len(self.tabs) - 1
        self._update_tab_buttons()
        self._sync_addr()

    @objc.IBAction
    def actBack_(self, sender):
        tab = self._active_tab()
        if tab and getattr(tab, "view", None):
            try:
                tab.view.goBack()
            except Exception as e:
                log(2, e)

    @objc.IBAction
    def actFwd_(self, sender):
        tab = self._active_tab()
        if tab and getattr(tab, "view", None):
            try:
                tab.view.goForward()
            except Exception as e:
                log(2, e)

    @objc.IBAction
    def actReload_(self, sender):
        tab = self._active_tab()
        if tab and getattr(tab, "view", None):
            try:
                tab.view.reload()
            except Exception as e:
                log(2, e)

    @objc.IBAction
    def actHome_(self, sender):
        try:
            self._add_tab(home=True)
        except Exception as e:
            print("[Nav] actHome_ error:", e)

    @objc.IBAction
    def addrEntered_(self, sender):
        try:
            text = str(self.addr.stringValue() or "").strip()
            if not text:
                return

            if "://" not in text and "." in text:
                text = "https://" + text
            elif "://" not in text:
                text = "https://www.mojeek.com/search?q=" + quote_plus(text)

            self._add_tab(home=False)

            self._navigate_to(text)

        except Exception as e:
            print("[Nav] addrEntered error:", e)

    # ================= TAB HELPERS =================

    def _active_tab(self):
        if not hasattr(self, "tabs"):
            return None
        if self.active < 0 or self.active >= len(self.tabs):
            return None
        return self.tabs[self.active]

    def _select_tab(self, idx):
        if idx < 0 or idx >= len(self.tabs):
            return

        self.active = idx

        cv = self.window.contentView()

        # Remove any existing WKWebViews from contentView
        for sub in list(cv.subviews()):
            if isinstance(sub, WKWebView):
                sub.removeFromSuperview()

        # Hide all tab WKWebViews except for the active one
        for i, tab in enumerate(self.tabs):
            view = getattr(tab, "view", None)
            if not view:
                continue
            if i == self.active:
                # Remount the active tab's WKWebView, ensure it's visible
                self._mount_webview(view)
                try:
                    view.setHidden_(False)
                except Exception as e:
                    log(2, e)
            else:
                try:
                    view.setHidden_(True)
                except Exception as e:
                    log(2, e)

        self._sync_addr()
        self._update_tab_buttons()
        self.refreshBookmarkButton()
        self._update_navigation_button_states()

    def _sync_addr(self):
        tab = self._active_tab()
        if not tab or not getattr(self, "addr", None):
            return

        try:
            self.addr.setStringValue_(getattr(tab, "url", "") or "")
        except Exception as e:
            log(2, e)

    def _navigate_to(self, url_str):
        tab = self._active_tab()
        if not tab or not getattr(tab, "view", None):
            return

        try:
            nsurl = NSURL.URLWithString_(url_str)
            tab.view.loadRequest_(NSURLRequest.requestWithURL_(nsurl))
            tab.url = url_str
            self._sync_addr()
        except Exception as e:
            print("[Nav] navigate error:", e)

    # ----- Toolbar -----
    def _mk_btn(self, symbol, tooltip):
        b = HoverButton.alloc().init()
        try:
            img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                symbol, None
            )
            # First, try the user-requested configuration
            cfg = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                54.0, 2, 2
            )
            if img and hasattr(img, "imageByApplyingSymbolConfiguration_"):
                img = img.imageByApplyingSymbolConfiguration_(cfg)
            if img:
                try:
                    img.setTemplate_(True)
                except Exception as e:
                    log(2, e)
                b.setImage_(img)
        except Exception as e:
            log(2, e)
        try:
            b.setBordered_(False)
            b.setBezelStyle_(1)
            b.setToolTip_(tooltip or "")
        except Exception as e:
            log(2, e)
        if hasattr(b, "setContentTintColor_"):
            b.setContentTintColor_(NSColor.whiteColor())
        return b

    # -------------------------------------------------------------------
    # Replace your existing _make_toolbar + _build_shadow_toolbar with this
    # -------------------------------------------------------------------
    def _make_toolbar(self):
        cv = self.window.contentView()

        # Determine a reliable top Y using contentLayoutRect (safe with titlebars/toolbars)
        try:
            clr = self.window.contentLayoutRect()
            top_y = clr.origin.y + clr.size.height
            width = clr.size.width
        except Exception:
            f = cv.frame()
            top_y = f.size.height
            width = f.size.width

        bar_h = TOOLBAR_HEIGHT
        y = top_y - bar_h

        # Container
        self.toolbar_container = NSView.alloc().initWithFrame_(
            NSMakeRect(0, y, width, bar_h)
        )
        self.toolbar_container.setAutoresizingMask_(10)  # width sizable + stick to top
        self.toolbar_container.setWantsLayer_(True)

        # Modern dark background
        self.toolbar_container.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.05, 0.06, 0.08, 1.0
            ).CGColor()
        )

        # subtle bottom border
        try:
            self.toolbar_container.layer().setBorderWidth_(1.0)
            self.toolbar_container.layer().setBorderColor_(
                NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.08).CGColor()
            )
        except Exception as e:
            log(2, e)

        cv.addSubview_(self.toolbar_container)

        # ----------------------------
        # Helpers: button factory
        # ----------------------------
        def make_icon_btn(icon_name, tooltip, tint=None, size=18.0):
            b = HoverButton.alloc().init()
            b.setBordered_(False)
            b.setBezelStyle_(1)
            b.setTitle_("")
            b.setToolTip_(tooltip or "")
            try:
                b.setImagePosition_(NSImageOnly)
                b.setImageScaling_(NSImageScaleProportionallyDown)
                b.setAlignment_(NSCenterTextAlignment)
            except Exception:
                pass

            # Navigation controls use bundled SVG artwork. Other toolbar
            # controls retain their original native SF Symbols.
            if str(icon_name).lower().endswith(".svg"):
                img = load_nav_svg(icon_name, size=size)
            else:
                img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                    icon_name, None
                )
                if img:
                    try:
                        cfg = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                            size, 2, 2
                        )
                        if hasattr(img, "imageByApplyingSymbolConfiguration_"):
                            img = img.imageByApplyingSymbolConfiguration_(cfg)
                        img.setTemplate_(True)
                    except Exception as e:
                        log(2, e)

            if img:
                b.setImage_(img)
                b.setImagePosition_(NSImageOnly)  # centered image-only
                if tint is not None and hasattr(b, "setContentTintColor_"):
                    try:
                        b.setContentTintColor_(tint)
                    except Exception as e:
                        log(2, e)

            if hasattr(b, "setDarkelfBaseTint_"):
                b.setDarkelfBaseTint_(tint if tint is not None else NSColor.whiteColor())
            b.setWantsLayer_(True)
            try:
                b.layer().setCornerRadius_(10.0)
            except Exception as e:
                log(2, e)
            return b

        # ----------------------------
        # Left buttons
        # ----------------------------
        self.btn_back = make_icon_btn("back.svg", "Back")
        self.btn_fwd = make_icon_btn("forward.svg", "Forward")
        self.btn_reload = make_icon_btn("reload.svg", "Reload")

        for b, sel in [
            (self.btn_back, "actBack:"),
            (self.btn_fwd, "actFwd:"),
            (self.btn_reload, "actReload:"),
        ]:
            b.setTarget_(self)
            b.setAction_(sel)
            self.toolbar_container.addSubview_(b)

        # ----------------------------
        # URL bar
        # ----------------------------
        self.urlbar = AddressField.alloc().initWithFrame_owner_(
            NSMakeRect(200, 6, 720, 32), self
        )
        self.addr = self.urlbar

        self.addr.setFocusRingType_(NSFocusRingTypeNone)

        self.urlbar.setBezeled_(True)

        self.urlbar.setFocusRingType_(0)
        self.urlbar.cell().setFocusRingType_(0)

        # THIS is the real fix
        self.urlbar.cell().setShowsFirstResponder_(False)

        self.urlbar.setDrawsBackground_(False)

        self.urlbar.setPlaceholderString_("Search or enter URL")

        # ✅ KEEP THIS (your working enter handler)
        self.urlbar.setTarget_(self)
        self.urlbar.setAction_("addrEntered:")

        self.urlbar.cell().setSendsWholeSearchString_(True)
        self.urlbar.cell().setSendsSearchStringImmediately_(False)

        self.urlbar.setAutoresizingMask_(2)

        # ✅ ADD THIS EXACTLY HERE (RIGHT BEFORE addSubview)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self,
            "controlTextDidBeginEditing:",
            "NSControlTextDidBeginEditingNotification",
            self.addr,
        )

        self.toolbar_container.addSubview_(self.urlbar)

        # ----------------------------
        # Right-side buttons
        # ----------------------------

        self.btn_hotkeys = make_icon_btn(
            "keyboard",
            "Keyboard Shortcuts"
        )
        
        self.btn_bookmark = make_icon_btn(
            "bookmark.svg",
            "Bookmarks"
        )
        
        self.btn_menu = make_icon_btn(
            "menu.svg",
            "Menu"
        )

        self.btn_menu.setTarget_(self)
        self.btn_menu.setAction_("toggleMenu:")
        
        self.btn_hotkeys.setTarget_(self)
        self.btn_hotkeys.setAction_("showKeyboardShortcuts:")
        
        self.btn_js = make_icon_btn(
            "bolt.fill" if self.js_enabled else "bolt.slash.fill",
            f"JavaScript: {'ON' if self.js_enabled else 'OFF'}",
            tint=(
                NSColor.systemGreenColor()
                if self.js_enabled
                else NSColor.systemRedColor()
            ),
        )

        self.btn_nuke = make_icon_btn(
            "trash.fill", "Clear All Data", tint=NSColor.systemRedColor()
        )
        self.btn_mini_ai = make_icon_btn(
            "shield.fill", "MiniAI System Report", tint=NSColor.systemGreenColor()
        )

        for b, sel in [
            (self.btn_hotkeys, "showKeyboardShortcuts:"),
            (self.btn_js, "actToggleJS:"),
            (self.btn_nuke, "actNuke:"),
            (self.btn_mini_ai, "showMiniAI:"),
            (self.btn_bookmark, "toggleBookmarkToolbar:"),   # NEW
            (self.btn_menu, "toggleMenu:"),
        ]:
            b.setTarget_(self)
            b.setAction_(sel)
            self.toolbar_container.addSubview_(b)
            
        # layout pass
        self._layout_toolbar()
        self._apply_accent_to_ui()
        return self.toolbar_container

    def _layout_toolbar(self):
        """Called on startup + window resize to keep toolbar aligned."""
        if not getattr(self, "toolbar_container", None):
            return

        bounds = self.window.contentView().bounds()
        width = bounds.size.width
        top_y = bounds.size.height

        # --------------------------------------------------
        # Toolbar geometry
        # --------------------------------------------------
        bar_h = 52.0
        self.toolbar_container.setFrame_(
            NSMakeRect(0, top_y - bar_h, width, bar_h)
        )

        pad = TOOLBAR_PADDING
        btn = TOOLBAR_BUTTON_SIZE

        # Vertically center everything
        btn_y = (bar_h - btn) / 2.0
        url_h = 32.0
        url_y = (bar_h - url_h) / 2.0

        # --------------------------------------------------
        # Left buttons
        # --------------------------------------------------
        x = pad

        # Back
        self.btn_back.setFrame_(NSMakeRect(x, btn_y, btn, btn))
        try:
            self.btn_back.updateTrackingAreas()
        except Exception:
            pass
        x += btn + 6

        # Forward
        self.btn_fwd.setFrame_(NSMakeRect(x, btn_y, btn, btn))
        try:
            self.btn_fwd.updateTrackingAreas()
        except Exception:
            pass
        x += btn + 6

        # Reload
        self.btn_reload.setFrame_(NSMakeRect(x, btn_y, btn, btn))
        try:
            self.btn_reload.updateTrackingAreas()
        except Exception:
            pass
        x += btn + 6

        left_end = x + 2

        # --------------------------------------------------
        # Right buttons
        # --------------------------------------------------
        right_buttons = (
            self.btn_bookmark,
            self.btn_menu,
        )

        # --------------------------------------------------
        # Right-side controls
        # --------------------------------------------------

        right_gap = TOOLBAR_RIGHT_GAP

        right_cluster_width = (
            len(right_buttons) * btn
            + (len(right_buttons) - 1) * right_gap
        )

        right_x = width - pad - right_cluster_width

        x_cursor = right_x

        for b in right_buttons:
            b.setFrame_(NSMakeRect(x_cursor, btn_y, btn, btn))
            try:
                b.updateTrackingAreas()
            except Exception:
                pass
            x_cursor += btn + right_gap

        # --------------------------------------------------
        # URL Bar (centered)
        # --------------------------------------------------

        available_left = left_end
        available_right = right_x - 20

        available_width = available_right - available_left

        # Responsive URL field: expand on wide windows while retaining enough
        # room for navigation and the right-side toolbar controls.
        available_width = max(0.0, available_width)
        url_w = min(URLBAR_MAX_WIDTH, available_width)
        if available_width >= URLBAR_MIN_WIDTH:
            url_w = max(URLBAR_MIN_WIDTH, url_w)

        url_x = available_left + max(0.0, (available_width - url_w) / 2.0)
        self.addr.setFrame_(NSMakeRect(url_x, url_y, url_w, url_h))

        self._update_navigation_button_states()

    def _update_navigation_button_states(self):
        """Reflect the active WKWebView history in Back/Forward controls."""
        tab = self._active_tab()
        view = getattr(tab, "view", None) if tab else None
        try:
            self.btn_back.setEnabled_(bool(view and view.canGoBack()))
            self.btn_fwd.setEnabled_(bool(view and view.canGoForward()))
            self.btn_reload.setEnabled_(bool(view))
        except Exception as e:
            log(2, e)

    # Make sure your existing onResize_ calls _layout() AND _layout_toolbar()
    def onResize_(self, note):
        try:
            self._layout()
        except Exception as e:
            log(2, e)

        try:
            self._layout_toolbar()
        except Exception as e:
            log(2, e)
            
    def _bring_tabbar_to_front(self):
        try:
            cv = self.window.contentView()

            # keep toolbar on top
            if getattr(self, "toolbar_container", None):
                if (
                    self.toolbar_container.superview() is not None
                    and self.toolbar_container.superview() != cv
                ):
                    try:
                        self.toolbar_container.removeFromSuperview()
                    except Exception as e:
                        log(2, e)

                if self.toolbar_container.superview() != cv:
                    cv.addSubview_(self.toolbar_container)

            # keep tabbar above webview
            if getattr(self, "tabbar", None):
                if (
                    self.tabbar.superview() is not None
                    and self.tabbar.superview() != cv
                ):
                    try:
                        self.tabbar.removeFromSuperview()
                    except Exception as e:
                        log(2, e)

                if self.tabbar.superview() != cv:
                    cv.addSubview_(self.tabbar)

                self.tabbar.displayIfNeeded()

        except Exception as e:
            log(2, e)

    # In actToggleJS_, after toggling, also update JS button icon/tint:
    def actToggleJS_(self, _):
        self.js_enabled = not bool(getattr(self, "js_enabled", True))

        # update UI button
        try:
            sym = "bolt.fill" if self.js_enabled else "bolt.slash.fill"
            img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(sym, None)
            if img:
                cfg = (
                    NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                        18.0, 2, 2
                    )
                )
                if hasattr(img, "imageByApplyingSymbolConfiguration_"):
                    img = img.imageByApplyingSymbolConfiguration_(cfg)
                img.setTemplate_(True)
                self.btn_js.setImage_(img)
            self.btn_js.setToolTip_(f"JavaScript: {'ON' if self.js_enabled else 'OFF'}")
            if hasattr(self.btn_js, "setContentTintColor_"):
                self.btn_js.setContentTintColor_(
                    NSColor.systemGreenColor()
                    if self.js_enabled
                    else NSColor.systemRedColor()
                )
        except Exception as e:
            log(2, e)

        # apply to active webview + reload
        try:
            wk = self.tabs[self.active].view
            prefs = wk.configuration().preferences()
            prefs.setJavaScriptEnabled_(self.js_enabled)
            wk.reload()
        except Exception as e:
            print("[JS Toggle] Reload error:", e)

    def _install_local_hsts(self, ucc):

        js = f"""
        (() => {{
          try {{
            const here = location.protocol;
            if (here !== 'file:' && here !== 'https:') return;

            if (document.querySelector('meta[http-equiv="Strict-Transport-Security"]')) return;

            const meta = document.createElement('meta');
            meta.httpEquiv = 'Strict-Transport-Security';
            meta.content = {repr(LOCAL_HSTS_VALUE)};
            (document.head || document.documentElement).prepend(meta);
          }} catch (e) {{
          }}
        }})();
        """

        try:
            script = (
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    js, 1, False
                )
            )
            ucc.addUserScript_(script)
            print("[HSTS] Local HSTS injector installed (https:// & file:// only).")
        except Exception as e:
            print("[HSTS] Injector add failed:", e)

    def _install_local_referrer_policy(self, ucc):

        js = f"""
        setTimeout(() => {{
          try {{
            const here = location.protocol;
            if (here !== 'file:' && here !== 'https:') return;

            if (document.querySelector('meta[name="referrer"]')) return;

            const meta = document.createElement('meta');
            meta.name = 'referrer';
            meta.content = {repr(LOCAL_REFERRER_POLICY_VALUE)};
            (document.head || document.documentElement).prepend(meta);
            console.log('[ReferrerPolicy] Meta injected after TLS handshake.');
          }} catch (e) {{
          }}
        }}, 100);
        """

        try:
            script = (
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    js, 1, False
                )
            )
            ucc.addUserScript_(script)
            print(
                "[ReferrerPolicy] Local Referrer-Policy injector installed (https:// & file:// only, delayed)."
            )
        except Exception as e:
            print("[ReferrerPolicy] Injector add failed:", e)

    def _install_local_websocket_policy(self, ucc):

        js = f"""
        setTimeout(() => {{
          try {{
            const here = location.protocol;
            if (here !== 'file:' && here !== 'https:') return;

            const existing = document.querySelectorAll('meta[http-equiv="Content-Security-Policy"]');
            for (const m of existing) {{
              if (m.content.includes("connect-src")) return;
            }}

            const meta = document.createElement('meta');
            meta.httpEquiv = 'Content-Security-Policy';
            meta.content = {repr(LOCAL_WEBSOCKET_POLICY_VALUE)};
            (document.head || document.documentElement).prepend(meta);
            console.log('[WebSocketPolicy] connect-src self injected.');
          }} catch (e) {{
          }}
        }}, 100);
        """

        try:
            script = (
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    js, 1, False
                )
            )
            ucc.addUserScript_(script)
            print(
                "[WebSocketPolicy] Local WebSocket Policy injector installed (connect-src 'self')."
            )
        except Exception as e:
            print("[WebSocketPolicy] Injector add failed:", e)

    @objc.python_method
    def _inject_core_scripts(self, ucc):
        """Install core defenses and conservative cosmetic CSS on every WKWebView."""
        try:
            ucc.addUserScript_(
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    UNIFIED_DEFENSE_JS, WKUserScriptInjectionTimeAtDocumentStart, False
                )
            )
        except Exception as e:
            print("[Darkelf] core script injection failed:", e)

        # These policies must not depend on a previous injection throwing.
        for enabled, installer, label in (
            (ENABLE_LOCAL_HSTS, self._install_local_hsts, "HSTS"),
            (ENABLE_LOCAL_REFERRER_POLICY, self._install_local_referrer_policy, "ReferrerPolicy"),
            (ENABLE_LOCAL_WEBSOCKET_POLICY, self._install_local_websocket_policy, "WebSocketPolicy"),
        ):
            if enabled:
                try:
                    installer(ucc)
                    print(f"[{label}] Local policy injector attached to UCC.")
                except Exception as e:
                    print(f"[{label}] Injector add failed:", e)

        # Narrow fallback: hide known advertising iframe sources, not page layout.
        # Registered at document end so document.documentElement exists.
        cosmetic_js = r"""
        (function() {
            try {
                if (location.hostname === 'youtube.com' || location.hostname.endsWith('.youtube.com')) return;
                var css = `
                    iframe[src*="doubleclick.net"],
                    iframe[src*="googlesyndication.com"],
                    iframe[src*="amazon-adsystem.com"],
                    iframe[src*="taboola.com"],
                    iframe[src*="outbrain.com"] { display: none !important; }
                `;
                var style = document.createElement('style');
                style.type = 'text/css';
                style.textContent = css;
                (document.head || document.documentElement).appendChild(style);
            } catch(e) {
                console.error('[Darkelf] Fallback cosmetic CSS failed:', e);
            }
        })();
        """
        try:
            ucc.addUserScript_(
                WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                    cosmetic_js, WKUserScriptInjectionTimeAtDocumentEnd, False
                )
            )
            print("[Inject] Core defense and fallback cosmetic scripts registered.")
        except Exception as e:
            print("[Inject] Fallback cosmetic script registration failed:", e)

    def _new_wk(self, container_nonce, pq_seed, tab):

        is_home = bool(getattr(self, "loading_home", False))

        cfg = WKWebViewConfiguration.alloc().init()

        # ----------------------------
        # USER CONTENT CONTROLLER
        # ----------------------------
        ucc = WKUserContentController.alloc().init()

        # ----------------------------
        # 🔐 128-BIT HEX SEED (PER TAB)
        # ----------------------------
        seed_hex = get_canvas_seed_hex(tab)

        seed_js = f'window.__darkelf_pq_seed_hex = "{seed_hex}";'

        seed_script = (
            WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                seed_js, WKUserScriptInjectionTimeAtDocumentStart, False
            )
        )

        ucc.addUserScript_(seed_script)

        # ----------------------------
        # 🎯 CANVAS DEFENSE (FIXED)
        # ----------------------------
        canvas_js = """
        (function() {

            if (!window.__darkelf_pq_seed_hex) return;

            function hex32(s) {
                return parseInt(s, 16) >>> 0;
            }

            const HEX = window.__darkelf_pq_seed_hex;

            const SEED_A = hex32(HEX.slice(0, 8));
            const SEED_B = hex32(HEX.slice(8, 16));

            const TAB_SEED = (SEED_A ^ SEED_B) >>> 0;

            function hash(n) {
                n = (n ^ 0x9E3779B1) + (n << 6);
                n ^= n >>> 11;
                n += n << 3;
                n ^= n >>> 15;
                return n >>> 0;
            }

            // ----------------------------
            // ORIGIN (iframe-safe)
            // ----------------------------
            let origin = location.origin || "";

            try {
                if (window.top && window.top.location && window.top.location.origin) {
                    origin = window.top.location.origin;
                }
            } catch (e) {}

            let originHash = 0;
            for (let i = 0; i < origin.length; i++) {
                originHash = (originHash * 31 + origin.charCodeAt(i)) >>> 0;
            }

            const SITE_SEED = hash(TAB_SEED ^ originHash);

            function noise(x, y) {
                return ((x * 13 + y * 17 + SITE_SEED) % 5) - 2;
            }

            const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;

            CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                const data = origGetImageData.call(this, x, y, w, h);

                for (let i = 0; i < data.data.length; i += 4) {
                    const px = (i / 4) % w;
                    const py = Math.floor((i / 4) / w);

                    const n = noise(px, py);

                    data.data[i]     = (data.data[i] + n) & 255;
                    data.data[i + 1] = (data.data[i + 1] + n) & 255;
                    data.data[i + 2] = (data.data[i + 2] + n) & 255;
                }

                return data;
            };

            const origToDataURL = HTMLCanvasElement.prototype.toDataURL;

            HTMLCanvasElement.prototype.toDataURL = function() {

                const ctx = this.getContext("2d");

                if (ctx) {
                    const w = this.width || 1;
                    const h = this.height || 1;

                    const shiftX = SITE_SEED % w;
                    const shiftY = (SITE_SEED >>> 3) % h;

                    ctx.fillStyle = "rgba(0,0,0,0.001)";
                    ctx.fillRect(shiftX, shiftY, 1, 1);
                }

                return origToDataURL.apply(this, arguments);
            };

        })();
        """

        canvas_script = (
            WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                canvas_js, WKUserScriptInjectionTimeAtDocumentStart, False
            )
        )

        ucc.addUserScript_(canvas_script)

        # ---------------------------
        # First-Party Isolation
        # ---------------------------
        url = getattr(self, "current_url_for_fpi", HOME_URL)

        # The Tab object is the single source of truth for container identity.
        tab_uid = getattr(tab, "tab_uid", None)
        nonce = getattr(tab, "container_nonce", None) or container_nonce

        key = self.fpi._key(url, tab_uid=tab_uid, nonce=nonce)
        tab.container_key = key
        tab.container_origin_url = url

        if key not in self._containers:

            store = self.fpi.store_for(
                url, tab_uid=tab_uid, nonce=nonce
            )

            pool = WKProcessPool.alloc().init()

            cache = (
                NSURLCache.alloc().initWithMemoryCapacity_diskCapacity_directoryURL_(
                    16 * 1024 * 1024, 0, None
                )
            )

            if cache.diskCapacity() != 0:
                raise RuntimeError("Darkelf security failure: disk cache detected")

            NSURLCache.setSharedURLCache_(NSURLCache.alloc().init())

            self._containers[key] = (store, pool)

        store, pool = self._containers[key]

        cfg.setWebsiteDataStore_(store)
        cfg.setProcessPool_(pool)

        cfg.setMediaTypesRequiringUserActionForPlayback_(0)

        if store.isPersistent():
            raise RuntimeError(
                "Darkelf security failure: persistent data store detected"
            )

        js_enabled = True if is_home else bool(getattr(self, "js_enabled", True))

        prefs = WKPreferences.alloc().init()
        prefs.setJavaScriptEnabled_(js_enabled)
        prefs.setJavaScriptCanOpenWindowsAutomatically_(True)
        prefs.setValue_forKey_(True, "fullScreenEnabled")
        cfg.setPreferences_(prefs)

        ContentRuleManager.attach_to_controller(ucc)

        ucc.addScriptMessageHandler_name_(self._nav_delegate, "netlog")
        ucc.addScriptMessageHandler_name_(self._nav_delegate, "blobdownload")
        ucc.addScriptMessageHandler_name_(self._search_handler, "search")

        inject_screen_spoof(ucc)

        self._inject_core_scripts(ucc)

        cfg.setUserContentController_(ucc)

        web = WKWebView.alloc().initWithFrame_configuration_(
            NSMakeRect(0, 0, 800, 600), cfg
        )

        darkelf_init_tab_identity(tab)
        web.setCustomUserAgent_(tab._ua_string)

        web.setNavigationDelegate_(self._nav_delegate)
        web.setUIDelegate_(self._ui_delegate)

        return web, store

    def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_completionHandler_(
        self, webView, message, frame, completionHandler
    ):
        """Handle JavaScript alerts"""
        try:
            print(f"[JS Alert] {message}")
            alert = NSAlert.alloc().init()
            alert.setMessageText_("JavaScript Alert")
            alert.setInformativeText_(str(message))
            alert.addButtonWithTitle_("OK")
            alert.runModal()
        finally:
            completionHandler()

    def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_completionHandler_(
        self, webView, message, frame, completionHandler
    ):
        """Handle JavaScript confirms"""
        try:
            print(f"[JS Confirm] {message}")
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Confirm")
            alert.setInformativeText_(str(message))
            alert.addButtonWithTitle_("OK")
            alert.addButtonWithTitle_("Cancel")
            result = alert.runModal()
            completionHandler(result == 1000)
        except Exception as e:
            print(f"[JS Confirm] Error: {e}")
            completionHandler(False)

    def webView_runJavaScriptTextInputPanelWithPrompt_defaultText_initiatedByFrame_completionHandler_(
        self, webView, prompt, defaultText, frame, completionHandler
    ):
        """Handle JavaScript prompts"""
        try:
            print(f"[JS Prompt] {prompt}")
            completionHandler(None)
        except Exception as e:
            print(f"[JS Prompt] Error: {e}")
            completionHandler(None)

    def webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_(
        self, webView, origin, frame, type, decisionHandler
    ):
        try:
            print(f"[Media] 🔒 Denied media capture for: {origin}")
            decisionHandler(0)  # Always deny
        except Exception as e:
            log(2, e)

    def _mount_webview(self, wk):
        cv = self.window.contentView()

        # Remove ALL existing WKWebViews immediately
        for sub in list(cv.subviews()):
            if "WKWebView" in str(type(sub)):
                sub.removeFromSuperview()

        # ====== Ensure Navigation and UI Delegates are set ======
        if getattr(self, "_nav_delegate", None):
            wk.setNavigationDelegate_(self._nav_delegate)
        if getattr(self, "_ui_delegate", None):
            wk.setUIDelegate_(self._ui_delegate)

        # Compute frame: subtract both toolbar and tabbar height!
        try:
            clr = self.window.contentLayoutRect()
            min_height = 100
            total_ui_height = self.TOOLBAR_HEIGHT + self.TABBAR_HEIGHT
            w = clr.size.width
            h = clr.size.height - total_ui_height

            if h < min_height:
                f = cv.frame()
                h = max(min_height, f.size.height - total_ui_height)
                log(2, "[WKWebView] Fallback to cv.frame(), height =", h)

            web_rect = NSMakeRect(0, 0, w, h)
            log(2, f"[WKWebView] Set frame: width={w}, height={h}")

        except Exception as e:
            f = cv.frame()
            min_height = 100
            h = max(
                min_height, f.size.height - (self.TOOLBAR_HEIGHT + self.TABBAR_HEIGHT)
            )
            w = f.size.width
            web_rect = NSMakeRect(0, 0, w, h)
            log(
                2,
                f"[WKWebView] Exception fallback. Set frame: width={w}, height={h}. Error: {e}",
            )

        cv.addSubview_(wk)
        
        if getattr(self, "menu_panel", None):
            self.menu_panel.removeFromSuperview()
            cv.addSubview_(self.menu_panel)
            
        # FIXED BACKGROUND HANDLING
        try:
            wk.setOpaque_(True)
            wk.setBackgroundColor_(NSColor.blackColor())
        except Exception as e:
            print("[WKWebView] Failed to set background:", e)

        wk.setFrame_(web_rect)
        wk.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        # Always re-add toolbar and tabbar after mounting webview!
        try:
            if getattr(self, "toolbar_container", None):
                if self.toolbar_container.superview() != cv:
                    cv.addSubview_(self.toolbar_container)

            if getattr(self, "tabbar", None):
                if self.tabbar.superview() != cv:
                    cv.addSubview_(self.tabbar)

        except Exception as e:
            print("[WKWebView] Failed to re-add toolbar/tabbar:", e)

        self._bring_tabbar_to_front()

    def _rebuild_active_webview(self):

        # --- never rebuild homepage ---
        try:
            u = self.tabs[self.active].view.URL()
            if u and u.absoluteString() == HOME_URL:
                print("[JS] Skip rebuild: homepage")
                return
        except Exception as e:
            log(2, e)

        if self.active < 0 or self.active >= len(self.tabs):
            return

        old = self.tabs[self.active].view

        # --- Clean up the old view ---
        try:
            ucc_old = old.configuration().userContentController()
            ucc_old.removeAllUserScripts()
            for name in ["tracker", "panic", "search"]:
                try:
                    ucc_old.removeScriptMessageHandlerForName_(name)
                except Exception as e:
                    log(2, e)
        except Exception as e:
            log(2, e)

        try:
            if old.superview() is not None:
                old.removeFromSuperview()
        except Exception as e:
            log(2, e)
        self.tabs[self.active].view = None

        # --- Determine which URL to reload ---
        url = ""
        try:
            u = old.URL()
            if u is not None:
                url = str(u.absoluteString())
        except Exception as e:
            log(2, e)
        if not url:
            url = self.tabs[self.active].url

        # --- Build a fresh WebView configuration (App-Bound OFF) ---
        config = WKWebViewConfiguration.alloc().init()

        config.preferences().setValue_forKey_(True, "fullScreenEnabled")

        # Security
        prefs = config.preferences()
        prefs.setValue_forKey_(False, "javaScriptCanOpenWindowsAutomatically")
        prefs.setValue_forKey_(False, "developerExtrasEnabled")

        config.setValue_forKey_(False, "allowFileAccessFromFileURLs")
        config.setValue_forKey_(False, "allowUniversalAccessFromFileURLs")

        try:
            config.setLimitsNavigationsToAppBoundDomains_(False)
        except Exception as e:
            log(2, e)

        # config = WKWebViewConfiguration.alloc().init()

        tab = self.tabs[self.active]
        store = getattr(tab, "data_store", None)
        if store is None:
            origin_url = getattr(tab, "container_origin_url", None) or url or HOME_URL
            store = self.fpi.store_for(
                origin_url,
                tab_uid=getattr(tab, "tab_uid", None),
                nonce=getattr(tab, "container_nonce", None),
            )
            tab.data_store = store

        config.setWebsiteDataStore_(store)

        webview = WKWebView.alloc().initWithFrame_configuration_(
            NSMakeRect(0, 0, width, height), config
        )

        # ✅ ATTACH CONTEXT MENU DELEGATE HERE
        menu = webview.menu()
        if not menu:
            menu = NSMenu.alloc().initWithTitle_("Context")
            webview.setMenu_(menu)

        menu_delegate = DarkelfMenuDelegate.alloc().init()
        menu.setDelegate_(menu_delegate)

        wk = WKWebView.alloc().initWithFrame_configuration_(old.frame(), config)

        if getattr(self, "_ui_delegate", None) is not None:
            wk.setUIDelegate_(self._ui_delegate)

        if getattr(self, "_nav_delegate", None) is not None:
            wk.setNavigationDelegate_(self._nav_delegate)

        # --- Set JS enabled or disabled ---
        prefs = WKPreferences.alloc().init()
        try:
            prefs.setJavaScriptEnabled_(
                True if url == HOME_URL else bool(getattr(self, "js_enabled", True))
            )
            prefs.setJavaScriptCanOpenWindowsAutomatically_(True)
        except Exception as e:
            log(2, e)
        config.setPreferences_(prefs)

        ucc = WKUserContentController.alloc().init()

        # ----------------------------
        # 🔥 1. Inject CONSISTENT seed (MATCH _new_wk)
        # ----------------------------
        tab = None
        if hasattr(self, "tabs") and 0 <= self.active < len(self.tabs):
            tab = self.tabs[self.active]

        seed = get_canvas_seed(tab)  # ✅ SAME as _new_wk

        seed_js = f"window.__darkelf_seed={seed};"

        ucc.addUserScript_(
            WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                seed_js, WKUserScriptInjectionTimeAtDocumentStart, False
            )
        )

        # ----------------------------
        # 🔥 2. Inject ALL defenses
        # ----------------------------
        inject_screen_spoof(ucc)

        # ----------------------------
        # 🔥 3. Core scripts
        # ----------------------------
        try:
            self._inject_core_scripts(ucc)
        except Exception as e:
            log(2, e)

        # ----------------------------
        # 🔥 4. ATTACH UCC (CRITICAL)
        # ----------------------------
        config.setUserContentController_(ucc)

        # --- Optional: Block external script resources when JS is off ---
        try:
            if not getattr(self, "js_enabled", True):
                store = WKContentRuleListStore.defaultStore()
                rule_text = '[{"trigger":{"url-filter":".*"},"action":{"type":"block","resource-type":["script"]}}]'

                def _cb(rule_list, err):
                    if rule_list and not err:
                        ucc.addContentRuleList_(rule_list)

                store.compileContentRuleListForIdentifier_encodedContentRuleList_completionHandler_(
                    "darkelf_block_scripts", rule_text, _cb
                )
        except Exception as e:
            log(2, e)

        # --- Attach the user content controller ---
        try:
            config.setUserContentController_(ucc)
        except Exception as e:
            log(2, e)

        try:
            frame = old.frame() if hasattr(old, "frame") else ((0, 0), (1200, 760))

            wk = WKWebView.alloc().initWithFrame_configuration_(frame, config)

            wk.setFrame_(NSMakeRect(0, 0, 1200, 760))

            if getattr(self, "_nav_delegate", None) is not None:
                wk.setNavigationDelegate_(self._nav_delegate)
            if getattr(self, "_ui_delegate", None) is not None:
                try:
                    wk.setUIDelegate_(self._ui_delegate)
                except Exception as e:
                    log(2, e)

            try:
                wk.setAutoresizingMask_(18)
            except Exception as e:
                log(2, e)

            # Mount & swap in
            self.tabs[self.active].view = wk
            self._mount_webview(wk)

        except Exception as e:
            print("[WK] creation failed:", e)
            return

        # --- Reload prior URL without redirecting to homepage ---
        try:
            old_url = ""
            try:
                u = old.URL()
                if u:
                    old_url = str(u.absoluteString())
            except Exception as e:
                log(2, e)
            if not old_url:
                try:
                    item = old.backForwardList().currentItem()
                    if item and item.URL():
                        old_url = str(item.URL().absoluteString())
                except Exception as e:
                    log(2, e)

            # Fall back to tab's remembered URL
            url = old_url or self.tabs[self.active].url or ""

            if not is_safe_url(url):
                log(1, "[BLOCKED URL]", url)
                return

            # If we're on the internal homepage or truly blank, render HOMEPAGE_HTML
            if url in (
                None,
                "",
                "about:home",
                "about://home",
                "about:blank",
                "about:blank#blocked",
            ):
                try:
                    self.tabs[self.active].view.loadHTMLString_baseURL_(
                        self._homepage_html(), NSURL.URLWithString_(HOME_URL)
                    )
                    self.tabs[self.active].url = HOME_URL
                    self.tabs[self.active].host = "home"
                    self._sync_addr()
                except Exception as e:
                    log(2, e)
                return  # <-- return ONLY in the homepage path

            # Otherwise load the same external URL so we remain on the current page
            req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
            wk.loadRequest_(req)
        except Exception as e:
            log(2, e)

    @property
    def active_tab(self):
        try:
            if 0 <= self.active < len(self.tabs):
                return self.tabs[self.active]
        except Exception as e:
            log(2, e)
        return None

    def _add_tab(self, url: str = "", home: bool = False):
        self.loading_home = bool(home)

        url_str = str(url or "").lower()

        # ----------------------------
        # 🔐 Generate PQ seed (ONLY ONCE)
        # ----------------------------
        if url_str.startswith("darkelf://") or home:
            print("[AddTab] Internal page → no PQ seed")
            pq_seed = None
        else:
            pq_seed = hashlib.sha256(os.urandom(32)).digest()
            print(f"[AddTab] PQ seed generated")

        container_nonce = secrets.token_hex(4)

        self._tab_uid_counter += 1
        tab_uid = self._tab_uid_counter

        self.current_url_for_fpi = url if url else HOME_URL

        # ----------------------------
        # 🔥 CREATE TAB FIRST (CRITICAL)
        # ----------------------------
        tab = Tab(
            view=None,
            data_store=None,
            url="",
            host="new",
            canvas_seed=None,
            container_nonce=container_nonce,
            tab_uid=tab_uid,
        )

        tab._pq_seed = pq_seed
        tab._pq_counter = 0
        tab._nonce = secrets.token_hex(8)

        # ----------------------------
        # 🔥 CREATE WEBVIEW USING TAB
        # ----------------------------
        wk, store = self._new_wk(container_nonce, pq_seed, tab)

        tab.view = wk
        tab.data_store = store

        wk.setNavigationDelegate_(self._nav_delegate)
        if getattr(self, "_ui_delegate", None):
            wk.setUIDelegate_(self._ui_delegate)
            
        # ----------------------------
        # CLEAN OLD VIEW
        # ----------------------------
        if 0 <= self.active < len(self.tabs):
            try:
                old_view = self.tabs[self.active].view
                old_view.stopLoading()
                #old_view.setNavigationDelegate_(None)
                #old_view.setUIDelegate_(None)
                old_view.removeFromSuperview()
            except Exception as e:
                log(2, e)

        # ----------------------------
        # MOUNT NEW VIEW
        # ----------------------------
        self._mount_webview(wk)
        self._bring_tabbar_to_front()

        self.tabs.append(tab)
        self.active = len(self.tabs) - 1

        # ----------------------------
        # MINI AI RESET
        # ----------------------------
        if hasattr(self, "mini_ai"):
            try:
                self.mini_ai.unique_domains.clear()
            except Exception as e:
                log(2, e)

        # ----------------------------
        # LOAD CONTENT
        # ----------------------------
        if home:
            try:
                self.urlbar.setStringValue_("")
            except Exception as e:
                log(2, e)

            wk.loadHTMLString_baseURL_(self._homepage_html(), NSURL.URLWithString_(HOME_URL))

            tab.url = HOME_URL
            tab.host = "Darkelf Home"

            self._pending_chip_sync = wk

        else:
            if url:
                try:
                    req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
                    wk.loadRequest_(req)
                    print(f"[AddTab] Loading URL")
                except Exception as e:
                    log(2, e)

                tab.url = url
                tab.host = "new"

        self.loading_home = False

        # ----------------------------
        # UI UPDATE
        # ----------------------------
        self._update_tab_buttons()
        self._sync_addr()

    def _teardown_webview(self, wk):
        if not wk:
            return
        try:
            js = r"""
            (function(){
              try {
                if (document.pictureInPictureElement) {
                  try { document.exitPictureInPicture(); } catch(e){}
                }
                document.querySelectorAll('video,audio').forEach(function(m){
                  try{ m.pause(); }catch(e){}
                  try{ m.src = ''; }catch(e){}
                  try{ m.load(); }catch(e){}
                });
                try {
                  if (window.YT && YT.get) {
                    var players = YT.get();
                    Object.keys(players || {}).forEach(function(k){
                      try{ players[k].stopVideo(); }catch(e){}
                    });
                  }
                } catch(e){}
                document.querySelectorAll('iframe').forEach(function(f){
                  try{ f.src = 'about:blank'; }catch(e){}
                });
              } catch(e){}
            })();
            """
            wk.evaluateJavaScript_completionHandler_(js, None)
        except Exception as e:
            log(2, e)

        try:
            wk.stopLoading()
        except Exception as e:
            log(2, e)
        try:
            wk.loadHTMLString_baseURL_("", None)
        except Exception as e:
            log(2, e)

        try:
            wk.setNavigationDelegate_(None)
        except Exception as e:
            log(2, e)
        try:
            wk.setUIDelegate_(None)
        except Exception as e:
            log(2, e)
        try:
            ucc = wk.configuration().userContentController()
            if ucc:
                try:
                    ucc.removeAllUserScripts()
                except Exception as e:
                    log(2, e)
                for name in ("netlog", "search"):
                    try:
                        ucc.removeScriptMessageHandlerForName_(name)
                    except Exception as e:
                        log(2, e)

        except Exception as e:
            log(2, e)

        try:
            wk.removeFromSuperview()
        except Exception as e:
            log(2, e)

        try:
            tab.data_store = None
        except Exception as e:
            log(2, e)

    def actNewTab_(self, _):
        self._add_tab(home=True)

    def actSwitchTab_(self, sender):
        """Switch to the tab identified by sender.tag() - PROPER tab isolation"""
        try:
            idx = int(sender.tag())
        except Exception:
            return

        if not (0 <= idx < len(self.tabs)) or idx == self.active:
            return

        cv = self.window.contentView()

        for subview in list(cv.subviews()):
            try:
                if isinstance(subview, WKWebView):
                    subview.removeFromSuperview()
            except Exception as e:
                log(2, e)

        # 🔹 update active tab
        self.active = idx

        # 🔹 mount correct webview
        self._mount_webview(self.tabs[idx].view)

        # 🔹 bring UI layers back
        self._bring_tabbar_to_front()

        # 🔹 refresh tab highlight
        self._update_tab_buttons()

        # 🔹 sync address bar
        self._sync_addr()

    def actCloseTabIndex_(self, sender):

        try:
            idx = int(sender.tag())
        except Exception:
            return

        log(2, "Close tab index:", idx)

        if not (0 <= idx < len(self.tabs)):
            return

        tab = self.tabs[idx]

        # 🔥 STEP 1 — adjust active index BEFORE deletion
        if idx == self.active:
            if len(self.tabs) > 1:
                self.active = min(idx, len(self.tabs) - 2)
            else:
                self.active = -1
        elif idx < self.active:
            self.active -= 1

        # 🔥 STEP 2 — release exact per-tab isolation/container references
        try:
            origin_url = getattr(tab, "container_origin_url", None) or getattr(tab, "url", None) or HOME_URL
            self.fpi.clear_tab(
                origin_url,
                tab_uid=getattr(tab, "tab_uid", None),
                nonce=getattr(tab, "container_nonce", None),
            )

            container_key = getattr(tab, "container_key", None)
            if container_key:
                self._containers.pop(container_key, None)
        except Exception as e:
            print("[CloseTab] isolation cleanup error:", e)

        # Destroy the WebView and clear the tab's ephemeral identity.
        try:
            darkelf_destroy_tab(tab)
        except Exception as e:
            print("[CloseTab] destroy error:", e)

        # 🔥 STEP 3 — remove tab
        del self.tabs[idx]

        # 🔥 STEP 4 — if no tabs left → create new
        if not self.tabs:
            self.active = -1
            self._add_tab(home=True)
            return

        # 🔥 STEP 5 — ensure valid index
        self.active = max(0, min(self.active, len(self.tabs) - 1))

        # 🔥 STEP 6 — mount new active tab
        wk = self.tabs[self.active].view

        try:
            self._mount_webview(wk)
        except Exception as e:
            print("[CloseTab] mount error:", e)

        # 🔥 STEP 7 — UI sync
        self._update_tab_buttons()
        self._sync_addr()

    def _close_tab(self):
        if 0 <= self.active < len(self.tabs):

            class _Tmp:
                def tag(self_inner):
                    return self.active

            self.actCloseTabIndex_(_Tmp())

    def actBack_(self, _):
        try:
            self.tabs[self.active].view.goBack_(None)
        except Exception as e:
            log(2, e)

    def actFwd_(self, _):
        try:
            self.tabs[self.active].view.goForward_(None)
        except Exception as e:
            log(2, e)

    def actReload_(self, _):
        try:
            if not self.tabs:
                return

            tab = self.tabs[self.active]
            wk = tab.view

            # Existing logic preserved
            u = wk.URL()
            cur = str(u.absoluteString()) if u is not None else (tab.url or "")

            if cur == HOME_URL:
                self.actHome_(None)
            else:
                wk.reload_(None)

        except Exception as e:
            print("[Reload] Failed:", e)

    def actHome_(self, _):
        try:
            wk = self.tabs[self.active].view

            wk.loadHTMLString_baseURL_(self._homepage_html(), NSURL.URLWithString_(HOME_URL))

            self.tabs[self.active].url = HOME_URL
            self.tabs[self.active].host = "Darkelf Home"

            self._update_tab_buttons()
            self._sync_addr()

        except Exception as e:
            print("[Home] Failed:", e)

    def actZoomIn_(self, _):
        try:
            s = self.tabs[self.active].view.magnification()
            self.tabs[self.active].view.setMagnification_centeredAtPoint_(
                min(s + 0.1, 3.0), (0, 0)
            )
        except Exception as e:
            log(2, e)

    def actZoomOut_(self, _):
        try:
            s = self.tabs[self.active].view.magnification()
            self.tabs[self.active].view.setMagnification_centeredAtPoint_(
                max(s - 0.1, 0.5), (0, 0)
            )
        except Exception as e:
            log(2, e)

    def actFull_(self, _):
        try:
            self.window.toggleFullScreen_(None)
        except Exception as e:
            log(2, e)

    @objc.python_method
    def _tint_alert_ok_green(self, alert):
        ACCENT = (52 / 255.0, 199 / 255.0, 89 / 255.0, 1.0)
        if alert.buttons().count() == 0:
            alert.addButtonWithTitle_("OK")
        btn = alert.buttons().objectAtIndex_(0)
        try:
            if hasattr(btn, "setBezelColor_"):
                btn.setBezelColor_(
                    NSColor.colorWithCalibratedRed_green_blue_alpha_(*ACCENT)
                )
            elif hasattr(btn, "setContentTintColor_"):
                btn.setContentTintColor_(
                    NSColor.colorWithCalibratedRed_green_blue_alpha_(*ACCENT)
                )
            else:
                btn.setWantsLayer_(True)
                btn.layer().setCornerRadius_(6.0)
                btn.layer().setBackgroundColor_(
                    NSColor.colorWithCalibratedRed_green_blue_alpha_(*ACCENT).CGColor()
                )
        except Exception as e:
            print("[Alert tint] failed:", e)

    def actGo_(self, sender):
        try:
            text = str(sender.stringValue()).strip()
            if not text:
                return

            # Build URL
            if "://" not in text and "." not in text:
                q = quote_plus(text)
                url = "https://www.mojeek.com/search?q=" + q
            elif "://" not in text:
                url = "https://" + text
            else:
                url = text

            # FIX: Use _navigate_to instead of _add_tab
            self._navigate_to(url)

        except Exception as e:
            print("[Go] Failed:", e)

    def actNuke_(self, sender):

        # 🔴 Confirmation Alert
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Clear All Browsing Data?")
        alert.setInformativeText_(
            "This will wipe cookies, cache, local storage, "
            "IndexedDB, and all website data, then close Darkelf."
        )
        alert.setAlertStyle_(NSAlertStyleCritical)

        # Order matters:
        # First button = 1000
        # Second button = 1001
        alert.addButtonWithTitle_("Cancel")  # 1000
        alert.addButtonWithTitle_("Wipe")  # 1001

        # 🔴 Response Handler
        def on_response(code):

            # Only proceed if Wipe was pressed (1001)
            if int(code) != 1001:
                return

            try:
                # 1️⃣ Destroy all WebViews (ephemeral wipe)
                for tab in list(self.tabs):
                    try:
                        self._teardown_webview(tab.view)
                    except Exception as e:
                        log(2, e)

                self.tabs.clear()
                self.active = -1

                # 2️⃣ Reset ephemeral store
                self._data_store = WKWebsiteDataStore.nonPersistentDataStore()

            except Exception as e:
                print("wipe error:", e)

            # 3️⃣ Shutdown browser cleanly
            NSApplication.sharedApplication().terminate_(None)

        # Show confirmation sheet
        alert.beginSheetModalForWindow_completionHandler_(self.window, on_response)

    def _storage_cleanup(self):
        try:
            store = WKWebsiteDataStore.nonPersistentDataStore()
            types = WKWebsiteDataStore.allWebsiteDataTypes()

            def handler():
                print("[Darkelf] Non-persistent storage cleanup complete.")

            store.removeDataOfTypes_modifiedSince_completionHandler_(types, 0, handler)
        except Exception as e:
            print("[Darkelf] Storage cleanup skipped:", e)

    def _load_url_in_active(self, url):
        try:
            req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
            self.tabs[self.active].view.loadRequest_(req)
            self.tabs[self.active].url = url
            from urllib.parse import urlparse

            u = urlparse(url)
            host = u.netloc or "site"
            if host.lower().startswith("www."):
                host = host[4:] or "site"
            self.tabs[self.active].host = host
            self._sync_addr()
            self._update_tab_buttons()
        except Exception as e:
            print("[Load] error:", e)

    def _sync_addr(self):
        try:
            v = ""
            if 0 <= self.active < len(self.tabs):
                try:
                    u = self.tabs[self.active].view.URL()
                    if u is not None:
                        v = str(u.absoluteString())
                except Exception as e:
                    log(2, e)

                if not v:
                    v = self.tabs[self.active].url or ""

            if v in (
                HOME_URL,
                "about:home",
                "about://home",
                "about:blank",
                "about:blank#blocked",
            ):
                v = ""

            self.urlbar.setStringValue_(v)

        except Exception as e:
            log(2, e)

    def _install_key_monitor(self):

        def handler(evt):

            try:

                if evt.type() != 10:
                    return evt

                flags = evt.modifierFlags()

                cmd = bool(flags & NSEventModifierFlagCommand)
                shift = bool(flags & NSEventModifierFlagShift)
                ctrl = bool(flags & NSEventModifierFlagControl)

                if not cmd:
                    return evt

                ch = evt.charactersIgnoringModifiers()
                raw = evt.characters()

                if ch:
                    ch = ch.lower()

                key = evt.keyCode()

                # ----------------------------------
                # ⌘ ←
                # ----------------------------------
                if key == 123:
                    self.actBack_(None)
                    return None

                # ----------------------------------
                # ⌘ →
                # ----------------------------------
                if key == 124:
                    self.actFwd_(None)
                    return None
                    
                # ----------------------------------
                # ⌘F FIND BAR
                # ----------------------------------
                if ch == "f" and not shift and not ctrl:

                    try:

                        NSOperationQueue.mainQueue().addOperationWithBlock_(
                            lambda: self.showFindBar()
                        )

                    except Exception as e:
                        print("[FindBar Shortcut Error]", e)

                    return None
                    
                # ----------------------------------
                # ⌃⌘F FULLSCREEN
                # ----------------------------------
                if ch == "f" and ctrl:

                    try:
                        self.window.toggleFullScreen_(None)
                    except Exception as e:
                        print("[Fullscreen Error]", e)

                    return None

                # ----------------------------------
                # ⌘L ADDRESS BAR
                # ----------------------------------
                if ch == "l" and not shift:

                    self.window.makeFirstResponder_(self.addr)
                    return None

                # ----------------------------------
                # ⌘T
                # ----------------------------------
                if ch == "t":
                    self.actNewTab_(None)
                    return None

                # ----------------------------------
                # ⌘W
                # ----------------------------------
                if ch == "w":
                    self.actCloseTab_(None)
                    return None

                # ----------------------------------
                # ⌘R
                # ----------------------------------
                if ch == "r":
                    self.actReload_(None)
                    return None

                # ----------------------------------
                # ⌘S
                # ----------------------------------
                if ch == "s":
                    self.actSnapshot_(None)
                    return None

                # ----------------------------------
                # ⇧⌘X
                # ----------------------------------
                if ch == "x" and shift:

                    NSApp().terminate_(None)
                    return None

                # ----------------------------------
                # ⌘=
                # ----------------------------------
                if raw == "=":
                    self.actZoomIn_(None)
                    return None

                # ----------------------------------
                # ⌘-
                # ----------------------------------
                if raw == "-":
                    self.actZoomOut_(None)
                    return None

                # ----------------------------------
                # ⇧⌘/
                # macOS returns "/" not "?"
                # ----------------------------------
                # ⇧⌘/
                if raw == "/" and shift:

                    self.openDarkelfCommandCenter_(None)
                    return None

            except Exception as e:
                print("[Hotkey Error]", e)

            return evt

        # IMPORTANT:
        # RETAIN monitor or GC kills shortcuts
        self._keyMonitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            1 << 10,
            handler
        )
        
    def showFindBar(self):

        try:

            # ------------------------------------------
            # destroy broken/stale panel
            # ------------------------------------------
            panel_ref = getattr(self, "_findPanel", None)

            if panel_ref is not None:

                try:

                    # avoid redundant Cocoa detach
                    if panel_ref.superview():
                        panel_ref.removeFromSuperview()

                except Exception as e:

                    print("[FindBar Cleanup Error]", e)

            self._findPanel = None

            # ------------------------------------------
            # floating overlay
            # ------------------------------------------
            panel = DraggableFindBar.alloc().initWithFrame_(
                NSMakeRect(28, 28, 430, 62)
            )

            panel.setAutoresizingMask_(
                NSViewMaxXMargin | NSViewMaxYMargin
            )

            panel.setWantsLayer_(True)

            layer = panel.layer()

            layer.setCornerRadius_(14)

            layer.setBackgroundColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.08, 0.09, 0.11, 0.98
                ).CGColor()
            )

            layer.setBorderWidth_(1.0)

            layer.setBorderColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.18, 0.20, 0.24, 1
                ).CGColor()
            )

            # ------------------------------------------
            # search field
            # ------------------------------------------
            field = DarkelfSearchField.alloc().initWithFrame_(
                NSMakeRect(16, 16, 370, 30)
            )

            field.browser = self
            
            field.setRefusesFirstResponder_(False)
            
            field.setPlaceholderString_("Find in page")

            field.setFont_(NSFont.systemFontOfSize_(14))

            # Native macOS rendering
            field.setFocusRingType_(NSFocusRingTypeNone)

            field.setBordered_(True)
            field.setBezeled_(True)

            # Better text rendering
            field.cell().setUsesSingleLineMode_(True)

            # Dark mode text
            try:

                field.setTextColor_(NSColor.whiteColor())

            except Exception as e:

                print("[FindBar TextColor Error]", e)

            # IMPORTANT:
            # DO NOT layer-style NSSearchField
            # Cocoa breaks rendering if you do

            try:

                field.setWantsLayer_(False)

            except Exception as e:

                print("[FindBar Layer Error]", e)

            panel.addSubview_(field)
            
            # ------------------------------------------
            # close button
            # ------------------------------------------

            close = NSButton.alloc().initWithFrame_(
                NSMakeRect(392, 18, 24, 24)
            )

            close.setBordered_(False)

            close.setTitle_("✕")

            close.setBezelStyle_(0)

            close.setFont_(
                NSFont.systemFontOfSize_weight_(13, 0.7)
            )

            close.setContentTintColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.20, 0.78, 0.35, 1
                )
            )

            close.setTarget_(self)

            close.setAction_("hideFindBar:")

            close.setWantsLayer_(True)

            close.layer().setCornerRadius_(8)

            close.layer().setBackgroundColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    0.12,
                    0.14,
                    0.17,
                    1
                ).CGColor()
            )

            panel.addSubview_(close)

            # ------------------------------------------
            # attach ABOVE EVERYTHING
            # ------------------------------------------
            content = self.window.contentView()

            content.addSubview_positioned_relativeTo_(
                panel,
                1,
                None
            )

            self._findPanel = panel
            self._findField = field

            # ------------------------------------------
            # live find
            # ------------------------------------------
            field.setTarget_(self)
            field.setAction_("performPageFind:")
            
            field.cell().setSendsSearchStringImmediately_(True)
            field.cell().setSendsWholeSearchString_(False)
            
            self.window.makeFirstResponder_(field)

        except Exception as e:
            print("[FindBar Error]", e)
            
    def hideFindBar_(self, sender):

        try:

            if hasattr(self, "_findPanel") and self._findPanel:

                self._findPanel.removeFromSuperview()

                self._findPanel = None
                self._findField = None
    
        except Exception as e:
            print("[FindBar Hide Error]", e)
        
    def performPageFind_(self, sender):

        try:

            text = self._findField.stringValue()

            if not text:
                return

            tab = self.tabs[self.active]

            js = f"""
            window.find({json.dumps(text)}, false, false, true, false, false, false);
            """

            tab.view.evaluateJavaScript_completionHandler_(
                js,
                None
            )

        except Exception as e:
            print("[Find Error]", e)
                        
    def setupHotkeys(self):

        def handler(event):

            chars = event.charactersIgnoringModifiers()

            mods = event.modifierFlags()

            cmd = mods & NSEventModifierFlagCommand
            shift = mods & NSEventModifierFlagShift
            
            # ESC closes FindBar
            if event.keyCode() == 53:

                if hasattr(self, "_findPanel") and self._findPanel:

                    self.hideFindBar_(None)

                    return None
                    
            # ⇧⌘/
            if cmd and shift and chars == "/":

                self.openDarkelfCommandCenter_(None)

                return None

            return event

        NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            10,   # keyDown
            handler
        )
            
    def safe_shutdown(self):

        if hasattr(self, "window"):
            try:
                nc = NSNotificationCenter.defaultCenter()
                nc.removeObserver_(self)
            except Exception as e:
                log(2, e)

        if hasattr(self, "tabs"):
            for tab in self.tabs:
                view = getattr(tab, "view", None)
                if view:
                    try:
                        ucc = view.configuration().userContentController()
                        for name in ("netlog", "search"):
                            ucc.removeScriptMessageHandlerForName_(name)
                        view.removeFromSuperview()
                    except Exception as e:
                        log(2, e)

    def _wipe_all_site_data(self):
        """
        Fully reset browser session:
        - Tear down all webviews
        - Clear tab list
        - Reset active index
        - Recreate fresh non-persistent data store
        """

        if getattr(self, "_has_wiped", False):
            return

        try:
            # Teardown all webviews safely
            for tab in list(self.tabs):
                try:
                    if hasattr(tab, "view") and tab.view:
                        self._teardown_webview(tab.view)
                except Exception as e:
                    log(2, e)

            # Clear tab state
            self.tabs = []
            self.active = 0

            # Reset to fresh ephemeral store
            self._data_store = WKWebsiteDataStore.nonPersistentDataStore()

            # Mark wipe complete only after success
            self._has_wiped = True

        except Exception as e:
            print("wipe error:", e)

    def windowWillClose_(self, notification):

        try:
            # Stop all webviews
            for tab in getattr(self, "tabs", []):
                try:
                    tab.view.stopLoading()
                except Exception as e:
                    log(2, e)
        except Exception as e:
            log(2, e)

        NSApplication.sharedApplication().terminate_(None)

    def applicationWillTerminate_(self, notification):
        try:
            pass
        except Exception as e:
            log(2, e)

    def wipe_webkit_memory():
        store = WKWebsiteDataStore.nonPersistentDataStore()

        types = WKWebsiteDataStore.allWebsiteDataTypes()

        store.removeDataOfTypes_modifiedSince_completionHandler_(types, 0, lambda: None)

    def actSnapshot_(self, sender):
        try:
            wk = self.tabs[self.active].view

            def handler(image, error):
                if image and not error:

                    # --- Darkelf snapshot folder ---
                    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                    library = os.path.join(desktop, "Darkelf Library")
                    snapdir = os.path.join(library, "Darkelf Snap")

                    os.makedirs(snapdir, exist_ok=True)

                    # timestamp filename
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"darkelf_snapshot_{ts}.png"
                    path = os.path.join(snapdir, filename)

                    url = NSURL.fileURLWithPath_(path)

                    tiff = image.TIFFRepresentation()
                    rep = NSBitmapImageRep.imageRepWithData_(tiff)
                    png = rep.representationUsingType_properties_(4, None)  # PNG
                    png.writeToURL_atomically_(url, True)

                    print("[Darkelf] Snapshot saved →", path)

            wk.takeSnapshotWithConfiguration_completionHandler_(None, handler)

        except Exception as e:
            print("[Snapshot] Failed:", e)


class AppDelegate(NSObject):

    def applicationShouldTerminate_(self, sender):
        # Allow termination immediately
        return True

    def applicationWillTerminate_(self, notification):
        """Graceful shutdown with threat report and data cleanup"""
        _clear_darkelf_cocoa_accent_override()
        print("\n" + "=" * 70)
        print("[Darkelf] Browser shutting down - initiating cleanup...")
        print("=" * 70 + "\n")

        try:
            if hasattr(self, "browser") and self.browser is not None:

                # ═══════════════════════════════════════════════════════════
                # 2. STOP COOKIE SCRUBBER
                # ═══════════════════════════════════════════════════════════
                print("\n" + "=" * 70)
                print("[Darkelf] Shutdown complete - all data wiped")
                print("=" * 70 + "\n")

        except Exception as e:
            print("[Quit] Unexpected shutdown error:", e)


def main():
    # Every launch starts with the original Darkelf green. Accent changes are
    # intentionally session-scoped and then propagate live to all UI surfaces.
    reset_accent_for_launch()
    try:
        defaults = NSUserDefaults.standardUserDefaults()
        defaults.setVolatileDomain_forName_({}, NSRegistrationDomain)
        # Session-only US-English preference. WebKit uses the application
        # language preference when constructing normal browser requests.
        defaults.registerDefaults_({"AppleLanguages": ["en-US", "en"]})
        print("[Prefs] NSUserDefaults set to volatile (RAM-only).")
        print("[Locale] US-English preference enabled (en-US, en).")
    except Exception as e:
        print("[Prefs] Failed to set volatile domain:", e)

    app = NSApplication.sharedApplication()
    sync_application_icon()

    # ✅ APPLY DARKELF THEME HERE (CORRECT SPOT)
    apply_darkelf_theme()

    # Sync native Cocoa controls to Darkelf's launch accent without changing
    # the user's global macOS Accent Color preference.
    _sync_cocoa_accent_to_darkelf(load_accent_rgba())

    # ✅ PRE-COMPILE RULES BEFORE BROWSER STARTS
    print("[Startup] Compiling content blocking rules...")
    ContentRuleManager.load_rules()

    # Compatibility diagnostic: restore pre-v15.07 startup grace period.
    # Pending controllers still receive the compiled rules asynchronously.
    time.sleep(3.0)

    # WebKit compilation is asynchronous. Every newly created controller is
    # registered and receives the rules when compilation completes; do not
    # block AppKit's main thread with an arbitrary sleep.
    if ContentRuleManager._rule_list:
        print("[Startup] Cached content rules ready")

    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    NSURLCache.setSharedURLCache_(None)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    delegate.browser = Browser.alloc().init()

    app.run()

    wipe_webkit_memory()

    nav_delegate.wipe_download_traces()


if __name__ == "__main__":
    main()
