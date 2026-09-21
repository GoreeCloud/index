package com.goreecloud.index.core

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.last
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class IndexIncrementalSearchTest {
    @Test
    fun incrementalSearchEmitsInitialThenProviderCompletionSnapshots() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val local = provider(
            id = "local",
            location = IndexProcessingLocation.LOCAL,
        ) {
            delay(100L)
            listOf(result("local", "local", "Calendar", 1))
        }
        val remote = provider(
            id = "remote",
            location = IndexProcessingLocation.REMOTE,
        ) {
            delay(500L)
            listOf(result("remote", "remote", "Calendar", Int.MAX_VALUE))
        }

        val snapshots = IndexQueryEngine(listOf(local, remote), dispatcher)
            .searchIncrementally(
                rawQuery = "calendar",
                executionContext = contextFor("local", "remote"),
            )
            .toList()

        assertEquals(listOf(0, 1, 2), snapshots.map { it.results.size })
        assertEquals(listOf("local"), snapshots[1].results.map { it.providerId })
        assertEquals(listOf("local", "remote"), snapshots.last().results.map { it.providerId })
        assertEquals(500L, testScheduler.currentTime)
    }

    @Test
    fun strongerLateRemoteResultReRanksThroughSameDeterministicComposition() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val local = provider(
            id = "local",
            location = IndexProcessingLocation.LOCAL,
        ) {
            delay(100L)
            listOf(result("local", "local", "Notes about calendar", Int.MAX_VALUE))
        }
        val remote = provider(
            id = "remote",
            location = IndexProcessingLocation.REMOTE,
        ) {
            delay(500L)
            listOf(result("remote", "remote", "Calendar", 1))
        }

        val snapshots = IndexQueryEngine(listOf(local, remote), dispatcher)
            .searchIncrementally(
                rawQuery = "calendar",
                executionContext = contextFor("local", "remote"),
            )
            .toList()

        assertEquals(listOf("local"), snapshots[1].results.map { it.providerId })
        assertEquals(listOf("remote", "local"), snapshots.last().results.map { it.providerId })
    }

    @Test
    fun authorizationIssueIsEmittedWithoutDispatchingProtectedProvider() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var invoked = false
        val protected = provider(
            id = "protected",
            requirements = setOf(IndexAuthorityRequirement.PRIVACY_SHIELD),
        ) {
            invoked = true
            listOf(result("one", "protected", "Calendar", 100))
        }

        val snapshots = IndexQueryEngine(listOf(protected), dispatcher)
            .searchIncrementally(
                rawQuery = "calendar",
                executionContext = contextFor("protected"),
            )
            .toList()

        assertFalse(invoked)
        assertEquals(1, snapshots.size)
        assertTrue(snapshots.single().results.isEmpty())
        assertEquals(
            IndexProviderIssueKind.AUTHORIZATION_REQUIRED,
            snapshots.single().providerIssues.single().kind,
        )
    }

    @Test
    fun cancellingIncrementalCollectionCancelsOutstandingProviderWork() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var providerCancelled = false
        val provider = provider("cancel") {
            try {
                awaitCancellation()
            } finally {
                providerCancelled = true
            }
        }
        val engine = IndexQueryEngine(listOf(provider), dispatcher)

        val collection = launch {
            engine.searchIncrementally(
                rawQuery = "calendar",
                executionContext = contextFor("cancel"),
            ).collect()
        }

        runCurrent()
        collection.cancelAndJoin()

        assertTrue(collection.isCancelled)
        assertTrue(providerCancelled)
    }

    @Test
    fun oneShotSearchMatchesFinalIncrementalSnapshot() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val first = provider("first") {
            listOf(result("one", "first", "Calendar", 100))
        }
        val second = provider("second") {
            listOf(result("two", "second", "Calendar notes", 900))
        }
        val engine = IndexQueryEngine(listOf(first, second), dispatcher)
        val context = contextFor("first", "second")

        val finalIncremental = engine.searchIncrementally(
            rawQuery = "calendar",
            executionContext = context,
        ).last()
        val oneShot = engine.search(
            rawQuery = "calendar",
            executionContext = context,
        )

        assertEquals(finalIncremental, oneShot)
    }

    private fun contextFor(vararg providerIds: String) = IndexExecutionContext(
        allowedProviderIds = providerIds.toSet(),
        localOnly = false,
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
        location: IndexProcessingLocation = IndexProcessingLocation.LOCAL,
        requirements: Set<IndexAuthorityRequirement> = emptySet(),
        block: suspend (IndexQuery) -> List<IndexResult>,
    ) = object : IndexProvider {
        override val providerId: String = id
        override val displayName: String = id
        override val processingLocation: IndexProcessingLocation = location
        override val timeoutMillis: Long = 1_000L
        override val contractVersion: Int = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION
        override val authorityRequirements: Set<IndexAuthorityRequirement> = requirements
        override suspend fun search(query: IndexQuery): List<IndexResult> = block(query)
    }
}
