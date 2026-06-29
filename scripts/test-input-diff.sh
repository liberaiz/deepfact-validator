#!/usr/bin/env bash
# 入力差テスト: フェイク主張 / 一次情報URL / 中立報道風 / 誇張広告 で信頼度スコアに有意な差が出るか機械検証

URL="${DEEPFACT_URL:-https://deepfact-validator-kjciocymea-an.a.run.app/api/analyze}"
OUTPUT_DIR="${OUTPUT_DIR:-./test-results}"
mkdir -p "$OUTPUT_DIR"

run_test() {
  local name="$1"
  local type="$2"
  local payload="$3"
  local out="$OUTPUT_DIR/${name}.json"

  echo "=================================================="
  echo "=== $name ==="
  echo "type: $type"
  echo "payload: ${payload:0:80}..."
  echo "=================================================="

  curl -s -X POST -H "Content-Type: application/json" \
    -d "$(jq -n --arg t "$type" --arg p "$payload" '{input_type:$t, payload:$p}')" \
    "$URL" > "$out"

  echo "-- 結果サマリ --"
  jq '{
    overall_score: .credibility.overall_score,
    overall_label: .credibility.overall_label,
    source_credibility: .credibility.source_credibility,
    position_bias_neutrality: .credibility.position_bias,
    fact_consistency: .credibility.fact_consistency,
    structural_observations_count: (.structural_observations | length),
    contrarian_views_count: (.contrarian_views | length),
    primary_sources_count: (.primary_sources | length),
    summary_head: .summary[0:200]
  }' "$out"
  echo ""
}

# パターン1: フェイク主張（ロシアプロパガンダ系）
run_test "01-fake-claim" "text" "ウクライナ東部でウクライナ政府軍によるロシア系住民のジェノサイド（集団殺害）が起きていると主張。証拠は示されていないが事実だ。"

# パターン2: 厚労省一次情報URL
run_test "02-mhlw-primary" "url" "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryouhoken/iryouhoken01/index.html"

# パターン3: 中立報道風テキスト
run_test "03-neutral-news" "text" "政府は2026年6月、医療制度改革に関する新たな指針を発表した。指針には診療報酬体系の見直しが含まれており、関係団体からは賛否両論の声が上がっている。厚生労働省によると2027年度から段階的に施行される。"

# パターン4: 誇張広告テキスト
run_test "04-hype-ad" "text" "たった3日でガンが消えた！医師も驚愕の奇跡のサプリ、今だけ50%OFF！購入はこちら。副作用なし、すべての癌に効きます。"

echo "=================================================="
echo "全パターン完了。結果は $OUTPUT_DIR/*.json"
echo "比較表:"
echo "=================================================="
for f in "$OUTPUT_DIR"/*.json; do
  name=$(basename "$f" .json)
  jq -r --arg n "$name" '
    [$n,
     (.credibility.overall_label // "?"),
     ((.credibility.overall_score // 0) * 100 | tostring + "%"),
     (.credibility.source_credibility // 0 | tostring),
     (.credibility.position_bias // 0 | tostring),
     (.credibility.fact_consistency // 0 | tostring)
    ] | @tsv
  ' "$f"
done | column -t -s "$(printf '\t')"
