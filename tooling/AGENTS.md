# Electric Barometer — Agent Guidelines

Canonical AI / agent development rules for the Electric Barometer ecosystem.
Leaf repositories reach this file via the shared `tooling/` symlink (or CI tooling sync).

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
