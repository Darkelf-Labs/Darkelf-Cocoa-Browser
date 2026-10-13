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


_BROWSER_LOCK_PREF = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Darkelf Cocoa", "browser-lock.json")

def _browser_lock_enabled():
    try:
        with open(_BROWSER_LOCK_PREF, "r", encoding="utf-8") as handle:
            return json.load(handle).get("enabled") is True
    except (OSError, ValueError, TypeError):
        return False


def _set_browser_lock_enabled(enabled):
    folder = os.path.dirname(_BROWSER_LOCK_PREF)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    tmp = _BROWSER_LOCK_PREF + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"enabled": bool(enabled)}, handle)
        os.replace(tmp, _BROWSER_LOCK_PREF)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _authenticate_mac_owner(reason, callback):
    """Async macOS Touch ID / account password; callback always on AppKit thread."""
    context = LAContext.alloc().init()
    ok, error = context.canEvaluatePolicy_error_(LAPolicyDeviceOwnerAuthentication, None)
    if not ok:
        AppHelper.callAfter(callback, False)
        return

    def finished(success, error):
        AppHelper.callAfter(callback, bool(success))

    context.evaluatePolicy_localizedReason_reply_(
        LAPolicyDeviceOwnerAuthentication, reason, finished
    )


def _clear_darkelf_cocoa_accent_override():
    from .application import _clear_darkelf_cocoa_accent_override as fn
    return fn()

