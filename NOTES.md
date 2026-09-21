# GoreeCloud Index — Notes

## Current Working State

- Release lifecycle: Development.
- Application version: `0.3.1-dev`.
- Canonical repository: `GoreeCloud/index`.
- Latest runtime-bearing integration checkpoint: `7b84ef011a8701f90e737a1ae340d8db09d58e78` from PR #41. Authoritative main is currently the later documentation-only checkpoint `29c1c4150ef0b80118b1cf8bdf1c34533014dee4`; verify GitHub live whenever the exact current default-branch SHA is material.
- No production acceptance or Stable qualification is claimed.

## Verified transport integration

PR #38 remains historical integration provenance for the Contract 0.4/V1.6 source line. PR #41 then integrated the dormant fixed-origin authenticated GoreeCloud Search HTTPS client on exact runtime-bearing main `7b84ef011a8701f90e737a1ae340d8db09d58e78`. Post-merge Platform Contract run `35625546653` and Android Index foundation run `35625545378` passed on that exact revision.

The client discovers `search.query` through Search status, uses bounded JSON POST to the fixed Search origin, carries separately supplied Privacy Shield capability and GoreeCloud Identity requester evidence, refuses redirects, bounds response size, validates media/status responses, and redacts wire data from debug rendering. It remains dormant and unregistered in Development source controls.

## Search cycle-safety readiness

A future Search capability must prove `goreecloud.search-index-delegation.v1` with `external_only` mode, Index-provider re-entry disabled, and fallback disabled before the Index Search provider will dispatch. This prevents a future `Index → Search → Index` recursion while preserving Search's ordinary ability to use Index for non-Index-originated callers.

Paired GoreeCloud Search PR #23 is integrated on its authoritative Development line with the cycle-safe authenticated HTTP boundary. Index still does not register Search in its Development UI, and no Identity/Privacy Shield runtime acceptance is created by either source integration.

## 2026-09-21 — Search runtime readiness gate candidate

The current Index candidate adds a separate production-only Search runtime-readiness preflight against the fixed `https://search.goreecloud.com/readyz` endpoint. Capability validation still runs first; a non-ready Search runtime then fails closed before Index asks Privacy Shield for an operation capability or GoreeCloud Identity for a requester credential. The preflight carries no authorization material or query content.

The paired Search PR #28 currently defines readiness as accepted authority transports plus at least one enabled external provider, while still advertising `production_accepted=false`. Index remains dormant/unregistered in Development source controls, so this candidate does not activate remote Search or create runtime acceptance.

## Runtime Boundary

- Development source selection is local-only and limited to Applications, Settings, and Contacts.
- Contacts permission review is Android-owned and cannot satisfy Privacy Shield/Identity.
- Live GoreeCloud Search remains unregistered. Android `INTERNET` permission is now present only so the dormant fixed-origin HTTPS client can function if a later governed registration is accepted; the permission alone does not enable remote Search or grant authority.
- Production Search source requires independent Privacy Shield and Identity evidence.
- No production credentials or concrete Identity registration are invented locally.

## Open Work

Canonical Drive DOCX reconciliation; live Identity/Privacy Shield authority transport and governed Search registration/user controls; accepted platform-runtime integrations; V1.6 rendered/native application acceptance; representative-device accessibility/performance/OEM evidence; additional providers; recovery/rollback; protected signing/distribution; Release Candidate; production; and Stable qualification.
