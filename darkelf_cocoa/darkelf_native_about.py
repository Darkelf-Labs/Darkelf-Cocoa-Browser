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

class DarkelfNativeAboutMixin:
    @objc.IBAction
    def showDarkelfAbout_(self, sender):
        """Show a native Darkelf-themed About panel without navigating a tab."""
        panel = getattr(self, "_darkelf_about_panel", None)
        if panel is None:
            panel = self._build_darkelf_about_panel()
            self._darkelf_about_panel = panel
        # Refresh the selected accent whenever the panel is reopened.
        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
        surface = panel.contentView()
        surface.layer().setBorderColor_(accent.colorWithAlphaComponent_(0.65).CGColor())
        self._darkelf_about_title.setTextColor_(accent)
        about_logo = getattr(self, "_darkelf_about_logo", None)
        if about_logo is not None:
            about_logo.setImage_(make_application_icon(256))
        self._darkelf_about_version.setStringValue_(f"Version {APP_VERSION}")
        # Keep About above its browser instead of acting as an unrelated window.
        browser_window = getattr(self.browser, "window", None)
        if browser_window is not None:
            browser_window.makeKeyAndOrderFront_(None)
            if panel.parentWindow() is not browser_window:
                if panel.parentWindow() is not None:
                    panel.parentWindow().removeChildWindow_(panel)
                browser_window.addChildWindow_ordered_(panel, NSWindowAbove)
            browser_frame = browser_window.frame()
            panel_frame = panel.frame()
            panel.setFrameOrigin_(NSMakePoint(
                browser_frame.origin.x + (browser_frame.size.width - panel_frame.size.width) / 2,
                browser_frame.origin.y + (browser_frame.size.height - panel_frame.size.height) / 2,
            ))
        else:
            panel.center()
        panel.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)


    @objc.python_method
    def _build_darkelf_about_panel(self):
        width, height = 510, 410
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, width, height),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered, False,
        )
        panel.setReleasedWhenClosed_(False)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setMovableByWindowBackground_(True)
        panel.setHasShadow_(True)

        surface = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        surface.setWantsLayer_(True)
        layer = surface.layer()
        layer.setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.02, 0.025, 0.03, 0.90).CGColor())
        layer.setBorderWidth_(1.0)
        layer.setCornerRadius_(16.0)
        layer.setMasksToBounds_(True)
        panel.setContentView_(surface)

        # Custom close control: no macOS title bar or system dialog chrome.
        close_button = HoverButton.alloc().initWithFrame_(NSMakeRect(width - 52, height - 48, 34, 32))
        close_button.setTitle_("✕")
        close_button.setBordered_(False)
        close_button.setFont_(NSFont.systemFontOfSize_(18))
        close_button.setContentTintColor_(NSColor.whiteColor())
        close_button.setWantsLayer_(True)
        close_button.layer().setCornerRadius_(8.0)
        close_button.layer().setMasksToBounds_(True)
        if hasattr(close_button, "setDarkelfBaseTint_"):
            close_button.setDarkelfBaseTint_(NSColor.whiteColor())
        close_button.setTarget_(self)
        close_button.setAction_("closeDarkelfAbout:")
        close_button.setToolTip_("Close About")
        surface.addSubview_(close_button)
        close_button.updateTrackingAreas()

        # Use the same accent-aware Darkelf shield as the Dock and lock screen.
        icon = NSImageView.alloc().initWithFrame_(NSMakeRect(199, 268, 112, 112))
        icon.setImage_(make_application_icon(256))
        icon.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        surface.addSubview_(icon)
        self._darkelf_about_logo = icon

        def text_field(value, y, size, color, bold=False, height=27):
            field = NSTextField.alloc().initWithFrame_(NSMakeRect(30, y, width - 60, height))
            field.setBordered_(False)
            field.setEditable_(False)
            field.setSelectable_(False)
            field.setDrawsBackground_(False)
            field.setAlignment_(NSCenterTextAlignment)
            field.setFont_(NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size))
            field.setTextColor_(color)
            field.setStringValue_(value)
            surface.addSubview_(field)
            return field

        white = NSColor.whiteColor()
        muted = NSColor.colorWithCalibratedWhite_alpha_(0.73, 1.0)
        self._darkelf_about_title = text_field("Darkelf Cocoa Browser", 227, 25, white, True, 36)
        self._darkelf_about_version = text_field(f"Version {APP_VERSION}", 200, 14, white)
        text_field("Native macOS privacy browser powered by Apple WebKit", 161, 13, muted)
        text_field("Ephemeral browsing  •  Tracker blocking  •  Fingerprint defenses", 133, 12, muted)
        text_field("Local MiniAI Sentinel  •  Custom Darkelf interface", 108, 12, muted)
        text_field("darkelfbrowser.com", 66, 13, muted)
        text_field("© 2025–2026 Darkelf Labs / Dr. Kevin Moore", 27, 11, muted)
        return panel


    @objc.IBAction
    def closeDarkelfAbout_(self, sender):
        panel = getattr(self, "_darkelf_about_panel", None)
        if panel is not None:
            panel.orderOut_(None)
            if panel.parentWindow() is not None:
                panel.parentWindow().removeChildWindow_(panel)


