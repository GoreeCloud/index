# GoreeCloud Index — Features

## Status

**Release lifecycle: Development.** Version `0.3.0-dev`. Production acceptance and Stable qualification remain false.

## Implemented Development Features

### Search Core

- Provider-neutral query, result, action, provenance, health/degradation, and authority models.
- Structured concurrent provider execution with cancellation propagation.
- Bounded per-provider timeouts and sanitized failure states.
- Partial-result preservation when another provider fails, times out, or is degraded.
- Deterministic NFKC query normalization and result ordering.
- Provider-scoped deduplication and bounded result counts.
- Provider contract-version compatibility checks.
- Fail-closed provider allowlisting and local-only gating.

### Applications · On-device

- Launcher-visible application discovery.
- No unrestricted package visibility.
- Exact component launch actions.
- Local processing.

### Settings · On-device

- Bounded static Settings destination catalog.
- No setting-value or private device-state reads.
- No blank-query enumeration.
- Closed Settings action allowlist.

### Contacts · On-device

- Android ContactsProvider-backed source.
- Minimized ID/lookup-key/display-name projection.
- No phone/email field reads in the current slice.
- No blank-query enumeration.
- Typed contact-view action.
- Android permission + Privacy Shield + GoreeCloud Identity authority requirements.
- Fail-closed runtime state: current Development gateway does not supply accepted platform authority, so Contacts is not dispatched.

### GoreeCloud Search Provider Foundation

- Search API v1 response binding.
- Index provider contract v1 compatibility.
- `search.query` capability preflight with freshness/authority checks.
- Canonical endpoint and published result-bound validation.
- Query/category/limit minimization and response integrity checks.
- Partial-degradation propagation.
- URL validation and safe web result actions.

This is source infrastructure only. The shipped runtime has no live Search transport registration and no Android Internet permission.

### GLAZE UI V1.4 Native Foundation

- Deterministic GoreeCloud semantic light/dark schemes.
- Accessibility-first fallback behavior.
- Source-aware result and issue presentation.
- V1.4 optical-policy boundaries without camera, wallpaper, telemetry, browsing-content, or remote-context collection.

Current Stable consumer target is V1.6 / `1.6.0`; migration and full application acceptance remain open.

## Platform Contract

The repository declares Contract `0.4` and explicitly evaluates Manager, Privacy Shield, Wardveil Security, Everkeep, Glaze UI, Mesh, Identity, Policy, and Observability. Missing runtime evidence remains blocked or migration-required rather than being upgraded by metadata.

## Not Yet Accepted

- Live GoreeCloud Search transport, discovery, authentication, TLS/proxy path, and Internet-provider controls.
- Contacts runtime enablement and user decision/permission flow.
- Accepted Privacy Shield, Identity, Wardveil, Everkeep, Mesh, Manager, Policy, and Observability runtime integration.
- GLAZE UI V1.6 source migration and full rendered/native consumer acceptance.
- Files/folders, calendar, media, additional application-content, connected-device, extension, and third-party providers.
- Local content indexing and incremental/streaming result delivery.
- Representative-device accessibility, localization/RTL, performance, and OEM/form-factor acceptance.
- Production signing/distribution, rollback/recovery acceptance, Release Candidate, production, or Stable qualification.

## Deprecated or Removed Features

None.
