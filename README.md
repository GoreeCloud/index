# GoreeCloud Index

GoreeCloud Index is GoreeCloud's privacy-first universal search and indexing layer. It coordinates authorized search providers while preserving source ownership, provenance, and independent platform authority.

## Status

**Release lifecycle: Development.** Production acceptance and Stable qualification remain false.

Canonical repository: `GoreeCloud/index`.

The verified integrated baseline immediately before this control-plane stabilization is `main` commit `258516d856fd48d7f3f181425d2a77199cdbab31`. Current source is version `0.3.0-dev` and remains local-only at runtime.

## Current Development Capability

Current source includes:

- Native Android Kotlin/Jetpack Compose application surface.
- Provider-neutral query/result/action contracts.
- Structured concurrent provider execution, cancellation propagation, bounded provider timeouts, and failure isolation.
- Deterministic NFKC query normalization and ranking with provider-scoped deduplication.
- Launcher-visible Applications search.
- Bounded static Android Settings navigation search.
- Authority-gated Android Contacts source that remains non-dispatchable without Android permission plus accepted Privacy Shield and GoreeCloud Identity evidence.
- Provider result provenance validation and explicit provider contract version compatibility.
- A transport-neutral GoreeCloud Search provider foundation with API-version checks, capability preflight, query/category/limit minimization, degraded-result propagation, URL validation, and safe web actions.
- A native GLAZE UI V1.4 / `1.4.0` semantic light/dark foundation.

The shipped runtime does **not** register the remote GoreeCloud Search provider, does not request Android Internet permission, and does not silently fall back to remote search.

## Product and Authority Boundaries

**GoreeCloud Index** is the universal search/indexing coordinator. **GoreeCloud Search** remains authoritative for Internet/web/current-information search. **GoreeCloud Launcher** is an invocation and presentation surface. Android and source applications/services remain authoritative for their own records and operations.

Privacy Shield, Wardveil Security, Everkeep, GoreeCloud Mesh, GoreeCloud Identity, GoreeCloud Policy, GoreeCloud Observability, and GoreeCloud Manager retain their own authority domains. Index may consume evidence or coordination from them; it does not manufacture their decisions.

## Contacts Boundary

Contacts source is implemented but remains fail-closed:

- Android ContactsProvider remains record authority.
- Only contact ID, lookup key, and display name are read by the current provider slice.
- Phone and email fields are not requested.
- Blank queries do not enumerate Contacts.
- Dispatch requires Android `READ_CONTACTS`, an unconstrained referenced Privacy Shield allow decision, and an accepted GoreeCloud Identity authorization result.
- Missing, denied, constrained, stale, user-decision-required, or unavailable evidence prevents dispatch.

## Settings Boundary

Settings search uses a repository-owned static destination catalog. It does not read setting values, accounts, device configuration, permission state, history, or other private device state. Handoffs are restricted to a closed Android Settings action allowlist.

## GoreeCloud Search Boundary

The Search provider source validates:

- Index provider contract version;
- GoreeCloud Search API version 1;
- `search.query` capability identity and freshness;
- canonical Search endpoint expectations;
- published result bounds;
- delegated query/category integrity;
- partial-degradation evidence; and
- safe result URLs/actions.

Live transport, service discovery, authentication, TLS/proxy behavior, Internet-provider user controls, and production acceptance remain separate open gates.

## Platform Contract

This repository declares GoreeCloud Platform Contract `0.4` and explicitly evaluates all nine Integral Platform Systems. GoreeCloud Sync remains separately governed and is not a tenth Integral Platform System.

Index currently implements a GLAZE UI V1.4 / `1.4.0` native semantic foundation. The current Platform Contract Stable consumer target is GLAZE UI V1.6 / `1.6.0`, so migration and fresh application-level acceptance remain required.

## Android Development Identity

- Production application ID: `com.goreecloud.index`
- Development application ID: `com.goreecloud.index.dev`
- Development label: `GoreeCloud Index Dev`
- Version: `0.3.0-dev`, version code `3`
- Minimum API: 26
- Compile API: 37
- Target API: 36

## Current Release Blockers

Representative-device accessibility/performance, GLAZE UI V1.6 application acceptance, accepted live platform-system integrations, live Search transport and user controls, signing/distribution, rollback/recovery, release provenance, Release Candidate qualification, production approval, and Stable qualification remain open.

## Documentation

- [Specifications](SPECIFICATIONS.md)
- [Features](FEATURES.md)
- [Feature roadmap](FEATURE-ROADMAP.md)
- [Capabilities](CAPABILITIES.md)
- [Architecture](ARCHITECTURE.md)
- [Conformance](CONFORMANCE.md)
- [User manual](USER-MANUAL.md)
- [Privacy policy](PRIVACY%20POLICY.md)
- [Security](SECURITY.md)
- [Notes](NOTES.md)
- [Benefits](BENEFITS.md)
- [Competitive objectives](COMPETITIVE-OBJECTIVES.md)

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
