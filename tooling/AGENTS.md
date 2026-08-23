# Electric Barometer — Agent Guidelines

Canonical AI / agent development rules for the Electric Barometer ecosystem.
Leaf repositories reach this file via the shared `tooling/` symlink (or CI tooling sync).

## Quality Control & Commit Requirements

### Mandatory Check Execution

Before completing any task, staging changes, or creating a git commit in any
repository across the ecosystem, run:

```text
python tooling/check.py
```

This script executes the mandatory verification chain:

1. `ruff format`
2. `ruff lint`
3. `pyright` (static type checking)
4. `pre-commit` checks
5. `pytest` test suite

### Resolution Obligation

Zero-tolerance: do not stage, commit, or push code if `python tooling/check.py`
fails. If the script reports any failures (formatting, linting, type errors, or
failing tests), fix them and rerun `python tooling/check.py` until it returns a
clean 100% pass.

### Symlink Awareness

`AGENTS.md` in leaf repositories is a symlink that points back to this file in
`eb-integration`. Preserve the symlink. Do not replace it with a concrete file.

## Changelog Mandate

Any modification to source code, APIs, or package metadata **MUST** include a
corresponding entry in that package's local `CHANGELOG.md` under `[Unreleased]`
or the active version header.

## Explicit Parameter Contracts

Avoid adding implicit or hardcoded default fallbacks for domain, operational, or
penalty parameters. Force callers or contracts to pass parameters explicitly
("no hidden heuristics").

## Typing & Root Exports

Maintain PEP 561 compliance (`py.typed`), strict type annotations, and expose new
public symbols in root `__init__.py` files.

## Decoupled Scope

Leaf changes must only touch local package files. System-wide master changelogs
are compiled at the integration hub level in CI.

## Documentation & Voice Protocol

Published docs, module docstrings, READMEs, and script headers must read as
native library documentation—not chat transcripts or prompt specifications.

1. **No conversational leftovers.** Do not use meta-announcements, chat outros
   (e.g. "If you want, next we can…"), or second-person tutorial phrasing in
   committed documentation.
2. **Concise module docstrings.** Module headers are 1–2 imperative sentences
   focused on technical mechanics. Do not write multi-paragraph essays with
   "Motivation", "Design goals", or "If you only have a single…" asides.
3. **No redundant default notes.** Do not restate "Required; there is no
   default" when the function signature already omits a default. Docstrings
   describe meaning and expected types only.
4. **Imperative voice.** Prefer objective statements ("Computes…", "Groups by…",
   "Avoids hard dependency…") over first-person narrative ("We compute…",
   "We intentionally avoid…").
