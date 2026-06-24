import React, { useState, useEffect } from 'react';
import useProfileStore from '../../store/profileStore.js';
import useGameStore from '../../store/gameStore.js';
import { AGE_CONFIGS } from '../../data/curriculum.js';
import { COLOR_PAINTER_SHAPES } from '../../data/categories.js';
import { calcRoundXp, calcStars } from '../../engine/progression.js';
import { speak } from '../../engine/speech.js';
import { sfx } from '../../engine/audio.js';
import Robi from '../../components/Robi/Robi.jsx';
import LevelHud from '../../components/ui/LevelHud.jsx';

const ALL_COLORS = ['red','blue','yellow','green','pink','orange','purple','white'];

const COLOR_HEX = {
  red: '#F44336', blue: '#2196F3', yellow: '#FFD600',
  green: '#4CAF50', pink: '#FF80AB', orange: '#FF9800',
  purple: '#9C27B0', white: '#F5F5F5',
};

function ShapeDisplay({ shape, filledColor }) {
  const fill = filledColor ? COLOR_HEX[filledColor] : '#e0e0e0';
  const stroke = '#ccc';
  const s = 120;

  const shapes = {
    sun:    <circle cx={s/2} cy={s/2} r={s*0.38} fill={fill} stroke={stroke} strokeWidth="3" />,
    heart:  <path d={`M${s/2} ${s*0.78} C${s*0.1} ${s*0.55} ${s*0.08} ${s*0.2} ${s/2} ${s*0.35} C${s*0.92} ${s*0.2} ${s*0.9} ${s*0.55} ${s/2} ${s*0.78}Z`} fill={fill} stroke={stroke} strokeWidth="3" />,
    star:   <polygon points={starPoints(s/2,s/2,s*0.42,s*0.17,5)} fill={fill} stroke={stroke} strokeWidth="3" />,
    cloud:  <><ellipse cx={s*0.5} cy={s*0.62} rx={s*0.38} ry={s*0.2} fill={fill} stroke={stroke} strokeWidth="2" /><ellipse cx={s*0.35} cy={s*0.52} rx={s*0.22} ry={s*0.18} fill={fill} stroke={stroke} strokeWidth="2" /><ellipse cx={s*0.62} cy={s*0.48} rx={s*0.2} ry={s*0.17} fill={fill} stroke={stroke} strokeWidth="2" /></>,
    flower: <><circle cx={s/2} cy={s/2} r={s*0.15} fill={fill} stroke={stroke} strokeWidth="2" />{[0,60,120,180,240,300].map(a=><ellipse key={a} cx={s/2+Math.cos(a*Math.PI/180)*s*0.25} cy={s/2+Math.sin(a*Math.PI/180)*s*0.25} rx={s*0.12} ry={s*0.18} fill={fill} stroke={stroke} strokeWidth="1.5" transform={`rotate(${a},${s/2+Math.cos(a*Math.PI/180)*s*0.25},${s/2+Math.sin(a*Math.PI/180)*s*0.25})`} />)}</>,
    house:  <><rect x={s*0.2} y={s*0.45} width={s*0.6} height={s*0.42} rx="4" fill={fill} stroke={stroke} strokeWidth="3" /><polygon points={`${s/2},${s*0.15} ${s*0.12},${s*0.48} ${s*0.88},${s*0.48}`} fill={fill} stroke={stroke} strokeWidth="3" /></>,
  };

  return (
    <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`}>
      {shapes[shape] ?? shapes.star}
    </svg>
  );
}

function starPoints(cx, cy, outerR, innerR, points) {
  let pts = '';
  for (let i = 0; i < points * 2; i++) {
    const r = i % 2 === 0 ? outerR : innerR;
    const angle = (i * Math.PI) / points - Math.PI / 2;
    pts += `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)} `;
  }
  return pts.trim();
}

export default function ColorPainter() {
  const profile     = useProfileStore(s => s.activeProfile());
  const finishRound = useGameStore(s => s.finishRound);
  const setRobiMood = useGameStore(s => s.setRobiMood);
  const robiMood    = useGameStore(s => s.robiMood);

  const ageMode = profile?.ageMode ?? 'amy';
  const config  = AGE_CONFIGS[ageMode];

  const [queue] = useState(() => shuffle([...COLOR_PAINTER_SHAPES]).slice(0, config.roundSize));
  const [qIdx, setQIdx] = useState(0);
  const [buckets, setBuckets] = useState([]);
  const [filledColor, setFilledColor] = useState(null);
  const [bucketState, setBucketState] = useState({});
  const [correct, setCorrect] = useState(0);
  const [answered, setAnswered] = useState(false);

  const current = queue[qIdx];

  useEffect(() => {
    if (!current) return;
    const distractors = shuffle(ALL_COLORS.filter(c => c !== current.color)).slice(0, 4);
    setBuckets(shuffle([current.color, ...distractors]));
    setFilledColor(null);
    setBucketState({});
    setAnswered(false);
    setRobiMood('idle');
    speak(`Paint it ${current.color}!`, 'en-US');
  }, [qIdx]);

  function handleBucketTap(color) {
    if (answered) return;
    setAnswered(true);

    if (color === current.color) {
      sfx.correct();
      setFilledColor(color);
      setBucketState({ [color]: 'correct' });
      setCorrect(c => c + 1);
      setRobiMood('happy');
    } else {
      sfx.wrong();
      setBucketState({ [color]: 'wrong' });
      setRobiMood('oops');
      setTimeout(() => {
        setBucketState({});
        setAnswered(false);
      }, 600);
      return;
    }

    setTimeout(() => advance(), 1300);
  }

  function advance() {
    if (qIdx + 1 >= queue.length) {
      const total = queue.length;
      finishRound({ correct, total, xpEarned: calcRoundXp(correct, total, config.xpMultiplier), stars: calcStars(correct, total), leveledUp: false });
    } else {
      setQIdx(i => i + 1);
    }
  }

  if (!current) return null;

  const isHe = profile?.lang === 'he';
  const scale = config.tileScale;

  return (
    <div style={gameWrap}>
      <div style={{ position: 'fixed', top: 12, left: 12, right: 12, display: 'flex', justifyContent: 'space-between', zIndex: 10 }}>
        <LevelHud />
        <ProgressPips total={queue.length} current={qIdx} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 70 }}>
        <Robi mood={robiMood} size={80} />
      </div>

      <div style={{ textAlign: 'center', marginTop: 12, fontFamily: "'Baloo 2', system-ui", fontSize: 20, fontWeight: 700, color: '#5B4B8A' }}>
        🎨 {isHe ? 'צבעי את' : 'Paint it'} <em>{current.color}</em>!
      </div>

      {/* Shape */}
      <div style={{ margin: '16px auto', display: 'flex', justifyContent: 'center', animation: filledColor ? 'popIn 0.3s ease-out' : undefined }}>
        <ShapeDisplay shape={current.shape} filledColor={filledColor} />
      </div>

      {/* Color buckets */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 * scale, justifyContent: 'center', marginTop: 8, padding: '0 12px' }}>
        {buckets.map(color => {
          const st = bucketState[color];
          return (
            <button
              key={color}
              onClick={() => handleBucketTap(color)}
              style={{
                width: 60 * scale,
                height: 70 * scale,
                borderRadius: 12 * scale,
                background: COLOR_HEX[color],
                border: st === 'correct' ? '4px solid #3DB5A0' : st === 'wrong' ? '4px solid #FF6B5B' : '3px solid rgba(0,0,0,0.1)',
                cursor: answered ? 'default' : 'pointer',
                boxShadow: `0 4px 0 ${COLOR_HEX[color]}88`,
                animation: st === 'wrong' ? 'shake 0.4s ease-out' : undefined,
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'center',
                paddingBottom: 6,
                transition: 'transform 0.1s',
              }}
            >
              <span style={{ fontSize: 10 * scale, fontFamily: "'Baloo 2', system-ui", fontWeight: 700, color: color === 'white' ? '#999' : 'rgba(255,255,255,0.9)' }}>
                {color}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ProgressPips({ total, current }) {
  return (
    <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{ width: i === current ? 16 : 8, height: 8, borderRadius: 4, background: i < current ? '#3DB5A0' : i === current ? '#FFB648' : 'rgba(255,255,255,0.5)', transition: 'width 0.2s' }} />
      ))}
    </div>
  );
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const gameWrap = {
  minHeight: '100vh',
  background: 'linear-gradient(180deg, #FFF8EC 0%, #E8F5E0 100%)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '0 24px 40px',
};
