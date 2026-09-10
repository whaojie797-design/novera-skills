---
name: npm-official-prompt
description: Mini fixture skill package used by skill-supply-chain-audit tests.
---

# npm-official-prompt

## Install

The helper library installs from the default official registries:

```bash
pip install sample-helper
```

```bash
npm install -g sample-cli
```

## Workflow

1. Read the local guide in references/notes.md.
2. Run scripts/main.py to verify the installation.

## Boundaries and red lines

- Exit codes: 0 = no findings; 1 = findings present; 2 = usage error.
- Every finding carries a file:line location.
