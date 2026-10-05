# Darkelf Cocoa Modules

Source of truth: Darkelf Cocoa Browser v7.0.7.

- `browser.py` — launcher
- `application.py` — Browser/AppDelegate and Cocoa UI orchestration
- `darkelf_delegates.py` — WebKit/Cocoa delegates
- `darkelf_content_rules.py` — content blocking and filter subscriptions
- `darkelf_sentinel.py` — MiniAI/Sentinel
- `darkelf_network.py` — network policy
- `darkelf_pq.py` — PQ/session identity
- `darkelf_isolation.py` — first-party isolation
- `darkelf_spoofing.py` — fingerprint/screen spoofing
- `darkelf_downloads.py` — download UI/helpers
- `darkelf_tabs.py` — Tab model and destruction
- `darkelf_ui.py` — reusable Cocoa UI classes
- `darkelf_theme.py` — shared toolbar/UI geometry constants
- `darkelf_pages.py` — internal homepage and unified defense JS
- `darkelf_policy.py` — local policy constants
- `darkelf_icons.py` — bundled SVG toolbar image loader
- `assets/nav/*.svg` — Back, Forward, Reload, Bookmark, filled Bookmark, Menu and Close vector assets
- `darkelf_utils.py` — shared helpers

## UI behavior

Navigation actions remain `actBack:`, `actFwd:`, and `actReload:`. Back/Forward now reflect WebKit history availability. Bookmark uses outline/filled SVG state and a matching tooltip. The collapsible menu switches between Menu and Close SVGs. The URL field uses responsive min/max sizing.

## Release packaging

Release ZIPs exclude `__pycache__`, `.pyc`, `.DS_Store`, `__MACOSX`, and AppleDouble `._*` metadata.
