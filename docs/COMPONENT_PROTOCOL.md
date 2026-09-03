# Component Protocol

A Foundry component is a capability manifest stored in `registry/components/*.json`.

Required fields:

- `id`
- `version`
- `title`
- `provides`
- `requires`
- `conflicts`
- `risk`
- `acceptance`
- `verification`

Optional fields:

- `packages`
- `platforms`
- `security_tags`
- `notes`

## Dependency semantics

`requires` references **capabilities**, not component IDs. The resolver picks a component that provides each required capability.

This keeps components replaceable. For example, an auth capsule can require `storage.secure` without knowing whether the implementation uses `flutter_secure_storage` or another audited provider.

## Conflict semantics

A conflict can name a component ID or capability. The resolver refuses a plan containing conflicts.

## Quality rule

A component with no acceptance criteria or verification class is not production-ready and should not enter the trusted registry.
