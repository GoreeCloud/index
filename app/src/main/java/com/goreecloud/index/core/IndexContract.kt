package com.goreecloud.index.core

import java.text.Normalizer
import java.util.Locale
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.last
import kotlinx.coroutines.launch
import kotlinx.coroutines.supervisorScope
import kotlinx.coroutines.withTimeout

object GoreeCloudIndexContract {
    const val ACTION_SEARCH = "com.goreecloud.index.action.SEARCH"
    const val EXTRA_QUERY = "com.goreecloud.index.extra.QUERY"
    const val PROVIDER_APPS = "goreecloud.index.provider.apps"
    const val PROVIDER_CONTACTS = "goreecloud.index.provider.contacts"
    const val PROVIDER_SETTINGS = "goreecloud.index.provider.settings"
    const val PROVIDER_SEARCH = "goreecloud.index.provider.search"
    const val PROVIDER_CONTRACT_VERSION = 1
}

enum class IndexResultType {
    APP,
    ACTION,
    CONTACT,
    FILE,
    CALENDAR,
    MEDIA,
    SETTING,
    GOREECLOUD,
    DEVICE,
    WEB,
}

enum class IndexProcessingLocation {
    LOCAL,
    REMOTE,
    MIXED,
}

enum class IndexProviderIssueKind {
    FAILED,
    TIMED_OUT,
    AUTHORIZATION_REQUIRED,
    INCOMPATIBLE_CONTRACT,
    DEGRADED,
    INVALID_RESULT,
}

sealed interface IndexAction {
    data class LaunchActivity(
        val packageName: String,
        val className: String,
    ) : IndexAction

    data class ViewContact(
        val uri: String,
    ) : IndexAction

    data class OpenSystemSetting(
        val action: String,
    ) : IndexAction

    data class OpenWeb(
        val uri: String,
    ) : IndexAction
}

data class IndexResult(
    val id: String,
    val providerId: String,
    val type: IndexResultType,
    val title: String,
    val subtitle: String? = null,
    /**
     * Provider-local ranking score. Index may use this to order results from the
     * same provider, but never compares the raw numeric value across providers.
     * Universal composition uses Index-owned normalized relevance instead.
     */
    val score: Int,
    val action: IndexAction? = null,
    /**
     * Optional zero-based ordering supplied by the owning provider after that
     * provider has completed its own ranking. Index uses this only to preserve
     * same-provider ordering when provider-local scores tie. It is never
     * compared across different providers and therefore cannot import a remote
     * provider's private ranking scale into universal composition.
     */
    val sourceOrdinal: Int? = null,
)

data class IndexQuery(
    val text: String,
    val maxResults: Int = 50,
)

data class IndexProviderResponse(
    val results: List<IndexResult> = emptyList(),
    val degraded: Boolean = false,
)

data class IndexExecutionContext(
    val allowedProviderIds: Set<String>,
    val localOnly: Boolean = true,
    val providerAuthorities: Map<String, IndexProviderAuthority> = emptyMap(),
) {
    fun isInScope(provider: IndexProvider): Boolean =
        provider.providerId in allowedProviderIds &&
            (!localOnly || provider.processingLocation == IndexProcessingLocation.LOCAL)

    fun allows(provider: IndexProvider): Boolean =
        isInScope(provider) &&
            providerAuthorities
                .getOrDefault(provider.providerId, IndexProviderAuthority())
                .satisfiesAll(provider.authorityRequirements)

    fun authorizationIssue(provider: IndexProvider): IndexProviderIssue? {
        if (!isInScope(provider)) return null
        if (provider.authorityRequirements.isEmpty()) return null

        val authority = providerAuthorities.getOrDefault(provider.providerId, IndexProviderAuthority())
        if (authority.satisfiesAll(provider.authorityRequirements)) return null

        return IndexProviderIssue(
            providerId = provider.providerId,
            providerName = provider.displayName,
            kind = IndexProviderIssueKind.AUTHORIZATION_REQUIRED,
        )
    }
}

data class IndexProviderIssue(
    val providerId: String,
    val providerName: String,
    val kind: IndexProviderIssueKind,
)

data class IndexSearchSnapshot(
    val results: List<IndexResult> = emptyList(),
    val providerIssues: List<IndexProviderIssue> = emptyList(),
)

