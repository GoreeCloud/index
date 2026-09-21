package com.goreecloud.index.core

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class IndexQueryNormalizerTest {
    @Test
    fun normalizeCollapsesWhitespaceAndCompatibilityCharacters() {
        assertEquals(
            "GoreeCloud Search",
            IndexQueryNormalizer.normalize("  ＧｏｒｅｅＣｌｏｕｄ\t  Search  "),
        )
    }

    @Test
    fun matcherUsesCompatibilityNormalization() {
        val exact = IndexTextMatcher.score("ＧｏｒｅｅＣｌｏｕｄ", "GoreeCloud")
        val prefix = IndexTextMatcher.score("ｓｅａｒ", "Search")

        assertEquals(1_000, exact)
        assertEquals(850, prefix)
    }

    @Test
    fun matcherTreatsCanonicalUnicodeFormsAsEquivalent() {
        val composed = "Café"
        val decomposed = "Cafe\u0301"

        assertEquals(1_000, IndexTextMatcher.score(decomposed, composed))
        assertEquals(1_000, IndexTextMatcher.score(composed, decomposed))
        assertEquals(
            540,
            IndexTextMatcher.score(
                query = "Re\u0301sume\u0301",
                title = "Documents",
                secondary = "Résumé",
            ),
        )
    }

    @Test
    fun unicodeSeparatorsPreserveWordPrefixRanking() {
        assertEquals(760, IndexTextMatcher.score("sett", "Privacy\u00A0Settings"))
        assertEquals(760, IndexTextMatcher.score("cal", "Work\u2003Calendar"))
    }

    @Test
    fun enginePassesCanonicalWhitespaceToProviders() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var observedQuery: IndexQuery? = null
        val provider = object : IndexProvider {
            override val providerId = "test"
            override val displayName = "Test"
            override val processingLocation = IndexProcessingLocation.LOCAL
            override val timeoutMillis = 1_000L
            override val contractVersion = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION

            override suspend fun search(query: IndexQuery): List<IndexResult> {
                observedQuery = query
                return emptyList()
            }
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "  calendar\t   event  ",
            executionContext = IndexExecutionContext(
                allowedProviderIds = setOf("test"),
            ),
        )

        assertEquals("calendar event", observedQuery?.text)
        assertTrue(snapshot.providerIssues.isEmpty())
    }
}
