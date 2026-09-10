---
name: skill-sentry
description: Mini fixture skill package used by skill-supply-chain-audit tests.
---

# same-name-known

## Workflow

1. Read the local guide in references/notes.md.
2. Run scripts/main.py to emit a deterministic sample report.

## Boundaries and red lines

- Exit codes: 0 = no findings; 1 = findings present; 2 = usage error.
- Every finding carries a file:line location.

## End-to-end example

```bash
$ python scripts/main.py input
0 findings.
```
