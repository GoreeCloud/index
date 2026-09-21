# GoreeCloud Index — Conformance

## Lifecycle

**Release lifecycle: Development.** Version `0.3.0-dev`. Production acceptance and Stable qualification remain false.

Candidate base: `c97a6ef3958b14cfcd99c15fd8e56222c56bc77d`.

## Repository and Platform Contract

- [x] Canonical repository `GoreeCloud/index`.
- [x] Contract schema `0.4`.
- [x] Exactly nine Integral Platform Systems evaluated.
- [x] GoreeCloud Sync separately governed.
- [x] Required Stable Glaze target `1.6.0`.
- [ ] Overall Platform conformance.
- [ ] Release eligibility.

## Query Runtime

- [x] Provider-neutral contracts and provenance validation.
- [x] Structured concurrent dispatch, cancellation propagation, and bounded timeouts.
- [x] Deterministic normalization/ranking and provider-scoped deduplication.
- [x] Partial/degraded result preservation.
- [x] Bounded provider fan-out.
- [x] Candidate incremental `Flow` delivery and one-shot/final-snapshot equivalence.
- [ ] Accepted cross-provider operational telemetry.

## Local Sources

- [x] Applications.
- [x] Bounded Settings navigation.
- [x] Contacts source with minimized fields and no blank enumeration.
- [x] Candidate session-scoped source controls limited to local integrated providers.
- [x] Candidate enforced local-only Development execution.
- [ ] Representative-device/OEM acceptance.

## Contacts Authority

- [x] Android permission, Privacy Shield, and Identity are independent requirements.
- [x] Missing/constrained/denied/stale/unavailable authority fails closed.
- [x] Candidate coarse missing-authority presentation.
- [x] Candidate explicit Android permission review.
- [ ] Accepted live Privacy Shield decision acquisition.
- [ ] Accepted live Identity authorization acquisition.
- [ ] Complete user decision lifecycle.
- [ ] Representative-device Contacts acceptance.

## GoreeCloud Search

- [x] Transport-neutral provider foundation.
- [x] API/provider-contract/capability validation.
- [x] Candidate Production requirement for both Privacy Shield and GoreeCloud Identity.
- [x] Candidate operation-scoped Privacy Shield reference and independent Identity requester credential boundary.
- [x] Sensitive-value redaction and safe URL/action validation.
- [x] Development runtime remains local-only with no Internet permission.
- [ ] Live transport registration/discovery/authentication/TLS/proxy acceptance.
- [ ] User-facing Internet-provider enablement/preferences.
- [ ] Representative runtime acceptance.

## GLAZE UI

- [x] Candidate native V1.6 / `1.6.0` source projection.
- [x] Stable release source/runtime identity recorded.
- [x] Accessibility-first fallback and fail-closed capability presentation.
- [x] No automatic permission/authorization/provider precedence/consequential execution.
- [ ] Rendered/native visual and interaction acceptance.
- [ ] TalkBack/screen-reader, keyboard/focus, text scaling/reflow, contrast, reduced motion/transparency, localization/RTL acceptance.
- [ ] Representative phone/tablet/form-factor and performance acceptance.
- [ ] Human Visual Excellence acceptance.
- [ ] Rollback and production acceptance.

## Integral Platform Systems v3.0

| System | Candidate declaration |
| --- | --- |
| GoreeCloud Manager | Applicable — Blocked |
| Privacy Shield | Applicable — Blocked |
| Wardveil Security | Applicable — Blocked |
| Everkeep | Applicable — Blocked |
| Glaze UI | Applicable — Blocked |
| GoreeCloud Mesh | Applicable — Blocked |
| GoreeCloud Identity | Applicable — Blocked |
| GoreeCloud Policy | Applicable — Blocked |
| GoreeCloud Observability | Applicable — Blocked |

Glaze no longer requires a version migration in candidate source, but application-level acceptance is still blocked. No declaration above equals production acceptance.

## Release Gates

- [ ] Fresh exact-head PR validation.
- [ ] Accepted platform-system runtime evidence.
- [ ] Representative-device accessibility/performance.
- [ ] Production security/privacy review.
- [ ] Recovery/rollback evidence.
- [ ] Protected signing/distribution/provenance.
- [ ] Release Candidate qualification.
- [ ] Production acceptance.
- [ ] Stable qualification.
