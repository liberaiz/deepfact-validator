# 🎯 社長アクション チェックリスト（帰宅後）

**作成**：2026-06-18 19:50・レン
**目的**：DeepFact Validator 実機デプロイのために社長権限が必要な5本のアクション

---

## ✅ チェックリスト

### 1. Google AI Studio で GEMINI_API_KEY 発行

- 🔗 https://aistudio.google.com/app/apikey
- ログイン → 「Create API Key」
- 任意のプロジェクト or 新規作成
- 出力されたキーを安全な場所にコピー
- 終わったら 👉 レンに「GEMINI_API_KEY発行できた」と伝える（値はチャットに貼らない・Secret Managerに直接入れる）

### 2. LINE Developers Console で Channel 発行

- 🔗 https://developers.line.biz/console/
- Provider「Liberaiz」（既存）or 新規
- 「Messaging API」Channel を新規作成（仮称「DeepFact Validator」）
- 取得するもの：
  - Channel Access Token (Messaging API設定 → 発行ボタン)
  - Channel Secret
- 終わったら 👉 「LINE Channel発行できた」

### 3. GCP プロジェクト

#### A案：新規プロジェクト
```powershell
gcloud auth login
gcloud projects create deepfact-validator --name="DeepFact Validator"
gcloud config set project deepfact-validator
gcloud billing projects link deepfact-validator --billing-account=<BILLING_ACCOUNT_ID>
```

#### B案：既存プロジェクト相乗り（費用節約）
- 既存：`<YOUR_EXISTING_GCP_PROJECT_ID>`（GCP プロジェクト相乗り）
- Cloud Run サービス名を `deepfact-validator` で別立てするだけ
- レン推し＝**B案**（コスト最小・既存設定流用）

社長判断 👉 「A」or「B」

### 4. Secret Manager 登録

社長 PC のターミナルで（or レンが社長同席のもとで実行）：

```bash
echo -n "YOUR_GEMINI_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
echo -n "YOUR_LINE_ACCESS_TOKEN" | gcloud secrets create LINE_CHANNEL_ACCESS_TOKEN --data-file=-
echo -n "YOUR_LINE_SECRET" | gcloud secrets create LINE_CHANNEL_SECRET --data-file=-
```

⚠️ チャットには貼らない。ターミナルに直接打つ。

### 5. デプロイ実行

```bash
cd marketing/hackathon-2026/deepfact-validator
bash scripts/deploy.sh
```

5-10分でデプロイ完了。Cloud Run URL が出る。

### 6. LINE Webhook URL設定（デプロイ後）

LINE Developers Console → 該当 Channel → Messaging API設定
- Webhook URL: `https://<デプロイURL>/webhook/line`
- 「Webhookの利用」ON
- 「検証」ボタンで疎通確認

### 7. 友達追加QRで動作確認

LINE Developers Console → Messaging API設定 → QRコード
- 社長スマホで友達追加
- 任意のニュース記事URLを送信
- DeepFact Validator から信頼度スコア＋構造分析が返信 → ✅成功

---

## 想定所要時間

| ステップ | 時間 |
|---|---|
| 1. GEMINI_API_KEY | 3分 |
| 2. LINE Channel | 5分 |
| 3. GCPプロジェクト判断 | 1分 |
| 4. Secret Manager登録 | 3分 |
| 5. デプロイ実行 | 10分 |
| 6. Webhook URL設定 | 3分 |
| 7. 動作確認 | 5分 |
| **合計** | **約30分** |

---

## レンのサポート

帰宅後 社長が「家ついた」とチャットくれたら、レンが画面共有相当のサポートで：
- 各ステップを順番に案内
- エラー出たら即対応
- B案（既存社内プロダクトプロジェクト相乗り）採用なら Cloud Run設定の調整もレンが実施
