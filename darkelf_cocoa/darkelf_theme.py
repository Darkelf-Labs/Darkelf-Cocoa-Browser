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
    "Cyan": (0.12, 0.82, 0.98, 1.0),
    "Gold": (0.96, 0.75, 0.22, 1.0),
    "Pink": (1.00, 0.42, 0.68, 1.0),
    "Magenta": (0.88, 0.30, 0.85, 1.0),
    "Amber": (1.00, 0.68, 0.12, 1.0),
    "Silver": (0.72, 0.77, 0.83, 1.0),
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


# Cocoa's native accent palette is discrete. Teal/custom colors are mapped
# to the nearest public macOS accent while Darkelf's own UI keeps exact RGB.
_COCOA_ACCENTS = {
    0: (1.00, 0.23, 0.19),  # red
    1: (1.00, 0.58, 0.00),  # orange
    2: (1.00, 0.80, 0.00),  # yellow
    3: (0.20, 0.78, 0.35),  # green
    4: (0.00, 0.48, 1.00),  # blue
    5: (0.69, 0.32, 0.87),  # purple
    6: (1.00, 0.18, 0.33),  # pink
}

def cocoa_accent_value_for_rgba(rgba):
    try:
        r, g, b = map(float, rgba[:3])
    except Exception:
        return 3
    return min(
        _COCOA_ACCENTS,
        key=lambda k: sum((v - t) ** 2 for v, t in zip((r, g, b), _COCOA_ACCENTS[k]))
    )


# Homepage background is session-scoped, matching Cocoa's accent behavior.
DEFAULT_BACKGROUND_NAME = "Darkelf Glow"
BACKGROUND_PRESETS = (
    "Darkelf Glow",
    "Midnight",
    "Aurora",
    "Nebula",
    "Carbon",
    "Pure Black",
    "Deep Ocean",
    "Crimson Eclipse",
    "Emerald Matrix",
    "Arctic Frost",
)
_SESSION_BACKGROUND = DEFAULT_BACKGROUND_NAME

def load_background_name():
    return _SESSION_BACKGROUND

def save_background_name(name):
    global _SESSION_BACKGROUND
    name = str(name)
    _SESSION_BACKGROUND = name if name in BACKGROUND_PRESETS else DEFAULT_BACKGROUND_NAME
    return _SESSION_BACKGROUND

def reset_background_for_launch():
    global _SESSION_BACKGROUND
    _SESSION_BACKGROUND = DEFAULT_BACKGROUND_NAME
    return _SESSION_BACKGROUND
