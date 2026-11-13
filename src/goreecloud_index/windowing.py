"""Pure compact GTK palette sizing for low-resolution displays.

GTK4 Gdk.Monitor geometry is in logical application pixels, not necessarily
the panel-reduced available work area. The compositor still owns placement.
"""

from __future__ import annotations

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
