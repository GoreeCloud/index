package com.goreecloud.index.provider.search

import com.goreecloud.index.core.GoreeCloudIndexContract
import com.goreecloud.index.core.IndexAuthorityEvidence
import com.goreecloud.index.core.IndexAuthorityOutcome
import com.goreecloud.index.core.IndexAuthorityRequirement
import com.goreecloud.index.core.IndexExecutionContext
import com.goreecloud.index.core.IndexProviderAuthority
import com.goreecloud.index.core.IndexProviderIssueKind
import com.goreecloud.index.core.IndexQueryEngine
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class GoreeCloudSearchAuthorityRequirementsTest {
    @Test
    fun productionSearchProviderRequiresPrivacyShieldAndIdentityAuthority() {
        val provider = productionProvider()

        assertEquals(
            setOf(
                IndexAuthorityRequirement.PRIVACY_SHIELD,
                IndexAuthorityRequirement.GOREECLOUD_IDENTITY,
            ),
            provider.authorityRequirements,
        )
    }

    @Test
    fun privacyShieldWithoutIdentityFailsProductionClosedBeforeCapabilityPreflight() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var capabilityCalls = 0
        var searchCalls = 0
        val provider = productionProvider(
            onCapability = { capabilityCalls++ },
            onSearch = { searchCalls++ },
        )

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = IndexExecutionContext(
                allowedProviderIds = setOf(GoreeCloudIndexContract.PROVIDER_SEARCH),
                localOnly = false,
                providerAuthorities = mapOf(
                    GoreeCloudIndexContract.PROVIDER_SEARCH to IndexProviderAuthority(
                        privacyShield = allowedEvidence("privacy-shield:test"),
                    ),
                ),
            ),
        )

        assertEquals(0, capabilityCalls)
        assertEquals(0, searchCalls)
        assertTrue(snapshot.results.isEmpty())
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.AUTHORIZATION_REQUIRED, snapshot.providerIssues.single().kind)
        assertEquals(GoreeCloudIndexContract.PROVIDER_SEARCH, snapshot.providerIssues.single().providerId)
    }

    private fun productionProvider(
        onCapability: () -> Unit = {},
        onSearch: () -> Unit = {},
    ): GoreeCloudSearchProvider = GoreeCloudSearchProvider(
        client = GoreeCloudSearchClient { request ->
            onSearch()
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = request.query,
                category = request.category,
                results = emptyList(),
            )
        },
        capabilityClient = GoreeCloudSearchCapabilityClient {
            onCapability()
            GoreeCloudSearchCapability(
                id = GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID,
                contractVersion = GOREECLOUD_SEARCH_API_VERSION,
                authoritative = true,
                current = true,
                endpoint = GOREECLOUD_SEARCH_QUERY_ENDPOINT,
                maxResults = GOREECLOUD_SEARCH_MAX_RESULTS,
                productionAccepted = false,
            )
        },
        acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
    )

    private fun allowedEvidence(reference: String): IndexAuthorityEvidence = IndexAuthorityEvidence(
        outcome = IndexAuthorityOutcome.ALLOW,
        reference = reference,
    )
}
