#!/usr/bin/env bash
# Qt PREVIEW Debian lifecycle, only on disposable GitHub-hosted Ubuntu 24.04.
# System packages are NEVER touched on a user's laptop or VPS.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_ENVIRONMENT:-}" != github-hosted ||
      "${RUNNER_OS:-}" != Linux || -z "${RUNNER_TEMP:-}" ||
      ! -d "${RUNNER_TEMP}" || "$(id -u)" == 0 ]]; then
  echo "Refusing Qt APT lifecycle outside unprivileged hosted CI" >&2
  exit 2
fi
if [[ ! -f /etc/os-release ]] ||
   ! grep -qx 'ID=ubuntu' /etc/os-release ||
   ! grep -qx 'VERSION_ID="24.04"' /etc/os-release; then
  echo "Qt APT lifecycle requires hosted Ubuntu 24.04" >&2
  exit 2
fi
if [[ "${QT_QPA_PLATFORM:-}" != offscreen ||
      "${QT_QUICK_BACKEND:-}" != software ||
      "${GOREECLOUD_INDEX_QT_LIFECYCLE_ISOLATED:-}" != 1 ]]; then
  echo "Refusing Qt APT lifecycle without isolated software QPA" >&2
  exit 2
fi
readonly package1="$PWD/dist/goreecloud-index_0.1.0-1_all.deb"
readonly package2="$PWD/dist/goreecloud-index_0.1.0-2_all.deb"
for package in "$package1" "$package2"; do
  [[ -f "$package" && ! -L "$package" ]] || {
    echo "Missing verified local Debian candidate: $package" >&2; exit 2;
  }
  [[ "$(dpkg-deb -f "$package" Package)" == goreecloud-index ]] || exit 2
  [[ "$(dpkg-deb -f "$package" Architecture)" == all ]] || exit 2
done

# This test owns only an ephemeral synthetic sentinel; it is not the Index
# database and cannot be confused with the user's ~/.local/share contents.
root="$(mktemp -d "$RUNNER_TEMP/gc-index-qt-apt-XXXXXXXX")"
[[ "$root" == "$RUNNER_TEMP"/gc-index-qt-apt-* ]] || exit 2
trap 'rm -rf -- "$root"' EXIT
export XDG_DATA_HOME="$root/private-data"
export XDG_CONFIG_HOME="$root/private-config"
mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME"
chmod 0700 "$XDG_DATA_HOME" "$XDG_CONFIG_HOME"
private_marker="$XDG_DATA_HOME/synthetic-consent-keep.txt"
printf 'GoreeCloud Index synthetic private data: do not purge\n' > "$private_marker"
chmod 0600 "$private_marker"
expected="$(sha256sum "$private_marker" | cut -d' ' -f1)"
verify_data() {
  [[ -f "$private_marker" && ! -L "$private_marker" ]] || {
    echo "A package step removed synthetic user data" >&2; exit 4;
  }
  [[ "$(sha256sum "$private_marker" | cut -d' ' -f1)" == "$expected" ]] || {
    echo "A package step altered synthetic user data" >&2; exit 4;
  }
  [[ "$(stat -c '%a' "$private_marker")" == 600 ]] || {
    echo "A package step changed private data permissions" >&2; exit 4;
  }
}
verify_install() {
  local version="$1"
  [[ "$(dpkg-query -W -f='${Version}' goreecloud-index)" == "$version" ]] || exit 4
  [[ "$(dpkg-query -W -f='${Status}' goreecloud-index)" == "install ok installed" ]] || exit 4
  [[ -f /usr/bin/goreecloud-index && -f /usr/lib/python3/dist-packages/goreecloud_index/qtquick/Main.qml ]] || exit 4
  # The hash-pinned Qt interpreter is supplied separately by CI; the
  # development .deb is NOT falsely presented as a Qt runtime installer.
  GOREECLOUD_INDEX_INSTALLED_QT_ISOLATED=1 python tools/smoke_installed_qt.py
  verify_data
}
verify_removed() {
  [[ ! -e /usr/bin/goreecloud-index ]] || exit 4
  [[ ! -e /usr/share/applications/com.goreecloud.Index.desktop ]] || exit 4
  [[ ! -f /usr/lib/python3/dist-packages/goreecloud_index/qtquick/Main.qml ]] || exit 4
  verify_data
}

# All apt operations below affect this GitHub-hosted disposable runner ONLY.
sudo apt-get install -y --no-install-recommends "$package1"
verify_install 0.1.0-1
echo "QT_CANDIDATE_INSTALL_PASS"

sudo apt-get install -y --no-install-recommends "$package2"
verify_install 0.1.0-2
echo "QT_CANDIDATE_UPGRADE_PASS"

sudo apt-get install -y --allow-downgrades --no-install-recommends "$package1"
verify_install 0.1.0-1
echo "QT_CANDIDATE_ROLLBACK_PASS"

sudo apt-get remove -y goreecloud-index
verify_removed
echo "QT_CANDIDATE_REMOVE_PASS"

sudo apt-get install -y --no-install-recommends "$package1"
verify_install 0.1.0-1
echo "QT_CANDIDATE_REINSTALL_PASS"

sudo apt-get purge -y goreecloud-index
verify_removed
echo "QT_CANDIDATE_PURGE_PRESERVES_DATA_PASS"

# This is a preview and does not qualify Qt runtime license compliance,
# signed release, Qt-primary desktop launcher, or real third-party handlers.
echo "HOSTED_QT_APT_PREVIEW_LIFECYCLE_PASS"
