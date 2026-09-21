package com.goreecloud.index.ui.theme

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GlazeV16ContractTest {
    @Test
    fun repositoryContractTargetsCurrentStableGlazeRelease() {
        assertEquals("1.6.0", GlazeV16Contract.VERSION)
        assertEquals(
            "a7180679ea851389e0f3004515f9a25f420e716d",
            GlazeV16Contract.STABLE_RELEASE_SOURCE,
        )
        assertEquals(
            "c7509c79256b04b0aa67cb9dd0737d7588e0ae4a",
            GlazeV16Contract.SOURCE_QUALIFICATION_ANCHOR,
        )
        assertEquals("js/glaze-v1.6.0.mjs", GlazeV16Contract.STABLE_RUNTIME_ENTRYPOINT)
        assertEquals("1.5.1", GlazeV16Contract.SHARED_ROLLBACK_BASELINE)
        assertEquals("1.4.0", GlazeV16Contract.INDEX_SOURCE_ROLLBACK_BASELINE)
    }

    @Test
    fun accessibilityStateForcesSolidPresentation() {
        assertEquals(
            GlazeV16Contract.OpticalMode.SolidAccessible,
            GlazeV16Contract.opticalMode(forcedColors = true, reducedTransparency = false),
        )
        assertEquals(
            GlazeV16Contract.OpticalMode.SolidAccessible,
            GlazeV16Contract.opticalMode(forcedColors = false, reducedTransparency = true),
        )
    }

    @Test
    fun presentationNeverManufacturesOperationalAuthority() {
        assertFalse(GlazeV16Contract.REMOTE_OPTICAL_CONTEXT_ALLOWED)
        assertFalse(GlazeV16Contract.TELEMETRY_REQUIRED_FOR_PRESENTATION)
        assertFalse(GlazeV16Contract.CAMERA_REQUIRED_FOR_PRESENTATION)
        assertFalse(GlazeV16Contract.PERMISSION_REQUEST_AUTOMATIC)
        assertFalse(GlazeV16Contract.AUTHORIZATION_INFERRED)
        assertFalse(GlazeV16Contract.PROVIDER_PRECEDENCE_INFERRED)
        assertFalse(GlazeV16Contract.CONSEQUENTIAL_EXECUTION_AUTOMATIC)
    }

    @Test
    fun duplicateCapabilityOwnershipFailsClosed() {
        val result = GlazeV16Contract.resolveAction(
            requiredCapabilityIds = setOf("service.search"),
            capabilities = listOf(
                GlazeV16Contract.CapabilityRecord(
                    id = "service.search",
                    state = GlazeV16Contract.CapabilityState.Available,
                    authority = "goreecloud-search",
                ),
                GlazeV16Contract.CapabilityRecord(
                    id = "service.search",
                    state = GlazeV16Contract.CapabilityState.Available,
                    authority = "duplicate-provider",
                ),
            ),
        )
        assertFalse(result.enabled)
        assertEquals(GlazeV16Contract.CapabilityState.Conflict, result.state)
        assertTrue(result.reasonCodes.contains("capability-conflict:service.search"))
        assertFalse(result.automaticExecutionAllowed)
        assertFalse(result.authorizationInferred)
        assertFalse(result.providerPrecedenceInferred)
        assertFalse(result.permissionRequestAutomatic)
    }

    @Test
    fun permissionRequiredStateDoesNotRequestPermissionAutomatically() {
        val result = GlazeV16Contract.resolveAction(
            requiredCapabilityIds = setOf("contacts.read"),
            capabilities = listOf(
                GlazeV16Contract.CapabilityRecord(
                    id = "contacts.read",
                    state = GlazeV16Contract.CapabilityState.PermissionRequired,
                    authority = "android",
                ),
            ),
        )
        assertFalse(result.enabled)
        assertEquals(GlazeV16Contract.CapabilityState.PermissionRequired, result.state)
        assertTrue(result.reasonCodes.contains("permission-required:contacts.read"))
        assertFalse(result.permissionRequestAutomatic)
    }
}
