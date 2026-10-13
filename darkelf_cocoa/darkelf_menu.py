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

class DarkelfMenuMixin:
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

        self._apply_accent_to_ui()


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
        for name in ("bookmark_view", "shortcut_view", "about_view", "mini_ai_view", "accent_view", "background_view", "privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view", "privacy_browser_lock_view"):
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
        if getattr(self, "background_buttons", None):
            for index, (_name, button) in enumerate(self.background_buttons):
                col, row = index % 2, index // 2
                button.setFrame_(NSMakeRect(16 + col * 126, top - 82 - row * 59, 120, 51))
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
        for _pn in ("privacy_view", "privacy_protection_view", "privacy_exceptions_view", "privacy_permissions_view", "privacy_browser_lock_view"):
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



# Local diagnostic logger for extracted menu methods.
LOG_LEVEL = int(os.environ.get("DARKELF_DEBUG", "0") == "1")
def log(level, *msg):
    if level <= LOG_LEVEL:
        print(*msg)
