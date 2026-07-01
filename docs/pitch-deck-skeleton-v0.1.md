# DeepFact Validator ピッチデック骨子 v0.1

**最終更新**：2026-06-18 18:45
**ステータス**：v0.1（骨格・hallmark経由HTML化待ち）

---

## 構成（5分ピッチ・8スライド）

### Slide 1：タイトル & 一行ピッチ（30秒）

**ビジュアル**：紺地に白文字「DeepFact Validator」／金文字「情報のObservability」／医師バッジ＋Anthropic Certified三冠

**話す**：
> 「ChatGPTに『この記事本当?』と聞くには、まず疑問を持たないといけません。
> でも、騙されている人は疑問を持ちません。
> だから AIエージェントが**質問される前に介入**します。
> 私は医師です。診断は必ず一次情報を確認します。この習慣を、AIエージェントで社会全体に拡張します。」

---

### Slide 2：課題（60秒）

**4ブロックグリッド**：
- 🚨 情報過多：1日13本のニュース・取捨選択不能
- ⚠️ 「気づかない」問題：騙されている人は疑問を持たない＝チャットボットでは助けられない
- 💸 影響：年間500億の特殊詐欺被害（消費者庁）
- 🌐 既存ファクトチェックの限界：人手判定×静的スコア×ユーザーが見にいかないと使えない

**話す**：
> 「情報過多の時代。でも、気づかないまま騙されているのが現実です。」

---

### Slide 3：「素のGemini で代替不可」5基準（30秒・先回り回答）

| # | 基準 | 実装 |
|---|---|---|
| ① | 状態継続 | Postmortem で直近24h履歴可視化 |
| ② | 外部連携 | 信頼ソース辞書20+件（Firestore + URL展開） |
| ③ | 専門深さ | ドメイン分類×カテゴリ（学術/政府/メディア/データ） |
| ④ | HITL | Human-in-the-Loop（構造分析提示・断定回避） |
| ⑤ | 業務自動化 | 3エージェント→記録の多段 |

---

### Slide 4：ライブデモ（120秒）

**3デモ並列**：
1. LINE Bot（仕込みなし・QR→友達追加→URL貼り付け→3秒で返信）
2. Chrome Extension（任意ニュースサイト→1クリック→構造分析表示）
3. Postmortem（直近24h履歴の SRE風振り返り）

---

### Slide 5：技術構成（30秒）

**アーキテクチャ図**：
```
[Chrome Extension]     [LINE Bot]
       │                  │
       └──────┬───────────┘
              ↓
      [Cloud Run + FastAPI]
              ↓
   Watcher → Investigator → Validator
              ↓
   [Vertex Vector Search] [Firestore]
              ↓
   [Cloud Logging Observability]
              ↓
    Postmortem 自動生成
```

**「DevOpsフレーム = 情報のObservability」**

---

### Slide 6：「人ではなく構造を見る」哲学（30秒）

**Before / After**：
- ❌ 旧来：「このジャーナリストは○○から金もらってる」（発信者個人への断定的指摘・名誉毀損）
- ✅ DeepFact：「この記事の出所と過去発言には XX という構造的関係がある」（構造分析）

**発信者個人・組織への断定的指摘を避け、情報構造を可視化する設計。**

---

### Slide 7：効果（30秒）

**実装上の根拠** （実測は Cloud Run デプロイ後）:
- 記事1件あたり 3秒で分析完了
- 信頼ソース20+件×4カテゴリでカバー
- LINE Bot QR1スキャンで誰でも利用開始
- Chrome Extension Manifest V3で常時稼働

---

### Slide 8：チーム & 出口戦略（30秒）

**社長プロフィール**：医師・医学博士・元院長・Anthropic Certified三冠
**「医師が一次情報まで追う習慣」を AI Agent で社会拡張**

**出口**：
- 受賞 → 「Anthropic三冠×情報リテラシー」のブランド権威
- 落選 → note記事「DeepFact Validator開発体験記」「情報のObservability」シリーズ

---

## デザイン方針

- 紺#1B2A4E × 金#C9A55C × オフ白#F8F6F1
- 游ゴシック・数字は欧文等幅
- 8スライド 1920×1080
- hallmark anti-slop通過
- 図句読点ゼロ

## hallmark経由HTML化（次フェーズ）

入力：`pitch-deck-skeleton-v0.1.md`
出力：`pitch/deepfact-validator-pitch-v0.1.html`
