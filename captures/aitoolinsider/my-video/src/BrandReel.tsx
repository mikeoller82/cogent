import {useCurrentFrame, useVideoConfig, AbsoluteFill, interpolate, Audio, staticFile} from 'remotion';
import React from 'react';

const BG = '#050D1A';
const CYAN = '#00D4FF';
const GOLD = '#FFD700';
const GREEN = '#00FF88';
const MUTED = '#7A9BBF';
const WHITE = '#FFFFFF';

const SceneTitle: React.FC<{children: React.ReactNode; color?: string; size?: number}> = ({children, color = WHITE, size = 72}) => (
  <h1 style={{fontSize: size, fontWeight: 900, color, lineHeight: 1.1, letterSpacing: '-1px', margin: 0, textAlign: 'center'}}>
    {children}
  </h1>
);

const SceneSubtitle: React.FC<{children: React.ReactNode}> = ({children}) => (
  <p style={{fontSize: 28, color: MUTED, lineHeight: 1.5, maxWidth: 1100, margin: '16px 0 0 0', textAlign: 'center'}}>
    {children}
  </p>
);

const Badge: React.FC<{children: React.ReactNode; color?: string}> = ({children, color = CYAN}) => (
  <div style={{
    display: 'inline-block',
    padding: '6px 16px',
    borderRadius: 20,
    fontSize: 14,
    fontWeight: 700,
    letterSpacing: '1px',
    textTransform: 'uppercase',
    background: color === CYAN ? 'rgba(0,212,255,0.15)' : color === GOLD ? 'rgba(255,215,0,0.15)' : 'rgba(0,255,136,0.15)',
    color,
    border: `1px solid ${color === CYAN ? 'rgba(0,212,255,0.3)' : color === GOLD ? 'rgba(255,215,0,0.3)' : 'rgba(0,255,136,0.3)'}`,
    marginBottom: 20
  }}>
    {children}
  </div>
);

const AccentLine: React.FC<{color?: string}> = ({color = CYAN}) => (
  <div style={{width: 60, height: 3, background: color, margin: '24px 0', borderRadius: 2}} />
);

const StatNumber: React.FC<{children: React.ReactNode; color?: string}> = ({children, color = CYAN}) => (
  <div style={{fontSize: 56, fontWeight: 900, color, lineHeight: 1}}>{children}</div>
);

const StatLabel: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div style={{fontSize: 16, color: MUTED, marginTop: 4, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px'}}>{children}</div>
);

const FadeInUp: React.FC<{children: React.ReactNode; frame: number; delay?: number; duration?: number; y?: number; hold?: boolean}> = ({
  children, frame, delay = 0, duration = 20, y = 40, hold = false
}) => {
  const progress = interpolate(frame - delay, [0, duration], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: hold ? 'clamp' : undefined});
  return (
    <div style={{
      opacity: progress,
      transform: `translateY(${(1 - progress) * y}px)`,
    }}>
      {children}
    </div>
  );
};

const RadBg: React.FC<{offset?: number}> = ({offset = 0}) => (
  <div style={{
    position: 'absolute', inset: 0,
    background: `radial-gradient(ellipse at ${offset % 100}% ${(offset * 37) % 100}%, rgba(0,212,255,0.07) 0%, transparent 65%)`
  }} />
);

const Scene: React.FC<{
  children: React.ReactNode;
  frame: number;
  start: number;
  end: number;
  bgOffset?: number;
}> = ({children, frame, start, end, bgOffset = 0}) => {
  const visible = frame >= start && frame < end;
  if (!visible) return null;
  const fadeIn = interpolate(frame - start, [0, 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame - (end - 10), [0, 10], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{
      opacity: Math.min(fadeIn, fadeOut),
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '80px 160px',
      textAlign: 'center',
    }}>
      <RadBg offset={bgOffset} />
      {children}
    </AbsoluteFill>
  );
};

