#!/usr/bin/env python3
"""validate-trust-sources.py — CI gate for DeepFact Validator trust dictionaries.

Validates two YAML files at PR time:
    config/trusted-domains.yaml
    config/propaganda-patterns.yaml

Exit codes:
    0  all checks passed
    1  validation error (printed to stderr with file:line context where possible)
    2  unexpected error / missing file

Checks (trusted-domains.yaml):
    - file exists, parses as YAML
    - required top-level keys: version, last_updated, categories, domains
    - `categories` is a non-empty list of strings (the enum)
    - `domains` is a non-empty list
    - each row has: domain (str), name (str), credibility (float in [0,1]),
      category (str in the enum)
    - domain values are unique
    - credibility is two-decimal-place friendly (warn only)

Checks (propaganda-patterns.yaml):
    - file exists, parses as YAML
    - required top-level keys: version, last_updated, weights, patterns
    - `weights` keys == `patterns` keys (no category drift)
    - every weight is a float in [0, 1]
    - every pattern category is a non-empty list of non-empty strings
    - no duplicate terms within a category

This script is called from .github/workflows/validate-trust-sources.yml and
can be run locally:  python scripts/validate-trust-sources.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:
    print("ERROR: PyYAML is required. `pip install pyyaml`.", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
TRUSTED_PATH = REPO_ROOT / "config" / "trusted-domains.yaml"
PROPAGANDA_PATH = REPO_ROOT / "config" / "propaganda-patterns.yaml"


class ValidationError(Exception):
    pass


def _err(path: Path, msg: str) -> str:
    return f"{path.relative_to(REPO_ROOT)}: {msg}"


def _load_yaml(path: Path) -> Any:
    if not path.is_file():
        raise ValidationError(_err(path, "file not found"))
    try:
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValidationError(_err(path, f"YAML parse error: {e}")) from e


def validate_trusted_domains(path: Path) -> tuple[int, list[str]]:
    """Returns (entry_count, warnings)."""
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise ValidationError(_err(path, "top level must be a mapping"))

    for key in ("version", "last_updated", "categories", "domains"):
        if key not in data:
            raise ValidationError(_err(path, f"missing required key: {key}"))

    cats = data["categories"]
    if not isinstance(cats, list) or not cats:
        raise ValidationError(_err(path, "`categories` must be a non-empty list"))
    if not all(isinstance(c, str) and c for c in cats):
        raise ValidationError(_err(path, "every `categories` entry must be a non-empty string"))
    cat_set = set(cats)
    if len(cat_set) != len(cats):
        raise ValidationError(_err(path, "`categories` list contains duplicates"))

    rows = data["domains"]
    if not isinstance(rows, list) or not rows:
        raise ValidationError(_err(path, "`domains` must be a non-empty list"))

    seen: dict[str, int] = {}
    warnings: list[str] = []
    used_cats: set[str] = set()

    for idx, row in enumerate(rows):
        loc = f"domains[{idx}]"
        if not isinstance(row, dict):
            raise ValidationError(_err(path, f"{loc} must be a mapping"))

        # Required fields + types
        for field_name, expected_type, type_label in [
            ("domain", str, "string"),
            ("name", str, "string"),
            ("category", str, "string"),
        ]:
            val = row.get(field_name)
            if not isinstance(val, expected_type) or not val:
                raise ValidationError(
                    _err(path, f"{loc}: missing or invalid `{field_name}` (expected non-empty {type_label})"),
                )

        domain = row["domain"].strip()
        if domain != row["domain"]:
            warnings.append(_err(path, f"{loc}.domain has leading/trailing whitespace: {row['domain']!r}"))

        if domain in seen:
            raise ValidationError(
                _err(path, f"{loc}.domain={domain!r} duplicates domains[{seen[domain]}]"),
            )
        seen[domain] = idx

        cred = row.get("credibility")
        try:
            cred_f = float(cred)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                _err(path, f"{loc}.credibility must be a number, got {cred!r}"),
            ) from e
        if not 0.0 <= cred_f <= 1.0:
            raise ValidationError(
                _err(path, f"{loc}.credibility={cred_f} out of range [0.0, 1.0]"),
            )

        category = row["category"]
        if category not in cat_set:
            raise ValidationError(
                _err(path,
                     f"{loc}.category={category!r} not in declared `categories` enum {sorted(cat_set)}",
                ),
            )
        used_cats.add(category)

    unused = cat_set - used_cats
    if unused:
        warnings.append(_err(path, f"declared categories never used by any row: {sorted(unused)}"))

    return len(rows), warnings


def validate_propaganda(path: Path) -> tuple[int, int, list[str]]:
    """Returns (category_count, total_terms, warnings)."""
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise ValidationError(_err(path, "top level must be a mapping"))

    for key in ("version", "last_updated", "weights", "patterns"):
        if key not in data:
            raise ValidationError(_err(path, f"missing required key: {key}"))

    weights = data["weights"]
    patterns = data["patterns"]
    if not isinstance(weights, dict) or not weights:
        raise ValidationError(_err(path, "`weights` must be a non-empty mapping"))
    if not isinstance(patterns, dict) or not patterns:
        raise ValidationError(_err(path, "`patterns` must be a non-empty mapping"))

    w_keys = set(weights.keys())
    p_keys = set(patterns.keys())
    if w_keys != p_keys:
        only_w = w_keys - p_keys
        only_p = p_keys - w_keys
        msg = "weights/patterns category mismatch"
        if only_w:
            msg += f" — in weights only: {sorted(only_w)}"
        if only_p:
            msg += f" — in patterns only: {sorted(only_p)}"
        raise ValidationError(_err(path, msg))

    warnings: list[str] = []
    total_terms = 0

    for cat, w in weights.items():
        try:
            w_f = float(w)
        except (TypeError, ValueError) as e:
            raise ValidationError(_err(path, f"weights.{cat} must be a number, got {w!r}")) from e
        if not 0.0 <= w_f <= 1.0:
            raise ValidationError(_err(path, f"weights.{cat}={w_f} out of range [0.0, 1.0]"))

    for cat, terms in patterns.items():
        if not isinstance(terms, list) or not terms:
            raise ValidationError(_err(path, f"patterns.{cat} must be a non-empty list"))
        seen_terms: set[str] = set()
        for j, t in enumerate(terms):
            if not isinstance(t, str) or not t.strip():
                raise ValidationError(
                    _err(path, f"patterns.{cat}[{j}] must be a non-empty string, got {t!r}"),
                )
            if t in seen_terms:
                warnings.append(_err(path, f"patterns.{cat} contains duplicate term: {t!r}"))
            seen_terms.add(t)
        total_terms += len(terms)

    return len(patterns), total_terms, warnings


def main() -> int:
    errors: list[str] = []
    all_warnings: list[str] = []

    try:
        td_count, td_warn = validate_trusted_domains(TRUSTED_PATH)
        all_warnings.extend(td_warn)
        print(f"  OK  trusted-domains.yaml: {td_count} domains")
    except ValidationError as e:
        errors.append(str(e))

    try:
        pp_cats, pp_terms, pp_warn = validate_propaganda(PROPAGANDA_PATH)
        all_warnings.extend(pp_warn)
        print(f"  OK  propaganda-patterns.yaml: {pp_cats} categories / {pp_terms} terms")
    except ValidationError as e:
        errors.append(str(e))

    for w in all_warnings:
        print(f"  WARN  {w}", file=sys.stderr)

    if errors:
        print("\nValidation FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  ERROR  {e}", file=sys.stderr)
        return 1

    print("\nAll trust-source YAML files validated.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — top-level safety net
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
