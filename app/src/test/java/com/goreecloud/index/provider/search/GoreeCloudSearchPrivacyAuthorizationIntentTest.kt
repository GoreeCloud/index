package com.goreecloud.index.provider.search

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class GoreeCloudSearchPrivacyAuthorizationIntentTest {
    @Test
    fun intentContainsCanonicalPrivacyShieldDecisionFieldsAndRequestId() {
        val request = GoreeCloudSearchPrivacyAuthorizationRequest(
            requestId = "index-search-request-123",
        )

        assertEquals("index-search-request-123", request.requestId)
        assertEquals("goreecloud-index", request.requesterId)
        assertEquals("application", request.requesterType)
        assertEquals("goreecloud.search.query", request.resourceId)
        assertEquals("query_text", request.resourceClassification)
        assertEquals("search.query", request.operation)
        assertEquals("internet_search", request.purpose)
        assertEquals("private_goreecloud", request.processingZone)
        assertEquals("https://search.goreecloud.com", request.destination)
        assertEquals("none", request.retentionMode)
        assertFalse(request.externalDisclosure)
    }

    @Test
    fun defaultIntentGeneratesDistinctRequestIds() {
        val first = GoreeCloudSearchPrivacyAuthorizationRequest()
        val second = GoreeCloudSearchPrivacyAuthorizationRequest()

        assertFalse(first.requestId.isBlank())
        assertFalse(second.requestId.isBlank())
        assertFalse(first.requestId == second.requestId)
    }
}
