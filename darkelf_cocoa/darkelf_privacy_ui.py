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
from LocalAuthentication import LAContext, LAPolicyDeviceOwnerAuthentication
from PyObjCTools import AppHelper

from .darkelf_pages import HOMEPAGE_HTML, UNIFIED_DEFENSE_JS, homepage_html_for_accent
from .darkelf_policy import *
from .darkelf_utils import *
from .darkelf_pq import *
from .darkelf_isolation import *
from .darkelf_content_rules import *
from .darkelf_sentry_rules import SentryRuleManager
from .darkelf_version import APP_VERSION
from .darkelf_spoofing import *
from .darkelf_downloads import *
from .darkelf_network import *
from .darkelf_delegates import _WindowDelegate, _UIDelegate, _NavDelegate
from .darkelf_sentinel import *
from .darkelf_tabs import Tab, darkelf_destroy_tab
from .darkelf_ui import (
    DarkelfMenuDelegate, HoverButton, TabHoverView, SearchHandler, AddressField,
    DarkelfAddressEditor, DarkelfWebView,
    DraggableFindBar, DarkelfSearchField, apply_darkelf_theme,
)
from .darkelf_icons import load_nav_svg, load_toolbar_svg
from .darkelf_branding import sync_application_icon, make_application_icon
from .darkelf_theme import (
    TOOLBAR_HEIGHT, TOOLBAR_PADDING, TOOLBAR_BUTTON_SIZE, TOOLBAR_BUTTON_GAP,
    TOOLBAR_RIGHT_GAP, URLBAR_MIN_WIDTH, URLBAR_MAX_WIDTH,
    ACCENT_PRESETS, load_accent_rgba, save_accent_rgba, reset_accent_for_launch,
    BACKGROUND_PRESETS, load_background_name, save_background_name, reset_background_for_launch,
    cocoa_accent_value_for_rgba,
)

APP_NAME = "Darkelf"
HOME_URL = "darkelf://home"
LOG_LEVEL = int(os.environ.get("DARKELF_DEBUG", "0") == "1")

def log(level, *msg):
    if level <= LOG_LEVEL:
        print(*msg)

from .darkelf_browser_lock import _browser_lock_enabled, _set_browser_lock_enabled, _authenticate_mac_owner

class DarkelfPrivacyUIMixin:
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
        self.browser_lock_button = HoverButton.alloc().initWithFrame_(
            NSMakeRect(20, 16, 200, 36)
        )
        self.browser_lock_button.setBordered_(False)
        self.browser_lock_button.setAlignment_(NSLeftTextAlignment)
        self.browser_lock_button.setFont_(NSFont.systemFontOfSize_(14))
        self.browser_lock_button.setTarget_(self)
        self.browser_lock_button.setAction_("toggleBrowserLock:")
        self.privacy_view.addSubview_(self.browser_lock_button)
        self._refresh_browser_lock_button()
        # Dedicated details arrow; the existing toggle remains independent.
        self.browser_lock_info_button = HoverButton.alloc().initWithFrame_(
            NSMakeRect(224, 16, 36, 36)
        )
        self.browser_lock_info_button.setTitle_("›")
        self.browser_lock_info_button.setBordered_(False)
        self.browser_lock_info_button.setFont_(NSFont.boldSystemFontOfSize_(20))
        self.browser_lock_info_button.setTarget_(self)
        self.browser_lock_info_button.setAction_("showBrowserLockInfo:")
        self.privacy_view.addSubview_(self.browser_lock_info_button)
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
                     "privacy_permissions_view", "privacy_browser_lock_view"):
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


