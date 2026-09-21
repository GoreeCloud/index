import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    "README.md", "SPECIFICATIONS.md", "FEATURES.md", "BENEFITS.md",
    "COMPETITIVE-OBJECTIVES.md", "CAPABILITIES.md", "ARCHITECTURE.md",
    "CONFORMANCE.md", "USER-MANUAL.md", "FEATURE-ROADMAP.md",
    "PRIVACY POLICY.md", "NOTES.md", "SECURITY.md", ".editorconfig",
    "goreecloud.platform.yaml", "app/build.gradle.kts",
    "app/src/main/AndroidManifest.xml",
    "app/src/main/java/com/goreecloud/index/MainActivity.kt",
    "app/src/main/java/com/goreecloud/index/core/IndexAuthority.kt",
    "app/src/main/java/com/goreecloud/index/core/IndexContract.kt",
    "app/src/main/java/com/goreecloud/index/core/IndexSourceControls.kt",
    "app/src/main/java/com/goreecloud/index/core/PlatformAuthorityAdapters.kt",
    "app/src/main/java/com/goreecloud/index/provider/apps/InstalledAppsProvider.kt",
    "app/src/main/java/com/goreecloud/index/provider/contacts/ContactsProvider.kt",
    "app/src/main/java/com/goreecloud/index/ui/IndexRoot.kt",
    "app/src/main/java/com/goreecloud/index/ui/theme/GlazeV16Contract.kt",
    "app/src/test/java/com/goreecloud/index/core/IndexQueryEngineTest.kt",
    "app/src/test/java/com/goreecloud/index/core/IndexIncrementalSearchTest.kt",
    "app/src/test/java/com/goreecloud/index/core/IndexSourceControlsTest.kt",
    "app/src/test/java/com/goreecloud/index/ui/theme/GlazeV16ContractTest.kt",
    "app/src/test/java/com/goreecloud/index/core/PlatformAuthorityAdaptersTest.kt",
    "goreecloud/privacy-shield.application-manifest.json",
    "goreecloud/privacy-shield.adapter.json",
    "goreecloud/PRIVACY-SHIELD.md",
]
missing = [path for path in required if not (ROOT / path).is_file()]
if missing:
    raise SystemExit(f"Missing required repository files: {', '.join(missing)}")

privacy_manifest = json.loads(
    (ROOT / "goreecloud/privacy-shield.application-manifest.json").read_text(encoding="utf-8")
)
if privacy_manifest.get("manifest_version") != 1:
    raise SystemExit("Privacy Shield application manifest must remain on contract version 1")
if privacy_manifest.get("application_id") != "com.goreecloud.index":
    raise SystemExit("Privacy Shield application manifest must bind to com.goreecloud.index")
if privacy_manifest.get("purposes") != [
    {
        "id": "universal-search",
        "description": "Return authorized local resources that match an explicit user search query.",
    }
]:
    raise SystemExit("Privacy Shield application purpose drifted from the reviewed universal-search scope")
manifest_resources = privacy_manifest.get("resources")
if not isinstance(manifest_resources, list) or len(manifest_resources) != 2:
    raise SystemExit("Current Privacy Shield application manifest must declare exactly Applications and Contacts")
resources_by_id = {resource.get("resource"): resource for resource in manifest_resources}
if set(resources_by_id) != {"android.launcher-applications", "android.contacts"}:
    raise SystemExit("Privacy Shield application manifest contains undeclared current resource scope")
for resource_id, resource in resources_by_id.items():
    if resource.get("purposes") != ["universal-search"]:
        raise SystemExit(f"{resource_id} must remain bound to universal-search only")
    if resource.get("operations") != ["search"]:
        raise SystemExit(f"{resource_id} must remain search-only in the current privacy manifest")
    if resource.get("processing_zones") != ["local"]:
        raise SystemExit(f"{resource_id} must remain local-only in the current privacy manifest")
    if resource.get("destinations") != ["goreecloud-index-ui"]:
        raise SystemExit(f"{resource_id} must not gain an undeclared destination")
    if resource.get("retention") != {"mode": "none"}:
        raise SystemExit(f"{resource_id} must remain no-retention in the current privacy manifest")
    if resource.get("ai_usage") is not False:
        raise SystemExit(f"{resource_id} must not gain AI usage without a reviewed privacy change")
    if resource.get("external_processors") != []:
        raise SystemExit(f"{resource_id} must not gain an external processor without a reviewed privacy change")

