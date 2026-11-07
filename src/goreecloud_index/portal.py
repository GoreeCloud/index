"""Open authorized files by inode-pinned fd via the freedesktop desktop portal.

Never accept file:// URIs or pathname-based fallbacks. This is a request for
the user's desktop to open a *specific fd*, not a promise that a third-party
handler will access its file only through the FD afterwards. This requires a
session bus and a portal supporting OpenURI.OpenFile (version >= 2).
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable


PORTAL_NAME = "org.freedesktop.portal.Desktop"
PORTAL_OBJECT = "/org/freedesktop/portal/desktop"
REQUEST_INTERFACE = "org.freedesktop.portal.Request"
OPEN_INTERFACE = "org.freedesktop.portal.OpenURI"


def request_open_fd(fd: int, on_result: Callable[[bool, str], None]) -> None:
    """Consume the checked O_PATH fd and request a desktop-mediated open.

    Caller must never use the pathname as a fallback. The portal receives an
    fd for the same inode that the authorized SQLite result identified.
    Success means the portal accepted/completed its action; it does not attest
    to the behavior or content access of external application handlers.
    """
    if not isinstance(fd, int) or fd < 0:
        raise ValueError("Invalid file descriptor")
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    connection = None
    fd_list = None
    try:
        # Check the bus before creating an asynchronous request. In a typical
        # Linux session bus_get_sync is immediate; absent bus => explicit error.
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        if connection is None or not connection.get_unique_name():
            raise RuntimeError("Desktop session bus unavailable")
        fd_list = Gio.UnixFDList.new()
        index = fd_list.append(fd)  # SCM_RIGHTS duplicates this open inode.
    finally:
        # This API *consumes* the caller's checked descriptor even on failure.
        os.close(fd)

    token = "gc_index_" + secrets.token_hex(12)
    unique = connection.get_unique_name()[1:].replace(".", "_")
    expected = f"/org/freedesktop/portal/desktop/request/{unique}/{token}"
    state = {
        "done": False,
        "path": expected,
        "subscription": None,
        "timer": None,
    }
    cancellable = Gio.Cancellable()

    def finish(ok: bool, message: str) -> None:
        if state["done"]:
            return
        state["done"] = True
        if state["subscription"] is not None:
            connection.signal_unsubscribe(state["subscription"])
            state["subscription"] = None
        if state["timer"] is not None:
            GLib.source_remove(state["timer"])
            state["timer"] = None
        on_result(ok, message)

    def response(_connection, _sender, object_path,
                 _interface, _signal_name, parameters) -> None:
        if object_path != state["path"] or state["done"]:
            return
        result_code, _details = parameters.unpack()
        if result_code == 0:
            finish(True, "Desktop accepted the file-open request")
        elif result_code == 1:
            finish(False, "File opening canceled")
        else:
            finish(False, "Desktop could not open the selected file")

    def subscribe(path: str) -> None:
        state["subscription"] = connection.signal_subscribe(
            PORTAL_NAME, REQUEST_INTERFACE, "Response", path,
            None, Gio.DBusSignalFlags.NONE, response,
        )

    def timed_out() -> bool:
        if state["done"]:
            return GLib.SOURCE_REMOVE
        # Ask the portal to close its pending prompt before reporting failure.
        try:
            connection.call(
                PORTAL_NAME, state["path"], REQUEST_INTERFACE, "Close", None,
                None, Gio.DBusCallFlags.NONE, 2000, None, None,
            )
        except GLib.Error:
            pass  # A disconnected session must not cause a GTK exception.
        cancellable.cancel()
        # The timeout source is already dispatching: finish must not try to
        # remove its own GLib source ID a second time.
        state["timer"] = None
        finish(False, "Desktop file-opening request timed out")
        return GLib.SOURCE_REMOVE

    def on_submit(bus: Gio.DBusConnection, result: Gio.AsyncResult) -> None:
        if state["done"]:
            return
        try:
            reply, _unused_fd_list = bus.call_with_unix_fd_list_finish(result)
            path = reply.unpack()[0]
            if not isinstance(path, str) or not path.startswith(
                "/org/freedesktop/portal/desktop/request/"
            ):
                raise RuntimeError("Unexpected desktop portal request handle")
            if path != state["path"]:
                # Old portals may return a different object path. Subscribe
                # there rather than silently treating the request as success.
                if state["subscription"] is not None:
                    bus.signal_unsubscribe(state["subscription"])
                state["path"] = path
                subscribe(path)
        except (GLib.Error, ValueError, RuntimeError) as exc:
            finish(False, f"Desktop portal unavailable or rejected request: {exc}")

    try:
        # Subscribing BEFORE the OpenFile call avoids losing a fast response.
        subscribe(expected)
        state["timer"] = GLib.timeout_add_seconds(45, timed_out)
        connection.call_with_unix_fd_list(
            PORTAL_NAME, PORTAL_OBJECT, OPEN_INTERFACE, "OpenFile",
            GLib.Variant(
                "(sha{sv})",
                ("", index, {
                    "handle_token": GLib.Variant("s", token),
                    "writable": GLib.Variant("b", False),
                }),
            ),
            GLib.VariantType.new("(o)"), Gio.DBusCallFlags.NONE, 5000,
            fd_list, cancellable, on_submit,
        )
    except Exception:
        if state["subscription"] is not None:
            connection.signal_unsubscribe(state["subscription"])
        if state["timer"] is not None:
            GLib.source_remove(state["timer"])
        raise
