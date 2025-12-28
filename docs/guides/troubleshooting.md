# Troubleshooting Guide for EB Integration

This guide helps you troubleshoot common issues when working with **eb-integration** workflows, including PR gating, release pipelines, and post-release verification. If you encounter issues during the CI/CD process, refer to the sections below for potential solutions.

---

## 1. PR Gate Issues

### Issue 1: **PR Gate Fails Due to Linting (Ruff) Issues**

**Error Message:**
```
ruff format --check failed
ruff check failed
```

**Possible Causes:**
- **Code style violations**: Ruff enforces strict code formatting and linting rules.
- **Unformatted code**: If the codebase isn't formatted according to the defined rules, the workflow will fail.

**Solutions:**
- **Run Ruff locally** to catch errors before pushing:
  ```bash
  ruff check .
  ruff format --check
  ```
- **Fix issues automatically** using Ruff’s built-in auto-fixing:
  ```bash
  ruff format .
  ```

### Issue 2: **Type Checking Fails**

**Error Message:**
```
pyright: [error] Missing type information
```

**Possible Causes:**
- **Missing type annotations**: Pyright checks for missing type annotations in functions or variables.
- **Incompatible types**: Pyright identifies type mismatches or violations of the declared types.

**Solutions:**
- **Add type annotations** to missing parts of the code. If you're using Pyright with strict settings, it will report missing types.
- **Use `--ignore` flag temporarily** if a certain file or section doesn’t need type checking:
  ```bash
  pyright --ignore "src/utils/special_case.py"
  ```

---

## 2. Release Pipeline Issues

### Issue 1: **Release Fails During Build Step**

**Error Message:**
```
python -m build --sdist --wheel failed
```

**Possible Causes:**
- **Missing or misconfigured `setup.py`**: If the `setup.py` file is missing required metadata or is misconfigured, the build step will fail.
- **Incorrect Python version**: Ensure that the correct Python version is being used for building the release.

**Solutions:**
- **Ensure the `setup.py` file is correct**: Check that it includes all required fields (e.g., `name`, `version`, `author`, etc.).
- **Check the Python version** used in the build step. It should match the version required for your project.
- **Build the package locally**:
  ```bash
  python -m build --sdist --wheel
  ```

### Issue 2: **Twine Check Fails**

**Error Message:**
```
python -m twine check dist/* failed
```

**Possible Causes:**
- **Invalid package metadata**: This occurs if the `setup.py` or `pyproject.toml` contains invalid metadata or missing fields.
- **Missing dependencies**: If your `sdist` or wheel package is missing dependencies or files, Twine will fail the check.

**Solutions:**
- **Run Twine check locally** to diagnose issues before pushing to PyPI:
  ```bash
  python -m twine check dist/*
  ```
- **Ensure all required files are included in `MANIFEST.in`** for source distribution packaging.

---

## 3. Post-Release Verification Issues

### Issue 1: **PyPI Smoke Test Fails**

**Error Message:**
```
ImportError: cannot import name 'some_module' from 'some_package'
```

**Possible Causes:**
- **Package not installed properly**: The smoke test fails if the package can’t be imported after installation.
- **Missing dependencies**: If the required dependencies are not installed or included in the distribution, the import will fail.

**Solutions:**
- **Check PyPI installation**: Ensure the package is installed from PyPI correctly:
  ```bash
  python -m pip install <your_package_name>
  ```
- **Verify the package’s dependencies** are properly listed in `setup.py` or `pyproject.toml`.
- **Run the smoke test locally** using the same commands as in the workflow to simulate the issue:
  ```bash
  python -c "import <your_package_name>"
  ```

### Issue 2: **Wheel Installation Fails**

**Error Message:**
```
Failed to install wheel from dist/*
```

**Possible Causes:**
- **Corrupt wheel file**: If the wheel file is incomplete or corrupted, it can’t be installed.
- **Incompatible wheel format**: Ensure the wheel is built for the correct Python version and platform.

**Solutions:**
- **Rebuild the wheel** using:
  ```bash
  python -m build --wheel
  ```
- **Install the wheel manually** to check for issues:
  ```bash
  python -m pip install dist/*.whl
  ```

---

## 4. General Troubleshooting Tips

### Issue 1: **GitHub Action Failures with `actions/checkout@v4`**

**Error Message:**
```
Checkout step failed: The repository could not be found
```

**Possible Causes:**
- **Permissions issue**: Ensure that the workflow has proper permissions to access the repository. This is common when working with private repositories.

**Solutions:**
- Ensure that the repository being checked out is accessible to the GitHub Action.
- If you're using private repositories, ensure that you have a GitHub token with the correct permissions to access the repositories.

### Issue 2: **Dependencies or Versioning Conflicts**

**Error Message:**
```
pip install -U -r requirements.txt failed
```

**Possible Causes:**
- **Conflicting versions**: There may be conflicts between package versions in `requirements.txt` or `pyproject.toml`.
- **Outdated dependencies**: Ensure that all dependencies are up-to-date and compatible with each other.

**Solutions:**
- **Check for version conflicts** by manually inspecting `requirements.txt` and `pyproject.toml`.
- Run `pip freeze` locally to verify installed versions.

### Issue 3: **Workflow Timeouts or Resource Limits**

**Error Message:**
```
The workflow exceeded the maximum execution time
```

**Possible Causes:**
- **Timeouts during testing**: CI pipelines may exceed their time limits if tests are slow.
- **Resource limits**: Some workflows might hit resource usage limits (CPU, memory, etc.).

**Solutions:**
- **Optimize test suite** to run faster (e.g., parallel testing).
- **Use caching** to speed up repeated steps.
- **Increase GitHub Action timeout** if necessary, though be mindful of the limits.

---

## Summary

If you encounter any issues, follow the troubleshooting steps above for common CI/CD problems. Most errors can be resolved by reviewing the configuration, fixing minor bugs in the code, or ensuring that your dependencies are correctly set up.

For more detailed assistance, refer to the GitHub Actions [documentation](https://docs.github.com/en/github/actions).
