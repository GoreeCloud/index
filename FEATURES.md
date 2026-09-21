# GoreeCloud Index — Features

## Status

**Release lifecycle: Development.** Version `0.3.1-dev`. Production acceptance and Stable qualification remain false.

## Integrated Development Features

### Search Core

- Provider-neutral contracts and provenance.
- Deterministic normalized ranking and provider-scoped deduplication.
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

### Contacts Permission Review

- Explicit user-triggered Android Contacts permission review.
- Android remains permission authority.
- Privacy Shield and GoreeCloud Identity remain independent requirements.
- No automatic permission request or platform-authority bypass.

### GoreeCloud Search Foundation

- Search API/provider-contract compatibility.
- Cycle-safe Search capability gating requiring external-only Index-originated delegation with Index re-entry and fallback disabled.
- Capability preflight and freshness checks.\n- Concrete `https://search.goreecloud.com` capability-discovery and JSON-body POST transport with redirect refusal, response bounds, strict JSON parsing, and credential/reference redaction.\n- Authenticated-Development acceptance mode requiring both Privacy Shield and GoreeCloud Identity while still accepting explicitly non-production capability evidence for source/CI qualification.
- Privacy Shield constrained intent/reference handling.
- Independent GoreeCloud Identity requester-credential requirement for Production delegation.
- Query/category/limit minimization, response binding, degradation propagation, URL/action validation, and sensitive rendering controls.
- Concrete fixed-origin HTTPS transport source and Android `INTERNET` declaration are present, but the current local-only Development UI does not register or enable the remote Search provider.

### GLAZE UI V1.6 Source Adoption

- Native `1.6.0` source contract bound to current shared Stable authority.
- Deterministic light/dark semantic mapping.
- Accessibility-first solid fallback.
- Fail-closed capability/conflict/permission-required presentation.
- No automatic authorization, permission request, provider precedence, navigation, or consequential execution.

## Not Yet Accepted

Live Search transport and user controls; accepted Privacy Shield/Identity/Manager/Wardveil/Everkeep/Mesh/Policy/Observability runtime integrations; Contacts runtime enablement; GLAZE UI rendered/native consumer acceptance; representative-device accessibility/performance/OEM qualification; Files/Calendar/media/additional providers; durable indexing; production signing/distribution; rollback/recovery; Release Candidate; production; and Stable qualification.
