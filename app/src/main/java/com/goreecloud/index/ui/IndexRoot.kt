package com.goreecloud.index.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.goreecloud.index.core.GoreeCloudIndexContract
import com.goreecloud.index.core.IndexAuthorityRequirement
import com.goreecloud.index.core.IndexPermissionReviewPolicy
import com.goreecloud.index.core.IndexProviderIssue
import com.goreecloud.index.core.IndexProviderIssueKind
import com.goreecloud.index.core.IndexResult
import com.goreecloud.index.core.IndexResultType
import com.goreecloud.index.core.IndexSearchSnapshot
import com.goreecloud.index.core.IndexSourceAuthorityStatus
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.collect

@Composable
fun IndexRoot(
    initialQuery: String,
    initiallyEnabledProviderIds: Set<String>,
    authorityRevision: Int,
    sourceAuthorityStatuses: Map<String, IndexSourceAuthorityStatus>,
    onSearch: (String, Set<String>) -> Flow<IndexSearchSnapshot>,
    onRequestContactsPermission: () -> Unit,
    onOpenResult: (IndexResult) -> Unit,
) {
    var query by rememberSaveable(initialQuery) { mutableStateOf(initialQuery) }
    var enabledProviderIds by remember(initiallyEnabledProviderIds) {
        mutableStateOf(initiallyEnabledProviderIds)
    }
    var snapshot by remember { mutableStateOf(IndexSearchSnapshot()) }
    var searching by remember { mutableStateOf(false) }
    val focusRequester = remember { FocusRequester() }
    val keyboard = LocalSoftwareKeyboardController.current

    key(authorityRevision) {
        LaunchedEffect(query, enabledProviderIds) {
            searching = true
            try {
                onSearch(query, enabledProviderIds).collect { update ->
                    snapshot = update
                }
            } finally {
                searching = false
            }
        }
    }

    LaunchedEffect(Unit) {
        focusRequester.requestFocus()
        keyboard?.show()
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.safeDrawing)
                .padding(horizontal = 20.dp, vertical = 18.dp),
        ) {
            Text(
                text = "GoreeCloud Index",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.semantics { heading() },
            )
            Text(
                text = "Universal search, source by source",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Spacer(Modifier.height(18.dp))

            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 56.dp)
                    .focusRequester(focusRequester),
                singleLine = true,
                shape = RoundedCornerShape(24.dp),
                label = { Text("Search this device") },
                placeholder = { Text("Applications, Settings, and authorized sources") },
                keyboardActions = KeyboardActions(onSearch = { keyboard?.hide() }),
            )

            Spacer(Modifier.height(12.dp))

            SourceStatusCard(
                enabledProviderIds = enabledProviderIds,
                sourceAuthorityStatuses = sourceAuthorityStatuses,
                onToggleProvider = { providerId, enabled ->
                    enabledProviderIds = if (enabled) {
                        enabledProviderIds + providerId
                    } else {
                        enabledProviderIds - providerId
                    }
                },
                onRequestContactsPermission = onRequestContactsPermission,
            )

            if (searching) {
                Spacer(Modifier.height(10.dp))
                Text(
                    text = "Searching enabled authorized sources…",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            snapshot.providerIssues.forEach { issue ->
                Spacer(Modifier.height(12.dp))
                ProviderIssueCard(issue)
            }

            Spacer(Modifier.height(16.dp))

            val results = snapshot.results
            if (results.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = when {
                            searching -> "Searching…"
                            enabledProviderIds.isEmpty() -> "Enable at least one local source to search"
                            snapshot.providerIssues.any {
                                it.kind == IndexProviderIssueKind.FAILED ||
                                    it.kind == IndexProviderIssueKind.TIMED_OUT ||
                                    it.kind == IndexProviderIssueKind.INCOMPATIBLE_CONTRACT ||
                                    it.kind == IndexProviderIssueKind.DEGRADED ||
                                    it.kind == IndexProviderIssueKind.INVALID_RESULT
                            } -> "Some search sources are temporarily unavailable"
                            query.isBlank() -> "Start typing to search enabled sources"
                            else -> "No matches in enabled sources"
                        },
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            } else {
                Text(
                    text = if (query.isBlank()) "Applications" else "Results",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.semantics { heading() },
                )
                Spacer(Modifier.height(8.dp))

                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(
                        items = results,
                        key = { "${it.providerId}:${it.id}" },
                    ) { result ->
                        IndexResultRow(
                            result = result,
                            onClick = { onOpenResult(result) },
                        )
                    }
                    item { Spacer(Modifier.height(24.dp)) }
                }
            }
        }
    }
}

