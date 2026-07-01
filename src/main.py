"""DeepFact Validator — Cloud Run エントリポイント (FastAPI).

ハイブリッド入口（社長指示 2026-06-18・既存社内プロダクト LINE Bot 流用）:
- POST /api/analyze         : Chrome Extension / 一般クライアント向けURL/テキスト解析
- POST /webhook/line        : LINE Bot Webhook（既存社内プロダクト構造完全流用）
- GET  /health              : ヘルスチェック
- GET  /                    : 簡易ステータスページ

既存社内プロダクト src/main.py を流用しつつ DeepFact 向けに書き換え。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import os
import httpx
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PostbackAction,
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)
from pydantic import BaseModel, Field
# (slowapi は デコレータが効かなかったため廃止・手動実装に切替・2026-06-26)

from src.config import get_settings
from src.observability import (
    EVENT_ANALYZE_REQUEST,
    EVENT_CACHE_HIT,
    EVENT_CACHE_MISS,
    EVENT_ERROR,
    EVENT_VALIDATOR_RESULT,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    Timer,
    log_event,
    log_exception,
    new_request_id,
    request_context,
)
from src.orchestrator import (
    AnalysisUnavailableError,
    AnalyzeInput,
    FALLBACK_USER_MESSAGE,
    run_analyze_pipeline,
)
from src.tools.observability import (
    WarningRecord,
    generate_postmortem,
    record_warning,
    severity_from_score,
)
from src.tools.feedback_store import get_latest_input, save_feedback, save_latest_input
from src.tools.response_cache import get_cached_response, save_cached_response
from src.tools.vertex_vector_search import (
    count_articles,
    save_article,
    warmup_trusted_sources_cache,
)

settings = get_settings()

logging.basicConfig(level=settings.app.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DeepFact Validator",
    description=(
        "情報のObservability=ニュース/SNSの信頼度+利害関係をリアルタイム可視化する"
        "マルチエージェント・ブラウザ拡張+LINE Bot。内部コード名: deepfact-validator"
    ),
    version="1.1.9",
)

# 🛡️ Rate Limiter (Economic DoS 対策・Critical C3)
# 同一IPあたり 5req/分 で /api/analyze と /webhook/line を保護。
# Cloud Run コスト爆発と Gemini quota 浪費を構造的に防止する。
# v0.4.11 で slowapi → in-memory dict → Firestore-based へ進化:
#   - slowapi: デコレータが効かない事象（FastAPI 非同期との干渉）
#   - in-memory: Cloud Run 複数インスタンス分散で状態共有されない（実機検証で原因究明 2026-06-26）
#   - Firestore-based: インスタンス跨ぎで完全に状態共有（最終解）.
from google.cloud import firestore as _fs

_RATE_LIMIT_PER_MINUTE = 5
_RATE_LIMIT_WINDOW_SEC = 60.0
_fs_client: Optional[_fs.Client] = None


def _get_fs_client() -> _fs.Client:
    global _fs_client
    if _fs_client is None:
        _fs_client = _fs.Client()
    return _fs_client


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _check_rate_limit(request: Request) -> None:
    """Rate limit check (Firestore-based・全インスタンス間で状態共有).

    超過時は HTTPException(429) を投げる.
    Firestore コスト: 1 req あたり read 1 + write 1 = $0.0000012 (無視可能).
    """
    ip = _get_client_ip(request)
    # Firestore document ID に使えない文字を置換
    safe_ip = ip.replace(":", "_").replace("/", "_").replace(".", "-")
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW_SEC

    db = _get_fs_client()
    doc_ref = db.collection("rate_limits").document(safe_ip)

    transaction = db.transaction()

    @_fs.transactional
    def _check_and_record(txn):
        snapshot = doc_ref.get(transaction=txn)
        data = snapshot.to_dict() if snapshot.exists else None
        timestamps = (data or {}).get("timestamps", []) if data else []
        recent = [t for t in timestamps if t > cutoff]
        logger.info("RATE_LIMIT_FS: ip=%s count=%d existing=%d", ip, len(recent), len(timestamps))
        if len(recent) >= _RATE_LIMIT_PER_MINUTE:
            logger.info("RATE_LIMIT_HIT: ip=%s count=%d limit=%d", ip, len(recent), _RATE_LIMIT_PER_MINUTE)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {_RATE_LIMIT_PER_MINUTE} requests per minute",
            )
        recent.append(now)
        # 最新 20 件のみ保持（無限増殖防止）
        txn.set(doc_ref, {"timestamps": recent[-20:], "updated_at": now})

    try:
        _check_and_record(transaction)
    except HTTPException:
        raise
    except Exception:
        # Firestore 障害時は rate limit を bypass（fail-open・サービス継続優先）
        logger.exception("Firestore rate limit failed, bypassing")

# CORS: Chrome Extension / 外部ブラウザクライアントからの fetch を許可
# ⚠️ コンテスト/デモ環境のため allow_origins=["*"] にしているが、
#     本番では `chrome-extension://*` + 自社ドメインのみに限定予定（Phase 3）.
#     公開 API として安全なのは GET/POST 経由の analyze エンドポイントのみ.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)

# LINE SDK 初期化（既存社内プロダクト流用）
_line_config: Optional[Configuration] = None
_line_handler: Optional[WebhookHandler] = None
if settings.line.channel_access_token and settings.line.channel_secret:
    _line_config = Configuration(access_token=settings.line.channel_access_token)
    _line_handler = WebhookHandler(settings.line.channel_secret)
else:
    logger.warning("LINE Channel credentials not configured. Webhook will return 503.")

# Gemini client は agents 内部で google-genai SDK を直接利用


# ============================================================
# Models
# ============================================================


class AnalyzeRequest(BaseModel):
    input_type: str = Field(
        default="url", description="url / text / dom (Chrome Extension からのDOMダンプ)"
    )
    payload: str = Field(..., description="URL/テキスト/DOMダンプ")
    user_context: Optional[dict] = Field(
        default=None, description="ユーザーの過去関心事(パーソナライズ用)"
    )


class CredibilityScore(BaseModel):
    overall_score: float = Field(..., description="0-1 総合信頼度")
    overall_label: str = Field(..., description="高/中/低/警告")
    source_credibility: float
    position_bias: float
    fact_consistency: float


class AnalyzeResponse(BaseModel):
    credibility: CredibilityScore
    summary: str
    structural_observations: list[str] = Field(
        default_factory=list,
        description="構造分析（人ではなく構造を見る）",
    )
    relationship_map: list[dict] = Field(
        default_factory=list, description="メディア×スポンサー関係グラフ"
    )
    primary_sources: list[str] = Field(default_factory=list, description="一次情報URL")
    contrarian_views: list[str] = Field(
        default_factory=list, description="異なる立場の論点"
    )
    evidence_sources: list[dict] = Field(
        default_factory=list,
        description="第三者エビデンスソース（Google Fact Check / Wikipedia 等のURL付き）",
    )
    footer: str


# ============================================================
# Orchestrator（Watcher → Investigator → Validator パイプライン・v0.3 Vertex AI 実装済）
# ============================================================


async def _run_orchestrator(
    text: str,
    user_context: Optional[dict] = None,
    input_type: str = "text",
    skip_cache: bool = False,
) -> AnalyzeResponse:
    """マルチエージェント（Watcher→Investigator→Validator）を実行.

    skip_cache: 将来のキャッシュ統合用（現状 LINE Bot 経路はキャッシュなし＝毎回新規解析）.
    C7 γ案「再分析」では強制リフレッシュ意図でこのフラグを渡すが、
    LINE 経路ではもとから新規解析のため実質同じ動作（UX 上は明示的に「再分析中」と通知）.
    """
    t0 = time.monotonic()

    # Vertex AI Gemini 2.5-flash マルチエージェント・パイプライン（v0.3 実装済）
    # temperature=0.0 + seed=42 + top_k=1 で完全決定化
    result = await run_analyze_pipeline(
        AnalyzeInput(
            input_type=input_type,
            payload=text,
            user_context=user_context,
        )
    )

    elapsed = time.monotonic() - t0
    logger.info(
        "LATENCY analyze label=%s score=%.2f elapsed=%.2fs",
        result.credibility.overall_label,
        result.credibility.overall_score,
        elapsed,
    )

    footer = (
        f"──────────\n{settings.app.disclaimer_footer}\n\n"
        f"📚 {settings.app.fact_check_footer}"
    )

    return AnalyzeResponse(
        credibility=CredibilityScore(
            overall_score=result.credibility.overall_score,
            overall_label=result.credibility.overall_label,
            source_credibility=result.credibility.source_credibility,
            position_bias=result.credibility.position_bias,
            fact_consistency=result.credibility.fact_consistency,
        ),
        summary=result.summary,
        structural_observations=result.structural_observations,
        relationship_map=result.relationship_map,
        primary_sources=result.primary_sources,
        contrarian_views=result.contrarian_views,
        evidence_sources=result.evidence_sources,
        footer=footer,
    )


# ============================================================
# Endpoints
# ============================================================


@app.on_event("startup")
async def _warmup() -> None:
    """コンテナ起動時に信頼ソースキャッシュを事前初期化."""
    try:
        n = warmup_trusted_sources_cache()
        logger.info("Warmup trusted sources cache: %d entries", n)
    except Exception:
        logger.exception("Warmup trusted sources cache failed")


@app.get("/health")
async def health() -> dict[str, str]:
    """ヘルスチェック."""
    return {"status": "ok", "version": "1.1.9"}


@app.get("/")
async def root() -> dict:
    """簡易ステータスページ."""
    return {
        "name": "DeepFact Validator",
        "version": "1.1.9",
        "entry_points": {
            "chrome_extension": "/api/analyze",
            "web_ui_workbench": "/workbench",
            "line_bot": "/webhook/line",
            "health": "/health",
        },
        "principle": settings.app.primary_source_principle_footer,
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request, req: AnalyzeRequest) -> AnalyzeResponse:
    _check_rate_limit(request)  # 🛡️ C3 rate limit (5/分)
    """Chrome Extension / 一般クライアント向けURL/テキスト解析.

    🛡️ 同一入力完全一致保証: Firestore 入力ハッシュキャッシュで
       Vertex AI Gemini serving 側の非決定性をユーザー視点で吸収する.
    """
    # 🆕 Observability: request_id を発行し、以後の構造化ログに伝搬
    rid = new_request_id()
    with request_context(rid):
        log_event(
            EVENT_ANALYZE_REQUEST,
            severity=SEVERITY_INFO,
            input_type=req.input_type,
            payload_length=len(req.payload or ""),
            has_user_context=bool(req.user_context),
        )

        # 🆕 キャッシュチェック（同一入力 → 完全一致）
        try:
            cached = get_cached_response(req.input_type, req.payload)
            if cached:
                log_event(
                    EVENT_CACHE_HIT,
                    severity=SEVERITY_INFO,
                    input_type=req.input_type,
                )
                try:
                    return AnalyzeResponse(**cached)
                except Exception:
                    log_exception(
                        EVENT_ERROR,
                        message="Cached response deserialize failed",
                        stage="cache_deserialize",
                    )
            else:
                log_event(
                    EVENT_CACHE_MISS,
                    severity=SEVERITY_INFO,
                    input_type=req.input_type,
                )
        except Exception:
            log_exception(
                EVENT_ERROR,
                message="Cache lookup failed (non-blocking)",
                stage="cache_lookup",
            )

        try:
            with Timer() as pipeline_t:
                response = await _run_orchestrator(
                    req.payload, req.user_context, input_type=req.input_type
                )
        except AnalysisUnavailableError as e:
            # 🆕 v1.1.5 メティス V29 致命#2 対策:
            # Watcher / Investigator / Validator が fallback 状態のとき、
            # 「中 50%」固定値を返さず HTTP 503 でエラーメッセージを返す。
            log_event(
                EVENT_ERROR,
                severity=SEVERITY_WARNING,
                message="Analysis engine unavailable (fallback gate triggered)",
                stage=getattr(e, "stage", "unknown"),
                error_state=getattr(e, "error_state", None) or "",
                input_type=req.input_type,
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "analysis_unavailable",
                    "message": e.user_message,
                    "stage": getattr(e, "stage", "unknown"),
                    "error_state": getattr(e, "error_state", None) or "",
                    "retry_after_sec": 30,
                },
                headers={"Retry-After": "30"},
            )

        # 🆕 Validator 結果イベント（ログベースメトリクスの中核）
        log_event(
            EVENT_VALIDATOR_RESULT,
            severity=(
                SEVERITY_WARNING
                if response.credibility.overall_score < 0.5
                else SEVERITY_INFO
            ),
            overall_score=response.credibility.overall_score,
            overall_label=response.credibility.overall_label,
            source_credibility=response.credibility.source_credibility,
            position_bias=response.credibility.position_bias,
            fact_consistency=response.credibility.fact_consistency,
            elapsed_ms=pipeline_t.elapsed_ms,
            input_type=req.input_type,
        )

        # 🆕 Day 10-14: Cloud Logging Observability（SRE流警告履歴）
        from datetime import datetime, timezone
        user_id = (req.user_context or {}).get("user_id", "anonymous")
        source_domain = (
            req.payload.split("/")[2]
            if req.input_type == "url" and "/" in req.payload
            else ""
        )
        try:
            record_warning(WarningRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                user_id=user_id,
                source_url=req.payload if req.input_type == "url" else "",
                source_domain=source_domain,
                credibility_score=response.credibility.overall_score,
                credibility_label=response.credibility.overall_label,
                structural_observations_count=len(response.structural_observations),
                primary_sources_count=len(response.primary_sources),
                severity=severity_from_score(response.credibility.overall_score),
            ))
        except Exception:
            log_exception(
                EVENT_ERROR,
                message="Warning record failed (non-blocking)",
                stage="record_warning",
            )

        # 🆕 v0.3: 過去類似主張照合のための記事蓄積（state continuity）
        try:
            save_article(
                url=req.payload if req.input_type == "url" else "",
                title=response.summary[:150],
                summary=response.summary,
                body_excerpt=(req.payload[:2000] if req.input_type in ("text", "dom") else ""),
                source_domain=source_domain,
                credibility_score=response.credibility.overall_score,
                credibility_label=response.credibility.overall_label,
            )
        except Exception:
            log_exception(
                EVENT_ERROR,
                message="save_article failed (non-blocking)",
                stage="save_article",
            )

        # 🆕 同一入力完全一致保証のためのキャッシュ保存
        #    Gemini が失敗した時の fallback 結果は is_high_quality=False で
        #    保存（次回呼び出しでは再計算される）
        is_high_quality = not any(
            "Gemini 一時的に不可" in obs for obs in response.structural_observations
        )
        try:
            save_cached_response(
                req.input_type,
                req.payload,
                response.model_dump(),
                is_high_quality=is_high_quality,
            )
        except Exception:
            log_exception(
                EVENT_ERROR,
                message="Response cache save failed (non-blocking)",
                stage="save_cached_response",
            )

        return response


class PostmortemRequest(BaseModel):
    user_id: str = Field(default="anonymous", description="LINE userId / Chrome installId / anonymous")
    hours: int = Field(default=24, ge=1, le=168, description="振り返り時間（1〜168時間 = 1週間）")


class PostmortemResponse(BaseModel):
    markdown: str
    user_id: str
    hours: int


@app.post("/api/postmortem", response_model=PostmortemResponse)
async def postmortem(req: PostmortemRequest) -> PostmortemResponse:
    """直近 N 時間の情報接触履歴を SRE 流 Postmortem 形式で振り返り生成.

    Vertex AI Gemini が Lessons Learned + 推奨アクションを自然言語で生成.
    """
    md = generate_postmortem(user_id=req.user_id, hours=req.hours)
    return PostmortemResponse(markdown=md, user_id=req.user_id, hours=req.hours)


class FeedbackRequest(BaseModel):
    """Chrome Extension HITL feedback ペイロード（動画 F5/F6 で見せる 3択 UI）."""
    request_id: str = Field(default="", description="analyze 応答の request_id 紐付け")
    verdict: str = Field(..., description="misjudge / warning_correct / unsure")
    url_or_text: str = Field(default="", description="判定対象の URL またはテキスト断片")
    score: float = Field(default=0.0, description="判定時の総合信頼度（0-1）")
    label: str = Field(default="", description="判定時のラベル（高/中/低/警告）")


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: str


@app.post("/api/feedback", response_model=FeedbackResponse)
async def receive_feedback(req: FeedbackRequest) -> FeedbackResponse:
    """Chrome Extension からの HITL feedback 受信（v1.1.6 追加）.

    動画 F5/F6 で見せる 3択（誤判定 / 警告正しい / よくわからない）を Firestore に蓄積。
    既存 save_feedback(user_id, verdict) を request_id ベースで活用する。
    LINE Bot 経路の useful/not_useful とは別軸（信頼ソース辞書の CI/CD 改善用）.
    """
    # 既存 save_feedback() を user_id=request_id で活用（feedback_store と互換）
    user_key = req.request_id or "chrome-anonymous"
    save_feedback(user_key, req.verdict)
    logger.info(
        "feedback_received: verdict=%s score=%.3f label=%s request_id=%s",
        req.verdict,
        req.score or 0.0,
        req.label,
        req.request_id,
    )
    return FeedbackResponse(status="saved", feedback_id=user_key)


@app.get("/api/articles/count")
async def articles_count() -> dict[str, int]:
    """蓄積記事数（運用メトリクス）."""
    return {"total": count_articles()}


@app.post("/webhook/line")
async def line_webhook(request: Request) -> dict[str, str]:
    """LINE Messaging API Webhook (既存社内プロダクト構造流用)."""
    _check_rate_limit(request)  # 🛡️ C3 rate limit (5/分)
    if _line_handler is None or _line_config is None:
        raise HTTPException(status_code=503, detail="LINE webhook not configured")

    body = (await request.body()).decode("utf-8")
    signature = request.headers.get("X-Line-Signature", "")
    logger.info("LINE webhook body preview: %s", body[:500])

    try:
        _line_handler.handle(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=403, detail="Invalid LINE signature")

    return {"status": "ok"}


# ============================================================
# LINE Bot ハンドラ（既存社内プロダクト 構造を流用）
# ============================================================

if _line_handler is not None:
    import threading

    # 🆕 v0.4.5: LINE Bot 用の永続 event loop（別スレッドで run_forever）
    #   asyncio.run() を毎回呼ぶと event loop が破棄→再生成され、
    #   Vertex AI / 外部 API の接続プールが毎回 cold start 状態になる.
    #   永続 loop + run_coroutine_threadsafe で接続持続化する.
    _LINE_BG_LOOP: asyncio.AbstractEventLoop | None = None
    _LINE_BG_LOOP_LOCK = threading.Lock()

    def _ensure_line_bg_loop() -> asyncio.AbstractEventLoop:
        global _LINE_BG_LOOP
        with _LINE_BG_LOOP_LOCK:
            if _LINE_BG_LOOP is None or _LINE_BG_LOOP.is_closed():
                _LINE_BG_LOOP = asyncio.new_event_loop()
                t = threading.Thread(
                    target=_LINE_BG_LOOP.run_forever,
                    daemon=True,
                    name="line-bg-loop",
                )
                t.start()
                logger.info("LINE background event loop started (persistent)")
        return _LINE_BG_LOOP

    async def _process_line_text_async(user_text: str, user_id: str, force_refresh: bool = False) -> None:
        """LINE Bot の DeepFact 解析→push_message（永続 event loop で実行）.

        force_refresh=True で Firestore キャッシュをスキップ（C7 γ案「再分析」用）.
        """
        try:
            # 再分析以外なら最新入力を保存（再分析時に取得用）
            if not force_refresh:
                save_latest_input(user_id, user_text)
            # URLっぽい入力は url 扱い・そうでなければ text
            input_type = "url" if user_text.strip().startswith(("http://", "https://")) else "text"
            result = await _run_orchestrator(user_text, user_context=None, input_type=input_type, skip_cache=force_refresh)
            footer = result.footer
            c = result.credibility
            # 🆕 v0.4.8: 信頼度ラベルにアイコン付与（一目で判別）
            label_icon = {
                "警告": "🚨",
                "低": "⚠️",
                "中": "〽️",
                "高": "✅",
            }.get(c.overall_label, "🔍")
            parts = [
                f"{label_icon}【信頼度: {c.overall_label} ({int(c.overall_score * 100)}%)】",
                f"出所 {c.source_credibility:.2f} / 中立性 {c.position_bias:.2f} / 事実整合性 {c.fact_consistency:.2f}",
                "",
                f"📝【要約】\n{result.summary}",
            ]
            # 構造観察（上位5件）
            obs_top = result.structural_observations[:5]
            if obs_top:
                parts.append("")
                parts.append("🔎【構造観察】")
                parts.extend(f"・{o}" for o in obs_top)
            # 対立見解
            if result.contrarian_views:
                parts.append("")
                parts.append("🌐【別の立場】")
                parts.extend(f"・{v}" for v in result.contrarian_views[:3])
            # 一次情報
            if result.primary_sources:
                parts.append("")
                parts.append("🔗【一次情報候補】")
                parts.extend(f"・{p}" for p in result.primary_sources[:5])
            # 📚 第三者判定エビデンス（Google Fact Check / Wikipedia 等）
            if result.evidence_sources:
                parts.append("")
                parts.append("📚【判定エビデンス・ソース】")
                for ev in result.evidence_sources[:5]:
                    pub = ev.get("publisher") or "（不明）"
                    rating = ev.get("rating") or ""
                    title = (ev.get("title") or "")[:60]
                    url = ev.get("url") or ""
                    rating_str = f"[{rating}] " if rating else ""
                    parts.append(f"・{rating_str}{pub}: {title}")
                    if url:
                        parts.append(f"  {url}")
            parts.append("")
            parts.append(footer)
            reply_text = "\n".join(parts)
            # v1.1.4 系列（C7 γ案 最終版・2択シンプル）: UX feedback のみ
            #   社長指示2026-06-26「再分析は決定的解析で結果同じ＝意味薄い」→ 2択化
            #   - 👍 役に立った
            #   - 👎 あまり役に立たなかった
            #   どちらも同じ「ありがとうございます」で返し、Firestore に蓄積
            hitl_quick_reply = QuickReply(items=[
                QuickReplyItem(action=PostbackAction(
                    label="👍 役に立った",
                    data="feedback=useful",
                    display_text="👍 役に立った",
                )),
                QuickReplyItem(action=PostbackAction(
                    label="👎 あまり役に立たなかった",
                    data="feedback=not_useful",
                    display_text="👎 あまり役に立たなかった",
                )),
            ])
            with ApiClient(_line_config) as api_client:  # type: ignore[arg-type]
                line_api = MessagingApi(api_client)
                line_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(
                            text=reply_text[:4900],
                            quick_reply=hitl_quick_reply,
                        )],
                    )
                )
        except AnalysisUnavailableError as e:
            # 🆕 v1.1.5 メティス V29 致命#2 対策:
            # Watcher/Investigator/Validator が fallback したとき、LINE Push で
            # 「分析エンジン混雑」メッセージを送る（「中 50%」固定値の返却を防ぐ）。
            logger.warning(
                "LINE: AnalysisUnavailableError stage=%s state=%s",
                getattr(e, "stage", "unknown"),
                getattr(e, "error_state", None),
            )
            try:
                with ApiClient(_line_config) as api_client:  # type: ignore[arg-type]
                    line_api = MessagingApi(api_client)
                    line_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(
                                text=(
                                    "⌛ " + e.user_message + "\n"
                                    "（30秒〜数分後にもう一度お試しください）"
                                )
                            )],
                        )
                    )
            except Exception:
                logger.exception("LINE fallback-push failed")
        except Exception:
            logger.exception("LINE background processing failed")
            try:
                with ApiClient(_line_config) as api_client:  # type: ignore[arg-type]
                    line_api = MessagingApi(api_client)
                    line_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(
                                text=(
                                    "申し訳ありません。解析中にエラーが発生しました。\n"
                                    "もう一度お試しください。"
                                )
                            )],
                        )
                    )
            except Exception:
                logger.exception("LINE error-push failed")

    def _process_line_text_in_background(user_text: str, user_id: str, force_refresh: bool = False) -> None:
        """LINE Bot handler から呼ぶ同期エントリ.
        永続 event loop に async タスクを schedule（fire-and-forget）.
        force_refresh=True で Firestore キャッシュをスキップ.
        """
        loop = _ensure_line_bg_loop()
        asyncio.run_coroutine_threadsafe(
            _process_line_text_async(user_text, user_id, force_refresh=force_refresh),
            loop,
        )

    @_line_handler.add(MessageEvent, message=TextMessageContent)
    def _handle_line_text_message(event: MessageEvent) -> None:
        """LINE テキストメッセージ：即 reply で「分析中」→ 永続 loop で分析→ push_message."""
        user_id = getattr(event.source, "user_id", None) or ""
        # 🆕 即時 reply（reply_token を 30 秒以内に消費）
        try:
            with ApiClient(_line_config) as api_client:  # type: ignore[arg-type]
                line_api = MessagingApi(api_client)
                line_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=(
                            "⌛ 分析中です…完了次第お返事します（30〜90秒）"
                        ))],
                    )
                )
        except Exception:
            logger.exception("Immediate reply failed (non-blocking)")

        # 永続 event loop に分析タスク schedule
        if user_id:
            _process_line_text_in_background(event.message.text, user_id)
        else:
            logger.warning("LINE event has no user_id, skip analysis")

    WELCOME_MESSAGE = (
        "🔍 DeepFact Validator へようこそ\n"
        "\n"
        "ネット記事の URL や、気になるテキストをそのまま送ってください。\n"
        "AIエージェントが以下を解析してお返しします:\n"
        "・信頼度スコア（0-100%）\n"
        "・構造分析（出所/論調/バイアス）\n"
        "・一次情報の所在\n"
        "・異なる立場の論点"
    )

    @_line_handler.add(FollowEvent)
    def _handle_follow_event(event: FollowEvent) -> None:
        """友だち追加（FollowEvent）時にあいさつメッセージ."""
        try:
            with ApiClient(_line_config) as api_client:  # type: ignore[arg-type]
                line_api = MessagingApi(api_client)
                line_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=WELCOME_MESSAGE)],
                    )
                )
        except Exception:
            logger.exception("Welcome message reply failed")

    @_line_handler.add(PostbackEvent)
    def _handle_line_postback(event: PostbackEvent) -> None:
        """v1.1.4 系列（C7 γ案 最終版）: UX feedback 2択（共通返答）."""
        user_id = getattr(event.source, "user_id", None) or ""
        data = event.postback.data or ""

        if data.startswith("feedback="):
            verdict = data.split("=", 1)[1]  # useful / not_useful
            save_feedback(user_id, verdict)
            _reply_simple(
                event.reply_token,
                "回答ありがとうございます😊 今後の品質向上の参考にさせていただきます",
            )
            return

        logger.warning("Unknown postback data: %s", data[:50])

    def _reply_simple(reply_token: str, text: str) -> None:
        """シンプルな reply ヘルパー."""
        try:
            with ApiClient(_line_config) as api_client:  # type: ignore[arg-type]
                line_api = MessagingApi(api_client)
                line_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=text)],
                    )
                )
        except Exception:
            logger.exception("reply failed")


# ============================================================
# Web UI Workbench (v1.1.7・popup 廃止後の主入口)
# ============================================================
#
# `extension/popup/` を廃止し、Web UI Workbench を `/workbench` で配信する.
#   - Cloud Run コンテナ (Dockerfile で COPY web-ui/ /app/web-ui/) → /app/web-ui
#   - ローカル開発 (cwd=プロジェクトルート)                 → ./web-ui
# どちらでも見つかるよう、存在チェックしてから mount する.
_WEB_UI_CANDIDATES = [
    "/app/web-ui",
    os.path.join(os.path.dirname(__file__), "..", "web-ui"),
    "web-ui",
]
for _candidate in _WEB_UI_CANDIDATES:
    _abs = os.path.abspath(_candidate)
    if os.path.isdir(_abs):
        app.mount("/workbench", StaticFiles(directory=_abs, html=True), name="workbench")
        logger.info("Mounted Web UI Workbench at /workbench from %s", _abs)
        break
else:
    logger.warning("web-ui directory not found in any candidate path: %s", _WEB_UI_CANDIDATES)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=True)
