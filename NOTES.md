# GoreeCloud Index — Notes

## Current Working State

- Release lifecycle: Development / nonconformant.
- Application version: `0.3.1-dev`.
- Canonical repository: `GoreeCloud/index`.
- Current authoritative `main` at the migration baseline: `8de424217d475662d49da9714452b63285ee08d0` from PR #45.
- PR #45 exact head `65b3e397b8c80b8bc21e801fcd4314d12f37c46c` passed Platform Contract run `35651653575` and Android Index foundation validation run `35651652655` before integration.
- No Production Acceptance or Stable qualification is claimed.
- Draft PR #46 remains a separate unmerged hardening candidate.

## Verified Search transport integration

PR #41 integrated the dormant fixed-origin authenticated GoreeCloud Search HTTPS client on runtime-bearing main checkpoint `7b84ef011a8701f90e737a1ae340d8db09d58e78`. Post-merge Platform Contract run `35625546653` and Android Index foundation run `35625545378` passed on that exact revision.

The client discovers Search capability state, uses bounded JSON POST to the fixed Search origin, carries separately supplied Privacy Shield capability and GoreeCloud Identity requester evidence, refuses redirects, bounds response size, validates media/status responses, and redacts sensitive wire data. It remains dormant and unregistered in Development source controls.

## Search cycle-safety contract

PR #40 integrated the cycle-safe delegation requirement: a Search capability used for Index-originated delegation must prove `goreecloud.search-index-delegation.v1`, `external_only` mode, Index-provider re-entry disabled, and delegation fallback disabled before Index will dispatch.

This prevents an `Index → Search → Index` recursion while preserving Search's separately governed behavior for other callers. It does not create live connectivity or runtime authority by itself.

## Search runtime readiness gate

PR #45 integrated a separate Production-only Search runtime-readiness preflight against fixed `https://search.goreecloud.com/readyz`.

Capability validation runs first. A valid `ready` result permits progression to later authority gates; a valid not-ready result fails closed before Index asks Privacy Shield for an operation capability, asks GoreeCloud Identity for a requester credential, or sends a Search query. Invalid service identity, inconsistent status/body, unsupported status/media type, or oversized response fails as a transport error.

The readiness request carries no authorization material, query text, local results, application inventory, or other user data.

## Runtime Boundary

- Development source selection is local-only and limited to Applications, Settings, and Contacts.
- Contacts permission review is Android-owned and cannot satisfy Privacy Shield/Identity.
- Live GoreeCloud Search remains unregistered.
- Android `INTERNET` permission is present only so the dormant fixed-origin HTTPS client can function if a later governed registration is accepted; the permission alone does not enable remote Search or grant authority.
- Production Search source requires cycle-safe capability evidence, positive runtime readiness, independent Privacy Shield authorization, and independent Identity requester evidence.
- No production credentials or concrete Identity registration are invented locally.

## Repository-native migration

The September 22 migration branch replaces the legacy dual repository/Drive roadmap and Drive-hosted changelog model with root `IMPLEMENTED-FEATURES.md`, `PLANNED-FEATURES.md`, and `CHANGELOGS.md`, plus repository-local historical changelog content.

Until the migration is accepted and verified on authoritative `main`, the legacy Drive roadmap/changelog and root `FEATURE-ROADMAP.md` remain migration sources only and are not yet eligible for deletion.

## Open Work

Live Identity/Privacy Shield authority transport and governed Search registration/user controls; accepted external-provider execution; Contacts runtime enablement; accepted platform-runtime integrations; GLAZE UI V1.6 rendered/native application acceptance; representative-device accessibility/performance/OEM evidence; additional providers; durable preferences/indexing; recovery/rollback; protected signing/distribution; Release Candidate; Production Acceptance; production deployment; and Stable qualification.
