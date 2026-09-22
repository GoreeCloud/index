# GoreeCloud Index — Features

## Status

**Release lifecycle: Development / nonconformant.** Version `0.3.1-dev`. Production Acceptance and Stable qualification remain false.

## Integrated Development Features

### Search Core

- Provider-neutral contracts and provenance.
- Deterministic Unicode-normalized ranking and provider-scoped deduplication.
- Concurrent provider execution with bounded timeouts and cancellation propagation.
- Partial/degraded result preservation.
- Bounded provider fan-out and result counts.
- Incremental `Flow` result delivery with one-shot/final-snapshot equivalence.

### Local Providers

- Launcher-visible Applications search.
- Bounded static Android Settings navigation.
- Authority-gated Android Contacts search with minimized fields and no blank enumeration.

### Session Source Controls

- Session-scoped enable/disable controls for Applications, Settings, and Contacts.
- Enforced Development local-only mode.
- Remote Search cannot be enabled through source controls.
- Privacy-safe missing-authority explanation.

### Contacts Permission Review and Authority Boundaries

- Explicit user-triggered Android Contacts permission review.
- Android remains permission authority.
- Privacy Shield and GoreeCloud Identity remain independent requirements.
- Source-controlled Privacy Shield application declarations and exact-scope Contacts decision binding.
- Fail-closed platform-authority gateway when authoritative GoreeCloud evidence is unavailable.
- No automatic permission request or platform-authority bypass.

### GoreeCloud Search Foundation

- Search API/provider-contract compatibility.
- Cycle-safe Search capability gating requiring external-only Index-originated delegation with Index re-entry and fallback disabled.
- Fixed-origin HTTPS Search client for capability discovery and bounded query dispatch.
- Privacy Shield constrained intent/reference handling.
- Independent GoreeCloud Identity requester-credential requirement for Production delegation.
- Query/category/limit minimization, response binding, degradation propagation, URL/action validation, response/media/size validation, redirect refusal, and sensitive rendering/wire-data controls.
- Separate credential-free fixed-origin `/readyz` runtime-readiness gate before Privacy Shield authorization, Identity requester acquisition, or Search query dispatch.
- A not-ready runtime fails closed without authority acquisition or query transmission.
- Android `INTERNET` permission is present only for the dormant fixed-origin HTTPS client and does not make remote Search user-enableable; live Search registration remains absent in Development.

### GLAZE UI V1.6 Source Adoption

- Native `1.6.0` source contract bound to current shared Stable authority.
- Deterministic light/dark semantic mapping.
- Accessibility-first solid fallback.
- Fail-closed capability/conflict/permission-required presentation.
- No automatic authorization, permission request, provider precedence, navigation, or consequential execution.

### Platform Contract 0.4

- All nine Integral Platform Systems are explicitly evaluated.
- Unsupported or unverified runtime integrations remain blocked/nonconformant.
- GoreeCloud Sync remains separately governed.

## Not Yet Accepted

Live Search registration and remote-provider user controls; accepted Privacy Shield/Identity/Manager/Wardveil/Everkeep/Mesh/Policy/Observability runtime integrations; Contacts runtime enablement; GLAZE UI rendered/native consumer acceptance; representative-device accessibility/performance/OEM qualification; Files/Calendar/media/additional providers; extension/third-party providers; durable provider preferences and local indexing; production signing/distribution; rollback/recovery; Release Candidate; Production Acceptance; production deployment; and Stable qualification.

Draft PR #46 is an unmerged Development hardening candidate and is not included in the implemented feature set above.
