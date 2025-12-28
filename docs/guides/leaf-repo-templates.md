# Leaf Repository Setup Templates

This guide provides templates for integrating **eb-integration** into your leaf repositories. These templates should be copied into the `.github/workflows` directory of your leaf repository. They will ensure your repository follows the EB ecosystem CI/CD policies, including the PR Quality Gate, Release Pipeline, and Post-release Verification.

---

## 1. **PR Quality Gate** (`ci.yml`)

This workflow runs the **PR Quality Gate**, which includes checks for code hygiene (Ruff), static type checking (Pyright or Mypy), tests, and packaging integrity. It ensures that no PR is merged without meeting the required quality standards.

```yaml
name: PR Quality Gate

on:
  pull_request:
    branches:
      - main

jobs:
  pr-gate:
    uses: Economistician/eb-integration/.github/workflows/pr-gate.yml@main
    with:
      python-version: "3.13"
      os: '["ubuntu-latest", "windows-latest"]'
      python_versions: '["3.11", "3.12", "3.13"]'
      run_precommit: true
      enable_typecheck: true
```

### Inputs:
- `python-version`: Python versions for testing (default: `3.13`)
- `os`: OS platforms to test on (default: `["ubuntu-latest", "windows-latest"]`)
- `python_versions`: Python versions to test across (default: `["3.11", "3.12", "3.13"]`)
- `run_precommit`: Whether to run pre-commit hooks (default: `true`)
- `enable_typecheck`: Whether to enable type checking (default: `false`)
- `extras`: Extra dependencies to install (e.g., `.[test]`)

---

## 2. **Release Pipeline** (`release.yml`)

This workflow automates the release process, including building distribution artifacts (source and wheel), validating metadata, and publishing to PyPI. It is triggered manually or when a version tag (`v*`) is pushed.

```yaml
name: PyPI Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:

jobs:
  release:
    uses: Economistician/eb-integration/.github/workflows/pypi-release.yml@main
    with:
      python-version: "3.12"
      build-command: "python -m build --sdist --wheel"
```

### Inputs:
- `python-version`: Python version for building the release (default: `3.12`)
- `build-command`: Command to build distribution artifacts (default: `python -m build --sdist --wheel`)
- `dist-dir`: Directory containing the built artifacts (default: `dist`)

---

## 3. **Post-release Verification** (`pypi-smoke.yml`)

This workflow is used for post-release verification. It ensures that the package can be installed from PyPI and works as expected after release. It can run on a schedule or be triggered after a successful release.

```yaml
name: PyPI Smoke Test

on:
  schedule:
    - cron: "0 0 * * 0"  # Weekly on Sundays
  workflow_run:
    workflows: ["PyPI Release"]
    types:
      - completed

jobs:
  smoke-test:
    uses: Economistician/eb-integration/.github/workflows/pypi-smoke.yml@main
    with:
      python-version: "3.12"
      package: "eb-metrics"
      import_module: "eb_metrics"
```

### Inputs:
- `python-version`: Python version to run the smoke test (default: `3.12`)
- `package`: Name of the package to install from PyPI (e.g., `eb-metrics`)
- `import_module`: The module to import after installation (e.g., `eb_metrics`)
- `index-url`: The index URL to install from (default: `https://pypi.org/simple`)
- `extra_smoke_command`: Optional command(s) to run after import (e.g., running tests or checking the version).

---

## 4. **Pre-commit Hooks (optional)** (`pre-commit.yml`)

This workflow runs pre-commit hooks on all files in the repository. Pre-commit hooks help enforce additional checks such as YAML syntax validation, end-of-file fixes, and more.

```yaml
name: Pre-commit Hooks

on:
  pull_request:
    branches:
      - main

jobs:
  pre-commit:
    uses: Economistician/eb-integration/.github/workflows/gate-pre-commit.yml@main
    with:
      python-version: "3.13"
```

### Inputs:
- `python-version`: The Python version to use for pre-commit hooks.

---

## 5. **Typecheck (optional)** (`typecheck.yml`)

If your project uses static type checking (e.g., Pyright or Mypy), this workflow runs the typechecker on the codebase to ensure that type annotations are correct and consistent.

```yaml
name: Typecheck

on:
  pull_request:
    branches:
      - main

jobs:
  typecheck:
    uses: Economistician/eb-integration/.github/workflows/gate-typecheck.yml@main
    with:
      python-version: "3.13"
      tool: "pyright"
```

### Inputs:
- `python-version`: The Python version to use for type checking (default: `3.13`)
- `tool`: The tool to use for type checking (`pyright` or `mypy`)

---

## Summary

These templates are the minimum configuration required to integrate **eb-integration**'s CI/CD workflows into your leaf repository. They will ensure that your repository adheres to the quality gates, release process, and post-release verification defined in the **EB ecosystem**.

Simply copy and paste the appropriate template into your `.github/workflows` directory, customize the inputs if necessary, and your repository will automatically align with the ecosystem's standards.

For more details on how to modify or extend these workflows, refer to the **[Reference](reference/)** section.