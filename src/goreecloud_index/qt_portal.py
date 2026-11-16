"""Qt Quick desktop-portal OpenFile, without PyGObject or pathname fallbacks.

The caller supplies a *validated inode-pinned* O_PATH descriptor. We consume
that descriptor on every path, hand a duplicated FD to the session D-Bus and
track exactly one portal Request.Response. We cannot control third-party
handlers after they receive the portal request.
"""
from __future__ import annotations

import os
import secrets
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtDBus import (
    QDBusConnection, QDBusMessage, QDBusPendingCallWatcher,
    QDBusUnixFileDescriptor, QDBusVariant,
)

PORTAL = "org.freedesktop.portal.Desktop"
DESKTOP = "/org/freedesktop/portal/desktop"
OPEN_INTERFACE = "org.freedesktop.portal.OpenURI"
REQUEST_INTERFACE = "org.freedesktop.portal.Request"
RESPONSE_SLOT = "1response(uint,QVariantMap)"
_PENDING: set["QtPortalRequest"] = set()


class QtPortalRequest(QObject):
    """One nonblocking, finite-duration file-open portal request."""

    def __init__(self, bus: QDBusConnection, path: str,
                 on_result: Callable[[bool, str], None]) -> None:
        super().__init__()
        self._bus = bus
        self._path = path
        self._callback = on_result
        self._subscribed = False
        self._done = False
        self._watcher: QDBusPendingCallWatcher | None = None
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._timed_out)

    def _subscribe(self, path: str) -> bool:
        if not self._bus.connect(
            PORTAL, path, REQUEST_INTERFACE, "Response", self, RESPONSE_SLOT
        ):
            return False
        self._path = path
        self._subscribed = True
        return True

    def start(self, message: QDBusMessage) -> None:
        # Subscribe before sending to avoid dropping a fast portal response.
        if not self._subscribe(self._path):
            raise RuntimeError("Could not subscribe to desktop portal response")
        self._timeout.start(45_000)
        call = self._bus.asyncCall(message, 5000)
        self._watcher = QDBusPendingCallWatcher(call, self)
        self._watcher.finished.connect(self._method_finished)

    def _method_finished(self, watcher: QDBusPendingCallWatcher) -> None:
        if self._done:
            return
        reply = watcher.reply()
        if reply.type() != QDBusMessage.MessageType.ReplyMessage:
            self._finish(False, "Desktop portal rejected the file-open request")
            return
        args = reply.arguments()
        if len(args) != 1:
            self._finish(False, "Unexpected portal request handle")
            return
        returned = args[0]
        path = returned.path() if hasattr(returned, "path") else returned
        if not isinstance(path, str) or not path.startswith(
            "/org/freedesktop/portal/desktop/request/"
        ):
            self._finish(False, "Unexpected portal request handle")
            return
        if path != self._path:
            self._unsubscribe()
            if not self._subscribe(path):
                self._finish(False, "Could not follow desktop portal request")
                return

    @Slot("uint", "QVariantMap")
    def response(self, code: int, details: dict) -> None:
        if self._done:
            return
        if code == 0:
            self._finish(True, "Desktop accepted the file-open request")
        elif code == 1:
            self._finish(False, "File opening canceled")
        else:
            self._finish(False, "Desktop could not open the selected file")

    def _unsubscribe(self) -> None:
        if self._subscribed:
            self._bus.disconnect(
                PORTAL, self._path, REQUEST_INTERFACE, "Response",
                self, RESPONSE_SLOT,
            )
            self._subscribed = False

    def _send_close(self) -> None:
        # Never block the GUI thread waiting for a stalled portal.
        request = QDBusMessage.createMethodCall(
            PORTAL, self._path, REQUEST_INTERFACE, "Close"
        )
        self._bus.send(request)

    def _timed_out(self) -> None:
        if self._done:
            return
        self._send_close()
        self._finish(False, "Desktop file-opening request timed out")

    def cancel(self) -> None:
        """Best-effort close of a pending portal request on window shutdown."""
        if self._done:
            return
        self._send_close()
        self._finish(False, "File opening canceled")

    def _finish(self, ok: bool, message: str) -> None:
        if self._done:
            return
        self._done = True
        self._timeout.stop()
        self._unsubscribe()
        _PENDING.discard(self)
        try:
            self._callback(ok, message)
        finally:
            # Do not destroy an active Qt receiver from inside its own signal.
            self.deleteLater()


def request_open_qt_fd(fd: int, on_result: Callable[[bool, str], None]
                       ) -> QtPortalRequest:
    """Consume fd and start an asynchronous FD-only OpenURI.OpenFile call."""
    if not isinstance(fd, int) or fd < 0:
        raise ValueError("Invalid file descriptor")
    try:
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected() or not bus.baseService():
            raise RuntimeError("Desktop session bus unavailable")
        capabilities = QDBusConnection.ConnectionCapability.UnixFileDescriptorPassing
        if not (bus.connectionCapabilities() & capabilities):
            raise RuntimeError("Desktop bus cannot pass Unix file descriptors")
        owned = QDBusUnixFileDescriptor(fd)
        if not owned.isValid():
            raise RuntimeError("Cannot duplicate authorized file descriptor")
    finally:
        # Qt's QDBusUnixFileDescriptor owns its own dup; the caller's FD is
        # ALWAYS consumed, including missing bus or failed duplication.
        os.close(fd)

    token = "gc_index_" + secrets.token_hex(12)
    unique = bus.baseService().lstrip(":").replace(".", "_")
    path = f"/org/freedesktop/portal/desktop/request/{unique}/{token}"
    message = QDBusMessage.createMethodCall(PORTAL, DESKTOP, OPEN_INTERFACE, "OpenFile")
    message.setArguments([
        "", owned, {
            "handle_token": QDBusVariant(token),
            "writable": QDBusVariant(False),
        },
    ])
    pending = QtPortalRequest(bus, path, on_result)
    _PENDING.add(pending)
    try:
        pending.start(message)
    except BaseException:
        pending._unsubscribe()
        pending._timeout.stop()
        _PENDING.discard(pending)
        pending.deleteLater()
        raise
    return pending


def cancel_pending_qt_portals() -> None:
    """Terminate outstanding requests without calling external applications."""
    for request in tuple(_PENDING):
        request.cancel()
