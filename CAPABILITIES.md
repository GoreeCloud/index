# GoreeCloud Index — Capabilities

## Overview

**Release lifecycle: Development.** Latest accepted runtime-bearing checkpoint is `34446cc519afb87bca27b0c3e6639db01ff114b8`; post-merge Platform Contract run `35613027668` and Android Index foundation run `35613026810` passed. The current `0.3.1-dev` HTTPS transport work is an unmerged candidate. Production acceptance and Stable qualification remain false.

## Search and Composition

- Provider-neutral query/result/action/provenance contracts.
- Deterministic Unicode normalization and cross-provider textual composition.
- Same-provider score/source ordering remains scoped to the provider that owns that score.
- Health-aware tie handling and local-first processing-location tie breaking.
- Bounded provider fan-out and final result limits.
- Incremental snapshots and final one-shot equivalence.
- Cancellation of superseded search work.

## Development Source Controls

Applications, Settings, and Contacts are the only selectable Development providers. Selection is session-scoped and sanitized against that set. `localOnly=true` is always enforced. GoreeCloud Search is excluded from Development source controls.

## Authority-Gated Contacts

Contacts requires Android permission, Privacy Shield, and GoreeCloud Identity. Coarse presentation may explain which authority domains are missing, but raw decision references, subjects, reason codes, timestamps, and credentials do not enter UI state.

Android permission review is user-initiated and addresses only Android's prerequisite.

## GoreeCloud Search Production Contract Source

Integrated Search source requires independent Privacy Shield and Identity evidence before Production delegation. The current candidate adds a concrete fixed-origin HTTPS client for capability discovery and bounded JSON-body query dispatch, but still invents no Identity issuer/token format/scope/client ID, Privacy Shield verifier, production credential, deployment path, or runtime registration.

## GLAZE UI

Active native theme source targets V1.6 / `1.6.0`. Presentation consumes caller-owned state and fails closed on unknown/conflicting authority. Shared Stable status does not establish Index-local application acceptance.

## Limits

The authoritative Development UI remains local-only. The candidate Android package has network permission and a dormant Search HTTPS client, but remote Search registration, accepted authority acquisition, live provider execution, target-runtime qualification, durable local indexing, additional providers, recovery/release gates, production, and Stable remain open.
