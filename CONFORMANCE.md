# GoreeCloud Index — Conformance

## Lifecycle

**Release lifecycle: Development.** Version `0.3.0-dev`. Production acceptance and Stable qualification remain false.

Verified integrated baseline before this control-plane stabilization: `258516d856fd48d7f3f181425d2a77199cdbab31`.

## Repository and Platform Contract

- [x] Canonical repository is `GoreeCloud/index`.
- [x] Root Platform Contract declaration uses schema `0.4`.
- [x] Exactly nine Integral Platform Systems are evaluated.
- [x] GoreeCloud Sync remains separately governed.
- [x] Current required Stable Glaze target is `1.6.0`.
- [x] Mandatory repository root controls include privacy, security, notes, and editor configuration.
- [ ] Overall Platform conformance.
- [ ] Release eligibility.

## Native Android Foundation

- [x] Original GoreeCloud-owned Kotlin/Jetpack Compose implementation.
- [x] Production package `com.goreecloud.index`.
- [x] Development package `com.goreecloud.index.dev`.
- [x] API 26 minimum, compile API 37, target API 36.
- [ ] Representative physical-device acceptance.
- [ ] Controlled production signing and distribution.

## Search Runtime

- [x] Provider-neutral contracts.
- [x] Structured concurrent dispatch.
- [x] Cancellation propagation and bounded timeouts.
- [x] Healthy sibling-result preservation.
- [x] Deterministic NFKC query normalization and ordering.
- [x] Provider result provenance validation.
- [x] Provider contract-version compatibility.
- [x] Partial-degradation propagation.
- [ ] Incremental/streaming delivery.
- [ ] Accepted cross-provider operational telemetry.

## Applications and Settings

- [x] Launcher-visible Applications provider.
- [x] No unrestricted `QUERY_ALL_PACKAGES`.
- [x] Bounded local Settings navigation provider.
- [x] Settings provider reads no setting values/private device state.
- [ ] Representative-device performance and OEM action acceptance.

## Contacts

- [x] Android `READ_CONTACTS` declared.
- [x] Android ContactsProvider remains source authority.
- [x] Minimized ID/lookup-key/display-name projection.
- [x] No blank-query enumeration.
- [x] Android + Privacy Shield + Identity requirements declared.
- [x] Missing/constrained/denied/stale/unavailable authority fails closed.
- [x] Current shipped Development gateway keeps Contacts non-dispatchable.
- [ ] Accepted live Privacy Shield adapter/evidence.
- [ ] Accepted GoreeCloud Identity adapter/evidence.
- [ ] User decision and Android permission workflow.
- [ ] Representative-device Contacts acceptance.

## GoreeCloud Search

- [x] Transport-neutral provider/client foundation.
- [x] Search API version 1 binding.
- [x] `search.query` capability preflight.
- [x] Endpoint/result-bound checks.
- [x] Query/category/limit minimization.
- [x] Response binding, degraded-state propagation, URL validation, safe actions.
- [x] Shipped runtime remains local-only with no Android Internet permission.
- [ ] Live transport registration.
- [ ] Service discovery/authentication/TLS/proxy acceptance.
- [ ] Explicit user-facing Internet-provider controls.
- [ ] Representative runtime acceptance.

## GLAZE UI

- [x] Native V1.4 / `1.4.0` semantic foundation.
- [x] Deterministic GoreeCloud light/dark schemes.
- [x] Accessibility-first fallback and source-aware status presentation.
- [ ] Migrate source to current Stable V1.6 / `1.6.0`.
- [ ] Rendered/native accessibility, text-scale/reflow, RTL/localization, reduced-motion/transparency, contrast, form-factor, performance, and Human Visual Excellence acceptance.

## Integral Platform Systems v3.0

| System | Current declaration |
| --- | --- |
| GoreeCloud Manager | Applicable — Blocked |
| Privacy Shield | Applicable — Blocked |
| Wardveil Security | Applicable — Blocked |
| Everkeep | Applicable — Blocked |
| Glaze UI | Applicable — Migration Required |
| GoreeCloud Mesh | Applicable — Blocked |
| GoreeCloud Identity | Applicable — Blocked |
| GoreeCloud Policy | Applicable — Blocked |
| GoreeCloud Observability | Applicable — Blocked |

No declaration above is equivalent to accepted runtime integration.

## Release Gates

- [ ] Accepted platform-system runtime evidence.
- [ ] Representative-device accessibility and performance.
- [ ] Production security/privacy review.
- [ ] Recovery/rollback evidence.
- [ ] Protected signing, packaging, distribution, and provenance.
- [ ] Release Candidate qualification.
- [ ] Production acceptance.
- [ ] Stable qualification.
