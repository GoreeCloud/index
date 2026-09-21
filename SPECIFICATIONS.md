# GoreeCloud Index — Specifications

## 1. Product Status

- **Product:** GoreeCloud Index
- **Repository:** `GoreeCloud/index`
- **Release lifecycle:** Development
- **Version:** `0.3.0-dev` / version code `3`
- **Supported implementation:** Android foundation
- **Verified integrated baseline before this control-plane stabilization:** `258516d856fd48d7f3f181425d2a77199cdbab31`
- **Production acceptance:** No
- **Stable qualification:** No
- **Implemented Glaze foundation:** V1.4 / `1.4.0`
- **Current required Stable Glaze consumer target:** V1.6 / `1.6.0`
- **Platform Contract:** `0.4`

## 2. Purpose

Index coordinates authorized search providers, normalizes and ranks results, preserves provider provenance, and exposes provider-authorized actions without taking ownership of provider data. GoreeCloud Search remains authoritative for Internet/web search.

## 3. Android Identity

- Production application ID: `com.goreecloud.index`
- Development application ID: `com.goreecloud.index.dev`
- Label: `GoreeCloud Index Dev`
- Minimum API 26; compile API 37; target API 36.

## 4. Provider Contract

Each `IndexProvider` declares provider identity, display name, contract compatibility, processing location, timeout, blank-query behavior, authority requirements, and suspendable search behavior. Undeclared or incompatible provider contract versions fail closed.

## 5. Query Runtime

The engine performs deterministic query normalization, applicability filtering, allowlist and processing-location checks, authority evaluation, structured concurrent dispatch, bounded timeouts, sanitized issues, provenance validation, deterministic ranking, provider-scoped deduplication, and final result bounding.

Parent cancellation propagates. One provider failure or timeout does not suppress healthy sibling results.

## 6. Applications Provider

The Applications provider uses launcher-visible Android components through `ACTION_MAIN` + `CATEGORY_LAUNCHER`, avoids unrestricted `QUERY_ALL_PACKAGES`, requires no Internet permission, and returns exact component actions.

## 7. Settings Provider

The Settings provider searches only a bounded repository-owned catalog of Android Settings destinations. It does not read setting values or private device configuration. Only allowlisted Settings actions are handed to Android.

## 8. Contacts Provider

Contacts source uses Android ContactsProvider with local processing, no blank-query enumeration, minimized projection of ID/lookup key/display name, and typed contact-view actions.

Dispatch requires Android runtime permission, Privacy Shield decision evidence, and GoreeCloud Identity authorization evidence. Constrained, denied, stale, missing, or unavailable platform evidence fails closed. The shipped Development gateway keeps Contacts non-dispatchable until accepted live platform integrations exist.

## 9. GoreeCloud Search Provider Foundation

The transport-neutral Search provider source requires compatible Index provider contract version 1 and Search API version 1. Before delegation it validates authoritative `search.query` capability evidence, endpoint expectations, freshness, result bounds, Privacy Shield gating, normalized query/category/limit minimization, response binding, degradation state, and safe URLs.

The shipped runtime does not register a remote Search transport and does not request Android Internet permission.

## 10. Platform Contract and Integral Platform Systems

Contract `0.4` requires explicit evaluation of exactly nine Integral Platform Systems:

1. GoreeCloud Manager
2. Privacy Shield
3. Wardveil Security
4. Everkeep
5. Glaze UI
6. GoreeCloud Mesh
7. GoreeCloud Identity
8. GoreeCloud Policy
9. GoreeCloud Observability

All nine remain nonconformant, blocked, or migration-required where substantive runtime and acceptance evidence is missing. GoreeCloud Sync remains separately governed.

## 11. GLAZE UI

Current source contains the V1.4 / `1.4.0` native semantic foundation, including deterministic GoreeCloud light/dark presentation and accessibility-first fallback behavior. Contract `0.4` currently requires V1.6 / `1.6.0` for Stable consumer conformance. Source migration plus rendered/native accessibility, form-factor, representative-device/OEM, performance, Human Visual Excellence, rollback, release, and production acceptance remain open.

## 12. Privacy, Security, and Data Handling

Core shipped search remains local-only. No persistent query history or query analytics are intentionally stored. Remote Search must never activate silently. Provider output and result actions are untrusted until validated. Secrets and private records must not enter ordinary logs or evidence.

## 13. Reliability and Accessibility

Required release validation includes cancellation/timeout behavior, partial and degraded results, provider isolation, text scaling/reflow, TalkBack/screen-reader semantics, keyboard/focus behavior where applicable, reduced motion/transparency, contrast, localization/RTL, representative performance, resource use, and failure recovery.

## 14. Current Open Scope

Files/folders, calendar, media, additional first-party application content, connected-device providers, extension/third-party providers, local content indexing, incremental result streaming, accepted live Search transport, provider controls, complete platform-system runtime acceptance, production signing/deployment, Release Candidate, and Stable qualification remain open.

## 15. Release Boundary

Successful source validation, a green PR, a build artifact, or a merged branch is Development evidence only. Production-ready or Stable claims require exact-release evidence for applicable platform integrations, privacy/security, accessibility, representative runtime behavior, recovery/rollback, packaging/signing, deployment, and production acceptance.
