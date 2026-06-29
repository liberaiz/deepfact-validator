"""信頼ソース Firestore Seed Script（DeepFact Validator Day 8-9）.

ローカル辞書 TRUSTED_DOMAINS を Firestore `deepfact_sources` に投入。
Phase 2 で Vertex Vector Search の embedding 用にも使う。

使い方:
    GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json \\
    GCP_PROJECT_ID=deepfact-validator \\
    python scripts/seed_trusted_sources.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, asdict

try:
    from google.cloud import firestore
except ImportError:
    print("google-cloud-firestore が未インストールです: pip install google-cloud-firestore")
    sys.exit(1)


# scripts/ から src/ を import するため path追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.agents.investigator_agent import TRUSTED_DOMAINS  # noqa: E402


@dataclass(frozen=True)
class TrustedSourceRecord:
    domain: str
    label: str
    credibility: float
    category: str


def seed(dry_run: bool = False) -> dict:
    records = [
        TrustedSourceRecord(domain=d, label=name, credibility=score, category=cat)
        for d, (name, score, cat) in TRUSTED_DOMAINS.items()
    ]

    by_category: dict[str, int] = {}
    for r in records:
        by_category[r.category] = by_category.get(r.category, 0) + 1

    if dry_run:
        return {"total": len(records), "by_category": by_category, "dry_run": True}

    pid = os.getenv("GCP_PROJECT_ID", "deepfact-validator")
    client = firestore.Client(project=pid)
    collection = client.collection("deepfact_sources")
    batch = client.batch()
    for r in records:
        doc_ref = collection.document(r.domain.replace(".", "_"))
        batch.set(doc_ref, asdict(r))
    batch.commit()

    return {"total": len(records), "by_category": by_category, "dry_run": False}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    print("=" * 60)
    print(" 信頼ソース Firestore Seed (DeepFact Validator)")
    print("=" * 60)
    result = seed(dry_run=dry)
    print(f"  Total sources: {result['total']}")
    print("  By category:")
    for cat, n in result["by_category"].items():
        print(f"    {cat}: {n}")
    if result.get("dry_run"):
        print("  (dry-run / Firestoreには書き込んでいません)")
    else:
        print("  ✅ Firestore に書き込み完了")