privacy_adapter = json.loads(
    (ROOT / "goreecloud/privacy-shield.adapter.json").read_text(encoding="utf-8")
)
expected_adapter = {
    "schema_version": 1,
    "adapter": {
        "id": "index-privacy",
        "product": "GoreeCloud Index",
        "runtime_authority": "GoreeCloud/index",
        "contract_version": 1,
    },
    "capabilities": ["data-minimization"],
    "privacy": {
        "local_first": True,
        "raw_private_activity_exported_for_status": False,
        "remote_tracker_learning": False,
        "remote_tracker_telemetry": False,
    },
    "acceptance": {
        "runtime_acceptance_required": True,
        "production_approved": False,
    },
}
if privacy_adapter != expected_adapter:
    raise SystemExit("Downstream Privacy Shield adapter candidate drifted from the reviewed fail-closed declaration")

privacy_boundary = (ROOT / "goreecloud/PRIVACY-SHIELD.md").read_text(encoding="utf-8")
for expected in [
    "downstream Development declarations",
    "do not establish a centrally accepted Privacy Shield adapter",
    "data-minimization",
    "runtime_acceptance_required: true",
    "production_approved: false",
    "UnavailableIndexPlatformAuthorityGateway",
    "Contacts remains non-dispatchable",
]:
    if expected not in privacy_boundary:
        raise SystemExit(f"Privacy Shield downstream boundary documentation missing: {expected}")

manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
if "android.permission.INTERNET" in manifest:
    raise SystemExit("Current local provider slice must not request INTERNET")
if "android.permission.QUERY_ALL_PACKAGES" in manifest:
    raise SystemExit("Applications provider must not request QUERY_ALL_PACKAGES")
for expected in [
    "android.permission.READ_CONTACTS",
    "android.intent.action.MAIN",
    "android.intent.category.LAUNCHER",
    "com.goreecloud.index.action.SEARCH",
]:
    if expected not in manifest:
        raise SystemExit(f"Missing Android contract: {expected}")

build = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8")
for expected in [
    'applicationId = "com.goreecloud.index"', 'applicationIdSuffix = ".dev"',
    'compileSdk = 37', 'targetSdk = 36', 'minSdk = 26', 'versionCode = 3',
    'versionName = "0.3.0-dev"', 'kotlinx-coroutines-android:1.11.0',
    'kotlinx-coroutines-test:1.11.0',
]:
    if expected not in build:
        raise SystemExit(f"Missing Android/runtime build contract: {expected}")

authority = (ROOT / "app/src/main/java/com/goreecloud/index/core/IndexAuthority.kt").read_text(encoding="utf-8")
for expected in [
    "ANDROID_RUNTIME_PERMISSION", "PRIVACY_SHIELD", "GOREECLOUD_IDENTITY",
    "ALLOW_WITH_CONSTRAINTS", "REQUIRE_USER_DECISION", "UNAVAILABLE",
    "outcome == IndexAuthorityOutcome.ALLOW", "!reference.isNullOrBlank()",
    "satisfiesAll",
]:
    if expected not in authority:
        raise SystemExit(f"Missing fail-closed authority contract: {expected}")

