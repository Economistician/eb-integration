# Electric Barometer · Integration (`eb-integration`)

[![Integration CI](https://github.com/Economistician/eb-integration/actions/workflows/pr-gate.yml/badge.svg)](https://github.com/Economistician/eb-integration/actions/workflows/pr-gate.yml)
![License: BSD 3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)
![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)

Centralized CI/CD platform for integration, testing, and publishing across the Electric Barometer ecosystem.

---

## Overview

`eb-integration` serves as the centralized CI/CD platform for the Electric Barometer ecosystem, providing cross-package integration and smoke tests. Its primary purpose is to ensure that independently developed and versioned Electric Barometer components work together seamlessly within representative workflows.

Instead of focusing on individual functions or metrics in isolation, this repository prioritizes system-level behavior. The tests are designed to catch breaking changes, interface drift, and dependency mismatches early, acting as an automated safeguard as the ecosystem evolves and new components are integrated.

---

## Role in the Electric Barometer Ecosystem

`eb-integration` serves as the system-level validation layer for the Electric Barometer ecosystem. It ensures that core components remain compatible as individual repositories evolve by running representative cross-package workflows.

This repository does not define metrics, evaluation logic, feature engineering, or model interfaces. Its sole purpose is to catch integration failures early, primarily through automated testing within continuous integration pipelines.

---

## Test Scope

The tests in this repository are focused on ecosystem-level validation to ensure that Electric Barometer components work seamlessly when integrated. These tests are designed to exercise key cross-package workflows and detect issues early in the development cycle. Typical coverage includes:

- **Cross-package import and dependency compatibility**
- **End-to-end workflows** spanning multiple repositories and real-world use cases
- **Detection of breaking changes** in interfaces, APIs, or contracts
- **Integration with new and evolving components** as the ecosystem grows

Tests are intentionally lightweight and are designed to fail fast when integration assumptions are violated.

---

## License

BSD 3-Clause License.
© 2025 Kyle Corrie.
