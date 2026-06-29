# DeepFact Validator — コンテスト提出物インデックス

**DevOps × AI Agent Hackathon 2026**（Findy／Google Cloud Japan協賛）
**提出締切：** 2026-07-10 23:59 JST
**応募方法：** 3 STEP（参加申込 → Proto Pedia 登録 → 作品提出フォーム）
**一次情報：** https://findy.notion.site/devops-ai-agent-hackathon-2026

**提出URL:**
- 📦 **GitHub**: https://github.com/liberaiz/deepfact-validator
- 🚀 **Live**: https://deepfact-validator-kjciocymea-an.a.run.app
- 🔄 **CI/CD**: https://github.com/liberaiz/deepfact-validator/actions/workflows/validate-trust-sources.yml

---

## 📋 必須要件（Notion 一次情報・2026-06-22 確認）

### 必須①：Google Cloud アプリケーション実行プロダクト（1つ以上選択）

| 選択肢 | DeepFact 採用 |
|---|:---:|
| App Engine・Google Compute Engine | — |
| Google Kubernetes Engine (GKE) | — |
| **Cloud Run・Cloud Functions** | ✅ **採用**（rev `deepfact-validator-00008+`） |
| Cloud TPU / GPU | — |

### 必須②：Google Cloud AI 技術（1つ以上選択）

| 選択肢 | DeepFact 採用 |
|---|:---:|
| **Gemini Enterprise Agent Platform（旧 Vertex AI）** | ✅ **採用**（Gemini 2.5-flash via `vertexai=True`） |
| Gemini API | — |
| Gemma・Imagen・Agent Builder | — |
| ADK（Agents Development Kit） | — |
| Speech-to-Text / Text-to-Speech API | — |
| Vision AI API・Natural Language AI API | — |
| Translation AI API | — |

### 任意：その他の技術
- Flutter / Firebase / Veo / Elasticsearch（スポンサー）／その他任意

---

## 📤 応募 3 STEP

| STEP | 内容 | 状態 | 担当 |
|:---:|---|:---:|:---:|
| ① | **ハッカソンへの参加申し込み** | ⏳社長確認要 | 社長 |
| ② | **作品をつくって Proto Pedia に登録** | ⏳社長 GO 待ち | 社長 + レン |
| ③ | **作品提出フォームから最終応募** | ⏳STEP②後 | 社長 + レン |

---

## 🎯 審査基準 5項目への対応度

| # | 審査基準 | DeepFact の対応 |
|---|---|---|
| 1 | **AIエージェントが価値の中心**（自律的振る舞い・必然性） | ✅ Watcher→Investigator→Validator の 3 エージェント自律連携 + **公的機関 URL 能動取得**（厚労省/PMDA/WHO/CDC + JFC/Snopes/Reuters Fact Check 等の IFCN 加盟団体）。素の Gemini で代替不可 |
| 2 | **課題アプローチ力**（ストーリー一貫性・妥当性・新規性） | ✅ 医師（創業者）の「真偽は一次情報まで辿る」北極星を AI Agent で社会拡張。誤情報問題への新規アプローチ |
| 3 | **ユーザビリティ** | ✅ LINE Bot（友達追加だけ・**🚨/⚠️/〽️/✅ 信頼度アイコン + 📚 判定エビデンス URL 付き返信**・即時 reply + push_message）+ Chrome Extension + HTTP API |
| 4 | **実用性・体験価値**（突き抜けたら加点） | ✅ 6 パターン信頼度差 78pt + **同一入力完全一致**（Firestore キャッシュ）+ **公的機関ソース上位常時表示**（Wikipedia オンリー構造排除）+ リアルタイム能動介入 |
| 5 | **実装力**（納得度・拡張性・実運用配慮） | ✅ Vertex AI 切替で本番運用適格・**Firestore キャッシュで同一入力一致保証**（`temperature=0+seed=42+top_k=1` はベストエフォート + Gemini 各 call 30s timeout）+ **125 ドメイン信頼辞書 + 143 煽動キーワード辞書 + Wikipedia/Fact Check ja+en 並列叩き + Wiki noise filter + 永続 event loop** + Cloud Logging Observability + SRE 流 Postmortem |

---

## 📦 提出物 一覧（既完成）

