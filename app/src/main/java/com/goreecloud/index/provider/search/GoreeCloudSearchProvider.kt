package com.goreecloud.index.provider.search

import com.goreecloud.index.core.GoreeCloudIndexContract
import com.goreecloud.index.core.IndexAction
import com.goreecloud.index.core.IndexAuthorityRequirement
import com.goreecloud.index.core.IndexProcessingLocation
import com.goreecloud.index.core.IndexProviderResponse
import com.goreecloud.index.core.IndexQuery
import com.goreecloud.index.core.IndexResult
import com.goreecloud.index.core.IndexResultType
import com.goreecloud.index.core.IndexStatusAwareProvider
import com.goreecloud.index.core.IndexTextMatcher
import java.net.URI
import java.util.Locale
import java.util.UUID

internal const val GOREECLOUD_SEARCH_API_VERSION = "1"
internal const val GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID = "search.query"
internal const val GOREECLOUD_SEARCH_QUERY_ENDPOINT = "/api/v1/search"
internal const val GOREECLOUD_SEARCH_DISCOVERY_ENDPOINT = "/api/v1/status"
internal const val GOREECLOUD_SEARCH_DISCOVERY_COLLECTION = "capability_evidence"
internal const val GOREECLOUD_SEARCH_ORIGIN = "https://search.goreecloud.com"
internal const val GOREECLOUD_SEARCH_MAX_RESULTS = 100
internal const val GOREECLOUD_SEARCH_PREFERRED_METHOD = "POST"
internal const val GOREECLOUD_SEARCH_PREFERRED_QUERY_TRANSPORT = "json_body"
internal const val GOREECLOUD_SEARCH_REQUEST_MEDIA_TYPE = "application/json"
internal const val GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE = "application/json"
internal const val GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_SCHEME = "privacy_shield_capability_token_reference"
internal const val GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_HEADER = "X-GoreeCloud-Privacy-Capability"
internal const val GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_ENFORCEMENT = "required"
internal const val GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_AUTHORITY = "goreecloud-identity"
internal const val GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_SCHEME = "bearer"
internal const val GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_HEADER = "Authorization"
internal const val GOREECLOUD_SEARCH_REQUESTER_CREDENTIAL_MAX_LENGTH = 16 * 1024
internal const val GOREECLOUD_SEARCH_PRIVACY_PROCESSING_ZONE = "private_goreecloud"
internal const val GOREECLOUD_SEARCH_PRIVACY_RETENTION_MODE = "none"
internal const val GOREECLOUD_SEARCH_PRIVACY_PURPOSE = "internet_search"
internal const val GOREECLOUD_SEARCH_PRIVACY_RESOURCE_ID = "goreecloud.search.query"
internal const val GOREECLOUD_SEARCH_PRIVACY_RESOURCE_CLASSIFICATION = "query_text"
internal const val GOREECLOUD_SEARCH_INDEX_DELEGATION_CONTRACT_VERSION = "goreecloud.search-index-delegation.v1"
internal const val GOREECLOUD_SEARCH_INDEX_DELEGATION_MODE = "external_only"
internal const val GOREECLOUD_SEARCH_INDEX_PROVIDER_REENTRY_ALLOWED = false
internal const val GOREECLOUD_SEARCH_INDEX_DELEGATION_FALLBACK_ALLOWED = false
internal const val GOREECLOUD_INDEX_PRIVACY_REQUESTER_ID = "goreecloud-index"
internal const val GOREECLOUD_INDEX_PRIVACY_REQUESTER_TYPE = "application"
internal const val GOREECLOUD_SEARCH_MAX_REQUEST_BYTES = 16 * 1024
private const val GOREECLOUD_SEARCH_GENERAL_CATEGORY = "general"

internal fun isCanonicalSearchRequesterBearerCredential(credential: String?): Boolean =
    credential != null &&
        credential.isNotEmpty() &&
        credential.length <= GOREECLOUD_SEARCH_REQUESTER_CREDENTIAL_MAX_LENGTH &&
        credential.none { character ->
            character.isWhitespace() || Character.isISOControl(character.code)
        }

