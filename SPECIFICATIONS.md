# GoreeCloud Index — Specifications

## Product Status

**Release lifecycle: Development.**

- Repository: `GoreeCloud/index`
- Version: `0.3.0-dev` / code `3`
- Candidate base: `c97a6ef3958b14cfcd99c15fd8e56222c56bc77d`
- Supported implementation: Android
- Platform Contract: `0.4`
- GLAZE UI source target: V1.6 / `1.6.0`
- Production acceptance: No
- Stable qualification: No

## Purpose

Index coordinates authorized search providers, normalizes and composes results, preserves provenance, and exposes provider-authorized actions. Provider applications and Android remain authoritative for their records. GoreeCloud Search remains authoritative for Internet/web search.

## Query Runtime

The candidate engine supports deterministic NFKC normalization, applicability filtering, exact provider allowlisting, local-only gating, authority evaluation, structured concurrent dispatch, bounded provider timeouts, cancellation propagation, partial/degraded results, provider-result provenance validation, provider-scoped deduplication, bounded fan-out, deterministic ranking, and incremental `Flow<IndexSearchSnapshot>` delivery.

One-shot search resolves through the same final incremental-composition path.

## Development Source Controls

Applications, Settings, and Contacts are the only selectable Development providers. Selection is session-scoped, sanitized against the allowlist, and always runs with `localOnly=true`. GoreeCloud Search is intentionally not user-enableable through the Development source selector.

## Contacts

Contacts uses Android ContactsProvider, no blank-query enumeration, and a minimized projection of contact ID, lookup key, and display name. It does not read phone or email columns in this slice.

Dispatch requires Android runtime permission plus Privacy Shield and GoreeCloud Identity evidence. Android permission review is explicitly user-initiated through `ActivityResultContracts.RequestPermission`; granting Android permission does not satisfy either GoreeCloud authority.

## GoreeCloud Search

The transport-neutral Search source validates Index provider contract v1, Search API v1, `search.query` capability identity/freshness, canonical endpoint and result bounds, Privacy Shield intent/reference, authenticated Identity requester metadata, response binding, degraded state, URL safety, and sensitive rendering boundaries.

The Development runtime does not register live Search transport and does not request Android Internet permission.

## GLAZE UI V1.6

The candidate includes a native V1.6 source projection bound to accepted release source `a7180679ea851389e0f3004515f9a25f420e716d`, qualification source `c7509c79256b04b0aa67cb9dd0737d7588e0ae4a`, and Stable runtime `js/glaze-v1.6.0.mjs`.

Presentation remains non-authorizing. Unknown, conflicting, restricted, unsupported, or permission-required capability state fails closed. Accessibility precedence can force a solid presentation path. Index application-level rendered/native, accessibility, device/form-factor, performance, rollback, release, and production acceptance remain incomplete.

## Platform Contract

All nine Integral Platform Systems are explicitly evaluated under Contract `0.4`. GLAZE UI is source-targeted at `1.6.0` but remains Applicable — Blocked until repository-local acceptance closes. Other systems remain blocked where runtime/acceptance evidence is missing. GoreeCloud Sync remains separately governed.

## Release Boundary

No source contract, unit test, build artifact, manifest validity, or shared Glaze Stable status automatically creates Index production or Stable acceptance.
