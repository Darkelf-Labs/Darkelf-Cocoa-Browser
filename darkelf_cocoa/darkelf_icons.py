import os
from AppKit import NSImage
from Foundation import NSMakeSize

_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "nav")

def load_toolbar_svg(filename, size=18.0):
    path = os.path.join(_ASSET_DIR, filename)
    if not os.path.isfile(path):
        print(f"[SVG] Missing toolbar asset: {path}")
        return None
    image = NSImage.alloc().initWithContentsOfFile_(path)
    if image is None:
        print(f"[SVG] Failed to load toolbar asset: {path}")
        return None
    try:
        image.setSize_(NSMakeSize(float(size), float(size)))
        image.setTemplate_(True)
    except Exception:
        pass
    return image

def load_nav_svg(filename, size=18.0):
    return load_toolbar_svg(filename, size=size)
