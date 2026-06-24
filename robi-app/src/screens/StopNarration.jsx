import React, { useState, useEffect } from 'react';
import useProfileStore from '../store/profileStore.js';
import useGameStore from '../store/gameStore.js';
import { CATEGORIES } from '../data/categories.js';
import { pickGame } from '../data/curriculum.js';
import { calcLevel } from '../engine/progression.js';
import { speak } from '../engine/speech.js';
import Robi from '../components/Robi/Robi.jsx';
import PrimaryButton from '../components/ui/PrimaryButton.jsx';

// Two-phase story intro before a game starts.
// Phase 0: Problem (Robi worried)
// Phase 1: Mission (Robi happy) + start button

export default function StopNarration() {
  const [phase, setPhase] = useState(0);
  const profile     = useProfileStore(s => s.activeProfile());
  const activeId    = useProfileStore(s => s.activeId);
  const startGame   = useGameStore(s => s.startGame);
  const goTo        = useGameStore(s => s.goTo);
  const activeCategory = useGameStore(s => s.activeCategory);

  const cat = CATEGORIES[activeCategory];
  if (!cat) return null;

  const { level } = calcLevel(profile?.totalXp ?? 0);
  const lang = profile?.lang ?? 'he';

  useEffect(() => {
    if (phase === 0) speak(cat.problem, 'en-US');
    else             speak(cat.mission, 'en-US');
  }, [phase]);

  function nextPhase() {
    if (phase === 0) {
      setPhase(1);
    } else {
      const game = pickGame(activeCategory, level, profile?.ageMode ?? 'amy');
      startGame(activeCategory, game);
    }
  }

  const isHe = lang === 'he';

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(180deg, #FFD5A8 0%, #FFF0D4 60%, #E8F5E0 100%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
      gap: 24,
    }}>
      {/* Back button */}
      <button
        onClick={() => goTo('home')}
        style={{
          position: 'fixed',
          top: 16,
          left: 16,
          background: 'rgba(255,255,255,0.85)',
          border: '2px solid #ddd',
          borderRadius: 12,
          padding: '6px 14px',
          fontSize: 20,
          cursor: 'pointer',
          fontFamily: "'Baloo 2', system-ui",
        }}
      >
        ←
      </button>

      {/* Scene label */}
      <div style={{
        fontFamily: "'Baloo 2', system-ui",
        fontSize: 15,
        color: '#888',
        fontWeight: 600,
      }}>
        {cat.scene}
      </div>

      {/* Robi */}
      <Robi mood={phase === 0 ? 'oops' : 'happy'} size={120} />

      {/* Story card */}
      <div style={{
        background: 'white',
        borderRadius: 24,
        padding: '24px 28px',
        boxShadow: '0 8px 32px rgba(91,75,138,0.12)',
        maxWidth: 340,
        textAlign: 'center',
        animation: 'popIn 0.3s ease-out',
      }}>
        <p style={{
          fontFamily: "'Nunito', system-ui",
          fontSize: 17,
          color: '#3a2f5b',
          lineHeight: 1.6,
          margin: 0,
        }}>
          {phase === 0 ? cat.problem : cat.mission}
        </p>

        {phase === 1 && (
          <div style={{
            marginTop: 16,
            padding: '10px 16px',
            background: '#FFF8EC',
            borderRadius: 12,
            fontSize: 14,
            color: '#888',
            fontFamily: "'Nunito', system-ui",
          }}>
            🎁 {cat.reward}
          </div>
        )}
      </div>

      {/* CTA button */}
      <PrimaryButton
        onClick={nextPhase}
        color={cat.color}
        style={{ fontSize: 17, padding: '16px 32px', marginTop: 8 }}
      >
        {phase === 0
          ? (isHe ? 'אז מה עושים?' : 'So what do we do?')
          : cat.buttonLabel
        }
      </PrimaryButton>
    </div>
  );
}
