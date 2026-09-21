package com.goreecloud.index.provider.search

import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import javax.net.ssl.HttpsURLConnection
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

internal const val GOREECLOUD_SEARCH_HTTP_MAX_RESPONSE_BYTES = 256 * 1024

class GoreeCloudSearchTransportException(message: String) : IllegalStateException(message)

class GoreeCloudSearchHttpRequest(
    val method: String,
    val url: URL,
    val headers: Map<String, String>,
    val body: ByteArray? = null,
) {
    override fun toString(): String =
        "GoreeCloudSearchHttpRequest(method=$method, url=<redacted>, headers=<redacted>, body=<redacted>)"
}

class GoreeCloudSearchHttpResponse(
    val status: Int,
    val contentType: String?,
    val body: ByteArray,
) {
    override fun toString(): String =
        "GoreeCloudSearchHttpResponse(status=$status, contentType=$contentType, body=<redacted>)"
}

fun interface GoreeCloudSearchHttpExchange {
    suspend fun execute(request: GoreeCloudSearchHttpRequest): GoreeCloudSearchHttpResponse
}

class HttpsUrlConnectionSearchExchange : GoreeCloudSearchHttpExchange {
    override suspend fun execute(request: GoreeCloudSearchHttpRequest): GoreeCloudSearchHttpResponse =
        withContext(Dispatchers.IO) {
            require(request.url.protocol.equals("https", ignoreCase = true)) {
                "GoreeCloud Search transport requires HTTPS"
            }
            val connection = request.url.openConnection() as? HttpsURLConnection
                ?: throw GoreeCloudSearchTransportException("GoreeCloud Search HTTPS connection is unavailable")
            try {
                connection.instanceFollowRedirects = false
                connection.connectTimeout = 5_000
                connection.readTimeout = 5_000
                connection.requestMethod = request.method
                connection.useCaches = false
                connection.setRequestProperty("Accept", GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE)
                request.headers.forEach(connection::setRequestProperty)
                request.body?.let { body ->
                    connection.doOutput = true
                    connection.setFixedLengthStreamingMode(body.size)
                    connection.outputStream.use { it.write(body) }
                }

                val status = connection.responseCode
                val stream = if (status in 200..299) connection.inputStream else connection.errorStream
                val bytes = stream?.use { readBounded(it, GOREECLOUD_SEARCH_HTTP_MAX_RESPONSE_BYTES) } ?: ByteArray(0)
                GoreeCloudSearchHttpResponse(
                    status = status,
                    contentType = connection.contentType,
                    body = bytes,
                )
            } finally {
                connection.disconnect()
            }
        }

    private fun readBounded(input: InputStream, maximum: Int): ByteArray {
        val buffer = ByteArray(8192)
        val output = java.io.ByteArrayOutputStream()
        var total = 0
        while (true) {
            val read = input.read(buffer)
            if (read < 0) break
            total += read
            if (total > maximum) {
                throw GoreeCloudSearchTransportException("GoreeCloud Search response exceeds the accepted size limit")
            }
            output.write(buffer, 0, read)
        }
        return output.toByteArray()
    }
}