| # | 項目 | 状態 | 所在地 |
|---|---|:---:|---|
| A | デプロイ済プロジェクト URL | ✅完成 | `https://deepfact-validator-kjciocymea-an.a.run.app` |
| B | ピッチ HTML 本体 v0.4 | ✅完成 | `../pitch/deepfact-validator-pitch-v0.4.html` |
| C | 実機検証エビデンス v0.3 | ✅完成 | `../pitch/demo-evidence-v0.3.html` |
| D | 6パターン信頼度判定結果 | ✅完成 | `../test-results/v0.3/01〜06-result.json` + `summary-table.md` |
| E | README（v0.3 セクション追記済） | ✅完成 | `../README.md` |
| F | アーキテクチャ図 | ✅完成 | demo-evidence v0.3 内に組込済 + README 内 |
| G | 1枚サマリ（審査員向け） | ✅完成 | `./1pager.md` |
| H | 提出チェックリスト | ✅完成 | `./SUBMISSION-CHECKLIST.md` |

---

## 🚨 社長確認 / 判断ポイント

| # | 項目 | 内容 |
|---|---|---|
| 1 | **STEP①参加申込状況** | 既に申込済みか？ 未申込なら参加申込フォームで申込必要 |
| 2 | **Proto Pedia 登録 GO**（STEP②） | 社長アカウント作成 + 作品掲載（外部公開・不可逆） |
| 3 | **作品提出フォーム入力 GO**（STEP③） | Notion 内のフォーム URL から提出 |
| 4 | **GitHub 公開要否** | Notion「ルール」タブ等に明記があるか追加スクショ要 |
| 5 | **デモ動画 要否** | Notion「ルール」タブ等に明記があるか追加スクショ要 |
| 6 | **ピッチ資料 要否** | Notion「ルール」タブ等に明記があるか追加スクショ要 |

---

## 📅 公式スケジュール（Notion 一次情報）

| 日程 | イベント | 備考 |
|---|---|---|
| 2026/6/7（日）13:00 | チームビルディングイベント | 個人参加可能・終了済 |
| 2026/6月 上旬〜下旬 | Boot Camp | 開催中（社長参加状況要確認） |
| **2026/7/10（金）23:59** | **プロジェクト提出〆切** | Proto Pedia 経由提出 |
| 2026/7/13（月）〜 | 一次審査 | ハッカソン運営事務局による審査 |
| 2026/7/21〜 | 二次審査 | 外部有識者による審査 |
| 2026/7/30（木） | 受賞者・決勝進出者告知 | Google Cloud Japan ブログ + 二次審査通過 10 チームへ個別通知 |
| **2026/8/19（水）** | **最終発表** | **渋谷 Google オフィス（東京都渋谷区渋谷 3-21-3 渋谷ストリーム）現地登壇** |
| 2026/9月予定 | アフターイベント | 優秀賞外でも審査員注目チームが登壇可能 |

## 📁 質担保スケジュール（7/10 締切から逆算）

| 日 | アクション | 担当 |
|---|---|:---:|
| 6/22-6/30 | 🛡️ アルゴス L2 独立目チェック × 1 周目 + Chrome Extension 実装推進 + 質担保 | レン |
| 6/22-6/30 | Boot Camp 録画/資料 確認 + Proto Pedia アカウント作成 | 社長 |
| 7/1-7/5 | 🛡️ アルゴス L2 独立目チェック × 2 周目 + デモ動画作成（必要なら） | レン + 社長 |
| 7/6-7/8 | Proto Pedia 登録（STEP②）+ 社長最終味見（PC + iPhone Safari） | 社長 + レン |
| 7/9 | STEP① 参加申込（未済の場合）+ STEP③ 作品提出フォーム 入力 | 社長 + レン |
| **7/10 23:59** | **提出締切** | — |
| 7/13-7/21 | 一次審査・二次審査期間（応答可能体制維持） | レン |
| 7/30 | 結果告知 | — |
| **8/19** | **最終発表（社長現地登壇）** | 社長 |

---

## 関連 memory

- [[project_hackathon_deepfact_validator]] プロジェクト memory
- [[feedback_distribution_autonomy]] 外部公開の承認ゲート
- [[feedback_dont_call_skeleton_working]] 機械検証必須原則（v0.3 で78pt差＋同入力完全一致 達成済）
- [[feedback_argus_double_check]] 🛡️アルゴス L2 ダブルチェック
- [[feedback_primary_source_mandatory]] 一次情報マスト（V29 朝の Notion スクショで確定）
