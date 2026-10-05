# Darkelf Cocoa v7.0.7 UI Polish Audit

Applied low-risk improvements to the working modular build:

- Responsive URL bar with centralized geometry constants.
- Back/Forward enabled state follows the active WKWebView history.
- Bookmark outline/filled SVG state plus dynamic tooltip.
- Menu/Close SVG state follows the collapsible panel.
- Sidebar Bookmarks row uses bundled SVG artwork.
- All bundled toolbar SVGs use template-friendly `currentColor`.
- Release packaging excludes cache/macOS metadata.
- Updated module documentation.

Deferred intentionally to avoid destabilizing the working PyObjC build:

- Wholesale replacement of Cocoa/WebKit wildcard imports.
- Large-scale controller extraction from `application.py`.
- Removal/reconciliation of duplicate legacy method definitions (including `_sync_addr`) until a dedicated behavioral equivalence pass is performed.
- Privacy/network behavior changes.

## v6 UI/context-menu update
- URL/search field now owns its contextual menu instead of falling through to macOS Search Services.
- Selected-text DuckDuckGo searches open with Browser._add_tab(), keeping them inside Darkelf Cocoa.
- URL bar maximum width increased to 1200 px.
- Added persistent native accent presets (Green, Blue, Purple, Orange, Red, Teal) and macOS Custom Color panel.
- Accent preference stores only RGBA UI data in ~/.darkelf/ui-settings.json; browser/site/privacy state is unchanged.

## v7 unified accent pass
- Accent presets/custom color now theme the internal Darkelf Home page live.
- Active tabs use an accent-tinted dark surface, accent border/title/close control.
- Inactive tabs remain neutral and gain a subtle accent hover surface.
- Toolbar HoverButton controls use accent hover/pressed feedback and restore their own base tint on exit.
- URL focus border and menu panel border remain tied to the same saved accent.
- Privacy/network/PQ/filtering behavior was not changed.


## v8 theme alignment
- Green is explicitly the clean-install default accent.
- Back/Forward/Reload now share identical 32x32 toolbar geometry so hover surfaces center consistently.
- Main side-menu controls follow the live selected accent; Nuke Session remains red as a destructive-action exception.
- Bookmark/menu utility rows now use HoverButton for consistent accent hover surfaces.

## v9 theme/control corrections
- Accent is session-scoped: every Cocoa launch starts with original Darkelf green.
- Preset/custom accent changes propagate live without writing `~/.darkelf/ui-settings.json`.
- URL border navigation delegate now uses the live accent instead of hardcoded green.
- Address-field selection highlight uses the live accent.
- Toolbar image position uses `NSImageOnly` (the old numeric `2` was `NSImageLeft`), centering icons inside 32x32 hover surfaces.
- Sidebar rows are normalized to identical 192x34 hover surfaces/tracking after reparenting.


## v12 branding
- Supplied purple Darkelf branding PNGs recolored to original Darkelf green for packaged/default assets.
- Running Cocoa/Dock icon is generated from the live session accent and updates with Accent Color changes.
- Clean launch still resets the session accent to Green.
