import React, { useEffect } from 'react';
import useProfileStore from '../store/profileStore.js';
import useGameStore from '../store/gameStore.js';
import { CATEGORIES } from '../data/categories.js';
import { calcLevel } from '../engine/progression.js';
import { sfx } from '../engine/audio.js';
import Robi from '../components/Robi/Robi.jsx';
import PrimaryButton from '../components/ui/PrimaryButton.jsx';
import Confetti from '../components/ui/Confetti.jsx';

export default function RoundComplete() {
  const roundResults   = useGameStore(s => s.roundResults);
  const activeCategory = useGameStore(s => s.activeCategory);
  const startNarration = useGameStore(s => s.startNarration);
  const goTo           = useGameStore(s => s.goTo);

  const profile     = useProfileStore(s => s.activeProfile());
  const addXp       = useProfileStore(s => s.addXp);
  const markStop    = useProfileStore(s => s.markStopComplete);

  if (!roundResults) return null;

  const { correct, total, xpEarned, stars, leveledUp } = roundResults;
  const cat    = CATEGORIES[activeCategory];
  const isPerfect = stars === 3;
  const lang = profile?.lang ?? 'he';
  const isHe = lang === 'he';

  // XP and completion marking happen here (once) via useEffect
  useEffect(() => {
    addXp(xpEarned);
    if (isPerfect) markStop(activeCategory);
    if (isPerfect) sfx.levelUp();
    else sfx.correct();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const bgGradient = isPerfect
    ? 'linear-gradient(135deg, #FFD976 0%, #FF6B5B 100%)'
    : 'linear-gradient(135deg, #3DB5A0 0%, #5B4B8A 100%)';

  return (
    <div style={{
      minHeight: '100vh',
      background: bgGradient,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
      gap: 20,
      position: 'relative',
    }}>
      {isPerfect && <Confetti active />}

      <Robi mood={isPerfect ? 'happy' : 'idle'} size={110} />

      {/* Stars */}
      <div style={{ fontSize: 44, letterSpacing: 4, animation: 'popIn 0.4s ease-out' }}>
        {[1,2,3].map(n => (
          <span key={n} style={{ opacity: n <= stars ? 1 : 0.25 }}>⭐</span>
        ))}
      </div>

      {/* Score */}
      <div style={{
        background: 'rgba(255,255,255,0.2)',
        borderRadius: 20,
        padding: '16px 28px',
        textAlign: 'center',
        animation: 'fadeUp 0.4s 0.1s ease-out both',
      }}>
        <div style={{ fontSize: 36, fontFamily: "'Baloo 2', system-ui", fontWeight: 900, color: 'white' }}>
          {correct}/{total}
        </div>
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.8)', fontFamily: "'Nunito', system-ui" }}>
          {isHe ? 'תשובות נכונות' : 'correct answers'}
        </div>
      </div>

      {/* XP badge */}
      <div style={{
        background: 'linear-gradient(135deg, #FFB648, #FFD976)',
        borderRadius: 16,
        padding: '10px 20px',
        fontFamily: "'Baloo 2', system-ui",
        fontWeight: 800,
        fontSize: 18,
        color: '#3a2f5b',
        animation: 'popIn 0.4s 0.2s ease-out both',
        boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
      }}>
        +{xpEarned} XP ⭐
      </div>

      {/* Level up! */}
      {leveledUp && (
        <div style={{
          background: 'linear-gradient(135deg, #FFD976, #FFB648)',
          borderRadius: 16,
          padding: '10px 24px',
          fontFamily: "'Baloo 2', system-ui",
          fontWeight: 900,
          fontSize: 20,
          color: '#3a2f5b',
          animation: 'popIn 0.4s 0.3s ease-out both',
          boxShadow: '0 6px 0 rgba(0,0,0,0.15)',
        }}>
          🎉 {isHe ? 'עלית רמה!' : 'Level Up!'}
        </div>
      )}

      {/* Quest reward on perfect */}
      {isPerfect && cat && (
        <div style={{
          background: 'rgba(255,255,255,0.15)',
          borderRadius: 16,
          padding: '12px 20px',
          fontFamily: "'Nunito', system-ui",
          fontSize: 14,
          color: 'white',
          textAlign: 'center',
          maxWidth: 280,
          animation: 'fadeUp 0.4s 0.4s ease-out both',
        }}>
          {cat.reward}
        </div>
      )}

      {/* Buttons */}
      <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
        <PrimaryButton
          color="#3DB5A0"
          onClick={() => startNarration(activeCategory)}
          style={{ fontSize: 16 }}
        >
          {isHe ? 'שחקי שוב' : 'Play Again'}
        </PrimaryButton>
        <PrimaryButton
          color="#5B4B8A"
          onClick={() => goTo('home')}
          style={{ fontSize: 16 }}
        >
          {isHe ? 'הביתה' : 'Home'}
        </PrimaryButton>
      </div>

      {/* Forest floor silhouette */}
      <svg style={{ position: 'fixed', bottom: 0, left: 0, width: '100%', pointerEvents: 'none' }} viewBox="0 0 400 60" preserveAspectRatio="none">
        <path d="M0 60 Q50 20 100 40 Q150 55 200 30 Q250 10 300 40 Q350 60 400 35 L400 60Z" fill="rgba(0,0,0,0.15)" />
      </svg>
    </div>
  );
}
