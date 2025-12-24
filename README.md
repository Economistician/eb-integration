[![Integration CI](https://github.com/Economistician/eb-integration/actions/workflows/ci.yml/badge.svg)](https://github.com/Economistician/eb-integration/actions/workflows/ci.yml)

# Electric Barometer Integration (`eb-integration`)

Integration smoke tests for the Electric Barometer ecosystem.

This repository validates cross-package compatibility and end-to-end execution
across the Electric Barometer Python libraries. It serves as a lightweight,
authoritative signal that the ecosystem installs correctly and core workflows
function as intended.

---

## Purpose

The goal of this repository is to provide fast, deterministic integration
smoke tests that answer a single question:

Does the Electric Barometer ecosystem work end-to-end?

These tests are intentionally minimal and operate on small, synthetic datasets.
They are designed to catch breaking changes caused by refactors, packaging
changes, or dependency drift across repositories.

---

## What This Repo Tests

- Editable installation of sibling Electric Barometer packages
- Cross-package import compatibility
- End-to-end metric evaluation using:
  - eb-metrics
  - eb-evaluation
- Basic hierarchical and panel evaluation workflows

---

## What This Repo Does Not Do

- Unit testing (lives in individual package repositories)
- Large datasets or performance benchmarks
- Notebooks, demos, or exploratory analysis
- Model training or production pipelines

---

## Repository Role in the Ecosystem

This repository is the canonical integration canary for Electric Barometer.

Recommended separation of responsibilities:

- eb-metrics — metric definitions and mathematical correctness
- eb-evaluation — DataFrame utilities and evaluation logic
- eb-examples — notebooks, demonstrations, and usage examples
- eb-integration — cross-package integration smoke tests

---

## Running Locally

From the repository root:

pip install -e .
pip install -e ../eb-metrics
pip install -e ../eb-evaluation
pytest -q

All tests should pass in under a few seconds.

---

## Continuous Integration

This repository includes a GitHub Actions workflow that runs the integration
smoke tests on every push and pull request. A green CI run indicates that the
Electric Barometer ecosystem remains compatible and functional as a whole.

---

## License

BSD 3-Clause License. See LICENSE for details.