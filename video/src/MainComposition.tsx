import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { FONT_FAMILIES } from "./load-fonts";

const FPS = 30;

const TIMELINE = {
  HOOK: { from: 0, duration: 8 * FPS },
  LINE: { from: 8 * FPS, duration: 14 * FPS },
  CHROME: { from: 22 * FPS, duration: 16 * FPS },
  WEBUI: { from: 38 * FPS, duration: 14 * FPS },
  OUTRO: { from: 52 * FPS, duration: 8 * FPS },
};

const C = {
  paper: "#F8F6F1",
  paperWarm: "#EFEBE0",
  paperDeep: "#E2DCC8",
  ink: "#1B2A4E",
  inkDeep: "#131F3B",
  inkSoft: "#2A3B66",
  inkMute: "rgba(27, 42, 78, 0.55)",
  inkFaint: "rgba(27, 42, 78, 0.32)",
  gold: "#C9A55C",
  goldDeep: "#A38440",
  goldSoft: "rgba(201, 165, 92, 0.25)",
  safe: "#3D8A55",
  warn: "#C8453B",
  rule: "rgba(27, 42, 78, 0.12)",
  ruleSoft: "rgba(27, 42, 78, 0.06)",
};

const F = FONT_FAMILIES;

export const MainComposition: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: C.ink }}>
      <Sequence from={TIMELINE.HOOK.from} durationInFrames={TIMELINE.HOOK.duration}>
        <HookScene />
      </Sequence>
      <Sequence from={TIMELINE.LINE.from} durationInFrames={TIMELINE.LINE.duration}>
        <LineBotScene />
      </Sequence>
      <Sequence from={TIMELINE.CHROME.from} durationInFrames={TIMELINE.CHROME.duration}>
        <ChromeExtScene />
      </Sequence>
      <Sequence from={TIMELINE.WEBUI.from} durationInFrames={TIMELINE.WEBUI.duration}>
        <WebUIScene />
      </Sequence>
      <Sequence from={TIMELINE.OUTRO.from} durationInFrames={TIMELINE.OUTRO.duration}>
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};

const HookScene: React.FC = () => {
  const frame = useCurrentFrame();
  const line1 = interpolate(frame, [0, 28], [0, 1], { extrapolateRight: "clamp" });
  const line2 = interpolate(frame, [70, 100], [0, 1], { extrapolateRight: "clamp" });
  const line1Y = interpolate(frame, [0, 28], [12, 0], { extrapolateRight: "clamp" });
  const line2Y = interpolate(frame, [70, 100], [12, 0], { extrapolateRight: "clamp" });
  const rule = interpolate(frame, [110, 150], [0, 80], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: C.paper,
        justifyContent: "center",
        alignItems: "center",
        padding: 80,
      }}
    >
      <div
        style={{
          color: C.ink,
          fontFamily: F.serifJp,
          fontSize: 78,
          textAlign: "center",
          lineHeight: 1.55,
          letterSpacing: "-0.04em",
          fontWeight: 600,
          whiteSpace: "nowrap",
        }}
      >
        <div style={{ opacity: line1, transform: `translateY(${line1Y}px)` }}>
          この情報過多社会、
        </div>
        <div
          style={{
            opacity: line2,
            transform: `translateY(${line2Y}px)`,
            marginTop: 28,
          }}
        >
          あなたが目にするその情報は真実ですか？
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 120,
          width: rule,
          height: 2,
          background: C.gold,
        }}
      />
    </AbsoluteFill>
  );
};

const SceneFrame: React.FC<{
  label: string;
  title: string;
  children?: React.ReactNode;
}> = ({ label, title, children }) => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: C.paper, padding: 96, opacity: fade }}>
      <div
        style={{
          fontFamily: F.serifEn,
          fontSize: 22,
          color: C.gold,
          letterSpacing: "0.25em",
          textTransform: "uppercase",
          marginBottom: 12,
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: F.serifJp,
          fontSize: 60,
          color: C.ink,
          letterSpacing: "-0.03em",
          marginBottom: 56,
          fontWeight: 700,
        }}
      >
        {title}
      </div>
      <div style={{ flex: 1, display: "flex", gap: 48, alignItems: "stretch" }}>{children}</div>
    </AbsoluteFill>
  );
};

