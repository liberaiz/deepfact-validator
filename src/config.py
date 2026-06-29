"""DeepFact Validator — 設定モジュール.

既存社内プロダクト config.py の構造を流用＋LINE Bot/Chrome Extension対応。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class GCPConfig:
    project_id: str
    region: str
    gemini_api_key: str
    gemini_model: str
    use_vertex_ai: bool
    vertex_project: str
    vertex_location: str
    google_fact_check_api_key: str = ""  # Google Fact Check Tools API（オプション）


@dataclass(frozen=True)
class FirestoreConfig:
    collection_sources: str          # 信頼ソース ホワイトリスト
    collection_warnings: str         # 警告履歴（Observability）
    collection_user_context: str     # ユーザー関心事
    collection_relationships: str    # メディア×スポンサー関係


@dataclass(frozen=True)
class LineConfig:
    """既存社内プロダクト LINE Bot 構造の完全流用."""
    channel_access_token: str
    channel_secret: str


@dataclass(frozen=True)
class AppConfig:
    env: str
    log_level: str
    disclaimer_footer: str
    fact_check_footer: str
    primary_source_principle_footer: str


@dataclass(frozen=True)
class ScoringConfig:
    """信頼度スコアリング設定."""
    weight_source_credibility: float
    weight_position_bias: float
    weight_fact_consistency: float
    threshold_warning: float
    threshold_critical: float


@dataclass(frozen=True)
class Settings:
    gcp: GCPConfig
    firestore: FirestoreConfig
    line: LineConfig
    app: AppConfig
    scoring: ScoringConfig


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """環境変数から設定を読み込む（キャッシュ付き）."""
    return Settings(
        gcp=GCPConfig(
            project_id=os.getenv("GCP_PROJECT_ID", "deepfact-validator"),
            region=os.getenv("GCP_REGION", "asia-northeast1"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            use_vertex_ai=os.getenv("USE_VERTEX_AI", "false").lower() == "true",
            vertex_project=os.getenv("VERTEX_PROJECT") or os.getenv("GCP_PROJECT_ID", "deepfact-validator"),
            vertex_location=os.getenv("VERTEX_LOCATION", "asia-northeast1"),
            google_fact_check_api_key=os.getenv("GOOGLE_FACT_CHECK_API_KEY", ""),
        ),
        firestore=FirestoreConfig(
            collection_sources=os.getenv("FIRESTORE_COLLECTION_SOURCES", "deepfact_sources"),
            collection_warnings=os.getenv("FIRESTORE_COLLECTION_WARNINGS", "deepfact_warnings"),
            collection_user_context=os.getenv(
                "FIRESTORE_COLLECTION_USER_CONTEXT", "deepfact_user_context"
            ),
            collection_relationships=os.getenv(
                "FIRESTORE_COLLECTION_RELATIONSHIPS", "deepfact_relationships"
            ),
        ),
        line=LineConfig(
            channel_access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""),
            channel_secret=os.getenv("LINE_CHANNEL_SECRET", ""),
        ),
        app=AppConfig(
            env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            disclaimer_footer=os.getenv("DISCLAIMER_FOOTER", ""),
            fact_check_footer=os.getenv(
                "FACT_CHECK_FOOTER",
                "情報の真偽判断は一次情報まで遡ることを推奨します。",
            ),
            primary_source_principle_footer=os.getenv(
                "PRIMARY_SOURCE_PRINCIPLE_FOOTER",
                "",
            ),
        ),
        scoring=ScoringConfig(
            weight_source_credibility=float(os.getenv("WEIGHT_SOURCE_CREDIBILITY", "0.40")),
            weight_position_bias=float(os.getenv("WEIGHT_POSITION_BIAS", "0.30")),
            weight_fact_consistency=float(os.getenv("WEIGHT_FACT_CONSISTENCY", "0.30")),
            threshold_warning=float(os.getenv("THRESHOLD_WARNING", "0.50")),
            threshold_critical=float(os.getenv("THRESHOLD_CRITICAL", "0.30")),
        ),
    )
