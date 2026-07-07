---
description: Validate a completed phase against spec, conventions, and tests
argument-hint: "<phase-num>"
model: haiku
allowed-tools: Agent, Bash(git diff:*), Bash(git log:*)
---

ROLE: QA orchestrator — spawn agents, collect results, report only
TASK: Validate Phase $ARGUMENTS against spec, conventions, and tests
CONTEXT: Phase $ARGUMENTS has just been committed. Validation checks three independent concerns in parallel: spec compliance, convention adherence, and test passage.
OUTPUT FORMAT: Structured report using the exact template below
STOP CONDITIONS: Do not read files yourself. Do not fix anything. Report only. Do not start Phase $ARGUMENTS+1.

## Inputs
Phase number: $ARGUMENTS

Evaluate these before spawning agents:
```
Recent commits:   !git log --oneline -10
```

Find the commit(s) belonging to Phase $ARGUMENTS: look for a commit message starting with "Phase $ARGUMENTS:" (the format build-phase.md uses). If the phase spans multiple commits, diff from the commit immediately before the first Phase $ARGUMENTS commit through HEAD. If exactly one commit matches, diff that commit against its parent. Then run:
```
Changed files:    !git diff --name-only <range-determined-above>
```

Collect the changed files list into a variable — pass it explicitly to each agent rather than re-running the git command inside agent prompts.

## Spawn these 3 agents in parallel

### Agent 1 — spec-validator
```
phase_number: $ARGUMENTS
changed_files: [list from git diff above]
instruction: >
  ROLE: QA engineer verifying spec compliance
  TASK: Check whether Phase $ARGUMENTS acceptance criteria from docs/PRD.md are satisfied by the changed files
  CONTEXT: Changed files are listed above. Read each file and map its implementation to the corresponding PRD acceptance criteria for Phase $ARGUMENTS.
  OUTPUT FORMAT: Markdown table — criterion | YES/PARTIAL/NO | one-line evidence
  STOP CONDITIONS: Do not check conventions or run tests. Spec compliance only.
```

### Agent 2 — convention-checker
```
changed_files: [list from git diff above]
instruction: >
  ROLE: Senior engineer enforcing code conventions
  TASK: Check whether all changed files comply with the conventions in CLAUDE.md
  CONTEXT: Changed files are listed above. Read CLAUDE.md for the full convention list, then check each changed file.
  OUTPUT FORMAT: List violations as "file:line — rule violated — fix". If no violations, output "no violations".
  STOP CONDITIONS: Do not check spec compliance or run tests. Conventions only.
```

### Agent 3 — test-reporter
```
phase_number: $ARGUMENTS
instruction: >
  ROLE: QA engineer running the test suite
  TASK: Run the project test suite and return a structured pass/fail report for Phase $ARGUMENTS
  CONTEXT: Read CLAUDE.md for the exact test command to run.
  OUTPUT FORMAT: Total tests | Passed | Failed | list of failing test names (if any)
  STOP CONDITIONS: Run tests only. Do not fix failures.
```

Wait for ALL 3 agents to complete before printing anything.

## Output format
Print this exact structure — no extra commentary:

```
================================================
PHASE $ARGUMENTS VALIDATION REPORT
================================================

SPEC COMPLIANCE
---------------
[paste spec-validator output verbatim]

CONVENTION CHECK
----------------
[paste convention-checker output verbatim]

TEST RESULTS
------------
[paste test-reporter output verbatim]

================================================
OVERALL: [PASS / FAIL / NEEDS REVIEW]
  PASS         = all criteria YES, no violations, tests green
  NEEDS REVIEW = any PARTIAL or minor violations, tests green
  FAIL         = any NO criteria, tests red, or blocking violations
================================================

NEXT STEP: [one sentence — "safe to start Phase N+1" or "fix [specific items] before proceeding"]
================================================
```

Stop here. Do not start Phase $ARGUMENTS+1.
