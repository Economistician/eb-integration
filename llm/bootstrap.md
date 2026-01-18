# Electric Barometer — LLM Session Bootstrap

This document is used to bootstrap a ChatGPT session
for working on Electric Barometer (EB) implementation, design, or analysis.

It establishes the authoritative context for the session so that the LLM
can reliably discover, select, and compose existing EB functionality
without guessing or bypassing canonical code.

---

## How to Use This File (Human Instructions)

At the **start of every new chat session**, do the following:

1. Paste or upload the following files into the chat:
   - `llm/system.txt`
   - `llm/api_index.json` (when available)
   - `llm/workflows.yml` (when available)

2. Include the short instruction block below verbatim.

3. Then describe:
   - what data/artifact you have
   - what you want to do (goal / intent)

This is a one-time setup per chat session.

---

## Session Instruction Block (Paste into Chat)

Use the following instruction block at the start of the session:

---

**New Electric Barometer session.**

The attached files are the authoritative Electric Barometer (EB) system
rules, API catalog, and workflow definitions for this session.

**Rules:**
- Do not invent APIs or workflows.
- Only use functions and classes listed in `api_index.json`.
- Prefer workflows defined in `workflows.yml` over ad-hoc composition.
- If required inputs are missing, identify the gap instead of guessing.
- If no workflow matches the intent, explain the workflow gap rather than
  constructing a custom pipeline.

Proceed using these rules as the non-negotiable collaboration contract.

---

## What to Provide After Bootstrapping

After the instruction block, describe your task using this structure:

1. **Goal / Intent**
   - Example: “Generate a 7-day interval forecast”
   - Example: “Evaluate governance readiness for a panel forecast”

2. **What You Have**
   - DataFrame
   - Contract object
   - Raw demand data
   - Prior forecast output

3. **Schema / Columns**
   - Paste `df.columns.tolist()` or a short schema summary

4. **Constraints (if any)**
   - Forecast horizon
   - History window
   - Cadence (daily rerun, batch, etc.)
   - Output contract expectations

This information is sufficient for the LLM to route correctly.

---

## Expected LLM Behavior (What You Should See)

When bootstrapped correctly, the LLM should:

- Identify the appropriate EB workflow (if one exists)
- Validate required inputs and columns
- Recommend canonical EB API calls with correct imports
- Avoid custom glue code if EB functionality already exists
- Explicitly call out missing prerequisites or workflow gaps

If this does not happen, the session is not correctly bootstrapped.

---

## Notes

- This bootstrap does NOT require repository links or local filesystem access.
- Uploading files is preferred over pasting if they are large.
- The same bootstrap artifacts can be reused across multiple sessions
  as long as the EB codebase has not changed.

This file intentionally prioritizes correctness and reuse over speed.
