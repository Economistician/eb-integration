# GitHub Actions (shared workflows)

This page documents the reusable GitHub Actions workflows provided by
`eb-integration`. These workflows are intended to be **called by other Electric
Barometer repositories** via `workflow_call`.

> **Normative language:** In this document, **must** indicates a requirement,
> **should** indicates a strong recommendation, and **may** indicates an option.

---

## Overview

`eb-integration` provides reusable workflows to standardize:
- linting and formatting (Ruff)
- ecosystem compatibility checks (smoke tests; optional / evolving)

Repositories in the Electric Barometer ecosystem **should** prefer these shared
workflows over duplicating YAML in each repo.

---

## Provided workflows

### `ruff.yml` — shared linting and formatting

**Purpose**
- Enforce consistent formatting and linting across all EB repositories using a
  centralized Ruff configuration.

**How it works**
- Checks out the caller repository.
- Checks out `Economistician/eb-integration` into a sibling directory at
  `.eb-integration/`.
- Runs Ruff formatting checks and lint checks using the shared config.

**Inputs**
- `python-version` (string, optional; default: `"3.13"`)
  - Sets the Python version used to install and run Ruff in CI.
  - This does **not** change the target-version inside `ruff.toml` (which controls
    lint rules and typing modernization expectations).

**What the workflow runs**
- `ruff format --check ...`
- `ruff check ...`

**Caller requirements**
- The caller repository **must** use a standard Python project layout such that
  linting the repository root (`.`) is appropriate.
- The caller workflow **must** exclude `.eb-integration` from linting if it is
  linting `.` (the shared workflow already does this).

**Example usage**

```yaml
name: Ruff

on:
  push:
  pull_request:

jobs:
  lint:
    uses: Economistician/eb-integration/.github/workflows/ruff.yml@main
```

---

## Recommended caller workflow naming

To keep the ecosystem consistent, repos **should** name their workflow file:

- `.github/workflows/lint.yml`

And name the workflow (top-level `name:`) as:

- `Ruff`

Consistency makes it easier to scan CI at the organization level.

---

## Debugging

If a workflow fails:

1. Open the failing job in GitHub Actions.
2. Identify which step failed:
   - `ruff format --check` indicates formatting drift.
   - `ruff check` indicates lint errors.
3. Reproduce locally using the shared config (see `ci-workflows.md` and
   `reference/ruff-config.md`).

---

## Policy

- Ecosystem repositories **must not** fork or modify the shared workflow without
  a strong justification.
- If a repository needs an exception, prefer a scoped per-file suppression
  (`# noqa: ...`) rather than changing the shared configuration.
- Changes to shared workflows should be treated as a **breaking governance
  change** and reviewed carefully.