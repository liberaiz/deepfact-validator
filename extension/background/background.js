/* DeepFact Validator background service worker (Manifest V3) */
chrome.runtime.onInstalled.addListener(() => {
  console.log("DeepFact Validator installed");
});

// ツールバーアイコン クリック → アクティブタブの content script に解析をトリガー
// （v1.1.7 で popup 廃止。バッジ 24h クローズ時もアイコンから再解析できる導線）
chrome.action.onClicked.addListener((tab) => {
  if (!tab || !tab.id) return;
  chrome.tabs.sendMessage(tab.id, { type: "ANALYZE_NOW" }, () => {
    // content script 未注入ページ（chrome://・about: 等）のエラーは無視
    void chrome.runtime.lastError;
  });
});
