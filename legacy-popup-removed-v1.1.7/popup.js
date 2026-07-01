/* DeepFact Validator popup client */

const API_ENDPOINT_DEFAULT = "https://deepfact-validator-kjciocymea-an.a.run.app";

async function getEndpoint() {
  const { endpoint } = await chrome.storage.sync.get(["endpoint"]);
  return endpoint || API_ENDPOINT_DEFAULT;
}

const METER_CIRCUMFERENCE = 2 * Math.PI * 42; // 263.89

const LABEL_ICON = {
  "警告": "🚨",
  "低": "⚠️",
  "中": "〽️",
  "高": "✅",
};

function labelToBand(label) {
  if (label === "高") return "high";
  if (label === "中") return "mid";
  if (label === "低") return "low";
  return "warn";
}

function labelToIcon(label) {
  return LABEL_ICON[label] || "🔍";
}

function setScoreClass(elem, label) {
  elem.classList.remove("high", "mid", "low", "warn");
  elem.classList.add(labelToBand(label));
}

function setMeterProgress(pct, band) {
  const ring = document.getElementById("meter-progress");
  if (!ring) return;
  ring.setAttribute("stroke-dasharray", METER_CIRCUMFERENCE.toFixed(2));
  ring.setAttribute("stroke-dashoffset", METER_CIRCUMFERENCE.toFixed(2));
  ring.classList.remove("high", "mid", "low", "warn");
  ring.classList.add(band);
  // ブラウザに初期値を反映させてからアニメーション
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      const offset = METER_CIRCUMFERENCE * (1 - Math.max(0, Math.min(100, pct)) / 100);
      ring.setAttribute("stroke-dashoffset", offset.toFixed(2));
    });
  });
}

async function analyzeCurrentTab() {
  const loading = document.getElementById("loading");
  const result = document.getElementById("result");
  loading.classList.remove("hidden");
  result.classList.add("hidden");

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url) throw new Error("アクティブタブが取得できません");

    // ⚠️ プライバシー対策：DOM 抽出時に input/textarea/password フィールドの値は除外する.
    //    パスワード・個人情報フォームの内容はサーバーに送信しない設計.
    //    Phase 3 で sanitize ロジックを更に強化予定.
    let domText = "";
    try {
      const [{ result: domDump }] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          const clone = document.body ? document.body.cloneNode(true) : null;
          if (!clone) return "";
          clone.querySelectorAll(
            'input, textarea, [contenteditable], [type="password"]'
          ).forEach((el) => el.remove());
          return clone.innerText || "";
        },
      });
      domText = domDump || "";
    } catch (e) {
      console.warn("本文抽出失敗:", e);
    }

    const endpoint = await getEndpoint();
    const resp = await fetch(`${endpoint}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_type: domText ? "dom" : "url",
        payload: domText || tab.url,
      }),
    });
    if (!resp.ok) {
      const t = await resp.text();
      throw new Error(`API error ${resp.status}: ${t}`);
    }
    const data = await resp.json();
    renderResult(data);
  } catch (e) {
    alert("解析失敗: " + e.message);
  } finally {
    loading.classList.add("hidden");
  }
}

function renderResult(data) {
  const result = document.getElementById("result");
  result.classList.remove("hidden");

  const meterLabel = document.getElementById("meter-label");
  const scoreValue = document.getElementById("score-value");
  const scoreIcon = document.getElementById("score-icon");
  const cred = data.credibility || {};
  const pct = Math.round((cred.overall_score || 0) * 100);
  const label = cred.overall_label || "?";
  const band = labelToBand(label);

  if (meterLabel) {
    meterLabel.textContent = label;
    meterLabel.classList.remove("high", "mid", "low", "warn");
    meterLabel.classList.add(band);
  }

  if (scoreValue) {
    scoreValue.textContent = pct + "%";
    setScoreClass(scoreValue, label);
  }

  if (scoreIcon) {
    scoreIcon.textContent = labelToIcon(label);
  }

  setMeterProgress(pct, band);

  document.getElementById("summary").textContent = data.summary || "";

  const obsList = document.getElementById("observations");
  obsList.innerHTML = (data.structural_observations || [])
    .map((o) => `<li>${o}</li>`)
    .join("");

  const psList = document.getElementById("primary-sources");
  psList.innerHTML = (data.primary_sources || [])
    .map((p) => `<li>${escapeHtml(p)}</li>`)
    .join("") || `<li>記事中に信頼できる一次情報URLが見つかりません</li>`;

  renderEvidenceSources(data.evidence_sources || []);
}

function escapeHtml(s) {
  if (s === undefined || s === null) return "";
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function ratingClass(rating) {
  if (!rating) return "";
  const r = String(rating).toLowerCase();
  if (/(虚偽|誤り|false|misleading|incorrect|fake|propaganda|warn)/.test(r)) return "warn";
  if (/(正確|true|correct|accurate|safe)/.test(r)) return "safe";
  if (/(一部|partial|mixed|疑|caution)/.test(r)) return "accent";
  return "";
}

function renderEvidenceSources(sources) {
  const heading = document.getElementById("evidence-heading");
  const container = document.getElementById("evidence-sources");
  if (!container) return;
  container.innerHTML = "";
  if (!sources || sources.length === 0) {
    heading && heading.classList.add("hidden");
    return;
  }
  heading && heading.classList.remove("hidden");
  sources.slice(0, 6).forEach((ev) => {
    const publisher = escapeHtml(ev.publisher || "（不明）");
    const rating = ev.rating || "";
    const title = escapeHtml((ev.title || "").slice(0, 100));
    const url = ev.url || "";
    const rClass = ratingClass(rating);
    const ratingHtml = rating
      ? `<span class="evidence-rating ${rClass}">${escapeHtml(rating)}</span>`
      : "";
    const card = document.createElement("a");
    card.className = "evidence-card";
    card.href = url || "#";
    card.target = "_blank";
    card.rel = "noopener noreferrer";
    card.innerHTML = `
      <div class="evidence-card-head">
        ${ratingHtml}
        <span class="evidence-publisher">${publisher}</span>
      </div>
      ${title ? `<div class="evidence-title">${title}</div>` : ""}
      ${url ? `<div class="evidence-url">${escapeHtml(url)}</div>` : ""}
    `.trim();
    container.appendChild(card);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("analyze-current").addEventListener("click", analyzeCurrentTab);
});