class DarkelfBrowserLockMixin:
    def _createBrowserLockInfoView(self):
        if getattr(self, "privacy_browser_lock_view", None) is not None:
            return
        view = self._privacy_page("Browser Lock", "showPrivacyView:")
        self.privacy_browser_lock_view = view
        self._privacy_label(view, "OPTIONAL LOCAL SECURITY", 20, 319, 245,
                            size=12, bold=True, accent=True)
        for name, detail, y in (
            ("On Startup", "Touch ID or Mac password", 277),
            ("10-Minute Inactivity", "Locks after no browser activity", 213),
            ("Dock Minimization", "Locks when minimized; unlock on return", 149),
        ):
            self._privacy_row(view, name, detail, y)
        self._privacy_label(view, "Uses macOS authentication.", 20, 69, 245,
                            size=12, muted=True)
        self._privacy_label(view, "No passwords or biometrics stored.", 20, 45, 245,
                            size=12, muted=True)


    def showBrowserLockInfo_(self, sender):
        self._createMenuPanel()
        self._createPrivacyView()
        self._createBrowserLockInfoView()
        self._show_privacy_page(self.privacy_browser_lock_view)


    def _refresh_browser_lock_button(self):
        button = getattr(self, "browser_lock_button", None)
        if button is not None:
            button.setTitle_(
                "✓  Browser Lock: On" if _browser_lock_enabled()
                else "○  Enable Browser Lock"
            )
            button.setEnabled_(not getattr(self, "_browser_lock_pending", False))


    def toggleBrowserLock_(self, sender):
        if getattr(self, "_browser_lock_pending", False):
            return
        enabling = not _browser_lock_enabled()
        self._browser_lock_pending = True
        self._refresh_browser_lock_button()

        def complete(success):
            self._browser_lock_pending = False
            if success:
                try:
                    _set_browser_lock_enabled(enabling)
                except OSError as exc:
                    print("[Browser Lock] Could not save preference:", exc)
            self._refresh_browser_lock_button()

        _authenticate_mac_owner(
            "Enable Darkelf Cocoa Browser Lock" if enabling
            else "Disable Darkelf Cocoa Browser Lock", complete
        )


    @objc.python_method
    def _browser_lock_activity_event(self, event):
        if self._lock_engaged:
            # Consume local browser events; native unlock button remains usable
            # via AppKit's normal control dispatch (mouse events are passed).
            if event.type() == 10:  # NSKeyDown
                return None
            return event
        if NSApplication.sharedApplication().isActive():
            self._lock_last_activity = time.monotonic()
        return event


    @objc.python_method
    def _browser_lock_cover(self):
        """Native, theme-aware opaque lock screen; authentication remains macOS-owned."""
        if self._lock_overlay is not None:
            return
        parent = self.window.contentView()
        bounds = parent.bounds()
        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
        # Keep the entire browsing surface concealed while locked.
        cover = NSView.alloc().initWithFrame_(bounds)
        cover.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        cover.setWantsLayer_(True)
        cover.layer().setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.025, 0.030, 0.043, 1.0).CGColor())

        # A centered native AppKit card follows window resizing without WebKit.
        card_width, card_height = 390, 340
        card = NSView.alloc().initWithFrame_(NSMakeRect(
            max(0, (bounds.size.width - card_width) / 2),
            max(0, (bounds.size.height - card_height) / 2),
            card_width, card_height))
        card.setAutoresizingMask_(NSViewMinXMargin | NSViewMaxXMargin |
                                  NSViewMinYMargin | NSViewMaxYMargin)
        card.setWantsLayer_(True)
        card.layer().setCornerRadius_(22)
        card.layer().setMasksToBounds_(True)
        card.layer().setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.085, 0.095, 0.12, 1.0).CGColor())
        card.layer().setBorderWidth_(1.0)
        card.layer().setBorderColor_(accent.colorWithAlphaComponent_(0.50).CGColor())
        cover.addSubview_(card)

        icon = NSImageView.alloc().initWithFrame_(NSMakeRect(157, 227, 76, 76))
        icon.setImage_(make_application_icon(256))
        icon.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        card.addSubview_(icon)

        def add_text(message, y, size, color, bold=False):
            field = NSTextField.alloc().initWithFrame_(NSMakeRect(20, y, 350, 30))
            field.setStringValue_(message)
            field.setEditable_(False)
            field.setSelectable_(False)
            field.setBordered_(False)
            field.setDrawsBackground_(False)
            field.setAlignment_(NSCenterTextAlignment)
            field.setFont_((NSFont.boldSystemFontOfSize_(size) if bold
                            else NSFont.systemFontOfSize_(size)))
            field.setTextColor_(color)
            card.addSubview_(field)
            return field

        add_text("DARKELF COCOA", 188, 20, NSColor.whiteColor(), True)
        add_text("BROWSER LOCKED", 158, 11, accent, True)
        add_text("Your browsing session is protected", 123, 13,
                 NSColor.colorWithCalibratedWhite_alpha_(0.76, 1.0))

        button = NSButton.alloc().initWithFrame_(NSMakeRect(73, 60, 244, 43))
        button.setTitle_("Unlock with Touch ID or Password")
        button.setTarget_(self)
        button.setAction_("unlockBrowserLock:")
        button.setBezelStyle_(NSBezelStyleRounded)
        button.setKeyEquivalent_("")
        button.setWantsLayer_(True)
        button.layer().setCornerRadius_(10)
        button.layer().setBorderWidth_(1.0)
        button.layer().setBorderColor_(accent.colorWithAlphaComponent_(0.70).CGColor())
        card.addSubview_(button)
        add_text("Authenticated securely by macOS", 22, 11,
                 NSColor.colorWithCalibratedWhite_alpha_(0.60, 1.0))

        self._lock_overlay = cover
        parent.addSubview_positioned_relativeTo_(cover, NSWindowAbove, None)


    @objc.python_method
    def _browser_lock_set_menu_enabled(self, enabled):
        """Disable native app-menu items while the lock overlay is visible."""
        app = NSApplication.sharedApplication()
        main_menu = app.mainMenu()
        if main_menu is None or main_menu.numberOfItems() == 0:
            return
        app_item = main_menu.itemAtIndex_(0)
        menu = app_item.submenu() if app_item is not None else None
        if menu is None:
            return
        # The custom NSView-backed rows do not automatically honor the visual
        # disabled state of NSMenuItem. Update both the native item and its view.
        # Keep Quit available so the user can always close a locked browser.
        for index in range(menu.numberOfItems()):
            item = menu.itemAtIndex_(index)
            if item.isSeparatorItem():
                continue
            allowed = bool(enabled) or str(item.title()) == "Quit Darkelf Cocoa"
            item.setEnabled_(allowed)
            view = item.view()
            if view is not None:
                view.setAlphaValue_(1.0 if allowed else 0.35)
                if not allowed:
                    view._darkelf_hovered = False
                view.setNeedsDisplay_(True)
        # Discard stale hover state when the lock transitions.
        try:
            from .application import DarkelfAccentMenuRow
            DarkelfAccentMenuRow.reset_hover()
        except (ImportError, AttributeError):
            pass

    @objc.python_method
    def _engage_browser_lock(self):
        if self._lock_engaged or not _browser_lock_enabled():
            return
        self._lock_engaged = True
        self._browser_lock_cover()
        # Disable all application-menu actions except Quit. A native menu
        # exists outside the NSWindow, so an overlay alone cannot secure it.
        self._browser_lock_set_menu_enabled(False)


    @objc.python_method
    def _request_browser_unlock(self):
        if not self._lock_engaged or self._lock_auth_pending or self.window.isMiniaturized():
            return
        self._lock_auth_pending = True

        def complete(success):
            self._lock_auth_pending = False
            if success and self._lock_engaged:
                self._lock_engaged = False
                if self._lock_overlay is not None:
                    self._lock_overlay.removeFromSuperview()
                    self._lock_overlay = None
                self._lock_last_activity = time.monotonic()
                self._browser_lock_set_menu_enabled(True)
            # Cancel/failure keeps the opaque cover in place; Unlock can retry.

        _authenticate_mac_owner(
            "Unlock Darkelf Cocoa with Touch ID or your Mac password", complete
        )


    def unlockBrowserLock_(self, sender):
        self._request_browser_unlock()


    def checkBrowserLockIdle_(self, timer):
        if not _browser_lock_enabled():
            self._lock_last_activity = time.monotonic()
            return
        if not self._lock_engaged and time.monotonic() - self._lock_last_activity >= 600:
            self._engage_browser_lock()
            if not self.window.isMiniaturized() and NSApplication.sharedApplication().isActive():
                self._request_browser_unlock()



# Shared browser-lock helpers, relocated for mixin independence.


_BROWSER_LOCK_PREF = os.path.join(
    os.path.expanduser("~"), "Library", "Application Support",
    "Darkelf Cocoa", "browser-lock.json"
)

def _browser_lock_enabled():
    try:
        with open(_BROWSER_LOCK_PREF, "r", encoding="utf-8") as handle:
            return json.load(handle).get("enabled") is True
    except (OSError, ValueError, TypeError):
        return False

def _set_browser_lock_enabled(enabled):
    folder = os.path.dirname(_BROWSER_LOCK_PREF)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    tmp = _BROWSER_LOCK_PREF + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"enabled": bool(enabled)}, handle)
        os.replace(tmp, _BROWSER_LOCK_PREF)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def _authenticate_mac_owner(reason, callback):
    """Async macOS Touch ID / account password; callback always on AppKit thread."""
    context = LAContext.alloc().init()
    ok, error = context.canEvaluatePolicy_error_(LAPolicyDeviceOwnerAuthentication, None)
    if not ok:
        AppHelper.callAfter(callback, False)
        return

    def finished(success, error):
        AppHelper.callAfter(callback, bool(success))

    context.evaluatePolicy_localizedReason_reply_(
        LAPolicyDeviceOwnerAuthentication, reason, finished
    )
