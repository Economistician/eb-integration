# Workflows in eb-integration

This document outlines the workflows in **eb-integration** and their role in the Electric Barometer ecosystem.

Each workflow in **eb-integration** is designed to enforce consistency across all EB repositories. Leaf repositories should call these workflows to ensure all pull requests, releases, and post-release checks adhere to the platform's standards.

---

## Layer 1 — PR Quality Gate

**Workflow:** `pr-gate.yml`

**Purpose:**
Ensures that pull requests meet the following quality standards before merging:
- **Code hygiene**: enforced with **Ruff** (linting + formatting)
- **Static correctness**: enforced with **Type checking** (optional via pyright/mypy)
- **Tests**: run tests across Python versions and OS platforms
- **Packaging integrity**: checks if the package builds correctly
- **Optional docs build**: ensures the docs can be built without errors

**Key Inputs:**
- `python-version`: Python version(s) for testing (default: `3.13`)
- `os`: List of OS platforms to run the tests on (default: `["ubuntu-latest", "windows-latest"]`)
- `python_versions`: List of Python versions for the test matrix (default: `["3.11", "3.12", "3.13"]`)
- `run_precommit`: Whether to run pre-commit hooks (default: `true`)
- `enable_typecheck`: Whether to enable typechecking (default: `false`)
- `extras`: Extra dependencies to install (e.g., `.[test]` for testing dependencies)

**Output:**
- The workflow will fail if any of the gates fail (e.g., linting, tests, typechecking).

---

## Layer 2 — Release Pipeline

**Workflow:** `pypi-release.yml`

**Purpose:**
Handles the release of new versions to PyPI, ensuring:
- **Builds**: builds the source distribution and wheels
- **Validation**: checks that the metadata is correct (e.g., versioning, required fields)
- **Publish**: publishes the artifacts to PyPI using trusted publishing (OIDC)

**Key Inputs:**
- `python-version`: Python version for building the release (default: `3.12`)
- `build-command`: The command to build distribution artifacts (default: `python -m build --sdist --wheel`)
- `dist-dir`: The directory containing the built artifacts (default: `dist`)

**Output:**
- Artifacts are built and validated.
- If all checks pass, the package is published to PyPI.

**Trigger:**
This workflow is triggered manually via version tags (`v*`) or by manual dispatch.

---

## Layer 3 — Post-release / Operational Verification

**Workflow:** `pypi-smoke.yml`

**Purpose:**
Verifies that the package can be installed from PyPI and works as expected. This ensures:
- The package is successfully installed from PyPI.
- The package can be imported without issues.
- Optional: run basic smoke tests or any other minimal checks.

**Key Inputs:**
- `python-version`: Python version to run the smoke test (default: `3.12`)
- `package`: The name of the package to install from PyPI (e.g., `eb-metrics`)
- `import_module`: The module to import after installation (e.g., `eb_metrics`)
- `index-url`: The index URL to install from (default: `https://pypi.org/simple`)
- `extra_smoke_command`: Optional command(s) to run after import, such as running tests or checking the version.

**Trigger:**
- This workflow runs on a schedule (e.g., nightly or weekly).
- Optionally, it can be triggered after a successful release (`workflow_run`).

---

## Component Workflows

These workflows are designed to be used within **Layer 1** (PR Gate) and are **reusable** across multiple repositories.

### `gate-ruff.yml`
**Purpose:**
Runs **Ruff** for linting and formatting checks across the repo.

**Key Inputs:**
- `python-version`: The Python version to run Ruff with (default: `3.13`)

**What it does:**
- Runs `ruff format --check` for formatting
- Runs `ruff check` for linting

### `gate-pre-commit.yml`
**Purpose:**
Runs pre-commit hooks on all files in the repo. These hooks can handle additional checks, such as end-of-file fixes, YAML validation, etc.

**Key Inputs:**
- `python-version`: The Python version to use (required)

**What it does:**
- Installs pre-commit and caches environments
- Runs the hooks defined in the `.pre-commit-config.yaml`

### `gate-pytest.yml`
**Purpose:**
Runs tests using **pytest** on the specified Python versions and OS platforms.

**Key Inputs:**
- `os`: The OS platforms for testing (e.g., `ubuntu-latest`, `windows-latest`)
- `python-version`: Python versions to test across (e.g., `3.11`, `3.12`, `3.13`)
- `extras`: Any extra dependencies for testing (e.g., `.[test]`)

**What it does:**
- Installs the necessary dependencies
- Runs `pytest` on the repo

### `gate-package.yml`
**Purpose:**
Handles packaging and publishing validation. Ensures the package builds correctly and passes validation checks.

**Key Inputs:**
- `python-version`: Python version for building (default: `3.13`)

**What it does:**
- Runs `python -m build` to build source distributions and wheels
- Runs `twine check` to ensure the package metadata is valid

### `gate-wheel-install.yml`
**Purpose:**
Runs a smoke test to ensure the built wheel installs correctly and can be imported.

**Key Inputs:**
- `python-version`: The Python version for testing
- `import_module`: The module to import after installation
- `wheel_pytest_command`: Optional pytest command to run after wheel installation

**What it does:**
- Installs the built wheel from the `dist/` directory
- Runs an import test to verify the module is installed and works

### `gate-typecheck.yml`
**Purpose:**
Runs **pyright** (or **mypy**) for static type checking.

**Key Inputs:**
- `python-version`: The Python version to use
- `tool`: The tool to use for type checking (e.g., `pyright`, `mypy`)

**What it does:**
- Installs the necessary type checker
- Runs `pyright` (with the `tooling/pyrightconfig.json` config) or `mypy`

### `gate-docs.yml`
**Purpose:**
Builds the documentation using **MkDocs**.

**Key Inputs:**
- `python-version`: Python version to use
- `extras`: Extra dependencies for documentation (e.g., `.[docs]`)
- `docs_command`: Command to run for building docs (default: `mkdocs build -s`)

**What it does:**
- Installs necessary dependencies
- Builds the docs with `mkdocs build`

---

## Summary

These workflows form the backbone of the **EB ecosystem's CI/CD**. Leaf repositories should call these workflows to enforce consistent quality, testing, packaging, and publishing policies across the ecosystem.

For further guidance, please see the **[Guides](guides/)** section for step-by-step instructions on setting up a leaf repository.
