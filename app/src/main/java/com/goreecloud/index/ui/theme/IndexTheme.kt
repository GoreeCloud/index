package com.goreecloud.index.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

private val IndexShapes = Shapes(
    small = RoundedCornerShape(14.dp),
    medium = RoundedCornerShape(20.dp),
    large = RoundedCornerShape(28.dp),
)

private val GlazeLightColorScheme = lightColorScheme(
    primary = Color(GlazeV16Contract.DEEP_TEAL),
    onPrimary = Color.White,
    primaryContainer = Color(GlazeV16Contract.SOFT_AQUA),
    onPrimaryContainer = Color(GlazeV16Contract.DEEP_GRAPHITE),
    secondary = Color(GlazeV16Contract.MINERAL_TEAL),
    onSecondary = Color.White,
    background = Color(GlazeV16Contract.FROST_WHITE),
    onBackground = Color(GlazeV16Contract.COOL_GRAPHITE),
    surface = Color(GlazeV16Contract.CRYSTAL_WHITE),
    onSurface = Color(GlazeV16Contract.COOL_GRAPHITE),
    surfaceVariant = Color(GlazeV16Contract.ICE_BLUE),
    onSurfaceVariant = Color(GlazeV16Contract.SLATE_GRAY),
    outline = Color(GlazeV16Contract.CLOUD_GRAY),
)

private val GlazeDarkColorScheme = darkColorScheme(
    primary = Color(GlazeV16Contract.SOFT_AQUA),
    onPrimary = Color(GlazeV16Contract.BLUE_BLACK),
    primaryContainer = Color(GlazeV16Contract.DEEP_TEAL),
    onPrimaryContainer = Color(GlazeV16Contract.CRYSTAL_WHITE),
    secondary = Color(GlazeV16Contract.MINERAL_TEAL),
    onSecondary = Color(GlazeV16Contract.BLUE_BLACK),
    background = Color(GlazeV16Contract.BLUE_BLACK),
    onBackground = Color(GlazeV16Contract.CRYSTAL_WHITE),
    surface = Color(GlazeV16Contract.DEEP_GRAPHITE),
    onSurface = Color(GlazeV16Contract.CRYSTAL_WHITE),
    surfaceVariant = Color(GlazeV16Contract.COOL_GRAPHITE),
    onSurfaceVariant = Color(GlazeV16Contract.CLOUD_GRAY),
    outline = Color(GlazeV16Contract.SLATE_GRAY),
)

/**
 * GoreeCloud Index's deterministic native GLAZE UI V1.6 source projection.
 *
 * The shared JavaScript runtime is not embedded in Compose. Presentation consumes only state
 * already owned by Index/platform authorities. Repository-local rendered/accessibility/device
 * acceptance remains separately gated.
 */
@Composable
fun GoreeCloudIndexTheme(content: @Composable () -> Unit) {
    val colorScheme = if (isSystemInDarkTheme()) GlazeDarkColorScheme else GlazeLightColorScheme
    MaterialTheme(colorScheme = colorScheme, shapes = IndexShapes, content = content)
}