/**
 * The only data Index needs to send to GoreeCloud Search for the initial
 * Internet-provider contract. Keeping this transport-neutral request narrow is
 * intentional: local provider state, local results, files, contacts, calendar
 * data, application inventory, identity identifiers, and raw authorization
 * evidence are not part of this boundary. Production requests carry only the
 * operation-scoped Privacy Shield reference and opaque Identity requester
 * credential required by Search.
 *
 * Query text and both authorization materials are deliberately excluded from
 * debug rendering so ordinary logs/diagnostics cannot turn this object into
 * search-history or credential telemetry.
 */
data class GoreeCloudSearchRequest(
    val query: String,
    val category: String = GOREECLOUD_SEARCH_GENERAL_CATEGORY,
    val limit: Int,
    val privacyCapabilityReference: String? = null,
    val requesterBearerCredential: String? = null,
) {
    override fun toString(): String =
        "GoreeCloudSearchRequest(" +
            "query=<redacted>, " +
            "category=$category, " +
            "limit=$limit, " +
            "privacyCapabilityReference=${if (privacyCapabilityReference == null) "null" else "<redacted>"}, " +
            "requesterBearerCredential=${if (requesterBearerCredential == null) "null" else "<redacted>"}" +
            ")"
}

data class GoreeCloudSearchResult(
    val title: String,
    val url: String,
    val snippet: String? = null,
    val searchScore: Int = 0,
) {
    override fun toString(): String =
        "GoreeCloudSearchResult(" +
            "title=<redacted>, " +
            "url=<redacted>, " +
            "snippet=${if (snippet == null) "null" else "<redacted>"}, " +
            "searchScore=$searchScore" +
            ")"
}

data class GoreeCloudSearchResponse(
    val apiVersion: String,
    val query: String,
    val category: String,
    val results: List<GoreeCloudSearchResult>,
    val degraded: Boolean = false,
) {
    override fun toString(): String =
        "GoreeCloudSearchResponse(" +
            "apiVersion=$apiVersion, " +
            "query=<redacted>, " +
            "category=$category, " +
            "resultCount=${results.size}, " +
            "degraded=$degraded" +
            ")"
}

data class GoreeCloudSearchCapability(
    val id: String,
    val contractVersion: String,
    val authoritative: Boolean,
    val current: Boolean,
    val endpoint: String,
    val maxResults: Int,
    val productionAccepted: Boolean,
    val discoveryEndpoint: String? = null,
    val discoveryCollection: String? = null,
    val methods: Set<String> = setOf("GET"),
    val preferredMethod: String = "GET",
    val preferredQueryTransport: String = "url_query",
    val requestMediaType: String? = null,
    val responseMediaType: String? = null,
    val privacyAuthorizationRequired: Boolean = false,
    val privacyAuthorizationScheme: String? = null,
    val privacyAuthorizationHeader: String? = null,
    val privacyAuthorizationEnforcement: String? = null,
    val authenticatedRequesterRequired: Boolean = false,
    val maxRequestBytes: Int = 0,
    val authenticatedRequesterAuthority: String? = null,
    val authenticatedRequesterScheme: String? = null,
    val authenticatedRequesterHeader: String? = null,
    val indexDelegationContractVersion: String? = null,
    val indexDelegationMode: String? = null,
    val indexProviderReentryAllowed: Boolean? = null,
    val indexDelegationFallbackAllowed: Boolean? = null,
)