@Composable
private fun SourceStatusCard(
    enabledProviderIds: Set<String>,
    sourceAuthorityStatuses: Map<String, IndexSourceAuthorityStatus>,
    onToggleProvider: (String, Boolean) -> Unit,
    onRequestContactsPermission: () -> Unit,
) {
    val contactsStatus = sourceAuthorityStatuses[GoreeCloudIndexContract.PROVIDER_CONTACTS]
    val contactsEnabled = GoreeCloudIndexContract.PROVIDER_CONTACTS in enabledProviderIds

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerLow,
        ),
    ) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
            Text(
                text = "Search sources",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.semantics { heading() },
            )
            Text(
                text = "Changes apply to this Index session only. They do not grant missing permissions or platform authority.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 2.dp, bottom = 6.dp),
            )

            SourceToggleRow(
                title = "Applications",
                detail = "On-device",
                checked = GoreeCloudIndexContract.PROVIDER_APPS in enabledProviderIds,
                onCheckedChange = { enabled ->
                    onToggleProvider(GoreeCloudIndexContract.PROVIDER_APPS, enabled)
                },
            )
            SourceToggleRow(
                title = "Settings",
                detail = "On-device navigation catalog",
                checked = GoreeCloudIndexContract.PROVIDER_SETTINGS in enabledProviderIds,
                onCheckedChange = { enabled ->
                    onToggleProvider(GoreeCloudIndexContract.PROVIDER_SETTINGS, enabled)
                },
            )
            SourceToggleRow(
                title = "Contacts",
                detail = contactsSourceDetail(contactsStatus),
                checked = contactsEnabled,
                onCheckedChange = { enabled ->
                    onToggleProvider(GoreeCloudIndexContract.PROVIDER_CONTACTS, enabled)
                },
            )

            if (contactsEnabled && contactsStatus != null && !contactsStatus.available) {
                Text(
                    text = "Why Contacts is unavailable: ${missingAuthoritySummary(contactsStatus)}. Index reports these prerequisites but does not approve or bypass them here.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp),
                )

                if (IndexPermissionReviewPolicy.canRequestAndroidContactsPermission(contactsStatus)) {
                    OutlinedButton(
                        onClick = onRequestContactsPermission,
                        modifier = Modifier.padding(top = 8.dp),
                    ) {
                        Text("Review Android Contacts permission")
                    }
                    Text(
                        text = "Android owns this permission decision. Granting it addresses only the Android prerequisite; Privacy Shield and GoreeCloud Identity remain independent requirements.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
            }

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Local-only mode",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = "Enforced in this Development build",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Switch(
                    checked = true,
                    onCheckedChange = null,
                    enabled = false,
                )
            }

            Text(
                text = "Internet/Web results remain unavailable here. Index will not silently enable GoreeCloud Search or another remote provider when a local source is disabled, unavailable, or unauthorized.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}

private fun contactsSourceDetail(status: IndexSourceAuthorityStatus?): String = when {
    status == null -> "On-device · authority status unavailable"
    status.available -> "On-device · authorization prerequisites satisfied"
    else -> "On-device · blocked by ${missingAuthoritySummary(status)}"
}

private fun missingAuthoritySummary(status: IndexSourceAuthorityStatus): String =
    status.missingRequirements.joinToString(separator = " · ") { requirement ->
        authorityRequirementLabel(requirement)
    }

private fun authorityRequirementLabel(requirement: IndexAuthorityRequirement): String = when (requirement) {
    IndexAuthorityRequirement.ANDROID_RUNTIME_PERMISSION -> "Android Contacts permission"
    IndexAuthorityRequirement.PRIVACY_SHIELD -> "Privacy Shield authorization"
    IndexAuthorityRequirement.GOREECLOUD_IDENTITY -> "GoreeCloud Identity authorization"
}

@Composable
private fun SourceToggleRow(
    title: String,
    detail: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = detail,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
        )
    }
}

