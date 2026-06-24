import React, { useState, useEffect, useRef } from 'react';
import useProfileStore from '../../store/profileStore.js';
import useGameStore from '../../store/gameStore.js';
import { getWordsForCategory, AGE_CONFIGS } from '../../data/curriculum.js';
import { calcRoundXp, calcStars } from '../../engine/progression.js';
import { speak } from '../../engine/speech.js';
import { sfx } from '../../engine/audio.js';
import Robi from '../../components/Robi/Robi.jsx';
import LevelHud from '../../components/ui/LevelHud.jsx';

// 12 cards: 6 emoji cards + 6 English word cards, flip to match pairs.
// Fix from spec: completion check happens inside useEffect after state settles, not in setTimeout.

export default function MemoryPairs() {
  const profile     = useProfileStore(s => s.activeProfile());
  const finishRound = useGameStore(s => s.finishRound);
  const setRobiMood = useGameStore(s => s.setRobiMood);
  const robiMood    = useGameStore(s => s.robiMood);
  const activeCategory = useGameStore(s => s.activeCategory);

  const ageMode = profile?.ageMode ?? 'amy';
  const config  = AGE_CONFIGS[ageMode];
  const allWords = getWordsForCategory(activeCategory, ageMode);

  const [words]    = useState(() => shuffle(allWords).slice(0, 6));
  const [cards]    = useState(() => buildCards);
  const [flipped, setFlipped]   = useState(new Set());
  const [matched,  setMatched]  = useState(new Set());
  const [locked,   setLocked]   = useState(false);
  const [mistakes, setMistakes] = useState(0);
  const prevFlipped = useRef(new Set());

  function buildCards() {
    const w = shuffle(allWords).slice(0, 6);
    const emojiCards = w.map((word, i) => ({ id: `emoji-${i}`, type: 'emoji', word }));
    const textCards  = w.map((word, i) => ({ id: `text-${i}`,  type: 'text',  word }));
    return shuffle([...emojiCards, ...textCards]);
  }

  // Check for completion when matched changes
  useEffect(() => {
    if (matched.size === cards.length && cards.length > 0) {
      const total    = words.length;
      const correct  = total;
      const xpEarned = calcRoundXp(correct, total, config.xpMultiplier);
      finishRound({ correct, total, xpEarned, stars: calcStars(correct - mistakes, total), leveledUp: false });
    }
  }, [matched]);

  function flipCard(card) {
    if (locked || flipped.has(card.id) || matched.has(card.id)) return;

    const newFlipped = new Set(flipped);
    newFlipped.add(card.id);
    setFlipped(newFlipped);

    const openCards = cards.filter(c => newFlipped.has(c.id) && !matched.has(c.id));

    if (openCards.length === 2) {
      setLocked(true);
      const [a, b] = openCards;
      if (a.word.en === b.word.en) {
        // Match
        sfx.correct();
        speak(a.word.en, 'en-US');
        setRobiMood('happy');
        const newMatched = new Set(matched);
        newMatched.add(a.id);
        newMatched.add(b.id);
        setMatched(newMatched);
        setFlipped(new Set());
        setLocked(false);
      } else {
        // No match
        sfx.wrong();
        setRobiMood('oops');
        setMistakes(m => m + 1);
        setTimeout(() => {
          setFlipped(new Set());
          setLocked(false);
          setRobiMood('idle');
        }, 900);
      }
    }
  }

  const isHe = profile?.lang === 'he';

  return (
    <div style={gameWrap}>
      <div style={{ position: 'fixed', top: 12, left: 12, right: 12, display: 'flex', justifyContent: 'space-between', zIndex: 10 }}>
        <LevelHud />
        <div style={{ background: 'rgba(255,255,255,0.85)', borderRadius: 12, padding: '4px 12px', fontFamily: "'Baloo 2', system-ui", fontSize: 13, color: '#5B4B8A', fontWeight: 700 }}>
          {matched.size / 2}/{words.length} ✓
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 70 }}>
        <Robi mood={robiMood} size={70} />
      </div>

      <div style={{ textAlign: 'center', marginTop: 8, marginBottom: 16, fontFamily: "'Nunito', system-ui", color: '#5B4B8A', fontSize: 15 }}>
        {isHe ? 'מצאי זוגות תואמים!' : 'Find the matching pairs!'}
      </div>

      {/* 4×3 card grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 72px)',
        gap: 10,
        justifyContent: 'center',
      }}>
        {cards.map(card => {
          const isFlipped  = flipped.has(card.id);
          const isMatched  = matched.has(card.id);
          const show       = isFlipped || isMatched;

          return (
            <div
              key={card.id}
              onClick={() => flipCard(card)}
              style={{
                width: 72,
                height: 72,
                borderRadius: 14,
                background: isMatched ? '#3DB5A0' : show ? 'white' : '#5B4B8A',
                border: isMatched ? '3px solid #2a9080' : show ? '3px solid #e8deff' : '3px solid #4a3a78',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: (isFlipped || isMatched || locked) ? 'default' : 'pointer',
                transition: 'background 0.25s, transform 0.25s',
                transform: show ? 'rotateY(0deg)' : 'rotateY(0deg)',
                animation: isMatched ? 'popIn 0.3s ease-out' : undefined,
                boxShadow: show ? '0 2px 8px rgba(0,0,0,0.1)' : '0 3px 0 rgba(0,0,0,0.2)',
              }}
            >
              {show ? (
                card.type === 'emoji'
                  ? <span style={{ fontSize: 34 }}>{card.word.emoji}</span>
                  : <span style={{ fontSize: 13, fontFamily: "'Baloo 2', system-ui", fontWeight: 700, color: isMatched ? 'white' : '#5B4B8A', textAlign: 'center', padding: '0 4px' }}>{card.word.en}</span>
              ) : (
                <span style={{ fontSize: 24, opacity: 0.5 }}>?</span>
              )}
            </div>
          );
        })}
      </div>
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
