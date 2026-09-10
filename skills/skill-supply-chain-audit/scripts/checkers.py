# -*- coding: utf-8 -*-
"""checkers.py - S1-S10 rule implementations.

Groups:
- profile (S1-S5): repository health from the gh api snapshot; every
  finding is "inferred" and must carry the snapshot value, the anchor
  date and the threshold with its "default convention" label (A3/A4).
- refs (S6-S7): reference surface; inventory is informational and separate
  from findings (design 2.2). S6/S7 are "explicit" (literal file facts).
- chain (S8-S10): distribution-chain risks; S8/S9 "explicit", S10 "inferred"
  with the similarity measure attached. curl|sh needs the double condition
  (pattern + negation/quote context) before a counter-example is suppressed.

Static analysis only: never executes anything, never touches the network.
Dependency direction: checkers -> chain_rules (never back).
"""

import ast
import os
import re
from datetime import date, datetime

from chain_rules import (
    INSTALL_PROMPT_RE,
    IP_ENDPOINT_RE,
    LOCAL_HOSTS,
    NEGATION_MARKERS,
    REGISTRY_ALLOWLIST,
    REGISTRY_FLAG_RES,
    RISK_PIPE_PATTERNS,
    RULE_NAMES,
    RULE_SEVERITY,
    THRESHOLDS,
    URL_RE,
    WELL_KNOWN_SKILLS,
)

_URL_RES = [re.compile(URL_RE)]
_IP_RES = re.compile(IP_ENDPOINT_RE)
_PIPE_RES = [re.compile(p) for p in RISK_PIPE_PATTERNS]
_PROMPT_RE = re.compile(INSTALL_PROMPT_RE)
_FLAG_RES = [re.compile(p) for p in REGISTRY_FLAG_RES]
_FM_NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.M)

SEVERITY = RULE_SEVERITY


def _basis(rule, threshold_note=None):
    ref = "references/rules.md"
    if threshold_note:
        return ("%s is a default convention (see %s), not a fact"
                % (threshold_note, ref))
    return "see %s" % ref


def _finding(file, line, rule, strength, signal, threshold_note=None):
    from report import Finding
    return Finding(file=file, line=line, rule=rule,
                   severity=SEVERITY[rule], strength=strength,
                   signal=signal, basis=_basis(rule, threshold_note))


def _iso_date(value):
    """Parse an ISO date/datetime string into a date; None if unusable."""
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _key_line(snap, file, key):
    return snap.key_lines.get(file, {}).get(key, 1)


def _repo_url_host(url):
    m = re.match(r"https?://([^/:?#]+)", url, re.I)
    return m.group(1).lower() if m else None


