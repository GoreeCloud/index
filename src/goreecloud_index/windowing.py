"""Pure compact GTK palette sizing for low-resolution displays.

GTK4 Gdk.Monitor geometry is in logical application pixels, not necessarily
the panel-reduced available work area. The compositor still owns placement.
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_PALETTE_SIZE = (660, 448)
MIN_PALETTE_SIZE = (390, 300)


def palette_startup_size(monitor_width: int, monitor_height: int) -> tuple[int, int]:
    """Start compact without requesting maximize or full-screen.

    Preserve the existing default on ordinary displays, but leave roughly
    10% margins on smaller monitors. On extremely small displays the tested
    minimum compact layout wins; no widget can guarantee visibility there.
    """
    if monitor_width <= 0 or monitor_height <= 0:
        return DEFAULT_PALETTE_SIZE
    return (
        max(MIN_PALETTE_SIZE[0],
            min(DEFAULT_PALETTE_SIZE[0], monitor_width * 9 // 10)),
        max(MIN_PALETTE_SIZE[1],
            min(DEFAULT_PALETTE_SIZE[1], monitor_height * 9 // 10)),
    )

def palette_startup_size_for_monitors(
    monitor_sizes: Iterable[tuple[int, int]],
) -> tuple[int, int]:
    """Fit the floating palette on ANY enumerated desktop monitor.

    A Wayland compositor chooses the initial location, which may not be the
    first or primary monitor. Using each valid logical monitor's minimum
    dimensions is conservative and independent of enumeration order.
    No coordinates, monitor names, or identifiers are stored.
    """
    valid = [
        (width, height) for width, height in monitor_sizes
        if type(width) is int and type(height) is int
        and width > 0 and height > 0
    ]
    if not valid:
        return DEFAULT_PALETTE_SIZE
    return palette_startup_size(
        min(width for width, _ in valid),
        min(height for _, height in valid),
    )
