package com.goreecloud.index.provider.search

import com.goreecloud.index.core.GoreeCloudIndexContract
import com.goreecloud.index.core.IndexAuthorityEvidence
import com.goreecloud.index.core.IndexAuthorityOutcome
import com.goreecloud.index.core.IndexExecutionContext
import com.goreecloud.index.core.IndexProviderAuthority
import com.goreecloud.index.core.IndexQueryEngine
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class GoreeCloudSearchRankingTest {
    @Test
    fun sameRelevanceSearchResultsPreserveSourceOrderWithoutTrustingRawScoreScale() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                GoreeCloudSearchResponse(
                    apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                    query = request.query,
                    category = request.category,
                    results = listOf(
                        GoreeCloudSearchResult(
                            title = "Zeta GoreeCloud",
                            url = "https://example.com/zeta",
                            searchScore = 1,
                        ),
                        GoreeCloudSearchResult(
                            title = "Alpha GoreeCloud",
                            url = "https://example.com/alpha",
                            searchScore = Int.MAX_VALUE,
                        ),
                    ),
                )
            },
            capabilityClient = GoreeCloudSearchCapabilityClient {
                GoreeCloudSearchCapability(
                    id = GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID,
                    contractVersion = GOREECLOUD_SEARCH_API_VERSION,
                    authoritative = true,
                    current = true,
                    endpoint = GOREECLOUD_SEARCH_QUERY_ENDPOINT,
                    maxResults = GOREECLOUD_SEARCH_MAX_RESULTS,
                    productionAccepted = false,
                    indexDelegationContractVersion = GOREECLOUD_SEARCH_INDEX_DELEGATION_CONTRACT_VERSION,
                    indexDelegationMode = GOREECLOUD_SEARCH_INDEX_DELEGATION_MODE,
                    indexProviderReentryAllowed = GOREECLOUD_SEARCH_INDEX_PROVIDER_REENTRY_ALLOWED,
                    indexDelegationFallbackAllowed = GOREECLOUD_SEARCH_INDEX_DELEGATION_FALLBACK_ALLOWED,
                )
            },
        )

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "goreecloud",
            executionContext = IndexExecutionContext(
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
            ),
        )

        assertEquals(
            listOf("Zeta GoreeCloud", "Alpha GoreeCloud"),
            snapshot.results.map { it.title },
        )
        assertEquals(listOf(0, 1), snapshot.results.map { it.sourceOrdinal })
    }
}
