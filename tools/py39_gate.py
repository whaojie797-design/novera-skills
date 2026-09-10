"""py39_gate.py - repository-wide Python 3.9 syntax gate.

Parses every .py file under the given paths with ast feature_version=(3, 9).
Any file that only parses on newer interpreters fails the gate.

Exit codes: 0 = all files pass, 1 = at least one file incompatible,
2 = usage or input error.
"""

import ast
import sys
from pathlib import Path


def main(argv):
    if not argv:
        sys.stderr.write("usage: python py39_gate.py DIR [DIR ...]\n")
        return 2
    checked = 0
    bad = 0
    for arg in argv:
        root = Path(arg)
        if not root.exists():
            sys.stderr.write("py39_gate: no such path: %s\n" % arg)
            return 2
        files = sorted(root.rglob("*.py")) if root.is_dir() else [root]
        for path in files:
            checked += 1
            try:
                ast.parse(path.read_text(encoding="utf-8"), mode="exec",
                          feature_version=(3, 9))
            except SyntaxError as exc:
                bad += 1
                sys.stderr.write("py39_gate: %s: %s\n" % (path, exc))
    sys.stdout.write("py39_gate: %d file(s) checked, %d incompatible\n" % (checked, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
