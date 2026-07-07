---
description: Distill PRD + ARCHITECTURE into a lean CLAUDE.md
model: haiku
---

ROLE: Technical writer who produces actionable developer reference docs
TASK: Distill docs/PRD.md and docs/ARCHITECTURE.md into a lean CLAUDE.md
CONTEXT: CLAUDE.md is loaded into every future Claude session for this project. It must be dense and actionable — not a summary of the docs. The docs are already referenced via @imports and will be read separately.
OUTPUT FORMAT: CLAUDE.md using the template below, target under 150 lines
STOP CONDITIONS: Do not duplicate content from PRD.md or ARCHITECTURE.md. Do not include feature descriptions, rationale, or aspirations. Reference the docs via @imports instead.

Read docs/PRD.md and docs/ARCHITECTURE.md.

## Rules for CLAUDE.md content
Include ONLY:
- Commands — exact shell commands, copy-paste ready, for whichever of build/test/lint/dev-server/run/install actually apply to the chosen stack. Skip any that don't exist for this project (e.g. a library has no dev server; a script has no build step).
- Conventions Claude would otherwise get wrong (naming patterns, file placement, layer rules) — derive these from ARCHITECTURE.md's actual stack and layering, not from any fixed example.
- Hard constraints (e.g. "never import X in Y layer") specific to this project's architecture.
- @docs/PRD.md and @docs/ARCHITECTURE.md as imports (reference, don't duplicate)

Exclude:
- Feature descriptions (already in PRD.md)
- Architecture rationale (already in ARCHITECTURE.md)
- Anything Claude can derive from reading the code itself
- Aspirations, goals, or explanatory prose

## Template to fill
```
# [App name]
@docs/PRD.md
@docs/ARCHITECTURE.md

## Commands
- [label]: [command]   ← one line per command that actually exists for this stack

## Conventions
- [one hard rule per line, 10–20 lines max]

## Constraints
- [absolute prohibitions only, 5–10 lines max]
```

## Self-check (mandatory before saving)
1. Count lines in the draft.
2. 150 lines is a target, not a hard wall — for a large polyglot or multi-service project it's fine to exceed it. If you exceed 150, briefly justify why (e.g. "N services each need their own command block") rather than cutting substance.
3. If over 150 with no such justification: cut the least actionable lines until under 150. List what you cut and why.
4. Verify every line is either a command, a convention Claude would get wrong, or a hard constraint. Remove anything else.

Save to CLAUDE.md.
Print: "CLAUDE.md saved — [N] lines"
Stop.
