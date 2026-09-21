package com.goreecloud.index.provider.search

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.net.URI
import javax.net.ssl.HttpsURLConnection

internal const val GOREECLOUD_SEARCH_HTTP_MAX_RESPONSE_BYTES = 1024 * 1024
internal const val GOREECLOUD_SEARCH_HTTP_CONNECT_TIMEOUT_MILLIS = 5_000
internal const val GOREECLOUD_SEARCH_HTTP_READ_TIMEOUT_MILLIS = 7_000

data class GoreeCloudSearchHttpRequest(
    val method: String,
    val uri: URI,
    val headers: Map<String, String>,
    val body: ByteArray = byteArrayOf(),
) {
    override fun toString(): String =
        "GoreeCloudSearchHttpRequest(" +
            "method=$method, uri=$uri, headers=${headers.keys.sorted()}, body=<redacted:${body.size} bytes>" +
            ")"
}

data class GoreeCloudSearchHttpResponse(
    val statusCode: Int,
    val contentType: String?,
    val body: ByteArray,
)

fun interface GoreeCloudSearchHttpExecutor {
    suspend fun execute(request: GoreeCloudSearchHttpRequest): GoreeCloudSearchHttpResponse
}

class HttpsUrlConnectionSearchExecutor(
    private val connectTimeoutMillis: Int = GOREECLOUD_SEARCH_HTTP_CONNECT_TIMEOUT_MILLIS,
    private val readTimeoutMillis: Int = GOREECLOUD_SEARCH_HTTP_READ_TIMEOUT_MILLIS,
) : GoreeCloudSearchHttpExecutor {
    init {
        require(connectTimeoutMillis in 1..60_000) { "Search HTTP connect timeout is invalid" }
        require(readTimeoutMillis in 1..60_000) { "Search HTTP read timeout is invalid" }
    }

    override suspend fun execute(request: GoreeCloudSearchHttpRequest): GoreeCloudSearchHttpResponse =
        withContext(Dispatchers.IO) {
            require(request.uri.scheme.equals("https", ignoreCase = true)) {
                "GoreeCloud Search transport requires HTTPS"
            }
            require(request.uri.userInfo == null && request.uri.fragment == null) {
                "GoreeCloud Search transport URI is invalid"
            }

            val connection = request.uri.toURL().openConnection() as? HttpsURLConnection
                ?: error("GoreeCloud Search transport requires HTTPS")
            try {
                connection.instanceFollowRedirects = false
                connection.requestMethod = request.method
                connection.connectTimeout = connectTimeoutMillis
                connection.readTimeout = readTimeoutMillis
                connection.useCaches = false
                request.headers.forEach { (name, value) ->
                    connection.setRequestProperty(name, value)
                }
                if (request.body.isNotEmpty()) {
                    connection.doOutput = true
                    connection.setFixedLengthStreamingMode(request.body.size)
                    connection.outputStream.use { output -> output.write(request.body) }
                }

                val status = connection.responseCode
                val stream = if (status >= 400) connection.errorStream else connection.inputStream
                val bytes = stream?.use { input ->
                    readBounded(input, GOREECLOUD_SEARCH_HTTP_MAX_RESPONSE_BYTES)
                } ?: byteArrayOf()
                GoreeCloudSearchHttpResponse(
                    statusCode = status,
                    contentType = connection.getHeaderField("Content-Type"),
                    body = bytes,
                )
            } finally {
                connection.disconnect()
            }
        }

    private fun readBounded(input: InputStream, maximumBytes: Int): ByteArray {
        val output = ByteArrayOutputStream(minOf(maximumBytes, 16 * 1024))
        val buffer = ByteArray(8 * 1024)
        var total = 0
        while (true) {
            val read = input.read(buffer)
            if (read < 0) break
            total += read
            check(total <= maximumBytes) { "GoreeCloud Search HTTP response exceeds the size limit" }
            output.write(buffer, 0, read)
        }
        return output.toByteArray()
    }
}

