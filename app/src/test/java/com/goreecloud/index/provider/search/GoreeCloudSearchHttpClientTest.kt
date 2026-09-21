package com.goreecloud.index.provider.search

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GoreeCloudSearchHttpClientTest {
    @Test
    fun capabilityDiscoveryParsesDevelopmentProductionShapedContract() = runTest {
        val exchange = RecordingExchange(
            response = jsonResponse(
                """
                {
                  "service":"goreecloud-search",
                  "version":"0.1.0.dev14",
                  "lifecycle":"development",
                  "production_accepted":false,
                  "capability_evidence":[{
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
                  }]
                }
                """.trimIndent(),
            ),
        )
        val client = AuthenticatedGoreeCloudSearchHttpClient(exchange)

        val capability = client.queryCapability()

        assertEquals("search.query", capability.id)
        assertFalse(capability.productionAccepted)
        assertEquals(setOf("POST"), capability.methods)
        assertEquals("POST", capability.preferredMethod)
        assertEquals("json_body", capability.preferredQueryTransport)
        assertTrue(capability.privacyAuthorizationRequired)
        assertTrue(capability.authenticatedRequesterRequired)
        assertEquals("goreecloud.search-index-delegation.v1", capability.indexDelegationContractVersion)
        assertEquals("external_only", capability.indexDelegationMode)
        assertEquals(false, capability.indexProviderReentryAllowed)
        assertEquals(false, capability.indexDelegationFallbackAllowed)
        assertEquals(1, exchange.requests.size)
        assertEquals("GET", exchange.requests.single().method)
        assertEquals("https://search.goreecloud.com/api/v1/status", exchange.requests.single().url.toString())
        assertFalse(exchange.requests.single().headers.containsKey("Authorization"))
    }

    @Test
    fun readinessParsesReadyAndNotReadyWithoutAuthorityHeaders() = runTest {
        val exchange = RecordingExchange(
            response = jsonResponse(
                """{"status":"ready","service":"goreecloud-search","version":"0.1.0.dev14","lifecycle":"development"}"""
            ),
        )
        val client = AuthenticatedGoreeCloudSearchHttpClient(exchange)

        assertTrue(client.queryReadiness())
        val readyRequest = exchange.requests.single()
        assertEquals("GET", readyRequest.method)
        assertEquals("https://search.goreecloud.com/readyz", readyRequest.url.toString())
        assertFalse(readyRequest.headers.containsKey("Authorization"))
        assertFalse(readyRequest.headers.containsKey("X-GoreeCloud-Privacy-Capability"))

        exchange.requests.clear()
        exchange.response = GoreeCloudSearchHttpResponse(
            status = 503,
            contentType = "application/json; charset=utf-8",
            body = """{"status":"not_ready","service":"goreecloud-search","version":"0.1.0.dev14","lifecycle":"development"}"""
                .toByteArray(Charsets.UTF_8),
        )

        assertFalse(client.queryReadiness())
        assertEquals("https://search.goreecloud.com/readyz", exchange.requests.single().url.toString())
    }

    @Test
    fun readinessRejectsInconsistentOrUnexpectedServiceResponses() = runTest {
        val exchange = RecordingExchange(
            response = jsonResponse(
                """{"status":"not_ready","service":"goreecloud-search","version":"0.1.0.dev14","lifecycle":"development"}"""
            ),
        )
        val client = AuthenticatedGoreeCloudSearchHttpClient(exchange)

        val inconsistent = runCatching { client.queryReadiness() }.exceptionOrNull()
        assertTrue(inconsistent is GoreeCloudSearchTransportException)
        assertEquals("GoreeCloud Search readiness response is inconsistent", inconsistent?.message)

        exchange.response = jsonResponse(
            """{"status":"ready","service":"unexpected-service","version":"0.1.0.dev14","lifecycle":"development"}"""
        )
        val unexpected = runCatching { client.queryReadiness() }.exceptionOrNull()
        assertTrue(unexpected is GoreeCloudSearchTransportException)
        assertEquals(
            "GoreeCloud Search readiness response identifies an unexpected service",
            unexpected?.message,
        )
    }

    @Test
    fun authenticatedSearchUsesPostBodyAndSeparateAuthorityHeaders() = runTest {
        val exchange = RecordingExchange(
            response = jsonResponse(
                """
                {
                  "apiVersion":"1",
                  "query":"goreecloud",
                  "category":"general",
                  "results":[{
                    "title":"GoreeCloud",
                    "url":"https://example.com/goreecloud",
                    "snippet":"result",
                    "searchScore":4200
                  }],
                  "degraded":false
                }
                """.trimIndent(),
            ),
        )
        val client = AuthenticatedGoreeCloudSearchHttpClient(exchange)

        val response = client.search(
            GoreeCloudSearchRequest(
                query = "goreecloud",
                category = "general",
                limit = 5,
                privacyCapabilityReference = "psc_test_reference",
                requesterBearerCredential = "identity_test_token",
            ),
        )

        assertEquals("1", response.apiVersion)
        assertEquals("goreecloud", response.query)
        assertEquals(1, response.results.size)
        val request = exchange.requests.single()
        assertEquals("POST", request.method)
        assertEquals("https://search.goreecloud.com/api/v1/search", request.url.toString())
        assertEquals(null, request.url.query)
        assertEquals("psc_test_reference", request.headers["X-GoreeCloud-Privacy-Capability"])
        assertEquals("Bearer identity_test_token", request.headers["Authorization"])
        val body = checkNotNull(request.body).toString(Charsets.UTF_8)
        assertTrue(body.contains("\"query\":\"goreecloud\""))
        assertTrue(body.contains("\"category\":\"general\""))
        assertTrue(body.contains("\"limit\":5"))
        assertFalse(body.contains("psc_test_reference"))
        assertFalse(body.contains("identity_test_token"))
    }

    @Test
    fun missingPrivacyOrIdentityAuthorityFailsBeforeNetworkExchange() = runTest {
        val exchange = RecordingExchange(response = jsonResponse("{}"))
        val client = AuthenticatedGoreeCloudSearchHttpClient(exchange)

        val missingPrivacy = runCatching {
            client.search(
                GoreeCloudSearchRequest(
                    query = "goreecloud",
                    limit = 1,
                    requesterBearerCredential = "identity_test_token",
                ),
            )
        }.exceptionOrNull()
        val missingIdentity = runCatching {
            client.search(
                GoreeCloudSearchRequest(
                    query = "goreecloud",
                    limit = 1,
                    privacyCapabilityReference = "psc_test_reference",
                ),
            )
        }.exceptionOrNull()

        assertTrue(missingPrivacy is GoreeCloudSearchTransportException)
        assertTrue(missingIdentity is GoreeCloudSearchTransportException)
        assertTrue(exchange.requests.isEmpty())
    }

    @Test
    fun transportRejectsNonSuccessWithoutSurfacingResponseBody() = runTest {
        val exchange = RecordingExchange(
            response = GoreeCloudSearchHttpResponse(
                status = 401,
                contentType = "application/json",
                body = """{"error":"authorization_required","secret":"do-not-surface"}""".toByteArray(),
            ),
        )
        val client = AuthenticatedGoreeCloudSearchHttpClient(exchange)

        val failure = runCatching {
            client.search(
                GoreeCloudSearchRequest(
                    query = "goreecloud",
                    limit = 1,
                    privacyCapabilityReference = "psc_test_reference",
                    requesterBearerCredential = "identity_test_token",
                ),
            )
        }.exceptionOrNull()

        assertTrue(failure is GoreeCloudSearchTransportException)
        assertEquals("GoreeCloud Search query failed with HTTP 401", failure?.message)
        assertFalse(failure?.message.orEmpty().contains("do-not-surface"))
    }

    @Test
    fun requestAndResponseDebugRenderingRedactsSensitiveWireData() {
        val request = GoreeCloudSearchHttpRequest(
            method = "POST",
            url = java.net.URL("https://search.goreecloud.com/api/v1/search"),
            headers = mapOf("Authorization" to "Bearer secret"),
            body = "private query".toByteArray(),
        )
        val response = GoreeCloudSearchHttpResponse(
            status = 200,
            contentType = "application/json",
            body = "private response".toByteArray(),
        )

        assertFalse(request.toString().contains("secret"))
        assertFalse(request.toString().contains("private query"))
        assertFalse(response.toString().contains("private response"))
    }

    private class RecordingExchange(
        var response: GoreeCloudSearchHttpResponse,
    ) : GoreeCloudSearchHttpExchange {
        val requests = mutableListOf<GoreeCloudSearchHttpRequest>()

        override suspend fun execute(request: GoreeCloudSearchHttpRequest): GoreeCloudSearchHttpResponse {
            requests += request
            return response
        }
    }

    private fun jsonResponse(body: String): GoreeCloudSearchHttpResponse =
        GoreeCloudSearchHttpResponse(
            status = 200,
            contentType = "application/json; charset=utf-8",
            body = body.toByteArray(Charsets.UTF_8),
        )
}
