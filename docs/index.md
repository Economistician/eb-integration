# eb-integration

`eb-integration` provides integration tooling, templates, and operational guidance for wiring Electric Barometer components together across repositories, environments, and deployment workflows.

This repository exists to support **composition and orchestration**, not to expose a public Python API.

## Scope

This package is responsible for:

- Defining repository structure and integration conventions
- Providing templates and tooling for leaf repositories
- Documenting workflows for cross-repo coordination
- Supporting CI/CD, release, and operational integration patterns

It intentionally does **not** define metrics, evaluation logic, optimization policies, or runtime APIs.

## API surface

This repository does not expose a public Python API and therefore contains no API reference documentation.

For usage, concepts, and architectural guidance, refer to the main Electric Barometer documentation in `eb-docs`.
