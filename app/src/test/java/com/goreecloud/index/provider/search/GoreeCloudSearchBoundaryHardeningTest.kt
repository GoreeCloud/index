package com.goreecloud.index.provider.search

import com.goreecloud.index.core.IndexQuery
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GoreeCloudSearchBoundaryHardeningTest {
    @Test
    fun finalProductionHandoffRejectsMalformedCapabilityReferences() = runTest {
        val invalidReferences = listOf(
            "psc_test capability",
            "psc_test\u0000capability",
            "psc_" + "a".repeat(PRIVACY_SHIELD_SEARCH_CAPABILITY_REFERENCE_MAX_LENGTH),
        )

        invalidReferences.forEach { invalidReference ->
            var searchCalls = 0
            val provider = GoreeCloudSearchProvider(
                client = GoreeCloudSearchClient { request ->
                    searchCalls++
                    GoreeCloudSearchResponse(
                        apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                        query = request.query,
                        category = request.category,
                        results = emptyList(),
                    )
                },
                capabilityClient = GoreeCloudSearchCapabilityClient {
                    productionCapability()
                },
                acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
                authorizationClient = GoreeCloudSearchAuthorizationClient {
                    GoreeCloudSearchPrivacyAuthorization(invalidReference)
                },
            )

            val failure = runCatching {
                provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
            }.exceptionOrNull()

            assertTrue(failure is IllegalStateException)
            assertEquals(
                "GoreeCloud Search production delegation requires a canonical Privacy Shield capability reference",
                failure?.message,
            )
            assertEquals(0, searchCalls)
        }
    }

    private fun productionCapability() = GoreeCloudSearchCapability(
        id = GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID,
        contractVersion = GOREECLOUD_SEARCH_API_VERSION,
        authoritative = true,
        current = true,
        endpoint = GOREECLOUD_SEARCH_QUERY_ENDPOINT,
        maxResults = GOREECLOUD_SEARCH_MAX_RESULTS,
        productionAccepted = true,
        discoveryEndpoint = GOREECLOUD_SEARCH_DISCOVERY_ENDPOINT,
        discoveryCollection = GOREECLOUD_SEARCH_DISCOVERY_COLLECTION,
        methods = setOf("POST", "GET"),
        preferredMethod = GOREECLOUD_SEARCH_PREFERRED_METHOD,
        preferredQueryTransport = GOREECLOUD_SEARCH_PREFERRED_QUERY_TRANSPORT,
        requestMediaType = GOREECLOUD_SEARCH_REQUEST_MEDIA_TYPE,
        responseMediaType = GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE,
        privacyAuthorizationRequired = true,
        privacyAuthorizationScheme = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_SCHEME,
        privacyAuthorizationHeader = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_HEADER,
        privacyAuthorizationEnforcement = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_ENFORCEMENT,
        authenticatedRequesterRequired = true,
        authenticatedRequesterAuthority = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_AUTHORITY,
        authenticatedRequesterScheme = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_SCHEME,
        authenticatedRequesterHeader = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_HEADER,
        maxRequestBytes = GOREECLOUD_SEARCH_MAX_REQUEST_BYTES,
    )
}
