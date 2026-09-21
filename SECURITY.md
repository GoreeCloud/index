# GoreeCloud Index — Security

## Security Status

GoreeCloud Index is in **Development**. Source validation, CI success, or a merged change does not establish production security acceptance or Stable qualification.

## Reporting a Vulnerability

Do not publish undisclosed vulnerability details, credentials, private user data, exploit material, or sensitive operational information in a public issue.

Use the repository's private GitHub Security Advisory reporting path when available. If that path is unavailable, use another owner-approved private GoreeCloud security channel rather than public disclosure.

Include only the minimum information needed to reproduce and assess the issue. Never include real reusable credentials or unrelated private data.

## Current Security Boundaries

- The current candidate requests Android `INTERNET` permission solely to support the dormant GoreeCloud Search HTTPS client; no remote provider is registered or user-enabled by this change.
- Applications search avoids unrestricted `QUERY_ALL_PACKAGES`.
- Contacts requires Android permission plus independent Privacy Shield and GoreeCloud Identity authority evidence before dispatch.
- Missing, constrained, denied, stale, or unavailable authority fails closed.
- Settings actions are restricted to a closed local allowlist.
- Provider results retain provenance and undergo provider-boundary validation.
- GoreeCloud Search provider source validates API version, provider contract compatibility, capability evidence, result bounds, response binding, degradation state, and safe URLs before results may be accepted.
- Live remote Search transport remains disabled in the shipped runtime.

## Untrusted Input

Provider output, URIs, remote Search responses, metadata, result actions, and future extension/third-party provider data must be treated as untrusted until validated at the applicable boundary.

No provider success is itself Wardveil Security acceptance.

## Secrets and Sensitive Data

Do not commit:

- passwords;
- API tokens;
- private keys;
- recovery codes;
- active credentials;
- secret-bearing environment files;
- private contact/query content used only for testing; or
- protected production configuration.

Use sanitized examples and approved secret-management mechanisms.

## Logging and Diagnostics

Logs and evidence should avoid raw private query text, contact contents, reusable credentials, and unnecessary identifying data. Security and observability evidence should preserve enough provenance and timing to diagnose behavior without becoming a secondary sensitive-data store.

## Dependency and CI Security

GitHub Actions dependencies should remain immutably pinned where governed. Build and dependency changes must preserve exact-source traceability and normal review/validation gates.

A green workflow proves only the checks it executes.

## Production Security Gates

Production or Stable qualification requires applicable evidence for:

- Wardveil Security integration and security review;
- Privacy Shield and Identity runtime authority;
- GoreeCloud Policy behavior where applicable;
- GoreeCloud Observability security-relevant operational evidence;
- representative-device/runtime testing;
- dependency and source review;
- protected signing and artifact provenance;
- rollback/recovery; and
- production deployment/acceptance.

Unknown or missing evidence remains a blocker.
