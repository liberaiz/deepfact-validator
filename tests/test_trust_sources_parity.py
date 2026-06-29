"""Parity test — config/*.yaml must equal `_*_FALLBACK` dicts in the agents.

YAML is the source of truth; the in-source fallback exists so the agent does not
crash when the YAML is missing at startup. If somebody edits one without the
other, scoring drifts silently. This test fails loudly when that happens.

Run locally:  pytest tests/test_trust_sources_parity.py
Runs in CI as part of the standard pytest suite.
"""
from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[1]
TRUSTED_PATH = REPO_ROOT / "config" / "trusted-domains.yaml"
PROPAGANDA_PATH = REPO_ROOT / "config" / "propaganda-patterns.yaml"


def _yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_trusted_domains_yaml_matches_fallback_dict():
    from src.agents.investigator_agent import _TRUSTED_DOMAINS_FALLBACK

    data = _yaml(TRUSTED_PATH)
    yaml_dict = {
        row["domain"]: (row["name"], float(row["credibility"]), row["category"])
        for row in data["domains"]
    }

    # Domains: every fallback entry must exist in YAML and vice versa.
    missing_in_yaml = set(_TRUSTED_DOMAINS_FALLBACK) - set(yaml_dict)
    missing_in_fallback = set(yaml_dict) - set(_TRUSTED_DOMAINS_FALLBACK)
    assert not missing_in_yaml, f"In fallback but not in YAML: {sorted(missing_in_yaml)}"
    assert not missing_in_fallback, f"In YAML but not in fallback: {sorted(missing_in_fallback)}"

    # Values: name / credibility / category must match.
    for domain, fb_value in _TRUSTED_DOMAINS_FALLBACK.items():
        assert yaml_dict[domain] == fb_value, (
            f"Drift for {domain}: fallback={fb_value} yaml={yaml_dict[domain]}"
        )


def test_propaganda_yaml_matches_fallback_dicts():
    from src.agents.watcher_agent import (
        _PROPAGANDA_PATTERNS_FALLBACK,
        _PROPAGANDA_WEIGHTS_FALLBACK,
    )

    data = _yaml(PROPAGANDA_PATH)
    yaml_patterns = data["patterns"]
    yaml_weights = {k: float(v) for k, v in data["weights"].items()}

    # Categories must match exactly across all 4 sources.
    pattern_keys_fb = set(_PROPAGANDA_PATTERNS_FALLBACK)
    weight_keys_fb = set(_PROPAGANDA_WEIGHTS_FALLBACK)
    pattern_keys_yaml = set(yaml_patterns)
    weight_keys_yaml = set(yaml_weights)
    assert pattern_keys_fb == pattern_keys_yaml == weight_keys_fb == weight_keys_yaml, (
        f"Category drift: pat_fb={pattern_keys_fb} pat_yaml={pattern_keys_yaml} "
        f"w_fb={weight_keys_fb} w_yaml={weight_keys_yaml}"
    )

    for cat, fb_terms in _PROPAGANDA_PATTERNS_FALLBACK.items():
        assert list(yaml_patterns[cat]) == list(fb_terms), (
            f"Terms drift for {cat}: yaml={yaml_patterns[cat]} fallback={fb_terms}"
        )

    for cat, fb_w in _PROPAGANDA_WEIGHTS_FALLBACK.items():
        assert yaml_weights[cat] == fb_w, (
            f"Weight drift for {cat}: yaml={yaml_weights[cat]} fallback={fb_w}"
        )
