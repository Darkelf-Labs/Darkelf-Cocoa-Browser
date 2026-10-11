from Cocoa import *
from AppKit import *
from Foundation import *
from WebKit import WKWebView
import objc
from urllib.parse import quote_plus
import subprocess
from .darkelf_theme import load_accent_rgba

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class DarkelfMenuDelegate(NSObject):

    def menu_willOpen_(self, menu, event):
        for item in menu.itemArray():
            item.setAttributedTitle_(
                NSAttributedString.alloc().initWithString_attributes_(
                    item.title(), {"NSForegroundColor": NSColor.whiteColor()}
                )
            )


class HoverButton(NSButton):
    def init(self):
        self = objc.super(HoverButton, self).init()
        if self is None:
            return None
        self._hoverArea = None
        self._darkelfBaseTint = None
        return self

    def updateTrackingAreas(self):
        if getattr(self, "_hoverArea", None) is not None:
            self.removeTrackingArea_(self._hoverArea)
        opts = (NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways
                | NSTrackingInVisibleRect)
        self._hoverArea = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(), opts, self, None
        )
        self.addTrackingArea_(self._hoverArea)
        objc.super(HoverButton, self).updateTrackingAreas()

    def setDarkelfBaseTint_(self, color):
        self._darkelfBaseTint = color
        try:
            self.setContentTintColor_(color)
        except Exception:
            pass

    def mouseEntered_(self, evt):
        try:
            accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
            self.setContentTintColor_(accent)
            self.setWantsLayer_(True)
            layer = self.layer()
            layer.setCornerRadius_(8.0)
            layer.setMasksToBounds_(True)
            layer.setBackgroundColor_(accent.colorWithAlphaComponent_(0.14).CGColor())
        except Exception:
            pass

    def mouseExited_(self, evt):
        try:
            base = getattr(self, "_darkelfBaseTint", None) or NSColor.whiteColor()
            self.setContentTintColor_(base)
            if self.layer():
                self.layer().setBackgroundColor_(NSColor.clearColor().CGColor())
        except Exception:
            pass


class TabHoverView(NSView):
    """Dark tab surface with Shadow-style accent hover treatment."""
    def initWithFrame_(self, frame):
        self = objc.super(TabHoverView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._hoverArea = None
        self._selected = False
        self.setWantsLayer_(True)
        return self

    def setDarkelfSelected_(self, selected):
        self._selected = bool(selected)
        self._apply_surface(False)

    def _apply_surface(self, hovered=False):
        if not self.layer():
            return
        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
        if self._selected:
            bg = accent.colorWithAlphaComponent_(0.16)
            border = accent.colorWithAlphaComponent_(0.90)
        elif hovered:
            bg = accent.colorWithAlphaComponent_(0.09)
            border = accent.colorWithAlphaComponent_(0.42)
        else:
            bg = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.09, 0.11, 0.13, 0.95)
            border = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.17, 0.19, 0.22, 1.0)
        self.layer().setBackgroundColor_(bg.CGColor())
        self.layer().setBorderWidth_(1.0)
        self.layer().setBorderColor_(border.CGColor())

    def updateTrackingAreas(self):
        if self._hoverArea is not None:
            self.removeTrackingArea_(self._hoverArea)
        opts = NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways
        self._hoverArea = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(), opts, self, None
        )
        self.addTrackingArea_(self._hoverArea)
        objc.super(TabHoverView, self).updateTrackingAreas()

    def mouseEntered_(self, event):
        self._apply_surface(True)

    def mouseExited_(self, event):
        self._apply_surface(False)


class SearchHandler(NSObject):
    def initWithOwner_(self, owner): ...
    def userContentController_didReceiveScriptMessage_(self, controller, message):
        self = objc.super(SearchHandler, self).init()
        if self is None:
            return None
        self.owner = owner
        return self

    def userContentController_didReceiveScriptMessage_(self, controller, message):
        try:
            owner = getattr(self, "owner", None)
            if (
                not owner
                or not getattr(owner, "tabs", None)
                or getattr(owner, "active", -1) < 0
            ):
                return

            body = message.body()
            print("🔥 MESSAGE RECEIVED:", body)

            if body == "darkelf_native_fullscreen":
                print("🔥 FULLSCREEN TRIGGERED")
                owner.window.toggleFullScreen_(None)
                return

            q = str(body)
            # Only search if q is non-empty, longer than 1 character
            if not q or len(q.strip()) < 2:
                return  # Ignore short/no input

            url = "https://www.mojeek.com/search?q=" + re.sub(r"\s+", "+", q)
            owner._add_tab(url)

        except Exception as e:
            print("SearchHandler error:", e)


