import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  staticFile,
} from "remotion";
import { FONT_FAMILIES } from "./load-fonts";

const FPS = 30;

// ── タイムライン（12 シーン / 99 秒）──────────────────────────────────────
// F0:   0- 9s  タイトル「気づかないまま騙されている」（v0.6: +4秒）
// F1:   9-14s  問題提起（医師の一言）
// F2:  14-24s  Chrome Extension 常時待機
// F3:  24-31s  Watcher スキャン
// F4:  31-39s  Investigator → Validator
// F5:  39-49s  警告ポップアップ
// F6:  49-57s  HITL フィードバック
// F7:  57-67s  Cloud Logging / Postmortem
// F8:  67-77s  GitHub PR → Cloud Build
// F9a: 77-82s  LINE Bot 個別エントリ（v0.5 新規）
// F9b: 82-87s  3エントリ並列（v0.5 新規）
// F10: 87-99s  クロージング
const T = {
  F0:  { from:   0 * FPS, dur:  9 * FPS },
  F1:  { from:   9 * FPS, dur:  5 * FPS },
  F2:  { from:  14 * FPS, dur: 10 * FPS },
  F3:  { from:  24 * FPS, dur:  7 * FPS },
  F4:  { from:  31 * FPS, dur:  8 * FPS },
  F5:  { from:  39 * FPS, dur: 10 * FPS },
  F6:  { from:  49 * FPS, dur:  8 * FPS },
  F7:  { from:  57 * FPS, dur: 10 * FPS },
  F8:  { from:  67 * FPS, dur: 10 * FPS },
  F9a: { from:  77 * FPS, dur:  5 * FPS },
  F9b: { from:  82 * FPS, dur:  5 * FPS },
  F10: { from:  87 * FPS, dur: 12 * FPS },
};

// ── カラーパレット（紙地 + 墨色 + 深緑 / 紺金禁止）──────────────────────
const C = {
  paper:     "#F4F1E8",
  paperWarm: "#EDE9DC",
  paperDeep: "#E2DCC8",
  ink:       "#1F1F1F",
  inkSoft:   "#2A2A2A",
  inkMute:   "rgba(31,31,31,0.55)",
  inkFaint:  "rgba(31,31,31,0.30)",
  green:     "#2D5A40",
  greenDark: "#1E3E2C",
  greenSoft: "rgba(45,90,64,0.15)",
  greenMute: "rgba(45,90,64,0.08)",
  warn:      "#8B3A2E",
  warnSoft:  "rgba(139,58,46,0.12)",
  safe:      "#3D7A55",
  rule:      "rgba(31,31,31,0.12)",
  terminal:  "#0F1A10",
  termText:  "#C8D8C8",
  termGreen: "#6EC87A",
  termAmber: "#E8C060",
  termRed:   "#E87060",
};

const F = FONT_FAMILIES;

