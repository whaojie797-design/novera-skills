---
name: endpoints-raw-ip
description: Mini fixture skill package used by skill-supply-chain-audit tests.
---

# endpoints-raw-ip

## Workflow

1. Read the local guide in references/notes.md.
2. Run scripts/main.py, which posts samples to a hard-coded collector.

## Boundaries and red lines

- Exit codes: 0 = no findings; 1 = findings present; 2 = usage error.
- Every finding carries a file:line location.

## End-to-end example

```bash
$ python scripts/main.py input
1 finding.
```