def _darkelf_edit_menu():
    """Only text editing actions; no macOS Search With / Services actions."""
    menu = NSMenu.alloc().initWithTitle_("Darkelf Text Editing")
    for title, action in (
        ("Cut", "cut:"),
        ("Copy", "copy:"),
        ("Paste", "paste:"),
        ("Select All", "selectAll:"),
    ):
        menu.addItem_(NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, action, ""
        ))
    return menu


# Address-bar-only Darkelf context panel. WebKit page menus remain native.
class _DarkelfContextActions(NSObject):
    def initWithEditor_panel_(self, editor, panel):
        self = objc.super(_DarkelfContextActions, self).init()
        if self is not None:
            self.editor = editor
            self.panel = panel
        return self

    def performEdit_(self, sender):
        actions = {1: "cut_", 2: "copy_", 3: "paste_", 4: "selectAll_"}
        method = actions.get(int(sender.tag()))
        _darkelf_context_popup.hide()
        if method and self.editor is not None:
            # Explicit editor target: the nonactivating panel must not steal focus.
            try:
                getattr(self.editor, method)(None)
            except Exception as exc:
                print("[Darkelf Edit Menu]", exc)


class _DarkelfContextPopup:
    """Borderless, nonactivating AppKit panel; never touches webpage menus."""

    def __init__(self):
        self.panel = None
        self.monitor = None
        self.actions = None
        self.buttons = []

    def hide(self):
        if self.panel is not None:
            self.panel.orderOut_(None)
        if self.monitor is not None:
            NSEvent.removeMonitor_(self.monitor)
            self.monitor = None

    def show(self, event, view, editor):
        if event is None:
            return False
        self.hide()
        if editor is None or view.window() is None:
            return False
        width, height = 250, 158
        origin = view.convertPoint_toView_(event.locationInWindow(), None) if event.window() is None else event.locationInWindow()
        screen = view.window().convertRectToScreen_(NSMakeRect(origin.x, origin.y, 0, 0)).origin
        screen_frame = view.window().screen().visibleFrame()
        x = max(screen_frame.origin.x + 4, min(screen.x, screen_frame.origin.x + screen_frame.size.width - width - 4))
        y = max(screen_frame.origin.y + 4, min(screen.y - height, screen_frame.origin.y + screen_frame.size.height - height - 4))
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height), style, NSBackingStoreBuffered, False)
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setHasShadow_(True)
        self.panel.setHidesOnDeactivate_(True)
        self.panel.setBecomesKeyOnlyIfNeeded_(True)
        self.panel.setLevel_(NSPopUpMenuWindowLevel)
        surface = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        surface.setWantsLayer_(True)
        layer = surface.layer()
        layer.setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.02, 0.025, 0.03, 0.96).CGColor())
        layer.setCornerRadius_(13.0)
        layer.setMasksToBounds_(True)
        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
        layer.setBorderWidth_(1.0)
        layer.setBorderColor_(accent.colorWithAlphaComponent_(0.60).CGColor())
        self.panel.setContentView_(surface)
        self.actions = _DarkelfContextActions.alloc().initWithEditor_panel_(editor, self.panel)
        self.buttons = []
        selection = editor.selectedRange().length > 0
        can_paste = bool(NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString))
        for index, (label, symbol, shortcut) in enumerate((
            ("Cut", "scissors", "⌘X"), ("Copy", "doc.on.doc", "⌘C"),
            ("Paste", "doc.on.clipboard", "⌘V"), ("Select All", "selection.pin.in.out", "⌘A"),
        ), 1):
            row = HoverButton.alloc().initWithFrame_(NSMakeRect(8, height - 8 - index * 36, width - 16, 33))
            row.setBordered_(False)
            row.setAlignment_(NSLeftTextAlignment)
            row.setFont_(NSFont.systemFontOfSize_(13))
            row.setTitle_("   " + label + "    " + shortcut)
            row.setAttributedTitle_(NSAttributedString.alloc().initWithString_attributes_(
                "   " + label + "     " + shortcut,
                {NSForegroundColorAttributeName: NSColor.whiteColor(), NSFontAttributeName: NSFont.systemFontOfSize_(13)}))
            row.setTarget_(self.actions)
            row.setAction_("performEdit:")
            row.setTag_(index)
            row.setEnabled_(selection if index in (1, 2) else can_paste if index == 3 else True)
            row.setWantsLayer_(True)
            surface.addSubview_(row)
            self.buttons.append(row)
        self.panel.orderFrontRegardless()

        def dismiss_on_outside(ev):
            if ev.window() is not self.panel:
                self.hide()
            return ev

        self.monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSEventMaskLeftMouseDown | NSEventMaskRightMouseDown | NSEventMaskKeyDown,
            dismiss_on_outside)
        return True


