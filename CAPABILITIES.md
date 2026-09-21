# GoreeCloud Index — Capabilities

## Overview

**Release lifecycle: Development.** This reconciliation candidate is based on authoritative `GoreeCloud/index` main `c97a6ef3958b14cfcd99c15fd8e56222c56bc77d`. Candidate source is not integrated merely because it exists or passes CI.

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

Candidate Search source requires independent Privacy Shield and Identity evidence before Production delegation. It validates Search capability metadata and transport intent before calling a supplied client. No concrete Identity registration, token format, issuer, scope, client ID, TLS/proxy path, or production credential is invented locally.

## GLAZE UI

Active native theme source targets V1.6 / `1.6.0`. Presentation consumes caller-owned state and fails closed on unknown/conflicting authority. Shared Stable status does not establish Index-local application acceptance.

## Limits

The candidate remains local-only in the Development UI. Live remote Search, accepted Contacts/platform runtime integrations, representative-device qualification, durable local indexing, additional providers, recovery/release gates, production, and Stable remain open.
