# GoreeCloud Index — Planned Features

**Record type:** Repository planned/open feature inventory  
**Repository:** `GoreeCloud/index`  
**Lifecycle:** Development / nonconformant  
**Migration state:** **Authoritative on `main` after PR #47 merged as `e70a3b699810f83bc3277a1b56fa2580a3f0fc4e` and default-branch readback verified this record. Legacy Drive roadmap/changelog retirement was subsequently verified.**  
**Repository authority baseline:** `main` at `e70a3b699810f83bc3277a1b56fa2580a3f0fc4e` (PR #47 merged September 22, 2026).  
**Latest application/runtime baseline:** `8de424217d475662d49da9714452b63285ee08d0` (PR #45); PR #47 did not promote runtime state.  
**Governing standard:** Standard — Repository Feature Tracking and Changelog Governance, version 1.0, effective September 22, 2026.

## Purpose

This file carries forward the material planned, partial, blocked, deferred, candidate, governance, and acceptance-gated obligations from the retired roadmap model while reconciling them to current verified repository state.

A partially implemented capability remains open here until its intended implementation and acceptance scope is complete. Source, unit-test, build, APK, emulator, or documentation evidence does not by itself establish Production Acceptance or Stable qualification.

## Migration reconciliation

This inventory was migrated from:

- retired repository `FEATURE-ROADMAP.md`;
- retired `GoreeCloud/Feature Roadmap/GoreeCloud Index/FEATURE-ROADMAP.docx`;
- the authoritative repository implementation/PR state; and
- existing GoreeCloud Tasks Management obligations, including the Index/Search stabilization task line.

The legacy roadmap copies were stale relative to PR #45 and were reconciled to verified repository evidence during PR #47. PR #47 final exact head `0f3e5ce0cab24716bb78b03203b88fe60f0941aa` passed Platform Contract run #104 / `35727458531` and Android Index foundation validation run #239 / `35727458037` before merge as `e70a3b699810f83bc3277a1b56fa2580a3f0fc4e`.

After authoritative `main` readback verified the three repository-native records, imported history, migrated validator, and absence of root `FEATURE-ROADMAP.md`, the legacy Index Drive changelog and roadmap were deleted. Their former file IDs now return not found, no Index changelog remains in the canonical GoreeCloud Changelogs folder, and the dedicated Index roadmap folder is empty.

The former Drive/repository roadmap synchronization requirement is superseded by **Standard — Repository Feature Tracking and Changelog Governance v1.0**. No active, mirrored, backup, convenience, or historical-shadow Index feature roadmap is authorized in Google Drive.

## Active implementation and acceptance obligations

### Search delegation and provider controls

- Keep GoreeCloud Search as the authoritative Internet/web/current-information provider while GoreeCloud Index remains the federation/composition authority for the Index experience.
- Preserve the PR #40 cycle-safety contract: Index-originated Search delegation must be external-only, must not re-enter Index, and must not use delegation fallback.
- Preserve the PR #41 fixed-origin, bounded, redirect-refusing Search transport and independent Privacy Shield / Identity header boundaries.
- Preserve the PR #45 credential-free `/readyz` prerequisite before Privacy Shield authorization, Identity requester acquisition, or query dispatch.
- Do not register remote Search in the Development UI or source controls until producer-owned runtime authority, approved external provider execution, explicit user control, and target-runtime transport acceptance are established.
- Add an understandable remote-provider enable/disable and processing-disclosure experience only after those authority boundaries are accepted.
- Keep user query text and local provider context out of readiness checks and unrelated remote-provider handoffs.

### Open Draft PR #46 candidate

Draft PR #46, **Keep control-bearing queries off Search transport**, is an active Development candidate based on the pre-migration runtime line. Its exact head `d223bed56a508023503b3cf2e498734def0c2fa6` passed Platform Contract run `35666837083` and Android Index foundation validation run `35666836688`.

The candidate rejects C0 control characters and DEL from Index-originated Search queries before network exchange. It remains **unmerged candidate evidence** and must not be represented as implemented until reconciled to current authoritative `main`, revalidated if needed, accepted, and read back there.

### Providers and local indexing

- Runtime-enable Contacts only after Android permission, Privacy Shield, and GoreeCloud Identity evidence are all available through accepted producer-owned paths and representative behavior is validated.
- Add Files, Calendar, media, first-party GoreeCloud content, connected-device resources, extensions, and optional third-party providers only through explicit provider contracts and authority/privacy/security boundaries.
- Keep third-party integration optional, explicit, scoped, revocable, and transparent about local versus remote processing.
- Add durable provider preferences only after profile/device scope, privacy behavior, migration, recovery, and Everkeep semantics are defined and tested.
- Add durable local indexing only where measured evidence justifies it; indexes must remain reconstructible, scoped, removable, rebuildable, and non-authoritative.
- Provide safe index/cache clearing and rebuilding controls where durable indexing is introduced.

### Integral Platform Systems

Complete evidence-backed runtime integration and application acceptance for the applicable nine Integral Platform Systems while preserving producer authority:

- GoreeCloud Manager;
- Privacy Shield;
- Wardveil Security;
- Everkeep;
- Glaze UI;
- GoreeCloud Mesh;
- GoreeCloud Identity;
- GoreeCloud Policy; and
- GoreeCloud Observability.

GoreeCloud Sync remains separately governed and must not be treated as a tenth Integral Platform System.

Unsupported or unverified states must remain blocked/nonconformant rather than being omitted or manufactured as positive integrations.

### GLAZE UI V1.6 application acceptance

The V1.6 source projection is implemented, but Index-specific acceptance remains open. Complete:

- rendered/native review;
- TalkBack and applicable assistive-technology behavior;
- keyboard/focus behavior where applicable;
- large text and reflow;
- localization and RTL;
- Reduced Motion / Reduced Transparency behavior;
- contrast/high-contrast behavior;
- representative phone/tablet/OEM/form-factor testing;
- measured performance and power review;
- Human Visual Excellence review;
- rollback verification; and
- release/production consumer acceptance.

### Reliability, recovery, and release

- Validate provider cancellation, timeout, partial-result, degraded-provider, and incremental-delivery behavior on representative targets.
- Complete target-runtime TLS/proxy/network acceptance for the dormant Search client before any production registration.
- Complete recovery/rollback planning and evidence for preferences, provider state, any future durable index, and applicable platform integrations.
- Establish protected production signing/distribution and provenance.
- Complete Release Candidate qualification only after provider, platform, privacy, security, accessibility, performance, and recovery gates have exact-release evidence.
- Complete Production Acceptance, production deployment, and Stable qualification as separate explicit lifecycle events.

## Migrated roadmap dispositions

| Legacy ID | Feature / obligation | Migrated disposition |
| --- | --- | --- |
| `FR-001` | Keep repository and Drive roadmap controls synchronized with verified reality. | **Superseded and retired.** Repository-native `IMPLEMENTED-FEATURES.md` and `PLANNED-FEATURES.md` replaced the dual-roadmap model. The successfully migrated Drive roadmap has been deleted after authoritative verification. |
| `FR-002` | Keep actionable Index obligations in GoreeCloud Tasks Management. | **Ongoing governance.** Existing Index/Search stabilization task records remain the task authority; do not duplicate them. |
| `FR-003` | Preserve Development/nonconformant state until release gates have evidence. | **Ongoing.** Index remains Development/nonconformant. |
| `FR-004` | Adopt current GLAZE UI V1.6 source and complete application acceptance. | **Partial.** Source adoption implemented; rendered/native/accessibility/device/performance/rollback/production acceptance remains open. |
| `FR-005` | Preserve deterministic composition, bounded fan-out, provenance, and cancellation. | **Implemented in current Development source; regression preservation remains ongoing.** |
| `FR-006` | Expand local/first-party providers through explicit authority contracts. | **Partial.** Applications and Settings implemented; Contacts source implemented but authority-gated; Files/Calendar/media/additional providers remain open. |
| `FR-007` | Complete GoreeCloud Search integration without silent remote context export. | **Partial.** Cycle-safety, dormant fixed-origin transport, authority boundaries, and `/readyz` gate are implemented. Live registration, real authority acquisition, explicit user controls, approved external execution, target-runtime acceptance, Production, and Stable remain open. |
| `FR-008` | Integrate and accept all applicable Integral Platform Systems. | **Partial / blocked.** Nine systems are explicitly evaluated; runtime acceptance remains incomplete. |
| `FR-009` | Provider controls and permission review without manufacturing authority. | **Partial.** Session local controls and Android Contacts permission review are implemented; durable/remote-provider controls and accepted user-decision flows remain open. |
| `FR-010` | Add reconstructible local indexing where justified. | **Planned.** No durable production local-content index accepted. |
| `FR-011` | Complete accessibility, localization/RTL, form-factor, performance, and representative-device qualification. | **Open.** Source-level reliability behavior exists; representative qualification remains open. |
| `FR-012` | Complete signing/provenance, rollback/recovery, RC, production, and Stable gates. | **Open.** |
| `FR-013` | Retire stale PR #35/#36 after unique work preservation. | **Complete historical disposition.** PR #38 preserved/replaced valid work; #35/#36 closed superseded. |
| `FR-014` | Maintain Contract 0.4, nine-system declarations, mandatory root controls, and current-state validation. | **Implemented control / ongoing maintenance.** PR #47 migrated the repository validator to require the three new root records and reject reintroduced `FEATURE-ROADMAP.md`. |

## Sequencing

1. Finish and disposition current Search hardening candidate(s) against authoritative `main`, with fresh exact-head validation for every changed candidate.
2. Keep the remote Search path dormant until producer-owned authority and explicit user control are accepted end to end.
3. Runtime-enable private/local providers only through their explicit Android + GoreeCloud authority requirements.
4. Complete GLAZE UI V1.6 and representative-device acceptance before lifecycle promotion.
5. Add broader providers and any durable indexing only after privacy/security/recovery contracts are defined.
6. Complete recovery, protected signing, Release Candidate, Production Acceptance, deployment, and Stable gates only with exact evidence.

## Completion rule

When an open capability becomes implemented:

1. reconcile the evidence-backed implemented portion in `IMPLEMENTED-FEATURES.md`;
2. remove or disposition the completed obligation here without erasing historical traceability; and
3. record the meaningful change in `CHANGELOGS.md`.

Do not mark candidate, partial, or green-CI-only work as complete merely because a branch or pull request passed automation.