// ── ユーティリティ ────────────────────────────────────────────────────────
const fadeIn = (frame: number, start = 0, end = 20) =>
  interpolate(frame, [start, end], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

const fadeOut = (frame: number, start = 0, end = 20) =>
  interpolate(frame, [start, end], [1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

const slideUp = (frame: number, start = 0, end = 20, dist = 16) =>
  interpolate(frame, [start, end], [dist, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

// ── 字幕コンポーネント（フェードイン→フェードアウト）────────────────────
const Caption: React.FC<{
  text: string;
  frame: number;
  sceneDur: number;       // シーン総フレーム数
  fadeInStart?: number;   // フェードイン開始フレーム（デフォルト 40）
  fadeInEnd?: number;     // フェードイン完了フレーム（デフォルト 70）
  fadeOutStart?: number;  // フェードアウト開始フレーム（-1 = sceneDur から自動算出）
  bottom?: number;
}> = ({
  text,
  frame,
  sceneDur,
  fadeInStart = 40,
  fadeInEnd = 70,
  fadeOutStart = -1,
  bottom = 42,
}) => {
  const foStart = fadeOutStart >= 0 ? fadeOutStart : sceneDur - 30;
  const foEnd = foStart + 20;

  const inOp  = fadeIn(frame, fadeInStart, fadeInEnd);
  const outOp = fadeOut(frame, foStart, foEnd);
  const opacity = Math.min(inOp, outOp);

  return (
    <div
      style={{
        position: "absolute",
        bottom,
        left: "50%",
        transform: "translateX(-50%)",
        opacity,
        maxWidth: 1200,
        width: "max-content",
        padding: "14px 40px",
        background: "rgba(255,255,255,0.82)",
        backdropFilter: "blur(4px)",
        borderRadius: 8,
        fontFamily: F.sans,
        fontSize: 36,
        color: C.ink,
        letterSpacing: "0.04em",
        lineHeight: 1.7,
        textAlign: "center",
        boxShadow: "0 2px 16px rgba(31,31,31,0.08)",
        zIndex: 100,
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  );
};

// ── 共通レイアウト部品 ────────────────────────────────────────────────────
const SceneLabel: React.FC<{ num: string; label: string; opacity?: number }> = ({
  num,
  label,
  opacity = 1,
}) => (
  <div
    style={{
      position: "absolute",
      top: 56,
      left: 80,
      display: "flex",
      alignItems: "baseline",
      gap: 20,
      opacity,
    }}
  >
    <span
      style={{
        fontFamily: F.serifEn,
        fontSize: 13,
        color: C.green,
        letterSpacing: "0.3em",
        fontWeight: 600,
      }}
    >
      {num}
    </span>
    <span
      style={{
        fontFamily: F.sans,
        fontSize: 13,
        color: C.inkMute,
        letterSpacing: "0.15em",
      }}
    >
      {label}
    </span>
  </div>
);

const Divider: React.FC<{ width?: number; top?: number; left?: number }> = ({
  width = 60,
  top = 0,
  left = 80,
}) => (
  <div
    style={{
      position: "absolute",
      top,
      left,
      width,
      height: 1,
      background: C.green,
    }}
  />
);

// ── ターミナル行 ──────────────────────────────────────────────────────────
const LogLine: React.FC<{
  ts: string;
  sev: string;
  msg: string;
  sevColor?: string;
  opacity?: number;
  translateY?: number;
}> = ({ ts, sev, msg, sevColor = C.termGreen, opacity = 1, translateY = 0 }) => (
  <div
    style={{
      fontFamily: F.mono,
      fontSize: 26,
      lineHeight: 1.9,
      color: C.termText,
      opacity,
      transform: `translateY(${translateY}px)`,
      letterSpacing: "0.02em",
    }}
  >
    <span style={{ color: "#6A8A6A" }}>{ts} </span>
    <span style={{ color: sevColor, fontWeight: 600 }}>{sev} </span>
    <span>{msg}</span>
  </div>
);

// ── エージェントフローバー ─────────────────────────────────────────────────
const AgentFlow: React.FC<{ active: 0 | 1 | 2 | "all"; opacity?: number }> = ({
  active,
  opacity = 1,
}) => {
  const agents = ["Watcher", "Investigator", "Validator"];
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 20,
        opacity,
      }}
    >
      {agents.map((a, i) => {
        const isActive =
          active === "all" || active === i || (active === 1 && i === 2);
        return (
          <React.Fragment key={a}>
            <div
              style={{
                padding: "10px 28px",
                border: `1.5px solid ${isActive ? C.green : C.rule}`,
                borderRadius: 4,
                fontFamily: F.serifEn,
                fontSize: 22,
                color: isActive ? C.paper : C.inkMute,
                background: isActive ? C.green : "transparent",
                letterSpacing: "0.08em",
                fontWeight: 600,
                transition: "all 0.3s",
              }}
            >
              {a}
            </div>
            {i < 2 && (
              <span
                style={{
                  color: C.green,
                  fontSize: 28,
                  fontFamily: F.serifEn,
                }}
              >
                →
              </span>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// メイン構成
// ════════════════════════════════════════════════════════════════════════════
export const MainComposition: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: C.paper }}>
      <Sequence from={T.F0.from} durationInFrames={T.F0.dur}>
        <Scene00_Title />
      </Sequence>
      <Sequence from={T.F1.from} durationInFrames={T.F1.dur}>
        <Scene01_Hook />
      </Sequence>
      <Sequence from={T.F2.from} durationInFrames={T.F2.dur}>
        <Scene02_Chrome />
      </Sequence>
      <Sequence from={T.F3.from} durationInFrames={T.F3.dur}>
        <Scene03_Watcher />
      </Sequence>
      <Sequence from={T.F4.from} durationInFrames={T.F4.dur}>
        <Scene04_Validator />
      </Sequence>
      <Sequence from={T.F5.from} durationInFrames={T.F5.dur}>
        <Scene05_Alert />
      </Sequence>
      <Sequence from={T.F6.from} durationInFrames={T.F6.dur}>
        <Scene06_Feedback />
      </Sequence>
      <Sequence from={T.F7.from} durationInFrames={T.F7.dur}>
        <Scene07_Logging />
      </Sequence>
      <Sequence from={T.F8.from} durationInFrames={T.F8.dur}>
        <Scene08_GitHubBuild />
      </Sequence>
      <Sequence from={T.F9a.from} durationInFrames={T.F9a.dur}>
        <Scene09a_LineBot />
      </Sequence>
      <Sequence from={T.F9b.from} durationInFrames={T.F9b.dur}>
        <Scene09b_EntryPoints />
      </Sequence>
      <Sequence from={T.F10.from} durationInFrames={T.F10.dur}>
        <Scene10_Outro />
      </Sequence>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F0: タイトルスライド「気づかないまま騙されている」（0-5s）— v0.4 新規
// ════════════════════════════════════════════════════════════════════════════
const Scene00_Title: React.FC = () => {
  const frame = useCurrentFrame();

  // ページ全体フェードイン
  const bgOp = fadeIn(frame, 0, 20);

  // メインタイトル: 行ごとにずらしてフェードイン
  const line1Op = fadeIn(frame, 10, 40);
  const line1Y  = slideUp(frame, 10, 40, 28);
  const line2Op = fadeIn(frame, 25, 55);
  const line2Y  = slideUp(frame, 25, 55, 28);

  // リード文: タイトル後にフェードイン
  const leadOp = fadeIn(frame, 55, 95);
  const leadY  = slideUp(frame, 55, 95, 20);

  // 区切りライン幅
  const lineW = interpolate(frame, [45, 100], [0, 120], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // 背景の薄い「？」モチーフ（書籍的）
  const motifOp = fadeIn(frame, 5, 35);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: C.paper,
        opacity: bgOp,
        justifyContent: "center",
        alignItems: "center",
        overflow: "hidden",
      }}
    >
      {/* 背景モチーフ: 巨大な「？」 */}
      <div
        style={{
          position: "absolute",
          right: -40,
          top: "50%",
          transform: "translateY(-50%)",
          fontFamily: F.serifJp,
          fontSize: 680,
          color: C.ink,
          opacity: motifOp * 0.045,
          fontWeight: 600,
          lineHeight: 1,
          userSelect: "none",
          pointerEvents: "none",
          letterSpacing: "-0.05em",
        }}
      >
        ？
      </div>

      {/* 左ボーダーライン（書籍カバー風） */}
      <div
        style={{
          position: "absolute",
          left: 100,
          top: "10%",
          bottom: "10%",
          width: 3,
          background: C.green,
          opacity: fadeIn(frame, 8, 28),
        }}
      />

      {/* コンテンツブロック */}
      <div
        style={{
          position: "absolute",
          left: 140,
          top: "50%",
          transform: "translateY(-50%)",
          maxWidth: 1300,
        }}
      >
        {/* マガジン名（小・上部） */}
        <div
          style={{
            fontFamily: F.sans,
            fontSize: 18,
            color: C.green,
            letterSpacing: "0.35em",
            fontWeight: 600,
            marginBottom: 48,
            opacity: fadeIn(frame, 5, 30),
          }}
        >
          DeepFact Validator — Demo
        </div>

        {/* メインタイトル 行1：「気づかないまま」 */}
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 108,
            color: C.ink,
            fontWeight: 600,
            lineHeight: 1.35,
            letterSpacing: "0.02em",
            opacity: line1Op,
            transform: `translateY(${line1Y}px)`,
          }}
        >
          気づかないまま
        </div>

        {/* メインタイトル 行2：「騙されている」アクセント色 */}
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 108,
            color: C.green,
            fontWeight: 600,
            lineHeight: 1.35,
            letterSpacing: "0.02em",
            opacity: line2Op,
            transform: `translateY(${line2Y}px)`,
            marginBottom: 48,
          }}
        >
          騙されている
        </div>

        {/* 区切りライン */}
        <div
          style={{
            width: lineW,
            height: 2,
            background: C.green,
            marginBottom: 40,
          }}
        />

        {/* リード文 */}
        <div
          style={{
            opacity: leadOp,
            transform: `translateY(${leadY}px)`,
          }}
        >
          <div
            style={{
              fontFamily: F.serifJp,
              fontSize: 32,
              color: C.inkSoft,
              lineHeight: 2.0,
              letterSpacing: "0.05em",
              fontWeight: 400,
            }}
          >
            この情報過多社会、あなたが目にするその情報は
            <span style={{ color: C.green, fontWeight: 500 }}>
              真実ですか？
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F1: 問題提起（5-10s）— 医師創業者の一言
// ════════════════════════════════════════════════════════════════════════════
const Scene01_Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const quoteOpacity = fadeIn(frame, 0, 30);
  const quoteY = slideUp(frame, 0, 30, 24);
  const nameOpacity = fadeIn(frame, 50, 90);
  const lineWidth = interpolate(frame, [40, 80], [0, 140], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #1A1F1A 0%, #0D1A0E 100%)`,
        justifyContent: "center",
        alignItems: "center",
        padding: 120,
      }}
    >
      {/* 背景 — 薄い緑の格子モチーフ */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(45,90,64,0.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(45,90,64,0.06) 1px, transparent 1px)
          `,
          backgroundSize: "80px 80px",
        }}
      />

      {/* 引用ブロック */}
      <div
        style={{
          opacity: quoteOpacity,
          transform: `translateY(${quoteY}px)`,
          borderLeft: `4px solid ${C.green}`,
          paddingLeft: 56,
          maxWidth: 1280,
        }}
      >
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 72,
            color: "#F4F1E8",
            lineHeight: 1.75,
            letterSpacing: "0.02em",
            fontWeight: 500,
          }}
        >
          「真偽判断は
          <br />
          一次情報まで遡る。
          <br />
          これが医師の習慣です。」
        </div>
      </div>

      {/* 区切り線 */}
      <div
        style={{
          position: "absolute",
          bottom: 220,
          left: 120 + 60,
          width: lineWidth,
          height: 1,
          background: C.green,
        }}
      />

      {/* 著者名 — 三冠→独立家（v0.4 修正） */}
      <div
        style={{
          position: "absolute",
          bottom: 160,
          left: 120 + 60,
          opacity: nameOpacity,
          fontFamily: F.sans,
          fontSize: 22,
          color: "rgba(200,216,200,0.7)",
          letterSpacing: "0.15em",
        }}
      >
        Dr. 加藤 — 医師・医学博士・独立家
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F2: Chrome Extension 常時待機（10-20s）
// ════════════════════════════════════════════════════════════════════════════
const Scene02_Chrome: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);
  const browserOp = fadeIn(frame, 20, 50);
  const browserY = slideUp(frame, 20, 50, 32);
  const badgeOp = fadeIn(frame, 120, 160);
  const badgePulse = Math.abs(Math.sin((frame / fps) * Math.PI * 1.5));
  const dur = T.F2.dur;

  return (
    <AbsoluteFill style={{ backgroundColor: C.paper }}>
      <SceneLabel num="02" label="Chrome Extension — 常時待機" opacity={labelOp} />

      {/* ブラウザウィンドウ */}
      <div
        style={{
          position: "absolute",
          top: 130,
          left: 120,
          right: 120,
          bottom: 80,
          opacity: browserOp,
          transform: `translateY(${browserY}px)`,
          background: "#FFFFFF",
          borderRadius: 12,
          boxShadow: "0 24px 80px rgba(31,31,31,0.16)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* ブラウザバー */}
        <div
          style={{
            background: "#F1F3F4",
            padding: "20px 28px",
            display: "flex",
            alignItems: "center",
            gap: 16,
            borderBottom: "1px solid #E0E0E0",
          }}
        >
          {/* トラフィックライト */}
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
            <div
              key={c}
              style={{ width: 18, height: 18, borderRadius: "50%", background: c }}
            />
          ))}
          {/* URL バー */}
          <div
            style={{
              flex: 1,
              background: "#FFFFFF",
              borderRadius: 8,
              padding: "10px 20px",
              fontFamily: F.mono,
              fontSize: 24,
              color: "#444",
              border: "1px solid #E0E0E0",
            }}
          >
            news.yahoo.co.jp/articles/...
          </div>
          {/* Extension アイコン */}
          <div
            style={{
              width: 40,
              height: 40,
              background: C.green,
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: C.paper,
              fontFamily: F.serifEn,
              fontSize: 18,
              fontWeight: 700,
            }}
          >
            DF
          </div>
        </div>

        {/* ページコンテンツ */}
        <div style={{ flex: 1, padding: 64, background: "#FAFAFA" }}>
          {/* Yahoo! News 風ヘッダー */}
          <div
            style={{
              fontFamily: F.sans,
              fontSize: 22,
              color: "#E60012",
              fontWeight: 700,
              marginBottom: 40,
              letterSpacing: "0.1em",
            }}
          >
            Yahoo! ニュース
          </div>

          {/* 見出し記事 */}
          <div
            style={{
              background: "#FFFFFF",
              border: "1px solid #E8E8E8",
              borderRadius: 8,
              padding: "40px 48px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              maxWidth: 900,
            }}
          >
            <div
              style={{
                fontFamily: F.sans,
                fontSize: 16,
                color: "#E60012",
                fontWeight: 600,
                marginBottom: 16,
                letterSpacing: "0.05em",
              }}
            >
              健康・医療
            </div>
            <div
              style={{
                fontFamily: F.serifJp,
                fontSize: 40,
                color: "#111",
                fontWeight: 600,
                lineHeight: 1.6,
                letterSpacing: "-0.01em",
              }}
            >
              「ワクチンに極秘成分が混入——
              <br />
              内部告発者が証拠映像を公開」
            </div>
            <div
              style={{
                marginTop: 24,
                fontFamily: F.sans,
                fontSize: 22,
                color: "#777",
              }}
            >
              2026年6月29日 09:10配信
            </div>

            {/* 評価ボタン（Yahoo! 再現） */}
            <div
              style={{
                marginTop: 28,
                display: "flex",
                gap: 12,
                borderTop: "1px solid #E8E8E8",
                paddingTop: 20,
              }}
            >
              {[
                { label: "役に立った", count: "243" },
                { label: "参考になった", count: "187" },
                { label: "もっと知りたい", count: "94" },
              ].map((btn) => (
                <div
                  key={btn.label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "10px 20px",
                    border: "1px solid #D0D0D0",
                    borderRadius: 20,
                    background: "#F7F7F7",
                    fontFamily: F.sans,
                    fontSize: 18,
                    color: "#444",
                    cursor: "pointer",
                  }}
                >
                  <span>{btn.label}</span>
                  <span style={{ color: "#999", fontSize: 16 }}>{btn.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* DeepFact 待機バッジ */}
        <div
          style={{
            position: "absolute",
            bottom: 40,
            right: 48,
            background: C.green,
            color: C.paper,
            fontFamily: F.sans,
            fontSize: 22,
            fontWeight: 600,
            padding: "14px 28px",
            borderRadius: 8,
            letterSpacing: "0.05em",
            opacity: badgeOp * (0.7 + badgePulse * 0.3),
            display: "flex",
            alignItems: "center",
            gap: 12,
            boxShadow: "0 4px 20px rgba(45,90,64,0.3)",
          }}
        >
          <div
            style={{
              width: 12,
              height: 12,
              borderRadius: "50%",
              background: "#A8F0B8",
            }}
          />
          DeepFact 待機中...
        </div>
      </div>

      {/* 字幕 */}
      <Caption
        text="真偽が気になるWeb上の情報を、機能拡張で常駐したDeepFactが即座に判定。"
        frame={frame}
        sceneDur={dur}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F3: Watcher スキャン（20-27s）
// ════════════════════════════════════════════════════════════════════════════
const Scene03_Watcher: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);
  const agentOp = fadeIn(frame, 10, 40);
  const dur = T.F3.dur;

  const logs = [
    { ts: "[Watcher]", sev: "INFO", msg: "主張抽出: \"極秘成分\" \"内部告発\" 検出", sevColor: C.termGreen },
    { ts: "[Watcher]", sev: "WARN", msg: "感情強度: 0.92  HIGH ▲", sevColor: C.termAmber },
    { ts: "[Watcher]", sev: "WARN", msg: "煽動パターン: conspiracy_theory ✓", sevColor: C.termAmber },
    { ts: "[Watcher]", sev: "INFO", msg: "出典URL: 未提示 (0/4 claims cited)", sevColor: C.termText },
    { ts: "[Watcher]", sev: "INFO", msg: "→ Investigator にハンドオフ", sevColor: C.termGreen },
  ];

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, #0F1A10 0%, #1A241A 100%)`,
      }}
    >
      {/* 格子背景 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(rgba(45,90,64,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(45,90,64,0.05) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />

      <SceneLabel num="03" label="Watcher Agent — 記事スキャン" opacity={labelOp} />

      {/* エージェントフロー */}
      <div
        style={{
          position: "absolute",
          top: 130,
          left: 120,
          opacity: agentOp,
        }}
      >
        <AgentFlow active={0} />
      </div>

      {/* タイトル */}
      <div
        style={{
          position: "absolute",
          top: 230,
          left: 120,
          fontFamily: F.serifJp,
          fontSize: 36,
          color: C.termText,
          opacity: agentOp,
          letterSpacing: "0.05em",
        }}
      >
        記事スキャン実行中...
      </div>

      {/* ログ出力 */}
      <div
        style={{
          position: "absolute",
          top: 310,
          left: 100,
          right: 100,
          bottom: 80,
          background: "rgba(0,0,0,0.4)",
          borderRadius: 12,
          padding: "36px 48px",
          border: `1px solid ${C.greenSoft}`,
          overflow: "hidden",
        }}
      >
        {logs.map((log, i) => {
          const sp = spring({
            frame: frame - 30 - i * 18,
            fps,
            config: { damping: 200 },
          });
          return (
            <LogLine
              key={i}
              ts={log.ts}
              sev={log.sev}
              msg={log.msg}
              sevColor={log.sevColor}
              opacity={sp}
              translateY={(1 - sp) * 20}
            />
          );
        })}
      </div>

      {/* 字幕 */}
      <Caption
        text="Watcher Agentが記事構造・主張・出典をスキャン。"
        frame={frame}
        sceneDur={dur}
        fadeInStart={35}
        fadeInEnd={60}
        bottom={28}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F4: Investigator → Validator（27-35s）
// ════════════════════════════════════════════════════════════════════════════
const Scene04_Validator: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);
  const agentOp = fadeIn(frame, 10, 40);
  const dur = T.F4.dur;

  const progressWidth = interpolate(frame, [20, 140], [0, 100], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  const scoreOp = fadeIn(frame, 140, 200);
  const scoreY = slideUp(frame, 140, 200, 32);

  const scores = [
    { val: "20%", label: "TRUST SCORE", color: C.warn },
    { val: "0.10", label: "SOURCE SCORE", color: C.termAmber },
    { val: "0.00", label: "FACT CHECK MATCH", color: C.termRed },
  ];

  const logs = [
    { ts: "[Investigator]", sev: "INFO", msg: "125 trusted domains 照合中...", sevColor: C.termGreen },
    { ts: "[Investigator]", sev: "INFO", msg: "Google Fact Check API: 0 matches", sevColor: C.termAmber },
    { ts: "[Validator]", sev: "WARN", msg: "統合スコア算出: 0.20", sevColor: C.termAmber },
    { ts: "[Validator]", sev: "WARN", msg: "→ ALERT 発火条件: threshold=0.40 超過", sevColor: C.termRed },
  ];

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, #0F1A10 0%, #1A241A 100%)`,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(rgba(45,90,64,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(45,90,64,0.05) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />

      <SceneLabel num="04" label="Investigator → Validator — スコア算出" opacity={labelOp} />

      {/* エージェントフロー */}
      <div style={{ position: "absolute", top: 130, left: 120, opacity: agentOp }}>
        <AgentFlow active={1} />
      </div>

      {/* プログレスバー */}
      <div
        style={{
          position: "absolute",
          top: 240,
          left: 120,
          right: 120,
          opacity: agentOp,
        }}
      >
        <div
          style={{
            fontFamily: F.sans,
            fontSize: 20,
            color: C.termGreen,
            letterSpacing: "0.15em",
            marginBottom: 12,
          }}
        >
          VALIDATION PIPELINE
        </div>
        <div
          style={{
            background: "rgba(255,255,255,0.08)",
            borderRadius: 6,
            height: 10,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progressWidth}%`,
              background: `linear-gradient(90deg, ${C.green} 0%, ${C.termAmber} 100%)`,
              borderRadius: 6,
              transition: "width 0.1s linear",
            }}
          />
        </div>
        <div
          style={{
            fontFamily: F.mono,
            fontSize: 18,
            color: C.termGreen,
            marginTop: 8,
            letterSpacing: "0.05em",
          }}
        >
          {Math.round(progressWidth)}%
        </div>
      </div>

      {/* ログ */}
      <div
        style={{
          position: "absolute",
          top: 360,
          left: 100,
          right: 100,
          background: "rgba(0,0,0,0.4)",
          borderRadius: 12,
          padding: "28px 48px",
          border: `1px solid ${C.greenSoft}`,
        }}
      >
        {logs.map((log, i) => {
          const sp = spring({ frame: frame - 20 - i * 16, fps, config: { damping: 200 } });
          return (
            <LogLine key={i} ts={log.ts} sev={log.sev} msg={log.msg} sevColor={log.sevColor} opacity={sp} translateY={(1 - sp) * 16} />
          );
        })}
      </div>

      {/* スコア表示 */}
      <div
        style={{
          position: "absolute",
          bottom: 70,
          left: 100,
          right: 100,
          display: "flex",
          gap: 40,
          opacity: scoreOp,
          transform: `translateY(${scoreY}px)`,
        }}
      >
        {scores.map((s) => (
          <div
            key={s.label}
            style={{
              flex: 1,
              background: "rgba(0,0,0,0.5)",
              border: `1px solid ${C.greenSoft}`,
              borderRadius: 12,
              padding: "28px 36px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontFamily: F.serifEn,
                fontSize: 64,
                fontWeight: 700,
                color: s.color,
                letterSpacing: "-0.04em",
                lineHeight: 1,
              }}
            >
              {s.val}
            </div>
            <div
              style={{
                fontFamily: F.sans,
                fontSize: 17,
                color: C.termText,
                letterSpacing: "0.2em",
                marginTop: 12,
                opacity: 0.7,
              }}
            >
              {s.label}
            </div>
          </div>
        ))}
      </div>

      {/* 字幕 */}
      <Caption
        text="Investigator → Validator が信頼度・煽動パターン・公的機関照合を統合判定。"
        frame={frame}
        sceneDur={dur}
        fadeInStart={30}
        fadeInEnd={60}
        bottom={28}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F5: 警告ポップアップ（35-45s）
// ════════════════════════════════════════════════════════════════════════════
const Scene05_Alert: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);

  const popupSpring = spring({ frame: frame - 30, fps, config: { damping: 180, stiffness: 120 } });
  const popupY = interpolate(popupSpring, [0, 1], [80, 0]);
  const sourceOp = fadeIn(frame, 80, 130);

  return (
    <AbsoluteFill style={{ backgroundColor: C.paperWarm }}>
      <SceneLabel num="05" label="警告ポップアップ — ユーザーへの通知" opacity={labelOp} />

      {/* ブラウザ背景（ぼかし表現） */}
      <div
        style={{
          position: "absolute",
          top: 130,
          left: 120,
          right: 120,
          bottom: 80,
          background: "rgba(240,238,230,0.6)",
          borderRadius: 12,
          border: `1px solid ${C.rule}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 32,
            color: C.inkFaint,
            letterSpacing: "0.1em",
          }}
        >
          Yahoo! ニュース — 記事閲覧中
        </div>
      </div>

      {/* 警告ポップアップ本体 */}
      <div
        style={{
          position: "absolute",
          bottom: 120,
          right: 160,
          width: 680,
          background: "#FFFFFF",
          borderRadius: 12,
          borderTop: `5px solid ${C.warn}`,
          boxShadow: "0 16px 60px rgba(139,58,46,0.22)",
          padding: "40px 48px",
          opacity: popupSpring,
          transform: `translateY(${popupY}px)`,
        }}
      >
        {/* ポップアップヘッダー */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            marginBottom: 24,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              background: C.warn,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#FFFFFF",
              fontFamily: F.serifEn,
              fontSize: 20,
              fontWeight: 700,
            }}
          >
            !
          </div>
          <div
            style={{
              fontFamily: F.sans,
              fontSize: 22,
              fontWeight: 700,
              color: C.warn,
              letterSpacing: "0.05em",
            }}
          >
            DeepFact — 情報構造に注意
          </div>
        </div>

        {/* スコア + 詳細 */}
        <div style={{ display: "flex", gap: 32, alignItems: "flex-start" }}>
          <div
            style={{
              fontFamily: F.serifEn,
              fontSize: 80,
              fontWeight: 700,
              color: C.warn,
              lineHeight: 1,
              letterSpacing: "-0.04em",
            }}
          >
            20%
          </div>
          <div
            style={{
              flex: 1,
              fontFamily: F.sans,
              fontSize: 22,
              color: C.inkSoft,
              lineHeight: 1.8,
            }}
          >
            出所：未検証サイト
            <br />
            煽動パターン：conspiracy 型 検出
            <br />
            一次情報：厚労省・WHO に反する記述
          </div>
        </div>

        {/* 参照ソース */}
        <div
          style={{
            marginTop: 24,
            padding: "16px 20px",
            background: C.greenMute,
            borderRadius: 8,
            fontFamily: F.sans,
            fontSize: 20,
            color: C.green,
            opacity: sourceOp,
          }}
        >
          参照一次情報: 厚労省 · WHO · PolitiFact · JFC
        </div>

        {/* フィードバックリンク */}
        <div
          style={{
            marginTop: 20,
            fontFamily: F.sans,
            fontSize: 19,
            color: C.green,
            letterSpacing: "0.02em",
            textDecoration: "underline",
            opacity: sourceOp,
          }}
        >
          この判定は誤りですか？ フィードバックする →
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F6: HITL フィードバック（45-53s）
// ════════════════════════════════════════════════════════════════════════════
const Scene06_Feedback: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);
  const cardSpring = spring({ frame: frame - 15, fps, config: { damping: 200 } });
  const selOp = fadeIn(frame, 80, 120);
  const arrowOp = fadeIn(frame, 140, 200);
  const dur = T.F6.dur;

  return (
    <AbsoluteFill style={{ backgroundColor: C.paper }}>
      <SceneLabel num="06" label="Human-in-the-Loop — ユーザーフィードバック" opacity={labelOp} />

      {/* HITL 説明タイトル */}
      <div
        style={{
          position: "absolute",
          top: 130,
          left: 120,
          fontFamily: F.serifJp,
          fontSize: 52,
          color: C.ink,
          fontWeight: 500,
          letterSpacing: "-0.02em",
          opacity: cardSpring,
          transform: `translateY(${(1 - cardSpring) * 24}px)`,
        }}
      >
        ユーザーの判断が
        <span style={{ color: C.green }}> CI/CD ループ</span> に直結する
      </div>

      {/* フィードバックカード */}
      <div
        style={{
          position: "absolute",
          top: 260,
          left: 120,
          width: 860,
          background: "#FFFFFF",
          borderRadius: 16,
          borderTop: `4px solid ${C.green}`,
          boxShadow: "0 8px 40px rgba(31,31,31,0.10)",
          padding: "52px 56px",
          opacity: cardSpring,
          transform: `translateY(${(1 - cardSpring) * 20}px)`,
        }}
      >
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 32,
            color: C.ink,
            fontWeight: 600,
            marginBottom: 36,
          }}
        >
          この警告についてどう思いますか？
        </div>

        {/* 選択肢 */}
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          {[
            { label: "✓ 誤判定だと思う", selected: true },
            { label: "警告は正しい", selected: false },
            { label: "よくわからない", selected: false },
          ].map((opt) => (
            <div
              key={opt.label}
              style={{
                padding: "16px 32px",
                border: `1.5px solid ${opt.selected ? C.green : C.rule}`,
                borderRadius: 8,
                fontFamily: F.sans,
                fontSize: 24,
                color: opt.selected ? C.paper : C.inkMute,
                background: opt.selected ? C.green : "transparent",
                fontWeight: opt.selected ? 600 : 400,
                opacity: opt.selected ? selOp : 0.5 * selOp,
              }}
            >
              {opt.label}
            </div>
          ))}
        </div>

        <div
          style={{
            marginTop: 32,
            fontFamily: F.sans,
            fontSize: 20,
            color: C.inkMute,
            lineHeight: 1.7,
          }}
        >
          フィードバックは匿名で記録されます。
          <br />
          信頼ソース辞書の継続的改善（CI/CD）に使用されます。
        </div>
      </div>

      {/* 矢印 → DevOps */}
      <div
        style={{
          position: "absolute",
          top: 360,
          right: 120,
          opacity: arrowOp,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
        }}
      >
        <div
          style={{
            fontFamily: F.sans,
            fontSize: 20,
            color: C.green,
            letterSpacing: "0.1em",
            textAlign: "center",
          }}
        >
          Cloud Logging
          <br />
          Postmortem
        </div>
        <div style={{ fontSize: 48, color: C.green }}>↓</div>
        <div
          style={{
            fontFamily: F.sans,
            fontSize: 20,
            color: C.green,
            letterSpacing: "0.1em",
            textAlign: "center",
          }}
        >
          GitHub PR
          <br />
          Cloud Build
        </div>
      </div>

      {/* 字幕 */}
      <Caption
        text="ユーザーのフィードバックが信頼ソース辞書を継続改善（CI/CD ループに直結）。"
        frame={frame}
        sceneDur={dur}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F7: Cloud Logging / Postmortem（53-63s）
