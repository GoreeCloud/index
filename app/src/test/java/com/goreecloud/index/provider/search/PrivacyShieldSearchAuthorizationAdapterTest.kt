package com.goreecloud.index.provider.search

import java.time.Instant
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PrivacyShieldSearchAuthorizationAdapterTest {
    private val now = Instant.parse("2026-09-14T12:00:00Z")
    private val request = GoreeCloudSearchPrivacyAuthorizationRequest(
        requestId = "index-search-request-123",
    )

    @Test
    fun canonicalConstrainedDecisionReturnsCapabilityReference() = runTest {
        var observedRequest: GoreeCloudSearchPrivacyAuthorizationRequest? = null
        val adapter = PrivacyShieldSearchAuthorizationAdapter(
            decisionClient = PrivacyShieldDecisionClient { submittedRequest ->
                observedRequest = submittedRequest
                allowedDecision(submittedRequest.requestId)
            },
            clock = { now },
        )

        val authorization = adapter.authorize(request)

        assertEquals("index-search-request-123", observedRequest?.requestId)
        assertEquals("search.query", observedRequest?.operation)
        assertEquals("private_goreecloud", observedRequest?.processingZone)
        assertEquals("https://search.goreecloud.com", observedRequest?.destination)
        assertEquals("none", observedRequest?.retentionMode)
        assertEquals("psc_test-capability-123", authorization.capabilityTokenReference)
    }

    @Test
    fun decisionForDifferentRequestFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision("different-request"),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision does not match the authorization request",
            failure?.message,
        )
    }

    @Test
    fun blankRequestIdFailsBeforeDecisionAcquisition() = runTest {
        var decisionCalls = 0
        val adapter = PrivacyShieldSearchAuthorizationAdapter(
            decisionClient = PrivacyShieldDecisionClient {
                decisionCalls++
                allowedDecision(it.requestId)
            },
            clock = { now },
        )

        val failure = runCatching {
            adapter.authorize(request.copy(requestId = "   "))
        }.exceptionOrNull()

        assertTrue(failure is IllegalArgumentException)
        assertEquals(
            "Privacy Shield Search authorization request is missing a request identifier",
            failure?.message,
        )
        assertEquals(0, decisionCalls)
    }

    @Test
    fun unconstrainedAllowFailsClosedForPrivateSearch() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(outcome = "ALLOW"),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision does not match the required constrained outcome",
            failure?.message,
        )
    }

    @Test
    fun unknownConstraintObligationFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(
                obligations = PRIVACY_SHIELD_SEARCH_REQUIRED_OBLIGATIONS + "redact-sensitive-terms",
            ),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision contains an unsupported obligation set",
            failure?.message,
        )
    }

    @Test
    fun missingCanonicalConstraintObligationFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(
                obligations = PRIVACY_SHIELD_SEARCH_REQUIRED_OBLIGATIONS - "enforce_processing_zone",
            ),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision contains an unsupported obligation set",
            failure?.message,
        )
    }

    @Test
    fun wrongDestinationFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(permittedDestinations = setOf("https://example.com")),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision does not permit the GoreeCloud Search destination",
            failure?.message,
        )
    }

    @Test
    fun expiredDecisionFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(expiresAt = "2026-09-14T11:59:59Z"),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals("Privacy Shield Search decision is expired", failure?.message)
    }

    @Test
    fun missingCapabilityReferenceFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(capabilityTokenReference = null),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision is missing a canonical capability-token reference",
            failure?.message,
        )
    }

    @Test
    fun nonCanonicalCapabilityReferenceFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(capabilityTokenReference = "privacy-shield:capability:123"),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision is missing a canonical capability-token reference",
            failure?.message,
        )
    }

    @Test
    fun capabilityReferenceWithWhitespaceFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(capabilityTokenReference = "psc_test capability"),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision is missing a canonical capability-token reference",
            failure?.message,
        )
    }

    @Test
    fun capabilityReferenceWithControlCharacterFailsClosed() = runTest {
        val adapter = adapter(
            allowedDecision(request.requestId).copy(capabilityTokenReference = "psc_test\u0000capability"),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision is missing a canonical capability-token reference",
            failure?.message,
        )
    }

    @Test
    fun oversizedCapabilityReferenceFailsClosed() = runTest {
        val oversized = "psc_" + "a".repeat(PRIVACY_SHIELD_SEARCH_CAPABILITY_REFERENCE_MAX_LENGTH)
        val adapter = adapter(
            allowedDecision(request.requestId).copy(capabilityTokenReference = oversized),
        )

        val failure = runCatching {
            adapter.authorize(request)
        }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
        assertEquals(
            "Privacy Shield Search decision is missing a canonical capability-token reference",
            failure?.message,
        )
    }

    private fun adapter(decision: PrivacyShieldSearchDecision) =
        PrivacyShieldSearchAuthorizationAdapter(
            decisionClient = PrivacyShieldDecisionClient { decision },
            clock = { now },
        )

    private fun allowedDecision(requestId: String) = PrivacyShieldSearchDecision(
        decisionId = "privacy-shield:decision:123",
        requestId = requestId,
        outcome = PRIVACY_SHIELD_SEARCH_REQUIRED_OUTCOME,
        permittedOperations = setOf("search.query"),
        processingZone = "private_goreecloud",
        permittedDestinations = setOf("https://search.goreecloud.com"),
        retentionMode = "none",
        obligations = PRIVACY_SHIELD_SEARCH_REQUIRED_OBLIGATIONS,
        expiresAt = "2026-09-14T12:05:00Z",
        capabilityTokenReference = "psc_test-capability-123",
    )
}