_darkelf_context_popup = _DarkelfContextPopup()


def _show_darkelf_edit_popup(event, view):
    if event is None:
        return False
    editor = view if isinstance(view, NSTextView) else view.currentEditor()
    return _darkelf_context_popup.show(event, view, editor)


class DarkelfAddressEditor(NSTextView):
    """Address field editor with a strictly edit-only right-click menu."""

    def menuForEvent_(self, event):
        # Returning a native NSMenu causes the gray macOS popup to flash.
        # Route every editor context request to our Darkelf panel instead.
        _show_darkelf_edit_popup(event, self)
        return None

    def rightMouseDown_(self, event):
        # NSTextView's default right-click implementation augments menus with
        # macOS Services (including external-browser search actions). Bypass
        # that implementation and display our own menu directly instead.
        _show_darkelf_edit_popup(event, self)

    def validRequestorForSendType_returnType_(self, send_type, return_type):
        # This field editor does not advertise selected address text to the
        # system Services framework. Clipboard Cut/Copy/Paste still work.
        return None


class AddressField(NSSearchField):
    """URL field with an edit-only menu; the actual field editor is also protected."""

    def initWithFrame_owner_(self, frame, owner):
        self = objc.super(AddressField, self).initWithFrame_(frame)
        if self is None:
            return None
        self._owner = owner
        return self

    def drawFocusRingMask(self):
        pass

    def focusRingMaskBounds(self):
        return NSMakeRect(0, 0, 0, 0)

    def menuForEvent_(self, event):
        _show_darkelf_edit_popup(event, self)
        return None

    def _install_editor_menu(self):
        editor = self.currentEditor()
        if editor is not None:
            editor.setMenu_(None)

    def mouseDown_(self, event):
        objc.super(AddressField, self).mouseDown_(event)
        self._install_editor_menu()

    def becomeFirstResponder(self):
        result = objc.super(AddressField, self).becomeFirstResponder()
        self._install_editor_menu()
        return result

    def rightMouseDown_(self, event):
        # The search-field cell can otherwise show its native menu before
        # the Darkelf field editor receives the right-click.
        editor = self.currentEditor()
        if editor is None:
            try:
                self.window().makeFirstResponder_(self)
                editor = self.currentEditor()
            except Exception:
                pass
        if editor is not None:
            editor.setMenu_(None)
        _darkelf_context_popup.show(event, self, editor)


class DraggableFindBar(NSView):

    def mouseDown_(self, event):

        self._drag_start = event.locationInWindow()
        self._start_origin = self.frame().origin

    def mouseDragged_(self, event):

        current = event.locationInWindow()

        dx = current.x - self._drag_start.x
        dy = current.y - self._drag_start.y

        new_x = self._start_origin.x + dx
        new_y = self._start_origin.y + dy

        self.setFrameOrigin_((new_x, new_y))


class DarkelfSearchField(NSSearchField):

    def cancelOperation_(self, sender):

        try:

            if hasattr(self, "browser"):
                self.browser.hideFindBar_(None)

        except Exception as e:

            print("[FindBar ESC Error]", e)

    def keyDown_(self, event):

        # fallback

        if event.keyCode() == 53:

            try:

                if hasattr(self, "browser"):
                    self.browser.hideFindBar_(None)

            except Exception as e:

                print("[FindBar ESC Error]", e)

            return

        objc.super(DarkelfSearchField, self).keyDown_(event)





def open_apple_passwords():
    """Open Apple's Passwords app; never read or inject credentials."""
    try:
        subprocess.Popen(["open", "-a", "Passwords"], close_fds=True)
    except Exception as exc:
        print("[Darkelf Passwords]", exc)


