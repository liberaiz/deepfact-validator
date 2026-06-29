"""Validator Agent — 統合・信頼度スコア算出・構造分析レポート生成."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from google import genai
from google.genai import types as genai_types

from src.agents.investigator_agent import InvestigatorResult
from src.agents.watcher_agent import WatcherResult
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CredibilityBreakdown:
    overall_score: float
    overall_label: str
    source_credibility: float
    position_bias: float        # 中立性スコア（高いほど中立）
    fact_consistency: float


@dataclass
class ValidatorResult:
    credibility: CredibilityBreakdown
    summary: str
    structural_observations: list[str] = field(default_factory=list)
    relationship_map: list[dict] = field(default_factory=list)
    primary_sources: list[str] = field(default_factory=list)
    contrarian_views: list[str] = field(default_factory=list)
    evidence_sources: list[dict] = field(default_factory=list)  # 🆕 第三者ソース URL 付き


def _label_from_score(score: float) -> str:
    if score >= 0.75:
        return "高"
    elif score >= 0.50:
        return "中"
    elif score >= 0.30:
        return "低"
    else:
        return "警告"


_GEMINI_CLIENT: genai.Client | None = None


def _get_gemini_client() -> genai.Client | None:
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT
    try:
        if settings.gcp.use_vertex_ai:
            _GEMINI_CLIENT = genai.Client(
                vertexai=True,
                project=settings.gcp.vertex_project,
                location=settings.gcp.vertex_location,
            )
            return _GEMINI_CLIENT
        if not settings.gcp.gemini_api_key:
            return None
        key = settings.gcp.gemini_api_key.strip()
        _GEMINI_CLIENT = genai.Client(api_key=key)
        return _GEMINI_CLIENT
    except Exception:
        logger.exception("Gemini client init failed")
        return None


VALIDATOR_PROMPT = """あなたは情報の信頼性を「構造として」可視化する分析官です。
以下のデータを統合し、客観的な構造分析レポートを生成してください。

【統合データ】
- 発信元: {source_label}（信頼度 {source_score:.2f}）
- 論調バイアス: {position_bias_raw:.2f}（0=中立, 1=極端）→ 中立性スコア {neutrality:.2f}
- 事実整合性: {fact_consistency:.2f}（0=検証不能, 1=完全検証可能）
- 主要主張: {claims}
- 観察された構造（バイアス）: {bias_obs}
- 観察された構造（事実整合性）: {fact_obs}
- 一次情報URL: {primary_sources}

【生成指示】
以下のJSON形式で返してください。

{{
  "summary": "本記事の構造的特徴を3-5文で要約。客観的に。人/団体を断定攻撃しない。",
  "structural_observations": ["構造観察を5-8個。「○○という構造」「○○の傾向」形式。具体的な構造名で。"],
  "concise_verdict": "1文で「この情報構造は信頼度○○、理由は○○の構造」と要約。"
}}

【トーン規律】
- 断定的な攻撃を避け「○○という構造」「○○の可能性」表現を使う。
- 政治・宗教的に微妙なテーマは「複数の立場が成り立つ構造」を必ず示す。
- JSONのみ。説明文を含めない。
"""


async def run_validator(
    watcher: WatcherResult,
    investigator: InvestigatorResult,
) -> ValidatorResult:
    s = settings.scoring
    source_cred = investigator.source_credibility_score
    bias_raw = investigator.position_bias_score
    neutrality_score = max(0.0, min(1.0, 1.0 - bias_raw))
    fact_consistency = investigator.fact_consistency_score

    overall = (
        source_cred * s.weight_source_credibility
        + neutrality_score * s.weight_position_bias
        + fact_consistency * s.weight_fact_consistency
    )
    overall = max(0.0, min(1.0, overall))

    breakdown = CredibilityBreakdown(
        overall_score=round(overall, 2),
        overall_label=_label_from_score(overall),
        source_credibility=round(source_cred, 2),
        position_bias=round(neutrality_score, 2),
        fact_consistency=round(fact_consistency, 2),
    )

    structural_observations: list[str] = [f.observation for f in investigator.findings]
    summary = ""

    client = _get_gemini_client()
    if client:
        try:
            prompt = VALIDATOR_PROMPT.format(
                source_label=investigator.source_label,
                source_score=source_cred,
                position_bias_raw=bias_raw,
                neutrality=neutrality_score,
                fact_consistency=fact_consistency,
                claims="\n".join(f"- {c}" for c in watcher.main_claims) if watcher.main_claims else "（未抽出）",
                bias_obs="\n".join(f"- {o}" for o in investigator.bias_observations) if investigator.bias_observations else "（なし）",
                fact_obs="\n".join(f"- {o}" for o in investigator.fact_observations) if investigator.fact_observations else "（なし）",
                primary_sources="\n".join(f"- {p}" for p in investigator.primary_sources) if investigator.primary_sources else "（なし・未明示）",
            )
            # 🆕 v0.4.8: Gemini call timeout 30s
            import asyncio as _asyncio
            response = await _asyncio.wait_for(
                client.aio.models.generate_content(
                    model=settings.gcp.gemini_model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.0,
                        top_k=1,
                        seed=42,
                        response_mime_type="application/json",
                    ),
                ),
                timeout=30.0,
            )
            data = json.loads(response.text)
            summary = data.get("summary", "")
            gemini_obs = list(data.get("structural_observations", []))
            structural_observations.extend(gemini_obs)

            logger.info("Validator Gemini OK summary_len=%d obs=%d", len(summary), len(gemini_obs))
        except Exception as e:
            logger.exception("Validator Gemini failed, fallback: %s", e)

    if not summary:
        parts = [
            f"発信元: {investigator.source_label}（信頼度 {source_cred:.2f}）",
        ]
        if watcher.keywords:
            parts.append(f"主要キーワード: {', '.join(watcher.keywords[:5])}")
        parts.append(
            f"構造分析: 出所{breakdown.source_credibility:.2f}"
            f" / 中立性{breakdown.position_bias:.2f}"
            f" / 事実整合性{breakdown.fact_consistency:.2f}"
        )
        if watcher.main_claims:
            parts.append(f"主要主張: {watcher.main_claims[0][:80]}…")
        summary = "。".join(parts)

    logger.info(
        "Validator overall=%.2f label=%s source=%.2f neut=%.2f fact=%.2f",
        overall, breakdown.overall_label, source_cred, neutrality_score, fact_consistency,
    )

    return ValidatorResult(
        credibility=breakdown,
        summary=summary,
        structural_observations=structural_observations,
        relationship_map=investigator.relationship_map,
        primary_sources=investigator.primary_sources,
        contrarian_views=investigator.contrarian_views,
        evidence_sources=investigator.evidence_sources,
    )
