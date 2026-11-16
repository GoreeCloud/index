#!/usr/bin/env bash
# Strictly hosted-runner-only Qt Wayland compositor lifecycle/compact UI.
# Never run Weston on the founder's laptop, current desktop, VPS or workstation.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" ||
      "${RUNNER_ENVIRONMENT:-}" != "github-hosted" ||
      "${RUNNER_OS:-}" != "Linux" ||
      -z "${RUNNER_TEMP:-}" || ! -d "${RUNNER_TEMP}" ]]; then
  echo "Refusing Qt Weston outside disposable hosted CI" >&2
  exit 2
fi
if [[ "$(id -u)" == 0 ||
      ! -f /etc/os-release ]] ||
      ! grep -q '^ID=ubuntu$' /etc/os-release ||
      ! grep -q '^VERSION_ID="24.04"$' /etc/os-release; then
  echo "Qt Weston requires unprivileged GitHub Ubuntu 24.04" >&2
  exit 2
fi
root="$(mktemp -d "$RUNNER_TEMP/gc-index-qt-weston-XXXXXXXX")"
if [[ -z "$root" || "$root" != "$RUNNER_TEMP"/gc-index-qt-weston-* ]]; then
  echo "Unsafe hosted temporary directory" >&2
  exit 2
fi
cleanup() {
  result=$?
  trap - EXIT
  # If a desktop portal somehow mounted its FUSE document directory, NEVER
  # traverse that mount with rm -rf. Fail this ephemeral job and let the
  # GitHub-hosted VM be destroyed by the runner.
  if [[ -e "$root/runtime/doc" || -L "$root/runtime/doc" ]]; then
    echo "Unexpected document portal path: refusing unsafe cleanup" >&2
    exit 4
  fi
  rm -rf -- "$root"
  exit "$result"
}
trap cleanup EXIT
mkdir -p "$root"/{home,config,data,cache,runtime}
chmod 0700 "$root/home" "$root/runtime"
export HOME="$root/home"
export XDG_CONFIG_HOME="$root/config"
export XDG_DATA_HOME="$root/data"
export XDG_CACHE_HOME="$root/cache"
export XDG_RUNTIME_DIR="$root/runtime"
export XDG_CURRENT_DESKTOP=none
export QT_QPA_PLATFORMTHEME=generic
export GSETTINGS_BACKEND=memory
export GIO_USE_VFS=local
export QT_QPA_PLATFORM=wayland
export QT_QUICK_BACKEND=software
export GOREECLOUD_INDEX_PRIVATE_QT_WESTON=1
export PYTHONPATH=src
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY WAYLAND_SOCKET

# Explicitly NO standard D-Bus activation directories. The default
# dbus-run-session config can auto-start xdg-desktop-portal, which mounts
# runtime/doc and leaks a document FUSE mount into our temporary root.
bus_config="$(python tools/qt_private_bus.py "$root")"
dbus-run-session --config-file="$bus_config" -- bash -euo pipefail <<'PRIVATE_QT_WESTON'
  activatable="$(dbus-send --session --print-reply     --dest=org.freedesktop.DBus /org/freedesktop/DBus     org.freedesktop.DBus.ListActivatableNames)"
  if grep -q 'org.freedesktop.portal.' <<<"$activatable"; then
    echo "Private Qt bus unexpectedly permits desktop portal activation" >&2
    exit 4
  fi
  echo "QT_PRIVATE_NO_PORTAL_ACTIVATION_PASS"
  socket=gc-index-qt-ci-wl
  compositor=""
  shutdown() {
    if [[ -n "$compositor" ]]; then
      kill "$compositor" 2>/dev/null || :
      wait "$compositor" 2>/dev/null || :
      compositor=""
    fi
  }
  trap shutdown EXIT
  # Test two *distinct* Wayland screen scales under this one private bus.
  # 3840x2160 physical at Qt 400% maps to 960x540 logical; Qt's preferred
  # floating window fits, unlike scaling up a tiny 640x360 pixel display.
  for case in compact hidpi4; do
    if [[ "$case" == compact ]]; then
      physical_width=640
      physical_height=360
      unset QT_SCALE_FACTOR
    else
      physical_width=3840
      physical_height=2160
      export QT_SCALE_FACTOR=4
    fi
    export GOREECLOUD_INDEX_QT_WESTON_CASE="$case"
    weston --no-config --backend=headless-backend.so --renderer=pixman \
      --width="$physical_width" --height="$physical_height" --idle-time=0 \
      --socket="$socket" --log="$XDG_RUNTIME_DIR/weston-$case.log" \
      >"$XDG_RUNTIME_DIR/weston-$case.stdout" 2>&1 &
    compositor=$!
    for i in $(seq 1 50); do
      if [[ -S "$XDG_RUNTIME_DIR/$socket" ]]; then break; fi
      if ! kill -0 "$compositor" 2>/dev/null; then break; fi
      sleep 0.2
    done
    if [[ ! -S "$XDG_RUNTIME_DIR/$socket" ]]; then
      echo "Private Qt Weston socket did not appear for $case" >&2
      tail -60 "$XDG_RUNTIME_DIR/weston-$case.log" >&2 || :
      exit 3
    fi
    export WAYLAND_DISPLAY="$socket"
    python tools/smoke_qt_weston.py
    shutdown
    # The compositor must remove its socket before starting another one.
    if [[ -S "$XDG_RUNTIME_DIR/$socket" ]]; then
      echo "Weston leaked the prior Wayland socket" >&2
      exit 4
    fi
  done
PRIVATE_QT_WESTON
