# GoreeCloud Index — Capabilities

## Overview

**Release lifecycle: Development / nonconformant.** Current authoritative `main` at the migration baseline is `8de424217d475662d49da9714452b63285ee08d0`, the merge of PR #45. PR #45 exact head `65b3e397b8c80b8bc21e801fcd4314d12f37c46c` passed Platform Contract run `35651653575` and Android Index foundation validation run `35651652655` before integration. Production Acceptance and Stable qualification remain false.

Draft PR #46 is a separate unmerged hardening candidate and is not part of current implemented capability.

## Search and Composition

- Provider-neutral query/result/action/provenance contracts.
- Deterministic Unicode-normalized composition on the current NFKC + `Locale.ROOT` line.
- Same-provider score/source ordering remains scoped to the provider that owns that score.
- Health-aware tie handling and local-first processing-location tie breaking.
- Bounded provider fan-out and final result limits.
- Incremental snapshots and final one-shot equivalence.
- Cancellation of superseded search work.

## Development Source Controls

Applications, Settings, and Contacts are the only selectable Development providers. Selection is session-scoped and sanitized against that set. `localOnly=true` is always enforced. GoreeCloud Search is excluded from Development source controls.

## Authority-Gated Contacts

Contacts requires Android permission, Privacy Shield, and GoreeCloud Identity. Coarse presentation may explain which authority domains are missing, but raw decision references, subjects, reason codes, timestamps, and credentials do not enter UI state.

Android permission review is user-initiated and addresses only Android's prerequisite. The shipped Development platform-authority gateway remains fail closed when authoritative GoreeCloud evidence is unavailable.

## GoreeCloud Search Production Contract Source

Integrated Search source requires independent Privacy Shield and Identity evidence before Production delegation.

Current authoritative source includes:

- PR #40's cycle-safe Search delegation contract requiring external-only Index-originated delegation, no Index-provider re-entry, and no delegation fallback;
- PR #41's fixed-origin HTTPS client for Search capability discovery and bounded JSON-body query dispatch, with separate Privacy Shield and Identity authority headers, redirect refusal, bounded responses, validation, and sensitive wire-data redaction; and
- PR #45's separate credential-free fixed-origin `/readyz` prerequisite before Privacy Shield authorization, Identity requester acquisition, or query dispatch.

A valid ready result only permits progression to later authority gates. A not-ready runtime fails closed without authority acquisition or Search dispatch. The readiness check contains no query text or authority credential.

The Development UI still does not register GoreeCloud Search. No producer-owned Identity registration/issuance, live Privacy Shield transport, deployment path, or Production approval is manufactured locally.

## GLAZE UI

Active native theme source targets V1.6 / `1.6.0`. Presentation consumes caller-owned state and fails closed on unknown/conflicting authority. Shared Stable status does not establish Index-local application acceptance.

## Limits

The authoritative Development UI remains local-only. The package has network permission and a dormant Search HTTPS client, but remote Search registration, accepted authority acquisition, approved external-provider execution, target-runtime qualification, durable local indexing, additional providers, recovery/release gates, Production Acceptance, production deployment, and Stable qualification remain open.
