#!/usr/bin/env bash
# Repeatable Linux Wayland layout tests on a disposable GitHub-hosted runner.
# Never start a compositor on an owner's desktop or change its display.
set -euo pipefail

if [[ "${GITHUB_ACTIONS:-}" != "true" ||
      "${RUNNER_ENVIRONMENT:-}" != "github-hosted" ||
      "${RUNNER_OS:-}" != "Linux" ||
      ! -d "${RUNNER_TEMP:-/nonexistent}" ]]; then
  echo "Refusing Wayland compositor outside a disposable hosted CI runner" >&2
  exit 2
fi
if [[ "$(id -u)" == "0" ]]; then
  echo "Wayland compositor must run as the unprivileged CI user" >&2
  exit 2
fi
if [[ ! -f /etc/os-release ]] ||
  ! grep -q '^ID=ubuntu$' /etc/os-release ||
  ! grep -q '^VERSION_ID="24.04"$' /etc/os-release; then
  echo "Only the GitHub-hosted Ubuntu 24.04 runner is qualified" >&2
  exit 2
fi

root="$(mktemp -d "$RUNNER_TEMP/gc-index-weston-XXXXXXXX")"
if [[ -z "$root" || "$root" != "$RUNNER_TEMP"/gc-index-weston-* ]]; then
  echo "Unsafe temporary directory; refusing" >&2
  exit 2
fi
trap 'rm -rf -- "$root"' EXIT

mkdir -p "$root/home" "$root/config" "$root/data" "$root/cache" "$root/runtime"
chmod 0700 "$root/runtime" "$root/home"
export HOME="$root/home"
export XDG_CONFIG_HOME="$root/config"
export XDG_DATA_HOME="$root/data"
export XDG_CACHE_HOME="$root/cache"
export XDG_RUNTIME_DIR="$root/runtime"
export GSETTINGS_BACKEND=memory
export GIO_USE_VFS=local
export GTK_USE_PORTAL=0
export GDK_BACKEND=wayland
export GSK_RENDERER=cairo
export PYTHONPATH=src
export GOREECLOUD_INDEX_PRIVATE_WAYLAND=1
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY WAYLAND_SOCKET

# A private bus ensures GTK/Weston cannot connect to the CI runner's
# session or auto-activate unrelated user applications. No real file
# handlers, personal files, portals or input devices are involved.
dbus-run-session -- bash -eu <<'PRIVATE_SESSION'
  set -o pipefail
  socket=gc-index-ci-wl
  weston --no-config --backend=headless-backend.so --renderer=pixman \
    --width=1024 --height=768 --idle-time=0 \
    --socket="$socket" --log="$XDG_RUNTIME_DIR/weston.log" \
    > "$XDG_RUNTIME_DIR/weston.stdout" 2>&1 &
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
    echo "Private headless Weston Wayland socket did not appear" >&2
    tail -60 "$XDG_RUNTIME_DIR/weston.log" >&2 || :
    exit 3
  fi
  export WAYLAND_DISPLAY="$socket"

  /usr/bin/python3 tools/smoke_layout_gtk.py --width 390
  /usr/bin/python3 tools/smoke_layout_gtk.py --width 440
  GTK_A11Y=test G_DEBUG=fatal-warnings /usr/bin/python3 tools/smoke_gtk.py
  GTK_A11Y=test G_DEBUG=fatal-warnings \
    /usr/bin/python3 tools/smoke_text_scale_gtk.py --width 390
  GTK_A11Y=test G_DEBUG=fatal-warnings \
    /usr/bin/python3 tools/smoke_text_scale_gtk.py --width 440
  echo "HOSTED_PRIVATE_WESTON_WAYLAND_PASS"
PRIVATE_SESSION