data class GoreeCloudSearchPrivacyAuthorizationRequest(
    val requestId: String = UUID.randomUUID().toString(),
    val requesterId: String = GOREECLOUD_INDEX_PRIVACY_REQUESTER_ID,
    val requesterType: String = GOREECLOUD_INDEX_PRIVACY_REQUESTER_TYPE,
    val resourceId: String = GOREECLOUD_SEARCH_PRIVACY_RESOURCE_ID,
    val resourceClassification: String = GOREECLOUD_SEARCH_PRIVACY_RESOURCE_CLASSIFICATION,
    val operation: String = GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID,
    val purpose: String = GOREECLOUD_SEARCH_PRIVACY_PURPOSE,
    val processingZone: String = GOREECLOUD_SEARCH_PRIVACY_PROCESSING_ZONE,
    val destination: String = GOREECLOUD_SEARCH_ORIGIN,
    val retentionMode: String = GOREECLOUD_SEARCH_PRIVACY_RETENTION_MODE,
    val externalDisclosure: Boolean = false,
)

data class GoreeCloudSearchPrivacyAuthorization(
    val capabilityTokenReference: String,
) {
    override fun toString(): String = "GoreeCloudSearchPrivacyAuthorization(capabilityTokenReference=<redacted>)"
}

data class GoreeCloudSearchRequesterAuthentication(
    val bearerCredential: String,
) {
    override fun toString(): String = "GoreeCloudSearchRequesterAuthentication(bearerCredential=<redacted>)"
}

enum class GoreeCloudSearchAcceptanceMode {
    DEVELOPMENT,
    AUTHENTICATED_DEVELOPMENT,
    PRODUCTION,
}

fun interface GoreeCloudSearchClient {
    suspend fun search(request: GoreeCloudSearchRequest): GoreeCloudSearchResponse
}

fun interface GoreeCloudSearchCapabilityClient {
    suspend fun queryCapability(): GoreeCloudSearchCapability
}

fun interface GoreeCloudSearchAuthorizationClient {
    suspend fun authorize(request: GoreeCloudSearchPrivacyAuthorizationRequest): GoreeCloudSearchPrivacyAuthorization
}

fun interface GoreeCloudSearchRequesterAuthenticationClient {
    suspend fun authenticateRequester(): GoreeCloudSearchRequesterAuthentication
}

object GoreeCloudSearchCapabilityDiscovery {
    fun select(capabilities: List<GoreeCloudSearchCapability>): GoreeCloudSearchCapability? {
        val matches = capabilities.filter { it.id == GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID }
        return matches.singleOrNull()
    }
}

