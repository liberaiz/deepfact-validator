import { loadFont as loadShipporiMinchoB1 } from "@remotion/google-fonts/ShipporiMinchoB1";
import { loadFont as loadCormorantGaramond } from "@remotion/google-fonts/CormorantGaramond";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";

const shippori = loadShipporiMinchoB1("normal", {
  weights: ["500", "700", "800"],
  subsets: ["japanese"],
});

const cormorant = loadCormorantGaramond("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin"],
});

const inter = loadInter("normal", {
  weights: ["400", "500", "600"],
  subsets: ["latin"],
});

export const FONT_FAMILIES = {
  serifJp: `${shippori.fontFamily}, 'Yu Mincho', 'YuMincho', serif`,
  serifEn: `${cormorant.fontFamily}, 'Times New Roman', serif`,
  sans: `${inter.fontFamily}, 'Yu Gothic', 'YuGothic', 'Hiragino Sans', sans-serif`,
  mono: `'JetBrains Mono', 'SFMono-Regular', monospace`,
};

export const FONT_WAIT_FOR_READY = Promise.all([
  shippori.waitUntilDone(),
  cormorant.waitUntilDone(),
  inter.waitUntilDone(),
]);
