# Branch Protection Rules

This document defines the **branch protection rules** for repositories in the **Electric Barometer (EB)** ecosystem.

Branch protection ensures that code meets quality standards before it is merged into key branches (e.g., `main`, `master`). These rules are designed to enforce the **PR Quality Gate** (Layer 1) to ensure that no code that fails the gate is ever merged.

---

## Required Status Checks

To enforce the PR gate policy, the following checks **must** pass before merging into the main branch (or other protected branches):

### 1) **PR Quality Gate**
The **PR Quality Gate** is the **most important check** and is enforced by the `pr-gate.yml` workflow. It includes the following sub-checks:
- **Ruff Linting & Formatting**
  - Linting checks using **Ruff** (for code style and formatting)
- **Type Checking** (optional, via Pyright or Mypy)
  - Runs **Pyright** (default) for static type checking, or **Mypy** if selected
- **Unit Tests**
  - Runs tests across multiple Python versions and OS platforms
- **Packaging Integrity**
  - Ensures the package can be built, installed, and imported without issues
- **Optional Documentation Build**
  - Ensures documentation can be built correctly if applicable

**How it works**:
The `pr-gate.yml` workflow runs automatically on every pull request to the main branch (or other protected branches). The status check for this workflow must pass before the PR can be merged.

**Required Inputs**:
- `python-version`: Defines the Python versions for testing.
- `os`: Defines the OS platforms to test (default: `["ubuntu-latest", "windows-latest"]`).
- `extras`: Extra dependencies to install, like `.[test]` for testing dependencies.

### 2) **Additional Checks**
Depending on the repo and its needs, other checks can be enabled:
- **Pre-commit Hooks**
  - Runs additional pre-commit hooks (if configured), such as YAML validation, end-of-file fixes, etc.
- **Type Checking** (optional)
  - Can be enforced by enabling the `enable_typecheck` input in the PR gate.

### 3) **Required Reviews**
In addition to the status checks, pull requests must be reviewed by a team member or maintainers before being merged.

- **At least 1 approved review** is required to merge.
- This review ensures that the code has been properly reviewed for logic and correctness, in addition to the automated checks performed by the PR gate.

---

## Branch Protection Setup

Follow these steps to set up **branch protection** on the main branch (or any key branch) of your repo:

1. Go to the **GitHub repository settings** page.
2. Navigate to **Branches** in the left sidebar.
3. Under **Branch protection rules**, click **Add rule**.
4. In the **Branch name pattern**, enter `main` (or the branch you want to protect).
5. Enable the following options:
    - **Require status checks to pass before merging**:
      - Select the status checks: `pr-gate.yml`
    - **Require pull request reviews before merging**:
      - Enable “At least 1 review required.”
    - Optionally, enable “Require review from Code Owners” if your project uses them.
6. Optionally enable:
    - **Include administrators**: Enforce the rules even for admins.
    - **Require signed commits**: If you want all commits to be signed (good for security).

---

## Why Branch Protection Is Important

Branch protection ensures that only code that meets **EB ecosystem quality standards** is merged into the main branch. By enforcing these checks, we ensure:
- **Consistency**: All leaf repos follow the same standards defined in `eb-integration`
- **Quality**: Code is free from linting, formatting, and type-checking issues
- **Reliability**: Only working code is published to PyPI

---

## Example of Protected Branch Settings

Here's an example of how branch protection rules might be set up for the `main` branch:

1. **Require status checks to pass before merging**:
   - `pr-gate.yml` (required)
2. **Require pull request reviews before merging**:
   - **At least 1 review** required
3. **Include administrators** (optional, recommended)
4. **Require signed commits** (optional)

By enabling these rules, you enforce **all of Layer 1’s checks** before any code is merged.

---

## Summary

Branch protection ensures that all pull requests meet the standards set by the **PR Quality Gate** (Layer 1). By enforcing these rules:
- Code hygiene is automatically enforced.
- Type checking ensures fewer bugs.
- Tests are validated across platforms.
- Only working code is merged into the main branch.

For further details on how to configure these checks, refer to the **GitHub documentation** on [branch protection](https://docs.github.com/en/github/administering-a-repository/configuration-options-for-repository-branches).
