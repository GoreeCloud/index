# GoreeCloud Index — Architecture

## Status

**Release lifecycle: Development.** Latest accepted runtime-bearing checkpoint is `34446cc519afb87bca27b0c3e6639db01ff114b8`. The current `0.3.1-dev` fixed-origin HTTPS Search client is an unmerged candidate layered on that exact authoritative baseline. Production acceptance and Stable qualification remain false.

## Authority Model

Index coordinates universal search; it does not own provider resources.

- Android remains authoritative for launcher applications, ContactsProvider records, runtime permissions, and Android handoffs.
- **GoreeCloud Search remains authoritative** for Internet/web/current-information search.
- **Index remains the universal-search/indexing authority** for provider selection, query coordination, composition, provenance, and safe result actions.
- **Privacy Shield remains authoritative** for privacy decisions and purpose/processing/destination constraints.
- **GoreeCloud Identity remains authoritative** for identity, authentication, and authorization evidence.
- Wardveil Security remains authoritative for security evidence.
- Everkeep remains authoritative for applicable durable-state continuity.
- GoreeCloud Mesh may coordinate first-party discovery without taking provider authority.
- GoreeCloud Policy and GoreeCloud Observability retain policy and operational-evidence authority.
- Glaze UI governs presentation only and never creates operational authority.

`ALLOW_WITH_CONSTRAINTS` remains fail-closed until returned obligations can be enforced. Missing required evidence produces `AUTHORIZATION_REQUIRED` rather than provider dispatch.

## Query Flow

```text
user / Launcher
  → MainActivity
  → session source selection
  → IndexDevelopmentSourcePolicy
      → sanitize to Applications / Settings / Contacts
      → force localOnly=true
      → preserve supplied authority evidence
  → IndexQueryEngine.searchIncrementally
      → query normalization
      → provider applicability
      → authority and processing-location checks
      → bounded concurrent dispatch
      → timeout / cancellation / failure isolation
      → provider-result validation
      → deterministic composition
      → incremental IndexSearchSnapshot
  → IndexRoot
      → source controls + coarse authority explanation
      → typed validated actions
```

## Incremental Composition

One `Flow<IndexSearchSnapshot>` path handles initial state, provider completion, deterministic re-ranking, and final state. One-shot search consumes that same path to its last snapshot.

Cross-provider comparison uses Index-owned normalized textual relevance instead of comparing unrelated provider-private score scales. Same-provider scoring stays a same-provider input. Equal-relevance composition can prefer healthier state and then LOCAL → MIXED → REMOTE processing location. Stable identity provides a deterministic final tie.

## Source Controls and Permission Review

`IndexDevelopmentSourcePolicy` exposes only integrated local providers and rejects remote Search from the selectable set. Source choice is session-only.

`IndexSourceAuthorityProjection` reports only missing authority domains needed to explain why ContactsProvider is unavailable. `IndexPermissionReviewPolicy` offers Android Contacts permission review only when the Android permission itself is missing; it cannot satisfy Privacy Shield or Identity.

## GoreeCloud Search Boundary

The provider remains transport-neutral. Production source validates Search API/provider contract, capability identity/freshness, endpoint/result bounds, Privacy Shield reference intent, authenticated Identity requester metadata, request/response binding, degraded state, and safe URLs/actions.

Development MainActivity does not register a live Search client/provider and Android does not request Internet permission. No remote fallback is created.

## GLAZE UI V1.6

`GlazeV16Contract` is the active native source projection. It binds current Stable shared source/runtime identity and adds fail-closed capability presentation for disabled, unavailable, restricted, unsupported, permission-required, unknown, and conflict states.

The shared JavaScript runtime is not embedded. No capability presentation can grant authorization, request permission automatically, choose provider precedence, or trigger consequential execution. Application-specific rendered/native acceptance is still blocked.

## Platform Contract

Contract `0.4` explicitly evaluates Manager, Privacy Shield, Wardveil Security, Everkeep, Glaze UI, Mesh, Identity, Policy, and Observability. GoreeCloud Sync remains separately governed.

## Failure Model

- Missing authority → no dispatch; `AUTHORIZATION_REQUIRED`.
- Provider timeout → `TIMED_OUT`; healthy siblings preserved.
- Provider failure → sanitized `FAILED`; healthy siblings preserved.
- Cancellation → propagates.
- Remote/mixed provider under Development local-only → no dispatch.
- Invalid result provenance/action → fail closed.
- Glaze capability conflict/unknown/restricted state → disabled presentation, no inferred authority.

## Release Boundary

Source/build validation does not satisfy representative-device, accessibility, performance, platform-runtime, rollback/recovery, signing/distribution, Release Candidate, production, or Stable gates.