const SectionHeading: React.FC<{ text: string; opacity: number; translateY: number }> = ({
  text,
  opacity,
  translateY,
}) => (
  <div
    style={{
      fontFamily: F.serifEn,
      fontSize: 18,
      color: C.gold,
      letterSpacing: "0.25em",
      textTransform: "uppercase",
      marginBottom: 20,
      fontWeight: 600,
      opacity,
      transform: `translateY(${translateY}px)`,
    }}
  >
    {text}
  </div>
);

const LineBotScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const headerSpring = spring({
    frame: frame - 30,
    fps,
    config: { damping: 200 },
  });

  const EVIDENCE = [
    { icon: "🏛", name: "厚生労働省", domain: "mhlw.go.jp" },
    { icon: "💊", name: "PMDA", domain: "pmda.go.jp" },
    { icon: "🌐", name: "WHO", domain: "who.int" },
    { icon: "🔍", name: "日本ファクトチェックセンター", domain: "factcheckcenter.jp" },
    { icon: "🛡️", name: "Snopes", domain: "snopes.com" },
  ];

  return (
    <SceneFrame label="Entry 01 · LINE Bot" title="URL を投げると 即返信">
      {/* 左: LINE バブル UI */}
      <div
        style={{
          background: "#06C755",
          color: C.paper,
          padding: 56,
          borderRadius: 24,
          width: 560,
          fontFamily: F.sans,
          fontSize: 24,
          lineHeight: 1.6,
          display: "flex",
          flexDirection: "column",
          gap: 16,
          alignSelf: "center",
          boxShadow: "0 12px 40px rgba(6,199,85,0.18)",
        }}
      >
        <div style={{ fontSize: 18, opacity: 0.85 }}>You</div>
        <div
          style={{
            background: "rgba(255,255,255,0.18)",
            borderRadius: 16,
            padding: 20,
            wordBreak: "break-all",
          }}
        >
          https://example.com/fake-news-article
        </div>
        <div style={{ fontSize: 18, opacity: 0.85, marginTop: 16 }}>DeepFact Validator</div>
        <div
          style={{
            background: "#FFFFFF",
            color: C.ink,
            borderRadius: 16,
            padding: 24,
            fontFamily: F.serifJp,
          }}
        >
          <div style={{ fontSize: 36, fontWeight: 700, color: C.warn, marginBottom: 8 }}>
            🚨 警告
          </div>
          <div style={{ fontFamily: F.serifEn, fontSize: 28, color: C.warn, fontWeight: 600 }}>
            20%
          </div>
          <div style={{ fontFamily: F.sans, fontSize: 18, marginTop: 16, color: C.inkMute }}>
            📚 厚労省 / PMDA / WHO
          </div>
        </div>
      </div>

      {/* 右: 判定エビデンスカード（5枚・spring立ち上がり） */}
      <div
        style={{
          flex: 1,
          alignSelf: "stretch",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <SectionHeading
          text="📚 Evidence · 公的機関ソース"
          opacity={headerSpring}
          translateY={(1 - headerSpring) * 12}
        />
        {EVIDENCE.map((ev, idx) => {
          const cardSpring = spring({
            frame: frame - 60 - idx * 16,
            fps,
            config: { damping: 200 },
          });
          return (
            <div
              key={ev.domain}
              style={{
                background: C.paper,
                border: `1px solid ${C.rule}`,
                borderRadius: 14,
                padding: "20px 28px",
                marginBottom: 14,
                fontFamily: F.sans,
                display: "flex",
                alignItems: "center",
                gap: 20,
                opacity: cardSpring,
                transform: `translateY(${(1 - cardSpring) * 24}px)`,
                boxShadow: "0 4px 16px rgba(27,42,78,0.06)",
              }}
            >
              <span style={{ fontSize: 36, lineHeight: 1 }}>{ev.icon}</span>
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    fontFamily: F.serifJp,
                    fontSize: 22,
                    color: C.ink,
                    fontWeight: 700,
                    letterSpacing: "-0.02em",
                  }}
                >
                  {ev.name}
                </div>
                <div
                  style={{
                    fontFamily: F.mono,
                    fontSize: 16,
                    color: C.inkMute,
                    marginTop: 2,
                  }}
                >
                  {ev.domain}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </SceneFrame>
  );
};

const ChromeExtScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const headerSpring = spring({
    frame: frame - 30,
    fps,
    config: { damping: 200 },
  });

  // メーター 0→20 カウントアップ
  const meterValue = Math.round(
    interpolate(frame, [60, 120], [0, 20], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );
  const meterWidth = interpolate(frame, [60, 120], [0, 20], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const STRUCTURE = [
    { title: "論理的飛躍", desc: "証拠なき断定" },
    { title: "煽動的構造", desc: "感情強度 0.92" },
    { title: "権威の曖昧な利用", desc: "出典不明 3 件" },
  ];

  return (
    <SceneFrame label="Entry 02 · Chrome Extension" title="閲覧中のページに 常時介入">
      {/* 左: Chrome Extension popup */}
      <div
        style={{
          background: C.paper,
          border: `1px solid ${C.rule}`,
          borderRadius: 20,
          padding: 48,
          width: 460,
          fontFamily: F.sans,
          color: C.ink,
          boxShadow: "0 12px 40px rgba(27,42,78,0.10)",
          alignSelf: "center",
        }}
      >
        <div
          style={{
            fontFamily: F.serifEn,
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: "0.03em",
            marginBottom: 4,
          }}
        >
          DeepFact Validator
        </div>
        <div
          style={{
            fontFamily: F.serifJp,
            fontSize: 11,
            color: C.inkMute,
            letterSpacing: "0.2em",
            marginBottom: 32,
          }}
        >
          情報の Observability
        </div>
        <div
          style={{
            width: 200,
            height: 200,
            borderRadius: "50%",
            border: `8px solid ${C.warn}`,
            display: "grid",
            placeItems: "center",
            margin: "0 auto 24px",
          }}
        >
          <div
            style={{
              fontFamily: F.serifJp,
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: "0.15em",
              color: C.warn,
            }}
          >
            警告
          </div>
        </div>
        <div
          style={{
            textAlign: "center",
            fontFamily: F.serifEn,
            fontSize: 17,
            color: C.warn,
            fontWeight: 600,
          }}
        >
          {meterValue}% 🚨
        </div>
      </div>

      {/* 右: 分析結果（信頼度バー + 構造観察3カード） */}
      <div
        style={{
          flex: 1,
          alignSelf: "stretch",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <SectionHeading
          text="📊 Analysis · 構造観察"
          opacity={headerSpring}
          translateY={(1 - headerSpring) * 12}
        />

        {/* 信頼度バー */}
        <div style={{ marginBottom: 36, opacity: headerSpring }}>
          <div
            style={{
              fontFamily: F.serifEn,
              fontSize: 14,
              color: C.inkMute,
              letterSpacing: "0.25em",
              marginBottom: 10,
            }}
          >
            CONFIDENCE
          </div>
          <div
            style={{
              background: C.paperWarm,
              borderRadius: 8,
              height: 14,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                background: C.warn,
                height: "100%",
                width: `${meterWidth}%`,
              }}
            />
          </div>
          <div
            style={{
              fontFamily: F.serifEn,
              fontSize: 56,
              color: C.warn,
              fontWeight: 700,
              marginTop: 12,
              letterSpacing: "-0.04em",
            }}
          >
            {meterValue}%
            <span
              style={{
                fontFamily: F.serifJp,
                fontSize: 22,
                color: C.warn,
                fontWeight: 700,
                letterSpacing: "0.15em",
                marginLeft: 16,
              }}
            >
              警告
            </span>
          </div>
        </div>

        {/* 構造観察 3カード */}
        {STRUCTURE.map((s, idx) => {
          const cardSpring = spring({
            frame: frame - 120 - idx * 16,
            fps,
            config: { damping: 200 },
          });
          return (
            <div
              key={s.title}
              style={{
                background: C.paper,
                border: `1px solid ${C.rule}`,
                borderRadius: 14,
                padding: "18px 28px",
                marginBottom: 12,
                fontFamily: F.sans,
                display: "flex",
                alignItems: "baseline",
                gap: 20,
                opacity: cardSpring,
                transform: `translateY(${(1 - cardSpring) * 20}px)`,
                boxShadow: "0 4px 16px rgba(27,42,78,0.05)",
              }}
            >
              <div
                style={{
                  fontFamily: F.serifEn,
                  fontSize: 18,
                  color: C.gold,
                  fontWeight: 600,
                  width: 32,
                }}
              >
                0{idx + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    fontFamily: F.serifJp,
                    fontSize: 22,
                    color: C.ink,
                    fontWeight: 700,
                    letterSpacing: "-0.02em",
                  }}
                >
                  {s.title}
                </div>
                <div
                  style={{
                    fontFamily: F.sans,
                    fontSize: 16,
                    color: C.inkMute,
                    marginTop: 2,
                  }}
                >
                  {s.desc}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </SceneFrame>
  );
};

const WebUIScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const stackSpring = spring({
    frame: frame - 140,
    fps,
    config: { damping: 200 },
  });
  const validateSpring = spring({
    frame: frame - 180,
    fps,
    config: { damping: 200 },
  });

  return (
    <SceneFrame label="Entry 03 · Web UI Workbench" title="3エージェントの判定 一画面で">
      <div
        style={{
          width: "100%",
          display: "flex",
          flexDirection: "column",
          gap: 28,
        }}
      >
        {/* 上: Workbench カード */}
        <div
          style={{
            background: C.paper,
            border: `1px solid ${C.rule}`,
            borderRadius: 20,
            padding: 44,
            fontFamily: F.sans,
            color: C.ink,
            display: "grid",
            gridTemplateColumns: "1fr 1.8fr",
            gap: 48,
            boxShadow: "0 8px 32px rgba(27,42,78,0.08)",
          }}
        >
          <div>
            <div
              style={{
                fontFamily: F.serifEn,
                fontSize: 14,
                color: C.gold,
                letterSpacing: "0.25em",
                textTransform: "uppercase",
                marginBottom: 12,
              }}
            >
              Confidence
            </div>
            <div
              style={{
                fontFamily: F.serifEn,
                fontSize: 84,
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
                fontFamily: F.serifJp,
                fontSize: 22,
                color: C.warn,
                fontWeight: 700,
                letterSpacing: "0.15em",
                marginTop: 6,
              }}
            >
              警告
            </div>
          </div>
          <div>
            <div
              style={{
                fontFamily: F.serifEn,
                fontSize: 14,
                color: C.gold,
                letterSpacing: "0.25em",
                textTransform: "uppercase",
                marginBottom: 12,
              }}
            >
              Structural Observations
            </div>
            <ul
              style={{
                listStyle: "none",
                padding: 0,
                margin: 0,
                fontFamily: F.serifJp,
                fontSize: 22,
                lineHeight: 1.75,
                color: C.ink,
              }}
            >
              <li>— 論理的飛躍：証拠なき断定</li>
              <li>— 煽動的構造：感情強度 0.92</li>
              <li>— 権威の曖昧な利用：出典不明 3 件</li>
            </ul>
            <div
              style={{
                marginTop: 16,
                fontFamily: F.serifEn,
                fontSize: 13,
                color: C.inkMute,
                letterSpacing: "0.1em",
              }}
            >
              EVIDENCE · 厚労省 · PMDA · WHO · Snopes · JFC
            </div>
          </div>
        </div>

        {/* 下: 補足要素2枚 grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 24,
          }}
        >
          {/* 技術スタック */}
          <div
            style={{
              background: C.paper,
              border: `1px solid ${C.rule}`,
              borderRadius: 16,
              padding: 28,
              fontFamily: F.sans,
              color: C.ink,
              opacity: stackSpring,
              transform: `translateY(${(1 - stackSpring) * 20}px)`,
              boxShadow: "0 4px 16px rgba(27,42,78,0.05)",
            }}
          >
            <div
              style={{
                fontFamily: F.serifEn,
                fontSize: 13,
                color: C.gold,
                letterSpacing: "0.25em",
                textTransform: "uppercase",
                marginBottom: 12,
              }}
            >
              ⚙️ Technical Stack
            </div>
            <div
              style={{
                fontFamily: F.serifJp,
                fontSize: 18,
                color: C.ink,
                lineHeight: 1.7,
                fontWeight: 600,
              }}
            >
              Cloud Run · Vertex AI Gemini 2.5
              <br />
              FastAPI · LINE Messaging API
              <br />
              Chrome Extension · Firestore
            </div>
          </div>

          {/* 実機検証 */}
          <div
            style={{
              background: C.paper,
              border: `1px solid ${C.rule}`,
              borderRadius: 16,
              padding: 28,
              fontFamily: F.sans,
              color: C.ink,
              opacity: validateSpring,
              transform: `translateY(${(1 - validateSpring) * 20}px)`,
              boxShadow: "0 4px 16px rgba(27,42,78,0.05)",
            }}
          >
            <div
              style={{
                fontFamily: F.serifEn,
                fontSize: 13,
                color: C.gold,
                letterSpacing: "0.25em",
                textTransform: "uppercase",
                marginBottom: 12,
              }}
            >
              📊 Empirical Validation
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 24,
                fontFamily: F.serifEn,
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 42,
                    fontWeight: 700,
                    color: C.ink,
                    letterSpacing: "-0.04em",
                    lineHeight: 1,
                  }}
                >
                  78pt
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: C.inkMute,
                    letterSpacing: "0.15em",
                    marginTop: 4,
                  }}
                >
                  CONFIDENCE GAP
                </div>
              </div>
              <div>
                <div
                  style={{
                    fontSize: 42,
                    fontWeight: 700,
                    color: C.ink,
                    letterSpacing: "-0.04em",
                    lineHeight: 1,
                  }}
                >
                  6
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: C.inkMute,
                    letterSpacing: "0.15em",
                    marginTop: 4,
                  }}
                >
                  TEST PATTERNS
                </div>
              </div>
              <div>
                <div
                  style={{
                    fontSize: 42,
                    fontWeight: 700,
                    color: C.ink,
                    letterSpacing: "-0.04em",
                    lineHeight: 1,
                  }}
                >
                  100%
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: C.inkMute,
                    letterSpacing: "0.15em",
                    marginTop: 4,
                  }}
                >
                  REPLAY MATCH
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </SceneFrame>
  );
};

const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = spring({ frame, fps, config: { damping: 200 } });
  const subFade = interpolate(frame, [30, 70], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: C.paper,
        justifyContent: "center",
        alignItems: "center",
        padding: 100,
        opacity: fade,
      }}
    >
      <div
        style={{
          color: C.ink,
          fontFamily: F.serifJp,
          fontSize: 64,
          letterSpacing: "-0.04em",
          textAlign: "center",
          marginBottom: 36,
          fontWeight: 700,
        }}
      >
        情報の Observability を 社会に
      </div>
      <div
        style={{
          width: 60,
          height: 1,
          background: C.gold,
          marginBottom: 28,
          opacity: subFade,
        }}
      />
      <div
        style={{
          color: C.ink,
          fontFamily: F.serifEn,
          fontSize: 30,
          letterSpacing: "0.15em",
          opacity: subFade,
          marginBottom: 8,
          fontWeight: 600,
        }}
      >
        DeepFact Validator
      </div>
      <div
        style={{
          color: C.inkMute,
          fontFamily: F.sans,
          fontSize: 18,
          letterSpacing: "0.1em",
          opacity: subFade,
        }}
      >
        by Liberaiz
      </div>
    </AbsoluteFill>
  );
};
