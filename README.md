# GoreeCloud Index

GoreeCloud Index is GoreeCloud's privacy-first universal search and indexing coordinator. It searches explicitly enabled and authorized sources while preserving source ownership, provider provenance, and independent platform authority.

## Status

**Release lifecycle: Development / nonconformant.** Production Acceptance and Stable qualification remain false.

Canonical repository: `GoreeCloud/index`.

Current authoritative `main` at the migration baseline is `8de424217d475662d49da9714452b63285ee08d0`, the merge of PR #45, **Gate production Search delegation on runtime readiness**. PR #45 exact head `65b3e397b8c80b8bc21e801fcd4314d12f37c46c` passed Platform Contract run `35651653575` and Android Index foundation validation run `35651652655` before integration.

Draft PR #46 is a separate unmerged candidate and is not part of the implemented `main` baseline.

## Integrated Development Capability

The current Development line includes:

- provider-neutral query/result/action contracts and result provenance validation;
- deterministic Unicode-normalized matching/composition and provider-scoped deduplication;
- concurrent provider execution, bounded timeouts, cancellation propagation, and partial/degraded result preservation;
- incremental `Flow<IndexSearchSnapshot>` delivery through the same deterministic composition path used by one-shot search;
- bounded provider fan-out and result-count validation;
- session-scoped source controls for Applications, Settings, and Contacts only;
- enforced local-only Development execution;
- privacy-safe missing-authority explanation;
- explicit Android Contacts permission review through Android's own permission contract;
- fail-closed Privacy Shield + GoreeCloud Identity authority projections for Contacts;
- source-controlled Privacy Shield application declarations and exact-scope Contacts decision binding;
- canonical Index visual identity and branding provenance validation;
- native GLAZE UI V1.6 / `1.6.0` source adoption;
- Platform Contract `0.4` with all nine Integral Platform Systems explicitly evaluated;
- a cycle-safe GoreeCloud Search production-delegation capability contract;
- a dormant fixed-origin authenticated Search HTTPS client with bounded transport behavior; and
- a separate credential-free Search `/readyz` gate that must report ready before Production authority acquisition or query dispatch can proceed.

## Runtime and Authority Boundaries

The Development UI still does **not** register a live GoreeCloud Search provider or expose remote Search in source controls. Android `INTERNET` permission is present because the dormant fixed-origin Search client exists in source; that permission alone does not enable Search, mint authority, establish deployment acceptance, or make remote Search user-selectable.

Contacts remains fail closed. Android `READ_CONTACTS` is only one prerequisite; Privacy Shield and GoreeCloud Identity remain independent authorities. Android permission review cannot mint or replace either GoreeCloud decision.

GoreeCloud Search remains authoritative for Internet/web/current-information retrieval. Production Search delegation requires compatible cycle-safe provider/API contracts, a positive runtime-readiness result, current `search.query` capability evidence, an operation-scoped Privacy Shield authorization reference, and a separately supplied GoreeCloud Identity requester credential. Missing or unsafe prerequisites fail closed before query dispatch.

The readiness request is credential-free and carries no user query, bearer credential, Privacy Shield reference, local result data, application inventory, or other user data.

## GLAZE UI V1.6

The integrated Development line targets current Official Stable GLAZE UI V1.6 / `1.6.0`, bound to accepted release source `a7180679ea851389e0f3004515f9a25f420e716d` and Stable runtime `js/glaze-v1.6.0.mjs`.

The native projection remains presentation-only. It does not automatically request permission, infer authorization, choose provider precedence, navigate, execute fallbacks, or collect remote optical context.

Source adoption does **not** establish Index-local Glaze conformance. Rendered/native accessibility, localization/RTL, representative-device/form-factor, performance, Human Visual Excellence, rollback, release, and production acceptance remain blocked.

## Platform Contract

The integrated Development line preserves Platform Contract `0.4`, exactly nine Integral Platform Systems, and GoreeCloud Sync as separately governed. Glaze source version is `1.6.0`, but its result remains **Applicable — Blocked** pending application-level acceptance. Manager, Privacy Shield, Wardveil Security, Everkeep, Mesh, Identity, Policy, and Observability also remain blocked where accepted runtime evidence is missing.

## Android Development Identity

- Production application ID: `com.goreecloud.index`
- Development application ID: `com.goreecloud.index.dev`
- Development label: `GoreeCloud Index Dev`
- Version: `0.3.1-dev`, code `4`
- Minimum API: 26
- Compile API: 37
- Target API: 36

## Release Boundary

Current source/CI evidence establishes Development implementation only. It does not by itself satisfy live provider registration, producer-owned runtime authority, representative-device acceptance, recovery/rollback, production signing/distribution, Release Candidate qualification, Production Acceptance, production deployment, or Stable qualification.

## Documentation

Repository-native feature and change-history controls:

- [Implemented features](IMPLEMENTED-FEATURES.md) — evidence-backed capabilities present in authoritative Development source after migration acceptance.
- [Planned features](PLANNED-FEATURES.md) — open, partial, blocked, deferred, candidate, governance, and acceptance-gated work.
- [Changelogs](CHANGELOGS.md) — repository-local human-readable change history, with imported legacy history under `docs/changelog-history/`.

Additional product and technical documentation:

- [Specifications](SPECIFICATIONS.md)
- [Features](FEATURES.md)
- [Capabilities](CAPABILITIES.md)
- [Architecture](ARCHITECTURE.md)
- [Conformance](CONFORMANCE.md)
- [Search integration](docs/SEARCH_INTEGRATION.md)
- [User manual](USER-MANUAL.md)
- [Privacy policy](PRIVACY%20POLICY.md)
- [Security](SECURITY.md)
- [Notes](NOTES.md)

Canonical project specifications and other governed project records may remain in the authorized GoreeCloud documentation hierarchy where applicable. Feature-state authority and Index changelog authority are repository-native after migration acceptance and must not be synchronized back to Google Drive.

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