// ════════════════════════════════════════════════════════════════════════════
const Scene07_Logging: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);
  const titleOp = fadeIn(frame, 10, 40);
  const dur = T.F7.dur;

  const logs = [
    {
      ts: "2026-06-29T09:14:32Z",
      sev: "[WARNING]",
      msg: 'alert_fired  url=yahoo.co.jp/...  score=0.20  pattern=conspiracy',
      sevColor: C.termAmber,
      delay: 30,
    },
    {
      ts: "2026-06-29T09:14:35Z",
      sev: "[INFO]   ",
      msg: "user_feedback: false_positive  uid=anon-a7f3",
      sevColor: C.termGreen,
      delay: 60,
    },
    {
      ts: "2026-06-29T09:14:35Z",
      sev: "[INFO]   ",
      msg: "postmortem_created  id=PM-2026-0042  severity=P3",
      sevColor: C.termGreen,
      delay: 80,
    },
    {
      ts: "2026-06-29T09:14:36Z",
      sev: "[INFO]   ",
      msg: "root_cause: trusted_source missing — reuters.com not in whitelist",
      sevColor: C.termGreen,
      delay: 100,
    },
    {
      ts: "2026-06-29T09:14:36Z",
      sev: "[INFO]   ",
      msg: "github_pr_queued: feat/add-reuters-to-trusted-sources",
      sevColor: C.termGreen,
      delay: 130,
    },
    {
      ts: "2026-06-29T09:14:37Z",
      sev: "[INFO]   ",
      msg: "cloud_build_triggered: cloudbuild.yaml  branch=main",
      sevColor: C.termGreen,
      delay: 160,
    },
  ];

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #0A100A 0%, #111811 100%)`,
      }}
    >
      <SceneLabel num="07" label="Cloud Logging — Postmortem 記録" opacity={labelOp} />

      {/* タイトル */}
      <div
        style={{
          position: "absolute",
          top: 120,
          left: 120,
          opacity: titleOp,
        }}
      >
        <div
          style={{
            fontFamily: F.serifEn,
            fontSize: 22,
            color: C.green,
            letterSpacing: "0.3em",
            fontWeight: 600,
            marginBottom: 8,
          }}
        >
          GOOGLE CLOUD LOGGING — DEEPFACT VALIDATOR
        </div>
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 44,
            color: "#E8F0E8",
            letterSpacing: "0.02em",
            fontWeight: 500,
          }}
        >
          誤情報を「情報の障害」として Postmortem 記録
        </div>
      </div>

      {/* ログコンソール */}
      <div
        style={{
          position: "absolute",
          top: 270,
          left: 80,
          right: 80,
          bottom: 70,
          background: "rgba(0,0,0,0.7)",
          borderRadius: 12,
          padding: "36px 48px",
          border: `1px solid rgba(45,90,64,0.3)`,
          fontFamily: F.mono,
          overflow: "hidden",
        }}
      >
        {/* コンソールヘッダー */}
        <div
          style={{
            fontFamily: F.sans,
            fontSize: 18,
            color: C.termGreen,
            letterSpacing: "0.2em",
            marginBottom: 28,
            borderBottom: `1px solid rgba(45,90,64,0.2)`,
            paddingBottom: 12,
          }}
        >
          $ gcloud logging read "resource.type=cloud_run_revision" --limit=20
        </div>

        {logs.map((log, i) => {
          const sp = spring({
            frame: frame - log.delay,
            fps,
            config: { damping: 200 },
          });
          return (
            <div
              key={i}
              style={{
                fontSize: 24,
                lineHeight: 1.85,
                color: C.termText,
                opacity: sp,
                transform: `translateY(${(1 - sp) * 16}px)`,
              }}
            >
              <span style={{ color: "#4A6A4A" }}>{log.ts} </span>
              <span style={{ color: log.sevColor, fontWeight: 600 }}>{log.sev} </span>
              <span>{log.msg}</span>
            </div>
          );
        })}
      </div>

      {/* 字幕 */}
      <Caption
        text="警告履歴は Cloud Logging に Postmortem 形式で蓄積。"
        frame={frame}
        sceneDur={dur}
        fadeInStart={35}
        fadeInEnd={65}
        bottom={28}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F8: GitHub PR → Cloud Build（63-73s）
