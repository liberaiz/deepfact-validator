"""Firestore 入力ハッシュキャッシュ — 同一入力完全一致保証.

目的:
  Vertex AI Gemini の serving 側非決定性により、temperature=0+seed=42+top_k=1 を
  指定しても実機で結果が揺れる現象を補完する。

設計:
  - 入力 (input_type + payload) を SHA256 でハッシュ化
  - Firestore コレクション `deepfact_response_cache` に保存
  - 同じ入力 → キャッシュヒット → 同じ結果即返却

注意:
  - fallback で返した結果はキャッシュしない（is_high_quality=False）
  - キャッシュ TTL は無期限（コンテストデモ事故ゼロ最優先・運用で TTL 追加可能）
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CACHE_COLLECTION = "deepfact_response_cache"

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


def _hash_input(input_type: str, payload: str) -> str:
    """入力タイプ + payload を SHA256 化したキー."""
    raw = f"{input_type}::{payload or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_response(input_type: str, payload: str) -> dict | None:
    """同一入力のキャッシュを取得．高品質キャッシュのみ返す."""
    client = _get_firestore()
    if client is None:
        return None
    key = _hash_input(input_type, payload)
    try:
        doc = client.collection(CACHE_COLLECTION).document(key).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        if not data.get("is_high_quality", False):
            return None
        response = data.get("response")
        if not response:
            return None
        logger.info("Response cache HIT key=%s...", key[:16])
        return response
    except Exception:
        logger.exception("Response cache get failed")
        return None


def save_cached_response(
    input_type: str,
    payload: str,
    response_dict: dict,
    is_high_quality: bool,
) -> bool:
    """analyze 結果をキャッシュ．fallback で返した結果は is_high_quality=False で保存（次回再計算）.
    """
    client = _get_firestore()
    if client is None:
        return False
    key = _hash_input(input_type, payload)
    try:
        client.collection(CACHE_COLLECTION).document(key).set({
            "input_type": input_type,
            "payload_excerpt": (payload or "")[:500],
            "payload_hash": key,
            "response": response_dict,
            "is_high_quality": bool(is_high_quality),
            "cached_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(
            "Response cache SAVE key=%s... quality=%s",
            key[:16], is_high_quality,
        )
        return True
    except Exception:
        logger.exception("Response cache save failed")
        return False
