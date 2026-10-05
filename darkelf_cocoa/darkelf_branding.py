"""Darkelf Cocoa branding synchronized with the live session accent."""
from AppKit import NSApplication, NSBezierPath, NSColor, NSImage
from Foundation import NSMakeRect, NSMakeSize, NSPoint
from darkelf_theme import load_accent_rgba


def _accent_color():
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(*load_accent_rgba())


def make_application_icon(size=512.0):
    """Draw the Darkelf shield/keyhole icon using the current session accent."""
    s = float(size)
    image = NSImage.alloc().initWithSize_(NSMakeSize(s, s))
    image.lockFocus()
    try:
        # Dark rounded-square background.
        bg = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(s*0.03, s*0.03, s*0.94, s*0.94), s*0.16, s*0.16
        )
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.055, 0.050, 0.075, 1.0).setFill()
        bg.fill()

        accent = _accent_color()
        # Shield silhouette, intentionally matching the supplied Darkelf artwork.
        sh = NSBezierPath.bezierPath()
        sh.moveToPoint_(NSPoint(s*0.50, s*0.80))
        sh.lineToPoint_(NSPoint(s*0.78, s*0.66))
        sh.lineToPoint_(NSPoint(s*0.78, s*0.43))
        sh.curveToPoint_controlPoint1_controlPoint2_(
            NSPoint(s*0.50, s*0.13), NSPoint(s*0.78, s*0.28), NSPoint(s*0.64, s*0.18)
        )
        sh.curveToPoint_controlPoint1_controlPoint2_(
            NSPoint(s*0.22, s*0.43), NSPoint(s*0.36, s*0.18), NSPoint(s*0.22, s*0.28)
        )
        sh.lineToPoint_(NSPoint(s*0.22, s*0.66))
        sh.closePath()
        accent.setFill(); sh.fill()

        # Soft highlight edge.
        accent.colorWithAlphaComponent_(0.70).setStroke()
        sh.setLineWidth_(s*0.012); sh.stroke()

        # Keyhole cutout.
        dark = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.035, 0.035, 0.055, 1.0)
        dark.setFill()
        circle = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(s*0.42, s*0.47, s*0.16, s*0.16))
        circle.fill()
        key = NSBezierPath.bezierPath()
        key.moveToPoint_(NSPoint(s*0.46, s*0.49))
        key.lineToPoint_(NSPoint(s*0.43, s*0.30))
        key.lineToPoint_(NSPoint(s*0.57, s*0.30))
        key.lineToPoint_(NSPoint(s*0.54, s*0.49))
        key.closePath(); key.fill()
    finally:
        image.unlockFocus()
    return image


def sync_application_icon():
    """Update the running Cocoa/Dock icon to the current Darkelf accent."""
    try:
        NSApplication.sharedApplication().setApplicationIconImage_(make_application_icon())
        return True
    except Exception:
        return False
