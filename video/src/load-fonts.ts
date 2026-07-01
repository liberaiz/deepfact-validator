import { loadFont as loadCormorantGaramond } from "@remotion/google-fonts/CormorantGaramond";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";

// 日本語フォントはネットワーク取得を廃止し、OS 搭載のシステムフォントを使う
// （ShipporiMinchoB1 の 360+ リクエストで ERR_INSUFFICIENT_RESOURCES が発生するため）
// Windows: Yu Mincho / YuMincho  ← Remotion 実行環境に搭載済み
// macOS: Hiragino Mincho ProN
// fallback: 游明朝 → serif

const cormorant = loadCormorantGaramond("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin"],
});

const inter = loadInter("normal", {
  weights: ["400", "500", "600"],
  subsets: ["latin"],
});

export const FONT_FAMILIES = {
  serifJp: `'Yu Mincho', 'YuMincho', 'Hiragino Mincho ProN', 'Noto Serif JP', serif`,
  serifEn: `${cormorant.fontFamily}, 'Times New Roman', serif`,
  sans: `${inter.fontFamily}, 'Yu Gothic', 'YuGothic', 'Hiragino Sans', sans-serif`,
  mono: `'JetBrains Mono', 'Courier New', 'SFMono-Regular', monospace`,
};

export const FONT_WAIT_FOR_READY = Promise.all([
  cormorant.waitUntilDone(),
  inter.waitUntilDone(),
]);
