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
trap 'rm -rf -- "$root"' EXIT
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

# A private bus plus private socket avoid the live user session. Never
# launch real apps, portals, or use a stored personal Index database.
dbus-run-session -- bash -euo pipefail <<'PRIVATE_QT_WESTON'
  socket=gc-index-qt-ci-wl
  weston --no-config --backend=headless-backend.so --renderer=pixman \
    --width=640 --height=360 --idle-time=0 \
    --socket="$socket" --log="$XDG_RUNTIME_DIR/weston.log" \
    >"$XDG_RUNTIME_DIR/weston.stdout" 2>&1 &
  compositor=$!
  shutdown() {
    kill "$compositor" 2>/dev/null || :
    wait "$compositor" 2>/dev/null || :
  }
  trap shutdown EXIT
  for i in $(seq 1 50); do
    if [[ -S "$XDG_RUNTIME_DIR/$socket" ]]; then break; fi
    if ! kill -0 "$compositor" 2>/dev/null; then break; fi
    sleep 0.2
  done
  if [[ ! -S "$XDG_RUNTIME_DIR/$socket" ]]; then
    echo "Private Qt Weston socket did not appear" >&2
    tail -60 "$XDG_RUNTIME_DIR/weston.log" >&2 || :
    exit 3
  fi
  export WAYLAND_DISPLAY="$socket"
  python tools/smoke_qt_weston.py
PRIVATE_QT_WESTON
