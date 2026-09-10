# -*- coding: utf-8 -*-
"""sarif.py - SARIF 2.1.0 rendering for skill-supply-chain-audit.

Mapping per design A7 and the SARIF 2.1.0 OASIS Standard (verified 2026-09-11,
see references/data-provenance.md):
- finding -> result: ruleId, level, message.text,
  locations[].physicalLocation{artifactLocation.uri, region.startLine};
- level: high->error, medium->warning, low/info->note;
- inventory is intentionally NOT carried into SARIF (findings only);
- exit codes are unaffected by the output format.

Dependency direction: sarif -> (nothing from this skill).
"""

import json

from chain_rules import RULE_NAMES, SARIF_LEVEL_MAP

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA_URI = ("https://docs.oasis-open.org/sarif/sarif/v2.1.0/"
                    "cos02/schemas/sarif-schema-2.1.0.json")


def _uri_for(file, base_dir=""):
    """Artifact URI: forward slashes, relative to base_dir when possible."""
    uri = file.replace("\\", "/")
    base = base_dir.replace("\\", "/")
    if base and uri.lower().startswith(base.lower().rstrip("/") + "/"):
        uri = uri[len(base.rstrip("/")) + 1:]
    return uri


def render_sarif(findings, tool_name="skill-supply-chain-audit",
                 base_dir=""):
    rules_seen = []
    for f in findings:
        if f.rule not in rules_seen:
            rules_seen.append(f.rule)
    rules = [
        {
            "id": rid,
            "name": RULE_NAMES.get(rid, rid),
            "shortDescription": {
                "text": RULE_NAMES.get(rid, rid)},
        }
        for rid in rules_seen
    ]
    results = []
    for f in findings:
        results.append({
            "ruleId": f.rule,
            "level": SARIF_LEVEL_MAP.get(f.severity, "note"),
            "message": {"text": f.signal},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": _uri_for(f.file,
                                                             base_dir)},
                        "region": {"startLine": max(1, int(f.line))},
                    }
                }
            ],
        })
    return {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "informationUri": (
                            "https://github.com/whaojie797-design/novera-skills"),
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def render_sarif_str(findings, tool_name="skill-supply-chain-audit",
                     base_dir=""):
    return json.dumps(
        render_sarif(findings, tool_name, base_dir),
        indent=2, sort_keys=True, ensure_ascii=False)