def name_similarity(a, b):
    """Plain Levenshtein edit distance (standard library DP)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------------------
# profile: S1-S5
# ---------------------------------------------------------------------------

def run_profile(snap, local_today):
    """Returns (findings, warnings). Warnings are input-quality notes and
    never count as findings."""
    findings = []
    warnings = []
    anchor, anchor_verified = _anchor(snap, local_today)
    if not anchor_verified:
        warnings.append(
            "snapshot has no usable fetched_at anchor; time base is the "
            "local machine date (%s), unverified" % anchor.isoformat())

    # --- S1 stale-repo -----------------------------------------------------
    last_push = None
    for c in snap.commits:
        if not isinstance(c, dict):
            continue
        commit = c.get("commit")
        if not isinstance(commit, dict):
            continue
        committer = commit.get("committer")
        author = commit.get("author")
        raw = None
        if isinstance(committer, dict):
            raw = committer.get("date")
        if raw is None and isinstance(author, dict):
            raw = author.get("date")
        d = _iso_date(raw)
        if d and (last_push is None or d > last_push):
            last_push = d
    if last_push is None:
        last_push = _iso_date(snap.repo.get("pushed_at"))
    if last_push is None:
        warnings.append("no commit date found in snapshot; S1 not decidable")
    else:
        days = (anchor - last_push).days
        if days < 0:
            warnings.append(
                "last push (%s) is newer than the anchor (%s); snapshot "
                "inconsistent, S1 not decidable"
                % (last_push.isoformat(), anchor.isoformat()))
        elif days > int(THRESHOLDS["stale_days"].value):
            findings.append(_finding(
                snap.repo_file,
                _key_line(snap, snap.repo_file, "pushed_at"),
                "S1", "inferred",
                "last push %s, anchor %s -> stale (%d days > %d%s)"
                % (last_push.isoformat(), anchor.isoformat(), days,
                   int(THRESHOLDS["stale_days"].value),
                   "d default convention"),
                threshold_note="stale threshold %dd"
                               % int(THRESHOLDS["stale_days"].value)))

    # --- S2 single-maintainer ----------------------------------------------
    uniq = _unique_contributors(snap.contributors)
    if not snap.contributors:
        created = _iso_date(snap.repo.get("created_at"))
        if snap.fetched_at and created and snap.fetched_at < created:
            warnings.append(
                "contributors array is empty and fetched_at precedes repo "
                "creation: export looks incomplete; S2 skipped (input "
                "warning, not a finding)")
        else:
            findings.append(_finding(
                snap.contributors_file, 1, "S2", "inferred",
                "contributors array is empty (%d unique maintainers < %d, "
                "minimum is a default convention)"
                % (len(uniq), int(THRESHOLDS["min_maintainers"].value)),
                threshold_note="minimum maintainers %d"
                               % int(THRESHOLDS["min_maintainers"].value)))
    elif len(uniq) < int(THRESHOLDS["min_maintainers"].value):
        findings.append(_finding(
            snap.contributors_file, 1, "S2", "inferred",
            "%d unique maintainer(s) in snapshot (below minimum %d, a "
            "default convention)" % (len(uniq),
                                     int(THRESHOLDS["min_maintainers"].value)),
            threshold_note="minimum maintainers %d"
                           % int(THRESHOLDS["min_maintainers"].value)))

    # --- S3 no-recent-release ----------------------------------------------
    if snap.releases is None:
        warnings.append("releases snapshot not provided; S3 not decidable")
    elif not snap.releases:
        findings.append(_finding(
            snap.releases_file or snap.repo_file,
            _key_line(snap, snap.releases_file or snap.repo_file,
                      "releases") if snap.releases_file else 1,
            "S3", "inferred",
            "no release ever published in snapshot",
            threshold_note="release window %dd"
                           % int(THRESHOLDS["release_window_days"].value)))
    else:
        latest = None
        for r in snap.releases:
            d = _iso_date(r.get("published_at")) if isinstance(r, dict) else None
            if d and (latest is None or d > latest):
                latest = d
        if latest is None:
            warnings.append("no parseable release published_at; S3 skipped")
        else:
            win = (anchor - latest).days
            if win < 0:
                warnings.append(
                    "latest release (%s) is newer than the anchor (%s); "
                    "snapshot inconsistent, S3 not decidable"
                    % (latest.isoformat(), anchor.isoformat()))
            elif win > int(THRESHOLDS["release_window_days"].value):
                findings.append(_finding(
                    snap.releases_file or snap.repo_file,
                    1 if not snap.releases_file else
                    _key_line(snap, snap.releases_file, "releases"),
                    "S3", "inferred",
                    "latest release %s, anchor %s -> no release within "
                    "window (%d days > %d default convention)"
                    % (latest.isoformat(), anchor.isoformat(), win,
                       int(THRESHOLDS["release_window_days"].value)),
                    threshold_note="release window %dd"
                                   % int(THRESHOLDS["release_window_days"].value)))

    # --- S4 high-open-ratio -------------------------------------------------
    opened = snap.repo.get("open_issues_count")
    closed = snap.repo.get("closed_issues_count")
    if not isinstance(opened, int) or not isinstance(closed, int):
        warnings.append(
            "open/closed issue counts not both present in snapshot; S4 not "
            "decidable offline (gh api repo export does not carry "
            "closed_issues_count by default)")
    else:
        total = opened + closed
        ratio = (float(opened) / total) if total > 0 else 0.0
        if ratio > THRESHOLDS["max_open_ratio"].value:
            findings.append(_finding(
                snap.repo_file,
                _key_line(snap, snap.repo_file, "open_issues_count"),
                "S4", "inferred",
                "open/closed issue ratio %.2f (%d open / %d closed) above "
                "%.2f default convention" % (ratio, opened, closed,
                                             THRESHOLDS["max_open_ratio"].value),
                threshold_note="max open ratio %.2f"
                               % THRESHOLDS["max_open_ratio"].value))

    # --- S5 archived-or-fork -------------------------------------------------
    if snap.repo.get("archived") is True:
        findings.append(_finding(
            snap.repo_file, _key_line(snap, snap.repo_file, "archived"),
            "S5", "inferred", "repository is archived (archived=true)"))
    if snap.repo.get("fork") is True:
        findings.append(_finding(
            snap.repo_file, _key_line(snap, snap.repo_file, "fork"),
            "S5", "inferred", "repository is a fork (fork=true)"))

    findings.sort(key=lambda f: (f.file, f.line, f.rule))
    return findings, warnings


def _anchor(snap, local_today):
    """A3: snapshot fetched_at anchor first; else the local machine date
    (flagged unverified by the caller via the boolean)."""
    if snap.fetched_at is not None:
        return snap.fetched_at, True
    return local_today, False


def _unique_contributors(contributors):
    seen = []
    for c in contributors:
        if not isinstance(c, dict):
            key = str(c)
        else:
            author = c.get("author") if isinstance(c.get("author"), dict) else c
            key = (author.get("login") or author.get("name")
                   or author.get("email") or author.get("id") or str(c))
        if key not in seen:
            seen.append(key)
    return seen


# ---------------------------------------------------------------------------
# refs: S6-S7 + inventory (inventory never affects the exit code)
# ---------------------------------------------------------------------------

def run_refs(skill_dir):
    findings = []
    inventory = []
    doc_files = _doc_files(skill_dir)
    for file, lineno, text in doc_files:
        for m in _URL_RES[0].finditer(text):
            url = m.group(0).rstrip(".,;")
            host = _repo_url_host(url)
            if url.lower().startswith("http://") and host not in LOCAL_HOSTS:
                findings.append(_finding(
                    file, lineno, "S6", "explicit",
                    'plaintext http:// endpoint "%s"' % url))
            inventory.append((file, lineno, url, "doc-url"))
    # scripts: string literals only (AST facts, never grep semantics)
    for file, tree, src_lines in _script_files(skill_dir):
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
                lineno = getattr(node, "lineno", 1) or 1
                for m in _URL_RES[0].finditer(text):
                    url = m.group(0).rstrip(".,;")
                    host = _repo_url_host(url)
                    if (url.lower().startswith("http://")
                            and host not in LOCAL_HOSTS):
                        findings.append(_finding(
                            file, lineno, "S6", "explicit",
                            'plaintext http:// endpoint in string literal '
                            '"%s"' % url))
                    inventory.append((file, lineno, url, "script-endpoint"))
                if _IP_RES.search(text):
                    findings.append(_finding(
                        file, lineno, "S7", "explicit",
                        'raw IP endpoint in string literal "%s"'
                        % _clip(text)))
    findings.sort(key=lambda f: (f.file, f.line, f.rule))
    from report import Inventory
    return findings, Inventory(items=inventory)


# ---------------------------------------------------------------------------
# chain: S8-S10
# ---------------------------------------------------------------------------

def run_chain(skill_dir, against_text=None):
    findings = []
    warnings = []
    doc_lines = _doc_files(skill_dir)

    # --- S8 risky-install-pattern -------------------------------------------
    findings.extend(_s8_findings(doc_lines))

    # --- S9 package-manager-prompt -------------------------------------------
    for file, lineno, text in doc_lines:
        if not _PROMPT_RE.search(text):
            continue
        hosts = []
        for rx in _FLAG_RES:
            for m in rx.finditer(text):
                host = m.group(1).lower()
                if host not in hosts:
                    hosts.append(host)
        for host in hosts:
            if host not in REGISTRY_ALLOWLIST:
                findings.append(_finding(
                    file, lineno, "S9", "explicit",
                    'install prompt targets non-official registry "%s" '
                    '(official registry allowlist is a default convention)'
                    % host,
                    threshold_note="registry allowlist"))

    # --- S10 name-impersonation ----------------------------------------------
    candidates = _candidate_names(skill_dir)
    if against_text:
        from snapshot import parse_remote_text, remote_repo_names
        for n in remote_repo_names(parse_remote_text(against_text)):
            if n not in candidates:
                candidates.append(n)
    # dedupe case-insensitively: frontmatter name and openai.yaml name are
    # usually the same string; one impersonation signal per distinct name
    uniq_candidates = []
    seen_lows = set()
    for n in candidates:
        low = n.lower()
        if low not in seen_lows:
            seen_lows.add(low)
            uniq_candidates.append(n)
    max_d = int(THRESHOLDS["impersonation_max_distance"].value)
    known = sorted(WELL_KNOWN_SKILLS)
    for cand in sorted(uniq_candidates):
        low = cand.lower()
        for w in known:
            if low == w:
                continue  # exact match = the well-known skill itself
            d = name_similarity(low, w)
            if d <= max_d:
                findings.append(_finding(
                    os.path.join(skill_dir, "SKILL.md").replace("\\", "/"),
                    1, "S10", "inferred",
                    'name "%s" vs well-known "%s" (edit distance %d <= %d '
                    'default convention)' % (cand, w, d, max_d),
                    threshold_note="impersonation distance %d" % max_d))
    findings.sort(key=lambda f: (f.file, f.line, f.rule))
    return findings, warnings


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _clip(text, limit=80):
    return text if len(text) <= limit else text[:limit - 1] + "..."


def _doc_files(skill_dir):
    files = [os.path.join(skill_dir, "SKILL.md")]
    refs_dir = os.path.join(skill_dir, "references")
    if os.path.isdir(refs_dir):
        for name in sorted(os.listdir(refs_dir)):
            if name.lower().endswith((".md", ".yaml", ".yml", ".txt")):
                files.append(os.path.join(refs_dir, name))
    yaml_path = os.path.join(skill_dir, "agents", "openai.yaml")
    if os.path.isfile(yaml_path):
        files.append(yaml_path)
    out = []
    for path in files:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            for lineno, line in enumerate(fh.read().splitlines(), start=1):
                out.append((path.replace("\\", "/"), lineno, line))
    return out


def _s8_findings(doc_lines):
    """S8 with the double condition: install pattern + negation/quote
    context. A hit line is suppressed only when the negation wording sits
    on the hit line itself, or (for a hit inside a fenced code block) on
    the non-empty text line immediately introducing that block. A plain
    install command in its own code block is NOT suppressed by an unrelated
    negation sentence elsewhere in the document."""
    findings = []
    by_file = {}
    order = []
    for file, lineno, text in doc_lines:
        if file not in by_file:
            by_file[file] = []
            order.append(file)
        by_file[file].append((lineno, text))
    for file in order:
        in_code = False
        intro = ""       # non-empty text line right before the open fence
        last_nonempty = ""
        for lineno, text in by_file[file]:
            stripped = text.lstrip()
            if stripped.startswith("```"):
                if not in_code:
                    intro = last_nonempty
                in_code = not in_code
                continue
            if not in_code and stripped:
                last_nonempty = stripped
            if not any(rx.search(text) for rx in _PIPE_RES):
                continue
            lowered = text.lower()
            neg_line = any(m in lowered for m in NEGATION_MARKERS)
            neg_intro = in_code and intro and any(
                m in intro.lower() for m in NEGATION_MARKERS)
            if neg_line or neg_intro:
                continue  # documented counter-example (double condition met)
            findings.append(_finding(
                file, lineno, "S8", "explicit",
                'install prompt "%s"' % _clip(text.strip())))
    return findings


def _script_files(skill_dir):
    scripts_dir = os.path.join(skill_dir, "scripts")
    out = []
    if not os.path.isdir(scripts_dir):
        return out
    for name in sorted(os.listdir(scripts_dir)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(scripts_dir, name)
        try:
            with open(path, "r", encoding="utf-8-sig",
                      errors="replace") as fh:
                src = fh.read()
            tree = ast.parse(src)
        except (OSError, SyntaxError, ValueError):
            continue  # parse failures are not this skill's findings
        out.append((path.replace("\\", "/"), tree, src.splitlines()))
    return out


def _candidate_names(skill_dir):
    names = []
    sk = os.path.join(skill_dir, "SKILL.md")
    if os.path.isfile(sk):
        with open(sk, "r", encoding="utf-8-sig", errors="replace") as fh:
            head = "\n".join(fh.read().splitlines()[:30])
        m = _FM_NAME_RE.search(head)
        if m:
            names.append(m.group(1).strip().strip("\"'"))
    yaml_path = os.path.join(skill_dir, "agents", "openai.yaml")
    if os.path.isfile(yaml_path):
        with open(yaml_path, "r", encoding="utf-8-sig",
                  errors="replace") as fh:
            for line in fh.read().splitlines():
                m = re.match(r"^name:\s*(.+?)\s*$", line)
                if m:
                    names.append(m.group(1).strip().strip("\"'"))
                    break
    base = os.path.basename(os.path.abspath(skill_dir))
    if base and base not in names:
        names.append(base)
    return [n for n in names if n]
