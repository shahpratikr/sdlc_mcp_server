---
description: Build phase of the app — scaffold, implement, test, commit
argument-hint: "<phase-num>"
model: sonnet
context: fork
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Glob, Grep
---

## PHASE NUMBER — READ THIS FIRST
PHASE_NUM = $ARGUMENTS (take the first token as the integer phase number).
You MUST implement exactly Phase PHASE_NUM as numbered in docs/ARCHITECTURE.md.
Do NOT auto-detect the phase from git history, existing files, or any other heuristic.
If $ARGUMENTS is "1", implement Phase 1. If "3", implement Phase 3. No exceptions.

ROLE: Senior engineer implementing a single, spec-referenced phase
TASK: Implement Phase PHASE_NUM of the app as defined in docs/ARCHITECTURE.md, with every piece of code traceable to a PRD requirement
CONTEXT: Spec is in docs/PRD.md (requirements have IDs per that PRD's own numbering scheme). Architecture phase plan is in docs/ARCHITECTURE.md. Conventions are in CLAUDE.md. Previous phases are already committed — do not touch them unless broken.
OUTPUT FORMAT: Working code committed to git, plus the report in Step 6
STOP CONDITIONS: Implement Phase PHASE_NUM ONLY. Nothing from Phase PHASE_NUM+1. No speculative abstractions. No refactoring outside this phase's scope.

## Setup
Read these files before doing anything else:
1. CLAUDE.md — conventions and commands. Note the exact test command listed under Commands — you will run this verbatim in Step 4. Note the requirement-citation convention (e.g. `// R-##`, `# R-##`, a docstring tag) if CLAUDE.md specifies one; otherwise default to a same-line comment in the file's native comment syntax citing the requirement ID scheme used in docs/PRD.md.
2. docs/PRD.md — requirements (note the requirement ID scheme, e.g. R-1, R-2, or whatever numbering the PRD actually uses)
3. docs/ARCHITECTURE.md — read the FULL file; extract the Phase PHASE_NUM section AND the folder structure, data models, database schema sections, and the declared architecture layers/module boundaries and their dependency direction (e.g. domain has no dependents among lower layers, or module A must not import module B)

Extract from docs/ARCHITECTURE.md for Phase PHASE_NUM:
- The exact bullet list of deliverables for Phase PHASE_NUM
- Every file path mentioned in the folder structure that belongs to Phase PHASE_NUM's scope
- Every data model definition (field names, types, constraints) relevant to this phase
- Every database schema (SQL) relevant to this phase

These extracted definitions are your source of truth for field names, file placement, and layer boundaries. Do NOT invent field names or file paths — use exactly what docs/ARCHITECTURE.md specifies.

Current branch:          !git branch --show-current
Last commit:             !git log --oneline -1
Uncommitted changes:     !git status --short

## Rules (enforce all — do not skip any)
- Every implemented function or class must include a comment citing its PRD requirement, using the citation convention identified in Setup step 1
- Keep only 1 line in functions for that requirement citation comment — never a multi-line comment block or docstring
- Follow every naming convention, file placement rule, and layer constraint in CLAUDE.md exactly
- Field names in domain models, entities, and data-access objects must match docs/ARCHITECTURE.md exactly — use its exact names, never abbreviate or rename
- File paths must match the folder structure in docs/ARCHITECTURE.md exactly
- Database column names must match the SQL schema in docs/ARCHITECTURE.md exactly
- Only implement files and features listed in Phase PHASE_NUM's deliverables — nothing from other phases
- If unsure about a design decision → STOP and ask. Never assume.
- Do not refactor code from previous phases unless it is demonstrably broken by this phase's changes.
- Clean up any temp or scratch files before finishing.

## Step 1 — Scaffold
Create the folder structure and empty files for Phase PHASE_NUM.
Show the file tree. STOP. Wait for explicit approval before writing any logic.

## Step 2 — Implement
Write logic file by file, in the dependency order declared by docs/ARCHITECTURE.md's layers/modules (lowest-level, most-depended-upon code first; code that depends on it follows). If ARCHITECTURE.md doesn't spell out an explicit build order, infer it from its stated dependency direction between layers/modules.
After EACH file:
- Print a 2-line summary: what it does | what it exports
- Confirm it satisfies the PRD requirement(s) it implements (cite its requirement ID)
Do not move to the next file until the current one is complete.

## Step 3 — Self-review
Before running tests, verify:
- Every public class/function has a requirement citation using the convention identified in Setup step 1
- Every file follows CLAUDE.md naming and placement conventions
- No code belonging to Phase PHASE_NUM+1 crept in — remove it if so
- No hardcoded values that should be constants or config

## Step 4 — Test
Run the exact test command from CLAUDE.md's Commands section (noted in Setup step 1). Never assume or substitute a different build tool's command — if CLAUDE.md doesn't list one, stop and ask the user for it before proceeding.
- If tests fail: fix them now. Do NOT proceed with failing tests.

## Step 5 — Commit
Stage only the files created or modified in this phase. Do NOT use `git add -A`.
Commit message must be a single line, exactly:
```
git commit -m "Phase PHASE_NUM: [short phase title from ARCHITECTURE.md]"
```
Do NOT add a body, bullet points, file lists, requirement ID lists, or any other content beyond this single line.

## Step 6 — Report and stop
Print exactly:
```
Phase PHASE_NUM complete.
Files created: [list]
Requirements covered: [requirement ID list, per PRD's own numbering scheme]
Tests: PASS / FAIL
Commit: [hash]
```

Do NOT start Phase PHASE_NUM+1. Stop here and wait.
