"""Pure compact native palette sizing for GTK and Qt Quick Linux clients.

Native GDK/QScreen monitor geometry is in logical application pixels, not
necessarily the desktop panel-reduced work area. The compositor owns placement.
No monitor names, coordinates, identifiers or user settings are retained.
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_PALETTE_SIZE = (660, 448)
MIN_PALETTE_SIZE = (390, 300)


def _check_preferred(preferred_size: tuple[int, int]) -> None:
    if (
        not isinstance(preferred_size, tuple) or len(preferred_size) != 2
        or any(type(size) is not int for size in preferred_size)
        or any(size < minimum for size, minimum in zip(
            preferred_size, MIN_PALETTE_SIZE
        ))
    ):
        raise ValueError("Invalid compact palette preferred size")


def palette_startup_size(
    monitor_width: int,
    monitor_height: int,
    *,
    preferred_size: tuple[int, int] = DEFAULT_PALETTE_SIZE,
) -> tuple[int, int]:
    """Start windowed, keeping ~10% margins on small displays.

    Defaults preserve GTK's existing 660x448 footprint. Qt may request a
    different compact preferred size with the same conservative algorithm.
    The minimum compact layout wins on extremely small monitors; no window
    toolkit can guarantee full visibility below that floor.
    """
    _check_preferred(preferred_size)
    if monitor_width <= 0 or monitor_height <= 0:
        return preferred_size
    return (
        max(MIN_PALETTE_SIZE[0],
            min(preferred_size[0], monitor_width * 9 // 10)),
        max(MIN_PALETTE_SIZE[1],
            min(preferred_size[1], monitor_height * 9 // 10)),
    )


def palette_startup_size_for_monitors(
    monitor_sizes: Iterable[tuple[int, int]],
    *,
    preferred_size: tuple[int, int] = DEFAULT_PALETTE_SIZE,
) -> tuple[int, int]:
    """Fit on ANY available monitor, regardless of enumeration order.

    Wayland compositors choose window placement, potentially on a small
    secondary display. Use the smallest valid logical width and height
    independently. This can be conservative but never records topology.
    """
    _check_preferred(preferred_size)
    valid = [
        (width, height) for width, height in monitor_sizes
        if type(width) is int and type(height) is int
        and width > 0 and height > 0
    ]
    if not valid:
        return preferred_size
    return palette_startup_size(
        min(width for width, _ in valid),
        min(height for _, height in valid),
        preferred_size=preferred_size,
    )