export const BrandReel: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill style={{background: BG}}>
      {/* Audio track */}
      <Audio src={staticFile('narration.mp3')} />

      {/* SCENE 1: Hook (0-6s = 0-180f) */}
      <Scene frame={frame} start={0} end={180} bgOffset={0}>
        <FadeInUp frame={frame} delay={5} hold>
          <Badge>✦ Brand Reel</Badge>
        </FadeInUp>
        <FadeInUp frame={frame} delay={20} y={50} hold>
          <SceneTitle size={68}>
            Most AI newsletters<br />
            recycle <span style={{color: MUTED}}>TechCrunch headlines</span>.
          </SceneTitle>
        </FadeInUp>
        <FadeInUp frame={frame} delay={70} y={30} hold>
          <AccentLine />
        </FadeInUp>
        <FadeInUp frame={frame} delay={85} y={20} hold>
          <div style={{fontSize: 32, color: WHITE, fontWeight: 700}}>This one runs tools in production.</div>
        </FadeInUp>
      </Scene>

      {/* SCENE 2: Early Access (6-14s = 180-420f) */}
      <Scene frame={frame} start={180} end={420} bgOffset={40}>
        <FadeInUp frame={frame} delay={185} hold>
          <Badge color={GOLD}>⚡ Early Adopter Window</Badge>
        </FadeInUp>
        <FadeInUp frame={frame} delay={200} y={50} hold>
          <SceneTitle size={56}>
            I test every tool<br />
            the week it launches.
          </SceneTitle>
        </FadeInUp>
        <FadeInUp frame={frame} delay={260} y={20} hold>
          <AccentLine color={GOLD} />
        </FadeInUp>
        <FadeInUp frame={frame} delay={280} hold>
          <SceneSubtitle>
            Before the hype. Before the price goes up.<br />
            You get the <span style={{color: GOLD, fontWeight: 700}}>early-adopter window</span>, not the aftermath.
          </SceneSubtitle>
        </FadeInUp>
      </Scene>

      {/* SCENE 3: Curation (14-20s = 420-600f) */}
      <Scene frame={frame} start={420} end={600} bgOffset={80}>
        <FadeInUp frame={frame} delay={425} hold>
          <Badge>📋 Curated Weekly</Badge>
        </FadeInUp>
        <FadeInUp frame={frame} delay={440} y={50} hold>
          <SceneTitle size={64}>Five tools per week.</SceneTitle>
        </FadeInUp>
        <FadeInUp frame={frame} delay={470} hold>
          <SceneTitle size={64} color={CYAN}>Zero filler.</SceneTitle>
        </FadeInUp>
        <FadeInUp frame={frame} delay={500} y={20} hold>
          <AccentLine />
        </FadeInUp>
        <FadeInUp frame={frame} delay={520} hold>
          <SceneSubtitle>
            Each one tested for <span style={{color: CYAN, fontWeight: 700}}>thirty days</span> in real workflows.
          </SceneSubtitle>
        </FadeInUp>
      </Scene>

      {/* SCENE 4: Stats (20-26s = 600-780f) */}
      <Scene frame={frame} start={600} end={780} bgOffset={120}>
        <FadeInUp frame={frame} delay={605} hold>
          <Badge color={GREEN}>📊 By the Numbers</Badge>
        </FadeInUp>
        <FadeInUp frame={frame} delay={620} y={40} hold>
          <div style={{display: 'flex', gap: 80, alignItems: 'center', justifyContent: 'center'}}>
            <div style={{textAlign: 'center'}}>
              <StatNumber color={CYAN}>90+</StatNumber>
              <StatLabel>Tools Reviewed</StatLabel>
            </div>
            <div style={{textAlign: 'center'}}>
              <StatNumber color={GREEN}>12</StatNumber>
              <StatLabel>Categories</StatLabel>
            </div>
            <div style={{textAlign: 'center'}}>
              <StatNumber color={GOLD}>1</StatNumber>
              <StatLabel>Honest Verdict</StatLabel>
            </div>
          </div>
        </FadeInUp>
        <FadeInUp frame={frame} delay={680} y={20} hold>
          <AccentLine color={GREEN} />
        </FadeInUp>
        <FadeInUp frame={frame} delay={700} hold>
          <SceneSubtitle>No fluff. Just what actually works.</SceneSubtitle>
        </FadeInUp>
      </Scene>

      {/* SCENE 5: Free CTA (26-31s = 780-960f) */}
      <Scene frame={frame} start={780} end={960} bgOffset={60}>
        <FadeInUp frame={frame} delay={785} hold>
          <Badge color={GOLD}>🎁 Free Weekly Drop</Badge>
        </FadeInUp>
        <FadeInUp frame={frame} delay={800} y={50} hold>
          <SceneTitle size={60}>
            Free every <span style={{color: CYAN}}>Monday</span>.
          </SceneTitle>
        </FadeInUp>
        <FadeInUp frame={frame} delay={830} y={20} hold>
          <div style={{display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16}}>
            {['No credit card required', 'No spam. Ever.', 'Curated by a human'].map((item, i) => (
              <div key={i} style={{display: 'flex', alignItems: 'center', gap: 12, fontSize: 22, color: WHITE, opacity: interpolate(frame - (830 + i * 20), [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
                <span style={{color: GREEN, fontSize: 26, fontWeight: 900}}>✓</span>
                {item}
              </div>
            ))}
          </div>
        </FadeInUp>
      </Scene>

      {/* SCENE 6: Closing (32-47s = 960-1450f) */}
      <Scene frame={frame} start={960} end={1450} bgOffset={20}>
        <FadeInUp frame={frame} delay={965} hold>
          <Badge color={CYAN}>🔔 Get the Drop</Badge>
        </FadeInUp>
        <FadeInUp frame={frame} delay={980} y={50} hold>
          <SceneTitle size={52}>
            Get the drop <span style={{color: CYAN}}>before everyone else</span>.
          </SceneTitle>
        </FadeInUp>
        <FadeInUp frame={frame} delay={1015} y={20} hold>
          <div style={{width: 60, height: 3, background: CYAN, margin: '20px auto', borderRadius: 2}} />
        </FadeInUp>
        <FadeInUp frame={frame} delay={1030} hold>
          <div style={{fontSize: 40, fontWeight: 900, color: WHITE, letterSpacing: 8, textTransform: 'uppercase'}}>
            AI<span style={{color: CYAN}}>Tool</span>Insider
          </div>
        </FadeInUp>
      </Scene>
    </AbsoluteFill>
  );
};
