package com.goreecloud.index.provider.search

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GoreeCloudSearchHttpTransportTest {
    private class RecordingExecutor(
        var response: GoreeCloudSearchHttpResponse,
    ) : GoreeCloudSearchHttpExecutor {
        val requests = mutableListOf<GoreeCloudSearchHttpRequest>()

        override suspend fun execute(request: GoreeCloudSearchHttpRequest): GoreeCloudSearchHttpResponse {
            requests += request
            return response
        }
    }

    @Test
    fun capabilityDiscoveryUsesFixedHttpsOriginAndMapsSearchContract() = runTest {
        val executor = RecordingExecutor(jsonResponse(capabilityJson()))
        val transport = GoreeCloudSearchHttpTransport(executor)

        val capability = transport.queryCapability()

        assertEquals("search.query", capability.id)
        assertEquals("1", capability.contractVersion)
        assertTrue(capability.authoritative)
        assertTrue(capability.current)
        assertFalse(capability.productionAccepted)
        assertEquals(setOf("POST"), capability.methods)
        assertEquals("POST", capability.preferredMethod)
        assertEquals("json_body", capability.preferredQueryTransport)
        assertEquals("required", capability.privacyAuthorizationEnforcement)
        assertTrue(capability.authenticatedRequesterRequired)
        assertEquals("goreecloud-identity", capability.authenticatedRequesterAuthority)
        assertEquals("goreecloud.search-index-delegation.v1", capability.indexDelegationContractVersion)
        assertEquals("external_only", capability.indexDelegationMode)
        assertEquals(false, capability.indexProviderReentryAllowed)
        assertEquals(false, capability.indexDelegationFallbackAllowed)

        val request = executor.requests.single()
        assertEquals("GET", request.method)
        assertEquals("https://search.goreecloud.com/api/v1/status", request.uri.toString())
        assertNull(request.uri.query)
        assertTrue(request.body.isEmpty())
        assertEquals("application/json", request.headers["Accept"])
        assertFalse(request.headers.containsKey("Authorization"))
    }

    @Test
    fun authenticatedSearchCarriesAuthorityOnlyInHeadersAndUsesJsonBodyPost() = runTest {
        val executor = RecordingExecutor(
            jsonResponse(
                """
                {
                  "apiVersion":"1",
                  "query":"goreecloud search",
                  "category":"general",
                  "results":[
                    {
                      "title":"GoreeCloud",
                      "url":"https://example.com/result",
                      "snippet":"Private result",
                      "searchScore":1250
                    }
                  ],
                  "degraded":false
                }
                """.trimIndent()
            )
        )
        val transport = GoreeCloudSearchHttpTransport(executor)

        val response = transport.search(
            GoreeCloudSearchRequest(
                query = "goreecloud search",
                limit = 3,
                privacyCapabilityReference = "psc_test_reference",
                requesterBearerCredential = "identity_test_token",
            )
        )

        val request = executor.requests.single()
        val body = request.body.decodeToString()
        assertEquals("POST", request.method)
        assertEquals("https://search.goreecloud.com/api/v1/search", request.uri.toString())
        assertNull(request.uri.query)
        assertEquals("application/json", request.headers["Content-Type"])
        assertEquals("psc_test_reference", request.headers["X-GoreeCloud-Privacy-Capability"])
        assertEquals("Bearer identity_test_token", request.headers["Authorization"])
        assertTrue(body.contains("\"query\":\"goreecloud search\""))
        assertTrue(body.contains("\"category\":\"general\""))
        assertTrue(body.contains("\"limit\":3"))
        assertFalse(body.contains("psc_test_reference"))
        assertFalse(body.contains("identity_test_token"))
        assertEquals("1", response.apiVersion)
        assertEquals("https://example.com/result", response.results.single().url)
        assertFalse(response.degraded)
        assertFalse(request.toString().contains("identity_test_token"))
        assertFalse(request.toString().contains("psc_test_reference"))
    }

    @Test
    fun missingAuthorityFailsBeforeHttpExecution() = runTest {
        val executor = RecordingExecutor(jsonResponse("{}"))
        val transport = GoreeCloudSearchHttpTransport(executor)

        val failure = runCatching {
            transport.search(
                GoreeCloudSearchRequest(
                    query = "goreecloud",
                    limit = 1,
                )
            )
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertTrue(executor.requests.isEmpty())
    }

    @Test
    fun redirectOrWrongMediaTypeFailsClosed() = runTest {
        val executor = RecordingExecutor(
            GoreeCloudSearchHttpResponse(
                statusCode = 302,
                contentType = "application/json",
                body = "{}".encodeToByteArray(),
            )
        )
        val transport = GoreeCloudSearchHttpTransport(executor)

        val redirectFailure = runCatching { transport.queryCapability() }.exceptionOrNull()
        assertTrue(redirectFailure is IllegalStateException)

        executor.response = GoreeCloudSearchHttpResponse(
            statusCode = 200,
            contentType = "text/html",
            body = "{}".encodeToByteArray(),
        )
        val mediaFailure = runCatching { transport.queryCapability() }.exceptionOrNull()
        assertTrue(mediaFailure is IllegalStateException)
    }

    @Test
    fun duplicateJsonFieldsFailClosed() = runTest {
        val duplicate = capabilityJson().replace(
            "\"service\":\"goreecloud-search\",",
            "\"service\":\"goreecloud-search\",\"service\":\"spoofed\",",
        )
        val executor = RecordingExecutor(jsonResponse(duplicate))
        val transport = GoreeCloudSearchHttpTransport(executor)

        val failure = runCatching { transport.queryCapability() }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
    }

    private fun jsonResponse(body: String): GoreeCloudSearchHttpResponse =
        GoreeCloudSearchHttpResponse(
            statusCode = 200,
            contentType = "application/json; charset=utf-8",
            body = body.encodeToByteArray(),
        )

    private fun capabilityJson(): String =
        """
        {
          "service":"goreecloud-search",
          "version":"0.1.0.dev14",
          "lifecycle":"development",
          "production_accepted":false,
          "capability_evidence":[
            {
              "id":"search.query",
              "contract_version":"1",
              "authoritative":true,
              "current":true,
              "endpoint":"/api/v1/search",
              "max_results":100,
              "production_accepted":false,
              "discovery_endpoint":"/api/v1/status",
              "discovery_collection":"capability_evidence",
              "methods":["POST"],
              "preferred_method":"POST",
              "preferred_query_transport":"json_body",
              "request_media_type":"application/json",
              "response_media_type":"application/json",
              "privacy_authorization_required":true,
              "privacy_authorization_scheme":"privacy_shield_capability_token_reference",
              "privacy_authorization_header":"X-GoreeCloud-Privacy-Capability",
              "privacy_authorization_enforcement":"required",
              "authenticated_requester_required":true,
              "authenticated_requester_authority":"goreecloud-identity",
              "authenticated_requester_scheme":"bearer",
              "authenticated_requester_header":"Authorization",
              "max_request_bytes":16384,
              "index_delegation_contract_version":"goreecloud.search-index-delegation.v1",
              "index_delegation_mode":"external_only",
              "index_provider_reentry_allowed":false,
              "index_delegation_fallback_allowed":false
            }
          ]
        }
        """.trimIndent()
}
