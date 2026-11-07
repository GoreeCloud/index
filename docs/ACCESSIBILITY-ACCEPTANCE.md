# GoreeCloud Index — Linux keyboard and accessibility acceptance

**Status:** automated native GTK interaction checks implemented; human assistive
technology and visual acceptance remain **OPEN**. This is not a WCAG or
accessibility certification.

Design authority: [GoreeCloud UI](https://github.com/GoreeCloud/gc-ui),
especially its principle of clear, consistent, accessible interactions.
The Index preview currently uses GTK4/libadwaita system semantic appearance.
Do not infer adoption of GC UI Foundations tokens or completed GC UI migration.

## Implemented interaction contract

| Operation | Expected behavior |
| --- | --- |
| Search field | Prominent native GTK SearchEntry in a floating rounded, undecorated panel; explicit accessible name/description of Up/Down and Enter behavior, with selected row exposed as its active descendant and immediate local filtering |
| Up/Down inside search | Select previous/next result, wrapping at the ends, scrolling the result into view when laid out, without moving focus out of the search field |
| Enter inside search | Activate the **selected** result, not blindly the first result |
| No matching results | Empty message and no selected result; Up/Down and Enter cannot activate a stale entry |
| Query or mode changes | Rebuild results and reset selection to first available result |
| Ctrl+1/2/3/4 | Switch All/Applications/Files/Actions mode and update visible button state |
| Escape | Clear a non-empty search, otherwise close the main window |
| Result accessible label | Identifies the kind, name and subtitle as plain text (no markup execution) |
| Result feedback | Position and title of the current selection appear in a GTK accessibility status role |
| Indexing status | Summary and action feedback use a GTK accessibility status role |
| Folder consent | Compact gear control opens the full native folder manager; folder additions default to metadata-only and content, root reauthorization or revocation require separate confirmation |

The search palette uses icon-only All/Apps/Files/Actions filters with explicit
accessible labels and shortcuts, plus separate manage/refresh/close controls.
The undecorated GTK WindowHandle preserves draggable window behavior in
supported desktop environments; native frame, focus and placement require
real-compositor validation. The desktop application has **no** global invoke
shortcut, clipboard recording or background search activity. File opening still invokes the system handler
only through explicit user activation and current authorization checks.

## Automated evidence

Run from the checkout in a Linux environment with GTK4/libadwaita and Xvfb:

    PYTHONPATH=src xvfb-run -a /usr/bin/python3 tools/smoke_gtk.py
    PYTHONPATH=src python3 -m unittest discover -s tests -v

The GTK smoke covers selection movement and wrap, modifier filtering, focus
preservation, selected-Enter activation dispatch, no-result behavior, status
roles, SearchEntry/list item accessible roles, explicit search help, active
descendant updates, mode keyboard-shortcut metadata, metadata-only new-root
consent and the existing indexing consent/reauthorization dialogs.
A second native GTK run uses `GTK_A11Y=test G_DEBUG=fatal-warnings`, as
recommended by upstream GTK for deterministic automated accessibility checks.
GTK 4.14 exposes `DESCRIPTION` for keyboard help but not the newer
`HELP_TEXT` property, so the implementation retains 4.14 compatibility. An additional isolated X11/Xvfb layout smoke
checks initial 390 px and 440 px window widths and basic large-font behavior
without reading a user's real files:

    GDK_BACKEND=x11 PYTHONPATH=src xvfb-run -a /usr/bin/python3 tools/smoke_layout_gtk.py --width 390
    GDK_BACKEND=x11 PYTHONPATH=src xvfb-run -a /usr/bin/python3 tools/smoke_layout_gtk.py --width 440

Source-reviewed, synthetic [light](screenshots/linux-compact-light.png) and
[dark](screenshots/linux-compact-dark.png) screenshots provide initial
Spotlight-inspired palette visual evidence at approximately 650x460. GTK semantic appearance follows the OS;
neither image specifies a mandatory GoreeCloud palette. Compact result rows
may require vertical scrolling; these checks do not measure contrast ratios,
test screen-reader announcements or establish final premium design approval.
An isolated X11/AT-SPI probe on November 7, 2026, with a disposable
`dbus-run-session` accessibility bus, did not enumerate either Index **or a
minimal GTK4 control application**, even with its private IsEnabled property
set. This points to a probe-environment limitation, not a demonstrated Index
defect or screen-reader success. Orca in a real GNOME desktop remains a release
acceptance blocker; no live user accessibility settings were changed.
A native headless `tools/smoke_text_scale_gtk.py` regression now changes
the **test process's** GTK default font through Sans 12, 24 and 48 (nominal
100%, 200%, 400% baseline), checks increasing measured Pango text height,
390/440 px window containment, mapped search/filter/status controls,
responsive decorative-caption collapse, and restores default layout. It
also simulates a libadwaita high-contrast state to assert the corresponding
semantic CSS class is applied and removed. The real desktop's font and
contrast settings are never modified. These are automated layout/state
checks, **not** validated physical 400% assistive-technology usability,
WCAG contrast measurements or native high-contrast compositor proof.

    GDK_BACKEND=x11 PYTHONPATH=src xvfb-run -a /usr/bin/python3 tools/smoke_text_scale_gtk.py --width 390
    GDK_BACKEND=x11 PYTHONPATH=src xvfb-run -a /usr/bin/python3 tools/smoke_text_scale_gtk.py --width 440

The handler smoke invokes keyboard callbacks directly under GTK/Xvfb. A second
first-party `tools/smoke_keyboard_x11.py` now injects actual X11 key events
into a **separate isolated Xvfb display** and verifies Up/Down, selection
aware Enter, literal typing, Escape clear/close and Ctrl+2 mode switching.
The test uses only synthetic app results and refuses the live `:0`/`:1`
display, without operating a privileged input device or launching apps.

    GOREECLOUD_INDEX_PRIVATE_XVFB=1 GDK_BACKEND=x11 PYTHONPATH=src \
      xvfb-run -a /usr/bin/python3 tools/smoke_keyboard_x11.py

This catches actual GTK event routing regressions, but is **not** a physical
keyboard, Wayland, assistive-technology or full Orca end-to-end test. Linux CI
performs the same isolated smoke. Python unit tests address core code, not
visual or screen-reader usability.

## Required manual acceptance before Stable

- [ ] Real keyboard-only test on GNOME Wayland and X11: focus, arrow keys,
      Escape, selected Enter, mode switching, results scrolling, and dialogs
- [ ] At least one KDE/Plasma session check, noting theme and shortcut conflicts
- [ ] Orca screen-reader review of search-field name, result item kind/name,
      selection feedback, loading/error status and permission confirmations
- [ ] 200% and 400% UI text scaling; narrow-window reflow, clipped labels and
      both large and small display configurations
- [ ] System light/dark, high-contrast and reduced-motion preferences, including
      focused/selected-state visibility and contrast
- [ ] Pointer and keyboard interaction checks for root-management controls,
      destructive confirmation defaults, and accessible field descriptions
- [ ] GC UI design authority review using verified Foundations tokens and
      components/adapters where appropriate, plus screenshot-led comparison
- [ ] Distribution installs and upgrade/uninstall outside test runners only with
      explicit host authorization and a rollback plan

**Known limitations:** native GTK accessibility status roles have not been
validated with Orca in a real desktop session; mode and status changes could
be too verbose or insufficiently announced. Result selection is bounded and UI lists at most 75 entries. Offscreen
scrolling and actual keyboard event routing require real-display validation.
No claim of
complete GC UI design compliance, WCAG conformance or release readiness.