platform_authority = (
    ROOT / "app/src/main/java/com/goreecloud/index/core/PlatformAuthorityAdapters.kt"
).read_text(encoding="utf-8")
for expected in [
    "PrivacyShieldDecisionOutcome", "ALLOW_WITH_CONSTRAINTS", "REQUIRE_USER_DECISION",
    "decision.requestId != expectedRequestId", "decision.expiresAt?.isAfter(now) == false",
    'IDENTITY_EVIDENCE_CONTRACT = "goreecloud.identity-evidence.v1"',
    'AUTHORIZATION_ASSERTION = "authorization-decision"',
    "containsReusableCredentials", "containsRawProfileAttributes",
    "IdentityAuthorizationOutcomeInterpreter", "?: return IndexAuthorityEvidence.unavailable()",
    "IndexPlatformAuthoritySnapshot", "IndexPlatformAuthorityGateway",
    "UnavailableIndexPlatformAuthorityGateway", "ContactsAuthorityProjection",
]:
    if expected not in platform_authority:
        raise SystemExit(f"Missing platform authority adapter boundary: {expected}")

core = (ROOT / "app/src/main/java/com/goreecloud/index/core/IndexContract.kt").read_text(encoding="utf-8")
for expected in [
    "PROVIDER_CONTACTS", "IndexProcessingLocation", "IndexProviderIssueKind",
    "IndexProviderIssueKind.AUTHORIZATION_REQUIRED", "IndexExecutionContext",
    "providerAuthorities", "authorityRequirements", "supportsEmptyQuery",
    "authorizationIssue", "allowedProviderIds", "localOnly", "processingLocation",
    "timeoutMillis", "suspend fun search", "fun searchIncrementally(",
    "Flow<IndexSearchSnapshot>", "supervisorScope", "launch(providerDispatcher)",
    "Channel<Pair<Int, IndexProviderOutcome>>", "composeSnapshot(", ".last()",
    "withTimeout", "catch (_: TimeoutCancellationException)",
    "catch (cancellation: CancellationException)", "throw cancellation",
    "IndexProviderIssueKind.TIMED_OUT", "IndexProviderIssueKind.FAILED",
    "sortedWith(ranking)", ".distinctBy { result ->",
]:
    if expected not in core:
        raise SystemExit(f"Missing query/provider authority contract: {expected}")
if core.index("sortedWith(ranking)") > core.index(".distinctBy { result ->"):
    raise SystemExit("Ranking must occur before provider-scoped deduplication")
if core.index("catch (_: TimeoutCancellationException)") > core.index("catch (cancellation: CancellationException)"):
    raise SystemExit("Timeout handling must occur before general cancellation propagation")

source_controls = (
    ROOT / "app/src/main/java/com/goreecloud/index/core/IndexSourceControls.kt"
).read_text(encoding="utf-8")
for expected in [
    "IndexDevelopmentSourcePolicy", "selectableProviderIds", "sanitizeEnabledProviderIds",
    "PROVIDER_APPS", "PROVIDER_SETTINGS", "PROVIDER_CONTACTS", "intersect(selectableProviderIds)",
    "localOnly = true", "IndexExecutionContext(", "providerAuthorities = providerAuthorities",
    "IndexSourceAuthorityStatus", "IndexSourceAuthorityProjection", "missingRequirements",
    "filterNot(authority::satisfies)", "IndexPermissionReviewPolicy",
    "canRequestAndroidContactsPermission", "ANDROID_RUNTIME_PERMISSION",
]:
    if expected not in source_controls:
        raise SystemExit(f"Missing fail-closed source-control/authority-presentation policy: {expected}")
if "PROVIDER_SEARCH" in source_controls:
    raise SystemExit("Development source controls must not make remote Search user-enableable")

apps = (ROOT / "app/src/main/java/com/goreecloud/index/provider/apps/InstalledAppsProvider.kt").read_text(encoding="utf-8")
for expected in [
    'displayName: String = "Applications"', "IndexProcessingLocation.LOCAL",
    "timeoutMillis: Long = 500L", "override suspend fun search",
    "PackageManager.ResolveInfoFlags.of(0L)", "Intent.ACTION_MAIN",
    "Intent.CATEGORY_LAUNCHER", "flattenToString()",
]:
    if expected not in apps:
        raise SystemExit(f"Missing Applications provider boundary: {expected}")