class AuthenticatedGoreeCloudSearchHttpClient(
    private val exchange: GoreeCloudSearchHttpExchange = HttpsUrlConnectionSearchExchange(),
) : GoreeCloudSearchClient, GoreeCloudSearchCapabilityClient, GoreeCloudSearchReadinessClient {
    private val origin = URL(GOREECLOUD_SEARCH_ORIGIN)

    init {
        check(
            origin.protocol == "https" &&
                origin.host == "search.goreecloud.com" &&
                origin.port == -1 &&
                origin.userInfo == null &&
                origin.query == null &&
                origin.ref == null
        ) { "GoreeCloud Search origin is not the canonical private HTTPS origin" }
    }

    override suspend fun queryCapability(): GoreeCloudSearchCapability {
        val response = exchange.execute(
            GoreeCloudSearchHttpRequest(
                method = "GET",
                url = endpoint(GOREECLOUD_SEARCH_DISCOVERY_ENDPOINT),
                headers = mapOf("Accept" to GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE),
            ),
        )
        validateJsonResponse(response, "capability discovery")
        val payload = parseObject(response.body)
        val capabilities = payload.getJSONArray(GOREECLOUD_SEARCH_DISCOVERY_COLLECTION)
        val matches = buildList {
            for (index in 0 until capabilities.length()) {
                val candidate = parseCapability(capabilities.getJSONObject(index))
                if (candidate.id == GOREECLOUD_SEARCH_QUERY_CAPABILITY_ID) add(candidate)
            }
        }
        return GoreeCloudSearchCapabilityDiscovery.select(matches)
            ?: throw GoreeCloudSearchTransportException(
                "GoreeCloud Search capability discovery did not return exactly one query capability"
            )
    }

    override suspend fun queryReadiness(): Boolean {
        val response = exchange.execute(
            GoreeCloudSearchHttpRequest(
                method = "GET",
                url = endpoint(GOREECLOUD_SEARCH_READINESS_ENDPOINT),
                headers = mapOf("Accept" to GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE),
            ),
        )
        validateReadinessResponse(response)
        val payload = parseObject(response.body)
        val service = payload.getString("service")
        val status = payload.getString("status")
        if (service != "goreecloud-search") {
            throw GoreeCloudSearchTransportException(
                "GoreeCloud Search readiness response identifies an unexpected service"
            )
        }
        return when (response.status) {
            HttpURLConnection.HTTP_OK -> {
                if (status != "ready") {
                    throw GoreeCloudSearchTransportException(
                        "GoreeCloud Search readiness response is inconsistent"
                    )
                }
                true
            }

            HttpURLConnection.HTTP_UNAVAILABLE -> {
                if (status != "not_ready") {
                    throw GoreeCloudSearchTransportException(
                        "GoreeCloud Search readiness response is inconsistent"
                    )
                }
                false
            }

            else -> error("readiness status validation should reject unsupported status")
        }
    }

    override suspend fun search(request: GoreeCloudSearchRequest): GoreeCloudSearchResponse {
        val privacyReference = request.privacyCapabilityReference?.trim()
            ?: throw GoreeCloudSearchTransportException(
                "GoreeCloud Search HTTP transport requires Privacy Shield authorization"
            )
        check(isCanonicalPrivacyShieldCapabilityReference(privacyReference)) {
            "GoreeCloud Search HTTP transport requires a canonical Privacy Shield capability reference"
        }
        val bearerCredential = request.requesterBearerCredential
            ?: throw GoreeCloudSearchTransportException(
                "GoreeCloud Search HTTP transport requires authenticated requester identity"
            )
        check(isCanonicalSearchRequesterBearerCredential(bearerCredential)) {
            "GoreeCloud Search HTTP transport requires a canonical requester credential"
        }
        require(request.limit in 1..GOREECLOUD_SEARCH_MAX_RESULTS) {
            "GoreeCloud Search request limit is outside the accepted range"
        }
        require(request.category == "general") {
            "GoreeCloud Search initial HTTP transport accepts only the general category"
        }
        require(request.query.isNotBlank()) { "GoreeCloud Search query must not be blank" }

        val body = JSONObject()
            .put("query", request.query)
            .put("category", request.category)
            .put("limit", request.limit)
            .toString()
            .toByteArray(Charsets.UTF_8)
        check(body.size <= GOREECLOUD_SEARCH_MAX_REQUEST_BYTES) {
            "GoreeCloud Search request exceeds the accepted size limit"
        }

        val response = exchange.execute(
            GoreeCloudSearchHttpRequest(
                method = "POST",
                url = endpoint(GOREECLOUD_SEARCH_QUERY_ENDPOINT),
                headers = mapOf(
                    "Accept" to GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE,
                    "Content-Type" to GOREECLOUD_SEARCH_REQUEST_MEDIA_TYPE,
                    GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_HEADER to privacyReference,
                    GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_HEADER to "Bearer $bearerCredential",
                ),
                body = body,
            ),
        )
        validateJsonResponse(response, "query")
        val payload = parseObject(response.body)
        val results = payload.getJSONArray("results")
        if (results.length() > GOREECLOUD_SEARCH_MAX_RESULTS) {
            throw GoreeCloudSearchTransportException("GoreeCloud Search returned too many results")
        }
        return GoreeCloudSearchResponse(
            apiVersion = payload.getString("apiVersion"),
            query = payload.getString("query"),
            category = payload.getString("category"),
            results = buildList {
                for (index in 0 until results.length()) {
                    val result = results.getJSONObject(index)
                    add(
                        GoreeCloudSearchResult(
                            title = result.getString("title"),
                            url = result.getString("url"),
                            snippet = result.nullableString("snippet"),
                            searchScore = result.getInt("searchScore"),
                        ),
                    )
                }
            },
            degraded = payload.getBoolean("degraded"),
        )
    }

    private fun endpoint(path: String): URL {
        require(path.startsWith("/") && !path.startsWith("//")) {
            "GoreeCloud Search endpoint must be an absolute path"
        }
        return URL(origin, path)
    }

    private fun validateReadinessResponse(response: GoreeCloudSearchHttpResponse) {
        if (
            response.status != HttpURLConnection.HTTP_OK &&
            response.status != HttpURLConnection.HTTP_UNAVAILABLE
        ) {
            throw GoreeCloudSearchTransportException(
                "GoreeCloud Search readiness failed with HTTP " + response.status
            )
        }
        val mediaType = response.contentType?.substringBefore(';')?.trim()?.lowercase()
        if (mediaType != GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE) {
            throw GoreeCloudSearchTransportException(
                "GoreeCloud Search readiness returned an unsupported media type"
            )
        }
        if (response.body.isEmpty() || response.body.size > GOREECLOUD_SEARCH_HTTP_MAX_RESPONSE_BYTES) {
            throw GoreeCloudSearchTransportException(
                "GoreeCloud Search readiness returned an invalid response size"
            )
        }
    }

    private fun validateJsonResponse(response: GoreeCloudSearchHttpResponse, operation: String) {
        if (response.status != HttpURLConnection.HTTP_OK) {
            throw GoreeCloudSearchTransportException(
                "GoreeCloud Search " + operation + " failed with HTTP " + response.status
            )
        }
        val mediaType = response.contentType?.substringBefore(';')?.trim()?.lowercase()
        if (mediaType != GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE) {
            throw GoreeCloudSearchTransportException(
                "GoreeCloud Search $operation returned an unsupported media type"
            )
        }
        if (response.body.isEmpty() || response.body.size > GOREECLOUD_SEARCH_HTTP_MAX_RESPONSE_BYTES) {
            throw GoreeCloudSearchTransportException(
                "GoreeCloud Search $operation returned an invalid response size"
            )
        }
    }

    private fun parseObject(body: ByteArray): JSONObject =
        try {
            JSONObject(body.toString(Charsets.UTF_8))
        } catch (error: Exception) {
            throw GoreeCloudSearchTransportException("GoreeCloud Search returned invalid JSON")
        }

    private fun parseCapability(value: JSONObject): GoreeCloudSearchCapability =
        GoreeCloudSearchCapability(
            id = value.getString("id"),
            contractVersion = value.getString("contract_version"),
            authoritative = value.getBoolean("authoritative"),
            current = value.getBoolean("current"),
            endpoint = value.getString("endpoint"),
            maxResults = value.getInt("max_results"),
            productionAccepted = value.getBoolean("production_accepted"),
            discoveryEndpoint = value.nullableString("discovery_endpoint"),
            discoveryCollection = value.nullableString("discovery_collection"),
            methods = value.getJSONArray("methods").let { methods ->
                buildSet {
                    for (index in 0 until methods.length()) add(methods.getString(index))
                }
            },
            preferredMethod = value.getString("preferred_method"),
            preferredQueryTransport = value.getString("preferred_query_transport"),
            requestMediaType = value.nullableString("request_media_type"),
            responseMediaType = value.nullableString("response_media_type"),
            privacyAuthorizationRequired = value.getBoolean("privacy_authorization_required"),
            privacyAuthorizationScheme = value.nullableString("privacy_authorization_scheme"),
            privacyAuthorizationHeader = value.nullableString("privacy_authorization_header"),
            privacyAuthorizationEnforcement = value.nullableString("privacy_authorization_enforcement"),
            authenticatedRequesterRequired = value.getBoolean("authenticated_requester_required"),
            maxRequestBytes = value.getInt("max_request_bytes"),
            authenticatedRequesterAuthority = value.nullableString("authenticated_requester_authority"),
            authenticatedRequesterScheme = value.nullableString("authenticated_requester_scheme"),
            authenticatedRequesterHeader = value.nullableString("authenticated_requester_header"),
            indexDelegationContractVersion = value.nullableString("index_delegation_contract_version"),
            indexDelegationMode = value.nullableString("index_delegation_mode"),
            indexProviderReentryAllowed = value.nullableBoolean("index_provider_reentry_allowed"),
            indexDelegationFallbackAllowed = value.nullableBoolean("index_delegation_fallback_allowed"),
        )

    private fun JSONObject.nullableString(name: String): String? =
        if (!has(name) || isNull(name)) null else getString(name)

    private fun JSONObject.nullableBoolean(name: String): Boolean? =
        if (!has(name) || isNull(name)) null else getBoolean(name)
}
