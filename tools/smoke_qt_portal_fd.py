"""Qt Quick -> GLib D-Bus -> inode-pinned portal smoke on an isolated bus.

Requires a fresh private session (dbus-run-session), synthetic files and the
GOREECLOUD_INDEX_PORTAL_ISOLATED=1 explicit test guard. It never invokes a
real desktop portal or third-party handler, changes desktop settings, or
touches a live GoreeCloud Index database. Run four modes: 0, 1, 2, error.
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path

if os.environ.get("GOREECLOUD_INDEX_PORTAL_ISOLATED") != "1":
    raise SystemExit("Refuse Qt portal smoke without explicit private-bus test flag")
if not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
    raise SystemExit("Refuse Qt portal smoke without private session bus")

# The opt-in Qt migration venv lacks system gi by default on Ubuntu. Only
# distro-provided gi may be exposed; no PyGObject binary is downloaded.
system_gi = "/usr/lib/python3/dist-packages"
if system_gi not in sys.path:
    sys.path.append(system_gi)

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from goreecloud_index.portal import PORTAL_NAME, PORTAL_OBJECT
from goreecloud_index.qtquick_app import IndexBridge
from goreecloud_index.scanner import scan_root
from goreecloud_index.storage import IndexStore


XML = """
<node>
 <interface name='org.freedesktop.portal.OpenURI'>
  <method name='OpenFile'>
   <arg type='s' direction='in'/>
   <arg type='h' direction='in'/>
   <arg type='a{sv}' direction='in'/>
   <arg type='o' direction='out'/>
  </method>
 </interface>
</node>
"""


def main() -> int:
    mode = os.environ.get("GOREECLOUD_INDEX_FAKE_PORTAL", "0")
    if mode not in {"0", "1", "2", "error"}:
        raise ValueError("Invalid isolated portal mode")

    app = QGuiApplication([])
    with tempfile.TemporaryDirectory(prefix="gc-index-qt-portal-") as temp:
        base = Path(temp)
        root = base / "selected"
        root.mkdir()
        current = root / "report.txt"
        current.write_text("original synthetic canary", encoding="utf-8")
        moved = base / "renamed-original.txt"
        db = IndexStore(base / "private" / "index.sqlite3")
        selected = db.add_root(root)
        scan_root(db, selected)
        expected_inode = current.stat().st_ino

        # Claim the name only on this disposable dbus-run-session bus.
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = bus.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "RequestName",
            GLib.Variant("(su)", (PORTAL_NAME, 0)),
            GLib.VariantType.new("(u)"), Gio.DBusCallFlags.NONE, 2000, None,
        )
        assert reply.unpack()[0] == 1, "Private fake portal name not acquired"
        info = Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0]
        state = {"received_fd": False, "completed": False, "error": None}
        bridge = IndexBridge(db, applications=[])
        bridge.refresh("report", "files")
        assert len(bridge.results) == 1, "Fixture must yield one consented file"

        def on_method(_connection, sender, _path, _interface,
                      method, parameters, invocation) -> None:
            try:
                assert method == "OpenFile"
                parent, index, options = parameters.unpack()
                assert parent == ""
                assert options["writable"] is False
                token = options["handle_token"]
                assert token.startswith("gc_index_")
                fd_list = invocation.get_message().get_unix_fd_list()
                assert fd_list is not None
                received = fd_list.get(index)
                try:
                    assert os.fstat(received).st_ino == expected_inode
                    assert moved.stat().st_ino == expected_inode
                    assert current.stat().st_ino != expected_inode
                    state["received_fd"] = True
                finally:
                    os.close(received)
                if mode == "error":
                    invocation.return_dbus_error(
                        "org.goreecloud.Index.FakePortalRejected",
                        "Synthetic, isolated D-Bus backend rejection",
                    )
                    return
                handle = (
                    "/org/freedesktop/portal/desktop/request/"
                    + sender[1:].replace(".", "_") + "/" + token
                )
                invocation.return_value(GLib.Variant("(o)", (handle,)))

                def respond():
                    bus.emit_signal(
                        None, handle, "org.freedesktop.portal.Request",
                        "Response", GLib.Variant("(ua{sv})", (int(mode), {})),
                    )
                    return GLib.SOURCE_REMOVE

                GLib.timeout_add(120, respond)
            except Exception:
                state["error"] = traceback.format_exc()
                invocation.return_dbus_error(
                    "org.goreecloud.Index.FakePortalFailed",
                    "Synthetic D-Bus fixture validation failure",
                )

        registration = bus.register_object(PORTAL_OBJECT, info, on_method, None, None)

        def start():
            try:
                bridge.activate(0)
                assert bridge._portal_running, bridge.status
                # Rename and substitute AFTER the FD was authorized, before
                # the Qt-timer-driven GLib portal method is dispatched.
                current.rename(moved)
                current.write_text("new synthetic replacement", encoding="utf-8")
                assert moved.stat().st_ino == expected_inode
            except Exception:
                state["error"] = traceback.format_exc()
                app.quit()

        def inspect():
            if not bridge._portal_running and state["received_fd"]:
                state["completed"] = True
                app.quit()

        def expire():
            if not state["completed"]:
                state["error"] = state["error"] or (
                    "Qt/GLib portal response integration did not complete"
                )
            app.quit()

        poller = QTimer()
        poller.timeout.connect(inspect)
        poller.start(20)
        QTimer.singleShot(0, start)
        QTimer.singleShot(5000, expire)
        try:
            app.exec()
        finally:
            poller.stop()
            bridge._portal_pump.stop()
            bus.unregister_object(registration)
            bus.call_sync(
                "org.freedesktop.DBus", "/org/freedesktop/DBus",
                "org.freedesktop.DBus", "ReleaseName",
                GLib.Variant("(s)", (PORTAL_NAME,)),
                GLib.VariantType.new("(u)"), Gio.DBusCallFlags.NONE, 2000, None,
            )
        expected_text = {
            "0": "Desktop accepted the file-open request",
            "1": "File opening canceled",
            "2": "Desktop could not open the selected file",
            "error": "Desktop portal unavailable or rejected request",
        }[mode]
        assert state["error"] is None, state["error"]
        assert state["completed"] and state["received_fd"], state
        assert expected_text in bridge.status, bridge.status
        assert not bridge._portal_running
        assert not bridge._portal_pump.isActive()
        assert current.read_text(encoding="utf-8") == "new synthetic replacement"
        assert moved.read_text(encoding="utf-8") == "original synthetic canary"
        print(
            f"PRIVATE_QT_PORTAL_PASS mode={mode}: original FD identity, "
            "Qt/GLib response, no path fallback"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