contacts = (ROOT / "app/src/main/java/com/goreecloud/index/provider/contacts/ContactsProvider.kt").read_text(encoding="utf-8")
for expected in [
    'displayName: String = "Contacts"', "IndexProcessingLocation.LOCAL",
    "timeoutMillis: Long = 750L", "supportsEmptyQuery: Boolean = false",
    "ANDROID_RUNTIME_PERMISSION", "PRIVACY_SHIELD", "GOREECLOUD_IDENTITY",
    "ContactsContract.Contacts.CONTENT_FILTER_URI", "ContactsContract.Contacts._ID",
    "ContactsContract.Contacts.LOOKUP_KEY", "ContactsContract.Contacts.DISPLAY_NAME_PRIMARY",
    "ContactsContract.Contacts.getLookupUri", "IndexResultType.CONTACT",
    "IndexAction.ViewContact", "MAX_CONTACT_RESULTS = 100",
]:
    if expected not in contacts:
        raise SystemExit(f"Missing Contacts provider boundary: {expected}")
for prohibited in [
    "CommonDataKinds.Phone", "CommonDataKinds.Email", "Phone.NUMBER", "Email.ADDRESS",
]:
    if prohibited in contacts:
        raise SystemExit(f"Contacts provider exceeds minimized display-data slice: {prohibited}")

main_activity = (ROOT / "app/src/main/java/com/goreecloud/index/MainActivity.kt").read_text(encoding="utf-8")
for expected in [
    "ContactsProvider", "PROVIDER_CONTACTS", "providerAuthorities",
    "Manifest.permission.READ_CONTACTS", "IndexPlatformAuthorityGateway",
    "UnavailableIndexPlatformAuthorityGateway", "ContactsAuthorityProjection.project",
    "platformAuthorityGateway.contactsSnapshot()", "queryEngine.searchIncrementally(",
    "IndexDevelopmentSourcePolicy.selectableProviderIds", "executionContext(enabledProviderIds)",
    "IndexDevelopmentSourcePolicy.executionContext(", "IndexSourceAuthorityProjection.contacts",
    "authorityRefreshRevision", "ActivityResultContracts.RequestPermission()",
    "contactsPermissionLauncher.launch(Manifest.permission.READ_CONTACTS)",
    "onRequestContactsPermission = ::requestContactsPermission",
    "IndexAction.ViewContact", "ContactsContract.AUTHORITY", 'uri.scheme == "content"',
    'uri.pathSegments.firstOrNull() == "contacts"', "Unable to open this application.",
    "Unable to open this contact.",
]:
    if expected not in main_activity:
        raise SystemExit(f"MainActivity missing provider/authority/permission/action boundary: {expected}")

ui = (ROOT / "app/src/main/java/com/goreecloud/index/ui/IndexRoot.kt").read_text(encoding="utf-8")
for expected in [
    "(String, Set<String>) -> Flow<IndexSearchSnapshot>",
    "LaunchedEffect(query, enabledProviderIds)", "collect { update ->", "snapshot = update",
    "Search sources", "Changes apply to this Index session only",
    "Local-only mode", "Enforced in this Development build",
    "Internet/Web results remain unavailable here",
    "Index will not silently enable GoreeCloud Search or another remote provider",
    "IndexProviderIssueKind.TIMED_OUT", "IndexProviderIssueKind.AUTHORIZATION_REQUIRED",
    "Required permission or platform authority evidence is incomplete",
    "IndexPermissionReviewPolicy.canRequestAndroidContactsPermission",
    "Review Android Contacts permission", "Android owns this permission decision",
    "Privacy Shield and GoreeCloud Identity remain independent requirements",
    "WindowInsets.safeDrawing", "heightIn(min = 72.dp)", "People · On-device",
]:
    if expected not in ui:
        raise SystemExit(f"Missing multi-source/incremental/source-control/permission-review UI contract: {expected}")

