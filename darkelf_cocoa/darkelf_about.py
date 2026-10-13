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

class DarkelfAboutMixin:
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
        version.setStringValue_(f"Version {APP_VERSION}")

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
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view", "privacy_browser_lock_view"):
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


