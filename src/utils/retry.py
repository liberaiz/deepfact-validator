"""指数バックオフリトライ ヘルパー (v1.1.5).

メティスV29致命#2「思考停止スコア」対策の一部。Vertex AI Gemini が 429/5xx を
返したときに 1s→2s→4s の指数バックオフで最大3回までリトライする。

検出方法:
    - google.genai 1.x の例外型 (google.api_core.exceptions / google.genai.errors)
    - 例外メッセージ中の "429"/"503"/"504"/"resource_exhausted"/"unavailable" 等
      文字列マッチ (SDK 内部例外型の変動対策)

設計:
    - 既存の `asyncio.wait_for(client.aio.models.generate_content(...), timeout=...)`
      の外側に 1 ラッパとして被せる
    - timeout は呼び出し側責任 (本ヘルパーは個別 call の timeout は触らない)
    - リトライ不能例外 (JSON parse error 等) はそのまま raise → 既存 fallback
      ロジックに任せる
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# リトライ対象とみなす HTTP ステータスコード (Vertex AI 429/5xx)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


# リトライ対象とみなす例外メッセージ部分文字列 (SDK の例外型ゆれ吸収)
_RETRYABLE_MESSAGE_TOKENS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "resource_exhausted",
    "resource exhausted",
    "unavailable",
    "deadline_exceeded",
    "deadline exceeded",
    "rate limit",
    "ratelimit",
    "too many requests",
    "internal server error",
    "bad gateway",
    "gateway timeout",
    "quota",
)


def is_retryable_error(exc: BaseException) -> bool:
    """例外が「指数バックオフでリトライする価値がある」種類か判定する.

    検出ロジック (どれか1つに当てはまればリトライ):
        1. `code` / `status_code` / `status` 属性が _RETRYABLE_STATUS_CODES に入る
        2. メッセージ文字列に _RETRYABLE_MESSAGE_TOKENS のどれかを含む
        3. 例外クラス名に "ResourceExhausted" / "ServiceUnavailable" /
           "DeadlineExceeded" / "InternalServerError" を含む
    """
    # 1. 数値 status code
    for attr in ("code", "status_code", "status"):
        val = getattr(exc, attr, None)
        if isinstance(val, int) and val in _RETRYABLE_STATUS_CODES:
            return True
        if isinstance(val, str):
            try:
                if int(val) in _RETRYABLE_STATUS_CODES:
                    return True
            except (TypeError, ValueError):
                pass

    # 2. メッセージ文字列マッチ
    msg = str(exc).lower()
    if any(token in msg for token in _RETRYABLE_MESSAGE_TOKENS):
        return True

    # 3. クラス名マッチ
    cls_name = type(exc).__name__.lower()
    for marker in (
        "resourceexhausted",
        "serviceunavailable",
        "deadlineexceeded",
        "internalservererror",
        "toomanyrequests",
    ):
        if marker in cls_name:
            return True

    return False


async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    jitter: bool = True,
) -> T:
    """非同期関数を指数バックオフでリトライ実行する.

    例:
        >>> async def call():
        ...     return await client.aio.models.generate_content(...)
        >>> result = await retry_with_backoff(call, max_retries=3, base_delay=1.0)

    挙動:
        - 1 回目失敗 → 1.0s 待機 → 2 回目
        - 2 回目失敗 → 2.0s 待機 → 3 回目
        - 3 回目失敗 → 4.0s 待機 → 4 回目 (= 最後の試行)
        - 4 回目も失敗 → 例外を呼び出し側に raise (既存 fallback に任せる)

        max_retries=3 は「初回 + 3回リトライ = 計4回試行」を意味する。
        (仕様書の「1秒→2秒→4秒の3回リトライ」と一致)

    Args:
        func: 引数なし async callable。各リトライで毎回呼び直す。
        max_retries: リトライ回数の上限 (初回は含まない)。デフォルト 3。
        base_delay: 初回バックオフ秒数。デフォルト 1.0 (= 1s, 2s, 4s)。
        jitter: True なら待機時間に ±20% のランダム揺らぎを加える
                (thundering herd 防止)。デフォルト True。

    Returns:
        func() の戻り値。

    Raises:
        Exception: 全リトライが失敗したときは最後の例外をそのまま re-raise。
                   リトライ不能と判定された例外は即 re-raise。
    """
    if max_retries < 0:
        raise ValueError(f"max_retries must be >= 0, got {max_retries}")

    last_exc: BaseException | None = None
    total_attempts = max_retries + 1  # 初回 + リトライ回数

    for attempt in range(total_attempts):
        try:
            return await func()
        except asyncio.CancelledError:
            # CancelledError は決してリトライしない (上位の cancel を尊重)
            raise
        except Exception as exc:
            last_exc = exc
            if not is_retryable_error(exc):
                logger.info(
                    "retry_with_backoff: non-retryable error type=%s msg=%s — re-raise",
                    type(exc).__name__,
                    str(exc)[:200],
                )
                raise

            # 最後の試行ならリトライせず raise
            if attempt >= max_retries:
                logger.warning(
                    "retry_with_backoff: exhausted attempts=%d type=%s msg=%s",
                    total_attempts,
                    type(exc).__name__,
                    str(exc)[:200],
                )
                raise

            # 指数バックオフ計算
            delay = base_delay * (2 ** attempt)
            if jitter:
                # ±20% のランダム揺らぎ
                delay *= 1.0 + random.uniform(-0.2, 0.2)
                delay = max(0.0, delay)

            logger.warning(
                "retry_with_backoff: attempt=%d/%d failed type=%s msg=%s — sleep=%.2fs",
                attempt + 1,
                total_attempts,
                type(exc).__name__,
                str(exc)[:200],
                delay,
            )
            await asyncio.sleep(delay)

    # ここには到達しないはず (最終 attempt で raise されるため)
    assert last_exc is not None
    raise last_exc
