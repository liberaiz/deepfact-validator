"""HITL フィードバック保存 + 最新入力履歴（C7 Critical・γ案）.

設計変更 2026-06-26 社長指示：「テキストの正誤を質問者に聞くのは矛盾」→ UX 評価+動線へ
- 「👍 役に立った」「😐 微妙」: UX feedback として記録
- 「🔄 再分析する」: 最新入力を強制リフレッシュで再解析

Schema:
- feedback/{user_id}/entries/{ts_doc_id}: verdict (useful/unclear), ts
- latest_inputs/{user_id}: text, ts （最新入力を保存・再分析用）
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from google.cloud import firestore

logger = logging.getLogger(__name__)

_client: Optional[firestore.Client] = None


def _get_client() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client()
    return _client


def save_feedback(user_id: str, verdict: str) -> bool:
    """LINE Bot からのユーザー UX feedback を Firestore に保存.

    verdict: useful / unclear（v0.4.12 γ案・「正誤」でなく「UX 評価」）
    Returns True on success, False on failure (silently logged).
    """
    if not user_id or not verdict:
        return False
    try:
        client = _get_client()
        now = datetime.now(timezone.utc)
        doc_id = now.strftime("%Y%m%dT%H%M%S%fZ")
        doc_ref = (
            client.collection("feedback")
            .document(user_id)
            .collection("entries")
            .document(doc_id)
        )
        doc_ref.set({
            "verdict": verdict,
            "ts": now.isoformat(),
        })
        logger.info("HITL feedback saved: user=%s verdict=%s", user_id[:8] + "...", verdict)
        return True
    except Exception:
        logger.exception("save_feedback failed")
        return False


def save_latest_input(user_id: str, text: str) -> bool:
    """ユーザーの最新入力を保存（再分析機能のため）."""
    if not user_id or not text:
        return False
    try:
        client = _get_client()
        client.collection("latest_inputs").document(user_id).set({
            "text": text[:4000],  # LINE message limit より少なく
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return True
    except Exception:
        logger.exception("save_latest_input failed")
        return False


def get_latest_input(user_id: str) -> Optional[str]:
    """ユーザーの最新入力を取得（再分析用）. 無ければ None."""
    if not user_id:
        return None
    try:
        client = _get_client()
        doc = client.collection("latest_inputs").document(user_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        return data.get("text")
    except Exception:
        logger.exception("get_latest_input failed")
        return None
