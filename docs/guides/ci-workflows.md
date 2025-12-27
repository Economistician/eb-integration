# CI workflows (how they run and how to debug)

This page explains how CI is structured across the Electric Barometer ecosystem,
with a focus on workflows provided by `eb-integration` and how they interact with
workflows inside each repository.

---

## Why multiple workflows may run

It is normal to see multiple jobs or workflows run on a single push or PR, for
example:

- a repository-level CI workflow (tests, build, packaging checks)
- a repository-level lint workflow (calls shared Ruff workflow)
- organization-level or reusable workflows called by other workflows

If your repository has both:
- `.github/workflows/ci.yml` (tests/build), and
- `.github/workflows/lint.yml` (Ruff),

then a push will often trigger **both**.

This is expected and desirable: linting and tests fail for different reasons and
have different remediation steps.

---

## The shared Ruff workflow pattern

In EB repos, linting is standardized by calling:

- `Economistician/eb-integration/.github/workflows/ruff.yml@main`

That workflow:
1. checks out the caller repository
2. checks out `eb-integration` into `.eb-integration/`
3. runs:
   - `ruff format --check`
   - `ruff check`

The caller repo does **not** need a local Ruff config.

---

## Reproducing CI locally

When CI fails, reproduce locally before pushing fixes.

### Formatting failures

CI output typically looks like:

- `Would reformat: <file>`
- `X files would be reformatted`

Fix by running:

```bash
ruff format --config ../eb-integration/tooling/ruff.toml .
```

(or Windows)

```powershell
ruff format --config ..\eb-integration\tooling\ruff.toml .
```

Then commit the changes.

### Lint failures

Fix by running:

```bash
ruff check --config ../eb-integration/tooling/ruff.toml .
```

For auto-fixable lint:

```bash
ruff check --fix --config ../eb-integration/tooling/ruff.toml .
```

Note: Some rules cannot be auto-fixed safely and require manual edits.

---

## What to do when checks pass locally but fail in CI

Common causes:

- **Different Ruff versions**
  - CI installs Ruff fresh each run.
  - Locally you may be using an older/newer version.
  - Check with: `ruff --version`

- **Uncommitted changes**
  - CI runs on the pushed commit only.
  - Ensure you committed formatted output.

- **Path differences**
  - CI uses `.eb-integration/tooling/ruff.toml` because it checks out the tooling repo.
  - Locally you may be pointing at the wrong config file.

---

## Recommended workflow layout per repo

A typical EB repo should have:

- `ci.yml` for tests, packaging checks, and build validation
- `lint.yml` for Ruff (calls shared workflow)

Keep them separate:
- Lint should be fast and fail early.
- Tests may take longer and produce different diagnostics.

---

## When to change CI structure

If CI becomes noisy or duplicated, the correct solution is usually:

- tighten `on:` triggers (e.g., restrict `push` to main branches, rely on PRs)
- consolidate jobs inside a single workflow file if desired

But separate workflows are still normal in professional repos.

---

## Next steps

As the ecosystem grows, `eb-integration` may add additional shared workflows
(e.g., for packaging validation or smoke testing). When added, each workflow will
be documented in `reference/github-actions.md` with its inputs and guarantees.