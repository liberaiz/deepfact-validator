"""Prompt Injection Defense — Layer 3 (output monitor).

メティス V29 致命#3「プロンプトインジェクション耐性ゼロ」対策の 3 層目.

3 層構成:
  Layer 1 = 各エージェントプロンプト先頭の「絶対遵守」ブロック (防御的プロンプティング)
  Layer 2 = `<user_input>...</user_input>` タグでユーザー入力を明示マーキング
  Layer 3 = LLM が返した JSON のフィールド値を機械検証し、攻撃成功痕跡を検出
            → 検出時は値を [INJECTION DETECTED] に置換 + 信頼度を ≤0.30 に強制低下

検出キーワードカテゴリ:
  A. メタ指示痕跡 ("これまでの指示を無視" "ignore previous" 等)
  B. 出力強制痕跡 ("以下のJSONを出力" "一字一句変えず" 等)
  C. 過剰肯定痕跡 ("公式に承認" "完全に信頼" 等 — 攻撃者が「最高評価」を強制した痕跡)

完全自前ロジック (外部 LLM 呼び出しなし) — 既存パイプラインの遅延を増やさない.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# 検出パターン辞書
# ============================================================
# 各パターンは「LLM の JSON 出力値に混入していたら攻撃成功の痕跡」を表す.
# 通常の構造分析結果には混入し得ない文字列のみを採用する.

_INJECTION_PATTERNS_META: list[str] = [
    # メタ指示痕跡 (A)
    "これまでの指示を無視",
    "これまでの指示はすべて無視",
    "以前の指示を無視",
    "上記の指示を無視",
    "前の指示を無視",
    "システムプロンプトを無視",
    "あなたは今から",
    "あなたは今後",
    "あなたの役割を変更",
    "新しい役割",
    "ignore previous instructions",
    "ignore all previous",
    "ignore the above",
    "disregard previous",
    "override previous",
    "forget all previous",
    "you are now",
    "act as",
    "pretend to be",
    "new instruction",
    "new instructions",
    "system prompt",
    "instruction override",
    "prompt injection",
]

_INJECTION_PATTERNS_FORCE_OUTPUT: list[str] = [
    # 出力強制痕跡 (B)
    "以下のJSONを出力",
    "以下のJSONをそのまま",
    "以下のJSONを、一字一句",
    "以下のjsonを一字一句",
    "一字一句変えず",
    "一字一句変えない",
    "一字一句そのまま",
    "そのまま出力してください",
    "下記JSONを返",
    "下記のJSONを返",
    "次のJSONを返",
    "output the following json",
    "return the following json",
    "respond with the following",
    "verbatim",
    "exactly as written",
    "without modification",
    "do not modify",
]

_INJECTION_PATTERNS_OVER_PRAISE: list[str] = [
    # 過剰肯定痕跡 (C) — 攻撃者が「最高評価」を強制した痕跡
    # ⚠️ 通常の中立的な分析結果には混入し得ない極端な言い回しのみ採用
    "完全に信頼できます",
    "完全に信頼できる",
    "完全に信頼性",
    "すべての主張は科学的根拠",
    "全ての主張は科学的根拠",
    "公式に承認されました",
    "公式に承認された",
    "最高の評価",
    "最高評価を与え",
    "100%信頼",
    "100％信頼",
    "absolute trust",
    "completely trustworthy",
    "officially approved",
    "highest rating",
    "highest score",
    "fully verified",
    "100% reliable",
]

# 統合キーワード辞書 (検出ログ用にカテゴリ付き)
_INJECTION_CATEGORIES: dict[str, list[str]] = {
    "meta_instruction": _INJECTION_PATTERNS_META,
    "force_output": _INJECTION_PATTERNS_FORCE_OUTPUT,
    "over_praise": _INJECTION_PATTERNS_OVER_PRAISE,
}


# ============================================================
# 信頼度低下のための上限値
# ============================================================
# 検出時に「信頼度・評価」を表すフィールドが上限 0.30 を超えていたら強制的に 0.30 まで落とす.
# 0.30 は label の「警告」と「低」の境界 (_label_from_score) — UX 上「警告」表示へ倒す.
INJECTION_SCORE_CAP: float = 0.30

# 信頼度・スコア系フィールド名 (層3 の cap 対象)
_SCORE_FIELD_NAMES: set[str] = {
    # English
    "overall_score",
    "source_credibility",
    "source_credibility_score",
    "fact_consistency",
    "fact_consistency_score",
    "neutrality",
    "credibility",
    "score",
    "confidence",
    # 日本語呼び (今後の互換用)
    "信頼度",
    "信頼性スコア",
    "総合スコア",
}

# 「中立性」は値が高いほど中立 — 攻撃で底上げされ得るので cap 対象に含めるが、
# 旧称 position_bias_raw (0=中立, 1=極端) は逆向き = 攻撃時に "中立寄せ" される可能性は低い.
# 安全側に倒し position_bias (中立性スコア) も含める.
_SCORE_FIELD_NAMES.add("position_bias")
_SCORE_FIELD_NAMES.add("position_bias_score")  # ⚠️ こちらは raw bias なので cap しないほうが安全だが、
# 検出時の "総合信頼度ダウン" は別途 overall_score 側で担保するため、ここでは含めない再判定が望ましい.
_SCORE_FIELD_NAMES.discard("position_bias_score")  # bias_score (高=偏り) は cap せず生のまま


# ============================================================
# 検出ロジック
# ============================================================


def _find_injection_keywords(text: str) -> list[tuple[str, str]]:
    """テキスト内の injection 痕跡キーワードを (category, term) のリストで返す."""
    if not text or not isinstance(text, str):
        return []
    text_lower = text.lower()
    hits: list[tuple[str, str]] = []
    for category, terms in _INJECTION_CATEGORIES.items():
        for term in terms:
            if term.lower() in text_lower:
                hits.append((category, term))
    return hits


def _scan_value(value: Any) -> list[tuple[str, str]]:
    """str / list / dict を再帰走査して injection 痕跡を集める."""
    if isinstance(value, str):
        return _find_injection_keywords(value)
    if isinstance(value, list):
        out: list[tuple[str, str]] = []
        for item in value:
            out.extend(_scan_value(item))
        return out
    if isinstance(value, dict):
        out = []
        for v in value.values():
            out.extend(_scan_value(v))
        return out
    return []


def _sanitize_value(value: Any, marker: str = "[INJECTION DETECTED]") -> Any:
    """検出された injection 痕跡を含む文字列フィールドを marker に置換.

    - 文字列: 痕跡語を含む場合 marker に丸ごと置換 (部分置換だと攻撃文の半分が残る)
    - リスト: 各要素を再帰的に sanitize
    - 辞書: 各値を再帰的に sanitize
    - その他: そのまま返す (数値 / bool / None)
    """
    if isinstance(value, str):
        if _find_injection_keywords(value):
            return marker
        return value
    if isinstance(value, list):
        return [_sanitize_value(v, marker) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_value(v, marker) for k, v in value.items()}
    return value


def _cap_score_fields(obj: Any, cap: float = INJECTION_SCORE_CAP) -> Any:
    """信頼度・スコア系フィールド (再帰) を上限 cap で頭打ちにする."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k in _SCORE_FIELD_NAMES and isinstance(v, (int, float)):
                if float(v) > cap:
                    out[k] = cap
                    logger.warning(
                        "Injection defense: capped score field %s %.3f -> %.3f",
                        k, float(v), cap,
                    )
                else:
                    out[k] = v
            else:
                out[k] = _cap_score_fields(v, cap)
        return out
    if isinstance(obj, list):
        return [_cap_score_fields(item, cap) for item in obj]
    return obj


