/* DeepFact Validator — Workbench v1.1.7
 * Transplanted from extension/popup/popup.js (popup architecture deprecated).
 * - Same-origin API: serves from `/workbench` and posts to `/api/analyze` on same host.
 * - URLっぽい入力なら input_type:"url"、そうでなければ "text"。
 * - HITL feedback 3択モーダル: overlay (content.js L128-205) 同形式。
 */

const API_ENDPOINT = "https://deepfact-validator-kjciocymea-an.a.run.app";

const METER_CIRCUMFERENCE = 2 * Math.PI * 42; // 263.89

const LABEL_ICON = {
  "警告": "🚨",
  "低": "⚠️",
  "中": "〽️",
  "高": "✅",
};

// === サンプル chip 4種 (mockup と整合) ===
const SAMPLES = {
  public:
    "総務省統計局の労働力調査によると、2025年の完全失業率は2.6%で、前年と同水準でした。雇用情勢は緩やかな改善傾向が続いているとされています。詳細は https://www.stat.go.jp/data/roudou/ を参照してください。",
  experience:
    "私の知人が試したところ、3ヶ月で体重が10kg減ったそうです。続けるだけで誰でも痩せられる方法だと言っていました。本当に効果があるのか、試してみる価値があると思います。",
  emotional:
    "信じられない衝撃の事実が今、明らかに!!! あなたの健康を脅かす危険な食品が、知らないうちに食卓に並んでいます。今すぐ確認しないと手遅れになります。拡散希望、家族にも教えてあげてください。",
  propaganda:
    "3日でガンが消える奇跡の水を5万円で販売しています。副作用ゼロ。厚労省は隠蔽していますが、これが本当の真実です。拡散希望。",
};

// === HITL feedback context (analyze 結果に紐付け) ===
let lastRequestId = null;
let lastAnalyzeContext = null; // { url_or_text, score, label }

function labelToBand(label) {
  if (label === "高") return "high";
  if (label === "中") return "mid";
  if (label === "低") return "low";
  return "warn";
}

function labelToIcon(label) {
  return LABEL_ICON[label] || "🔍";
}

function escapeHtml(s) {
  if (s === undefined || s === null) return "";
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function setMeterProgress(pct, band) {
  const ring = document.getElementById("meter-progress");
  if (!ring) return;
  ring.setAttribute("stroke-dasharray", METER_CIRCUMFERENCE.toFixed(2));
  ring.setAttribute("stroke-dashoffset", METER_CIRCUMFERENCE.toFixed(2));
  ring.classList.remove("high", "mid", "low", "warn");
  ring.classList.add(band);
  // 初期値反映 → アニメーション
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      const offset = METER_CIRCUMFERENCE * (1 - Math.max(0, Math.min(100, pct)) / 100);
      ring.setAttribute("stroke-dashoffset", offset.toFixed(2));
    });
  });
}

function ratingClass(rating) {
  if (!rating) return "";
  const r = String(rating).toLowerCase();
  if (/(虚偽|誤り|false|misleading|incorrect|fake|propaganda|warn)/.test(r)) return "warn";
  if (/(正確|true|correct|accurate|safe)/.test(r)) return "safe";
  if (/(一部|partial|mixed|疑|caution)/.test(r)) return "accent";
  return "";
}

function isUrl(text) {
  if (!text) return false;
  const t = text.trim();
  return /^https?:\/\//i.test(t);
}

