"""DeepFact Validator — 構造化ログ Observability 層（Cloud Logging / Monitoring 接続）.

メティス指摘「装飾でなく構造」への直接対応 (2026-06-29).

設計方針:
  - Python 標準 `logging` の `extra` 引数で JSON フィールドを渡す
    （google-cloud-logging が `jsonPayload` に自動展開する GCP 標準パターン）
  - ローカル実行時も stdout に JSON 1行で吐く（テスト可能）
  - Cloud Run 環境では std logger → Cloud Logging Agent 自動取り込み
  - イベント名（`event`）を必ず付与 → Logs Explorer で `jsonPayload.event=...` で絞り込める
  - 各イベントに `request_id` を伝搬 → 1リクエストの一連処理を時系列で追跡可能

【スコープ外】
  - `src/tools/observability.py` は警告履歴の Firestore 永続化 + Postmortem 生成担当（既存）.
    本ファイルは構造化 JSON ログ送出のみを担当し、責任分離する.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

# ============================================================
# 定数
# ============================================================

SERVICE_NAME = "deepfact-validator"
SERVICE_VERSION = "1.1.9"

# イベント名（Cloud Logging で `jsonPayload.event` フィルタに使う）
EVENT_ANALYZE_REQUEST = "analyze_request"
EVENT_WATCHER_RESULT = "watcher_result"
EVENT_INVESTIGATOR_RESULT = "investigator_result"
EVENT_VALIDATOR_RESULT = "validator_result"
EVENT_CACHE_HIT = "cache_hit"
EVENT_CACHE_MISS = "cache_miss"
EVENT_ERROR = "error"

# severity → Cloud Logging LogSeverity（GCP 標準）
SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_ERROR = "ERROR"


# ============================================================
# request_id コンテキスト伝搬
# ============================================================
# FastAPI 非同期環境でも 1 リクエストの一連処理を紐づけられるよう
# ContextVar で持ち回る.

_request_id_var: ContextVar[Optional[str]] = ContextVar("deepfact_request_id", default=None)


def new_request_id() -> str:
    """新規 request_id を生成し、ContextVar にセット."""
    rid = str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """ContextVar から取得（未設定なら "no-request-id"）."""
    return _request_id_var.get() or "no-request-id"


@contextmanager
def request_context(request_id: Optional[str] = None) -> Iterator[str]:
    """with 構文で request_id を一時的にセットする helper.

    例: with request_context() as rid: ...
    """
    rid = request_id or str(uuid.uuid4())
    token = _request_id_var.set(rid)
    try:
        yield rid
    finally:
        _request_id_var.reset(token)


# ============================================================
# JSON Formatter（GCP Cloud Logging 構造化ログ標準フォーマット）
# ============================================================


class GCPJsonFormatter(logging.Formatter):
    """Python logging.Record → Cloud Logging 構造化 JSON 1行.

    GCP 公式仕様:
      - `severity` (string)        : LogSeverity
      - `message` (string)         : ログ本文
      - `timestamp` (string ISO8601): 発生時刻
      - 任意の追加フィールドは `jsonPayload.<name>` として保存される
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            "severity": getattr(record, "severity", record.levelname),
            "message": record.getMessage(),
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
        }
        # event_payload に詰めた構造化フィールドを展開
        event_payload = getattr(record, "event_payload", None)
        if isinstance(event_payload, dict):
            for k, v in event_payload.items():
                payload[k] = v
        # 例外情報
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


# ============================================================
# Logger 初期化
# ============================================================

_logger: Optional[logging.Logger] = None
_initialized = False


def get_logger() -> logging.Logger:
    """共有 logger 取得（最初の呼び出しで JSON formatter を初期化）."""
    global _logger, _initialized
    if _logger is not None and _initialized:
        return _logger

    logger = logging.getLogger(SERVICE_NAME)
    log_level_name = os.environ.get("DEEPFACT_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level_name, logging.INFO))

    # 既存ハンドラを一掃して JSON formatter のみ装着
    # （main.py の logging.basicConfig と二重出力にならないよう propagate=False）
    for h in list(logger.handlers):
        logger.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(GCPJsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False

    _logger = logger
    _initialized = True
    return logger


# ============================================================
# 公開 API — log_event
# ============================================================


def log_event(
    event: str,
    *,
    severity: str = SEVERITY_INFO,
    message: Optional[str] = None,
    request_id: Optional[str] = None,
    **payload: Any,
) -> None:
    """構造化イベントを Cloud Logging に出力（JSON 1行）.

    Args:
      event:      イベント種別（EVENT_* 定数推奨）.
      severity:   "INFO" / "WARNING" / "ERROR".
      message:    任意の人間向けメッセージ. 省略時は event 名そのまま.
      request_id: 明示指定がなければ ContextVar から自動取得.
      **payload:  各イベント固有のフィールド.

    例:
      log_event(
        EVENT_WATCHER_RESULT,
        elapsed_ms=1234,
        original_publisher="朝日新聞",
        extraction_success=True,
      )
    """
    logger = get_logger()
    rid = request_id or get_request_id()
    sev = (severity or SEVERITY_INFO).upper()

    event_payload: dict[str, Any] = {
        "event": event,
        "request_id": rid,
        **payload,
    }

    level = {
        SEVERITY_INFO: logging.INFO,
        SEVERITY_WARNING: logging.WARNING,
        SEVERITY_ERROR: logging.ERROR,
    }.get(sev, logging.INFO)

    logger.log(
        level,
        message or event,
        extra={
            "event_payload": event_payload,
            "severity": sev,
        },
    )


def log_exception(
    event: str = EVENT_ERROR,
    *,
    message: Optional[str] = None,
    request_id: Optional[str] = None,
    **payload: Any,
) -> None:
    """例外を ERROR severity でスタックトレース付き記録.

    `except` ブロック内で呼ぶこと.
    """
    logger = get_logger()
    rid = request_id or get_request_id()
    event_payload: dict[str, Any] = {
        "event": event,
        "request_id": rid,
        **payload,
    }
    logger.error(
        message or event,
        exc_info=True,
        extra={
            "event_payload": event_payload,
            "severity": SEVERITY_ERROR,
        },
    )


# ============================================================
# 計測ヘルパー — Timer
# ============================================================


@dataclass
class Timer:
    """`with Timer() as t: ...` で経過 ms を計測."""
    elapsed_ms: int = 0
    _t0: float = 0.0

    def __enter__(self) -> "Timer":
        self._t0 = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed_ms = int((time.monotonic() - self._t0) * 1000)


# ============================================================
# Stdin/Stdout テスト用ヘルパー（ユニットテスト用に再公開）
# ============================================================


def _reset_for_test() -> None:
    """テスト時に formatter 状態をリセット."""
    global _logger, _initialized
    if _logger is not None:
        for h in list(_logger.handlers):
            _logger.removeHandler(h)
    _logger = None
    _initialized = False
