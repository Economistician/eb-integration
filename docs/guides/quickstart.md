# Quickstart Guide for EB Integration

Welcome to the **Electric Barometer (EB)** ecosystem! This guide will walk you through the initial setup for using **eb-integration** with your repository.

The EB ecosystem is powered by **GitHub Actions** and uses centralized policies and workflows to enforce quality and consistency across multiple repositories.

---

## Step 1: Add `eb-integration` as a GitHub Action Dependency

In your leaf repository (e.g., `eb-metrics`), you will need to call the workflows defined in **`eb-integration`**.

1. Go to your repository's **.github/workflows** directory.
2. Create or modify a workflow file (e.g., `ci.yml`) that calls the respective workflows from **`eb-integration`**.

Here is an example configuration for your **PR Quality Gate** (`pr-gate.yml`):

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

---

## Step 2: Configure Branch Protection

To ensure that the PR Quality Gate is enforced on your main branch (or any other important branches):

1. Go to **Settings** > **Branches** > **Branch protection rules**.
2. Create a protection rule for your `main` branch (or other protected branches).
3. Ensure that **`pr-gate.yml`** passes as a required status check before merging a PR.
4. Optionally, enable **Required pull request reviews** and **Require signed commits** for added security.

---

## Step 3: Add Release Pipeline

In your **leaf repository**, you will also want to add a **Release Pipeline** to handle publishing to PyPI. Here’s how to call the **Release Workflow** (`pypi-release.yml`):

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

This workflow will automatically publish the package to PyPI when a version tag is pushed (e.g., `v1.0.0`).

---

## Step 4: Post-release Verification

After your release, you'll want to verify that the package can be installed from PyPI and works as expected. You can enable **Post-release smoke tests** by calling the **`pypi-smoke.yml`** workflow:

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

This ensures that the released package can be installed from PyPI and is functioning correctly.

---

## Step 5: Monitor and Enforce

Once your workflows are set up, make sure to monitor your repositories and enforce the policies across the organization:
- Any PR merged into protected branches will be subject to the **PR Quality Gate**.
- Releases will be managed by the **Release Pipeline** and verified by **Post-release verification**.

To add or modify configurations, simply update the workflows in **`eb-integration`**, and the changes will propagate to all leaf repositories.

---

## Summary

By following this guide, you've set up the essential workflows to ensure:
- Quality checks before merging PRs.
- A safe and automated release process to PyPI.
- Post-release verification to ensure your package works after deployment.

For further details, refer to the **[Reference](reference/)** and **[Troubleshooting](guides/troubleshooting.md)** sections as needed.

Welcome to the EB ecosystem!