tests = (ROOT / "app/src/test/java/com/goreecloud/index/core/IndexQueryEngineTest.kt").read_text(encoding="utf-8")
for expected in [
    "providerTimeoutIsReportedWithoutSuppressingHealthyResults", "providersExecuteConcurrently",
    "cancellationPropagatesInsteadOfBecomingProviderIssue",
    "localOnlyExecutionContextFailsClosedForRemoteProviders", "disallowedProviderIsNotDispatched",
    "authorityGatedProviderIsNotDispatchedWithoutEvidence",
    "authorityGatedProviderRunsWithUnconstrainedEvidence",
    "constrainedAuthorityFailsClosedUntilObligationsAreSupported",
    "nonBrowsingProviderDoesNotRequestAuthorityForBlankQuery",
    "resultsAreRankedBeforeProviderScopedDuplicatesAreCollapsed", "resultLimitRemainsBounded",
    "StandardTestDispatcher", "runTest",
]:
    if expected not in tests:
        raise SystemExit(f"Missing async/authority runtime test: {expected}")

incremental_tests = (
    ROOT / "app/src/test/java/com/goreecloud/index/core/IndexIncrementalSearchTest.kt"
).read_text(encoding="utf-8")
for expected in [
    "incrementalSearchEmitsInitialThenProviderCompletionSnapshots",
    "strongerLateRemoteResultReRanksThroughSameDeterministicComposition",
    "authorizationIssueIsEmittedWithoutDispatchingProtectedProvider",
    "cancellingIncrementalCollectionCancelsOutstandingProviderWork",
    "oneShotSearchMatchesFinalIncrementalSnapshot",
    "searchIncrementally", "StandardTestDispatcher", "awaitCancellation",
]:
    if expected not in incremental_tests:
        raise SystemExit(f"Missing incremental search regression: {expected}")

source_control_tests = (
    ROOT / "app/src/test/java/com/goreecloud/index/core/IndexSourceControlsTest.kt"
).read_text(encoding="utf-8")
for expected in [
    "developmentSourcePolicyAllowsOnlyIntegratedLocalProviders",
    "developmentSourcePolicyAlwaysEnforcesLocalOnlyExecution",
    "developmentSourcePolicyPreservesAuthorityEvidenceWithoutGrantingNewScope",
    "contactsAuthorityProjectionReportsOnlyMissingAuthorityDomains",
    "contactsAuthorityProjectionReportsAllPrerequisitesWhenAuthorityIsUnavailable",
    "contactsAuthorityProjectionBecomesAvailableOnlyWhenEveryRequirementIsSatisfied",
    "permissionReviewPolicyOffersAndroidRequestOnlyWhenAndroidPermissionIsMissing",
    "permissionReviewPolicyDoesNotTreatPrivacyOrIdentityAsAndroidPermissionActions",
    "PROVIDER_SEARCH", "sanitizeEnabledProviderIds", "assertFalse",
]:
    if expected not in source_control_tests:
        raise SystemExit(f"Missing source-control/authority-presentation/permission-review regression: {expected}")

platform_tests = (
    ROOT / "app/src/test/java/com/goreecloud/index/core/PlatformAuthorityAdaptersTest.kt"
).read_text(encoding="utf-8")
for expected in [
    "privacyShieldUnconstrainedAllowProjectsAllow", "privacyShieldObligationsRemainConstrained",
    "privacyShieldStaleEvidenceFailsClosed", "identityAuthorizationUsesIdentityOwnedInterpreter",
    "identityUnknownOutcomeFailsClosed", "identityMinimizationViolationFailsClosed",
    "unavailableGatewayKeepsContactsBlocked", "acceptedSnapshotCanSatisfyContactsAuthorities",
]:
    if expected not in platform_tests:
        raise SystemExit(f"Missing platform authority adapter test: {expected}")

documents = [
    "README.md", "SPECIFICATIONS.md", "FEATURES.md", "FEATURE-ROADMAP.md",
    "CAPABILITIES.md", "ARCHITECTURE.md", "CONFORMANCE.md", "USER-MANUAL.md",
    "PRIVACY POLICY.md", "NOTES.md", "SECURITY.md", "BENEFITS.md",
    "COMPETITIVE-OBJECTIVES.md",
]
for document in documents:
    text = (ROOT / document).read_text(encoding="utf-8")
    normalized = text.lower().replace("*", "")
    if document not in {".editorconfig"} and "release lifecycle" not in normalized and document not in {
        "FEATURE-ROADMAP.md", "PRIVACY POLICY.md", "NOTES.md", "SECURITY.md"
    }:
        raise SystemExit(f"{document} missing Development lifecycle state")
    if "GoreeCloud/goreecloud-index" in text:
        raise SystemExit(f"{document} still references the superseded repository namespace")