class GoreeCloudSearchHttpTransport(
    private val executor: GoreeCloudSearchHttpExecutor = HttpsUrlConnectionSearchExecutor(),
) : GoreeCloudSearchClient, GoreeCloudSearchCapabilityClient {
    private val origin = URI(GOREECLOUD_SEARCH_ORIGIN)

    init {
        check(origin.scheme == "https")
        check(origin.host == "search.goreecloud.com")
        check(origin.userInfo == null && origin.query == null && origin.fragment == null)
        check(origin.path.isNullOrEmpty())
    }

    override suspend fun queryCapability(): GoreeCloudSearchCapability {
        val response = execute(
            method = "GET",
            path = GOREECLOUD_SEARCH_DISCOVERY_ENDPOINT,
            headers = mapOf("Accept" to GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE),
        )
        val root = parseResponseObject(response, "capability discovery")
        check(root.requireString("service") == "goreecloud-search") {
            "GoreeCloud Search discovery service identity is invalid"
        }
        val capabilities = root.requireArray(GOREECLOUD_SEARCH_DISCOVERY_COLLECTION).map { item ->
            parseCapability(item.requireObject("capability"))
        }
        return checkNotNull(GoreeCloudSearchCapabilityDiscovery.select(capabilities)) {
            "GoreeCloud Search discovery must return exactly one search.query capability"
        }
    }

    override suspend fun search(request: GoreeCloudSearchRequest): GoreeCloudSearchResponse {
        require(request.query.isNotBlank()) { "GoreeCloud Search HTTP query must not be blank" }
        require(request.category == "general") { "GoreeCloud Search HTTP transport supports only the general category" }
        require(request.limit in 1..GOREECLOUD_SEARCH_MAX_RESULTS) {
            "GoreeCloud Search HTTP result limit is invalid"
        }
        val privacyReference = checkNotNull(request.privacyCapabilityReference) {
            "Authenticated GoreeCloud Search transport requires a Privacy Shield capability reference"
        }
        check(isCanonicalPrivacyShieldCapabilityReference(privacyReference)) {
            "Authenticated GoreeCloud Search transport requires a canonical Privacy Shield capability reference"
        }
        val bearerCredential = checkNotNull(request.requesterBearerCredential) {
            "Authenticated GoreeCloud Search transport requires a GoreeCloud Identity requester credential"
        }
        check(isCanonicalSearchRequesterBearerCredential(bearerCredential)) {
            "Authenticated GoreeCloud Search transport requires a canonical Identity requester credential"
        }

        val body = buildString {
            append('{')
            append("\"query\":")
            append(jsonString(request.query))
            append(",\"category\":")
            append(jsonString(request.category))
            append(",\"limit\":")
            append(request.limit)
            append('}')
        }.encodeToByteArray()
        check(body.size <= GOREECLOUD_SEARCH_MAX_REQUEST_BYTES) {
            "GoreeCloud Search HTTP request exceeds the advertised request limit"
        }

        val response = execute(
            method = "POST",
            path = GOREECLOUD_SEARCH_QUERY_ENDPOINT,
            headers = mapOf(
                "Accept" to GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE,
                "Content-Type" to GOREECLOUD_SEARCH_REQUEST_MEDIA_TYPE,
                GOREECLOUD_SEARCH_PRIVACY_AUTHORIZATION_HEADER to privacyReference,
                GOREECLOUD_SEARCH_REQUESTER_AUTHENTICATION_HEADER to "Bearer $bearerCredential",
            ),
            body = body,
        )
        val root = parseResponseObject(response, "search")
        root.requireExactKeys("apiVersion", "query", "category", "results", "degraded")
        val results = root.requireArray("results")
        check(results.size <= GOREECLOUD_SEARCH_MAX_RESULTS) {
            "GoreeCloud Search response exceeds the result limit"
        }
        return GoreeCloudSearchResponse(
            apiVersion = root.requireString("apiVersion"),
            query = root.requireString("query"),
            category = root.requireString("category"),
            results = results.map { item ->
                val result = item.requireObject("search result")
                result.requireExactKeys("title", "url", "snippet", "searchScore")
                val title = result.requireString("title")
                val url = result.requireString("url")
                val snippet = result.optionalString("snippet")
                check(title.isNotBlank() && title.length <= 4_096) {
                    "GoreeCloud Search result title is invalid"
                }
                check(url.isNotBlank() && url.length <= 8_192) {
                    "GoreeCloud Search result URL is invalid"
                }
                check(snippet == null || snippet.length <= 16_384) {
                    "GoreeCloud Search result snippet is too large"
                }
                GoreeCloudSearchResult(
                    title = title,
                    url = url,
                    snippet = snippet,
                    searchScore = result.requireInt("searchScore"),
                )
            },
            degraded = root.requireBoolean("degraded"),
        )
    }

    private suspend fun execute(
        method: String,
        path: String,
        headers: Map<String, String>,
        body: ByteArray = byteArrayOf(),
    ): GoreeCloudSearchHttpResponse {
        check(path.startsWith("/") && !path.contains('?') && !path.contains('#')) {
            "GoreeCloud Search endpoint path is invalid"
        }
        val uri = origin.resolve(path)
        check(uri.scheme == "https" && uri.host == origin.host && uri.userInfo == null) {
            "GoreeCloud Search endpoint escaped the fixed origin"
        }
        return executor.execute(
            GoreeCloudSearchHttpRequest(
                method = method,
                uri = uri,
                headers = headers,
                body = body,
            )
        )
    }

    private fun parseResponseObject(
        response: GoreeCloudSearchHttpResponse,
        operation: String,
    ): Map<String, Any?> {
        check(response.statusCode == 200) {
            "GoreeCloud Search $operation HTTP status is not accepted"
        }
        check(response.body.size <= GOREECLOUD_SEARCH_HTTP_MAX_RESPONSE_BYTES) {
            "GoreeCloud Search $operation response exceeds the size limit"
        }
        val mediaType = response.contentType
            ?.substringBefore(';')
            ?.trim()
            ?.lowercase()
        check(mediaType == GOREECLOUD_SEARCH_RESPONSE_MEDIA_TYPE) {
            "GoreeCloud Search $operation response media type is invalid"
        }
        val text = response.body.decodeToString()
        return JsonParser(text).parse().requireObject("$operation response")
    }

    private fun parseCapability(value: Map<String, Any?>): GoreeCloudSearchCapability {
        val methods = value.requireArray("methods").map { item ->
            item.requireString("capability method")
        }
        check(methods.isNotEmpty() && methods.size == methods.toSet().size) {
            "GoreeCloud Search capability methods are invalid"
        }
        return GoreeCloudSearchCapability(
            id = value.requireString("id"),
            contractVersion = value.requireString("contract_version"),
            authoritative = value.requireBoolean("authoritative"),
            current = value.requireBoolean("current"),
            endpoint = value.requireString("endpoint"),
            maxResults = value.requireInt("max_results"),
            productionAccepted = value.requireBoolean("production_accepted"),
            discoveryEndpoint = value.optionalString("discovery_endpoint"),
            discoveryCollection = value.optionalString("discovery_collection"),
            methods = methods.toSet(),
            preferredMethod = value.requireString("preferred_method"),
            preferredQueryTransport = value.requireString("preferred_query_transport"),
            requestMediaType = value.optionalString("request_media_type"),
            responseMediaType = value.optionalString("response_media_type"),
            privacyAuthorizationRequired = value.requireBoolean("privacy_authorization_required"),
            privacyAuthorizationScheme = value.optionalString("privacy_authorization_scheme"),
            privacyAuthorizationHeader = value.optionalString("privacy_authorization_header"),
            privacyAuthorizationEnforcement = value.optionalString("privacy_authorization_enforcement"),
            authenticatedRequesterRequired = value.requireBoolean("authenticated_requester_required"),
            maxRequestBytes = value.requireInt("max_request_bytes"),
            authenticatedRequesterAuthority = value.optionalString("authenticated_requester_authority"),
            authenticatedRequesterScheme = value.optionalString("authenticated_requester_scheme"),
            authenticatedRequesterHeader = value.optionalString("authenticated_requester_header"),
            indexDelegationContractVersion = value.optionalString("index_delegation_contract_version"),
            indexDelegationMode = value.optionalString("index_delegation_mode"),
            indexProviderReentryAllowed = value.optionalBoolean("index_provider_reentry_allowed"),
            indexDelegationFallbackAllowed = value.optionalBoolean("index_delegation_fallback_allowed"),
        )
    }
}