class _DarkelfPageActions(NSObject):
    def initWithView_(self, view):
        self = objc.super(_DarkelfPageActions, self).init()
        if self is not None:
            self.view = view
        return self

    def performPage_(self, sender):
        tag = int(sender.tag())
        view = self.view
        owner = getattr(view, "_darkelf_owner", None)
        _darkelf_context_popup.hide()
        try:
            if tag == 1 and view.canGoBack(): view.goBack()
            elif tag == 2 and view.canGoForward(): view.goForward()
            elif tag == 3:
                if owner is not None: owner.actReload_(None)
                else: view.reload_(None)
            elif tag == 4:
                url = view.URL()
                if url is not None:
                    NSPasteboard.generalPasteboard().clearContents()
                    NSPasteboard.generalPasteboard().setString_forType_(str(url.absoluteString()), NSPasteboardTypeString)
            elif tag == 5: view.evaluateJavaScript_completionHandler_("document.execCommand('copy')", None)
            elif tag == 6: view.evaluateJavaScript_completionHandler_("document.execCommand('selectAll')", None)
            elif tag == 8 and owner is not None: owner.showFindBar()
        except Exception as exc:
            print("[Darkelf Page Menu]", exc)


class DarkelfWebView(WKWebView):
    """WKWebView with an AppKit Darkelf-styled right-click panel."""
    def setDarkelfOwner_(self, owner):
        self._darkelf_owner = owner

    def rightMouseDown_(self, event):
        if not _darkelf_context_popup.show_page(event, self):
            objc.super(DarkelfWebView, self).rightMouseDown_(event)


def _darkelf_show_page(self, event, view):
    self.hide()
    if view.window() is None:
        return False
    entries = [
        ("Back", "⌘←", 1, bool(view.canGoBack())),
        ("Forward", "⌘→", 2, bool(view.canGoForward())),
        ("Reload", "⌘R", 3, True),
        ("Copy Page URL", "⇧⌘C", 4, view.URL() is not None),
        ("Copy Selection", "⌘C", 5, True),
        ("Select All", "⌘A", 6, True),
        ("Find in Page", "⌘F", 8, True),
    ]
    width, height = 258, len(entries)*34 + 16
    pos = view.window().convertRectToScreen_(NSMakeRect(event.locationInWindow().x, event.locationInWindow().y, 0, 0)).origin
    frame = view.window().screen().visibleFrame()
    x = max(frame.origin.x+4, min(pos.x, frame.origin.x+frame.size.width-width-4))
    y = max(frame.origin.y+4, min(pos.y-height, frame.origin.y+frame.size.height-height-4))
    self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x,y,width,height), NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
        NSBackingStoreBuffered, False)
    self.panel.setOpaque_(False)
    self.panel.setBackgroundColor_(NSColor.clearColor())
    self.panel.setHasShadow_(True)
    self.panel.setHidesOnDeactivate_(True)
    self.panel.setLevel_(NSPopUpMenuWindowLevel)
    surface = NSView.alloc().initWithFrame_(NSMakeRect(0,0,width,height))
    surface.setWantsLayer_(True)
    layer = surface.layer()
    layer.setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.02,0.025,0.03,0.96).CGColor())
    layer.setCornerRadius_(13)
    layer.setMasksToBounds_(True)
    accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())
    layer.setBorderWidth_(1)
    layer.setBorderColor_(accent.colorWithAlphaComponent_(0.65).CGColor())
    self.panel.setContentView_(surface)
    self.actions = _DarkelfPageActions.alloc().initWithView_(view)
    self.buttons = []
    for i,(label, shortcut, tag, enabled) in enumerate(entries):
        button = HoverButton.alloc().initWithFrame_(NSMakeRect(8,height-8-(i+1)*34,width-16,31))
        button.setBordered_(False)
        button.setAlignment_(NSLeftTextAlignment)
        button.setFont_(NSFont.systemFontOfSize_(13))
        button.setTitle_("   " + label + "     " + shortcut)
        button.setTarget_(self.actions)
        button.setAction_("performPage:")
        button.setTag_(tag)
        button.setEnabled_(enabled)
        surface.addSubview_(button)
        self.buttons.append(button)
    self.panel.orderFrontRegardless()
    def dismiss(ev):
        if ev.window() is not self.panel:
            self.hide()
        return ev
    self.monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
        NSEventMaskLeftMouseDown | NSEventMaskRightMouseDown | NSEventMaskKeyDown, dismiss)
    return True

_DarkelfContextPopup.show_page = _darkelf_show_page

def apply_darkelf_theme():
    """Apply Darkelf's dark appearance without forcing a fixed accent color."""
    NSApplication.sharedApplication().setAppearance_(
        NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua")
    )