# ============================================================
# 公開 API
# ============================================================


def check_and_filter_injection(
    json_obj: dict,
    *,
    agent_name: str = "unknown",
    marker: str = "[INJECTION DETECTED]",
    score_cap: float = INJECTION_SCORE_CAP,
) -> tuple[dict, bool]:
    """LLM が返した JSON dict を機械検証し、injection 痕跡を検出 + 中和する.

    Args:
        json_obj: LLM が返したパース済 JSON (dict).
        agent_name: ログ識別用 (watcher / investigator / validator).
        marker: 検出文字列を置換するマーカー.
        score_cap: 検出時に信頼度・スコア系フィールドを頭打ちにする上限値.

    Returns:
        (フィルタ後 dict, 検出したかの bool).
        - dict が dict でない場合は (元の値, False) を返す.
        - 検出時:
            * 痕跡含む文字列フィールドを marker に置換
            * 信頼度・スコア系フィールド (overall_score / source_credibility 等) を
              score_cap 以下に頭打ち
            * warning ログを出す
    """
    if not isinstance(json_obj, dict):
        return (json_obj, False)

    hits = _scan_value(json_obj)
    if not hits:
        return (json_obj, False)

    # 検出ログ (代表 5 件のみ・重複削除)
    seen: set[tuple[str, str]] = set()
    unique_hits: list[tuple[str, str]] = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            unique_hits.append(h)
    sample = unique_hits[:5]
    logger.warning(
        "PROMPT_INJECTION_DETECTED agent=%s hits=%d sample=%s",
        agent_name,
        len(unique_hits),
        [f"{cat}:{term[:30]}" for cat, term in sample],
    )

    # フィールドを sanitize → score を cap
    sanitized = _sanitize_value(json_obj, marker)
    if not isinstance(sanitized, dict):
        # 念のためフォールバック
        sanitized = {"_injection_detected": True, "_original_keys": list(json_obj.keys())}
    capped = _cap_score_fields(sanitized, cap=score_cap)
    if not isinstance(capped, dict):
        capped = sanitized
    return (capped, True)


def is_likely_injection_text(text: str) -> bool:
    """単純な bool 判定 — 入力テキスト自体に攻撃痕跡があるか.

    利用例: テスト・将来の Watcher 前段フィルタ.
    """
    return bool(_find_injection_keywords(text))


__all__ = [
    "check_and_filter_injection",
    "is_likely_injection_text",
    "INJECTION_SCORE_CAP",
]
