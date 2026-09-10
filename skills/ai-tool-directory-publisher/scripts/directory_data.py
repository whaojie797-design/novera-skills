# -*- coding: utf-8 -*-
"""directory_data.py - Per-directory requirement snapshots for
ai-tool-directory-publisher.

PURE DATA MODULE - no logic, no I/O, no network access.

Six AI tool directories are covered. The `verified` flag records whether the
snapshot for that directory was confirmed against the directory's own
official submission pages during implementation (fetch date in
SNAPSHOT_DATE); unverified snapshots are skipped by default and only run
with --include-unverified.

IMPORTANT: directory field requirements change over time. Every conclusion
derived from this snapshot carries an "official site is authoritative"
disclaimer (see references/data-provenance.md). Length limits and screenshot
specs are a compiled baseline; the official pages do not publish numeric
limits, so they must be re-checked before each submission.
"""

from dataclasses import dataclass, field


@dataclass
class FieldSpec:
    required: bool
    min_len: int = None          # min chars (or list items); None = no check
    max_len: int = None          # max chars (or list items); None = no check
    enum: list = None            # allowed values; None = free-form
    screenshot_spec: str = None  # human-readable spec for screenshot fields
    verified: bool = False       # site-level verification (see module docstring)


@dataclass
class DirectorySpec:
    slug: str
    name: str
    source_url: str
    snapshot_date: str
    verified: bool
    file_tokens: list = field(default_factory=list)  # filename match tokens
    fields: dict = field(default_factory=dict)       # field name -> FieldSpec


SNAPSHOT_DATE = "2026-09-10"

# Pricing enum is fixed by this skill's design (V3): the listing's pricing
# value must be one of these four canonical values.
PRICING_ENUM = ["free", "freemium", "paid", "subscription"]

# Compiled common category baseline (used as the category enum for the
# verified-directory snapshots; see data-provenance for verification status).
CATEGORY_ENUM = [
    "AI Writing", "Image Generation", "Video Generation", "Audio & Music",
    "Productivity", "Marketing", "Development", "Chatbot", "Design",
    "Business", "Data Analysis", "Search", "Education", "Other",
]

SCREENSHOT_SPEC = "PNG or JPG, landscape, minimum 1280x720"


def _baseline_fields():
    """Compiled baseline field requirements shared by the verified snapshots.

    The four verified directories' official pages confirm a paid, editorial-
    reviewed submission flow but do not publish numeric limits, so these
    numbers are a compiled baseline (see data-provenance.md)."""
    return {
        "name": FieldSpec(required=True, min_len=1, max_len=60),
        "tagline": FieldSpec(required=True, min_len=10, max_len=60),
        "description": FieldSpec(required=True, min_len=50, max_len=1000),
        "category": FieldSpec(required=True, enum=CATEGORY_ENUM),
        "pricing": FieldSpec(required=True, enum=PRICING_ENUM),
        "features": FieldSpec(required=False, min_len=0),
        "url": FieldSpec(required=True),
        "screenshot": FieldSpec(required=False,
                                screenshot_spec=SCREENSHOT_SPEC),
    }


# Unverified directories reuse the same baseline shape so that
# --include-unverified can exercise the same rules; their findings are
# labelled strength=unverified and carry the "not verified" caveat.
_UNVERIFIED_FIELDS = {
    "name": FieldSpec(required=True, min_len=1, max_len=60),
    "tagline": FieldSpec(required=True, min_len=10, max_len=60),
    "description": FieldSpec(required=True, min_len=50, max_len=1000),
    "category": FieldSpec(required=True, enum=CATEGORY_ENUM),
    "pricing": FieldSpec(required=True, enum=PRICING_ENUM),
    "features": FieldSpec(required=False, min_len=0),
    "url": FieldSpec(required=True),
    "screenshot": FieldSpec(required=False,
                            screenshot_spec=SCREENSHOT_SPEC),
}


DIRECTORIES = {
    "futurepedia": DirectorySpec(
        slug="futurepedia",
        name="Futurepedia",
        source_url="https://www.futurepedia.io/submit-tool",
        snapshot_date=SNAPSHOT_DATE,
        verified=True,
        file_tokens=["futurepedia"],
        fields=_baseline_fields(),
    ),
    "toolify": DirectorySpec(
        slug="toolify",
        name="Toolify",
        source_url="https://www.toolify.ai/submit",
        snapshot_date=SNAPSHOT_DATE,
        verified=True,
        file_tokens=["toolify"],
        fields=_baseline_fields(),
    ),
    "taaft": DirectorySpec(
        slug="taaft",
        name="There's An AI For That",
        source_url="https://theresanaiforthat.com/launch/",
        snapshot_date=SNAPSHOT_DATE,
        verified=True,
        file_tokens=["taaft", "theres-an-ai-for-that"],
        fields=_baseline_fields(),
    ),
    "topai-tools": DirectorySpec(
        slug="topai-tools",
        name="TopAI.tools",
        source_url="https://topai.tools/submit",
        snapshot_date=SNAPSHOT_DATE,
        verified=True,
        file_tokens=["topai-tools", "topai.tools"],
        fields=_baseline_fields(),
    ),
    "ai-tools-directory": DirectorySpec(
        slug="ai-tools-directory",
        name="AI Tools Directory",
        source_url="https://aitoolsdirectory.com/submit",
        snapshot_date=SNAPSHOT_DATE,
        verified=False,
        file_tokens=["ai-tools-directory", "aitoolsdirectory"],
        fields=dict(_UNVERIFIED_FIELDS),
    ),
    "aitools-fyi": DirectorySpec(
        slug="aitools-fyi",
        name="AITools.fyi",
        source_url="https://aitools.fyi/submit",
        snapshot_date=SNAPSHOT_DATE,
        verified=False,
        file_tokens=["aitools-fyi", "aitoolsfyi"],
        fields=dict(_UNVERIFIED_FIELDS),
    ),
}
