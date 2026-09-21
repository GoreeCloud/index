# GoreeCloud Index — User Manual

## Current Development Scope

**Release lifecycle: Development.** This reconciliation candidate is not production accepted or Stable.

## Opening Index

Open **GoreeCloud Index Dev** or invoke the supported Android external search action.

## Search Sources

Candidate source provides session controls for Applications, Settings, and Contacts. These controls affect only the current Index session. Development mode is enforced local-only.

GoreeCloud Search / Internet results are not available through these controls and are never silently enabled.

## Contacts

Contacts may be selected as a source, but search still requires all authority gates. When Android permission is missing, Index can show **Review Android Contacts permission**. Choosing it invokes Android's own permission UI.

Granting Android permission does not satisfy Privacy Shield or GoreeCloud Identity. If either authority remains unavailable, Contacts remains blocked and no Contacts query is sent.

The Contacts provider reads only ID, lookup key, and display name in the current slice and keeps no persistent contact cache or query history.

## Incremental Results

Authorized providers can report results as they complete. Result composition remains deterministic as later providers finish, and cancellation stops superseded provider work.

## Search States

- Searching authorized sources.
- Source unavailable because required authority is incomplete.
- Provider timed out.
- Provider failed.
- Provider degraded but returned usable results.
- No matches.
- Action could not be opened.

## Privacy and Remote Search

Development runtime has no Android Internet permission and does not register a live remote Search provider. The repository includes transport-neutral GoreeCloud Search Production-contract source, but source code cannot activate networking by itself.

## GLAZE UI

Candidate source targets GLAZE UI V1.6 / `1.6.0`. This is source adoption only; rendered/native accessibility, device/form-factor, performance, rollback, release, and production acceptance remain open.

## Development Identity

- Application ID: `com.goreecloud.index.dev`
- Label: `GoreeCloud Index Dev`
- Version: `0.3.0-dev`, code `3`

## Known Limitations

Live Search transport, accepted platform authority acquisition, Contacts runtime enablement, Files/Calendar/media/additional providers, durable indexing, representative-device qualification, production signing/distribution, recovery/rollback, Release Candidate, production, and Stable qualification remain incomplete.
