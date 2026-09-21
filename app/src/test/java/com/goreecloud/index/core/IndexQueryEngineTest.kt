package com.goreecloud.index.core

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class IndexQueryEngineTest {
    @Test
    fun providerFailureIsReportedWithoutSuppressingHealthyResults() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val healthy = provider("healthy", "Healthy") {
            listOf(result("one", "healthy", "Calendar", 700))
        }
        val failing = provider("failing", "Failing") {
            error("provider unavailable")
        }

        val snapshot = IndexQueryEngine(listOf(failing, healthy), dispatcher).search(
            rawQuery = "cal",
            executionContext = contextFor("failing", "healthy"),
        )

        assertEquals(1, snapshot.results.size)
        assertEquals("Calendar", snapshot.results.single().title)
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.FAILED, snapshot.providerIssues.single().kind)
        assertEquals("failing", snapshot.providerIssues.single().providerId)
        assertEquals("Failing", snapshot.providerIssues.single().providerName)
    }

    @Test
    fun providerTimeoutIsReportedWithoutSuppressingHealthyResults() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val healthy = provider("healthy", "Healthy") {
            listOf(result("one", "healthy", "Calendar", 700))
        }
        val slow = provider(
            id = "slow",
            name = "Slow provider",
            providerTimeoutMillis = 100L,
        ) {
            delay(1_000L)
            listOf(result("late", "slow", "Late result", 900))
        }

        val snapshot = IndexQueryEngine(listOf(slow, healthy), dispatcher).search(
            rawQuery = "cal",
            executionContext = contextFor("slow", "healthy"),
        )

        assertEquals(listOf("Calendar"), snapshot.results.map { it.title })
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.TIMED_OUT, snapshot.providerIssues.single().kind)
        assertEquals("slow", snapshot.providerIssues.single().providerId)
    }

    @Test
    fun providersExecuteConcurrently() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val first = provider("first", "First", providerTimeoutMillis = 2_000L) {
            delay(1_000L)
            listOf(result("one", "first", "One", 500))
        }
        val second = provider("second", "Second", providerTimeoutMillis = 2_000L) {
            delay(1_000L)
            listOf(result("two", "second", "Two", 400))
        }

        val snapshot = IndexQueryEngine(listOf(first, second), dispatcher).search(
            rawQuery = "",
            executionContext = contextFor("first", "second"),
        )

        assertEquals(1_000L, testScheduler.currentTime)
        assertEquals(2, snapshot.results.size)
    }

    @Test
    fun cancellationPropagatesInsteadOfBecomingProviderIssue() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var providerCancelled = false
        val cancelableProvider = provider(
            id = "cancel",
            name = "Cancelable",
            providerTimeoutMillis = 5_000L,
        ) {
            try {
                awaitCancellation()
            } finally {
                providerCancelled = true
            }
        }
        val engine = IndexQueryEngine(listOf(cancelableProvider), dispatcher)

        val searchJob = launch {
            engine.search(
                rawQuery = "query",
                executionContext = contextFor("cancel"),
            )
        }
        runCurrent()
        searchJob.cancelAndJoin()

        assertTrue(providerCancelled)
        assertTrue(searchJob.isCancelled)
    }

    @Test
    fun localOnlyExecutionContextFailsClosedForRemoteProviders() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var localInvoked = false
        var remoteInvoked = false
        val local = provider("local", "Local") {
            localInvoked = true
            listOf(result("local", "local", "Local result", 500))
        }
        val remote = provider(
            id = "remote",
            name = "Remote",
            location = IndexProcessingLocation.REMOTE,
        ) {
            remoteInvoked = true
            listOf(result("remote", "remote", "Remote result", 900))
        }

        val snapshot = IndexQueryEngine(listOf(local, remote), dispatcher).search(
            rawQuery = "",
            executionContext = IndexExecutionContext(
                allowedProviderIds = setOf("local", "remote"),
                localOnly = true,
            ),
        )

        assertTrue(localInvoked)
        assertFalse(remoteInvoked)
        assertEquals(listOf("Local result"), snapshot.results.map { it.title })
        assertTrue(snapshot.providerIssues.isEmpty())
    }

    @Test
    fun disallowedProviderIsNotDispatched() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var invoked = false
        val blockedProvider = provider("blocked", "Blocked") {
            invoked = true
            listOf(result("one", "blocked", "Should not appear", 900))
        }

        val snapshot = IndexQueryEngine(listOf(blockedProvider), dispatcher).search(
            rawQuery = "",
            executionContext = IndexExecutionContext(
                allowedProviderIds = emptySet(),
                localOnly = true,
            ),
        )

        assertFalse(invoked)
        assertTrue(snapshot.results.isEmpty())
        assertTrue(snapshot.providerIssues.isEmpty())
    }

    @Test
    fun incompatibleProviderContractFailsClosedBeforeDispatch() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var invoked = false
        val incompatible = provider(
            id = "future",
            name = "Future provider",
            contractVersion = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION + 1,
        ) {
            invoked = true
            listOf(result("one", "future", "Should not appear", 900))
        }

        val snapshot = IndexQueryEngine(listOf(incompatible), dispatcher).search(
            rawQuery = "future",
            executionContext = contextFor("future"),
        )

        assertFalse(invoked)
        assertTrue(snapshot.results.isEmpty())
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.INCOMPATIBLE_CONTRACT, snapshot.providerIssues.single().kind)
        assertEquals("future", snapshot.providerIssues.single().providerId)
    }

    @Test
    fun authorityGatedProviderIsNotDispatchedWithoutEvidence() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var invoked = false
        val contacts = provider(
            id = "contacts",
            name = "Contacts",
            requirements = CONTACT_REQUIREMENTS,
        ) {
            invoked = true
            listOf(result("one", "contacts", "Ada Lovelace", 900))
        }

        val snapshot = IndexQueryEngine(listOf(contacts), dispatcher).search(
            rawQuery = "ada",
            executionContext = contextFor("contacts"),
        )

        assertFalse(invoked)
        assertTrue(snapshot.results.isEmpty())
        assertEquals(1, snapshot.providerIssues.size)
        assertEquals(IndexProviderIssueKind.AUTHORIZATION_REQUIRED, snapshot.providerIssues.single().kind)
    }

    @Test
    fun authorityGatedProviderRunsWithUnconstrainedEvidence() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var invoked = false
        val contacts = provider(
            id = "contacts",
            name = "Contacts",
            requirements = CONTACT_REQUIREMENTS,
        ) {
            invoked = true
            listOf(result("one", "contacts", "Ada Lovelace", 900))
        }
        val authority = IndexProviderAuthority(
            androidPermissionGranted = true,
            privacyShield = IndexAuthorityEvidence(IndexAuthorityOutcome.ALLOW, "privacy-decision-1"),
            identity = IndexAuthorityEvidence(IndexAuthorityOutcome.ALLOW, "identity-authz-1"),
        )

        val snapshot = IndexQueryEngine(listOf(contacts), dispatcher).search(
            rawQuery = "ada",
            executionContext = IndexExecutionContext(
                allowedProviderIds = setOf("contacts"),
                providerAuthorities = mapOf("contacts" to authority),
            ),
        )

        assertTrue(invoked)
        assertEquals(listOf("Ada Lovelace"), snapshot.results.map { it.title })
        assertTrue(snapshot.providerIssues.isEmpty())
    }

    @Test
    fun constrainedAuthorityFailsClosedUntilObligationsAreSupported() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var invoked = false
        val contacts = provider(
            id = "contacts",
            name = "Contacts",
            requirements = CONTACT_REQUIREMENTS,
        ) {
            invoked = true
            emptyList()
        }
        val authority = IndexProviderAuthority(
            androidPermissionGranted = true,
            privacyShield = IndexAuthorityEvidence(
                IndexAuthorityOutcome.ALLOW_WITH_CONSTRAINTS,
                "privacy-decision-2",
            ),
            identity = IndexAuthorityEvidence(IndexAuthorityOutcome.ALLOW, "identity-authz-2"),
        )

        val snapshot = IndexQueryEngine(listOf(contacts), dispatcher).search(
            rawQuery = "ada",
            executionContext = IndexExecutionContext(
                allowedProviderIds = setOf("contacts"),
                providerAuthorities = mapOf("contacts" to authority),
            ),
        )

        assertFalse(invoked)
        assertEquals(IndexProviderIssueKind.AUTHORIZATION_REQUIRED, snapshot.providerIssues.single().kind)
    }

    @Test
    fun nonBrowsingProviderDoesNotRequestAuthorityForBlankQuery() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        var invoked = false
        val contacts = provider(
            id = "contacts",
            name = "Contacts",
            requirements = CONTACT_REQUIREMENTS,
            emptyQuery = false,
        ) {
            invoked = true
            emptyList()
        }

        val snapshot = IndexQueryEngine(listOf(contacts), dispatcher).search(
            rawQuery = "",
            executionContext = contextFor("contacts"),
        )

        assertFalse(invoked)
        assertTrue(snapshot.results.isEmpty())
        assertTrue(snapshot.providerIssues.isEmpty())
    }

    @Test
    fun resultsAreRankedBeforeProviderScopedDuplicatesAreCollapsed() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val appsProvider = provider("apps", "Applications") {
            listOf(
                result("same", "apps", "Beta lower", 400),
                result("same", "apps", "Beta best", 900),
                result("alpha", "apps", "Alpha", 800),
            )
        }

        val snapshot = IndexQueryEngine(listOf(appsProvider), dispatcher).search(
            rawQuery = "a",
            executionContext = contextFor("apps"),
        )

        assertEquals(listOf("Beta best", "Alpha"), snapshot.results.map { it.title })
        assertTrue(snapshot.providerIssues.isEmpty())
    }

    @Test
    fun crossProviderRankingUsesIndexNormalizedRelevanceInsteadOfProviderScoreScale() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val exact = provider("exact", "Exact") {
            listOf(result("exact", "exact", "Calendar", 1))
        }
        val inflated = provider("inflated", "Inflated") {
            listOf(result("weak", "inflated", "Notes about calendar", Int.MAX_VALUE))
        }

        val snapshot = IndexQueryEngine(listOf(inflated, exact), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("inflated", "exact"),
        )

        assertEquals(
            listOf("Calendar", "Notes about calendar"),
            snapshot.results.map { it.title },
        )
    }

    @Test
    fun sameProviderRankingRetainsProviderLocalScore() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val appsProvider = provider("apps", "Applications") {
            listOf(
                result("low", "apps", "Calendar alpha", 1),
                result("high", "apps", "Calendar beta", 9_999),
            )
        }

        val snapshot = IndexQueryEngine(listOf(appsProvider), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("apps"),
        )

        assertEquals(
            listOf("Calendar beta", "Calendar alpha"),
            snapshot.results.map { it.title },
        )
    }

    @Test
    fun crossProviderNormalizedTieUsesStableIdentityNotProviderScore() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val alpha = provider("alpha", "Alpha") {
            listOf(result("one", "alpha", "Calendar", 1))
        }
        val zulu = provider("zulu", "Zulu") {
            listOf(result("two", "zulu", "Calendar", Int.MAX_VALUE))
        }

        val snapshot = IndexQueryEngine(listOf(zulu, alpha), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("zulu", "alpha"),
        )

        assertEquals(listOf("alpha", "zulu"), snapshot.results.map { it.providerId })
    }

    @Test
    fun canonicallyEquivalentCrossProviderTieFallsThroughToStableProviderIdentity() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val zProvider = provider("z-provider", "Z") {
            listOf(result("one", "z-provider", "Cafe\u0301", 700))
        }
        val aProvider = provider("a-provider", "A") {
            listOf(result("two", "a-provider", "Café", 700))
        }

        val snapshot = IndexQueryEngine(listOf(zProvider, aProvider), dispatcher).search(
            rawQuery = "cafe",
            executionContext = contextFor("z-provider", "a-provider"),
        )

        assertEquals(listOf("a-provider", "z-provider"), snapshot.results.map { it.providerId })
    }

    @Test
    fun healthyProviderWinsEqualCrossProviderRelevanceAgainstDegradedProvider() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val degraded = statusProvider("a-degraded", "Degraded") {
            IndexProviderResponse(
                results = listOf(result("degraded", "a-degraded", "Calendar", Int.MAX_VALUE)),
                degraded = true,
            )
        }
        val healthy = statusProvider("z-healthy", "Healthy") {
            IndexProviderResponse(
                results = listOf(result("healthy", "z-healthy", "Calendar", 1)),
            )
        }

        val snapshot = IndexQueryEngine(listOf(degraded, healthy), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("a-degraded", "z-healthy"),
        )

        assertEquals(listOf("z-healthy", "a-degraded"), snapshot.results.map { it.providerId })
        assertEquals(IndexProviderIssueKind.DEGRADED, snapshot.providerIssues.single().kind)
    }

    @Test
    fun strongerDegradedMatchStillOutranksWeakerHealthyMatch() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val degraded = statusProvider("degraded", "Degraded") {
            IndexProviderResponse(
                results = listOf(result("exact", "degraded", "Calendar", 1)),
                degraded = true,
            )
        }
        val healthy = statusProvider("healthy", "Healthy") {
            IndexProviderResponse(
                results = listOf(result("weak", "healthy", "Notes about calendar", Int.MAX_VALUE)),
            )
        }

        val snapshot = IndexQueryEngine(listOf(healthy, degraded), dispatcher).search(
            rawQuery = "calendar",
            executionContext = contextFor("healthy", "degraded"),
        )

        assertEquals(listOf("degraded", "healthy"), snapshot.results.map { it.providerId })
        assertEquals(IndexProviderIssueKind.DEGRADED, snapshot.providerIssues.single().kind)
    }

    @Test
    fun resultLimitRemainsBounded() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val appsProvider = provider("apps", "Applications") {
            (1..150).map { index ->
                result(
                    id = index.toString(),
                    providerId = "apps",
                    title = "App $index",
                    score = 1_000 - index,
                )
            }
        }

        val snapshot = IndexQueryEngine(listOf(appsProvider), dispatcher).search(
            rawQuery = "",
            executionContext = contextFor("apps"),
            maxResults = 500,
        )

        assertEquals(100, snapshot.results.size)
    }

    @Test
    fun textMatcherPrioritizesExactAndPrefixMatches() {
        val exact = IndexTextMatcher.score("maps", "Maps", "com.example.maps")
        val prefix = IndexTextMatcher.score("map", "Maps", "com.example.maps")
        val secondary = IndexTextMatcher.score("example", "Maps", "com.example.maps")

        assertTrue(exact!! > prefix!!)
        assertTrue(prefix > secondary!!)
        assertEquals(null, IndexTextMatcher.score("calendar", "Maps", "com.example.maps"))
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
        name: String,
        location: IndexProcessingLocation = IndexProcessingLocation.LOCAL,
        providerTimeoutMillis: Long = 1_000L,
        contractVersion: Int = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION,
        requirements: Set<IndexAuthorityRequirement> = emptySet(),
        emptyQuery: Boolean = true,
        block: suspend (IndexQuery) -> List<IndexResult>,
    ) = object : IndexProvider {
        override val providerId: String = id
        override val displayName: String = name
        override val processingLocation: IndexProcessingLocation = location
        override val timeoutMillis: Long = providerTimeoutMillis
        override val contractVersion: Int = contractVersion
        override val authorityRequirements: Set<IndexAuthorityRequirement> = requirements
        override val supportsEmptyQuery: Boolean = emptyQuery
        override suspend fun search(query: IndexQuery): List<IndexResult> = block(query)
    }

    private fun statusProvider(
        id: String,
        name: String,
        location: IndexProcessingLocation = IndexProcessingLocation.LOCAL,
        providerTimeoutMillis: Long = 1_000L,
        block: suspend (IndexQuery) -> IndexProviderResponse,
    ) = object : IndexStatusAwareProvider {
        override val providerId: String = id
        override val displayName: String = name
        override val processingLocation: IndexProcessingLocation = location
        override val timeoutMillis: Long = providerTimeoutMillis
        override val contractVersion: Int = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION
        override suspend fun searchWithStatus(query: IndexQuery): IndexProviderResponse = block(query)
    }

    private companion object {
        val CONTACT_REQUIREMENTS = setOf(
            IndexAuthorityRequirement.ANDROID_RUNTIME_PERMISSION,
            IndexAuthorityRequirement.PRIVACY_SHIELD,
            IndexAuthorityRequirement.GOREECLOUD_IDENTITY,
        )
    }
}
