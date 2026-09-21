# GoreeCloud Index — Privacy Policy

## Status and Scope

GoreeCloud Index is in **Development** and is not production accepted or Stable. This repository policy describes the privacy boundary implemented by the current Development source; it does not claim that every planned provider or platform integration is enabled.

## Privacy Principles

Index is designed to coordinate search without becoming an unnecessary copy of source data. Source applications, Android platform providers, and GoreeCloud services remain authoritative for their own records.

Current principles are:

- local-first execution for shipped providers;
- no silent remote fallback;
- data minimization;
- purpose-limited provider access;
- explicit provider provenance;
- fail-closed authorization;
- no intentional persistent query history or behavioral profiling;
- no sale of user data or advertising use; and
- no remote provider activation merely because transport source code exists.

## Current Local Providers

### Applications

The Applications provider searches launcher-visible applications. It does not request unrestricted `QUERY_ALL_PACKAGES` visibility and does not require Android Internet permission.

### Settings

The Settings provider searches a static GoreeCloud-owned catalog of Android Settings destinations. It does not read setting values, accounts, permission state, device configuration, history, or other private device state.

### Contacts

The Contacts provider source uses Android ContactsProvider and is intentionally authority-gated.

The current provider projection reads only contact ID, lookup key, and primary display name. It does not request phone-number or email fields. Blank queries do not enumerate Contacts.

Dispatch requires:

1. Android `READ_CONTACTS` permission;
2. applicable Privacy Shield decision evidence; and
3. applicable GoreeCloud Identity authorization evidence.

Missing, denied, constrained, stale, user-decision-required, or unavailable evidence prevents dispatch. The shipped Development gateway does not fabricate platform approval, so Contacts remains non-dispatchable until accepted runtime authority exists.

## GoreeCloud Search and Remote Processing

The repository contains a transport-neutral GoreeCloud Search provider foundation. The shipped Android runtime does not register a live remote Search provider and does not request Android Internet permission.

Any future Internet-provider enablement must provide explicit user-facing controls, disclose local-versus-remote processing, minimize delegated query context, and satisfy applicable Privacy Shield, Identity, Wardveil Security, Policy, and other authority requirements. Local source data must not be silently bundled with an Internet query.

## Retention

Current search query state is transient. The current source does not intentionally maintain a persistent query-history database or analytics profile.

If future history, indexing, cache, or synchronization features add durable data, their retention, deletion, export, recovery, and privacy behavior must be documented and accepted before production use.

## Logging and Evidence

Private query text, contact contents, reusable credentials, tokens, private keys, and other sensitive source data must not be placed in ordinary logs, CI artifacts, diagnostics, or conformance evidence.

Operational evidence should use minimized status and provenance sufficient to establish behavior without copying underlying private content.

## Third-Party Providers

No third-party remote provider is enabled by the current shipped runtime. Future third-party providers must be explicitly connected or enabled, narrowly scoped, independently revocable, and transparent about processing location and retained data.

## Platform Authorities

Privacy Shield remains authoritative for applicable privacy decisions. GoreeCloud Identity remains authoritative for identity and authorization. Wardveil Security remains authoritative for security evidence. GoreeCloud Policy and GoreeCloud Observability retain their respective policy and operational-evidence domains. Index consumes those authorities; it does not replace them.

## User Rights and Control

Before production acceptance, Index must provide all user controls required by applicable GoreeCloud governance for enabled providers, permissions, remote processing, retained history/index state, revocation, clearing, export, and deletion.

## Production Boundary

This Development privacy policy does not establish production approval. Production acceptance requires exact-release validation of actual enabled providers, data flows, permissions, retention, user controls, security/privacy behavior, representative runtime behavior, and applicable platform-system evidence.
