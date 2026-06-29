/* DeepFact Validator content script — Phase 2
 * 役割:
 *   - 開いたページの URL を検知（SPA 対応: pushState/replaceState/popstate + MutationObserver）
 *   - 記事相当のコンテンツ量があれば DeepFact API に投げて構造分析
 *   - 結果を右上のオーバーレイに常駐表示
 *   - ユーザーは ✕ で閉じる・popup から「再分析」できる
 *
 * 「リアルタイム能動介入」＝ユーザーが質問を投げる前に AI Agent から構造を可視化する
 */
(function () {
  if (window.__deepfactInjected) return;
  window.__deepfactInjected = true;

  const API_DEFAULT = "https://deepfact-validator-kjciocymea-an.a.run.app";
  const COOLDOWN_MS = 5000;
  const MIN_BODY_LENGTH = 600;
  const DEBOUNCE_MS = 800;

  let currentUrl = null;
  let overlay = null;
  let lastAnalyzeAt = 0;
  let debounceTimer = null;
  // HITL フィードバック: analyze 結果に紐付ける context（動画 F5/F6 で見せている UX）
  let lastRequestId = null;
  let lastAnalyzeContext = null; // { url_or_text, score, label }
  let feedbackModal = null;

  async function getConfig() {
    try {
      const { endpoint, enabled } = await chrome.storage.sync.get(["endpoint", "enabled"]);
      return {
        endpoint: endpoint || API_DEFAULT,
        enabled: enabled !== false,
      };
    } catch (e) {
      return { endpoint: API_DEFAULT, enabled: true };
    }
  }

  function escapeHtml(s) {
    if (typeof s !== "string") return "";
    return s.replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  function ensureFonts() {
    if (document.querySelector('link[data-deepfact-fonts]')) return;
    try {
      const preconnect1 = document.createElement("link");
      preconnect1.rel = "preconnect";
      preconnect1.href = "https://fonts.googleapis.com";
      preconnect1.setAttribute("data-deepfact-fonts", "1");
      document.head && document.head.appendChild(preconnect1);

      const preconnect2 = document.createElement("link");
      preconnect2.rel = "preconnect";
      preconnect2.href = "https://fonts.gstatic.com";
      preconnect2.crossOrigin = "anonymous";
      preconnect2.setAttribute("data-deepfact-fonts", "1");
      document.head && document.head.appendChild(preconnect2);

      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Shippori+Mincho+B1:wght@500;700;800&display=swap";
      link.setAttribute("data-deepfact-fonts", "1");
      document.head && document.head.appendChild(link);
    } catch (e) {
      // フォント注入失敗時はシステムフォントで継続
    }
  }

  function ensureOverlay() {
    if (overlay && document.documentElement.contains(overlay)) return overlay;
    ensureFonts();
    overlay = document.createElement("div");
    overlay.id = "deepfact-overlay";
    overlay.innerHTML = [
      '<div class="df-head">',
      '  <span class="df-brand">DeepFact</span>',
      '  <span class="df-status">分析中...</span>',
      '  <span class="df-close" title="閉じる">×</span>',
      "</div>",
      '<div class="df-body">',
      '  <div class="df-meter-block">',
      '    <div class="df-meter">',
      '      <svg class="df-meter-svg" viewBox="0 0 100 100" aria-hidden="true">',
      '        <circle class="df-meter-track" cx="50" cy="50" r="42" fill="none"></circle>',
      '        <circle class="df-meter-progress" cx="50" cy="50" r="42" fill="none"></circle>',
      "      </svg>",
      '      <div class="df-meter-center">',
      '        <span class="df-meter-label">—</span>',
      "      </div>",
      "    </div>",
      '    <div class="df-score-meta">',
      '      <span class="df-score-meta-label">信頼度</span>',
      '      <span class="df-score-value-mini">—</span>',
      '      <span class="df-score-icon">—</span>',
      "    </div>",
      "  </div>",
      '  <div class="df-summary"></div>',
      '  <h4 class="df-h4">構造観察</h4>',
      '  <ul class="df-obs"></ul>',
      '  <h4 class="df-h4">一次情報候補</h4>',
      '  <ul class="df-primary"></ul>',
      '  <h4 class="df-h4 df-evidence-heading">判定エビデンス・ソース</h4>',
      '  <div class="df-evidence"></div>',
      '  <div class="df-feedback-link-wrap">',
      '    <a class="df-feedback-link" href="#">この判定は誤りですか？ フィードバックする →</a>',
      "  </div>",
      "</div>",
    ].join("");
    document.documentElement.appendChild(overlay);

    overlay.querySelector(".df-close").addEventListener("click", () => {
      overlay.style.display = "none";
    });
    const fbLink = overlay.querySelector(".df-feedback-link");
    if (fbLink) {
      fbLink.addEventListener("click", (e) => {
        e.preventDefault();
        openFeedbackModal();
      });
    }
    return overlay;
  }

  // === HITL フィードバック モーダル（動画 F5/F6 で見せている 3択 UI）===
  function ensureFeedbackModal() {
    if (feedbackModal && document.documentElement.contains(feedbackModal)) return feedbackModal;
    feedbackModal = document.createElement("div");
    feedbackModal.id = "deepfact-feedback-modal";
    feedbackModal.innerHTML = [
      '<div class="df-fb-backdrop"></div>',
      '<div class="df-fb-dialog" role="dialog" aria-modal="true" aria-labelledby="df-fb-title">',
      '  <div class="df-fb-head">',
      '    <span class="df-fb-title" id="df-fb-title">この判定について</span>',
      '    <span class="df-fb-close" title="閉じる">×</span>',
      "  </div>",
      '  <div class="df-fb-body">',
      '    <p class="df-fb-question">この判定について、どう感じましたか？</p>',
      '    <div class="df-fb-options">',
      '      <button class="df-fb-opt" data-verdict="misjudge">✓ 誤判定だと思う</button>',
      '      <button class="df-fb-opt" data-verdict="warning_correct">警告は正しい</button>',
      '      <button class="df-fb-opt" data-verdict="unsure">よくわからない</button>',
      "    </div>",
      '    <p class="df-fb-note">フィードバックは匿名で記録されます。信頼ソース辞書の継続的改善（CI/CD）に使用されます。</p>',
      '    <p class="df-fb-done" style="display:none;">フィードバックを送信しました。ありがとうございます。</p>',
      "  </div>",
      "</div>",
    ].join("");
    document.documentElement.appendChild(feedbackModal);

    feedbackModal.querySelector(".df-fb-backdrop").addEventListener("click", closeFeedbackModal);
    feedbackModal.querySelector(".df-fb-close").addEventListener("click", closeFeedbackModal);
    feedbackModal.querySelectorAll(".df-fb-opt").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const verdict = e.currentTarget.getAttribute("data-verdict");
        // 選択 UI 反映
        feedbackModal.querySelectorAll(".df-fb-opt").forEach((b) => b.classList.remove("df-fb-opt-selected"));
        e.currentTarget.classList.add("df-fb-opt-selected");
        await sendFeedback(verdict);
      });
    });
    return feedbackModal;
  }

  function openFeedbackModal() {
    const m = ensureFeedbackModal();
    m.querySelector(".df-fb-done").style.display = "none";
    m.querySelectorAll(".df-fb-opt").forEach((b) => {
      b.classList.remove("df-fb-opt-selected");
      b.disabled = false;
    });
    m.style.display = "block";
  }

  function closeFeedbackModal() {
    if (feedbackModal) feedbackModal.style.display = "none";
  }

  async function sendFeedback(verdict) {
    const { endpoint } = await getConfig();
    const ctx = lastAnalyzeContext || {};
    const payload = {
      request_id: lastRequestId || "",
      verdict: verdict,
      url_or_text: ctx.url_or_text || location.href,
      score: typeof ctx.score === "number" ? ctx.score : null,
      label: ctx.label || "",
    };
    try {
      await fetch(endpoint + "/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      // ネットワーク失敗時も UX は完了表示（匿名フィードバック・retry なし）
    }
    if (feedbackModal) {
      feedbackModal.querySelectorAll(".df-fb-opt").forEach((b) => (b.disabled = true));
      feedbackModal.querySelector(".df-fb-done").style.display = "block";
    }
  }

  const DF_METER_CIRCUMFERENCE = 2 * Math.PI * 42; // 263.89

  const DF_LABEL_ICON = {
    "警告": "🚨",
    "低": "⚠️",
    "中": "〽️",
    "高": "✅",
  };

  function labelToBand(label) {
    if (label === "高") return "df-high";
    if (label === "中") return "df-mid";
    if (label === "低") return "df-low";
    return "df-warn";
  }

  function labelToIcon(label) {
    return DF_LABEL_ICON[label] || "🔍";
  }

  function setMeterProgress(o, pct, bandClass) {
    const ring = o.querySelector(".df-meter-progress");
    if (!ring) return;
    ring.setAttribute("stroke-dasharray", DF_METER_CIRCUMFERENCE.toFixed(2));
    ring.setAttribute("stroke-dashoffset", DF_METER_CIRCUMFERENCE.toFixed(2));
    ring.classList.remove("df-high", "df-mid", "df-low", "df-warn");
    ring.classList.add(bandClass);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        const offset = DF_METER_CIRCUMFERENCE * (1 - Math.max(0, Math.min(100, pct)) / 100);
        ring.setAttribute("stroke-dashoffset", offset.toFixed(2));
      });
    });
  }

  function renderResult(data, contextInput) {
    const o = ensureOverlay();
    o.style.display = "block";

    const cred = data.credibility || {};
    const pct = Math.round((cred.overall_score || 0) * 100);
    const label = cred.overall_label || "?";
    const bandClass = labelToBand(label);

    // HITL フィードバック紐付け: request_id + 判定 context を overlay に保持
    lastRequestId = data.request_id || data.requestId || null;
    lastAnalyzeContext = {
      url_or_text: contextInput || location.href,
      score: (cred.overall_score != null) ? cred.overall_score : null,
      label: label,
    };

    const meterLabel = o.querySelector(".df-meter-label");
    if (meterLabel) {
      meterLabel.textContent = label;
      meterLabel.classList.remove("df-high", "df-mid", "df-low", "df-warn");
      meterLabel.classList.add(bandClass);
    }

    const scoreVal = o.querySelector(".df-score-value-mini");
    if (scoreVal) {
      scoreVal.textContent = pct + "%";
      scoreVal.classList.remove("df-high", "df-mid", "df-low", "df-warn");
      scoreVal.classList.add(bandClass);
    }

    const scoreIcon = o.querySelector(".df-score-icon");
    if (scoreIcon) {
      scoreIcon.textContent = labelToIcon(label);
    }

    setMeterProgress(o, pct, bandClass);

    o.querySelector(".df-summary").textContent = data.summary || "";

    const obsList = (data.structural_observations || []).slice(0, 3);
    o.querySelector(".df-obs").innerHTML = obsList.length
      ? obsList.map((s) => "<li>" + escapeHtml(s) + "</li>").join("")
      : '<li class="df-empty">構造観察なし</li>';

    const psList = (data.primary_sources || []).slice(0, 3);
    o.querySelector(".df-primary").innerHTML = psList.length
      ? psList.map((s) => "<li>" + escapeHtml(s) + "</li>").join("")
      : '<li class="df-empty">記事中に信頼できる一次情報URLが見つかりません</li>';

    renderEvidenceSources(o, data.evidence_sources || []);

    o.querySelector(".df-status").textContent = "完了";
  }

  function ratingClass(rating) {
    if (!rating) return "";
    const r = String(rating).toLowerCase();
    if (/(虚偽|誤り|false|misleading|incorrect|fake|propaganda|warn)/.test(r)) return "df-rating-warn";
    if (/(正確|true|correct|accurate|safe)/.test(r)) return "df-rating-safe";
    if (/(一部|partial|mixed|疑|caution)/.test(r)) return "df-rating-accent";
    return "";
  }

  function renderEvidenceSources(o, sources) {
    const heading = o.querySelector(".df-evidence-heading");
    const container = o.querySelector(".df-evidence");
    if (!container) return;
    container.innerHTML = "";
    if (!sources || sources.length === 0) {
      heading && (heading.style.display = "none");
      return;
    }
    heading && (heading.style.display = "");
    sources.slice(0, 5).forEach((ev) => {
      const publisher = escapeHtml(ev.publisher || "（不明）");
      const rating = ev.rating || "";
      const title = escapeHtml((ev.title || "").slice(0, 80));
      const url = ev.url || "";
      const rClass = ratingClass(rating);
      const ratingHtml = rating
        ? '<span class="df-evidence-rating ' + rClass + '">' + escapeHtml(rating) + "</span>"
        : "";
      const card = document.createElement("a");
      card.className = "df-evidence-card";
      card.href = url || "#";
      card.target = "_blank";
      card.rel = "noopener noreferrer";
      card.innerHTML =
        '<div class="df-evidence-head">' +
          ratingHtml +
          '<span class="df-evidence-publisher">' + publisher + "</span>" +
        "</div>" +
        (title ? '<div class="df-evidence-title">' + title + "</div>" : "") +
        (url ? '<div class="df-evidence-url">' + escapeHtml(url) + "</div>" : "");
      container.appendChild(card);
    });
  }

  function setStatus(text) {
    const o = ensureOverlay();
    o.style.display = "block";
    const statusEl = o.querySelector(".df-status");
    if (!statusEl) return;
    // 「分析中...」のときはドット 3 つをアニメ化する
    if (text === "分析中..." || text === "分析中") {
      statusEl.innerHTML =
        '<span class="df-status-text">分析中</span>' +
        '<span class="df-status-dot">.</span>' +
        '<span class="df-status-dot">.</span>' +
        '<span class="df-status-dot">.</span>';
    } else {
      statusEl.textContent = text;
    }
  }

  function isLikelyArticle() {
    if (!document.body) return false;
    const textLen = (document.body.innerText || "").length;
    if (textLen < MIN_BODY_LENGTH) return false;
    // 検索結果ページ・ホーム・SPA ローディング状態は除外
    const path = location.pathname;
    if (path === "/" || path === "" || path === "/index.html") return false;
    return true;
  }

  async function analyzeCurrentPage(force) {
    const url = location.href;
    if (!url || url.startsWith("chrome://") || url.startsWith("about:")) return;

    const now = Date.now();
    if (!force && now - lastAnalyzeAt < COOLDOWN_MS) return;
    lastAnalyzeAt = now;

    const { endpoint, enabled } = await getConfig();
    if (!enabled) return;

    if (!isLikelyArticle()) return;

    setStatus("分析中...");

    try {
      const resp = await fetch(endpoint + "/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input_type: "url", payload: url }),
      });
      if (!resp.ok) {
        setStatus("エラー " + resp.status);
        return;
      }
      const data = await resp.json();
      renderResult(data);
    } catch (e) {
      setStatus("通信失敗");
    }
  }

  function checkUrlChange() {
    const url = location.href;
    if (url === currentUrl) return;
    currentUrl = url;
    // SPA 遷移後のレンダリング待ちを兼ねたデバウンス
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => analyzeCurrentPage(false), DEBOUNCE_MS);
  }

  // SPA history API hook
  const origPush = history.pushState;
  history.pushState = function () {
    origPush.apply(this, arguments);
    setTimeout(checkUrlChange, 200);
  };
  const origReplace = history.replaceState;
  history.replaceState = function () {
    origReplace.apply(this, arguments);
    setTimeout(checkUrlChange, 200);
  };
  window.addEventListener("popstate", () => setTimeout(checkUrlChange, 200));

  // 動的更新検知 (lightweight: 1.5s デバウンスで再評価)
  let observerTimer = null;
  const observer = new MutationObserver(() => {
    if (observerTimer) return;
    observerTimer = setTimeout(() => {
      observerTimer = null;
      checkUrlChange();
    }, 1500);
  });
  if (document.documentElement) {
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  }

  // メッセージリスナー (popup から)
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg) return;
    if (msg.type === "GET_DOM_TEXT") {
      // ⚠️ プライバシー対策：popup.js の sanitize と同じく input/textarea/password/contenteditable を除外
      try {
        const clone = document.body ? document.body.cloneNode(true) : null;
        if (!clone) {
          sendResponse({ html: "" });
          return true;
        }
        clone.querySelectorAll(
          'input, textarea, [contenteditable], [type="password"]'
        ).forEach((el) => el.remove());
        sendResponse({ html: clone.innerText || "" });
      } catch (e) {
        sendResponse({ html: "" });
      }
      return true;
    }
    if (msg.type === "ANALYZE_NOW") {
      analyzeCurrentPage(true);
      sendResponse({ ok: true });
      return true;
    }
  });

  // 初回起動
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(checkUrlChange, 2000));
  } else {
    setTimeout(checkUrlChange, 2000);
  }
})();
