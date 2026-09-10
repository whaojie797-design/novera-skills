# -*- coding: utf-8 -*-
"""eval_rules.py - Check definitions and reference data for skill-eval-harness.

PURE DATA MODULE - no logic beyond constant declarations.

Contents:
  - CHECKS: E1-E12 check spec table with the profile matrix
    (minimal / novera) and each check's basis reference key.
  - STDLIB_MODULES: built-in allowlist of Python 3.9 standard library
    top-level module names (3.9 has no sys.stdlib_module_names; A7).
  - BANNED_CALL_ROOTS / OS_BANNED_FUNC_PREFIXES: modules and os.* function
    prefixes treated as network/spawn calls by E6 (AST Call matching).

Provenance for every rule's normative basis (Agent Skills open standard,
novera profile conventions) lives in references/data-provenance.md with
URL, fetch date and evidence strength.
"""

from dataclasses import dataclass, field


@dataclass
class CheckSpec:
    id: str
    group: str        # skill-md | scripts | fixtures | structure
    profiles: list    # profiles in which this check runs
    basis_ref: str    # key into references/data-provenance.md


CHECKS = {
    "E1": CheckSpec("E1", "skill-md", ["minimal", "novera"],
                    "agent-skills-standard"),
    "E2": CheckSpec("E2", "skill-md", ["minimal", "novera"],
                    "novera-profile-conventions"),
    "E3": CheckSpec("E3", "skill-md", ["minimal", "novera"],
                    "novera-profile-conventions"),
    "E4": CheckSpec("E4", "skill-md", ["minimal", "novera"],
                    "novera-profile-conventions"),
    "E5": CheckSpec("E5", "scripts", ["minimal", "novera"],
                    "novera-profile-conventions"),
    "E6": CheckSpec("E6", "scripts", ["minimal", "novera"],
                    "novera-profile-conventions"),
    "E7": CheckSpec("E7", "scripts", ["minimal", "novera"],
                    "novera-profile-conventions"),
    "E8": CheckSpec("E8", "scripts", ["novera"],
                    "novera-profile-conventions"),
    "E9": CheckSpec("E9", "fixtures", ["minimal", "novera"],
                    "novera-profile-conventions"),
    "E10": CheckSpec("E10", "structure", ["minimal", "novera"],
                     "novera-profile-conventions"),
    "E11": CheckSpec("E11", "structure", ["minimal", "novera"],
                     "novera-profile-conventions"),
    "E12": CheckSpec("E12", "structure", ["minimal", "novera"],
                     "novera-profile-conventions"),
}

# Profile presets: which checks run by default per profile. --only overrides.
PROFILE_CHECKS = {
    "minimal": [cid for cid, spec in CHECKS.items() if "minimal" in spec.profiles],
    "novera": [cid for cid, spec in CHECKS.items() if "novera" in spec.profiles],
}

# novera profile E3 expectations (lead ruling on A6: exact match, no tolerance)
NOVERA_TRIGGER_COUNT = 8
NOVERA_NON_TRIGGER_COUNT = 4
NOVERA_E2E_COUNT = 1

# E2 line budget (novera profile conventions; see data-provenance)
LINE_BUDGET = 500

# ---------------------------------------------------------------------------
# Python 3.9 standard library top-level module allowlist (A7). Local sibling
# imports (module names backed by files inside the evaluated scripts/ dir)
# are allowed separately by checkers.py.
STDLIB_MODULES = frozenset([
    "abc", "aifc", "antigravity", "argparse", "array", "ast", "asynchat",
    "asyncio", "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2", "calendar", "cmath", "cmd",
    "code", "codecs", "codeop", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars", "copy",
    "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses", "dataclasses",
    "datetime", "dbm", "decimal", "difflib", "dis", "distutils", "doctest",
    "email", "encodings", "ensurepip", "enum", "errno", "faulthandler",
    "filecmp", "fileinput", "fnmatch", "fractions", "ftplib", "functools",
    "gc", "getopt", "getpass", "gettext", "glob", "graphlib", "gzip",
    "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib",
    "imghdr", "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
    "json", "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
    "modulefinder", "msilib", "msvcrt", "multiprocessing", "netrc", "nis",
    "nntplib", "numbers", "operator", "os", "pathlib", "pdb", "pickle",
    "pickletools", "pipes", "pkgutil", "platform", "plistlib", "poplib",
    "posix", "posixpath", "pprint", "profile", "pstats", "pty", "pwd",
    "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random", "re",
    "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
    "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
    "sqlite3", "ssl", "stat", "statistics", "string", "stringprep", "struct",
    "subprocess", "sunau", "symtable", "sys", "sysconfig", "tarfile",
    "telnetlib", "tempfile", "termios", "textwrap", "threading", "time",
    "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
    "tracemalloc", "tty", "turtle", "types", "typing", "unicodedata",
    "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave",
    "weakref", "webbrowser", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp",
    "zipfile", "zipimport", "zlib", "zoneinfo",
])

# E6: any Call whose dotted target starts with one of these module paths is
# a network/spawn call. urllib.parse is NOT banned (stdlib urlparse work).
BANNED_CALL_ROOTS = ("socket", "urllib.request", "http.client", "subprocess",
                     "telnetlib", "ftplib", "smtplib", "poplib", "imaplib",
                     "nntplib", "xmlrpc.client", "asyncio")

# E6: os.<func> call names that are process spawning / code execution.
OS_BANNED_FUNC_PREFIXES = ("system", "popen", "exec", "spawn")

# E12: forbidden filename patterns inside a skill package (case-insensitive,
# matched on the file basename).
FORBIDDEN_FILE_PATTERNS = ("readme*", "changelog*", "install*")