// ════════════════════════════════════════════════════════════════════════════
const Scene08_GitHubBuild: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);
  const titleOp = fadeIn(frame, 10, 40);
  const dur = T.F8.dur;

  const prSpring = spring({ frame: frame - 30, fps, config: { damping: 180 } });
  const buildSpring = spring({ frame: frame - 110, fps, config: { damping: 180 } });
  const deploySpring = spring({ frame: frame - 190, fps, config: { damping: 180 } });

  const buildProgress = interpolate(frame, [110, 220], [0, 100], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #0D120D 0%, #141A14 100%)`,
      }}
    >
      <SceneLabel num="08" label="GitHub PR → Cloud Build → Cloud Run" opacity={labelOp} />

      <div
        style={{
          position: "absolute",
          top: 120,
          left: 120,
          opacity: titleOp,
        }}
      >
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 44,
            color: "#E8F0E8",
            letterSpacing: "0.02em",
            fontWeight: 500,
          }}
        >
          信頼ソースの継続的改善 ——
          <span style={{ color: C.termGreen }}> 情報の CI/CD</span>
        </div>
      </div>

      {/* 3カード縦並び */}
      <div
        style={{
          position: "absolute",
          top: 220,
          left: 100,
          right: 100,
          bottom: 70,
          display: "flex",
          flexDirection: "column",
          gap: 32,
        }}
      >
        {/* GitHub PR */}
        <div
          style={{
            flex: 1,
            background: "rgba(45,90,64,0.12)",
            border: `1px solid rgba(45,90,64,0.4)`,
            borderRadius: 12,
            padding: "28px 40px",
            opacity: prSpring,
            transform: `translateX(${(1 - prSpring) * -40}px)`,
            display: "flex",
            alignItems: "center",
            gap: 36,
          }}
        >
          <div
            style={{
              fontFamily: F.serifEn,
              fontSize: 28,
              color: C.termGreen,
              fontWeight: 700,
              whiteSpace: "nowrap",
            }}
          >
            PR #147
          </div>
          <div style={{ flex: 1 }}>
            <div
              style={{
                fontFamily: F.mono,
                fontSize: 18,
                color: "#6A8A6A",
                marginBottom: 6,
                letterSpacing: "0.05em",
              }}
            >
              auto-generated by DeepFact / postmortem PM-2026-0042
            </div>
            <div
              style={{
                fontFamily: F.sans,
                fontSize: 28,
                color: "#E8F0E8",
                fontWeight: 600,
              }}
            >
              feat: add Reuters Fact Check to trusted-source whitelist
            </div>
          </div>
          <div
            style={{
              padding: "8px 20px",
              background: "rgba(45,90,64,0.5)",
              borderRadius: 6,
              fontFamily: F.mono,
              fontSize: 18,
              color: C.termGreen,
              letterSpacing: "0.05em",
            }}
          >
            open
          </div>
        </div>

        {/* Cloud Build */}
        <div
          style={{
            flex: 1,
            background: "rgba(232,192,96,0.06)",
            border: `1px solid rgba(232,192,96,0.25)`,
            borderRadius: 12,
            padding: "28px 40px",
            opacity: buildSpring,
            transform: `translateX(${(1 - buildSpring) * -40}px)`,
          }}
        >
          <div
            style={{
              fontFamily: F.serifEn,
              fontSize: 20,
              color: C.termAmber,
              letterSpacing: "0.25em",
              fontWeight: 600,
              marginBottom: 16,
            }}
          >
            CLOUD BUILD — deepfact-validator
          </div>
          <div
            style={{
              background: "rgba(0,0,0,0.4)",
              borderRadius: 6,
              height: 10,
              overflow: "hidden",
              marginBottom: 12,
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${buildProgress}%`,
                background: C.termGreen,
                borderRadius: 6,
              }}
            />
          </div>
          <div
            style={{
              fontFamily: F.mono,
              fontSize: 22,
              color: buildProgress >= 100 ? C.termGreen : C.termAmber,
              letterSpacing: "0.05em",
            }}
          >
            {buildProgress >= 100
              ? "✓  BUILD SUCCESS  —  cloudbuild.yaml  step 4/4"
              : `BUILDING... ${Math.round(buildProgress)}%  —  step ${Math.floor(buildProgress / 25) + 1}/4`}
          </div>
        </div>

        {/* Cloud Run Deploy */}
        <div
          style={{
            flex: 1,
            background: "rgba(110,200,122,0.06)",
            border: `1px solid rgba(110,200,122,0.25)`,
            borderRadius: 12,
            padding: "28px 40px",
            opacity: deploySpring,
            transform: `translateX(${(1 - deploySpring) * -40}px)`,
            display: "flex",
            alignItems: "center",
            gap: 36,
          }}
        >
          <div style={{ flex: 1 }}>
            <div
              style={{
                fontFamily: F.serifEn,
                fontSize: 20,
                color: C.termGreen,
                letterSpacing: "0.25em",
                fontWeight: 600,
                marginBottom: 8,
              }}
            >
              CLOUD RUN — DEPLOYED
            </div>
            <div
              style={{
                fontFamily: F.mono,
                fontSize: 22,
                color: "#C8D8C8",
              }}
            >
              deepfact-validator-kjciocymea-an.a.run.app — revision 00013
            </div>
          </div>
          <div
            style={{
              fontFamily: F.serifEn,
              fontSize: 28,
              color: C.termGreen,
              fontWeight: 700,
              letterSpacing: "0.1em",
            }}
          >
            LIVE ✓
          </div>
        </div>
      </div>

      {/* 字幕 */}
      <Caption
        text="改善は GitHub Actions で検証→Cloud Build→Cloud Run に自動 deploy。"
        frame={frame}
        sceneDur={dur}
        fadeInStart={35}
        fadeInEnd={65}
        bottom={28}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F9a: LINE Bot 個別エントリ（73-78s）— v0.5 新規
// ════════════════════════════════════════════════════════════════════════════
const Scene09a_LineBot: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);
  const titleOp = fadeIn(frame, 10, 45);
  const dur = T.F9a.dur;

  const phoneSpring = spring({ frame: frame - 20, fps, config: { damping: 200 } });
  const msg1Spring = spring({ frame: frame - 55, fps, config: { damping: 200 } });
  const msg2Spring = spring({ frame: frame - 95, fps, config: { damping: 200 } });

  return (
    <AbsoluteFill style={{ backgroundColor: C.paper }}>
      <SceneLabel num="09a" label="LINE Bot — 個別エントリ" opacity={labelOp} />

      {/* タイトル */}
      <div
        style={{
          position: "absolute",
          top: 100,
          left: 120,
          right: 120,
          opacity: titleOp,
        }}
      >
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 50,
            color: C.ink,
            fontWeight: 500,
            letterSpacing: "-0.01em",
            lineHeight: 1.5,
          }}
        >
          Chrome だけじゃない。
          <span style={{ color: C.green }}> LINE に URL を送るだけ。</span>
        </div>
        <div
          style={{
            fontFamily: F.sans,
            fontSize: 22,
            color: C.inkMute,
            marginTop: 12,
            letterSpacing: "0.04em",
          }}
        >
          公式アカウントに URL を貼る ── 信頼度＋一次情報 URL が即返信
        </div>
      </div>

      {/* スマートフォンモック（中央・縦長） */}
      <div
        style={{
          position: "absolute",
          top: 240,
          left: "50%",
          transform: `translateX(-50%) translateY(${(1 - phoneSpring) * 50}px)`,
          opacity: phoneSpring,
          width: 420,
          background: "#1A1A1A",
          borderRadius: 36,
          padding: 14,
          boxShadow: "0 28px 72px rgba(31,31,31,0.32)",
        }}
      >
        <div
          style={{
            background: "#FFFFFF",
            borderRadius: 26,
            overflow: "hidden",
          }}
        >
          {/* LINE ヘッダー */}
          <div
            style={{
              background: "#06C755",
              padding: "18px 22px",
              display: "flex",
              alignItems: "center",
              gap: 14,
            }}
          >
            <div
              style={{
                width: 38,
                height: 38,
                background: "rgba(255,255,255,0.3)",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontFamily: F.serifEn,
                fontWeight: 700,
                fontSize: 14,
              }}
            >
              DF
            </div>
            <div>
              <div
                style={{
                  color: "white",
                  fontFamily: F.sans,
                  fontSize: 18,
                  fontWeight: 700,
                  letterSpacing: "0.02em",
                }}
              >
                DeepFact
              </div>
              <div
                style={{
                  color: "rgba(255,255,255,0.75)",
                  fontFamily: F.sans,
                  fontSize: 13,
                }}
              >
                公式アカウント
              </div>
            </div>
          </div>

          {/* チャット本体 */}
          <div
            style={{
              background: "#DFE5EA",
              padding: "20px 18px",
              minHeight: 320,
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
          >
            {/* ユーザー送信：URL 貼り付け */}
            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                opacity: msg1Spring,
                transform: `translateY(${(1 - msg1Spring) * 14}px)`,
              }}
            >
              <div
                style={{
                  background: "#06C755",
                  color: "white",
                  borderRadius: "18px 18px 4px 18px",
                  padding: "12px 18px",
                  fontFamily: F.mono,
                  fontSize: 16,
                  maxWidth: "88%",
                  lineHeight: 1.55,
                  wordBreak: "break-all",
                }}
              >
                https://news.yahoo.co.jp/articles/...
              </div>
            </div>

            {/* Bot 即返信 */}
            <div
              style={{
                display: "flex",
                gap: 10,
                opacity: msg2Spring,
                transform: `translateY(${(1 - msg2Spring) * 14}px)`,
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  background: C.green,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "white",
                  fontFamily: F.serifEn,
                  fontWeight: 700,
                  fontSize: 13,
                  flexShrink: 0,
                  alignSelf: "flex-end",
                }}
              >
                DF
              </div>
              <div
                style={{
                  background: "white",
                  color: C.ink,
                  borderRadius: "18px 18px 18px 4px",
                  padding: "14px 18px",
                  fontFamily: F.sans,
                  fontSize: 17,
                  maxWidth: "88%",
                  lineHeight: 1.7,
                  boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                }}
              >
                <span style={{ color: C.warn, fontWeight: 700 }}>
                  ⚠️ 情報構造に注意
                </span>
                <br />
                信頼度 <strong>25%</strong> / 出所：未検証サイト
                <br />
                <span style={{ fontSize: 15, color: C.green }}>
                  一次情報: 厚労省 / WHO / PolitiFact
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 字幕 */}
      <Caption
        text="LINE Bot に URL を送れば、信頼度＋一次情報URLが即返信"
        frame={frame}
        sceneDur={dur}
        fadeInStart={30}
        fadeInEnd={60}
        bottom={36}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F9b: 3エントリ並列（78-83s）— v0.5 新規
// ════════════════════════════════════════════════════════════════════════════
const Scene09b_EntryPoints: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const labelOp = fadeIn(frame, 0, 20);
  const titleOp = fadeIn(frame, 10, 45);
  const dur = T.F9b.dur;

  const entries = [
    {
      icon: "🔧",
      name: "Chrome Extension",
      nameJp: "拡張機能",
      desc: "ブラウザ常駐型\n閲覧中に自動チェック",
      delay: 25,
    },
    {
      icon: "💬",
      name: "LINE Bot",
      nameJp: "公式アカウント",
      desc: "URL を送るだけ\n即返信・障壁ゼロ",
      delay: 50,
    },
    {
      icon: "🖥️",
      name: "Web UI",
      nameJp: "Workbench",
      desc: "ダッシュボード\n精査・履歴・管理",
      delay: 75,
    },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: C.paper }}>
      <SceneLabel num="09b" label="3 エントリポイント" opacity={labelOp} />

      {/* 中央見出し */}
      <div
        style={{
          position: "absolute",
          top: 100,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOp,
        }}
      >
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 54,
            color: C.ink,
            fontWeight: 500,
            letterSpacing: "0.02em",
            lineHeight: 1.4,
          }}
        >
          どこからでも
          <span style={{ color: C.green }}>即チェック</span>
        </div>
        <div
          style={{
            fontFamily: F.sans,
            fontSize: 22,
            color: C.inkMute,
            marginTop: 12,
            letterSpacing: "0.08em",
          }}
        >
          3 エントリポイント（拡張機能 · LINE · Web UI）
        </div>
      </div>

      {/* 3カード横一列 */}
      <div
        style={{
          position: "absolute",
          top: 270,
          left: 80,
          right: 80,
          bottom: 100,
          display: "flex",
          gap: 48,
          alignItems: "stretch",
        }}
      >
        {entries.map((e) => {
          const sp = spring({ frame: frame - e.delay, fps, config: { damping: 200 } });
          return (
            <div
              key={e.name}
              style={{
                flex: 1,
                background: "#FFFFFF",
                borderRadius: 20,
                borderTop: `4px solid ${C.green}`,
                boxShadow: "0 8px 40px rgba(31,31,31,0.10)",
                padding: "52px 44px 44px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 20,
                opacity: sp,
                transform: `translateY(${(1 - sp) * 40}px)`,
              }}
            >
              {/* アイコン */}
              <div
                style={{
                  fontSize: 64,
                  lineHeight: 1,
                }}
              >
                {e.icon}
              </div>

              {/* 名称 */}
              <div style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontFamily: F.serifEn,
                    fontSize: 28,
                    fontWeight: 700,
                    color: C.green,
                    letterSpacing: "0.05em",
                    marginBottom: 6,
                  }}
                >
                  {e.name}
                </div>
                <div
                  style={{
                    fontFamily: F.sans,
                    fontSize: 18,
                    color: C.inkMute,
                    letterSpacing: "0.1em",
                    background: C.greenMute,
                    padding: "4px 16px",
                    borderRadius: 20,
                    display: "inline-block",
                  }}
                >
                  {e.nameJp}
                </div>
              </div>

              {/* 説明 */}
              <div
                style={{
                  fontFamily: F.sans,
                  fontSize: 20,
                  color: C.inkSoft,
                  lineHeight: 1.8,
                  textAlign: "center",
                  letterSpacing: "0.02em",
                  whiteSpace: "pre-line",
                }}
              >
                {e.desc}
              </div>
            </div>
          );
        })}
      </div>

      {/* 字幕 */}
      <Caption
        text="3 エントリ（拡張機能・LINE・Web UI）どこからでも即チェック"
        frame={frame}
        sceneDur={dur}
        fadeInStart={30}
        fadeInEnd={60}
        bottom={36}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// F10: クロージング（83-95s）
// ════════════════════════════════════════════════════════════════════════════
const Scene10_Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgSpring = spring({ frame, fps, config: { damping: 220 } });
  const tagOp = fadeIn(frame, 20, 70);
  const tagY = slideUp(frame, 20, 70, 32);
  const dividerWidth = interpolate(frame, [70, 120], [0, 200], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const productOp = fadeIn(frame, 110, 170);
  const subOp = fadeIn(frame, 150, 220);
  const urlOp = fadeIn(frame, 230, 290);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #1A1F1A 0%, #0D1A0E 100%)`,
        justifyContent: "center",
        alignItems: "center",
        padding: 120,
        opacity: bgSpring,
      }}
    >
      {/* 格子背景 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(rgba(45,90,64,0.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(45,90,64,0.06) 1px, transparent 1px)`,
          backgroundSize: "80px 80px",
        }}
      />

      {/* タグライン */}
      <div
        style={{
          opacity: tagOp,
          transform: `translateY(${tagY}px)`,
          textAlign: "center",
          zIndex: 1,
        }}
      >
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 80,
            color: "#F4F1E8",
            lineHeight: 1.65,
            letterSpacing: "0.04em",
            fontWeight: 500,
          }}
        >
          医師の習慣を、
          <br />
          社会の
          <span style={{ color: C.termGreen }}> 真実層 </span>
          に。
        </div>
      </div>

      {/* 区切り線 */}
      <div
        style={{
          width: dividerWidth,
          height: 1,
          background: C.green,
          marginTop: 48,
          zIndex: 1,
        }}
      />

      {/* プロダクト名 */}
      <div
        style={{
          opacity: productOp,
          zIndex: 1,
          marginTop: 36,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily: F.serifEn,
            fontSize: 48,
            color: "#F4F1E8",
            letterSpacing: "0.15em",
            fontWeight: 600,
          }}
        >
          DeepFact Validator
        </div>
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 24,
            color: C.termGreen,
            letterSpacing: "0.2em",
            marginTop: 12,
          }}
        >
          情報の Observability
        </div>
      </div>

      {/* サブライン */}
      <div
        style={{
          opacity: subOp,
          zIndex: 1,
          marginTop: 40,
          textAlign: "center",
          fontFamily: F.sans,
          fontSize: 22,
          color: "rgba(200,216,200,0.6)",
          letterSpacing: "0.1em",
          lineHeight: 1.8,
        }}
      >
        Watcher · Investigator · Validator — 3 Agents · Human-in-the-Loop · CI/CD
        <br />
        DevOps × AI Agent Hackathon 2026 — by Liberaiz
      </div>

      {/* URL */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: urlOp,
          fontFamily: F.mono,
          fontSize: 18,
          color: "rgba(100,150,100,0.6)",
          letterSpacing: "0.05em",
        }}
      >
        deepfact-validator-kjciocymea-an.a.run.app — Cloud Run rev 00013
      </div>
    </AbsoluteFill>
  );
};
