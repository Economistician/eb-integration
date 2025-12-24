# Electric Barometer · Integration (`eb-integration`)

[![Integration CI](https://github.com/Economistician/eb-integration/actions/workflows/ci.yml/badge.svg)](https://github.com/Economistician/eb-integration/actions/workflows/ci.yml)
![License: BSD 3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)
![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)

Cross-package integration and smoke tests for the Electric Barometer ecosystem.

---

## Overview

`eb-integration` provides cross-package integration and smoke tests for the Electric Barometer ecosystem. Its purpose is to validate that independently developed and versioned Electric Barometer components interoperate correctly when used together in representative workflows.

Rather than testing individual functions or metrics in isolation, this repository focuses on system-level behavior. The tests are designed to detect breaking changes, interface drift, and dependency incompatibilities early, serving as an automated safeguard as the ecosystem evolves.

---

## Role in the Electric Barometer Ecosystem

`eb-integration` acts as a system-level validation layer for the Electric Barometer ecosystem. It exercises representative cross-package workflows to ensure that core components remain compatible as individual repositories evolve.

This repository does not define metrics, evaluation logic, feature engineering, or model interfaces. Its sole responsibility is to surface integration failures early, primarily through automated testing in continuous integration pipelines.

---

## Test Scope

The tests in this repository focus on ecosystem-level validation rather than unit-level correctness. Typical coverage includes:

- Cross-package import and dependency compatibility
- Basic end-to-end workflows spanning multiple repositories
- Detection of breaking interface or contract changes

Tests are intentionally lightweight and are designed to fail fast when integration assumptions are violated.

---

## License

BSD 3-Clause License.  
© 2025 Kyle Corrie.