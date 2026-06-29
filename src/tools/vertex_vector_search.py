"""Vertex AI 埋め込み + Firestore による過去類似主張照合.

v0.3 (2026-06-22) 実装：
- Vertex AI text-embedding-005 でテキスト→768次元ベクトル化
- Firestore コレクション `deepfact_articles` に保存
- cosine similarity による線形検索（コレクション全件読み・Phase 3 で Vertex AI Vector Search index に移行）

「素のGeminiで代替不可」5基準のうち
  ① 状態継続（発信源の過去発言/類似主張蓄積）
  ⑤ 業務自動化（記事ごとに自動蓄積）
を実装する。
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Iterable

logger = logging.getLogger(__name__)

# Firestore コレクション名（将来 config 化推奨）
ARTICLE_COLLECTION = "deepfact_articles"
EMBEDDING_MODEL = "text-embedding-005"
EMBEDDING_MAX_INPUT_CHARS = 3000

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


# ============================================================
# 信頼ソース照合（Phase 1 からの継続実装）
# ============================================================


@dataclass
class TrustedSourceHit:
    domain: str
    label: str
    credibility: float
    category: str
    similarity: float


def lookup_trusted_source(domain: str) -> TrustedSourceHit | None:
    """ドメイン → 信頼ソース照合（investigator_agent.TRUSTED_DOMAINS 共有）."""
    from src.agents.investigator_agent import TRUSTED_DOMAINS

    if not domain:
        return None
    if domain in TRUSTED_DOMAINS:
        name, score, cat = TRUSTED_DOMAINS[domain]
        return TrustedSourceHit(
            domain=domain, label=name, credibility=score, category=cat, similarity=1.0,
        )
    for root, (name, score, cat) in TRUSTED_DOMAINS.items():
        if domain.endswith("." + root) or domain.endswith(root):
            return TrustedSourceHit(
                domain=domain, label=name, credibility=score, category=cat, similarity=0.9,
            )
    return None


def warmup_trusted_sources_cache() -> int:
    """Cloud Run startup hook で呼ぶ・キャッシュwarmup."""
    from src.agents.investigator_agent import TRUSTED_DOMAINS

    n = len(TRUSTED_DOMAINS)
    logger.info("Trusted sources cache warmup: %d entries", n)
    return n


# ============================================================
# Embedding 生成（Vertex AI text-embedding-005）
# ============================================================


def _embed(text: str) -> list[float] | None:
    """Vertex AI で text → 768次元 embedding を生成."""
    if not text or not text.strip():
        return None
    try:
        from google import genai  # type: ignore
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
            return None

        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[text[:EMBEDDING_MAX_INPUT_CHARS]],
        )
        embs = getattr(result, "embeddings", None)
        if not embs:
            return None
        first = embs[0]
        values = getattr(first, "values", None)
        if values is None and isinstance(first, dict):
            values = first.get("values")
        return list(values) if values else None
    except Exception:
        logger.exception("Embedding failed (graceful)")
        return None


def _cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    """cosine similarity (両ベクトルは同次元前提)."""
    a_list = list(a)
    b_list = list(b)
    if not a_list or not b_list or len(a_list) != len(b_list):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a_list, b_list):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


# ============================================================
# 記事蓄積 + 類似主張検索（状態継続の実装）
# ============================================================


def save_article(
    url: str,
    title: str,
    summary: str,
    body_excerpt: str,
    source_domain: str = "",
    credibility_score: float = 0.0,
    credibility_label: str = "",
) -> bool:
    """記事を embedding 化して Firestore に蓄積．
    失敗時は False（ブロック禁止・analyze は通常通り返る）.
    """
    client = _get_firestore()
    if client is None:
        logger.debug("Firestore unavailable, skip save_article")
        return False
    try:
        compose = "\n".join(
            part for part in (title, summary, body_excerpt) if part
        )
        emb = _embed(compose)
        if emb is None:
            logger.debug("Embedding unavailable, skip save_article")
            return False
        from datetime import datetime, timezone

        client.collection(ARTICLE_COLLECTION).add({
            "url": url[:1500],
            "title": (title or "")[:500],
            "summary": (summary or "")[:1500],
            "source_domain": source_domain[:200],
            "credibility_score": float(credibility_score),
            "credibility_label": credibility_label[:20],
            "embedding": emb,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": len(emb),
        })
        logger.info("save_article OK domain=%s label=%s dim=%d", source_domain, credibility_label, len(emb))
        return True
    except Exception:
        logger.exception("save_article failed (graceful)")
        return False


def find_similar_articles(
    query_text: str,
    top_k: int = 3,
    min_similarity: float = 0.72,
) -> list[dict]:
    """過去蓄積記事から類似主張を検索（cosine similarity）.

    Phase 3 では Vertex AI Vector Search index に移行予定.
    現状はコレクション全件読み（O(N)・規模 < 10k 想定）.
    """
    if not query_text or not query_text.strip():
        return []

    client = _get_firestore()
    if client is None:
        return []

    query_emb = _embed(query_text)
    if query_emb is None:
        return []

    try:
        candidates: list[dict] = []
        for doc in client.collection(ARTICLE_COLLECTION).stream():
            data = doc.to_dict() or {}
            emb = data.get("embedding")
            if not emb:
                continue
            sim = _cosine_similarity(query_emb, emb)
            if sim < min_similarity:
                continue
            candidates.append({
                "url": data.get("url", ""),
                "title": data.get("title", ""),
                "summary": data.get("summary", ""),
                "source_domain": data.get("source_domain", ""),
                "credibility_score": data.get("credibility_score"),
                "credibility_label": data.get("credibility_label"),
                "analyzed_at": data.get("analyzed_at"),
                "similarity": round(sim, 4),
            })
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates[:top_k]
    except Exception:
        logger.exception("find_similar_articles failed (graceful)")
        return []


def count_articles() -> int:
    """蓄積記事数（運用メトリクス用）."""
    client = _get_firestore()
    if client is None:
        return 0
    try:
        return sum(1 for _ in client.collection(ARTICLE_COLLECTION).select([]).stream())
    except Exception:
        logger.exception("count_articles failed")
        return 0