interface IndexProvider {
    val providerId: String
    val displayName: String
    val processingLocation: IndexProcessingLocation
    val timeoutMillis: Long
    val contractVersion: Int
        get() = 0
    val authorityRequirements: Set<IndexAuthorityRequirement>
        get() = emptySet()
    val supportsEmptyQuery: Boolean
        get() = true
    suspend fun search(query: IndexQuery): List<IndexResult>
}

interface IndexStatusAwareProvider : IndexProvider {
    suspend fun searchWithStatus(query: IndexQuery): IndexProviderResponse

    override suspend fun search(query: IndexQuery): List<IndexResult> =
        searchWithStatus(query).results
}

private data class IndexProviderOutcome(
    val processingLocation: IndexProcessingLocation,
    val results: List<IndexResult> = emptyList(),
    val issue: IndexProviderIssue? = null,
)

private data class RankedIndexResult(
    val result: IndexResult,
    val normalizedRelevance: Int,
    val degradedProvider: Boolean,
    val processingLocation: IndexProcessingLocation,
    val normalizedTitle: String,
)

class IndexQueryEngine(
    private val providers: List<IndexProvider>,
    private val providerDispatcher: CoroutineDispatcher = Dispatchers.Default,
) {
    suspend fun search(
        rawQuery: String,
        executionContext: IndexExecutionContext,
        maxResults: Int = 50,
    ): IndexSearchSnapshot = searchIncrementally(
        rawQuery = rawQuery,
        executionContext = executionContext,
        maxResults = maxResults,
    ).last()

    /**
     * Emits an initial authority/compatibility snapshot and then a newly
     * composed snapshot each time one eligible provider completes. Provider
     * completion timing controls when an update is available, but never how
     * accumulated results are ranked: every emission is rebuilt through the
     * same deterministic relevance, health, processing-location, identity,
     * validation, fan-out, and deduplication rules used by the final result.
     *
     * Cancelling collection cancels this supervisor scope and therefore all
     * outstanding provider jobs. Provider cancellation remains cancellation;
     * it is not converted into a provider failure or timeout issue.
     */
    fun searchIncrementally(
        rawQuery: String,
        executionContext: IndexExecutionContext,
        maxResults: Int = 50,
    ): Flow<IndexSearchSnapshot> = flow {
        supervisorScope {
            val query = IndexQuery(
                text = IndexQueryNormalizer.normalize(rawQuery),
                maxResults = maxResults.coerceIn(1, MAX_RESULTS),
            )

            val applicableProviders = providers.filter { provider ->
                query.text.isNotEmpty() || provider.supportsEmptyQuery
            }
            val scopedProviders = applicableProviders.filter(executionContext::isInScope)
            val compatibilityIssues = scopedProviders.mapNotNull(::compatibilityIssue)
            val compatibleProviders = scopedProviders.filter(::isCompatibleProvider)
            val authorizationIssues = compatibleProviders
                .mapNotNull(executionContext::authorizationIssue)
            val eligibleProviders = compatibleProviders.filter(executionContext::allows)
            val completedOutcomes = MutableList<IndexProviderOutcome?>(eligibleProviders.size) { null }

            emit(
                composeSnapshot(
                    query = query,
                    compatibilityIssues = compatibilityIssues,
                    authorizationIssues = authorizationIssues,
                    outcomes = emptyList(),
                ),
            )

            if (eligibleProviders.isEmpty()) {
                return@supervisorScope
            }

            val completions = Channel<Pair<Int, IndexProviderOutcome>>(eligibleProviders.size)
            try {
                eligibleProviders.forEachIndexed { position, provider ->
                    launch(providerDispatcher) {
                        completions.send(position to queryProvider(provider, query))
                    }
                }

                repeat(eligibleProviders.size) {
                    val (position, outcome) = completions.receive()
                    completedOutcomes[position] = outcome
                    emit(
                        composeSnapshot(
                            query = query,
                            compatibilityIssues = compatibilityIssues,
                            authorizationIssues = authorizationIssues,
                            outcomes = completedOutcomes.filterNotNull(),
                        ),
                    )
                }
            } finally {
                completions.close()
            }
        }
    }

    private fun composeSnapshot(
        query: IndexQuery,
        compatibilityIssues: List<IndexProviderIssue>,
        authorizationIssues: List<IndexProviderIssue>,
        outcomes: List<IndexProviderOutcome>,
    ): IndexSearchSnapshot {
        val ranking = Comparator<RankedIndexResult> { left, right ->
            if (left.result.providerId == right.result.providerId) {
                compareSameProviderResults(left, right)
            } else {
                val relevanceOrder = right.normalizedRelevance.compareTo(left.normalizedRelevance)
                if (relevanceOrder != 0) {
                    relevanceOrder
                } else {
                    val healthOrder = compareProviderHealth(left, right)
                    if (healthOrder != 0) {
                        healthOrder
                    } else {
                        val locationOrder = compareProcessingLocation(left, right)
                        if (locationOrder != 0) {
                            locationOrder
                        } else {
                            compareStableResultIdentity(left, right)
                        }
                    }
                }
            }
        }

        val results = outcomes
            .asSequence()
            .flatMap { outcome ->
                val degradedProvider = outcome.issue?.kind == IndexProviderIssueKind.DEGRADED
                outcome.results.asSequence().map { result ->
                    rankedResult(
                        query = query,
                        result = result,
                        degradedProvider = degradedProvider,
                        processingLocation = outcome.processingLocation,
                    )
                }
            }
            .sortedWith(ranking)
            .map { it.result }
            .distinctBy { result -> "${result.providerId}:${result.id}" }
            .take(query.maxResults)
            .toList()

        return IndexSearchSnapshot(
            results = results,
            providerIssues = (
                compatibilityIssues +
                    authorizationIssues +
                    outcomes.mapNotNull { it.issue }
                ).distinctBy { it.providerId },
        )
    }

    private fun rankedResult(
        query: IndexQuery,
        result: IndexResult,
        degradedProvider: Boolean,
        processingLocation: IndexProcessingLocation,
    ) = RankedIndexResult(
        result = result,
        normalizedRelevance = normalizedCrossProviderRelevance(query, result),
        degradedProvider = degradedProvider,
        processingLocation = processingLocation,
        normalizedTitle = IndexQueryNormalizer.normalizeForMatching(result.title),
    )

    private fun compareSameProviderResults(
        left: RankedIndexResult,
        right: RankedIndexResult,
    ): Int {
        val providerScoreOrder = right.result.score.compareTo(left.result.score)
        if (providerScoreOrder != 0) return providerScoreOrder

        val sourceOrder = (left.result.sourceOrdinal ?: Int.MAX_VALUE)
            .compareTo(right.result.sourceOrdinal ?: Int.MAX_VALUE)
        if (sourceOrder != 0) return sourceOrder

        val relevanceOrder = right.normalizedRelevance.compareTo(left.normalizedRelevance)
        if (relevanceOrder != 0) return relevanceOrder

        return compareStableResultIdentity(left, right)
    }

    private fun compareProviderHealth(
        left: RankedIndexResult,
        right: RankedIndexResult,
    ): Int = when {
        left.degradedProvider == right.degradedProvider -> 0
        left.degradedProvider -> 1
        else -> -1
    }

    private fun compareProcessingLocation(
        left: RankedIndexResult,
        right: RankedIndexResult,
    ): Int = processingLocationRank(left.processingLocation)
        .compareTo(processingLocationRank(right.processingLocation))

    private fun processingLocationRank(location: IndexProcessingLocation): Int = when (location) {
        IndexProcessingLocation.LOCAL -> 0
        IndexProcessingLocation.MIXED -> 1
        IndexProcessingLocation.REMOTE -> 2
    }

    private fun normalizedCrossProviderRelevance(
        query: IndexQuery,
        result: IndexResult,
    ): Int = IndexTextMatcher.score(
        query = query.text,
        title = result.title,
        secondary = result.subtitle.orEmpty(),
    ) ?: 0

    private fun compareStableResultIdentity(
        left: RankedIndexResult,
        right: RankedIndexResult,
    ): Int {
        val titleOrder = left.normalizedTitle.compareTo(right.normalizedTitle)
        if (titleOrder != 0) return titleOrder
        val providerOrder = left.result.providerId.compareTo(right.result.providerId)
        if (providerOrder != 0) return providerOrder
        return left.result.id.compareTo(right.result.id)
    }

    private fun boundProviderResults(
        results: List<IndexResult>,
        query: IndexQuery,
        processingLocation: IndexProcessingLocation,
    ): List<IndexResult> = results
        .asSequence()
        .map { result ->
            rankedResult(
                query = query,
                result = result,
                degradedProvider = false,
                processingLocation = processingLocation,
            )
        }
        .sortedWith(
            Comparator { left, right ->
                compareSameProviderResults(left, right)
            },
        )
        .map { it.result }
        .distinctBy(IndexResult::id)
        .take(query.maxResults)
        .toList()

    private fun isCompatibleProvider(provider: IndexProvider): Boolean =
        provider.contractVersion == GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION

    private fun compatibilityIssue(provider: IndexProvider): IndexProviderIssue? {
        if (isCompatibleProvider(provider)) return null
        return IndexProviderIssue(
            providerId = provider.providerId,
            providerName = provider.displayName,
            kind = IndexProviderIssueKind.INCOMPATIBLE_CONTRACT,
        )
    }

    private suspend fun queryProvider(
        provider: IndexProvider,
        query: IndexQuery,
    ): IndexProviderOutcome = try {
        val timeoutMillis = provider.timeoutMillis.coerceIn(1L, MAX_PROVIDER_TIMEOUT_MILLIS)
        val providerResponse = withTimeout(timeoutMillis) {
            if (provider is IndexStatusAwareProvider) {
                provider.searchWithStatus(query)
            } else {
                IndexProviderResponse(results = provider.search(query))
            }
        }
        val validResults = providerResponse.results.filter { result ->
            result.providerId == provider.providerId &&
                result.id.isNotBlank() &&
                result.title.isNotBlank() &&
                (result.sourceOrdinal == null || result.sourceOrdinal >= 0)
        }
        val exceededResultBound = providerResponse.results.size > query.maxResults
        val issue = when {
            validResults.size != providerResponse.results.size || exceededResultBound -> IndexProviderIssue(
                providerId = provider.providerId,
                providerName = provider.displayName,
                kind = IndexProviderIssueKind.INVALID_RESULT,
            )
            providerResponse.degraded -> IndexProviderIssue(
                providerId = provider.providerId,
                providerName = provider.displayName,
                kind = IndexProviderIssueKind.DEGRADED,
            )
            else -> null
        }

        IndexProviderOutcome(
            processingLocation = provider.processingLocation,
            results = boundProviderResults(
                results = validResults,
                query = query,
                processingLocation = provider.processingLocation,
            ),
            issue = issue,
        )
    } catch (_: TimeoutCancellationException) {
        IndexProviderOutcome(
            processingLocation = provider.processingLocation,
            issue = IndexProviderIssue(
                providerId = provider.providerId,
                providerName = provider.displayName,
                kind = IndexProviderIssueKind.TIMED_OUT,
            ),
        )
    } catch (cancellation: CancellationException) {
        throw cancellation
    } catch (_: Exception) {
        IndexProviderOutcome(
            processingLocation = provider.processingLocation,
            issue = IndexProviderIssue(
                providerId = provider.providerId,
                providerName = provider.displayName,
                kind = IndexProviderIssueKind.FAILED,
            ),
        )
    }

    private companion object {
        const val MAX_RESULTS = 100
        const val MAX_PROVIDER_TIMEOUT_MILLIS = 5_000L
    }
}

object IndexQueryNormalizer {
    private val whitespace = Regex("\\s+")

    fun normalize(value: String): String =
        whitespace.replace(
            Normalizer.normalize(value, Normalizer.Form.NFKC).trim(),
            " ",
        )

    fun normalizeForMatching(value: String): String =
        normalize(value).lowercase(Locale.ROOT)
}

object IndexTextMatcher {
    fun score(query: String, title: String, secondary: String = ""): Int? {
        val needle = IndexQueryNormalizer.normalizeForMatching(query)
        if (needle.isEmpty()) return 100

        val normalizedTitle = IndexQueryNormalizer.normalizeForMatching(title)
        val normalizedSecondary = IndexQueryNormalizer.normalizeForMatching(secondary)

        return when {
            normalizedTitle == needle -> 1_000
            normalizedTitle.startsWith(needle) -> 850
            normalizedTitle.split(' ').any { it.startsWith(needle) } -> 760
            normalizedTitle.contains(needle) -> 650
            normalizedSecondary == needle -> 540
            normalizedSecondary.startsWith(needle) -> 500
            normalizedSecondary.contains(needle) -> 420
            else -> null
        }
    }
}
