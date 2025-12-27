# eb-integration

`eb-integration` provides **shared tooling, CI workflows, and ecosystem-level
validation** for the Electric Barometer project.

This repository is intentionally **not** a runtime library. Instead, it serves as
the governance and glue layer that ensures:

- consistent code quality across repositories
- shared linting and formatting standards
- reusable GitHub Actions workflows
- cross-repo smoke tests for compatibility

## What this repository provides

- **Shared Ruff configuration** used across all EB Python packages
- **Reusable GitHub Actions workflows** (via `workflow_call`)
- **Ecosystem smoke tests** validating cross-package compatibility

## What this repository does not provide

- Forecasting models
- Metrics implementations
- Optimization logic
- Feature engineering utilities

Those live in their respective repositories.

## Who should read this documentation

- Contributors working across multiple EB repositories
- Maintainers onboarding new EB packages
- Anyone modifying CI, linting, or release infrastructure