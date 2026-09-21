package com.goreecloud.index.core

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class IndexLocalFirstRankingTest {
    @Test
    fun localProviderWinsOnlyAfterCrossProviderRelevanceAndHealthTie() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val remote = provider(
            id = "a-remote",
            location = IndexProcessingLocation.REMOTE,
        ) {
            listOf(result("remote", "a-remote", "Calendar", Int.MAX_VALUE))
        }
        val local = provider(
            id = "z-local",
            location = IndexProcessingLocation.LOCAL,
        ) {
            listOf(result("local", "z-local", "Calendar", 1))
        }

        val snapshot = IndexQueryEngine(listOf(remote, local), dispatcher).search(
            rawQuery = "calendar",
            executionContext = remoteEnabledContext("a-remote", "z-local"),
        )

        assertEquals(listOf("z-local", "a-remote"), snapshot.results.map { it.providerId })
    }

    @Test
    fun strongerRemoteMatchStillOutranksWeakerLocalMatch() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val remote = provider(
            id = "remote",
            location = IndexProcessingLocation.REMOTE,
        ) {
            listOf(result("remote", "remote", "Calendar", 1))
        }
        val local = provider(
            id = "local",
            location = IndexProcessingLocation.LOCAL,
        ) {
            listOf(result("local", "local", "Notes about calendar", Int.MAX_VALUE))
        }

        val snapshot = IndexQueryEngine(listOf(local, remote), dispatcher).search(
            rawQuery = "calendar",
            executionContext = remoteEnabledContext("local", "remote"),
        )

        assertEquals(listOf("remote", "local"), snapshot.results.map { it.providerId })
    }

    @Test
    fun mixedProviderRanksBetweenLocalAndRemoteOnFullTie() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val remote = provider("remote", IndexProcessingLocation.REMOTE) {
            listOf(result("remote", "remote", "Calendar", 100))
        }
        val mixed = provider("mixed", IndexProcessingLocation.MIXED) {
            listOf(result("mixed", "mixed", "Calendar", 100))
        }
        val local = provider("local", IndexProcessingLocation.LOCAL) {
            listOf(result("local", "local", "Calendar", 100))
        }

        val snapshot = IndexQueryEngine(listOf(remote, mixed, local), dispatcher).search(
            rawQuery = "calendar",
            executionContext = remoteEnabledContext("remote", "mixed", "local"),
        )

        assertEquals(listOf("local", "mixed", "remote"), snapshot.results.map { it.providerId })
    }

    private fun remoteEnabledContext(vararg providerIds: String) = IndexExecutionContext(
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
        location: IndexProcessingLocation,
        block: suspend (IndexQuery) -> List<IndexResult>,
    ) = object : IndexProvider {
        override val providerId: String = id
        override val displayName: String = id
        override val processingLocation: IndexProcessingLocation = location
        override val timeoutMillis: Long = 1_000L
        override val contractVersion: Int = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION
        override suspend fun search(query: IndexQuery): List<IndexResult> = block(query)
    }
}
