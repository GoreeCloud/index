# GoreeCloud Index — Implemented Features

**Record type:** Repository implemented-feature inventory  
**Repository:** `GoreeCloud/index`  
**Lifecycle:** Development / nonconformant  
**Migration state:** **Authoritative on `main` after PR #47 merged as `e70a3b699810f83bc3277a1b56fa2580a3f0fc4e` and default-branch readback verified this record. Legacy Drive roadmap/changelog retirement was subsequently verified.**  
**Repository authority baseline:** `main` at `e70a3b699810f83bc3277a1b56fa2580a3f0fc4e` (PR #47 merged September 22, 2026).  
**Latest application/runtime baseline:** `8de424217d475662d49da9714452b63285ee08d0` (PR #45 merged September 21, 2026); PR #47 is governance/documentation/validator migration and does not promote runtime state.  
**Governing standard:** Standard — Repository Feature Tracking and Changelog Governance, version 1.0, effective September 22, 2026.

## Interpretation

This file records capabilities implemented in the current GoreeCloud Index Development source. It does **not** claim Release Candidate, Production Acceptance, production deployment, Stable qualification, representative-device acceptance, or completed Integral Platform System integration unless separate authoritative evidence establishes those states.

Partially implemented capabilities remain open in `PLANNED-FEATURES.md` until their implementation and acceptance scope is complete.

## Current verified source baseline

The latest application/runtime baseline remains `8de424217d475662d49da9714452b63285ee08d0`, the verified merge of PR #45, **Gate production Search delegation on runtime readiness**. PR #45 exact head `65b3e397b8c80b8bc21e801fcd4314d12f37c46c` passed Platform Contract run `35651653575` and Android Index foundation validation run `35651652655` before integration.

PR #47 established repository-native feature/changelog authority and migrated the repository validator. Final exact head `0f3e5ce0cab24716bb78b03203b88fe60f0941aa` passed Platform Contract run #104 / `35727458531` and Android Index foundation validation run #239 / `35727458037` before squash merge to `e70a3b699810f83bc3277a1b56fa2580a3f0fc4e`. That migration does not itself change application runtime capability.

PR #46 is a separate open Draft candidate at `d223bed56a508023503b3cf2e498734def0c2fa6`; its green CI is candidate evidence only and is not represented here as implemented on `main`.

## Implemented Development capabilities

### Native Android application foundation

- Native Android / Jetpack Compose Index application foundation.
- Production application ID `com.goreecloud.index` and Development application ID `com.goreecloud.index.dev`.
- Current Development version line `0.3.1-dev` / version code `4`.
- Provider-neutral query, result, action, provenance, provider-issue, and search-snapshot models.
- Repository validation, Android lint/unit-test/build validation, APK identity checks, Platform Contract validation, branding validation, and evidence publication paths.

### Deterministic search composition

- Deterministic Unicode-normalized matching and ordering using the current NFKC + `Locale.ROOT` line.
- Provider-scoped deduplication and same-provider ordering semantics without treating private provider score scales as cross-provider authority.
- Index-owned normalized textual relevance across providers.
- Health-aware tie behavior and local-first processing-location tie breaking.
- Bounded provider fan-out and bounded final result counts.
- Validation of invalid or over-limit provider responses without silently treating them as trusted results.

### Asynchronous and incremental provider execution

- Suspendable provider execution with structured concurrency.
- Concurrent provider dispatch under failure isolation.
- Bounded per-provider timeouts and distinct failed/timed-out provider issue states.
- Cancellation propagation for superseded search work.
- Preservation of healthy and partial results when another provider fails or degrades.
- Incremental `Flow<IndexSearchSnapshot>` delivery through the same deterministic composition path used by final one-shot results.

### Local Development providers

- Launcher-visible Applications search backed by scoped Android application discovery.
- Bounded static Android Settings navigation/search provider.
- Contacts provider source with minimized local search fields and blank-query protections.
- Contacts remains authority-gated at runtime; presence of provider source does not mean it is dispatchable in the shipped Development application.

### Session source controls and local-only Development policy

- Session-scoped source enable/disable controls for Applications, Settings, and Contacts.
- Sanitization of source selection against the reviewed local provider set.
- Forced `localOnly=true` behavior for the current Development UI path.
- GoreeCloud Search is excluded from Development source controls and cannot be silently enabled through local source selection.
- Privacy-safe explanation of missing authority domains without exposing raw authority evidence.

### Android Contacts permission and authority boundaries

- Explicit user-triggered Android Contacts permission review through Android's permission contract.
- Android `READ_CONTACTS` remains only one prerequisite and cannot substitute for GoreeCloud Privacy Shield or GoreeCloud Identity authority.
- Application-side platform authority gateway and evidence-validation seam for Privacy Shield and Identity.
- Fail-closed default `UnavailableIndexPlatformAuthorityGateway`, so missing platform authority keeps Contacts non-dispatchable.
- Exact-scope Contacts Privacy Shield request binding for `android.contacts` / `search` / `universal-search` / local processing / Index UI destination / no retention.
- Constraint, stale-evidence, mismatched-scope, consent-required, and unknown-authority states fail closed rather than manufacturing permission.

### Privacy Shield application declarations

- Source-controlled Privacy Shield application declaration bounded to the Index application, approved current resources, `search` operation, local processing, no retention, no AI use, no external disclosure/processors, and `production_approved=false`.
- Repository validation rejects unsupported resource expansion, retention/AI/external-processing drift, unsupported capability claims, or false production approval.

### Canonical visual identity and branding provenance

- GoreeCloud branding-assets repository is the canonical visual-identity authority.
- Canonical Index identity is `products/index/app-icon.svg` with exact provenance recorded in repository branding controls.
- Traceable Android launcher derivative and manifest wiring are present.
- Branding validation fails closed on provenance/identity drift and keeps Index visually distinct from GoreeCloud Search and GoreeCloud Launcher.

### GLAZE UI V1.6 source adoption

- Native GLAZE UI V1.6 / `1.6.0` source projection bound to current governed Stable authority.
- Deterministic light/dark semantic mapping and accessibility-first solid fallback.
- Fail-closed presentation for missing, unavailable, restricted, conflicting, or permission-required states.
- Presentation mapping does not itself request permission, mint authorization, choose provider precedence, transmit queries, or execute consequential actions.
- Shared Stable source adoption does not establish Index-local rendered/native/device acceptance.

### Platform Contract 0.4 control plane

- Platform Contract `0.4` is integrated.
- Exactly nine Integral Platform Systems are explicitly evaluated: GoreeCloud Manager, Privacy Shield, Wardveil Security, Everkeep, Glaze UI, GoreeCloud Mesh, GoreeCloud Identity, GoreeCloud Policy, and GoreeCloud Observability.
- GoreeCloud Sync remains separately governed.
- Missing runtime evidence remains blocked/nonconformant instead of being omitted or promoted.

### GoreeCloud Search production-delegation foundation

GoreeCloud Search remains authoritative for Internet/web/current-information retrieval. Current Index source implements a deliberately dormant production-delegation foundation:

- PR #40 added a fail-closed cycle-safety consumer contract requiring `goreecloud.search-index-delegation.v1`, external-only delegation, no Index re-entry, and no delegation fallback before Search dispatch.
- PR #41 added a dormant fixed-origin HTTPS client for `https://search.goreecloud.com`, capability discovery, bounded JSON search dispatch, independent Privacy Shield capability-reference and Identity bearer-header transport, redirect refusal, response-size/media/status validation, sensitive wire-data redaction, and Android `INTERNET` permission required by that dormant client.
- Search remains unregistered in `MainActivity` and unavailable in Development source controls.
- Production Search delegation requires compatible Search capability evidence, operation-scoped Privacy Shield authorization, and a separately supplied GoreeCloud Identity requester credential; missing evidence fails closed before remote dispatch.
- PR #45 added a separate credential-free fixed-origin `/readyz` runtime-readiness prerequisite before Privacy Shield/Identity acquisition or query dispatch.
- `200 + status=ready` permits progression to later authority gates; `503 + status=not_ready` is a normal fail-closed state; malformed identity/status/media/size responses fail as transport errors.
- Readiness carries no query text, bearer credential, Privacy Shield reference, local results, application inventory, or other user data.

No current implemented code path makes this dormant Search integration a production-accepted or user-enabled remote provider.

## Evidence highlights

| Change | Evidence | Implemented result |
| --- | --- | --- |
| PR #1 | merge `331e97507a7b3b7ca3d930771915f1026bf2d4a8`; exact-main workflow `33418751538` | Native Android/Compose foundation, provider-neutral model, Applications provider, deterministic ranking |
| PR #3 | exact head `61672b76443f21bae23d307935f16faf802a50f8`; run `33420429068`; merge `19737c11c59a30a94ee8b6dad8855b449c011eca`; exact-main run `33420873144` | Provider issue/snapshot model, failure-state UI, Android discovery hardening, repository docs/validation |
| PR #4 | exact head `d8b563705ccf1d05444df18e7a593a454d4c4103`; run `33429486374`; merge `e0576bd39e3793bf62c5b4b3f0b887ded4a6d0f9`; exact-main run `33429792389` | Structured concurrent provider runtime, timeouts, cancellation, local-only execution gating |
| PR #7 | exact source `5517a99a1e0c0a411585a881d29fa35b43b8b6ef`; validation `33529147548`; merge `e8c6f63760cc7af9d8fa4ebb742ffe7a9ecfb6e4`; post-merge `33529425449` | Authority-gated Contacts provider source |
| PR #9 | exact source `1498d84dae08234d827ca93942f56de42cd9eb5b`; validation `33531050694`; merge `2ed1bfc6a2be3b81304e8281222f5b12a39e1c3d`; exact-main `33535086566` | Privacy Shield/Identity authority adapter seam and fail-closed gateway |
| PR #14 | exact source `273d1526ffdf39d58e80c57f72be0c03541ccca3`; runs `33539947576` / `33540394379`; merge `4e9672660fdac97d87c142092337e6d0c6cf532e` | Exact-scope Contacts Privacy Shield decision binding |
| PR #15 | exact head `3c8f2be2efc9c7955069ca52a685ebc5d85952ac`; run `33542064849`; merge `6f292862ab7cb2b402cdc64868f02758beb3c2be` | Approved Index visual identity integration and provenance validation |
| PR #37 | exact head `35f1ff2e4e9ea8f360800209924cca017b7e1b9a`; runs `35596231639` / `35596231037`; merge `c97a6ef3958b14cfcd99c15fd8e56222c56bc77d` | Platform Contract 0.4, nine-system model, mandatory repository controls |
| PR #38 | exact head `e7ef8933a1a1efbfe1b944295fd24e4f7bb56c75`; runs `35600510610` / `35600509670`; merge `5ae1a1debc79a7adc8b65266bb947baf633d4d1f` | Modernized runtime/test work plus GLAZE UI V1.6 source adoption |
| PR #39 | exact head `4c66e542aea094384c60248c00b2ab6fcf402731`; runs `35602837175` / `35602836347`; merge `0230a57fd3e96c217ba8908262140ebfd83bee1c` | Current-line documentation reconciliation and Unicode regressions |
| PR #40 | exact head `7026f1fdc9b064e8871bfb50545743fa6ea113e6`; runs `35606889502` / `35606888807`; merge `34446cc519afb87bca27b0c3e6639db01ff114b8` | Cycle-safe Search delegation capability gate |
| PR #41 | integrated runtime checkpoint `7b84ef011a8701f90e737a1ae340d8db09d58e78`; post-merge runs `35625546653` / `35625545378` | Dormant authenticated fixed-origin Search HTTPS client and Development `INTERNET` permission |
| PR #45 | exact head `65b3e397b8c80b8bc21e801fcd4314d12f37c46c`; runs `35651653575` / `35651652655`; runtime baseline `8de424217d475662d49da9714452b63285ee08d0` | Separate fail-closed Search runtime-readiness gate before authority acquisition |
| PR #47 | exact head `0f3e5ce0cab24716bb78b03203b88fe60f0941aa`; Platform #104 / `35727458531`; Android #239 / `35727458037`; merge `e70a3b699810f83bc3277a1b56fa2580a3f0fc4e` | Repository-native feature/changelog authority and migrated validator; no runtime promotion |

## Material limitations

The following remain incomplete or separately acceptance-gated and therefore are **not** represented as fully implemented product capability: live Search provider registration/user controls; accepted live Privacy Shield/Identity authority acquisition for remote Search; approved external provider execution; Contacts runtime enablement; Files/Calendar/media/additional first-party providers; extension and optional third-party providers; durable provider preferences; durable local content indexing; accepted Manager/Wardveil/Everkeep/Mesh/Policy/Observability runtime integrations; GLAZE UI rendered/native consumer acceptance; accessibility/localization/RTL/form-factor/OEM/performance qualification; recovery/rollback; protected production signing/distribution; Release Candidate; Production Acceptance; production deployment; and Stable qualification.

See `PLANNED-FEATURES.md` for the active obligations and candidate work.
