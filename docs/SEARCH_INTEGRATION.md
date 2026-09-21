# GoreeCloud Index — GoreeCloud Search Integration

**Status:** Development contract  
**Role:** Remote Internet/web provider for GoreeCloud Index

## Authority

GoreeCloud Index is the universal search/indexing coordinator. GoreeCloud Search remains authoritative for Internet, web, and current-information search. Index may federate Search results into a universal result set, but it must not duplicate Search provider orchestration or convert Search into a local source.

Privacy Shield remains authoritative for remote-processing authorization, capability-reference validity, expiry/revocation/replay state, and required privacy obligations.

## Eligibility

The Search provider is eligible only when all of the following are true:

- the query is non-empty;
- the execution context permits remote processing;
- `search` is explicitly present in the provider allowlist;
- applicable Privacy Shield authorization evidence is present and enforceable;
- the Search `search.query` capability is current, authoritative, version-compatible, structurally valid, and appropriate for the current build lifecycle.

Local-only execution must not perform Search capability preflight, Privacy Shield remote-Search authorization, or network search.

## Capability discovery and lifecycle

The initial Search capability contract is version `1`, capability ID `search.query`, endpoint `/api/v1/search`.

Capability discovery is expected from `/api/v1/status` under the `capability_evidence` collection. Consumers must select exactly one `search.query` record; missing or duplicate records fail closed.

Current Search capability evidence may advertise `POST` and `GET`, with `POST` preferred for first-party consumers. The preferred production query transport is `json_body`, with `application/json` request/response media types, an explicit Privacy Shield authorization requirement, a 16 KiB request ceiling, and a bounded result maximum.

Production capability evidence must additionally identify:

- authorization scheme `privacy_shield_capability_token_reference`;
- authorization header `X-GoreeCloud-Privacy-Capability`;
- accepted server-side enforcement state `required`;
- `authenticated_requester_required=true`.

The current Search Development service advertises `privacy_authorization_enforcement=not_enforced_development`; Index must reject that evidence in Production mode even if the service is reachable.

Development Index builds may consume explicitly non-production or legacy-GET capability evidence only when the build is itself Development and the exception is recorded in repository-local evidence.

Stable/production Index builds must require Search capability evidence that is explicitly production accepted **and** matches the complete private transport contract. A merely reachable endpoint, GET-compatible capability, consumer-side Privacy Shield decision without server enforcement, or server contract without authenticated requester identity is insufficient.

A Development exception must never be interpreted as permission to promote Index or Search to Stable.

## Cycle-safe Index-originated delegation

A future Index-to-Search request must advertise and satisfy Search's cycle-safety contract before Index may dispatch:

- contract version `goreecloud.search-index-delegation.v1`;
- delegation mode `external_only`;
- Index-provider re-entry disabled;
- delegation fallback disabled.

This is required in Development and Production capability evidence. It is independent of the later Privacy Shield/Identity production checks.

The purpose is architectural: Index treats Search as the Internet/web provider, while Search may also expose an Index provider to other callers. Index must therefore reject any Search capability that could route an Index-originated request back to `GOREECLOUD_INDEX`, another first-party/local provider, or a fallback stage.

The paired Search source candidate implements a dedicated `search_from_index` path that uses only external primary providers and fails before dispatch when no eligible external provider remains. That source contract is readiness evidence only; it does not create live transport, authentication, provider credentials, deployment, or production acceptance.

## Privacy Shield authorization carried with the operation

The higher-level Index execution context still requires Privacy Shield authority before the remote provider becomes eligible. Production Search delegation adds a second provider-local boundary so bypassing the query coordinator cannot silently bypass authorization.

Index creates a unique Privacy Shield `request_id` before each production Search authorization attempt. The canonical request identifies:

- requester `goreecloud-index` with requester type `application`;
- resource `goreecloud.search.query` classified as `query_text`;
- operation `search.query`;
- purpose `internet_search`;
- processing zone `private_goreecloud`;
- destination `https://search.goreecloud.com`;
- retention mode `none`;
- `external_disclosure=false` for the Index-to-first-party-Search boundary.

The `PrivacyShieldSearchAuthorizationAdapter` validates the canonical Privacy Shield decision response. The decision must echo the same `request_id`; evidence for a different request fails closed even if the remaining authorization fields appear compatible.

For private GoreeCloud Search processing, Privacy Shield intentionally returns `ALLOW_WITH_CONSTRAINTS`. Index accepts only that exact outcome and the exact supported obligation set:

