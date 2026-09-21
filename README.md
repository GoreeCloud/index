# GoreeCloud Index

GoreeCloud Index is GoreeCloud's privacy-first universal search and indexing coordinator. It searches explicitly enabled and authorized sources while preserving source ownership, provider provenance, and independent platform authority.

## Status

**Release lifecycle: Development.** Production acceptance and Stable qualification remain false.

Canonical repository: `GoreeCloud/index`.

Authoritative `main` for this checkpoint is `5ae1a1debc79a7adc8b65266bb947baf633d4d1f`, produced by the confirmed squash merge of PR #38 after exact-head validation. Post-merge Platform Contract run `35600884480` and Android Index foundation run `35600883648` both passed on that exact `main` revision.

## Integrated Development Capability

Authoritative `main` preserves the still-valid runtime work reconciled from PR #35 without inheriting its obsolete seven-system, Contract 0.3, older Glaze, or validator assumptions:

- provider-neutral query/result/action contracts and result provenance validation;
- deterministic Unicode normalization and provider-scoped composition;
- concurrent provider execution, bounded timeouts, cancellation propagation, and partial/degraded result preservation;
- incremental `Flow<IndexSearchSnapshot>` delivery through the same deterministic composition path used by one-shot search;
- bounded provider fan-out and result-count validation;
- session-scoped source controls for Applications, Settings, and Contacts only;
- enforced local-only Development execution;
- privacy-safe authority explanation;
- explicit Android Contacts permission review through Android's own permission contract;
- stronger GoreeCloud Search Privacy Shield + GoreeCloud Identity Production authority requirements;
- safe Search result/action validation and sensitive-value redaction; and
- native GLAZE UI V1.6 / `1.6.0` source adoption.

## Runtime and Authority Boundaries

The Development runtime does **not** register live GoreeCloud Search transport and does not request Android Internet permission. Source controls cannot enable GoreeCloud Search or an unknown remote provider.

Contacts remains fail-closed. Android `READ_CONTACTS` is only one prerequisite; Privacy Shield and GoreeCloud Identity remain independent authorities. Android permission review cannot mint or replace either GoreeCloud decision.

GoreeCloud Search remains authoritative for Internet/web/current-information retrieval. Production Search source requires compatible provider/API contracts, current `search.query` capability evidence, bounded transport expectations, an operation-scoped Privacy Shield authorization reference, and a separately supplied GoreeCloud Identity requester credential. Missing authority fails closed before remote dispatch.

## GLAZE UI V1.6

Authoritative `main` targets current Official Stable GLAZE UI V1.6 / `1.6.0`, bound to accepted release source `a7180679ea851389e0f3004515f9a25f420e716d` and Stable runtime `js/glaze-v1.6.0.mjs`.

The native projection remains presentation-only. It does not automatically request permission, infer authorization, choose provider precedence, navigate, execute fallbacks, or collect remote optical context.

Source adoption does **not** establish Index-local Glaze conformance. Rendered/native accessibility, localization/RTL, representative-device/form-factor, performance, Human Visual Excellence, rollback, release, and production acceptance remain blocked.

## Platform Contract

Authoritative `main` preserves Platform Contract `0.4`, exactly nine Integral Platform Systems, and GoreeCloud Sync as separately governed. Glaze source version is `1.6.0`, but its result remains **Applicable — Blocked** pending application-level acceptance. Manager, Privacy Shield, Wardveil Security, Everkeep, Mesh, Identity, Policy, and Observability also remain blocked pending accepted runtime evidence.

## Android Development Identity

- Production application ID: `com.goreecloud.index`
- Development application ID: `com.goreecloud.index.dev`
- Development label: `GoreeCloud Index Dev`
- Version: `0.3.0-dev`, code `3`
- Minimum API: 26
- Compile API: 37
- Target API: 36

## Release Boundary

Fresh post-merge CI on authoritative `main` proves the checks executed at exact revision `5ae1a1debc79a7adc8b65266bb947baf633d4d1f`; it does not by itself satisfy later runtime or release gates. Production signing/distribution, representative-device acceptance, recovery/rollback, Release Candidate qualification, production approval, and Stable qualification remain separate gates.

## Documentation

- [Specifications](SPECIFICATIONS.md)
- [Features](FEATURES.md)
- [Capabilities](CAPABILITIES.md)
- [Architecture](ARCHITECTURE.md)
- [Conformance](CONFORMANCE.md)
- [Feature roadmap](FEATURE-ROADMAP.md)
- [Search integration](docs/SEARCH_INTEGRATION.md)
- [User manual](USER-MANUAL.md)
- [Privacy policy](PRIVACY%20POLICY.md)
- [Security](SECURITY.md)
- [Notes](NOTES.md)

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
