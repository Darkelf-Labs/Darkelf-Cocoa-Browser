from Cocoa import *
from AppKit import *
from Foundation import *
import objc
from urllib.parse import quote_plus
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
        opts = NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways
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


class AddressField(NSSearchField):
    """Darkelf-owned URL/search field context menu.

    Cocoa's stock NSSearchField menu can expose a system "Search With …"
    service that launches the macOS default browser.  This menu deliberately
    keeps web searches inside the owning Darkelf Browser.
    """

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

    def _selected_text(self):
        try:
            editor = self.currentEditor()
            if editor is None:
                return ""
            rng = editor.selectedRange()
            text = str(editor.string())
            if rng.length <= 0:
                return ""
            return text[rng.location:rng.location + rng.length].strip()
        except Exception:
            return ""

    def darkelfSearchSelection_(self, sender):
        query = self._selected_text()
        owner = getattr(self, "_owner", None)
        if query and owner is not None:
            owner._add_tab("https://duckduckgo.com/?q=" + quote_plus(query))

    def menuForEvent_(self, event):
        menu = NSMenu.alloc().initWithTitle_("Darkelf")

        def add(title, action, target=None, enabled=True):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
            if target is not None:
                item.setTarget_(target)
            item.setEnabled_(bool(enabled))
            menu.addItem_(item)
            return item

        selected = self._selected_text()
        add("Cut", "cut:")
        add("Copy", "copy:")
        add("Paste", "paste:")
        add("Select All", "selectAll:")
        menu.addItem_(NSMenuItem.separatorItem())
        label = "Search DuckDuckGo in New Darkelf Tab"
        add(label, "darkelfSearchSelection:", self, bool(selected))
        return menu

    def _install_editor_menu(self):
        """Force the shared NSTextView field editor to use Darkelf's menu.

        Once an NSSearchField is editing, right-click events are received by the
        window field editor (NSTextView), not by the NSSearchField itself.
        Installing the menu on that editor prevents macOS Services from adding
        an external "Search With DuckDuckGo" command.
        """
        try:
            editor = self.currentEditor()
            if editor is not None:
                editor.setMenu_(self.menuForEvent_(None))
        except Exception as e:
            print("Darkelf field-editor menu error:", e)

    def mouseDown_(self, event):
        objc.super(AddressField, self).mouseDown_(event)
        self._install_editor_menu()

    def becomeFirstResponder(self):
        result = objc.super(AddressField, self).becomeFirstResponder()
        self._install_editor_menu()
        return result

    def rightMouseDown_(self, event):
        try:
            menu = self.menuForEvent_(event)
            editor = self.currentEditor()
            target_view = editor if editor is not None else self
            if editor is not None:
                editor.setMenu_(menu)
            NSMenu.popUpContextMenu_withEvent_forView_(menu, event, target_view)
        except Exception as e:
            print("Darkelf context menu error:", e)


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




def apply_darkelf_theme():
    """Apply the original Darkelf Cocoa dark appearance."""
    green = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.20, 0.78, 0.35, 1)
    NSApplication.sharedApplication().setAppearance_(
        NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua")
    )
