---
description: Read docs/PRD.md and produce docs/ARCHITECTURE.md
model: sonnet
---

ROLE: Software architect producing a committed Architecture Decision Record
TASK: Read docs/PRD.md and produce a single, committed architecture for the app
CONTEXT: Requirements are locked in docs/PRD.md. Architecture must be constrained by the spec — not an open-ended design exercise. Every decision must be justified against a specific PRD requirement.
OUTPUT FORMAT: docs/ARCHITECTURE.md with sections listed in Step 1–3. One committed architecture, not a menu of options.
STOP CONDITIONS: No implementation code. No package installation. If you surface multiple options, commit to one before saving — "Rejected Options" is a required section.

Read docs/PRD.md. Do NOT write code. Do NOT install packages.

## Step 1 — Stack proposal
For each decision, name ONE choice and give a one-line justification tied to a PRD requirement:
- Language + framework (with reason)
- Database or persistence approach (with reason — omit if the PRD implies none)
- Required libraries only (each must map to a PRD feature — no speculative additions)
- Folder tree — as shallow as the chosen stack's own conventions allow; justify any level beyond what's idiomatic for that stack/framework
- Core data models (field names and types only — no code)

## Step 2 — Overengineering audit (mandatory)
For every library and architectural pattern proposed, ask: "Is this required by a PRD feature, or am I adding it speculatively?"
List each item with verdict: REQUIRED (cite PRD feature) or SPECULATIVE.
Ask the user: keep or cut each SPECULATIVE item. Wait for answer before continuing.

## Step 3 — ADR (Architecture Decision Record)
Produce one ADR with these sections:
- **Decision**: What is being built and with what stack
- **Rationale**: Why this stack satisfies the PRD constraints (cite requirement numbers where possible)
- **Rejected Options**: What alternatives were considered and why each was rejected against the spec
- **Risks**: What could go wrong with this decision
- **Phase Plan**: Phase 1 = foundation only (no business logic, independently runnable); each subsequent phase adds exactly one feature group, independently testable. Choose the grouping unit (feature, layer, or module) that best fits the chosen stack and say which one you used.

If you find yourself listing options without committing, stop and pick one. Justify it. The user can override — but you must commit first.

## Step 4 — Save
Write docs/ARCHITECTURE.md. Print phase count. Stop.
