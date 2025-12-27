# Ruff configuration (shared contract)

This page describes the **shared Ruff configuration** used across the Electric
Barometer ecosystem.

The canonical configuration lives in:

```
eb-integration/tooling/ruff.toml
```

All ecosystem repositories **must** use this configuration (via the shared GitHub
Actions workflow) to ensure consistent formatting and linting standards.

---

## What Ruff does in this ecosystem

Ruff is used for two distinct tasks:

1. **Formatting**
   - `ruff format`
   - Enforces a consistent code style (similar to Black).
2. **Linting**
   - `ruff check`
   - Enforces correctness, import ordering, modern typing conventions, and other
     quality rules.

In CI, formatting is enforced as a **check** (`--check`) so that drift fails fast.

---

## Core design principles

### Centralized governance
- The Ruff config is centralized in `eb-integration` so the ecosystem behaves
  like a single cohesive codebase.
- Individual repositories **should not** introduce local Ruff config unless
  explicitly approved.

### Stable public surfaces
- Public APIs are curated and documented.
- Lint rules are selected to push the ecosystem toward clarity and consistency
  without excessive noise.

### Modern Python typing
- The configuration encourages modern type syntax (e.g., `X | Y` unions) and
  modern standard library imports (e.g., `collections.abc` types).

---

## Formatting policy

- Formatting is non-negotiable: repositories **must** format to match CI.
- When CI reports "Would reformat", run:

```bash
ruff format --config <path-to-ruff.toml> .
```

and commit the results.

---

## Import policy (E402 / I001)

The ecosystem enforces a strict import layout:

- `from __future__ import annotations` is allowed at the top (when used).
- The module docstring comes next.
- All imports must follow immediately after the docstring.
- Imports must be sorted and grouped (Ruff handles this).

Common first-adoption issues include:
- `E402` "Module level import not at top of file"
- `I001` "Import block is un-sorted or un-formatted"

Fix by moving imports directly under the docstring and running `ruff check --fix`.

---

## `__all__` policy

When modules define `__all__`, it is treated as part of the public API and must
be consistent.

- `__all__` should reflect the intended stable surface.
- `__all__` ordering should be consistent with import ordering and naming.

If `__all__` ordering rules are enabled, apply Ruff fixes or reorder manually to
match the configured convention.

---

## Docstring linting (why it may be disabled for now)

Docstring linting is often valuable, but it can create high friction during
initial ecosystem standardization.

The shared configuration may intentionally defer strict docstring linting until:
- formatting and linting converge across all repositories, and
- public API surfaces stabilize.

When enabled later, docstring rules will be rolled out deliberately and will be
documented here.

---

## Version targeting

Two different “versions” matter:

- **CI python-version**: the Python version used to run Ruff in CI
- **Ruff target-version**: the version Ruff assumes when enforcing certain rules

The Ruff `target-version` is set in `ruff.toml`. CI may run on a newer Python
version (e.g., 3.13) while still targeting a stable baseline for style and lint
expectations (e.g., py311).

---

## Changing the shared config

Changes to `tooling/ruff.toml` affect **every repository** that consumes it.

Therefore:
- Changes **must** be reviewed carefully.
- Prefer incremental changes.
- Document rationale and expected impact.
- Consider rollout strategy if it will create many failures across repos.