private fun jsonString(value: String): String = buildString(value.length + 2) {
    append('"')
    value.forEach { character ->
        when (character) {
            '"' -> append("\\"")
            '\\' -> append("\\\\")
            '\b' -> append("\\b")
            '\u000C' -> append("\\f")
            '\n' -> append("\\n")
            '\r' -> append("\\r")
            '\t' -> append("\\t")
            else -> {
                if (character.code < 0x20) {
                    append("\\u")
                    append(character.code.toString(16).padStart(4, '0'))
                } else {
                    append(character)
                }
            }
        }
    }
    append('"')
}

private fun Any?.requireObject(label: String): Map<String, Any?> {
    @Suppress("UNCHECKED_CAST")
    return this as? Map<String, Any?>
        ?: error("GoreeCloud Search $label must be a JSON object")
}

private fun Any?.requireString(label: String): String =
    this as? String ?: error("GoreeCloud Search $label must be a string")

private fun Map<String, Any?>.requireString(key: String): String =
    this[key].requireString(key)

private fun Map<String, Any?>.optionalString(key: String): String? {
    val value = this[key] ?: return null
    return value as? String ?: error("GoreeCloud Search $key must be a string or null")
}

private fun Map<String, Any?>.requireBoolean(key: String): Boolean =
    this[key] as? Boolean ?: error("GoreeCloud Search $key must be a boolean")

private fun Map<String, Any?>.optionalBoolean(key: String): Boolean? {
    val value = this[key] ?: return null
    return value as? Boolean ?: error("GoreeCloud Search $key must be a boolean or null")
}

private fun Map<String, Any?>.requireInt(key: String): Int {
    val value = this[key] as? Long ?: error("GoreeCloud Search $key must be an integer")
    check(value in Int.MIN_VALUE.toLong()..Int.MAX_VALUE.toLong()) {
        "GoreeCloud Search $key is outside the integer range"
    }
    return value.toInt()
}

private fun Map<String, Any?>.requireArray(key: String): List<Any?> =
    this[key] as? List<Any?> ?: error("GoreeCloud Search $key must be an array")

private fun Map<String, Any?>.requireExactKeys(vararg keys: String) {
    check(this.keys == keys.toSet()) {
        "GoreeCloud Search response fields are incompatible"
    }
}

private class JsonParser(private val source: String) {
    private var offset = 0

    fun parse(): Any? {
        skipWhitespace()
        val value = parseValue()
        skipWhitespace()
        check(offset == source.length) { "GoreeCloud Search JSON contains trailing data" }
        return value
    }

    private fun parseValue(): Any? {
        check(offset < source.length) { "GoreeCloud Search JSON ended unexpectedly" }
        return when (source[offset]) {
            '{' -> parseObject()
            '[' -> parseArray()
            '"' -> parseString()
            't' -> parseLiteral("true", true)
            'f' -> parseLiteral("false", false)
            'n' -> parseLiteral("null", null)
            '-', in '0'..'9' -> parseNumber()
            else -> error("GoreeCloud Search JSON value is invalid")
        }
    }

    private fun parseObject(): Map<String, Any?> {
        expect('{')
        skipWhitespace()
        val result = linkedMapOf<String, Any?>()
        if (consume('}')) return result
        while (true) {
            skipWhitespace()
            val key = parseString()
            check(!result.containsKey(key)) { "GoreeCloud Search JSON contains a duplicate field" }
            skipWhitespace()
            expect(':')
            skipWhitespace()
            result[key] = parseValue()
            skipWhitespace()
            if (consume('}')) return result
            expect(',')
            skipWhitespace()
        }
    }

    private fun parseArray(): List<Any?> {
        expect('[')
        skipWhitespace()
        val result = mutableListOf<Any?>()
        if (consume(']')) return result
        while (true) {
            result += parseValue()
            skipWhitespace()
            if (consume(']')) return result
            expect(',')
            skipWhitespace()
        }
    }

    private fun parseString(): String {
        expect('"')
        val result = StringBuilder()
        while (offset < source.length) {
            val character = source[offset++]
            when {
                character == '"' -> return result.toString()
                character == '\\' -> {
                    check(offset < source.length) { "GoreeCloud Search JSON escape is incomplete" }
                    when (val escaped = source[offset++]) {
                        '"' -> result.append('"')
                        '\\' -> result.append('\\')
                        '/' -> result.append('/')
                        'b' -> result.append('\b')
                        'f' -> result.append('\u000C')
                        'n' -> result.append('\n')
                        'r' -> result.append('\r')
                        't' -> result.append('\t')
                        'u' -> {
                            check(offset + 4 <= source.length) {
                                "GoreeCloud Search JSON unicode escape is incomplete"
                            }
                            val code = source.substring(offset, offset + 4).toIntOrNull(16)
                                ?: error("GoreeCloud Search JSON unicode escape is invalid")
                            result.append(code.toChar())
                            offset += 4
                        }
                        else -> error("GoreeCloud Search JSON escape is invalid: $escaped")
                    }
                }
                character.code < 0x20 -> error("GoreeCloud Search JSON string contains a control character")
                else -> result.append(character)
            }
        }
        error("GoreeCloud Search JSON string is unterminated")
    }

    private fun parseNumber(): Number {
        val start = offset
        consume('-')
        check(offset < source.length) { "GoreeCloud Search JSON number is incomplete" }
        if (consume('0')) {
            check(offset >= source.length || !source[offset].isDigit()) {
                "GoreeCloud Search JSON number has a leading zero"
            }
        } else {
            check(source[offset] in '1'..'9') { "GoreeCloud Search JSON number is invalid" }
            while (offset < source.length && source[offset].isDigit()) offset++
        }
        var floating = false
        if (consume('.')) {
            floating = true
            check(offset < source.length && source[offset].isDigit()) {
                "GoreeCloud Search JSON fraction is invalid"
            }
            while (offset < source.length && source[offset].isDigit()) offset++
        }
        if (offset < source.length && (source[offset] == 'e' || source[offset] == 'E')) {
            floating = true
            offset++
            if (offset < source.length && (source[offset] == '+' || source[offset] == '-')) offset++
            check(offset < source.length && source[offset].isDigit()) {
                "GoreeCloud Search JSON exponent is invalid"
            }
            while (offset < source.length && source[offset].isDigit()) offset++
        }
        val token = source.substring(start, offset)
        return if (floating) {
            token.toDoubleOrNull()?.takeIf { it.isFinite() }
                ?: error("GoreeCloud Search JSON number is invalid")
        } else {
            token.toLongOrNull() ?: error("GoreeCloud Search JSON integer is invalid")
        }
    }

    private fun parseLiteral(token: String, value: Any?): Any? {
        check(source.startsWith(token, offset)) { "GoreeCloud Search JSON literal is invalid" }
        offset += token.length
        return value
    }

    private fun expect(character: Char) {
        check(consume(character)) { "GoreeCloud Search JSON expected '$character'" }
    }

    private fun consume(character: Char): Boolean {
        if (offset < source.length && source[offset] == character) {
            offset++
            return true
        }
        return false
    }

    private fun skipWhitespace() {
        while (offset < source.length && (
                source[offset] == ' ' ||
                    source[offset] == '\t' ||
                    source[offset] == '\n' ||
                    source[offset] == '\r'
            )
        ) {
            offset++
        }
    }
}
