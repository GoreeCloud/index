package com.goreecloud.index.provider.search

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GoreeCloudSearchSensitiveRenderingTest {
    @Test
    fun searchRequestDebugRenderingRedactsQueryAndCapabilityReference() {
        val query = "private medical research query"
        val reference = "psc_sensitive_authority_reference"
        val rendered = GoreeCloudSearchRequest(
            query = query,
            limit = 5,
            privacyCapabilityReference = reference,
        ).toString()

        assertFalse(rendered.contains(query))
        assertFalse(rendered.contains(reference))
        assertTrue(rendered.contains("query=<redacted>"))
        assertTrue(rendered.contains("privacyCapabilityReference=<redacted>"))
    }

    @Test
    fun privacyAuthorizationDebugRenderingRedactsCapabilityReference() {
        val reference = "psc_sensitive_authority_reference"
        val rendered = GoreeCloudSearchPrivacyAuthorization(reference).toString()

        assertFalse(rendered.contains(reference))
        assertTrue(rendered.contains("capabilityTokenReference=<redacted>"))
    }

    @Test
    fun searchResultDebugRenderingRedactsContentAndUrl() {
        val title = "Sensitive result title"
        val url = "https://example.com/private-result"
        val snippet = "Sensitive result summary"
        val rendered = GoreeCloudSearchResult(
            title = title,
            url = url,
            snippet = snippet,
            searchScore = 42,
        ).toString()

        assertFalse(rendered.contains(title))
        assertFalse(rendered.contains(url))
        assertFalse(rendered.contains(snippet))
        assertTrue(rendered.contains("title=<redacted>"))
        assertTrue(rendered.contains("url=<redacted>"))
        assertTrue(rendered.contains("snippet=<redacted>"))
        assertTrue(rendered.contains("searchScore=42"))
    }

    @Test
    fun searchResponseDebugRenderingRedactsQueryAndNestedResults() {
        val query = "private medical research query"
        val title = "Sensitive result title"
        val url = "https://example.com/private-result"
        val rendered = GoreeCloudSearchResponse(
            apiVersion = GOREECLOUD_SEARCH_API_VERSION,
            query = query,
            category = "general",
            results = listOf(
                GoreeCloudSearchResult(
                    title = title,
                    url = url,
                    snippet = "Sensitive result summary",
                ),
            ),
            degraded = false,
        ).toString()

        assertFalse(rendered.contains(query))
        assertFalse(rendered.contains(title))
        assertFalse(rendered.contains(url))
        assertTrue(rendered.contains("query=<redacted>"))
        assertTrue(rendered.contains("resultCount=1"))
    }
}
