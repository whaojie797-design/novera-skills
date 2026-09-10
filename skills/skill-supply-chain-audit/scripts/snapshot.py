# -*- coding: utf-8 -*-
"""snapshot.py - offline snapshot parsing for skill-supply-chain-audit.

Parses user-provided gh api export JSON files (never fetches anything):
- top-level keys are located line-by-line so findings can point at the
  exact key line inside the JSON file (design A10);
- schema violations raise SnapshotError, which the CLI turns into exit 2;
- a missing fetched_at anchor degrades the time base to the local machine
  date, flagged "unverified" in reports (design A3) - not an input error;
- also parses git remote output text and applies minimal text extraction
  to marketplace HTML archives (lead ruling 3: no full HTML parsing).

Dependency direction: snapshot -> (nothing from this skill).
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime


class SnapshotError(Exception):
    """Raised for invalid JSON or schema violations -> CLI exit 2."""


@dataclass
class Snapshot:
    repo: dict
    commits: list
    contributors: list
    releases: object                 # list or None (input optional)
    fetched_at: object               # date or None
    fetched_at_verified: bool        # False when degraded to local date
    repo_file: str = ""
    commits_file: str = ""
    contributors_file: str = ""
    releases_file: str = ""
    key_lines: dict = field(default_factory=dict)  # file -> {key: line}


_TOP_KEY_RE = re.compile(r'^\s*"([A-Za-z0-9_.\-]+)"\s*:')


def _key_lines_of(text):
    """Map top-level JSON keys to their 1-based line numbers (A10)."""
    lines = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        m = _TOP_KEY_RE.match(raw)
        if m and m.group(1) not in lines:
            lines[m.group(1)] = lineno
    return lines


def _load_json_file(path, required_type, what):
    if not os.path.isfile(path):
        raise SnapshotError("%s file does not exist: %s" % (what, path))
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        raise SnapshotError("cannot read %s: %s" % (path, exc))
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise SnapshotError("%s is not valid JSON (%s): %s"
                            % (what, path, exc))
    if not isinstance(data, required_type):
        raise SnapshotError(
            "%s must be a JSON %s, got %s: %s"
            % (what, required_type.__name__, type(data).__name__, path))
    return data, text


def _parse_fetched_at(value):
    """Accept ISO dates/datetimes; return a date or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    txt = value.strip()
    try:
        return datetime.strptime(txt[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def load_gh_export(repo_path, commits_path, contributors_path,
                   releases_path=None):
    """Load the gh api export set and validate the minimal schema.

    Required: repo is an object; commits and contributors are arrays.
    Optional per design: releases file; fetched_at inside repo.json.
    """
    repo, repo_text = _load_json_file(repo_path, dict, "repo snapshot")
    commits, commits_text = _load_json_file(commits_path, list,
                                            "commits snapshot")
    contributors, contrib_text = _load_json_file(
        contributors_path, list, "contributors snapshot")

    releases = None
    releases_text = ""
    if releases_path:
        releases, releases_text = _load_json_file(releases_path, list,
                                                  "releases snapshot")

    for key in ("full_name", "created_at", "pushed_at", "archived", "fork"):
        if key not in repo:
            raise SnapshotError(
                "repo snapshot missing required key \"%s\": %s"
                % (key, repo_path))

    key_lines = {
        repo_path: _key_lines_of(repo_text),
        commits_path: _key_lines_of(commits_text),
        contributors_path: _key_lines_of(contrib_text),
    }
    if releases_path:
        key_lines[releases_path] = _key_lines_of(releases_text)

    fetched_at = None
    if "fetched_at" in repo:
        fetched_at = _parse_fetched_at(repo.get("fetched_at"))
    # fetched_at present but unparseable also degrades (report says why);
    # absent fetched_at is NOT an input error (design 5.2).
    return Snapshot(
        repo=repo, commits=commits, contributors=contributors,
        releases=releases, fetched_at=fetched_at,
        fetched_at_verified=fetched_at is not None,
        repo_file=repo_path, commits_file=commits_path,
        contributors_file=contributors_path, releases_file=releases_path,
        key_lines=key_lines,
    )


def anchor_date(snap, local_today):
    """Time anchor per A3: snapshot fetched_at first, else the local date.

    Returns (date, verified_bool). verified=False means reports must label
    the anchor "local machine date, unverified".
    """
    if snap.fetched_at is not None:
        return snap.fetched_at, True
    return local_today, False


# ---------------------------------------------------------------------------
# git remote output and marketplace HTML archive (minimal text extraction)
# ---------------------------------------------------------------------------

_REMOTE_URL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://\S+")


def parse_remote_text(text):
    """Extract remote URLs from `git remote -v` output or .git/config text."""
    urls = []
    for line in text.splitlines():
        for cand in _REMOTE_URL_RE.findall(line):
            cand = cand.strip("\"',;")
            if cand not in urls:
                urls.append(cand)
    return urls


_REPO_NAME_RE = re.compile(r"/([^/]+?)(?:\.git)?/?$")


def remote_repo_names(urls):
    """Best-effort repo names from remote URLs (used by chain S10)."""
    names = []
    for url in urls:
        if url.startswith("git@"):
            tail = url.split(":", 1)[-1]
        else:
            tail = re.sub(r"^[A-Za-z][A-Za-z0-9+.\-]*://[^/]+/", "", url)
        m = _REPO_NAME_RE.search(tail.rstrip("/"))
        if m:
            name = m.group(1)
            if name and name not in names:
                names.append(name)
    return names


def minimal_html_text(text):
    """Minimal text extraction from an HTML archive (lead ruling 3).

    Drops script/style blocks and tags, keeps line structure so that
    file:line findings stay meaningful. Not a full HTML parser.
    """
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", text)
    text = re.sub(r"(?i)<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<")
    text = text.replace("&gt;", ">").replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    lines = []
    for raw in text.splitlines():
        collapsed = re.sub(r"\s+", " ", raw).strip()
        lines.append(collapsed)
    return "\n".join(lines)
