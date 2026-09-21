package com.goreecloud.index.ui.theme

/**
 * Repository-local native projection of GLAZE UI V1.6 / 1.6.0 Stable presentation semantics.
 *
 * Index supplies already-owned capability and authority state. This contract never grants
 * authorization, requests permission automatically, selects provider precedence, navigates
 * automatically, or executes a consequential fallback.
 *
 * Source adoption is not application-level acceptance. Rendered/native accessibility,
 * representative-device/form-factor, performance, rollback, release, and production evidence
 * remain separate GoreeCloud Index gates.
 */
object GlazeV16Contract {
    const val VERSION = "1.6.0"
    const val PRODUCT_LABEL = "GLAZE UI V1.6"
    const val STABLE_RELEASE_SOURCE = "a7180679ea851389e0f3004515f9a25f420e716d"
    const val SOURCE_QUALIFICATION_ANCHOR = "c7509c79256b04b0aa67cb9dd0737d7588e0ae4a"
    const val QUALIFICATION_EVIDENCE_INTEGRATION = "354f5759385c28596fcfec26a3ad525e89fb1c35"
    const val STABLE_RUNTIME_ENTRYPOINT = "js/glaze-v1.6.0.mjs"
    const val SHARED_ROLLBACK_BASELINE = "1.5.1"
    const val INDEX_SOURCE_ROLLBACK_BASELINE = "1.4.0"

    const val DEEP_TEAL = 0xFF0F6B6F
    const val MINERAL_TEAL = 0xFF1C8A8D
    const val SOFT_AQUA = 0xFF8FD6D2
    const val FROST_WHITE = 0xFFF4F8FA
    const val CRYSTAL_WHITE = 0xFFFBFDFE
    const val ICE_BLUE = 0xFFDCECF6
    const val CLOUD_GRAY = 0xFFDCE3E8
    const val SLATE_GRAY = 0xFF7E8D99
    const val COOL_GRAPHITE = 0xFF151C22
    const val DEEP_GRAPHITE = 0xFF0E1419
    const val BLUE_BLACK = 0xFF070C11

    const val GENERAL_TARGET_DP = 48
    const val TOUCH_ASSISTANCE_TARGET_DP = 56
    const val MAX_DECORATIVE_ENVIRONMENTAL_TINT_INFLUENCE = 0.08f

    const val REMOTE_OPTICAL_CONTEXT_ALLOWED = false
    const val TELEMETRY_REQUIRED_FOR_PRESENTATION = false
    const val CAMERA_REQUIRED_FOR_PRESENTATION = false
    const val PERMISSION_REQUEST_AUTOMATIC = false
    const val AUTHORIZATION_INFERRED = false
    const val PROVIDER_PRECEDENCE_INFERRED = false
    const val CONSEQUENTIAL_EXECUTION_AUTOMATIC = false

    enum class OpticalMode { AdaptiveOptical, SolidAccessible }

    enum class CapabilityState {
        Available,
        Disabled,
        TemporarilyUnavailable,
        Restricted,
        Unsupported,
        PermissionRequired,
        Unknown,
        Conflict,
    }

    data class CapabilityRecord(
        val id: String,
        val state: CapabilityState,
        val authority: String,
    )

    data class ActionPresentation(
        val enabled: Boolean,
        val state: CapabilityState,
        val reasonCodes: Set<String>,
        val automaticExecutionAllowed: Boolean = false,
        val authorizationInferred: Boolean = false,
        val providerPrecedenceInferred: Boolean = false,
        val permissionRequestAutomatic: Boolean = false,
    )

    fun opticalMode(
        forcedColors: Boolean,
        reducedTransparency: Boolean,
    ): OpticalMode = if (forcedColors || reducedTransparency) {
        OpticalMode.SolidAccessible
    } else {
        OpticalMode.AdaptiveOptical
    }

    fun targetFloorDp(touchAssistance: Boolean): Int =
        if (touchAssistance) TOUCH_ASSISTANCE_TARGET_DP else GENERAL_TARGET_DP

    fun resolveAction(
        requiredCapabilityIds: Set<String>,
        capabilities: Collection<CapabilityRecord>,
    ): ActionPresentation {
        if (requiredCapabilityIds.isEmpty()) {
            return ActionPresentation(true, CapabilityState.Available, emptySet())
        }

        val recordsById = capabilities.groupBy { it.id }
        val reasons = linkedSetOf<String>()
        var resolved = CapabilityState.Available

        for (capabilityId in requiredCapabilityIds.sorted()) {
            val records = recordsById[capabilityId].orEmpty()
            val state = when {
                records.isEmpty() -> CapabilityState.Unknown
                records.size > 1 -> CapabilityState.Conflict
                else -> records.single().state
            }
            resolved = strongest(resolved, state)
            when (state) {
                CapabilityState.Available -> Unit
                CapabilityState.Disabled -> reasons += "local-state-disabled:$capabilityId"
                CapabilityState.TemporarilyUnavailable ->
                    reasons += "capability-temporarily-unavailable:$capabilityId"
                CapabilityState.Restricted ->
                    reasons += "restricted-by-authority:$capabilityId"
                CapabilityState.Unsupported -> reasons += "runtime-unsupported:$capabilityId"
                CapabilityState.PermissionRequired -> reasons += "permission-required:$capabilityId"
                CapabilityState.Unknown -> reasons += "capability-state-unknown:$capabilityId"
                CapabilityState.Conflict -> reasons += "capability-conflict:$capabilityId"
            }
        }

        return ActionPresentation(
            enabled = resolved == CapabilityState.Available,
            state = resolved,
            reasonCodes = reasons,
        )
    }

    private fun strongest(current: CapabilityState, candidate: CapabilityState): CapabilityState {
        val order = mapOf(
            CapabilityState.Available to 0,
            CapabilityState.Disabled to 1,
            CapabilityState.TemporarilyUnavailable to 2,
            CapabilityState.Unsupported to 3,
            CapabilityState.PermissionRequired to 4,
            CapabilityState.Restricted to 5,
            CapabilityState.Unknown to 6,
            CapabilityState.Conflict to 7,
        )
        return if (order.getValue(candidate) > order.getValue(current)) candidate else current
    }
}
