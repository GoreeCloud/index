package com.goreecloud.index

import android.Manifest
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.ContactsContract
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.mutableIntStateOf
import androidx.core.content.ContextCompat
import com.goreecloud.index.core.ContactsAuthorityProjection
import com.goreecloud.index.core.GoreeCloudIndexContract
import com.goreecloud.index.core.IndexAction
import com.goreecloud.index.core.IndexDevelopmentSourcePolicy
import com.goreecloud.index.core.IndexExecutionContext
import com.goreecloud.index.core.IndexPlatformAuthorityGateway
import com.goreecloud.index.core.IndexProviderAuthority
import com.goreecloud.index.core.IndexQueryEngine
import com.goreecloud.index.core.IndexResult
import com.goreecloud.index.core.IndexSourceAuthorityProjection
import com.goreecloud.index.core.UnavailableIndexPlatformAuthorityGateway
import com.goreecloud.index.provider.apps.InstalledAppsProvider
import com.goreecloud.index.provider.contacts.ContactsProvider
import com.goreecloud.index.provider.settings.SystemSettingsProvider
import com.goreecloud.index.ui.IndexRoot
import com.goreecloud.index.ui.theme.GoreeCloudIndexTheme
import java.util.Locale

class MainActivity : ComponentActivity() {
    private lateinit var appsProvider: InstalledAppsProvider
    private lateinit var contactsProvider: ContactsProvider
    private lateinit var settingsProvider: SystemSettingsProvider
    private lateinit var queryEngine: IndexQueryEngine
    private val authorityRefreshRevision = mutableIntStateOf(0)
    private val contactsPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) {
        authorityRefreshRevision.intValue += 1
    }
    private val platformAuthorityGateway: IndexPlatformAuthorityGateway =
        UnavailableIndexPlatformAuthorityGateway

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        appsProvider = InstalledAppsProvider(this)
        contactsProvider = ContactsProvider(this)
        settingsProvider = SystemSettingsProvider()
        queryEngine = IndexQueryEngine(listOf(appsProvider, contactsProvider, settingsProvider))

        setContent {
            val authorityRevision = authorityRefreshRevision.intValue
            val contactsAuthority = contactsAuthority()
            GoreeCloudIndexTheme {
                IndexRoot(
                    initialQuery = intent.getStringExtra(GoreeCloudIndexContract.EXTRA_QUERY).orEmpty(),
                    initiallyEnabledProviderIds = IndexDevelopmentSourcePolicy.selectableProviderIds,
                    authorityRevision = authorityRevision,
                    sourceAuthorityStatuses = mapOf(
                        GoreeCloudIndexContract.PROVIDER_CONTACTS to
                            IndexSourceAuthorityProjection.contacts(contactsAuthority),
                    ),
                    onSearch = { query, enabledProviderIds ->
                        queryEngine.searchIncrementally(
                            rawQuery = query,
                            executionContext = executionContext(enabledProviderIds),
                        )
                    },
                    onRequestContactsPermission = ::requestContactsPermission,
                    onOpenResult = ::openResult,
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (::appsProvider.isInitialized) {
            appsProvider.refresh()
        }
        authorityRefreshRevision.intValue += 1
    }

    private fun contactsAuthority(): IndexProviderAuthority = ContactsAuthorityProjection.project(
        androidPermissionGranted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.READ_CONTACTS,
        ) == PackageManager.PERMISSION_GRANTED,
        snapshot = platformAuthorityGateway.contactsSnapshot(),
    )

    private fun executionContext(enabledProviderIds: Set<String>): IndexExecutionContext =
        IndexDevelopmentSourcePolicy.executionContext(
            requestedProviderIds = enabledProviderIds,
            providerAuthorities = mapOf(
                GoreeCloudIndexContract.PROVIDER_CONTACTS to contactsAuthority(),
            ),
        )

    private fun requestContactsPermission() {
        if (
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.READ_CONTACTS,
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            authorityRefreshRevision.intValue += 1
            return
        }

        contactsPermissionLauncher.launch(Manifest.permission.READ_CONTACTS)
    }

    private fun openResult(result: IndexResult) {
        when (val action = result.action) {
            is IndexAction.LaunchActivity -> openApplication(action)
            is IndexAction.ViewContact -> openContact(action)
            is IndexAction.OpenSystemSetting -> openSystemSetting(action)
            is IndexAction.OpenWeb -> openWeb(action)
            null -> Unit
        }
    }

    private fun openApplication(action: IndexAction.LaunchActivity) {
        val launchIntent = Intent(Intent.ACTION_MAIN)
            .addCategory(Intent.CATEGORY_LAUNCHER)
            .setComponent(ComponentName(action.packageName, action.className))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        runCatching { startActivity(launchIntent) }
            .onFailure {
                Toast.makeText(
                    this,
                    "Unable to open this application.",
                    Toast.LENGTH_SHORT,
                ).show()
            }
    }

    private fun openContact(action: IndexAction.ViewContact) {
        val uri = Uri.parse(action.uri)
        val validContactUri = uri.scheme == "content" &&
            uri.authority == ContactsContract.AUTHORITY &&
            uri.pathSegments.firstOrNull() == "contacts"
        if (!validContactUri) {
            Toast.makeText(this, "Unable to open this contact.", Toast.LENGTH_SHORT).show()
            return
        }

        runCatching {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        }.onFailure {
            Toast.makeText(this, "Unable to open this contact.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun openSystemSetting(action: IndexAction.OpenSystemSetting) {
        if (!SystemSettingsProvider.isAllowedAction(action.action)) {
            Toast.makeText(this, "Unable to open this setting.", Toast.LENGTH_SHORT).show()
            return
        }

        runCatching {
            startActivity(Intent(action.action))
        }.onFailure {
            Toast.makeText(this, "Unable to open this setting.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun openWeb(action: IndexAction.OpenWeb) {
        val uri = Uri.parse(action.uri)
        val scheme = uri.scheme?.lowercase(Locale.ROOT)
        val validWebUri = (scheme == "https" || scheme == "http") &&
            !uri.host.isNullOrBlank() &&
            uri.userInfo == null
        if (!validWebUri) {
            Toast.makeText(this, "Unable to open this web result.", Toast.LENGTH_SHORT).show()
            return
        }

        runCatching {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        }.onFailure {
            Toast.makeText(this, "Unable to open this web result.", Toast.LENGTH_SHORT).show()
        }
    }
}
