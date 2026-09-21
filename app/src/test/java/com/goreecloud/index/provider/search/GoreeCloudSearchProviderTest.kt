package com.goreecloud.index.provider.search

import com.goreecloud.index.core.GoreeCloudIndexContract
import com.goreecloud.index.core.IndexAction
import com.goreecloud.index.core.IndexAuthorityEvidence
import com.goreecloud.index.core.IndexAuthorityOutcome
import com.goreecloud.index.core.IndexAuthorityRequirement
import com.goreecloud.index.core.IndexExecutionContext
import com.goreecloud.index.core.IndexProcessingLocation
import com.goreecloud.index.core.IndexProviderAuthority
import com.goreecloud.index.core.IndexProviderIssueKind
import com.goreecloud.index.core.IndexQuery
import com.goreecloud.index.core.IndexQueryEngine
import com.goreecloud.index.core.IndexResultType
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class GoreeCloudSearchProviderTest {
    @Test
    fun providerMetadataKeepsInternetSearchRemoteAndPrivacyShieldGated() {
        val provider = searchProvider { request -> emptyResponse(request) }

        assertEquals(GoreeCloudIndexContract.PROVIDER_SEARCH, provider.providerId)
        assertEquals("GoreeCloud Search", provider.displayName)
        assertEquals(IndexProcessingLocation.REMOTE, provider.processingLocation)
        assertEquals(5_000L, provider.timeoutMillis)
        assertEquals(setOf(IndexAuthorityRequirement.PRIVACY_SHIELD), provider.authorityRequirements)
        assertFalse(provider.supportsEmptyQuery)
    }

    @Test
    fun localOnlyExecutionDoesNotPerformCapabilityPreflightOrSearch() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var capabilityCalls = 0
        var searchCalls = 0
        val provider = searchProvider(
            onCapability = { capabilityCalls++ },
        ) { request ->
            searchCalls++
            emptyResponse(request)
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = IndexExecutionContext(
                allowedProviderIds = setOf(GoreeCloudIndexContract.PROVIDER_SEARCH),
                localOnly = true,
            ),
        )

        assertEquals(0, capabilityCalls)
        assertEquals(0, searchCalls)
        assertTrue(snapshot.results.isEmpty())
        assertTrue(snapshot.providerIssues.isEmpty())
    }

    @Test
    fun missingPrivacyShieldEvidenceFailsClosedBeforeCapabilityPreflightOrSearch() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var capabilityCalls = 0
        var searchCalls = 0
        val provider = searchProvider(
            onCapability = { capabilityCalls++ },
        ) { request ->
            searchCalls++
            emptyResponse(request)
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = IndexExecutionContext(
                allowedProviderIds = setOf(GoreeCloudIndexContract.PROVIDER_SEARCH),
                localOnly = false,
            ),
        )

        assertEquals(0, capabilityCalls)
        assertEquals(0, searchCalls)
        assertTrue(snapshot.results.isEmpty())
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.AUTHORIZATION_REQUIRED, snapshot.providerIssues.single().kind)
        assertEquals(GoreeCloudIndexContract.PROVIDER_SEARCH, snapshot.providerIssues.single().providerId)
    }

    @Test
    fun authorizedDelegationPreflightsCapabilityThenSendsMinimizedQuery() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var capabilityCalls = 0
        var observed: GoreeCloudSearchRequest? = null
        val provider = searchProvider(
            onCapability = { capabilityCalls++ },
        ) { request ->
            observed = request
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = request.query,
                category = request.category,
                results = listOf(
                    GoreeCloudSearchResult(
                        title = "GoreeCloud release notes",
                        url = "https://example.com/goreecloud",
                        snippet = "Current release information",
                        searchScore = 30_000,
                    ),
                ),
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "  goreecloud  ",
            executionContext = authorizedRemoteContext(),
            maxResults = 7,
        )

        assertEquals(1, capabilityCalls)
        assertEquals(
            GoreeCloudSearchRequest(
                query = "goreecloud",
                category = "general",
                limit = 7,
            ),
            observed,
        )
        val result = snapshot.results.single()
        assertEquals(GoreeCloudIndexContract.PROVIDER_SEARCH, result.providerId)
        assertEquals(IndexResultType.WEB, result.type)
        assertEquals("https://example.com/goreecloud", result.id)
        assertEquals(IndexAction.OpenWeb("https://example.com/goreecloud"), result.action)
        assertEquals(850, result.score)
        assertTrue(snapshot.providerIssues.isEmpty())
    }

    @Test
    fun incompatibleCapabilityFailsClosedBeforeSearchClientCall() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var searchCalls = 0
        val provider = searchProvider(
            capability = compatibleCapability().copy(contractVersion = "2"),
        ) { request ->
            searchCalls++
            emptyResponse(request)
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = authorizedRemoteContext(),
        )

        assertEquals(0, searchCalls)
        assertTrue(snapshot.results.isEmpty())
        assertEquals(IndexProviderIssueKind.FAILED, snapshot.providerIssues.single().kind)
    }

    @Test
    fun nonCurrentCapabilityFailsClosedBeforeSearchClientCall() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var searchCalls = 0
        val provider = searchProvider(
            capability = compatibleCapability().copy(current = false),
        ) { request ->
            searchCalls++
            emptyResponse(request)
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = authorizedRemoteContext(),
        )

        assertEquals(0, searchCalls)
        assertTrue(snapshot.results.isEmpty())
        assertEquals(IndexProviderIssueKind.FAILED, snapshot.providerIssues.single().kind)
    }

    @Test
    fun publishedCapabilityResultBoundLowersDelegatedLimit() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var observed: GoreeCloudSearchRequest? = null
        val provider = searchProvider(
            capability = compatibleCapability(maxResults = 2),
        ) { request ->
            observed = request
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = request.query,
                category = request.category,
                results = listOf(
                    GoreeCloudSearchResult("One", "https://example.com/1"),
                    GoreeCloudSearchResult("Two", "https://example.com/2"),
                    GoreeCloudSearchResult("Three", "https://example.com/3"),
                ),
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "example",
            executionContext = authorizedRemoteContext(),
            maxResults = 7,
        )

        assertEquals(2, observed?.limit)
        assertEquals(2, snapshot.results.size)
    }

    @Test
    fun developmentCapabilityDoesNotPretendProductionAcceptanceIsRequired() = runTest {
        val provider = searchProvider(
            capability = compatibleCapability().copy(productionAccepted = false),
        ) { request -> emptyResponse(request) }

        val response = provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))

        assertTrue(response.results.isEmpty())
        assertFalse(response.degraded)
    }

    @Test
    fun degradedSearchResponsePreservesValidResultsAndReportsPartialAvailability() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = searchProvider { request ->
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = request.query,
                category = request.category,
                results = listOf(
                    GoreeCloudSearchResult(
                        title = "GoreeCloud documentation",
                        url = "https://docs.example.com/goreecloud",
                        snippet = "Available from a healthy upstream source",
                    ),
                ),
                degraded = true,
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = authorizedRemoteContext(),
        )

        assertEquals(listOf("GoreeCloud documentation"), snapshot.results.map { it.title })
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.DEGRADED, snapshot.providerIssues.single().kind)
        assertEquals(GoreeCloudIndexContract.PROVIDER_SEARCH, snapshot.providerIssues.single().providerId)
    }

    @Test
    fun invalidResultTakesPrecedenceOverDegradedSignalWhileValidSiblingSurvives() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = searchProvider { request ->
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = request.query,
                category = request.category,
                results = listOf(
                    GoreeCloudSearchResult("Unsafe", "javascript:alert(1)"),
                    GoreeCloudSearchResult("Valid", "https://example.com/valid"),
                ),
                degraded = true,
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "valid",
            executionContext = authorizedRemoteContext(),
        )

        assertEquals(listOf("Valid"), snapshot.results.map { it.title })
        assertEquals(IndexProviderIssueKind.INVALID_RESULT, snapshot.providerIssues.single().kind)
    }

    @Test
    fun incompatibleSearchApiVersionFailsProviderClosed() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = searchProvider { request ->
            GoreeCloudSearchResponse(
                apiVersion = "2",
                query = request.query,
                category = request.category,
                results = listOf(
                    GoreeCloudSearchResult(
                        title = "Should not be accepted",
                        url = "https://example.com/incompatible",
                    ),
                ),
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = authorizedRemoteContext(),
        )

        assertTrue(snapshot.results.isEmpty())
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.FAILED, snapshot.providerIssues.single().kind)
        assertEquals(GoreeCloudIndexContract.PROVIDER_SEARCH, snapshot.providerIssues.single().providerId)
    }

    @Test
    fun mismatchedSearchResponseFailsProviderClosed() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = searchProvider { request ->
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = "different query",
                category = request.category,
                results = emptyList(),
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = authorizedRemoteContext(),
        )

        assertTrue(snapshot.results.isEmpty())
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.FAILED, snapshot.providerIssues.single().kind)
    }

    @Test
    fun unsafeWebResultIsRejectedWithoutSuppressingValidSibling() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = searchProvider { request ->
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = request.query,
                category = request.category,
                results = listOf(
                    GoreeCloudSearchResult(
                        title = "Unsafe",
                        url = "javascript:alert(1)",
                    ),
                    GoreeCloudSearchResult(
                        title = "GoreeCloud documentation",
                        url = "https://docs.example.com/goreecloud/../goreecloud/index",
                        snippet = "Documentation",
                    ),
                ),
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = authorizedRemoteContext(),
        )

        assertEquals(1, snapshot.results.size)
        assertEquals("https://docs.example.com/goreecloud/index", snapshot.results.single().id)
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.INVALID_RESULT, snapshot.providerIssues.single().kind)
        assertEquals(GoreeCloudIndexContract.PROVIDER_SEARCH, snapshot.providerIssues.single().providerId)
    }

    @Test
    fun providerCapsResponseToDelegatedLimit() = runTest {
        val provider = searchProvider { request ->
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = request.query,
                category = request.category,
                results = listOf(
                    GoreeCloudSearchResult("One", "https://example.com/1"),
                    GoreeCloudSearchResult("Two", "https://example.com/2"),
                    GoreeCloudSearchResult("Three", "https://example.com/3"),
                ),
            )
        }

        val results = provider.search(IndexQuery(text = "example", maxResults = 2))

        assertEquals(2, results.size)
        assertEquals(listOf("https://example.com/1", "https://example.com/2"), results.map { it.id })
    }

    @Test
    fun unsafeUserInfoURLCannotBecomeExecutableWebAction() = runTest {
        val provider = searchProvider { request ->
            GoreeCloudSearchResponse(
                apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                query = request.query,
                category = request.category,
                results = listOf(
                    GoreeCloudSearchResult("Credential-shaped URL", "https://user:pass@example.com/private"),
                ),
            )
        }

        val result = provider.search(IndexQuery(text = "credential", maxResults = 1)).single()

        assertEquals("", result.id)
        assertNull(result.action)
    }

    private fun searchProvider(
        capability: GoreeCloudSearchCapability? = null,
        onCapability: (() -> Unit)? = null,
        block: suspend (GoreeCloudSearchRequest) -> GoreeCloudSearchResponse,
    ): GoreeCloudSearchProvider = GoreeCloudSearchProvider(
        client = GoreeCloudSearchClient { request -> block(request) },
        capabilityClient = GoreeCloudSearchCapabilityClient {
            onCapability?.invoke()
            capability ?: compatibleCapability()
        },
    )

    private fun compatibleCapability(
        maxResults: Int = GOREECLOUD_SEARCH_MAX_RESULTS,
    ): GoreeCloudSearchCapability = GoreeCloudSearchCapability(
        id = GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID,
        contractVersion = GOREECLOUD_SEARCH_API_VERSION,
        authoritative = true,
        current = true,
        endpoint = GOREECLOUD_SEARCH_QUERY_ENDPOINT,
        maxResults = maxResults,
        productionAccepted = false,
        indexDelegationContractVersion = GOREECLOUD_SEARCH_INDEX_DELEGATION_CONTRACT_VERSION,
        indexDelegationMode = GOREECLOUD_SEARCH_INDEX_DELEGATION_MODE,
        indexProviderReentryAllowed = GOREECLOUD_SEARCH_INDEX_PROVIDER_REENTRY_ALLOWED,
        indexDelegationFallbackAllowed = GOREECLOUD_SEARCH_INDEX_DELEGATION_FALLBACK_ALLOWED,
    )

    private fun authorizedRemoteContext(): IndexExecutionContext = IndexExecutionContext(
        allowedProviderIds = setOf(GoreeCloudIndexContract.PROVIDER_SEARCH),
        localOnly = false,
        providerAuthorities = mapOf(
            GoreeCloudIndexContract.PROVIDER_SEARCH to IndexProviderAuthority(
                privacyShield = IndexAuthorityEvidence(
                    outcome = IndexAuthorityOutcome.ALLOW,
                    reference = "privacy-shield:test-evidence",
                ),
            ),
        ),
    )

    private fun emptyResponse(request: GoreeCloudSearchRequest): GoreeCloudSearchResponse =
        GoreeCloudSearchResponse(
            apiVersion = GOREECLOUD_SEARCH_API_VERSION,
            query = request.query,
            category = request.category,
            results = emptyList(),
        )
}
