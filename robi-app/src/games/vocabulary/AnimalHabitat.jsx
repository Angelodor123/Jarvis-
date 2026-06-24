import React, { useState, useEffect } from 'react';
import useProfileStore from '../../store/profileStore.js';
import useGameStore from '../../store/gameStore.js';
import { getWordsForCategory, AGE_CONFIGS } from '../../data/curriculum.js';
import { ANIMAL_HABITATS } from '../../data/categories.js';
import { calcRoundXp, calcStars } from '../../engine/progression.js';
import { speak } from '../../engine/speech.js';
import { sfx } from '../../engine/audio.js';
import Robi from '../../components/Robi/Robi.jsx';
import LevelHud from '../../components/ui/LevelHud.jsx';

const ZONES = [
  { id: 'ocean',  label: 'Ocean',  emoji: '🌊', color: '#1E88E5', bg: '#E3F2FD' },
  { id: 'forest', label: 'Forest', emoji: '🌿', color: '#43A047', bg: '#E8F5E9' },
  { id: 'sky',    label: 'Sky',    emoji: '☁️',  color: '#7E57C2', bg: '#EDE7F6' },
];

export default function AnimalHabitat() {
  const profile     = useProfileStore(s => s.activeProfile());
  const finishRound = useGameStore(s => s.finishRound);
  const setRobiMood = useGameStore(s => s.setRobiMood);
  const robiMood    = useGameStore(s => s.robiMood);

  const ageMode = profile?.ageMode ?? 'amy';
  const config  = AGE_CONFIGS[ageMode];
  const words   = getWordsForCategory('animals', ageMode);

  const [queue] = useState(() => shuffle([...words]).slice(0, config.roundSize));
  const [qIdx, setQIdx] = useState(0);
  const [zoneState, setZoneState] = useState({});  // { zoneId: 'correct'|'wrong' }
  const [correct, setCorrect] = useState(0);
  const [answered, setAnswered] = useState(false);

  const current = queue[qIdx];

  useEffect(() => {
    if (!current) return;
    setZoneState({});
    setAnswered(false);
    setRobiMood('idle');
    speak(`Where does the ${current.en} live?`, 'en-US');
  }, [qIdx]);

  function correctZoneFor(animalEn) {
    for (const [zone, animals] of Object.entries(ANIMAL_HABITATS)) {
      if (animals.includes(animalEn)) return zone;
    }
    return 'forest'; // fallback
  }

  function handleZoneTap(zoneId) {
    if (answered) return;
    setAnswered(true);

    const correct_ = correctZoneFor(current.en);
    if (zoneId === correct_) {
      sfx.correct();
      speak(current.en, 'en-US');
      setZoneState({ [zoneId]: 'correct' });
      setCorrect(c => c + 1);
      setRobiMood('happy');
    } else {
      sfx.wrong();
      setZoneState({ [zoneId]: 'wrong', [correct_]: 'correct' });
      setRobiMood('oops');
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

      <div style={{ textAlign: 'center', marginTop: 16, fontFamily: "'Nunito', system-ui", color: '#5B4B8A', fontSize: 16 }}>
        {isHe ? 'איפה גר ה' : 'Where does the'} <strong>{current.en}</strong> {isHe ? '?' : 'live?'}
      </div>

      {/* Animal display */}
      <div style={{
        fontSize: 90,
        textAlign: 'center',
        margin: '12px 0',
        animation: answered ? undefined : 'robiFloat 2s ease-in-out infinite',
      }}>
        {current.emoji}
      </div>

      {/* Zone buttons */}
      <div style={{ display: 'flex', gap: 14 * scale, justifyContent: 'center', flexWrap: 'wrap', padding: '0 12px' }}>
        {ZONES.map(zone => {
          const st = zoneState[zone.id];
          return (
            <button
              key={zone.id}
              onClick={() => handleZoneTap(zone.id)}
              style={{
                width: 90 * scale,
                height: 90 * scale,
                borderRadius: 20 * scale,
                background: st === 'correct' ? zone.color : st === 'wrong' ? '#FF6B5B' : zone.bg,
                border: `3px solid ${st === 'correct' ? zone.color : st === 'wrong' ? '#e05545' : zone.color + '66'}`,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: answered ? 'default' : 'pointer',
                animation: st === 'wrong' ? 'shake 0.4s ease-out' : st === 'correct' ? 'popIn 0.3s ease-out' : undefined,
                transition: 'background 0.2s',
              }}
            >
              <span style={{ fontSize: 32 * scale }}>{zone.emoji}</span>
              <span style={{ fontSize: 12 * scale, fontFamily: "'Baloo 2', system-ui", fontWeight: 700, color: st ? 'white' : zone.color, marginTop: 4 }}>
                {zone.label}
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
