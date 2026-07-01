"""Cloud Logging Observability — 警告履歴 + SRE 流 Postmortem 自動生成.

「情報のObservability」フレームの実装：
  - 警告履歴を Cloud Logging + Firestore に蓄積（標準logger経由で gcloud logging から検索可）
  - 直近 N 時間の接触履歴を SRE Postmortem 形式で振り返り生成（Vertex AI Gemini）

DevOps × AI Agent Hackathon 2026 のフレーム🅰：
  - Observability = ユーザーが見た情報履歴を SRE 的に蓄積・可視化・アラート
  - Postmortem = 誤情報接触の振り返り → 再発防止
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

WARNING_COLLECTION_DEFAULT = "deepfact_warnings"

try:
    from google.cloud import firestore as _firestore_module  # type: ignore
except ImportError:
    _firestore_module = None  # type: ignore

_firestore_client = None


def _get_firestore():
    global _firestore_client
    if _firestore_module is None:
        return None
    if _firestore_client is None:
        try:
            _firestore_client = _firestore_module.Client()
        except Exception:
            logger.exception("Firestore client init failed")
            return None
    return _firestore_client


def _warnings_collection_name() -> str:
    try:
        from src.config import get_settings
        return get_settings().firestore.collection_warnings
    except Exception:
        return WARNING_COLLECTION_DEFAULT


# ============================================================
# Warning Record（蓄積）
# ============================================================


@dataclass
class WarningRecord:
    """SREメタデータ付き警告記録."""
    timestamp: str
    user_id: str           # LINE userId / Chrome Extension installId / "anonymous"
    source_url: str
    source_domain: str
    credibility_score: float
    credibility_label: str
    structural_observations_count: int
    primary_sources_count: int
    severity: str          # "INFO" / "WARN" / "CRITICAL"


def severity_from_score(score: float) -> str:
    """信頼度スコアから severity（SRE流）."""
    if score >= 0.75:
        return "INFO"
    elif score >= 0.50:
        return "WARN"
    else:
        return "CRITICAL"


def record_warning(record: WarningRecord) -> None:
    """警告履歴を Firestore + Cloud Logging に記録."""
    # Cloud Logging（標準logger経由 / gcloud logging で検索可）
    logger.warning(
        "DEEPFACT_WARNING ts=%s user=%s domain=%s score=%.2f label=%s severity=%s",
        record.timestamp, record.user_id, record.source_domain,
        record.credibility_score, record.credibility_label, record.severity,
    )
    # Firestore（履歴蓄積・Postmortem に使う）
    client = _get_firestore()
    if client is None:
        return
    try:
        client.collection(_warnings_collection_name()).add(asdict(record))
    except Exception:
        logger.exception("Firestore warning record failed")


# ============================================================
# Postmortem 自動生成（v0.3 実装）
# ============================================================


def generate_postmortem(user_id: str, hours: int = 24) -> str:
    """過去 N 時間の警告履歴から SRE 流 Postmortem を生成.

    手順：
      1. Firestore から user_id × 直近N時間 で履歴抽出
      2. ラベル / severity / ドメインで集計
      3. Vertex AI Gemini で Lessons Learned + 推奨アクションを自然言語生成
      4. SRE Postmortem 形式に組立て返す
    """
    client = _get_firestore()
    if client is None:
        return _no_data_postmortem(user_id, hours, reason="Firestore unavailable")

    try:
        records = _fetch_recent_records(client, user_id, hours)
    except Exception:
        logger.exception("Postmortem: fetch failed")
        return _no_data_postmortem(user_id, hours, reason="fetch error")

    if not records:
        return _no_data_postmortem(user_id, hours, reason="no records")

    summary = _aggregate(records)
    narrative = _generate_narrative(
        hours=hours,
        total=summary["total"],
        label_counts=summary["label_counts"],
        top_domains=summary["top_domains"],
    )
    return _format_postmortem(
        user_id=user_id,
        hours=hours,
        total=summary["total"],
        label_counts=summary["label_counts"],
        severity_counts=summary["severity_counts"],
        top_domains=summary["top_domains"],
        timeline=summary["timeline"],
        narrative=narrative,
    )


def _fetch_recent_records(client, user_id: str, hours: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    col = client.collection(_warnings_collection_name())
    # user_id == anonymous の場合は全件（user_id 指定なし）
    if user_id and user_id != "anonymous":
        query = col.where("user_id", "==", user_id).where("timestamp", ">=", since)
    else:
        query = col.where("timestamp", ">=", since)
    return [doc.to_dict() or {} for doc in query.stream()]


def _aggregate(records: list[dict]) -> dict:
    total = len(records)
    label_counts: Counter = Counter()
    severity_counts: Counter = Counter()
    domain_counts: Counter = Counter()
    timeline: list[dict] = []
    for r in records:
        label = r.get("credibility_label", "")
        sev = r.get("severity", "")
        domain = r.get("source_domain") or "(unknown)"
        if label:
            label_counts[label] += 1
        if sev:
            severity_counts[sev] += 1
        domain_counts[domain] += 1
        timeline.append({
            "ts": r.get("timestamp", ""),
            "domain": domain,
            "label": label,
            "score": r.get("credibility_score", 0.0),
        })
    timeline.sort(key=lambda x: x["ts"], reverse=True)
    top_domains = domain_counts.most_common(5)
    return {
        "total": total,
        "label_counts": dict(label_counts),
        "severity_counts": dict(severity_counts),
        "top_domains": top_domains,
        "timeline": timeline[:5],
    }


def _generate_narrative(
    hours: int,
    total: int,
    label_counts: dict,
    top_domains: list,
) -> str:
    """Vertex AI Gemini で Lessons Learned + 推奨アクションを生成."""
    try:
        from google import genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore
        from src.config import get_settings

        s = get_settings()
        if s.gcp.use_vertex_ai:
            client = genai.Client(
                vertexai=True,
                project=s.gcp.vertex_project,
                location=s.gcp.vertex_location,
            )
        elif s.gcp.gemini_api_key:
            client = genai.Client(api_key=s.gcp.gemini_api_key)
        else:
            return _fallback_narrative()

        top_domains_str = "\n".join(
            f"- {d}: {c} 件" for d, c in top_domains
        ) or "- （データなし）"

        prompt = (
            "あなたは情報接触のSRE流Postmortem専門家です。"
            f"以下の直近{hours}時間の情報接触履歴を構造的に振り返ってください。\n\n"
            "【接触履歴サマリ】\n"
            f"- 接触記事数: {total}\n"
            f"- ラベル分布: 高 {label_counts.get('高', 0)} / 中 {label_counts.get('中', 0)} / 警告 {label_counts.get('警告', 0)}\n"
            f"- ドメイン Top 5:\n{top_domains_str}\n\n"
            "【生成形式】markdownで以下2セクションのみ生成：\n\n"
            "## Lessons Learned\n"
            "2-3個の構造的観察。「○○が多い構造」「○○に偏る傾向」形式。発信者(個人・組織)を断定的に指摘しない。\n\n"
            "## 推奨アクション\n"
            "次にどう情報接触するか 1-2個。一次情報重視・複数ソース照合を推奨。\n\n"
            "【重要】\n"
            "- markdownのみ返す。説明文を含めない。\n"
            "- 「発信者個人を断定せず・構造を可視化する」原則を守る。\n"
        )

        response = client.models.generate_content(
            model=s.gcp.gemini_model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.0,
                top_k=1,
                seed=42,
            ),
        )
        text = (response.text or "").strip()
        return text or _fallback_narrative()
    except Exception:
        logger.exception("postmortem narrative generation failed")
        return _fallback_narrative()


def _fallback_narrative() -> str:
    return (
        "## Lessons Learned\n"
        "- 自動振り返り生成は今回スキップされました（Vertex AI 接続不可または quota）。\n\n"
        "## 推奨アクション\n"
        "- 信頼度「中」「警告」と判定された記事は一次情報を確認してください。\n"
    )


def _no_data_postmortem(user_id: str, hours: int, reason: str = "") -> str:
    body = (
        f"# Postmortem: 直近{hours}時間の情報接触記録 (user={user_id})\n\n"
        f"直近{hours}時間の接触記録は見つかりませんでした。\n"
    )
    if reason:
        body += f"\n_理由: {reason}_\n"
    return body


def _format_postmortem(
    user_id: str,
    hours: int,
    total: int,
    label_counts: dict,
    severity_counts: dict,
    top_domains: list,
    timeline: list,
    narrative: str,
) -> str:
    parts = [
        f"# Postmortem: 直近{hours}時間の情報接触 (user={user_id})",
        "",
        "## サマリ",
        f"- 接触記事数: **{total}** 件",
        f"- ラベル分布: 高 {label_counts.get('高', 0)} / 中 {label_counts.get('中', 0)} / 警告 {label_counts.get('警告', 0)}",
        f"- severity 分布: INFO {severity_counts.get('INFO', 0)} / WARN {severity_counts.get('WARN', 0)} / CRITICAL {severity_counts.get('CRITICAL', 0)}",
        "",
        "## Timeline（最近 5 件）",
    ]
    if timeline:
        for entry in timeline:
            score_pct = int((entry.get("score", 0) or 0) * 100)
            ts = (entry.get("ts") or "")[:16]
            parts.append(
                f"- `{ts}` → {entry.get('domain', '(unknown)')} → "
                f"{entry.get('label', '?')} ({score_pct}%)"
            )
    else:
        parts.append("- （該当なし）")
    parts.extend([
        "",
        "## ドメイン Top 5",
    ])
    if top_domains:
        for domain, count in top_domains:
            parts.append(f"- {domain}: {count} 件")
    else:
        parts.append("- （該当なし）")
    parts.extend([
        "",
        narrative,
    ])
    return "\n".join(parts)
