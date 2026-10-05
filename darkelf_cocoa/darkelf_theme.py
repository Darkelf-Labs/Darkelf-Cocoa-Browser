"""Shared Darkelf Cocoa UI geometry and session accent settings."""

TOOLBAR_HEIGHT = 52.0
TOOLBAR_PADDING = 10.0
TOOLBAR_BUTTON_SIZE = 32.0
TOOLBAR_BUTTON_GAP = 6.0
TOOLBAR_RIGHT_GAP = 14.0
URLBAR_MIN_WIDTH = 280.0
URLBAR_MAX_WIDTH = 1200.0

DEFAULT_ACCENT_NAME = "Green"

ACCENT_PRESETS = {
    "Green": (0.20, 0.78, 0.35, 1.0),
    "Blue": (0.20, 0.55, 1.00, 1.0),
    "Purple": (0.69, 0.40, 1.00, 1.0),
    "Orange": (1.00, 0.58, 0.18, 1.0),
    "Red": (1.00, 0.28, 0.32, 1.0),
    "Teal": (0.18, 0.82, 0.78, 1.0),
}

# Accent is intentionally session-scoped. Every Cocoa launch begins with the
# original Darkelf green; a user selection updates all live UI for that run.
_SESSION_ACCENT = ACCENT_PRESETS[DEFAULT_ACCENT_NAME]

def load_accent_rgba():
    return _SESSION_ACCENT

def save_accent_rgba(rgba):
    global _SESSION_ACCENT
    _SESSION_ACCENT = tuple(max(0.0, min(1.0, float(v))) for v in rgba)
    return _SESSION_ACCENT

def reset_accent_for_launch():
    global _SESSION_ACCENT
    _SESSION_ACCENT = ACCENT_PRESETS[DEFAULT_ACCENT_NAME]
    return _SESSION_ACCENT
