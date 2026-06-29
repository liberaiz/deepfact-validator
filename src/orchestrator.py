"""DeepFact Validator Orchestrator — Watcher → Investigator → Validator のパイプライン.

Gemini API でマルチエージェント実装（2026-06-19 v0.2 本実装）.
2026-06-29: 各エージェント呼び出し前後に observability の計測ポイントを追加.
2026-06-29 v1.1.5: メティス V29 致命#2 対策 — Watcher fallback で早期リターン.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from src.agents.investigator_agent import run_investigator
from src.agents.validator_agent import ValidatorResult, run_validator
from src.agents.watcher_agent import run_watcher
from src.observability import (
    EVENT_INVESTIGATOR_RESULT,
    EVENT_WATCHER_RESULT,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    log_event,
)

logger = logging.getLogger(__name__)


# 🆕 v1.1.5 思考停止スコア対策：fallback 時にユーザーへ返すエラーメッセージ
FALLBACK_USER_MESSAGE = (
    "現在分析エンジンが混み合っています。"
    "時間をおいて再試行してください。"
)


class AnalysisUnavailableError(Exception):
    """Watcher / Investigator / Validator が fallback 状態のとき raise.

    main.py 側で HTTP 503 + FALLBACK_USER_MESSAGE に変換される.
    LINE Bot 経路では同メッセージを Push 送信する.
    """

    def __init__(
        self,
        message: str = FALLBACK_USER_MESSAGE,
        *,
        error_state: str | None = None,
        stage: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.user_message = message
        self.error_state = error_state
        self.stage = stage  # "watcher" / "investigator" / "validator"


@dataclass
class AnalyzeInput:
    input_type: str  # "url" / "text" / "dom"
    payload: str
    user_context: dict | None = None


async def run_analyze_pipeline(req: AnalyzeInput) -> ValidatorResult:
    """3エージェント・パイプライン実行.

    🆕 v1.1.5 メティス V29 致命#2「思考停止スコア」対策:
        Watcher が fallback 状態 (Gemini 429/5xx 等で空主張) の場合、
        Investigator / Validator を呼ばずに AnalysisUnavailableError を raise する。
        これによって「どの入力でも 50% が返る思考停止状態」を構造的に防ぐ。
    """
    t0 = time.monotonic()

    # Watcher: 入力から本文/主張/感情強度を抽出
    watcher_result = await run_watcher(req.input_type, req.payload)
    t_watcher = time.monotonic() - t0

    # 🆕 構造化ログ: Watcher 結果 (元配信元抽出の成否を unknown_rate メトリクスへ)
    original_publisher = getattr(watcher_result, "original_publisher", "") or ""
    is_relay = getattr(watcher_result, "is_relay_platform", False)
    publisher_hint = getattr(watcher_result, "publisher_hint", "") or ""
    # 抽出成功判定: relay platform 経由なら original_publisher 必須 / 通常は publisher_hint
    if is_relay:
        extraction_success = bool(original_publisher)
        extraction_method = "relay_html_or_dict" if extraction_success else "none"
    else:
        extraction_success = bool(publisher_hint or original_publisher)
        extraction_method = "direct" if extraction_success else "none"
    log_event(
        EVENT_WATCHER_RESULT,
        severity=SEVERITY_INFO if extraction_success else SEVERITY_WARNING,
        extraction_success=extraction_success,
        extraction_method=extraction_method,
        original_publisher=original_publisher,
        publisher_hint=publisher_hint,
        is_relay_platform=is_relay,
        relay_platform_name=getattr(watcher_result, "relay_platform_name", "") or "",
        source_domain=getattr(watcher_result, "source_domain", "") or "",
        elapsed_ms=int(t_watcher * 1000),
        input_type=req.input_type,
        is_fallback=getattr(watcher_result, "is_fallback", False),
        error_state=getattr(watcher_result, "error_state", None) or "",
    )

    # 🆕 v1.1.5 早期リターンゲート:
    # Watcher が Gemini 失敗で fallback したときは、後段の Investigator/Validator を
    # 呼ばずに即エラーで返す。Gemini 失敗が「中 50%」固定値として返る事故を防ぐ。
    # ただし empty_body (URL 取得失敗 / 入力空) は別エラー（503 でなく Watcher は
    # ヒューリスティックで動かしたいケースもあるため、ここでも 503 として落とす方が
    # ユーザー体験的に正直）。
    if getattr(watcher_result, "is_fallback", False):
        err_state = getattr(watcher_result, "error_state", None) or "unknown"
        logger.warning(
            "Pipeline early-return: Watcher fallback detected error_state=%s — return 503",
            err_state,
        )
        raise AnalysisUnavailableError(
            FALLBACK_USER_MESSAGE,
            error_state=err_state,
            stage="watcher",
        )

    # Investigator: 発信元信頼度 + Gemini で論調バイアス・事実整合性分析
    investigator_result = await run_investigator(watcher_result)
    t_invest = time.monotonic() - t0

    # 🆕 構造化ログ: Investigator 結果
    log_event(
        EVENT_INVESTIGATOR_RESULT,
        severity=(
            SEVERITY_WARNING
            if getattr(investigator_result, "is_fallback", False)
            else SEVERITY_INFO
        ),
        source_credibility=getattr(investigator_result, "source_credibility_score", 0.0),
        position_bias=getattr(investigator_result, "position_bias_score", 0.0),
        fact_consistency=getattr(investigator_result, "fact_consistency_score", 0.0),
        source_label=getattr(investigator_result, "source_label", "") or "",
        elapsed_ms=int((t_invest - t_watcher) * 1000),
        is_fallback=getattr(investigator_result, "is_fallback", False),
        error_state=getattr(investigator_result, "error_state", None) or "",
    )

    # 🆕 v1.1.5 早期リターンゲート（2 段目）:
    # Investigator が Gemini で fallback したときも 503 で返す。
    # （source_credibility は domain ベースで取れているが、bias/fact は heuristic 推定値
    #   になっており、これを最終スコアに混ぜると「思考停止 50%」相当が再発しうるため。）
    if getattr(investigator_result, "is_fallback", False):
        err_state = getattr(investigator_result, "error_state", None) or "unknown"
        logger.warning(
            "Pipeline early-return: Investigator fallback detected error_state=%s — return 503",
            err_state,
        )
        raise AnalysisUnavailableError(
            FALLBACK_USER_MESSAGE,
            error_state=err_state,
            stage="investigator",
        )

    # Validator: 統合・スコア算出・自然言語レポート生成
    validator_result = await run_validator(watcher_result, investigator_result)
    t_total = time.monotonic() - t0

    logger.info(
        "Pipeline watcher=%.2fs investigator=%.2fs validator=%.2fs total=%.2fs "
        "score=%.2f label=%s source=%.2f neut=%.2f fact=%.2f",
        t_watcher,
        t_invest - t_watcher,
        t_total - t_invest,
        t_total,
        validator_result.credibility.overall_score,
        validator_result.credibility.overall_label,
        validator_result.credibility.source_credibility,
        validator_result.credibility.position_bias,
        validator_result.credibility.fact_consistency,
    )

    return validator_result