class GoreeCloudSearchProvider(
    private val client: GoreeCloudSearchClient,
    private val capabilityClient: GoreeCloudSearchCapabilityClient,
    private val acceptanceMode: GoreeCloudSearchAcceptanceMode = GoreeCloudSearchAcceptanceMode.DEVELOPMENT,
    private val authorizationClient: GoreeCloudSearchAuthorizationClient? = null,
    private val requesterAuthenticationClient: GoreeCloudSearchRequesterAuthenticationClient? = null,
) : IndexStatusAwareProvider {
    override val providerId: String = GoreeCloudIndexContract.PROVIDER_SEARCH
    override val displayName: String = "GoreeCloud Search"
    override val processingLocation: IndexProcessingLocation = IndexProcessingLocation.REMOTE
    override val timeoutMillis: Long = 5_000L
    override val contractVersion: Int = GoreeCloudIndexContract.PROVIDER_CONTRACT_VERSION
    private val requiresAuthenticatedTransport: Boolean
        get() = acceptanceMode != GoreeCloudSearchAcceptanceMode.DEVELOPMENT

    override val authorityRequirements: Set<IndexAuthorityRequirement> =
        if (requiresAuthenticatedTransport) {
            setOf(
                IndexAuthorityRequirement.PRIVACY_SHIELD,
                IndexAuthorityRequirement.GOREECLOUD_IDENTITY,
            )
        } else {
            setOf(IndexAuthorityRequirement.PRIVACY_SHIELD)
        }
    override val supportsEmptyQuery: Boolean = false

    override suspend fun searchWithStatus(query: IndexQuery): IndexProviderResponse {
        val normalizedQuery = query.text.trim()
        require(normalizedQuery.isNotEmpty()) { "GoreeCloud Search requires a non-empty query" }

        val capability = capabilityClient.queryCapability()
        validateCapability(capability)
        val privacyCapabilityReference = authenticatedPrivacyCapabilityReference()
        val requesterBearerCredential = authenticatedRequesterBearerCredential()
        val limit = minOf(query.maxResults.coerceIn(1, GOREECLOUD_SEARCH_MAX_RESULTS), capability.maxResults)
        val request = GoreeCloudSearchRequest(
            query = normalizedQuery,
            category = GOREECLOUD_SEARCH_GENERAL_CATEGORY,
            limit = limit,
            privacyCapabilityReference = privacyCapabilityReference,
            requesterBearerCredential = requesterBearerCredential,
        )
        val response = client.search(request)

        check(response.apiVersion == GOREECLOUD_SEARCH_API_VERSION) { "GoreeCloud Search response API version is not supported" }
        check(response.query == request.query) { "GoreeCloud Search response query does not match the delegated query" }
        check(response.category == request.category) { "GoreeCloud Search response category does not match the delegated category" }

        return IndexProviderResponse(
            results = response.results.asSequence().take(limit).mapIndexed { sourceOrdinal, result ->
                result.toIndexResult(normalizedQuery, sourceOrdinal)
            }.toList(),
            degraded = response.degraded,
        )
    }

    private suspend fun authenticatedPrivacyCapabilityReference(): String? {
        if (!requiresAuthenticatedTransport) return null
        val production = acceptanceMode == GoreeCloudSearchAcceptanceMode.PRODUCTION
        val authorizer = checkNotNull(authorizationClient) {
            if (production) {
                "GoreeCloud Search production delegation requires a Privacy Shield authorization client"
            } else {
                "GoreeCloud Search authenticated Development delegation requires a Privacy Shield authorization client"
            }
        }
        val authorizationRequest = GoreeCloudSearchPrivacyAuthorizationRequest()
        check(authorizationRequest.requestId.isNotBlank()) {
            if (production) {
                "GoreeCloud Search production delegation requires a Privacy Shield request identifier"
            } else {
                "GoreeCloud Search authenticated Development delegation requires a Privacy Shield request identifier"
            }
        }
        val authorization = authorizer.authorize(authorizationRequest)
        val reference = authorization.capabilityTokenReference.trim()
        check(isCanonicalPrivacyShieldCapabilityReference(reference)) {
            if (production) {
                "GoreeCloud Search production delegation requires a canonical Privacy Shield capability reference"
            } else {
                "GoreeCloud Search authenticated Development delegation requires a canonical Privacy Shield capability reference"
            }
        }
        return reference
    }

    private suspend fun authenticatedRequesterBearerCredential(): String? {
        if (!requiresAuthenticatedTransport) return null
        val production = acceptanceMode == GoreeCloudSearchAcceptanceMode.PRODUCTION
        val authenticator = checkNotNull(requesterAuthenticationClient) {
            if (production) {
                "GoreeCloud Search production delegation requires a GoreeCloud Identity requester authentication client"
            } else {
                "GoreeCloud Search authenticated Development delegation requires a GoreeCloud Identity requester authentication client"
            }
        }
        val authentication = authenticator.authenticateRequester()
        val credential = authentication.bearerCredential
        check(isCanonicalSearchRequesterBearerCredential(credential)) {
            if (production) {
                "GoreeCloud Search production delegation requires a canonical Identity requester credential"
            } else {
                "GoreeCloud Search authenticated Development delegation requires a canonical Identity requester credential"
            }
        }
        return credential
    }

    private fun validateCapability(capability: GoreeCloudSearchCapability) {
        check(capability.id == GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID) { "GoreeCloud Search query capability is unavailable" }
        check(capability.contractVersion == GOREECLOUD_SEARCH_API_VERSION) { "GoreeCloud Search capability contract version is not supported" }
        check(capability.authoritative && capability.current) { "GoreeCloud Search query capability is not current and authoritative" }
        check(
            capability.indexDelegationContractVersion == GOREECLOUD_SEARCH_INDEX_DELEGATION_CONTRACT_VERSION &&
                capability.indexDelegationMode == GOREECLOUD_SEARCH_INDEX_DELEGATION_MODE &&
                capability.indexProviderReentryAllowed == GOREECLOUD_SEARCH_INDEX_PROVIDER_REENTRY_ALLOWED &&
                capability.indexDelegationFallbackAllowed == GOREECLOUD_SEARCH_INDEX_DELEGATION_FALLBACK_ALLOWED
        ) { "GoreeCloud Search query capability does not provide cycle-safe Index-originated delegation" }
        if (acceptanceMode == GoreeCloudSearchAcceptanceMode.PRODUCTION) {
            check(capability.productionAccepted) { "GoreeCloud Search query capability is not production accepted" }
        }
        if (requiresAuthenticatedTransport) {
            check(capability.discoveryEndpoint == GOREECLOUD_SEARCH_DISCOVERY_ENDPOINT && capability.discoveryCollection == GOREECLOUD_SEARCH_DISCOVERY_COLLECTION) {
                "GoreeCloud Search query capability discovery contract is incompatible"
            }
            check(GOREECLOUD_SEARCH_PREFERRED_METHOD in capability.methods && capability.preferredMethod == GOREECLOUD_SEARCH_PREFERRED_METHOD) {
                "GoreeCloud Search query capability does not provide the required authenticated POST transport"
            }
            check(
                capability.preferredQueryTransport == GOREECLOUD_SEARCH_PREFERRED_QUERY_TRANSPORT &&
                    capability.requestMediaType == GOREECLOUD_SEARCH_REQUEST_MEDIA_TYPE &&
                    capability.responseMediaType == GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE &&
                    capability.maxRequestBytes == GOREECLOUD_SEARCH_MAX_REQUEST_BYTES
            ) { "GoreeCloud Search query capability does not provide the required private JSON-body contract" }
            check(
                capability.privacyAuthorizationRequired &&
                    capability.privacyAuthorizationScheme == GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_SCHEME &&
                    capability.privacyAuthorizationHeader == GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_HEADER &&
                    capability.privacyAuthorizationEnforcement == GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_ENFORCEMENT &&
                    capability.authenticatedRequesterRequired &&
                    capability.authenticatedRequesterAuthority == GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_AUTHORITY &&
                    capability.authenticatedRequesterScheme == GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_SCHEME &&
                    capability.authenticatedRequesterHeader == GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_HEADER
            ) { "GoreeCloud Search query capability does not enforce the required Privacy Shield authorization and authenticated requester transport" }
        }
        check(capability.endpoint == GOREECLOUD_SEARCH_QUERY_ENDPOINT) { "GoreeCloud Search query endpoint is incompatible" }
        check(capability.maxResults >= 1) { "GoreeCloud Search result capability is invalid" }
    }

    private fun GoreeCloudSearchResult.toIndexResult(query: String, sourceOrdinal: Int): IndexResult {
        val normalizedURL = normalizeWebURL(url)
        val normalizedTitle = title.trim()
        val normalizedSnippet = snippet?.trim()?.takeIf(String::isNotEmpty)
        val localScore = IndexTextMatcher.score(query = query, title = normalizedTitle, secondary = normalizedSnippet.orEmpty()) ?: 0
        return IndexResult(
            id = normalizedURL.orEmpty(),
            providerId = providerId,
            type = IndexResultType.WEB,
            title = normalizedTitle,
            subtitle = normalizedSnippet,
            score = localScore,
            action = normalizedURL?.let(IndexAction::OpenWeb),
            sourceOrdinal = sourceOrdinal,
        )
    }

    private fun normalizeWebURL(raw: String): String? {
        val uri = runCatching { URI(raw.trim()) }.getOrNull() ?: return null
        val scheme = uri.scheme?.lowercase(Locale.ROOT) ?: return null
        if (scheme != "https" && scheme != "http") return null
        if (uri.host.isNullOrBlank()) return null
        if (uri.userInfo != null) return null
        return uri.normalize().toASCIIString()
    }
}
