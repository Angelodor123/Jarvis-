import React, { useState, useEffect } from 'react';
import useProfileStore from '../../store/profileStore.js';
import useGameStore from '../../store/gameStore.js';
import { WORDS, CATEGORIES } from '../../data/categories.js';
import { getUnlockedCategories, AGE_CONFIGS } from '../../data/curriculum.js';
import { calcLevel, calcRoundXp, calcStars } from '../../engine/progression.js';
import { speak } from '../../engine/speech.js';
import { sfx } from '../../engine/audio.js';
import Robi from '../../components/Robi/Robi.jsx';
import LevelHud from '../../components/ui/LevelHud.jsx';

// Item appears; tap which of two category baskets it belongs to.
// Uses two unlocked categories as the two baskets.

export default function SortItOut() {
  const profile     = useProfileStore(s => s.activeProfile());
  const finishRound = useGameStore(s => s.finishRound);
  const setRobiMood = useGameStore(s => s.setRobiMood);
  const robiMood    = useGameStore(s => s.robiMood);

  const ageMode = profile?.ageMode ?? 'amy';
  const config  = AGE_CONFIGS[ageMode];
  const { level } = calcLevel(profile?.totalXp ?? 0);

  // Pick two unlocked categories as baskets
  const [catIds] = useState(() => {
    const unlocked = getUnlockedCategories(level);
    const picked = shuffle(unlocked).slice(0, 2);
    return picked.length >= 2 ? picked : ['animals', 'colors'];
  });

  // Build queue: mix items from both categories
  const [queue] = useState(() => {
    const items = [];
    for (const catId of catIds) {
      const words = (WORDS[catId] ?? []).slice(0, 4);
      words.forEach(w => items.push({ word: w, categoryId: catId }));
    }
    return shuffle(items).slice(0, config.roundSize);
  });

  const [qIdx, setQIdx]       = useState(0);
  const [basketState, setBasketState] = useState({});
  const [correct, setCorrect] = useState(0);
  const [answered, setAnswered] = useState(false);

  const current = queue[qIdx];

  useEffect(() => {
    if (!current) return;
    setBasketState({});
    setAnswered(false);
    setRobiMood('idle');
    speak(current.word.en, 'en-US');
  }, [qIdx]);

  function handleBasketTap(catId) {
    if (answered) return;
    setAnswered(true);

    if (catId === current.categoryId) {
      sfx.correct();
      speak(current.word.en, 'en-US');
      setBasketState({ [catId]: 'correct' });
      setCorrect(c => c + 1);
      setRobiMood('happy');
    } else {
      sfx.wrong();
      setBasketState({ [catId]: 'wrong', [current.categoryId]: 'correct' });
      setRobiMood('oops');
    }

    setTimeout(() => advance(), 1200);
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

  return (
    <div style={gameWrap}>
      <div style={{ position: 'fixed', top: 12, left: 12, right: 12, display: 'flex', justifyContent: 'space-between', zIndex: 10 }}>
        <LevelHud />
        <ProgressPips total={queue.length} current={qIdx} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 70 }}>
        <Robi mood={robiMood} size={80} />
      </div>

      <div style={{ textAlign: 'center', marginTop: 12, fontFamily: "'Nunito', system-ui", color: '#5B4B8A', fontSize: 16 }}>
        {isHe ? 'להיכן שייך זה?' : 'Where does this belong?'}
      </div>

      {/* Current item */}
      <div style={{ textAlign: 'center', margin: '16px 0', animation: 'robiFloat 2s ease-in-out infinite' }}>
        <div style={{ fontSize: 80 }}>{current.word.emoji}</div>
        <div style={{ fontFamily: "'Baloo 2', system-ui", fontWeight: 800, color: '#3a2f5b', fontSize: 22, marginTop: 4 }}>
          {current.word.en}
        </div>
      </div>

      {/* Two baskets */}
      <div style={{ display: 'flex', gap: 24, justifyContent: 'center' }}>
        {catIds.map(catId => {
          const cat = CATEGORIES[catId];
          const st  = basketState[catId];
          return (
            <button
              key={catId}
              onClick={() => handleBasketTap(catId)}
              style={{
                width: 130,
                height: 130,
                borderRadius: 24,
                background: st === 'correct' ? cat.color : st === 'wrong' ? '#FF6B5B' : 'white',
                border: `3px solid ${st === 'correct' ? cat.color : st === 'wrong' ? '#e05545' : cat.color + '88'}`,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: answered ? 'default' : 'pointer',
                animation: st === 'wrong' ? 'shake 0.4s ease-out' : st === 'correct' ? 'popIn 0.3s ease-out' : undefined,
                boxShadow: st ? 'none' : '0 4px 12px rgba(0,0,0,0.1)',
                transition: 'background 0.2s',
              }}
            >
              <span style={{ fontSize: 36 }}>{cat.emoji}</span>
              <span style={{ fontFamily: "'Baloo 2', system-ui", fontWeight: 700, fontSize: 16, color: st ? 'white' : cat.color, marginTop: 8 }}>
                {isHe ? cat.labelHe : cat.labelEn}
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
