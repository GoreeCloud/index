package com.goreecloud.index.provider.search

import java.time.Instant

internal const val PRIVACY_SHIELD_SEARCH_REQUIRED_OUTCOME = "ALLOW_WITH_CONSTRAINTS"
internal const val PRIVACY_SHIELD_SEARCH_CAPABILITY_REFERENCE_MAX_LENGTH = 512
internal val PRIVACY_SHIELD_SEARCH_REQUIRED_OBLIGATIONS: Set<String> = setOf(
    "record_privacy_evidence",
    "generate_privacy_receipt",
    "enforce_processing_zone",
)

internal fun isCanonicalPrivacyShieldCapabilityReference(reference: String?): Boolean {
    if (reference == null || !reference.startsWith("psc_") || reference.length <= 4) return false
    if (reference.length > PRIVACY_SHIELD_SEARCH_CAPABILITY_REFERENCE_MAX_LENGTH) return false
    return reference.none { character ->
        character.isWhitespace() || Character.isISOControl(character.code)
    }
}

/**
 * Transport-neutral adapter between Privacy Shield's canonical enforcement
 * result and Index's production GoreeCloud Search authorization client.
 *
 * Private GoreeCloud processing is intentionally constrained. The adapter
 * accepts only the exact constraint set whose authority-side evidence/receipt
 * obligations are satisfied by Privacy Shield and whose processing-zone
 * obligation must be enforced by the Search-side capability verifier. Unknown
 * or additional obligations remain fail-closed.
 */
class PrivacyShieldSearchAuthorizationAdapter(
    private val decisionClient: PrivacyShieldDecisionClient,
    private val clock: () -> Instant = Instant::now,
) : GoreeCloudSearchAuthorizationClient {
    override suspend fun authorize(
        request: GoreeCloudSearchPrivacyAuthorizationRequest,
    ): GoreeCloudSearchPrivacyAuthorization {
        require(request.requestId.isNotBlank()) {
            "Privacy Shield Search authorization request is missing a request identifier"
        }
        val decision = decisionClient.decide(request)
        validateDecision(request, decision, clock())
        return GoreeCloudSearchPrivacyAuthorization(
            capabilityTokenReference = decision.capabilityTokenReference!!.trim(),
        )
    }

    private fun validateDecision(
        request: GoreeCloudSearchPrivacyAuthorizationRequest,
        decision: PrivacyShieldSearchDecision,
        now: Instant,
    ) {
        check(decision.decisionId.isNotBlank()) {
            "Privacy Shield Search decision is missing a decision identifier"
        }
        check(decision.requestId == request.requestId) {
            "Privacy Shield Search decision does not match the authorization request"
        }
        check(decision.outcome == PRIVACY_SHIELD_SEARCH_REQUIRED_OUTCOME) {
            "Privacy Shield Search decision does not match the required constrained outcome"
        }
        check(request.operation in decision.permittedOperations) {
            "Privacy Shield Search decision does not permit the Search operation"
        }
        check(decision.processingZone == request.processingZone) {
            "Privacy Shield Search decision does not permit the required processing zone"
        }
        check(request.destination in decision.permittedDestinations) {
            "Privacy Shield Search decision does not permit the GoreeCloud Search destination"
        }
        check(decision.retentionMode == request.retentionMode) {
            "Privacy Shield Search decision does not permit the required retention mode"
        }
        check(decision.obligations == PRIVACY_SHIELD_SEARCH_REQUIRED_OBLIGATIONS) {
            "Privacy Shield Search decision contains an unsupported obligation set"
        }
        if (decision.expiresAt != null) {
            val expiresAt = runCatching { Instant.parse(decision.expiresAt) }.getOrNull()
                ?: error("Privacy Shield Search decision expiry is invalid")
            check(expiresAt.isAfter(now)) {
                "Privacy Shield Search decision is expired"
            }
        }
        val capabilityReference = decision.capabilityTokenReference?.trim()
        check(isCanonicalPrivacyShieldCapabilityReference(capabilityReference)) {
            "Privacy Shield Search decision is missing a canonical capability-token reference"
        }
    }
}

fun interface PrivacyShieldDecisionClient {
    suspend fun decide(
        request: GoreeCloudSearchPrivacyAuthorizationRequest,
    ): PrivacyShieldSearchDecision
}

data class PrivacyShieldSearchDecision(
    val decisionId: String,
    val requestId: String,
    val outcome: String,
    val permittedOperations: Set<String>,
    val processingZone: String,
    val permittedDestinations: Set<String>,
    val retentionMode: String,
    val obligations: Set<String> = emptySet(),
    val expiresAt: String? = null,
    val capabilityTokenReference: String? = null,
)
