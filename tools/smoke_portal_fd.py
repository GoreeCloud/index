"""Descriptor-based desktop OpenFile portal integration smoke (private bus only).

Run through: dbus-run-session -- /usr/bin/python3 tools/smoke_portal_fd.py
No actual desktop app or portal is invoked. A minimal fake freedesktop
portal asserts that the received UNIX FD refers to an original indexed file
even after another real file is placed at the same pathname.
"""

from __future__ import annotations

import os
import tempfile
import traceback
from pathlib import Path

if not os.environ.get("GOREECLOUD_INDEX_PORTAL_ISOLATED") == "1":
    raise SystemExit("Refuse fake portal outside explicit private D-Bus test")

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

from goreecloud_index.portal import request_open_fd, PORTAL_NAME, PORTAL_OBJECT
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


def run() -> None:
    mode = os.environ.get("GOREECLOUD_INDEX_FAKE_PORTAL", "0")
    if mode not in {"0", "1", "2", "error"}:
        raise ValueError("Invalid private portal response mode")
    with tempfile.TemporaryDirectory(prefix="gc-index-portal-smoke-") as temp:
        base = Path(temp)
        root = base / "approved"
        root.mkdir()
        item = root / "report.txt"
        item.write_text("original canary", encoding="utf-8")
        old = base / "old-report.txt"
        db = IndexStore(base / "db" / "index.sqlite3")
        indexed = db.add_root(root)
        scan_root(db, indexed)
        expected = item.stat().st_ino

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        name_id = Gio.bus_own_name_on_connection(bus, PORTAL_NAME,
                                                  Gio.BusNameOwnerFlags.NONE, None, None)
        info = Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0]
        state: dict[str, object] = {
            "received_fd": False, "ok": False, "error": None, "completed": False,
        }
        loop = GLib.MainLoop()

        def on_method(_connection, sender, _obj_path, _interface,
                      method, parameters, invocation):
            try:
                assert method == "OpenFile", method
                parent, index, opts = parameters.unpack()
                assert parent == ""
                assert opts["writable"] is False
                token = opts["handle_token"]
                assert token.startswith("gc_index_")
                fds = invocation.get_message().get_unix_fd_list()
                assert fds is not None
                received = fds.get(index)
                try:
                    st = os.fstat(received)
                    assert st.st_ino == expected, (st.st_ino, expected)
                    assert item.stat().st_ino != expected, "Original pathname not replaced"
                    assert old.stat().st_ino == expected
                    state["received_fd"] = True
                finally:
                    os.close(received)
                sender_tag = sender[1:].replace(".", "_")
                handle = f"/org/freedesktop/portal/desktop/request/{sender_tag}/{token}"
                if mode == "error":
                    invocation.return_dbus_error(
                        "org.goreecloud.Index.TestFailure", "Synthetic backend failure"
                    )
                    return
                invocation.return_value(GLib.Variant("(o)", (handle,)))

                def respond():
                    bus.emit_signal(None, handle, "org.freedesktop.portal.Request",
                                    "Response", GLib.Variant("(ua{sv})", (int(mode), {})))
                    return GLib.SOURCE_REMOVE

                GLib.timeout_add(180, respond)
            except Exception:
                state["error"] = traceback.format_exc()
                invocation.return_dbus_error("org.goreecloud.Index.TestFailure",
                                             "Private portal fixture failed")
                loop.quit()

        registration = bus.register_object(PORTAL_OBJECT, info, on_method, None, None)

        def on_result(ok: bool, message: str) -> None:
            state["ok"] = ok
            state["message"] = message
            state["completed"] = True
            loop.quit()

        def start():
            try:
                # Open and authorize the original inode, then swap the path
                # BEFORE the asynchronous desktop portal has received it.
                fd = db.open_authorized_result_fd(item)
                item.rename(old)
                item.write_text("attacker-replacement", encoding="utf-8")
                request_open_fd(fd, on_result)
                try:
                    os.fstat(fd)
                except OSError:
                    pass  # The API consumes the original descriptor.
                else:
                    raise AssertionError("Portal request leaked caller-owned descriptor")
            except Exception:
                state["error"] = traceback.format_exc()
                loop.quit()
            return GLib.SOURCE_REMOVE

        def expire():
            if not state["completed"]:
                state["error"] = state["error"] or "Private fake portal timeout"
                loop.quit()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(200, start)
        GLib.timeout_add(7000, expire)
        try:
            loop.run()
        finally:
            bus.unregister_object(registration)
            Gio.bus_unown_name(name_id)
        if (not state["received_fd"] or not state["completed"]
                or state["ok"] is not (mode == "0") or state["error"]):
            raise AssertionError(f"Isolated portal fd test failed in mode {mode}: {state}")
        assert item.read_text() == "attacker-replacement"
        assert old.read_text() == "original canary"
        print(f"PRIVATE_FD_PORTAL_PASS mode={mode}: original inode transmitted, replacement excluded")


if __name__ == "__main__":
    run()
