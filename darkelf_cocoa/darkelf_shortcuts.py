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

class DarkelfShortcutsMixin:
    def showKeyboardShortcuts_(self, sender):
        if getattr(self, "btn_privacy", None) is not None:
            self.btn_privacy.setHidden_(True)
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view", "privacy_browser_lock_view"):
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

            "Context Menus": [
                ("⌘X", "Cut Text (address bar / editable text)"),
                ("⌘C", "Copy Text / Selection"),
                ("⌘V", "Paste Text"),
                ("⇧⌘V", "Paste and Go (address bar)"),
                ("⌘A", "Select All"),
                ("⇧⌘C", "Copy Page URL"),
                ("Right-click", "Darkelf Context Menu"),
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
                ("⌘H", "Hide Darkelf Cocoa"),
                ("⌥⌘H", "Hide Others"),
                ("⌘Q", "Quit Darkelf Cocoa"),
                ("⇧⌘X", "Exit Darkelf"),
            ],
        }

        # Start collapsed
        self.shortcut_expanded = {
            section: False
            for section in self.shortcut_sections
        }

        self._loadBookmarks()


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


