#!/usr/bin/env python3
"""test-yaml-load.py — Smoke test that the trust YAML files load through
the production code path (investigator_agent / watcher_agent at import time).

Prints:
    TRUSTED_DOMAINS: N entries (expected >= 125)
    PROPAGANDA_PATTERNS: M categories, K terms (expected M >= 5)

Exit codes:
    0  loads succeeded and the dicts are non-empty
    1  any dict is empty (means YAML didn't load and fallback wasn't usable
       in this environment — investigate before deploying)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from src.agents.investigator_agent import TRUSTED_DOMAINS
    from src.agents.watcher_agent import PROPAGANDA_PATTERNS, PROPAGANDA_WEIGHTS

    td_count = len(TRUSTED_DOMAINS)
    pp_cat_count = len(PROPAGANDA_PATTERNS)
    pp_term_count = sum(len(v) for v in PROPAGANDA_PATTERNS.values())
    pw_count = len(PROPAGANDA_WEIGHTS)

    print(f"TRUSTED_DOMAINS: {td_count} entries")
    print(f"PROPAGANDA_PATTERNS: {pp_cat_count} categories, {pp_term_count} terms")
    print(f"PROPAGANDA_WEIGHTS: {pw_count} entries")

    # Sample a few well-known domains
    samples = ["who.int", "mhlw.go.jp", "reuters.com", "kcna.kp"]
    print("\nSpot check:")
    for d in samples:
        if d in TRUSTED_DOMAINS:
            name, score, cat = TRUSTED_DOMAINS[d]
            print(f"  {d:24s} -> {name} / {score:.2f} / {cat}")
        else:
            print(f"  {d:24s} -> MISSING")

    if td_count == 0 or pp_cat_count == 0 or pw_count == 0:
        print("\nFAIL: one or more dicts are empty.", file=sys.stderr)
        return 1
    if td_count < 100:
        print(f"\nWARN: TRUSTED_DOMAINS only has {td_count} entries (expected >=100).", file=sys.stderr)
    print("\nOK: dicts loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
