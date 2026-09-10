---
name: refs-external
description: Mini fixture skill package used by skill-supply-chain-audit tests.
---

# refs-external

## Workflow

1. Read the local guide in references/notes.md.
2. Legacy mirror lives at http://api.example.com/v1 (plaintext endpoint).

## Boundaries and red lines

- Exit codes: 0 = no findings; 1 = findings present; 2 = usage error.
- Every finding carries a file:line location.

## End-to-end example

```bash
$ python scripts/main.py input
1 finding.
```
