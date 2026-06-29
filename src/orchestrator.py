"""DeepFact Validator Orchestrator — Watcher → Investigator → Validator のパイプライン.

Gemini API でマルチエージェント実装（2026-06-19 v0.2 本実装）.
2026-06-29: 各エージェント呼び出し前後に observability の計測ポイントを追加.
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


@dataclass
class AnalyzeInput:
    input_type: str  # "url" / "text" / "dom"
    payload: str
    user_context: dict | None = None


async def run_analyze_pipeline(req: AnalyzeInput) -> ValidatorResult:
    """3エージェント・パイプライン実行."""
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
    )

    # Investigator: 発信元信頼度 + Gemini で論調バイアス・事実整合性分析
    investigator_result = await run_investigator(watcher_result)
    t_invest = time.monotonic() - t0

    # 🆕 構造化ログ: Investigator 結果
    log_event(
        EVENT_INVESTIGATOR_RESULT,
        severity=SEVERITY_INFO,
        source_credibility=getattr(investigator_result, "source_credibility_score", 0.0),
        position_bias=getattr(investigator_result, "position_bias_score", 0.0),
        fact_consistency=getattr(investigator_result, "fact_consistency_score", 0.0),
        source_label=getattr(investigator_result, "source_label", "") or "",
        elapsed_ms=int((t_invest - t_watcher) * 1000),
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