@Composable
private fun ProviderIssueCard(issue: IndexProviderIssue) {
    val informational = issue.kind == IndexProviderIssueKind.AUTHORIZATION_REQUIRED ||
        issue.kind == IndexProviderIssueKind.DEGRADED
    val title = when (issue.kind) {
        IndexProviderIssueKind.FAILED -> "${issue.providerName} temporarily unavailable"
        IndexProviderIssueKind.TIMED_OUT -> "${issue.providerName} took too long"
        IndexProviderIssueKind.AUTHORIZATION_REQUIRED -> "${issue.providerName} authorization required"
        IndexProviderIssueKind.INCOMPATIBLE_CONTRACT -> "${issue.providerName} needs an update"
        IndexProviderIssueKind.DEGRADED -> "${issue.providerName} is partially available"
        IndexProviderIssueKind.INVALID_RESULT -> "${issue.providerName} returned invalid results"
    }
    val detail = when (issue.kind) {
        IndexProviderIssueKind.FAILED ->
            "Index isolated the provider failure and kept results from healthy providers."
        IndexProviderIssueKind.TIMED_OUT ->
            "Index stopped waiting at the provider's bounded timeout and kept results from healthy providers."
        IndexProviderIssueKind.AUTHORIZATION_REQUIRED ->
            "Required permission or platform authority evidence is incomplete, so Index did not send this provider the query."
        IndexProviderIssueKind.INCOMPATIBLE_CONTRACT ->
            "This provider does not declare the current Index provider contract, so Index did not send it the query."
        IndexProviderIssueKind.DEGRADED ->
            "Some upstream sources were unavailable, so Index kept the valid results that GoreeCloud Search could still return."
        IndexProviderIssueKind.INVALID_RESULT ->
            "Index rejected or bounded results that violated provider provenance, required identity/title fields, source ordering, or the requested result limit, while preserving valid bounded results."
    }
    val containerColor = if (informational) {
        MaterialTheme.colorScheme.surfaceContainerHigh
    } else {
        MaterialTheme.colorScheme.errorContainer
    }
    val contentColor = if (informational) {
        MaterialTheme.colorScheme.onSurface
    } else {
        MaterialTheme.colorScheme.onErrorContainer
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = containerColor),
    ) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
            Text(
                text = title,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
                color = contentColor,
            )
            Text(
                text = detail,
                style = MaterialTheme.typography.bodySmall,
                color = contentColor,
                modifier = Modifier.padding(top = 2.dp),
            )
        }
    }
}

@Composable
private fun IndexResultRow(
    result: IndexResult,
    onClick: () -> Unit,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 72.dp)
            .clickable(enabled = result.action != null, onClick = onClick),
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
        tonalElevation = 1.dp,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                modifier = Modifier.size(48.dp),
                shape = CircleShape,
                color = MaterialTheme.colorScheme.primaryContainer,
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = result.title.firstOrNull()?.uppercaseChar()?.toString() ?: "•",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }

            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 12.dp),
            ) {
                Text(
                    text = result.title,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    fontWeight = FontWeight.SemiBold,
                )
                result.subtitle?.takeIf { it.isNotBlank() }?.let { subtitle ->
                    Text(
                        text = subtitle,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Text(
                text = sourceLabel(result.type),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary,
            )
        }
    }
}

private fun sourceLabel(type: IndexResultType): String = when (type) {
    IndexResultType.APP -> "Apps · On-device"
    IndexResultType.ACTION -> "Action"
    IndexResultType.CONTACT -> "People · On-device"
    IndexResultType.FILE -> "Files"
    IndexResultType.CALENDAR -> "Calendar"
    IndexResultType.MEDIA -> "Media"
    IndexResultType.SETTING -> "Settings · On-device"
    IndexResultType.GOREECLOUD -> "GoreeCloud"
    IndexResultType.DEVICE -> "Device"
    IndexResultType.WEB -> "Web"
}
