# GoreeCloud Index — Competitive Objectives

## Status

**Release lifecycle: Development.** This document defines benchmark objectives, not current parity or superiority claims. Authoritative `main` is `5ae1a1debc79a7adc8b65266bb947baf633d4d1f`; the integrated `0.3.0-dev` line includes Applications, bounded Settings navigation, authority-gated Contacts source, reconciled query/runtime improvements, and GLAZE UI V1.6 source adoption. Production acceptance and Stable qualification remain false.

## Benchmark References

Relevant capability references include Apple Spotlight, Windows Search/Start, Android system/launcher search, Samsung Finder/system search, GNOME Shell search, KDE Plasma KRunner, Raycast, and Alfred. They guide capability expectations only; GoreeCloud Index remains original GoreeCloud-owned software and must not copy proprietary code/assets/trade dress.

## Capabilities Worth Matching

- Immediate predictable invocation.
- Fast local results.
- Application, file/folder, contact, and calendar discovery where authorized.
- Useful ordering, categories, actions, accessibility, and incremental results.
- Graceful unavailable/slow-provider handling.

## Areas GoreeCloud Intends to Exceed

### Provider Transparency

- Explicit source/provider identity and local/remote/mixed processing location.
- Provider-specific permissions and authority state.
- Distinct authorization-required, failure, timeout, cancellation, and healthy-result behavior.

### Privacy and Authority

- No silent private-source dispatch when authority evidence is missing.
- Android permission, Privacy Shield data-use authority, and GoreeCloud Identity authorization remain separate gates.
- Constrained Privacy Shield decisions are not silently widened.
- Non-browsing private providers can refuse blank-query enumeration.
- No silent local-data upload to improve Internet results.
- Authentication never becomes blanket source authorization.

### Extensibility and Reliability

- Versionable provider contracts.
- Structured concurrency, cancellation, bounded timeouts, and provider failure isolation.
- Provider-scoped provenance and typed actions.
- Future capability negotiation without source ownership takeover.

### GoreeCloud Integration

- GoreeCloud Search remains the Internet/current-information authority.
- Privacy Shield governs data use.
- Identity governs platform identity/authority.
- Wardveil governs security/trust evidence.
- Everkeep governs continuity for durable configuration.
- Mesh coordinates first-party capability discovery.
- Glaze UI 2.1.0 remains the current Stable presentation target.

## Current Development Differentiators

Accepted source already provides local application search, source identity, structured concurrency, cancellation, bounded timeouts, and fail-closed provider eligibility.

The current branch additionally implements a Contacts provider that cannot run without all required permission/authority evidence, reads only minimal contact display metadata, avoids blank-query enumeration, and returns to Android's contact surface for actions. Current runtime deliberately leaves Contacts authority unavailable rather than simulating platform approval.

## Behaviors Intentionally Rejected

Mandatory cloud round-trips for locally answerable queries; silent third-party enrollment; advertising/sponsorship ranking; undisclosed profiling; unrestricted provider access to unrelated data; authentication-as-authorization; hidden source origin; monolithic takeover of source data; unsupported privacy/security badges; or presenting source implementation as accepted platform integration.

## Accepted Main Evidence

`cc3cc21d6e11dad026253c3371c3b67663d3b726` passed exact-main workflow `33431294298`; APK SHA-256 `54139051e4243ca83b245338ed5e40680edd4ffd3e673a12dfff6b75eed3e99f`; artifact `9772740479`; artifact digest `sha256:87162d517a95622f35c46a63992ed1c545e125ee620c0fa544e265285d61a22c`.

## Long-Term Objective

A fast, local-first universal search layer with explicit provider authority, optional external providers, GoreeCloud Search delegation for Internet results, evidence-backed platform integrations, accessible Glaze UI presentation, and recoverable original GoreeCloud-owned implementation. Every claimed advantage remains evidence-gated.