for document in documents:
    text = (ROOT / document).read_text(encoding="utf-8").lower()
    for prohibited in [
        "contacts integration is accepted",
        "privacy shield integration is accepted",
        "goreecloud identity integration is accepted",
        "production accepted and stable",
        "contacts provider is enabled",
    ]:
        if prohibited in text:
            raise SystemExit(f"Unsupported provider/integration/release claim in {document}: {prohibited}")

for document in ["README.md", "SPECIFICATIONS.md", "FEATURE-ROADMAP.md", "CONFORMANCE.md", "NOTES.md"]:
    text = (ROOT / document).read_text(encoding="utf-8")
    if "GoreeCloud/index" not in text:
        raise SystemExit(f"{document} missing canonical repository identity")

platform_manifest = (ROOT / "goreecloud.platform.yaml").read_text(encoding="utf-8")
for expected in [
    "schema_version: '0.4'",
    "repository: GoreeCloud/index",
    "  policy:",
    "  observability:",
    "platform_contract: '0.4'",
    "glaze_ui_required: '1.6.0'",
    "goreecloud-platform-contract==0.4",
    "glaze-ui==1.6.0",
]:
    if expected not in platform_manifest:
        raise SystemExit(f"Platform Contract declaration missing current control: {expected}")
if "GoreeCloud Sync" in platform_manifest:
    raise SystemExit("GoreeCloud Sync must not be represented as a Platform Contract system key")

for control in ["PRIVACY POLICY.md", "NOTES.md", "SECURITY.md", ".editorconfig"]:
    if not (ROOT / control).is_file():
        raise SystemExit(f"Missing mandatory repository control: {control}")

glaze = (ROOT / "app/src/main/java/com/goreecloud/index/ui/theme/GlazeV16Contract.kt").read_text(encoding="utf-8")
for expected in [
    'VERSION = "1.6.0"',
    'STABLE_RELEASE_SOURCE = "a7180679ea851389e0f3004515f9a25f420e716d"',
    'SOURCE_QUALIFICATION_ANCHOR = "c7509c79256b04b0aa67cb9dd0737d7588e0ae4a"',
    'STABLE_RUNTIME_ENTRYPOINT = "js/glaze-v1.6.0.mjs"',
    'SHARED_ROLLBACK_BASELINE = "1.5.1"',
    "PERMISSION_REQUEST_AUTOMATIC = false",
    "AUTHORIZATION_INFERRED = false",
    "PROVIDER_PRECEDENCE_INFERRED = false",
    "CapabilityState.PermissionRequired",
    "CapabilityState.Conflict",
]:
    if expected not in glaze:
        raise SystemExit(f"Missing GLAZE UI V1.6 source/authority boundary: {expected}")

theme = (ROOT / "app/src/main/java/com/goreecloud/index/ui/theme/IndexTheme.kt").read_text(encoding="utf-8")
if "GlazeV16Contract" not in theme or "GlazeV15Contract" in theme:
    raise SystemExit("Active Index theme must target GlazeV16Contract only")

architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
for expected in [
    "GoreeCloud Search remains authoritative", "Index remains the universal-search/indexing authority",
    "Privacy Shield remains authoritative", "GoreeCloud Identity remains authoritative",
    "ALLOW_WITH_CONSTRAINTS", "ContactsProvider", "AUTHORIZATION_REQUIRED",
]:
    if expected not in architecture:
        raise SystemExit(f"ARCHITECTURE.md missing authority/runtime boundary: {expected}")

print("GoreeCloud Index privacy declaration and authority repository validation passed")
