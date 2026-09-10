# -*- coding: utf-8 -*-
"""chain_rules.py - pure data module for skill-supply-chain-audit.

Contains: default thresholds (each explicitly marked as a default
convention, never a fact), well-known skill name list, risky install
patterns, registry allowlist, SARIF level mapping, and severity per rule.

Every threshold in THRESHOLDS carries is_convention=True:
it is a drafting default (default_convention: true), NOT a verified fact.
Reports must label each threshold as "default convention" when used.

Dependency direction: chain_rules -> (nothing). Nobody may import back.
"""

from dataclasses import dataclass


@dataclass
class Threshold:
    value: float
    unit: str
    is_convention: bool = True  # default_convention: true, always


# ---------------------------------------------------------------------------
# Default thresholds (draft values; default_convention: true for each).
# None of these numbers is a measured or verified fact.
# ---------------------------------------------------------------------------

THRESHOLDS = {
    # S1: a repo whose last push is older than this many days (measured from
    # the snapshot anchor) is reported stale. default_convention: true
    "stale_days": Threshold(180, "days"),
    # S2: fewer unique maintainers/contributors than this count is reported.
    # default_convention: true
    "min_maintainers": Threshold(2, "count"),
    # S3: no release published within this window (or none ever) is reported.
    # default_convention: true
    "release_window_days": Threshold(365, "days"),
    # S4: open issues / (open + closed issues) above this ratio is reported.
    # Requires both counts in the snapshot; missing counts => check skipped.
    # default_convention: true
    "max_open_ratio": Threshold(0.8, "ratio"),
    # S10: edit distance between a candidate name and a well-known skill name
    # at or below this value (and not an exact match) is reported as an
    # impersonation signal. default_convention: true
    "impersonation_max_distance": Threshold(2, "edit-distance"),
}

# Negation / counter-example wording used by the S8 double condition
# (install pattern + negation/quote context). A curl|sh hit inside a code
# block whose nearby context contains one of these markers is treated as a
# documented counter-example and is NOT reported.
NEGATION_MARKERS = (
    "avoid", "do not", "don't", "never run", "never pipe",
    "not recommended", "dangerous", "unsafe",
    "不要", "切勿", "勿", "不推荐", "危险", "反例", "禁止",
)

# ---------------------------------------------------------------------------
# Well-known skill name list (S10 baseline).
# v0.1 scope: only the novera skill family names, which are organizational
# facts (this repo + the planned sibling tooling named in the repo docs).
# Public registry / marketplace well-known lists were NOT verified during
# implementation => status "unverified", kept out of the v0.1 list on
# purpose (honesty red line: do not invent a catalog).
# ---------------------------------------------------------------------------

WELL_KNOWN_SKILLS = frozenset({
    "geo-evidence-audit",
    "ai-tool-directory-publisher",
    "skill-eval-harness",
    "skill-supply-chain-audit",
    "skill-sentry",          # planned sibling tool named in repo scope docs
})

# ---------------------------------------------------------------------------
# S8: risky install prompt patterns (curl/wget piped into a shell).
# Matched per line of SKILL.md / references/*.md.
# ---------------------------------------------------------------------------

RISK_PIPE_PATTERNS = (
    r"curl\s+[^|\n]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b",
    r"curl\s+[^|\n]*\|\s*bash\b",
    r"wget\s+[^|\n]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b",
    r"wget\s+[^|\n]*\|\s*bash\b",
    r"curl\s+[^|\n]*\|\s*python(?:3)?\b",
)

# ---------------------------------------------------------------------------
# S9: package-manager install prompt patterns and the official registry
# allowlist. The allowlist is the well-known default registry hosts;
# default_convention: true (a drafting default, not a verified inventory).
# ---------------------------------------------------------------------------

INSTALL_PROMPT_RE = r"(?:pip\d?|pipx|npm|yarn|pnpm)\s+(?:install|add|i)\b[^#\n]*"

REGISTRY_ALLOWLIST = frozenset({
    "pypi.org",
    "files.pythonhosted.org",
    "registry.npmjs.org",
    "npmjs.com",
    "www.npmjs.com",
    "yarnpkg.com",
    "registry.yarnpkg.com",
})

# Markers that the install line pins a non-default registry/source.
REGISTRY_FLAG_RES = (
    r"--index-url\s*(?:https?://)?([A-Za-z0-9.\-]+)",
    r"-i\s+(?:https?://)?([A-Za-z0-9.\-]+)",
    r"--extra-index-url\s*(?:https?://)?([A-Za-z0-9.\-]+)",
    r"--registry\s*(?:https?://)?([A-Za-z0-9.\-]+)",
    r"@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})/",   # npm @host/name style (non-scope)
)

# ---------------------------------------------------------------------------
# S6/S7: endpoint shapes. S7 requires an IP with an explicit scheme or port
# so that version numbers like 1.2.3.4 in prose are not misreported. Each
# octet is range-validated (0-255) so that 999.x.y.z style text does not
# match (matches the protection documented in references/rules.md).
# ---------------------------------------------------------------------------

_IP_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
_IP_ADDR = _IP_OCTET + r"(?:\." + _IP_OCTET + r"){3}"

IP_ENDPOINT_RE = (
    r"(?:https?://" + _IP_ADDR + r"\b"
    r"|\b" + _IP_ADDR + r":\d{2,5}\b)"
)

URL_RE = r"https?://[^\s\"'<>\\)\]]+"

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "[::1]"})

# ---------------------------------------------------------------------------
# Severity and SARIF level mapping (A7).
# ---------------------------------------------------------------------------

RULE_SEVERITY = {
    "S1": "medium",
    "S2": "medium",
    "S3": "low",
    "S4": "low",
    "S5": "medium",
    "S6": "medium",
    "S7": "medium",
    "S8": "high",
    "S9": "medium",
    "S10": "medium",
}

SARIF_LEVEL_MAP = {
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}

# Rule short names, keyed by rule id (used in messages and rule metadata).
RULE_NAMES = {
    "S1": "stale-repo",
    "S2": "single-maintainer",
    "S3": "no-recent-release",
    "S4": "high-open-ratio",
    "S5": "archived-or-fork",
    "S6": "plaintext-endpoint",
    "S7": "raw-ip-endpoint",
    "S8": "risky-install-pattern",
    "S9": "package-manager-prompt",
    "S10": "name-impersonation",
}
