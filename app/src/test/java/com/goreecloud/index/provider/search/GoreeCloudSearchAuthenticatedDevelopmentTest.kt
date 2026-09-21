package com.goreecloud.index.provider.search

import com.goreecloud.index.core.IndexAuthorityRequirement
import com.goreecloud.index.core.IndexQuery
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GoreeCloudSearchAuthenticatedDevelopmentTest {
    @Test
    fun authenticatedDevelopmentRequiresPrivacyShieldAndIdentityAndCarriesBoth() = runTest {
        var observed: GoreeCloudSearchRequest? = null
        var authorizationCalls = 0
        var authenticationCalls = 0
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                observed = request
                GoreeCloudSearchResponse(
                    apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                    query = request.query,
                    category = request.category,
                    results = emptyList(),
                )
            },
            capabilityClient = GoreeCloudSearchCapabilityClient { authenticatedDevelopmentCapability() },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.AUTHENTICATED_DEVELOPMENT,
            authorizationClient = GoreeCloudSearchAuthorizationClient {
                authorizationCalls++
                GoreeCloudSearchPrivacyAuthorization("psc_development")
            },
            requesterAuthenticationClient = GoreeCloudSearchRequesterAuthenticationClient {
                authenticationCalls++
                GoreeCloudSearchRequesterAuthentication("identity_development")
            },
        )

        provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 2))

        assertEquals(
            setOf(
                IndexAuthorityRequirement.PRIVACY_SHIELD,
                IndexAuthorityRequirement.GOREECLOUD_IDENTITY,
            ),
            provider.authorityRequirements,
        )
        assertEquals(1, authorizationCalls)
        assertEquals(1, authenticationCalls)
        assertEquals("psc_development", observed?.privacyCapabilityReference)
        assertEquals("identity_development", observed?.requesterBearerCredential)
    }

    @Test
    fun authenticatedDevelopmentAcceptsProductionShapedCapabilityWithoutProductionClaim() = runTest {
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
                authenticatedDevelopmentCapability(productionAccepted = false)
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.AUTHENTICATED_DEVELOPMENT,
            authorizationClient = GoreeCloudSearchAuthorizationClient {
                GoreeCloudSearchPrivacyAuthorization("psc_development")
            },
            requesterAuthenticationClient = GoreeCloudSearchRequesterAuthenticationClient {
                GoreeCloudSearchRequesterAuthentication("identity_development")
            },
        )

        provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))

        assertEquals(1, searchCalls)
    }

    @Test
    fun authenticatedDevelopmentRejectsGetOnlyCapabilityBeforeAuthorityAcquisition() = runTest {
        var authorizationCalls = 0
        var authenticationCalls = 0
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
                authenticatedDevelopmentCapability(
                    methods = setOf("GET"),
                    preferredMethod = "GET",
                )
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.AUTHENTICATED_DEVELOPMENT,
            authorizationClient = GoreeCloudSearchAuthorizationClient {
                authorizationCalls++
                GoreeCloudSearchPrivacyAuthorization("psc_development")
            },
            requesterAuthenticationClient = GoreeCloudSearchRequesterAuthenticationClient {
                authenticationCalls++
                GoreeCloudSearchRequesterAuthentication("identity_development")
            },
        )

        val failure = runCatching {
            provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "GoreeCloud Search query capability does not provide the required authenticated Development POST transport",
            failure?.message,
        )
        assertEquals(0, authorizationCalls)
        assertEquals(0, authenticationCalls)
        assertEquals(0, searchCalls)
    }

    @Test
    fun legacyDevelopmentModeRemainsUnauthenticatedAndNonNetworkByDefault() = runTest {
        var observed: GoreeCloudSearchRequest? = null
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                observed = request
                GoreeCloudSearchResponse(
                    apiVersion = GOREECLOUD_SEARCH_API_VERSION,
                    query = request.query,
                    category = request.category,
                    results = emptyList(),
                )
            },
            capabilityClient = GoreeCloudSearchCapabilityClient {
                authenticatedDevelopmentCapability()
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.DEVELOPMENT,
        )

        provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))

        assertEquals(setOf(IndexAuthorityRequirement.PRIVACY_SHIELD), provider.authorityRequirements)
        assertFalse(provider.authorityRequirements.contains(IndexAuthorityRequirement.GOREECLOUD_IDENTITY))
        assertEquals(null, observed?.privacyCapabilityReference)
        assertEquals(null, observed?.requesterBearerCredential)
    }

    private fun authenticatedDevelopmentCapability(
        productionAccepted: Boolean = false,
        methods: Set<String> = setOf("POST"),
        preferredMethod: String = GOREECLOUD_SEARCH_PREFERRED_METHOD,
    ): GoreeCloudSearchCapability = GoreeCloudSearchCapability(
        id = GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID,
        contractVersion = GOREECLOUD_SEARCH_API_VERSION,
        authoritative = true,
        current = true,
        endpoint = GOREECLOUD_SEARCH_QUERY_ENDPOINT,
        maxResults = GOREECLOUD_SEARCH_MAX_RESULTS,
        productionAccepted = productionAccepted,
        discoveryEndpoint = GOREECLOUD_SEARCH_DISCOVERY_ENDPOINT,
        discoveryCollection = GOREECLOUD_SEARCH_DISCOVERY_COLLECTION,
        methods = methods,
        preferredMethod = preferredMethod,
        preferredQueryTransport = GOREECLOUD_SEARCH_PREFERRED_QUERY_TRANSPORT,
        requestMediaType = GOREECLOUD_SEARCH_REQUEST_MEDIA_TYPE,
        responseMediaType = GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE,
        privacyAuthorizationRequired = true,
        privacyAuthorizationScheme = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_SCHEME,
        privacyAuthorizationHeader = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_HEADER,
        privacyAuthorizationEnforcement = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_ENFORCEMENT,
        authenticatedRequesterRequired = true,
        maxRequestBytes = GOREECLOUD_SEARCH_MAX_REQUEST_BYTES,
        authenticatedRequesterAuthority = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_AUTHORITY,
        authenticatedRequesterScheme = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_SCHEME,
        authenticatedRequesterHeader = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_HEADER,
        indexDelegationContractVersion = GOREECLOUD_SEARCH_INDEX_DELEGATION_CONTRACT_VERSION,
        indexDelegationMode = GOREECLOUD_SEARCH_INDEX_DELEGATION_MODE,
        indexProviderReentryAllowed = GOREECLOUD_SEARCH_INDEX_PROVIDER_REENTRY_ALLOWED,
        indexDelegationFallbackAllowed = GOREECLOUD_SEARCH_INDEX_DELEGATION_FALLBACK_ALLOWED,
    )
}
