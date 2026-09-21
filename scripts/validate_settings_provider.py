from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

provider_path = ROOT / "app/src/main/java/com/goreecloud/index/provider/settings/SystemSettingsProvider.kt"
test_path = ROOT / "app/src/test/java/com/goreecloud/index/provider/settings/SystemSettingsProviderTest.kt"
core_path = ROOT / "app/src/main/java/com/goreecloud/index/core/IndexContract.kt"
source_controls_path = ROOT / "app/src/main/java/com/goreecloud/index/core/IndexSourceControls.kt"
main_path = ROOT / "app/src/main/java/com/goreecloud/index/MainActivity.kt"
manifest_path = ROOT / "app/src/main/AndroidManifest.xml"

for path in [provider_path, test_path, core_path, source_controls_path, main_path, manifest_path]:
    if not path.is_file():
        raise SystemExit(f"Missing Settings provider contract file: {path.relative_to(ROOT)}")

provider = provider_path.read_text(encoding="utf-8")
core = core_path.read_text(encoding="utf-8")
source_controls = source_controls_path.read_text(encoding="utf-8")
main = main_path.read_text(encoding="utf-8")
manifest = manifest_path.read_text(encoding="utf-8")
tests = test_path.read_text(encoding="utf-8")

for expected in [
    'const val PROVIDER_SETTINGS = "goreecloud.index.provider.settings"',
    "data class OpenSystemSetting(",
]:
    if expected not in core:
        raise SystemExit(f"Missing typed Settings provider/action contract: {expected}")

for expected in [
    "class SystemSettingsProvider : IndexProvider",
    "GoreeCloudIndexContract.PROVIDER_SETTINGS",
    'displayName: String = "Settings · On-device"',
    "IndexProcessingLocation.LOCAL",
    "timeoutMillis: Long = 250L",
    "supportsEmptyQuery: Boolean = false",
    "if (query.text.isBlank()) return emptyList()",
    "IndexResultType.SETTING",
    "IndexAction.OpenSystemSetting(destination.action)",
    "IndexTextMatcher.score(",
    "fun isAllowedAction(action: String): Boolean = action in ALLOWED_ACTIONS",
]:
    if expected not in provider:
        raise SystemExit(f"Missing bounded Settings provider behavior: {expected}")

required_actions = {
    "android.settings.SETTINGS",
    "android.settings.WIFI_SETTINGS",
    "android.settings.BLUETOOTH_SETTINGS",
    "android.settings.DISPLAY_SETTINGS",
    "android.settings.SOUND_SETTINGS",
    "android.settings.ACCESSIBILITY_SETTINGS",
    "android.settings.LOCATION_SOURCE_SETTINGS",
    "android.settings.SECURITY_SETTINGS",
    "android.settings.MANAGE_APPLICATIONS_SETTINGS",
    "android.settings.BATTERY_SAVER_SETTINGS",
}
for action in required_actions:
    if provider.count(f'"{action}"') != 1:
        raise SystemExit(f"Settings action must appear exactly once in static provider catalog: {action}")
if provider.count("SystemSettingDestination(") != 11:  # data class declaration + 10 catalog entries
    raise SystemExit("Settings provider must remain the reviewed ten-destination static catalog")

for prohibited in [
    "ContentResolver",
    "ContentObserver",
    "Settings.Secure",
    "Settings.System",
    "Settings.Global",
    "getString(",
    "getInt(",
    "getLong(",
    "query(",
    "java.net",
    "okhttp",
    "http://",
    "https://",
    "android.permission",
]:
    if prohibited in provider:
        raise SystemExit(f"Settings provider exceeded static navigation-only boundary: {prohibited}")

for expected in [
    "IndexDevelopmentSourcePolicy",
    "GoreeCloudIndexContract.PROVIDER_SETTINGS",
    "selectableProviderIds",
    "localOnly = true",
]:
    if expected not in source_controls:
        raise SystemExit(f"Central source policy missing Settings eligibility boundary: {expected}")

for expected in [
    "SystemSettingsProvider",
    "IndexDevelopmentSourcePolicy.selectableProviderIds",
    "IndexDevelopmentSourcePolicy.executionContext(",
    "IndexAction.OpenSystemSetting",
    "SystemSettingsProvider.isAllowedAction(action.action)",
    "startActivity(Intent(action.action))",
    '"Unable to open this setting."',
]:
    if expected not in main:
        raise SystemExit(f"MainActivity missing Settings handoff boundary: {expected}")

# INTERNET is now an application-level prerequisite for the separately bounded
# GoreeCloud Search HTTPS candidate. The Settings provider itself remains local,
# static, and network-free through the provider-source prohibitions above.
if "android.permission.QUERY_ALL_PACKAGES" in manifest:
    raise SystemExit("Local Settings provider must not add unrestricted package visibility")

for expected in [
    "providerIsLocalNonBrowsingAndPermissionFree",
    "blankQueryReturnsNoSettingsEnumeration",
    "wifiQueryReturnsTypedWhitelistedDestination",
    "keywordSearchCanFindDestinationWithoutReadingSettingValues",
    "unknownQueryReturnsNoResults",
    "destinationCatalogUsesUniqueIdsAndWhitelistedActions",
    "maxResultsRemainsBoundedByQuery",
    'SystemSettingsProvider.isAllowedAction("android.intent.action.VIEW")',
    'SystemSettingsProvider.isAllowedAction("https://example.com")',
]:
    if expected not in tests:
        raise SystemExit(f"Missing Settings provider regression coverage: {expected}")

print("GoreeCloud Index bounded local Settings provider validation passed")
