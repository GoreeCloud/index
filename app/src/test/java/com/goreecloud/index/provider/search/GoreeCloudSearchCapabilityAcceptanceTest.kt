package com.goreecloud.index.provider.search

import com.goreecloud.index.core.IndexQuery
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GoreeCloudSearchCapabilityAcceptanceTest {
    @Test
    fun duplicateQueryCapabilitiesFailDiscoveryClosed() {
        val evidence = capability(productionAccepted = true)
        assertNull(GoreeCloudSearchCapabilityDiscovery.select(listOf(evidence, evidence)))
    }

    @Test
    fun developmentModeAcceptsLegacyDevelopmentGetCapability() = runTest {
        var searchCalls = 0
        val provider = provider(
            mode = GoreeCloudSearchAcceptanceMode.DEVELOPMENT,
            capability = capability(
                productionAccepted = false,
                discoveryEndpoint = null,
                discoveryCollection = null,
                methods = setOf("GET"),
                preferredMethod = "GET",
                preferredQueryTransport = "url_query",
                requestMediaType = null,
                responseMediaType = null,
                privacyAuthorizationRequired = false,
                privacyAuthorizationScheme = null,
                privacyAuthorizationHeader = null,
                privacyAuthorizationEnforcement = null,
                authenticatedRequesterRequired = false,
                authenticatedRequesterAuthority = null,
                authenticatedRequesterScheme = null,
                authenticatedRequesterHeader = null,
                maxRequestBytes = 0,
            ),
        ) {
            searchCalls++
        }

        val response = provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))

        assertEquals(1, searchCalls)
        assertTrue(response.results.isEmpty())
    }

    @Test
    fun productionModeRejectsDevelopmentCapabilityBeforeQuery() = runTest {
        var searchCalls = 0
        val provider = provider(
            mode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            capability = capability(productionAccepted = false),
        ) {
            searchCalls++
        }

        val failure = runCatching {
            provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals("GoreeCloud Search query capability is not production accepted", failure?.message)
        assertEquals(0, searchCalls)
    }

    @Test
    fun productionModeRejectsGetOnlyCapabilityBeforeQuery() = runTest {
        var searchCalls = 0
        val provider = provider(
            mode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            capability = capability(
                productionAccepted = true,
                methods = setOf("GET"),
                preferredMethod = "GET",
            ),
        ) {
            searchCalls++
        }

        val failure = runCatching {
            provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "GoreeCloud Search query capability does not provide the required production POST transport",
            failure?.message,
        )
        assertEquals(0, searchCalls)
    }

    @Test
    fun productionModeRejectsUrlQueryTransportBeforeQuery() = runTest {
        var searchCalls = 0
        val provider = provider(
            mode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            capability = capability(
                productionAccepted = true,
                preferredQueryTransport = "url_query",
            ),
        ) {
            searchCalls++
        }

        val failure = runCatching {
            provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "GoreeCloud Search query capability does not provide the required private JSON-body contract",
            failure?.message,
        )
        assertEquals(0, searchCalls)
    }

    @Test
    fun productionModeRejectsDevelopmentAuthorizationEnforcementBeforeAuthorizationOrQuery() = runTest {
        var authorizationCalls = 0
        var searchCalls = 0
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                searchCalls++
                emptyResponse(request)
            },
            capabilityClient = GoreeCloudSearchCapabilityClient {
                capability(
                    productionAccepted = true,
                    privacyAuthorizationEnforcement = "not_enforced_development",
                )
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            authorizationClient = GoreeCloudSearchAuthorizationClient {
                authorizationCalls++
                GoreeCloudSearchPrivacyAuthorization("psc_test")
            },
        )

        val failure = runCatching {
            provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "GoreeCloud Search query capability does not enforce the required Privacy Shield authorization and authenticated requester transport",
            failure?.message,
        )
        assertEquals(0, authorizationCalls)
        assertEquals(0, searchCalls)
    }

    @Test
    fun productionModeRejectsMissingAuthenticatedRequesterRequirementBeforeAuthorizationOrQuery() = runTest {
        var authorizationCalls = 0
        var searchCalls = 0
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                searchCalls++
                emptyResponse(request)
            },
            capabilityClient = GoreeCloudSearchCapabilityClient {
                capability(
                    productionAccepted = true,
                    authenticatedRequesterRequired = false,
                )
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            authorizationClient = GoreeCloudSearchAuthorizationClient {
                authorizationCalls++
                GoreeCloudSearchPrivacyAuthorization("psc_test")
            },
        )

        val failure = runCatching {
            provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "GoreeCloud Search query capability does not enforce the required Privacy Shield authorization and authenticated requester transport",
            failure?.message,
        )
        assertEquals(0, authorizationCalls)
        assertEquals(0, searchCalls)
    }

    @Test
    fun productionModeRejectsWrongRequesterAuthenticationCarrierBeforeAuthorizationOrQuery() = runTest {
        val variants = listOf(
            capability(
                productionAccepted = true,
                authenticatedRequesterAuthority = "untrusted-authority",
            ),
            capability(
                productionAccepted = true,
                authenticatedRequesterScheme = "basic",
            ),
            capability(
                productionAccepted = true,
                authenticatedRequesterHeader = "X-GoreeCloud-Requester",
            ),
        )

        for (candidate in variants) {
            var authorizationCalls = 0
            var searchCalls = 0
            val provider = GoreeCloudSearchProvider(
                client = GoreeCloudSearchClient { request ->
                    searchCalls++
                    emptyResponse(request)
                },
                capabilityClient = GoreeCloudSearchCapabilityClient { candidate },
                acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
                authorizationClient = GoreeCloudSearchAuthorizationClient {
                    authorizationCalls++
                    GoreeCloudSearchPrivacyAuthorization("psc_test")
                },
            )

            val failure = runCatching {
                provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
            }.exceptionOrNull()

            assertTrue(failure is IllegalStateException)
            assertEquals(
                "GoreeCloud Search query capability does not enforce the required Privacy Shield authorization and authenticated requester transport",
                failure?.message,
            )
            assertEquals(0, authorizationCalls)
            assertEquals(0, searchCalls)
        }
    }

    @Test
    fun productionModeRequiresAuthorizationClientBeforeQuery() = runTest {
        var searchCalls = 0
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                searchCalls++
                emptyResponse(request)
            },
            capabilityClient = GoreeCloudSearchCapabilityClient {
                capability(productionAccepted = true)
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            authorizationClient = null,
        )

        val failure = runCatching {
            provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "GoreeCloud Search production delegation requires a Privacy Shield authorization client",
            failure?.message,
        )
        assertEquals(0, searchCalls)
    }

    @Test
    fun productionModeRejectsNoncanonicalPrivacyCapabilityReferenceBeforeQuery() = runTest {
        var searchCalls = 0
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                searchCalls++
                emptyResponse(request)
            },
            capabilityClient = GoreeCloudSearchCapabilityClient {
                capability(productionAccepted = true)
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            authorizationClient = GoreeCloudSearchAuthorizationClient {
                GoreeCloudSearchPrivacyAuthorization("privacy-shield:capability:test")
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

    @Test
    fun productionModeCarriesCapabilityTokenReferenceWithSearchOperation() = runTest {
        var observedRequest: GoreeCloudSearchRequest? = null
        var observedAuthorizationRequest: GoreeCloudSearchPrivacyAuthorizationRequest? = null
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                observedRequest = request
                emptyResponse(request)
            },
            capabilityClient = GoreeCloudSearchCapabilityClient {
                capability(productionAccepted = true)
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            authorizationClient = GoreeCloudSearchAuthorizationClient { request ->
                observedAuthorizationRequest = request
                GoreeCloudSearchPrivacyAuthorization(" psc_test ")
            },
            requesterAuthenticationClient = GoreeCloudSearchRequesterAuthenticationClient {
                GoreeCloudSearchRequesterAuthentication("identity-requester-token")
            },
        )

        provider.searchWithStatus(IndexQuery(text = "goreecloud", maxResults = 1))

        assertEquals("search.query", observedAuthorizationRequest?.operation)
        assertEquals("private_goreecloud", observedAuthorizationRequest?.processingZone)
        assertEquals("https://search.goreecloud.com", observedAuthorizationRequest?.destination)
        assertEquals("none", observedAuthorizationRequest?.retentionMode)
        assertEquals("psc_test", observedRequest?.privacyCapabilityReference)
        assertEquals("identity-requester-token", observedRequest?.requesterBearerCredential)
    }

    @Test
    fun productionModeAcquiresFreshAuthorizationForEachQuery() = runTest {
        var authorizationCalls = 0
        val observedReferences = mutableListOf<String?>()
        val provider = GoreeCloudSearchProvider(
            client = GoreeCloudSearchClient { request ->
                observedReferences += request.privacyCapabilityReference
                emptyResponse(request)
            },
            capabilityClient = GoreeCloudSearchCapabilityClient {
                capability(productionAccepted = true)
            },
            acceptanceMode = GoreeCloudSearchAcceptanceMode.PRODUCTION,
            authorizationClient = GoreeCloudSearchAuthorizationClient {
                authorizationCalls++
                GoreeCloudSearchPrivacyAuthorization("psc_query_$authorizationCalls")
            },
            requesterAuthenticationClient = GoreeCloudSearchRequesterAuthenticationClient {
                GoreeCloudSearchRequesterAuthentication("identity-requester-token")
            },
        )

        provider.searchWithStatus(IndexQuery(text = "first", maxResults = 1))
        provider.searchWithStatus(IndexQuery(text = "second", maxResults = 1))

        assertEquals(2, authorizationCalls)
        assertEquals(listOf("psc_query_1", "psc_query_2"), observedReferences)
    }

    private fun provider(
        mode: GoreeCloudSearchAcceptanceMode,
        capability: GoreeCloudSearchCapability,
        onSearch: () -> Unit,
    ): GoreeCloudSearchProvider = GoreeCloudSearchProvider(
        client = GoreeCloudSearchClient { request ->
            onSearch()
            emptyResponse(request)
        },
        capabilityClient = GoreeCloudSearchCapabilityClient { capability },
        acceptanceMode = mode,
        authorizationClient = if (mode == GoreeCloudSearchAcceptanceMode.PRODUCTION) {
            GoreeCloudSearchAuthorizationClient {
                GoreeCloudSearchPrivacyAuthorization("psc_test")
            }
        } else {
            null
        },
    )

    private fun capability(
        productionAccepted: Boolean,
        discoveryEndpoint: String? = GOREECLOUD_SEARCH_DISCOVERY_ENDPOINT,
        discoveryCollection: String? = GOREECLOUD_SEARCH_DISCOVERY_COLLECTION,
        methods: Set<String> = setOf("POST", "GET"),
        preferredMethod: String = GOREECLOUD_SEARCH_PREFERRED_METHOD,
        preferredQueryTransport: String = GOREECLOUD_SEARCH_PREFERRED_QUERY_TRANSPORT,
        requestMediaType: String? = GOREECLOUD_SEARCH_REQUEST_MEDIA_TYPE,
        responseMediaType: String? = GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE,
        privacyAuthorizationRequired: Boolean = true,
        privacyAuthorizationScheme: String? = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_SCHEME,
        privacyAuthorizationHeader: String? = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_HEADER,
        privacyAuthorizationEnforcement: String? = GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_ENFORCEMENT,
        authenticatedRequesterRequired: Boolean = true,
        authenticatedRequesterAuthority: String? = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_AUTHORITY,
        authenticatedRequesterScheme: String? = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_SCHEME,
        authenticatedRequesterHeader: String? = GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_HEADER,
        maxRequestBytes: Int = GOREECLOUD_SEARCH_MAX_REQUEST_BYTES,
    ): GoreeCloudSearchCapability = GoreeCloudSearchCapability(
        id = GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID,
        contractVersion = GOREECLOUD_SEARCH_API_VERSION,
        authoritative = true,
        current = true,
        endpoint = GOREECLOUD_SEARCH_QUERY_ENDPOINT,
        maxResults = GOREECLOUD_SEARCH_MAX_RESULTS,
        productionAccepted = productionAccepted,
        discoveryEndpoint = discoveryEndpoint,
        discoveryCollection = discoveryCollection,
        methods = methods,
        preferredMethod = preferredMethod,
        preferredQueryTransport = preferredQueryTransport,
        requestMediaType = requestMediaType,
        responseMediaType = responseMediaType,
        privacyAuthorizationRequired = privacyAuthorizationRequired,
        privacyAuthorizationScheme = privacyAuthorizationScheme,
        privacyAuthorizationHeader = privacyAuthorizationHeader,
        privacyAuthorizationEnforcement = privacyAuthorizationEnforcement,
        authenticatedRequesterRequired = authenticatedRequesterRequired,
        maxRequestBytes = maxRequestBytes,
        authenticatedRequesterAuthority = authenticatedRequesterAuthority,
        authenticatedRequesterScheme = authenticatedRequesterScheme,
        authenticatedRequesterHeader = authenticatedRequesterHeader,
    )

    private fun emptyResponse(request: GoreeCloudSearchRequest): GoreeCloudSearchResponse =
        GoreeCloudSearchResponse(
            apiVersion = GOREECLOUD_SEARCH_API_VERSION,
            query = request.query,
            category = request.category,
            results = emptyList(),
        )
}
