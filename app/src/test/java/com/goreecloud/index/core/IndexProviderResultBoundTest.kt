package com.goreecloud.index.core

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class IndexProviderResultBoundTest {
    @Test
    fun providerReturningMoreThanRequestedIsBoundedAndReportedInvalid() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = provider("overflow") {
            (1..8).map { index ->
                result(
                    id = index.toString(),
                    providerId = "overflow",
                    title = "Calendar $index",
                    score = 100 - index,
                )
            }
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("overflow"),
            maxResults = 3,
        )

        assertEquals(3, snapshot.results.size)
        assertEquals(IndexProviderIssueKind.INVALID_RESULT, snapshot.providerIssues.single().kind)
    }

    @Test
    fun overflowBoundKeepsStrongestProviderLocalResultsRatherThanResponseOrder() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = provider("ranked") {
            listOf(
                result("low-a", "ranked", "Calendar low A", 1),
                result("low-b", "ranked", "Calendar low B", 2),
                result("best", "ranked", "Calendar best", 1_000),
                result("second", "ranked", "Calendar second", 900),
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("ranked"),
            maxResults = 2,
        )

        assertEquals(listOf("best", "second"), snapshot.results.map { it.id })
        assertEquals(IndexProviderIssueKind.INVALID_RESULT, snapshot.providerIssues.single().kind)
    }

    @Test
    fun providerScopedDuplicatesDoNotConsumeTheBoundBeforeDeduplication() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = provider("duplicates") {
            listOf(
                result("same", "duplicates", "Calendar weak duplicate", 1),
                result("same", "duplicates", "Calendar best duplicate", 1_000),
                result("unique", "duplicates", "Calendar unique", 900),
                result("extra", "duplicates", "Calendar extra", 800),
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("duplicates"),
            maxResults = 2,
        )

        assertEquals(listOf("same", "unique"), snapshot.results.map { it.id })
        assertEquals("Calendar best duplicate", snapshot.results.first().title)
        assertEquals(IndexProviderIssueKind.INVALID_RESULT, snapshot.providerIssues.single().kind)
    }

    @Test
    fun overflowInvalidResultPrecedesProviderDegradedSignal() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val provider = statusProvider("degraded-overflow") {
            IndexProviderResponse(
                results = listOf(
                    result("one", "degraded-overflow", "Calendar one", 100),
                    result("two", "degraded-overflow", "Calendar two", 90),
                    result("three", "degraded-overflow", "Calendar three", 80),
                ),
                degraded = true,
            )
        }

        val snapshot = IndexQueryEngine(listOf(provider), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("degraded-overflow"),
            maxResults = 2,
        )

        assertEquals(2, snapshot.results.size)
        assertEquals(IndexProviderIssueKind.INVALID_RESULT, snapshot.providerIssues.single().kind)
    }

    private fun contextFor(vararg providerIds: String) = IndexExecutionContext(
        allowedProviderIds = providerIds.toSet(),
        localOnly = true,
    )

    private fun result(
        id: String,
        providerId: String,
        title: String,
        score: Int,
    ) = IndexResult(
        id = id,
        providerId = providerId,
        type = IndexResultType.APP,
        title = title,
        score = score,
    )

    private fun provider(
        id: String,
        block: suspend (IndexQuery) -> List<IndexResult>,
    ) = object : IndexProvider {
        override val providerId: String = id
        override val displayName: String = id
        override val processingLocation = IndexProcessingLocation.LOCAL
        override val timeoutMillis: Long = 1_000L
        override val contractVersion: Int = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION
        override suspend fun search(query: IndexQuery): List<IndexResult> = block(query)
    }

    private fun statusProvider(
        id: String,
        block: suspend (IndexQuery) -> IndexProviderResponse,
    ) = object : IndexStatusAwareProvider {
        override val providerId: String = id
        override val displayName: String = id
        override val processingLocation = IndexProcessingLocation.LOCAL
        override val timeoutMillis: Long = 1_000L
        override val contractVersion: Int = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION
        override suspend fun searchWithStatus(query: IndexQuery): IndexProviderResponse = block(query)
    }
}
