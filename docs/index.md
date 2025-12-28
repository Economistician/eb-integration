# EB Integration Platform

**eb-integration** is the centralized CI/CD policy and workflow platform for the
**Electric Barometer (EB)** ecosystem.

This repository defines *how code is validated, packaged, and verified* across all
EB Python packages. Leaf repositories do **not** define their own CI logic; they
delegate to this platform.

The goal is simple:

> **One ecosystem. One standard. One place to change it.**

---

## What This Repository Is (and Is Not)

**eb-integration is:**
- The **source of truth** for CI/CD behavior across the EB ecosystem
- A collection of **reusable GitHub Actions workflows**
- The home of **shared tooling policy** (linting, type checking, etc.)

**eb-integration is not:**
- A runtime dependency
- A feature library
- A place for application logic

---

## The Three-Layer CI/CD Model

The EB ecosystem uses a deliberately layered CI/CD architecture.

### Layer 1 — PR Quality Gate (required to merge)
**Answers:** *“Is this change safe to merge?”*

This layer is enforced via branch protection and must pass for all pull requests.

It includes:
- Code hygiene (Ruff lint + format)
- Optional pre-commit checks
- Optional static type checking
- Unit tests (matrix across Python + OS)
- Packaging integrity (build, install, import smoke)
- Optional documentation build

**Key workflow:** `pr-gate.yml`
**Component workflows:** `gate-*`

---

### Layer 2 — Release Pipeline (publishing)
**Answers:** *“Can we safely ship this artifact?”*

This layer is intentionally separate from PR gating and runs only on:
- version tags (`v*`)
- manual dispatch

It handles:
- building distributions
- validating package metadata
- publishing to PyPI via trusted publishing (OIDC)

**Key workflow:** `pypi-release.yml`

---

### Layer 3 — Post-release / Operational Verification
**Answers:** *“What users can pip install actually works.”*

This layer is *production verification*, not CI gating.

It runs:
- on a schedule (nightly / weekly)
- optionally after a successful release

It verifies:
- install from PyPI
- dependency resolution
- import smoke
- optional lightweight runtime checks

**Key workflow:** `pypi-smoke.yml`

---

## How Leaf Repositories Use This Platform

Leaf repositories in the EB ecosystem are intentionally small and simple.

Each leaf repo typically contains only:
- `ci.yml` → calls `pr-gate.yml`
- `release.yml` → calls `pypi-release.yml`
- `pypi-smoke.yml` → calls `pypi-smoke.yml`

All logic, policy, and enforcement live here.

---

## Shared Tooling Policy

Tooling configuration is centralized under the `tooling/` directory:

- `tooling/ruff.toml` — canonical linting & formatting policy
- `tooling/pyrightconfig.json` — canonical static type-checking policy

These files are **not duplicated** in leaf repositories.
All gates reference them directly.

---

## Design Principles

This platform is built on a few core principles:

- **Centralized policy, decentralized execution**
- **Explicit layers with clear responsibility**
- **Composable workflows, not copy-paste CI**
- **Low-noise, high-signal enforcement**
- **Ecosystem-wide consistency**

If you change behavior here, you change it everywhere — intentionally.

---

## Where to Go Next

- See **Guides** for how leaf repositories integrate with this platform
- See **Reference** for detailed workflow and tooling documentation
