# Electric Barometer — LLM Integration

This directory contains the canonical artifacts that govern how a
large language model (LLM) interacts with the Electric Barometer (EB)
ecosystem during design, implementation, and analysis workflows.

The goal of this directory is to make EB discoverable, composable,
and safe to use in interactive sessions by providing explicit,
machine-readable, and human-readable context.

---

## Purpose

Electric Barometer spans multiple repositories and layers
(contracts, metrics, evaluation, optimization, adapters, integration).
Without an explicit catalog and workflow map, interactive use can
devolve into:

- guessing function names
- re-implementing existing logic
- bypassing governance or validation layers
- ad-hoc pipelines that drift from canonical behavior

The `llm/` directory exists to prevent this.

It establishes:
- a single source of truth for public EB functionality
- canonical workflows (“golden paths”)
- non-negotiable collaboration rules for LLM-driven work

---

## Contents

### `system.txt`
Defines the **non-negotiable system rules** governing LLM behavior.

It specifies:
- core collaboration principles
- authoritative sources and precedence
- prohibited behaviors (guessing, shortcuts, silent bypassing)
- expectations when workflows are missing

This file is the highest-level behavioral contract.

---

### `bootstrap.md`
Provides **human-facing instructions** for starting a new LLM session.

It includes:
- which files to load at session start
- a copy-paste session instruction block
- guidance on how to describe tasks and inputs
- expected LLM behavior when bootstrapped correctly

This file exists to make correct usage easy and repeatable.

---

### `api_index.json` (generated)
A **machine-generated inventory** of all public Electric Barometer APIs.

It is produced by tooling in `tooling/` and enumerates:
- public functions and classes
- import paths and signatures
- high-level intent (doc summaries)
- optional input/output metadata

Only APIs listed in this file are considered available to the LLM.

If an API is not indexed, it must not be used.

---

### `workflows.yml`
A **hand-authored, curated set of canonical workflows**.

Each workflow documents:
- intent and scope
- required inputs (columns, contracts)
- expected outputs
- the ordered sequence of public APIs

Workflows represent the intended way EB functionality is composed.
They should be stable, versioned, and treated as “golden paths.”

---

## Authoritative Precedence

When resolving what functionality exists or how it should be used,
the following order applies:

1. `api_index.json`
2. `workflows.yml`
3. Public package APIs (`__all__`)
4. EB documentation and contracts

If information is missing from these sources, the correct behavior is
to identify the gap — not to invent behavior.

---

## Design Philosophy

The artifacts in this directory reflect Electric Barometer’s core values:

- explicit contracts over implicit assumptions
- governed workflows over ad-hoc pipelines
- reuse over reinvention
- correctness over convenience

The LLM is treated as a collaborator, not an oracle.

---

## Evolution

This directory is expected to evolve as the EB ecosystem grows.

Planned extensions include:
- expanded API metadata (stability, deprecation, variants)
- additional workflows as new use cases emerge
- tooling to validate consistency between code and metadata

All additions should preserve the core principle:
**LLM-driven work must be constrained, explicit, and reproducible.**
