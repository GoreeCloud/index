# GoreeCloud Index — Capabilities

## Overview

**Release lifecycle: Development.** Latest runtime-bearing integration checkpoint is `5ae1a1debc79a7adc8b65266bb947baf633d4d1f`. PR #38 is integrated and post-merge Platform Contract run `35600884480` plus Android Index foundation run `35600883648` passed on that checkpoint. Documentation/test-only commits may advance the default branch; verify GitHub live whenever the exact current `main` SHA is material. Production acceptance and Stable qualification remain false.

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

Integrated Search source requires independent Privacy Shield and Identity evidence before authenticated Development or Production delegation. The candidate now includes a concrete fixed-origin HTTPS client for capability discovery and JSON-body Search POST, with redirect refusal, bounded responses, strict JSON parsing, and header-only authority carriage. No concrete Identity registration, issuer/audience/scope, live Privacy Shield verifier path, production credential, proxy acceptance, or production provider registration is invented locally.

## GLAZE UI

Active native theme source targets V1.6 / `1.6.0`. Presentation consumes caller-owned state and fails closed on unknown/conflicting authority. Shared Stable status does not establish Index-local application acceptance.

## Limits

The authoritative Development runtime remains local-only in the Development UI. Live remote Search, accepted Contacts/platform runtime integrations, representative-device qualification, durable local indexing, additional providers, recovery/release gates, production, and Stable remain open.
