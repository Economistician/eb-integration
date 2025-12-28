# Tooling Policy for eb-integration

This document describes the **tooling policy** used across the **Electric Barometer (EB)** ecosystem. All configuration files in the `tooling/` directory serve as the central source of truth for the entire ecosystem. Leaf repositories should **not** duplicate these configurations; they should rely on this platform to enforce the same standards everywhere.

---

## Purpose and Scope

This tooling policy exists to ensure that **all Electric Barometer repositories behave consistently** with respect to code quality, formatting, static analysis, testing, packaging, and documentation.

By centralizing tooling configuration in **eb-integration**, the ecosystem gains:

- A **single, authoritative source of truth** for tooling rules
- **Consistent CI behavior** across all repositories
- Reduced configuration drift and maintenance overhead
- Clear ownership and auditability of policy changes

Leaf repositories are intentionally kept lightweight. They do **not** define their own linting, formatting, or type-checking rules. Instead, they opt into this policy by invoking the shared `gate-*` workflows, which enforce the same standards everywhere.

Any change to tooling policy must be made in **eb-integration**. Once updated, those changes automatically propagate to all participating repositories, ensuring the ecosystem evolves in a coordinated and predictable way.

---

## Centralized Tooling in `tooling/`

The `tooling/` directory in **eb-integration** holds configuration files for the following tools:

- **Ruff**: Linting and formatting policy (`tooling/ruff.toml`)
- **Pyright**: Static type-checking policy (`tooling/pyrightconfig.json`)
- **Pre-commit**: Hook configuration (optional)
- **MkDocs**: Documentation build configuration (optional)
- **Pytest**: Test configuration (optional)

All these tools help enforce consistent coding practices, quality checks, and ecosystem-wide standards. Leaf repositories should reference these configs directly without modification or duplication.

---

## Tooling Configurations

### 1) **`tooling/ruff.toml`** — Linting & Formatting

**Ruff** is the official linter and formatter for the EB ecosystem, ensuring consistent code quality across all repositories. It enforces both linting and code formatting rules.

**Key sections:**
- **Core Settings**: `line-length`, `target-version`, `include`, `exclude`
- **Formatter Configuration**: `quote-style`, `indent-style`, `line-ending`
- **Lint Rules**: `select`, `ignore`, and `fixable` rules that define which checks to run and which issues to auto-fix.
- **Per-file Rule Overrides**: Special rules for certain file types or locations (e.g., ignoring unused imports in tests).

Leaf repos should not modify this file. They should rely on **`gate-ruff.yml`** to run the `ruff` checks.

**Reference**: [Full `ruff.toml` contents](tooling/ruff.toml)

---

### 2) **`tooling/pyrightconfig.json`** — Static Type Checking

**Pyright** is used for static type checking across the EB ecosystem. The configuration file defines the type checking rules for the entire platform. It uses **basic type checking mode** to avoid too many false positives, providing a good balance between safety and flexibility.

**Key sections:**
- **typeCheckingMode**: set to `basic` for low noise
- **exclude**: standard excludes like `__pycache__`, `dist/`, etc.
- **reporting**: controls error levels for missing imports and unknown members

Leaf repositories should reference this file for type checking, and **`gate-typecheck.yml`** will run Pyright using this configuration.

**Reference**: [Full `pyrightconfig.json` contents](tooling/pyrightconfig.json)

---

### 3) **`tooling/pre-commit/`** — Pre-commit Hooks (optional)

The **Pre-commit hooks** are optional but recommended for additional hygiene checks. This is managed using **pre-commit** (the tool).

**Default Hooks:**
- End-of-file fixer
- YAML syntax checker
- Basic Python code hygiene (auto-fixers)

Each repo can install its own set of hooks, but they should be based on the configuration in **`tooling/pre-commit/`**. Leaf repositories should **not duplicate** this configuration; they should rely on **`gate-pre-commit.yml`** to run pre-commit hooks.

**Reference**: [Pre-commit configuration](tooling/pre-commit)

---

### 4) **`tooling/mkdocs/`** — Documentation Build (optional)

When documentation is part of a project, **MkDocs** is used to build the static site. All repos should use a consistent configuration for building documentation, and **`tooling/mkdocs/`** holds this configuration.

This section of the tooling is optional and should be enabled by individual repositories that maintain documentation.

---

### 5) **`tooling/pytest.ini` or `tooling/pytest.toml`** — Testing Configuration (optional)

If your repo has specific **pytest** configuration requirements (e.g., plugins, pytest markers, etc.), you can centralize those settings here. However, it’s **optional** because most pytest configuration is handled at the repo level.

---

## Best Practices

- **Do not duplicate tooling configurations in leaf repos**:
  All tooling configuration (Ruff, Pyright, Pre-commit, etc.) must be referenced from `eb-integration` and should never be copied or altered in leaf repositories.

- **Use the `gate-*` workflows** to enforce the policy:
  Every leaf repo should call the respective `gate-*` workflows (e.g., `gate-ruff.yml`, `gate-typecheck.yml`) to enforce linting, type checking, testing, etc. These workflows will automatically reference the shared tooling configuration from `eb-integration`.

- **Update the tooling policy in `eb-integration`**:
  If a change needs to be made to the linting, type checking, or other tooling configuration, do it in the `tooling/` folder of **eb-integration**. These changes will automatically propagate across all leaf repositories that call the platform’s workflows.

---

## Summary

The **tooling/** directory in **eb-integration** is the **centralized home for all ecosystem-wide configuration**. It ensures that all leaf repos adhere to consistent quality standards and best practices across linting, type checking, testing, and more. By centralizing configuration, we avoid duplication, reduce drift, and make maintenance easier.

- **Ruff** and **Pyright** configs are the core
- **Pre-commit hooks** and **MkDocs** are optional but enforceable across repos
- Leaf repos only reference these configs via `gate-*` workflows

For further details, see the **[Reference](reference/)** section for individual tool configurations and their purpose.