// === Analyze 実行 ===
async function analyzeContent() {
  const input = document.getElementById("compose-input");
  const btn = document.getElementById("btn-analyze");
  const hint = document.getElementById("compose-hint");
  const status = document.getElementById("report-status");
  const loadingBlock = document.getElementById("loading-block");
  const emptyBlock = document.getElementById("empty-block");
  const resultBlock = document.getElementById("result-block");

  const text = (input.value || "").trim();
  if (!text) {
    hint.textContent = "解析対象を入力してください。";
    return;
  }
  hint.textContent = "";

  // UI を loading 状態へ
  btn.disabled = true;
  status.textContent = "解析中";
  emptyBlock.style.display = "none";
  resultBlock.style.display = "none";
  loadingBlock.style.display = "block";

  const inputType = isUrl(text) ? "url" : "text";

  try {
    const resp = await fetch(`${API_ENDPOINT}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_type: inputType,
        payload: text,
      }),
    });
    if (!resp.ok) {
      const t = await resp.text();
      throw new Error(`API error ${resp.status}: ${t}`);
    }
    const data = await resp.json();
    renderResult(data, text);
    status.textContent = "3-agent · 並列分析完了";
  } catch (e) {
    hint.textContent = "解析失敗: " + (e && e.message ? e.message : String(e));
    status.textContent = "失敗";
    emptyBlock.style.display = "block";
  } finally {
    loadingBlock.style.display = "none";
    btn.disabled = false;
  }
}

function renderResult(data, contextInput) {
  const resultBlock = document.getElementById("result-block");
  resultBlock.style.display = "flex";

  const cred = data.credibility || {};
  const pct = Math.round((cred.overall_score || 0) * 100);
  const label = cred.overall_label || "?";
  const band = labelToBand(label);

  // HITL feedback 紐付け
  lastRequestId = data.request_id || data.requestId || null;
  lastAnalyzeContext = {
    url_or_text: contextInput || "",
    score: (cred.overall_score != null) ? cred.overall_score : null,
    label: label,
  };

  // Meter ラベル
  const meterLabel = document.getElementById("meter-label");
  if (meterLabel) {
    meterLabel.textContent = label;
    meterLabel.classList.remove("high", "mid", "low", "warn");
    meterLabel.classList.add(band);
  }

  // Verdict rows
  const scoreEl = document.getElementById("verdict-score");
  if (scoreEl) {
    scoreEl.textContent = pct + "%";
    scoreEl.classList.remove("high", "mid", "low", "warn");
    scoreEl.classList.add(band);
  }
  const iconEl = document.getElementById("verdict-icon");
  if (iconEl) {
    iconEl.textContent = labelToIcon(label);
  }
  const sourceEl = document.getElementById("verdict-source");
  if (sourceEl) sourceEl.textContent = (cred.source_credibility || 0).toFixed(2);
  const neutralEl = document.getElementById("verdict-neutral");
  if (neutralEl) neutralEl.textContent = (cred.position_bias || 0).toFixed(2);
  const factEl = document.getElementById("verdict-fact");
  if (factEl) factEl.textContent = (cred.fact_consistency || 0).toFixed(2);

  setMeterProgress(pct, band);

  // Headline = 要約の先頭 80字 (mockup の verdict-headline 位置)
  const headlineEl = document.getElementById("verdict-headline");
  if (headlineEl) {
    const summary = data.summary || "";
    headlineEl.textContent = summary.length > 100 ? summary.slice(0, 100) + "…" : summary;
  }

  // Summary 本文
  const summaryEl = document.getElementById("summary-text");
  if (summaryEl) summaryEl.textContent = data.summary || "";

  // 構造観察
  const obsList = document.getElementById("obs-list");
  obsList.innerHTML = "";
  const obs = data.structural_observations || [];
  if (obs.length === 0) {
    obsList.innerHTML = '<li>構造観察なし</li>';
  } else {
    obs.forEach((o) => {
      const li = document.createElement("li");
      li.textContent = o;
      obsList.appendChild(li);
    });
  }

  // 一次情報
  const psList = document.getElementById("primary-list");
  psList.innerHTML = "";
  const ps = data.primary_sources || [];
  if (ps.length === 0) {
    psList.innerHTML = '<li class="empty">本文に信頼できる一次情報URLが見当たりません。</li>';
  } else {
    ps.forEach((p) => {
      const li = document.createElement("li");
      li.textContent = p;
      psList.appendChild(li);
    });
  }

  // 判定エビデンス
  renderEvidenceSources(data.evidence_sources || []);
}

function renderEvidenceSources(sources) {
  const section = document.getElementById("evidence-section");
  const stack = document.getElementById("evidence-stack");
  if (!stack) return;
  stack.innerHTML = "";
  if (!sources || sources.length === 0) {
    if (section) section.style.display = "none";
    return;
  }
  if (section) section.style.display = "flex";
  sources.slice(0, 6).forEach((ev) => {
    const publisher = ev.publisher || "(不明)";
    const rating = ev.rating || "";
    const title = (ev.title || "").slice(0, 120);
    const url = ev.url || "";
    const rClass = ratingClass(rating);

    const a = document.createElement("a");
    a.className = "evi";
    a.href = url || "#";
    a.target = "_blank";
    a.rel = "noopener noreferrer";

    const ratingSpan = document.createElement("span");
    ratingSpan.className = "evi-rating" + (rClass ? " " + rClass : "");
    ratingSpan.textContent = rating || "—";

    const body = document.createElement("div");
    body.className = "evi-body";
    const pub = document.createElement("span");
    pub.className = "evi-publisher";
    pub.textContent = publisher;
    body.appendChild(pub);
    if (title) {
      const t = document.createElement("span");
      t.className = "evi-title";
      t.textContent = title;
      body.appendChild(t);
    }

    const urlSpan = document.createElement("span");
    urlSpan.className = "evi-url";
    urlSpan.textContent = url || "";

    a.appendChild(ratingSpan);
    a.appendChild(body);
    a.appendChild(urlSpan);
    stack.appendChild(a);
  });
}

// === HITL Feedback Modal (overlay と同じ 3択構造) ===
function openFeedbackModal() {
  const modal = document.getElementById("feedback-modal");
  if (!modal) return;
  // 状態リセット
  modal.querySelector(".fb-done").style.display = "none";
  modal.querySelectorAll(".fb-opt").forEach((b) => {
    b.classList.remove("fb-opt-selected");
    b.disabled = false;
  });
  modal.style.display = "block";
}

function closeFeedbackModal() {
  const modal = document.getElementById("feedback-modal");
  if (modal) modal.style.display = "none";
}

async function sendFeedback(verdict) {
  const ctx = lastAnalyzeContext || {};
  const payload = {
    request_id: lastRequestId || "",
    verdict: verdict,
    url_or_text: ctx.url_or_text || "",
    score: typeof ctx.score === "number" ? ctx.score : 0.0,
    label: ctx.label || "",
  };
  try {
    await fetch(`${API_ENDPOINT}/api/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    // ネットワーク失敗時も UX は完了表示 (匿名フィードバック・retry なし)
  }
  const modal = document.getElementById("feedback-modal");
  if (modal) {
    modal.querySelectorAll(".fb-opt").forEach((b) => (b.disabled = true));
    modal.querySelector(".fb-done").style.display = "block";
    modal.querySelector(".fb-done").textContent = "フィードバックを送信しました。ありがとうございます。";
  }
}

// === Sample chip クリック ===
function attachSampleChips() {
  const chips = document.querySelectorAll(".sample-chip");
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const key = chip.getAttribute("data-sample");
      const text = SAMPLES[key];
      if (!text) return;
      const input = document.getElementById("compose-input");
      if (input) {
        input.value = text;
        input.focus();
      }
      chips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
    });
  });
}

// === Init ===
document.addEventListener("DOMContentLoaded", () => {
  attachSampleChips();

  const btn = document.getElementById("btn-analyze");
  if (btn) btn.addEventListener("click", analyzeContent);

  const fbLink = document.getElementById("feedback-link");
  if (fbLink) {
    fbLink.addEventListener("click", (e) => {
      e.preventDefault();
      openFeedbackModal();
    });
  }

  const modal = document.getElementById("feedback-modal");
  if (modal) {
    modal.querySelector(".fb-backdrop").addEventListener("click", closeFeedbackModal);
    modal.querySelector(".fb-close").addEventListener("click", closeFeedbackModal);
    modal.querySelectorAll(".fb-opt").forEach((b) => {
      b.addEventListener("click", async (e) => {
        const verdict = e.currentTarget.getAttribute("data-verdict");
        modal.querySelectorAll(".fb-opt").forEach((x) => x.classList.remove("fb-opt-selected"));
        e.currentTarget.classList.add("fb-opt-selected");
        await sendFeedback(verdict);
      });
    });
  }
});
