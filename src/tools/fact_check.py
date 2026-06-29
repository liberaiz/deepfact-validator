"""第三者ソース照合 — Google Fact Check Tools API + Wikipedia API.

目的:
  キーワード辞書だけに頼らず、実体ソース（URL 付き）で判定根拠を能動取得する.

ソース:
  1. Google Fact Check Tools API
     - 公式: https://factchecktools.googleapis.com/v1alpha1/claims:search
     - IFCN 加盟ファクトチェック団体（Snopes / PolitiFact / FullFact / JFC 等）の検証結果
     - 無料・要 API キー（Secret Manager: DEEPFACT_GOOGLE_FACT_CHECK_API_KEY）
  2. Wikipedia REST API
     - 公式: https://ja.wikipedia.org/w/api.php
     - 無料・登録不要・主張から関連記事を能動検索
     - 「○○陰謀論」「○○の主張」記事をヒットさせる

出力:
  EvidenceSource のリスト（URL / 発行者 / 評価 / 関連度）
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

FACT_CHECK_API = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
WIKIPEDIA_API_JA = "https://ja.wikipedia.org/w/api.php"
WIKIPEDIA_API_EN = "https://en.wikipedia.org/w/api.php"

# v0.4.4: タイムアウト短縮（8s→5s）+ リトライ 1 回（cold start 等での一時的失敗復活）
HTTP_TIMEOUT = 5.0
RETRY_COUNT = 1

# v0.4.4: API 全失敗時の fallback エビデンス
#   PROPAGANDA_PATTERNS カテゴリ別に対応する Wikipedia 反証記事を辞書化.
#   gather_evidence が空配列を返した場合に、検出されたカテゴリから category-based
#   Wikipedia URL を返して「最低限の判定エビデンス」を保証する.
PROPAGANDA_COUNTER_WIKI: dict[str, list[dict]] = {
    "high_alert": [
        {"title": "プロパガンダ", "url": "https://ja.wikipedia.org/wiki/プロパガンダ",
         "excerpt": "感情を煽る発信の構造を解説する記事"},
        {"title": "認知バイアス", "url": "https://ja.wikipedia.org/wiki/認知バイアス",
         "excerpt": "断定的主張で陥りやすい思考の偏り"},
    ],
    "evidence_lack": [
        {"title": "確証バイアス", "url": "https://ja.wikipedia.org/wiki/確証バイアス",
         "excerpt": "証拠なし主張を受け入れやすい認知傾向"},
        {"title": "悪魔の証明", "url": "https://ja.wikipedia.org/wiki/悪魔の証明",
         "excerpt": "「証拠が無いこと」を主張根拠にする論法の問題"},
    ],
    "urgency": [
        {"title": "ソーシャルメディアによる偽情報の拡散",
         "url": "https://ja.wikipedia.org/wiki/ソーシャルメディアによる偽情報の拡散",
         "excerpt": "拡散煽動型フェイクの構造的解説"},
    ],
    "medical_fraud": [
        {"title": "ワクチン忌避", "url": "https://ja.wikipedia.org/wiki/ワクチン忌避",
         "excerpt": "ワクチン陰謀論の構造的解説と反証"},
        {"title": "2019年コロナウイルス感染症流行に関連する誤情報",
         "url": "https://ja.wikipedia.org/wiki/2019年コロナウイルス感染症流行に関連する誤情報",
         "excerpt": "COVID-19 周辺の主要誤情報をまとめた反証記事"},
        {"title": "5Gと健康への影響をめぐる議論",
         "url": "https://ja.wikipedia.org/wiki/第5世代移動通信システム#健康と環境への影響",
         "excerpt": "5G関連陰謀論への科学的反証"},
    ],
    "conspiracy": [
        {"title": "陰謀論", "url": "https://ja.wikipedia.org/wiki/陰謀論",
         "excerpt": "陰謀論の構造・心理学的特徴の網羅的解説"},
        {"title": "ディープステート", "url": "https://ja.wikipedia.org/wiki/ディープステート",
         "excerpt": "「闇の政府」陰謀論の出典と批判"},
    ],
}

# v0.4.6: 公的機関・ファクトチェック団体の直接 URL（Wikipedia 一色解消）
#   社長指摘「Wikipedia 自体に編集権限問題がある」→ 公的機関・IFCN 加盟団体を上位ソースに.
#   Wikipedia は補助・確認用の位置付けに格下げ.
PROPAGANDA_COUNTER_OFFICIAL: dict[str, list[dict]] = {
    "high_alert": [
        {"publisher": "日本ファクトチェックセンター (JFC)", "title": "JFC - 国内主要ファクトチェック機関",
         "url": "https://www.factcheckcenter.jp/",
         "excerpt": "IFCN 加盟・Google.org 支援の独立ファクトチェック機関"},
        {"publisher": "FactCheck.org", "title": "FactCheck.org - 非党派ファクトチェック",
         "url": "https://www.factcheck.org/",
         "excerpt": "アネンバーグ公共政策センター運営の非党派ファクトチェック"},
    ],
    "evidence_lack": [
        {"publisher": "Snopes", "title": "Snopes - 老舗ファクトチェック機関",
         "url": "https://www.snopes.com/",
         "excerpt": "1994年創設・IFCN 加盟の独立ファクトチェック"},
        {"publisher": "PolitiFact", "title": "PolitiFact - 政治発言検証",
         "url": "https://www.politifact.com/",
         "excerpt": "ピューリッツァー賞受賞・IFCN 加盟の検証機関"},
    ],
    "urgency": [
        {"publisher": "Full Fact UK", "title": "Full Fact - 英国独立ファクトチェック",
         "url": "https://fullfact.org/",
         "excerpt": "英国の独立慈善団体・IFCN 加盟"},
        {"publisher": "Lead Stories", "title": "Lead Stories - 米国IFCN加盟ファクトチェック",
         "url": "https://leadstories.com/",
         "excerpt": "IFCN 加盟・米国の独立系ファクトチェック機関"},
    ],
    "medical_fraud": [
        {"publisher": "厚生労働省", "title": "厚労省 - 新型コロナワクチンに関するQ&A",
         "url": "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000121431_00094.html",
         "excerpt": "厚生労働省公式のワクチンQ&A・有効性・安全性"},
        {"publisher": "PMDA 医薬品医療機器総合機構", "title": "PMDA - 公式トップ",
         "url": "https://www.pmda.go.jp/",
         "excerpt": "医薬品・ワクチン副反応・安全性の独立評価機関"},
        {"publisher": "WHO", "title": "WHO - COVID-19 vaccines facts",
         "url": "https://www.who.int/emergencies/diseases/novel-coronavirus-2019/covid-19-vaccines",
         "excerpt": "世界保健機関の COVID-19 ワクチン公式情報"},
        {"publisher": "CDC", "title": "CDC - COVID-19 Vaccine Safety",
         "url": "https://www.cdc.gov/coronavirus/2019-ncov/vaccines/safety/safety-of-vaccines.html",
         "excerpt": "米国疾病予防管理センターのワクチン安全性公式情報"},
        {"publisher": "総務省", "title": "総務省 - 電波利用ホームページ",
         "url": "https://www.tele.soumu.go.jp/",
         "excerpt": "電波（5G を含む）の利用と健康影響に関する総務省公式情報"},
    ],
    "conspiracy": [
        {"publisher": "日本ファクトチェックセンター (JFC)", "title": "JFC - 陰謀論検証アーカイブ",
         "url": "https://www.factcheckcenter.jp/",
         "excerpt": "IFCN 加盟・国内陰謀論ファクトチェックの入口"},
        {"publisher": "Snopes", "title": "Snopes - 検証アーカイブ",
         "url": "https://www.snopes.com/fact-check/",
         "excerpt": "1994年創設・IFCN 加盟の老舗ファクトチェックの最新検証一覧"},
        {"publisher": "PolitiFact", "title": "PolitiFact - 検証アーカイブ",
         "url": "https://www.politifact.com/factchecks/",
         "excerpt": "ピューリッツァー賞受賞・IFCN 加盟の検証機関最新一覧"},
    ],
}


@dataclass
class EvidenceSource:
    """判定エビデンスソース．LINE Bot / Chrome Extension に渡る構造."""
    source_type: str        # "fact_check" / "wikipedia" / "trusted_domain"
    publisher: str          # 発行者・媒体名（例: Snopes, JFC, Wikipedia）
    title: str              # ソース見出し
    url: str                # 実URL（クリック可能）
    rating: str = ""        # 「FALSE」「Misleading」「true」など（fact-check のみ）
    relevance: float = 0.0  # 0-1 関連度
    excerpt: str = ""       # 短い抜粋（任意）


async def _http_get_json_with_retry(
    url: str,
    params: dict,
    headers: dict | None = None,
    api_name: str = "API",
) -> dict | None:
    """HTTP GET → JSON。失敗時 1 回リトライ。最終失敗で None.

    cold start や一時的接続失敗からの復活を狙う.
    """
    import asyncio as _aio
    last_error = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers=headers or {}) as client:
                r = await client.get(url, params=params)
                if r.status_code == 200:
                    return r.json()
                last_error = f"status={r.status_code} body={r.text[:160]}"
                if 500 <= r.status_code < 600 and attempt < RETRY_COUNT:
                    await _aio.sleep(0.5)
                    continue
                logger.warning("%s %s", api_name, last_error)
                return None
        except Exception as e:
            last_error = str(e)
            if attempt < RETRY_COUNT:
                logger.warning("%s attempt %d failed: %s — retrying", api_name, attempt + 1, e)
                await _aio.sleep(0.5)
                continue
            logger.exception("%s call failed after retries", api_name)
            return None
    if last_error:
        logger.warning("%s exhausted: %s", api_name, last_error)
    return None


async def search_google_fact_check(
    query: str,
    language_code: str = "ja",
    page_size: int = 5,
) -> list[EvidenceSource]:
    """Google Fact Check Tools API でクレームを検索.

    API キーが未設定なら空リスト返却（graceful）.
    """
    if not query or not query.strip():
        return []

    settings = get_settings()
    api_key = getattr(settings.gcp, "google_fact_check_api_key", "") or ""
    if not api_key:
        logger.debug("Google Fact Check API key not configured, skipping")
        return []

    params = {
        "query": query[:500],
        "languageCode": language_code,
        "pageSize": page_size,
        "key": api_key,
    }

    data = await _http_get_json_with_retry(FACT_CHECK_API, params, api_name="FactCheck")
    if data is None:
        return []

    out: list[EvidenceSource] = []
    for claim in data.get("claims", []):
        claim_text = claim.get("text", "")
        claimant = claim.get("claimant", "")
        for review in claim.get("claimReview", []):
            publisher = (review.get("publisher") or {}).get("name", "")
            url = review.get("url", "")
            rating = review.get("textualRating", "")
            title = review.get("title", "") or claim_text[:120]
            if not url:
                continue
            out.append(EvidenceSource(
                source_type="fact_check",
                publisher=publisher or "（不明）",
                title=title,
                url=url,
                rating=rating,
                relevance=0.9,
                excerpt=f"主張: {claim_text[:140]}（発言者: {claimant or '不明'}）" if claim_text else "",
            ))
    logger.info("Fact Check API hits=%d query=%s", len(out), query[:60])
    return out[:page_size]


# v0.4.7: Wikipedia 検索ノイズフィルタ（TF-IDF で関係ないアニメ・ゲーム記事ヒット対策）
WIKIPEDIA_NOISE_KEYWORDS = [
    # アニメ・特撮
    "仮面ライダー", "ウルトラマン", "ゴジラ", "戦隊", "プリキュア",
    "アニメ", "声優", "Vチューバー", "VTuber",
    # ゲーム
    "メタルギア", "ファイナルファンタジー", "ドラゴンクエスト",
    "ポケモン", "デジモン", "ガンダム", "マリオ", "ゼルダ",
    "PSYCHO-PASS", "サイコパス", "ペルソナ",
    "ブラック★ロックシューター", "センチュリオ",
    # バラエティ・TV
    "進め!電波少年", "クイズ", "ドラマ", "映画化",
    # 一般年代記事
    "平成", "昭和", "令和", "明治", "大正",
    # アーティスト・芸能
    "ジャニーズ", "AKB", "乃木坂", "アーティスト",
    # 🆕 v0.4.9: TF-IDF 誤ヒット典型例
    "登場キャラクター", "登場人物", "登場メカ", "シリーズ一覧",
    "東芝", "ソニー", "パナソニック",  # 一般大企業（フェイク文脈で関係性低）
    "覚醒剤", "薬物", "麻薬",  # 「マイクロチップ」「兵器」と誤マッチしがち
    "家畜", "畜産",  # tracking → 家畜
]


def _is_wiki_noise(title: str) -> bool:
    """Wikipedia 検索結果がフェイク主張の検証と無関係なエンタメ記事か判定."""
    if not title:
        return False
    return any(kw in title for kw in WIKIPEDIA_NOISE_KEYWORDS)


async def search_wikipedia(
    query: str,
    lang: str = "ja",
    page_size: int = 3,
) -> list[EvidenceSource]:
    """Wikipedia 検索 API で関連記事を取得（無料・登録不要）.

    主張の固有名詞・カテゴリで関連する Wikipedia 記事を引く.
    陰謀論・誇張広告は「○○陰謀論」「○○詐欺」などの記事にヒットしやすい.
    """
    if not query or not query.strip():
        return []

    endpoint = WIKIPEDIA_API_JA if lang == "ja" else WIKIPEDIA_API_EN
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query[:300],
        "srlimit": page_size,
        "format": "json",
        "utf8": "1",
    }
    data = await _http_get_json_with_retry(
        endpoint,
        params,
        headers={"User-Agent": "DeepFact-Validator/0.4 (+https://liberaiz.co.jp)"},
        api_name=f"Wikipedia({lang})",
    )
    if data is None:
        return []

    base_url = "https://ja.wikipedia.org/wiki/" if lang == "ja" else "https://en.wikipedia.org/wiki/"
    out: list[EvidenceSource] = []
    for hit in data.get("query", {}).get("search", []):
        title = hit.get("title", "")
        if not title:
            continue
        # 🆕 v0.4.7: アニメ・ゲーム・芸能等のノイズ記事を除外
        if _is_wiki_noise(title):
            logger.debug("Wikipedia noise filtered: %s", title)
            continue
        snippet = hit.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
        url = base_url + title.replace(" ", "_")
        out.append(EvidenceSource(
            source_type="wikipedia",
            publisher="Wikipedia",
            title=title,
            url=url,
            rating="",
            relevance=0.6,  # 0.7 → 0.6 に微減（公的機関 0.75 > Wikipedia 0.6 順位確立）
            excerpt=snippet[:140],
        ))
    logger.info("Wikipedia hits=%d query=%s", len(out), query[:60])
    return out[:page_size]


async def gather_evidence(
    claims: list[str],
    language_code: str = "ja",
) -> list[dict]:
    """複数 claim から第三者ソースを並列取得．

    claims リスト先頭から最大 3 件を **並列で** 全部叩き、
    重複 URL は排除し、relevance 降順に並べる.

    変更履歴 v0.4.1: 単一 claim だけだと抽象化されすぎた main_claim[0] が
        関係ない Wikipedia 記事をヒットさせる事故が発生したため、
        複数 claim 並列叩きで関連性精度を上げる.
    """
    if not claims:
        return []

    import asyncio

    valid_claims: list[str] = []
    seen: set[str] = set()
    for c in claims:
        if not c:
            continue
        q = c.strip()[:300]
        if not q or q in seen:
            continue
        seen.add(q)
        valid_claims.append(q)
        if len(valid_claims) >= 3:
            break

    if not valid_claims:
        return []

    has_english = any(_looks_like_english(c) for c in valid_claims)

    # 並列で複数 claim × 複数 API 叩く
    # 🆕 v0.4.2: Google Fact Check は ja + en 両方で叩く
    #    （Snopes/PolitiFact/FullFact 等は英語のフェイクチェックを多数持つ）
    tasks = []
    for q in valid_claims:
        tasks.append(search_google_fact_check(q, language_code="ja", page_size=3))
        tasks.append(search_google_fact_check(q, language_code="en", page_size=3))
        tasks.append(search_wikipedia(q, lang="ja", page_size=2))
        if has_english:
            tasks.append(search_wikipedia(q, lang="en", page_size=1))

    # v0.4.6: 全体タイムアウト 15s で「4 分応答」事故を抑制
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=15.0,
        )
    except asyncio.TimeoutError:
        logger.warning("evidence gather global timeout=15s reached")
        return []

    combined: list[EvidenceSource] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("evidence gather sub-task failed: %s", r)
            continue
        combined.extend(r)

    # URL 重複排除（先勝ち＝relevance 高い source_type 優先）
    seen_urls: set[str] = set()
    dedup: list[EvidenceSource] = []
    # fact_check を先に処理（relevance 0.9）→ wikipedia（0.7）の順
    combined.sort(key=lambda x: x.relevance, reverse=True)
    for src in combined:
        if src.url in seen_urls:
            continue
        seen_urls.add(src.url)
        dedup.append(src)

    return [asdict(s) for s in dedup[:8]]


def _looks_like_english(text: str) -> bool:
    if not text:
        return False
    ascii_chars = sum(1 for c in text if c.isascii() and (c.isalpha() or c.isspace()))
    return ascii_chars > len(text) * 0.5


def build_fallback_evidence(propaganda_categories: list[str], limit: int = 6) -> list[dict]:
    """API call が全失敗した時の fallback エビデンス.

    PROPAGANDA カテゴリから対応する反証ソースを返す.
    **公的機関・FC団体を優先 + Wikipedia を補助**で混合（社長指示・Wiki オンリー回避）.
    「最低限の判定エビデンス」を保証する.
    """
    out: list[EvidenceSource] = []
    seen_urls: set[str] = set()

    # 1. 公的機関・ファクトチェック団体（relevance 0.75・上位表示）
    for cat in propaganda_categories:
        for entry in PROPAGANDA_COUNTER_OFFICIAL.get(cat, []):
            url = entry.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            out.append(EvidenceSource(
                source_type="official_or_factcheck",
                publisher=entry.get("publisher", "（不明）"),
                title=entry.get("title", ""),
                url=url,
                rating="",
                relevance=0.75,
                excerpt=entry.get("excerpt", f"{cat} カテゴリ・公的検証ソース"),
            ))
            if len(out) >= limit:
                return [asdict(s) for s in out]

    # 2. Wikipedia 補助（relevance 0.55・下位表示）
    for cat in propaganda_categories:
        for entry in PROPAGANDA_COUNTER_WIKI.get(cat, []):
            url = entry.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            out.append(EvidenceSource(
                source_type="wikipedia_category",
                publisher="Wikipedia（カテゴリ反証）",
                title=entry.get("title", ""),
                url=url,
                rating="",
                relevance=0.55,
                excerpt=entry.get("excerpt", f"{cat} カテゴリ煽動表現の構造的反証記事"),
            ))
            if len(out) >= limit:
                return [asdict(s) for s in out]

    return [asdict(s) for s in out]