- `record_privacy_evidence`;
- `generate_privacy_receipt`;
- `enforce_processing_zone`.

The decision must additionally permit the exact operation, zone, destination, and retention mode, remain unexpired, and return a canonical `psc_*` capability reference. An unconditional `ALLOW`, any different constrained outcome, or any missing/additional obligation fails closed.

The provider performs a final canonical-reference check even after the authorization adapter. Surrounding whitespace is normalized, but non-`psc_*` or whitespace-bearing references are rejected before the Search client is called.

Index acquires fresh Privacy Shield authorization for each production Search query. A prior capability reference is not cached or treated as provider/application state.

Only the opaque capability reference is carried into `GoreeCloudSearchRequest`. Raw signed capability tokens, Privacy Shield signing keys, policy documents, decision payloads, local result sets, and unrelated authority evidence do not cross the Search boundary.

## Search-side reference verification

Production Index must not assume that carrying a capability reference means Search will enforce it. Search must advertise and prove server-side reference enforcement and authenticated requester identity.

Search's planned authority call uses Privacy Shield's version-1 capability-reference verification contract defined by:

```text
contracts/privacy-shield.capability-reference-verification.schema.json
```

Search authenticates as verification consumer `goreecloud-search` while separately binding the original requester identity `goreecloud-index`. Those identities are not interchangeable.

The verifier request contains only the v1 contract version, opaque reference, exact expected requester/resource/purpose/operation/processing-zone/destination/retention claims, and `consume=true` for the one Search execution. Privacy Shield remains authoritative for signed-token validation, expiry, revocation, replay policy, and single-use consumption.

Search must derive the original Index requester identity from an authenticated runtime/transport boundary rather than trusting arbitrary request data. Privacy Shield must likewise derive Search's verification-consumer identity from the authenticated verification transport.

## Minimized request

Index delegates only:

- the normalized query string;
- the selected Search category;
- a bounded result limit;
- for accepted production delegation, the minimum opaque Privacy Shield capability reference required by the Search authorization transport.

Index must not send installed apps, contacts, files, calendar items, local result sets, device inventory, Identity identifiers, raw signed Privacy Shield tokens, or unrelated authorization evidence payloads to Search.

The preferred production request representation is a bounded `application/json` POST body. Query text must not be duplicated into the request URL when the POST transport is used. The capability reference belongs in the separately advertised authorization header rather than the JSON query body.

## Result handling

Index independently validates every executable Search destination. Only normalized HTTP(S) URLs with a valid host and no embedded user-info credentials may become `OpenWeb` actions.

Invalid results are dropped as executable actions by the Index validation pipeline and must produce sanitized provider issue evidence without suppressing healthy sibling results. If Search returns more entries than the delegated limit, Index preserves its consumer-owned bounded cap rather than widening the result set.

Search-owned raw numeric ranking metadata is transport/source metadata; Index must not compare that scale directly with app, contact, setting, file, or other provider scores. Current source integration instead preserves Search-owned result order only as a same-provider tie-breaker when Index-normalized relevance is equal.

## Degraded responses

When Search reports partial degradation, Index may preserve valid results while surfacing degraded provider status. Degradation must not be hidden or rewritten as healthy availability. Invalid-result evidence takes precedence where applicable while valid sibling results remain usable.

## Cancellation

Superseded user queries must cancel previous Search delegation through the Index query lifecycle. Cancellation is not a provider failure and must not be rewritten as degraded Search availability. The Search service contract independently preserves the same distinction between caller cancellation and its own provider timeout boundary.

## Browser handoff

Web results selected from Index hand off to Browser through a typed validated web action. Index does not gain tab/session authority, and Browser does not gain Index provider authority by opening the destination.

## Glaze UI

Index-owned search surfaces must use the latest approved Stable Glaze UI release and retain Index-local acceptance evidence. Search results do not inherit Search's Glaze status, and Search availability cannot satisfy Index design-system acceptance.

## Stability boundary

The existence of the Search provider and Privacy Shield decision adapters is source integration evidence only. Stable acceptance requires current Search capability evidence, real Privacy Shield decision acquisition with request correlation and exact constrained-obligation handling, a versioned authenticated Search-side capability-reference verification transport, authenticated requester identity, supported runtime behavior, accessibility, degradation handling, cancellation behavior, and representative real-device validation.
