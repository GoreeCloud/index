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
| Search field | Explicit accessible name; immediate local filtering on text changes for apps, selected files and safe actions so Enter does not use a stale query |
| Up/Down inside search | Select previous/next result, wrapping at the ends, scrolling the result into view when laid out, without moving focus out of the search field |
| Enter inside search | Activate the **selected** result, not blindly the first result |
| No matching results | Empty message and no selected result; Up/Down and Enter cannot activate a stale entry |
| Query or mode changes | Rebuild results and reset selection to first available result |
| Ctrl+1/2/3/4 | Switch All/Applications/Files/Actions mode and update visible button state |
| Escape | Clear a non-empty search, otherwise close the main window |
| Result accessible label | Identifies the kind, name and subtitle as plain text (no markup execution) |
| Result feedback | Position and title of the current selection appear in a GTK accessibility status role |
| Indexing status | Summary and action feedback use a GTK accessibility status role |
| Folder consent | Explicit confirmation for content permission changes, root replacement reauthorization and root revocation |

The desktop application has **no** global invoke shortcut, clipboard recording
or background search activity. File opening still invokes the system handler
only through explicit user activation and current authorization checks.

## Automated evidence

Run from the checkout in a Linux environment with GTK4/libadwaita and Xvfb:

    PYTHONPATH=src xvfb-run -a /usr/bin/python3 tools/smoke_gtk.py
    PYTHONPATH=src python3 -m unittest discover -s tests -v

The GTK smoke covers selection movement and wrap, modifier filtering, focus
preservation, selected-Enter activation dispatch, no-result behavior, status
roles, search modes and the existing indexing consent/reauthorization dialogs.
The test invokes the registered keyboard handler directly under GTK/Xvfb; it is
**not** a hardware-keyboard or assistive-technology end-to-end test. Linux CI
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
