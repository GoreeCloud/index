#!/usr/bin/env bash
# Only run on a disposable GitHub-hosted Ubuntu runner. Never on a user's host.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" || "${RUNNER_OS:-}" != "Linux" ||
      "${RUNNER_ENVIRONMENT:-}" != "github-hosted" ]]; then
  echo "Refusing apt installation outside a GitHub-hosted disposable Linux runner" >&2
  exit 2
fi
if [[ "$(id -u)" == "0" ]]; then
  echo "Run as the unprivileged runner user; sudo only for apt lifecycle" >&2
  exit 2
fi
if [[ -z "${RUNNER_TEMP:-}" || ! -d "$RUNNER_TEMP" ]]; then
  echo "Missing a valid ephemeral runner temp directory" >&2
  exit 2
fi
if [[ ! -f /etc/os-release ]] || ! grep -q '^VERSION_ID="24.04"$' /etc/os-release ||
   ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo "Only Ubuntu 24.04 is qualified for this CI job" >&2
  exit 2
fi

readonly v1="dist/goreecloud-index_0.1.0-1_all.deb"
readonly v2="dist/goreecloud-index_0.1.0-2_all.deb"
for pkg in "$v1" "$v2"; do
  [[ -f "$pkg" && ! -L "$pkg" ]] || { echo "Missing staged package: $pkg" >&2; exit 2; }
  [[ "$(dpkg-deb -f "$pkg" Package)" == "goreecloud-index" ]] || exit 2
  [[ "$(dpkg-deb -f "$pkg" Architecture)" == "all" ]] || exit 2
done

echo "Installing from Ubuntu signed repositories and local first-party .deb"
sudo apt-get update -qq
sudo apt-get install --yes --no-install-recommends xvfb
sudo apt-get install --yes --no-install-recommends "./$v1"
dpkg-query -W -f='${db:Status-Abbrev} ${Version}\n' goreecloud-index
for dep in python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 xdg-desktop-portal; do
  dpkg-query -W -f='${Status}\n' "$dep" | grep -Fxq 'install ok installed'
done
goreecloud-index calc "12% of 75" | grep -Fxq '9'
echo "dependency-checked install: PASS"

# Import the installed module, not source from the checkout. Xvfb provides
# only headless GTK lifecycle checks (not human visual or AT certification).
export XDG_DATA_HOME="$RUNNER_TEMP/gc-index-installed-data"
mkdir -p "$XDG_DATA_HOME"
xvfb-run -a /usr/bin/python3 - <<'PY'
from gi.repository import GLib
from goreecloud_index.ui import IndexApplication
app = IndexApplication()
seen = []
def smoke():
    assert app.window is not None
    assert app.search_entry is not None
    seen.append(True)
    app.quit()
    return GLib.SOURCE_REMOVE
GLib.timeout_add(250, smoke)
GLib.timeout_add(3500, app.quit)
assert app.run([]) == 0
assert seen, "GTK activation never reached ready state"
print("installed GTK4/libadwaita smoke: PASS")
PY

sudo apt-get install --yes --no-install-recommends "./$v2"
[[ "$(dpkg-query -W -f='${Version}' goreecloud-index)" == "0.1.0-2" ]]
goreecloud-index calc "5 km in m" | grep -Fxq '5000 m'
echo "dependency-checked upgrade: PASS"

sudo apt-get install --yes --allow-downgrades --no-install-recommends "./$v1"
[[ "$(dpkg-query -W -f='${Version}' goreecloud-index)" == "0.1.0-1" ]]
goreecloud-index calc "12% of 75" | grep -Fxq '9'
echo "dependency-checked rollback: PASS"

sudo apt-get purge --yes goreecloud-index
[[ ! -e /usr/bin/goreecloud-index ]]
[[ ! -e /usr/share/applications/com.goreecloud.Index.desktop ]]
[[ ! -e /usr/lib/python3/dist-packages/goreecloud_index/cli.py ]]
if [[ -d /usr/lib/python3/dist-packages/goreecloud_index ]]; then
  echo "WARNING: residual package Python directory after purge" >&2
  find /usr/lib/python3/dist-packages/goreecloud_index -maxdepth 2 -type f -printf '%P\n' >&2
  exit 1
fi
echo "dependency-checked purge and payload cleanup: PASS"
echo "HOSTED_RUNNER_DEBIAN_LIFECYCLE_PASS"
