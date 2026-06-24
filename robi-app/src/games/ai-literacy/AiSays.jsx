import React, { useState, useEffect } from 'react';
import useProfileStore from '../../store/profileStore.js';
import useGameStore from '../../store/gameStore.js';
import { getWordsForCategory, AGE_CONFIGS } from '../../data/curriculum.js';
import { calcRoundXp, calcStars } from '../../engine/progression.js';
import { speak } from '../../engine/speech.js';
import { sfx } from '../../engine/audio.js';
import Robi from '../../components/Robi/Robi.jsx';
import LevelHud from '../../components/ui/LevelHud.jsx';
import SpeechBubble from '../../components/ui/SpeechBubble.jsx';

// AI literacy crossover: Robi "guesses" what the picture shows.
// 40% chance he's wrong. Player gives thumbs up/down to teach him.

const WRONG_REASONS = [
  "I only learned from a few pictures! I need more examples.",
  "My training data wasn't very good for this one.",
  "I confused it with something similar I saw before.",
  "Even AI makes mistakes — you can teach me!",
];

export default function AiSays() {
  const profile       = useProfileStore(s => s.activeProfile());
  const markConceptSeen = useProfileStore(s => s.markConceptSeen);
  const finishRound   = useGameStore(s => s.finishRound);
  const setRobiMood   = useGameStore(s => s.setRobiMood);
  const robiMood      = useGameStore(s => s.robiMood);
  const activeCategory = useGameStore(s => s.activeCategory);

  const ageMode = profile?.ageMode ?? 'amy';
  const config  = AGE_CONFIGS[ageMode];
  const words   = getWordsForCategory(activeCategory, ageMode);

  const [queue] = useState(() => shuffle([...words]).slice(0, config.roundSize));
  const [qIdx, setQIdx] = useState(0);
  const [robiGuess, setRobiGuess] = useState(null);  // the word Robi says
  const [isCorrect, setIsCorrect] = useState(null);  // true = right guess, false = wrong
  const [phase, setPhase] = useState('show');         // 'show' | 'feedback' | 'explain'
  const [playerFeedback, setPlayerFeedback] = useState(null);
  const [correct, setCorrect] = useState(0);

  const current = queue[qIdx];

  useEffect(() => {
    if (!current) return;
    setPhase('show');
    setPlayerFeedback(null);
    setRobiMood('thinking');

    // Robi "thinks" for 1.5s then guesses
    setTimeout(() => {
      const wrong = Math.random() < 0.4;
      let guess;
      if (wrong) {
        const others = words.filter(w => w.en !== current.en);
        guess = others[Math.floor(Math.random() * others.length)];
      } else {
        guess = current;
      }
      setRobiGuess(guess);
      setIsCorrect(!wrong);
      speak(`Is this a ${guess.en}?`, 'en-US');
      setRobiMood('idle');
      setPhase('feedback');
    }, 1500);
  }, [qIdx]);

  function handleFeedback(thumbsUp) {
    if (phase !== 'feedback') return;
    setPlayerFeedback(thumbsUp);

    const robiWasRight = isCorrect;
    const playerAgreed = thumbsUp;

    if (robiWasRight && playerAgreed) {
      sfx.correct();
      speak("Yes! I got it right this time!", 'en-US');
      setRobiMood('happy');
      setCorrect(c => c + 1);
      setTimeout(() => advance(), 1400);
    } else if (!robiWasRight && !playerAgreed) {
      // Player correctly caught Robi's mistake
      sfx.correct();
      setRobiMood('oops');
      setPhase('explain');
      markConceptSeen('can_be_wrong');
      speak("Oops! I guessed wrong. AI doesn't always know — you can teach me!", 'en-US');
      setCorrect(c => c + 1);
      setTimeout(() => advance(), 2800);
    } else {
      // Player was wrong about Robi
      sfx.wrong();
      setRobiMood('oops');
      setTimeout(() => advance(), 1200);
    }
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
        <Robi mood={robiMood} size={90} />
      </div>

      {/* Robi speech bubble */}
      <div style={{ display: 'flex', justifyContent: 'center', margin: '12px 0' }}>
        {phase === 'show' && (
          <SpeechBubble text={isHe ? '...אני חושב...' : '...thinking...'} />
        )}
        {phase === 'feedback' && robiGuess && (
          <SpeechBubble text={`Is this a ${robiGuess.en}? 🤔`} />
        )}
        {phase === 'explain' && (
          <SpeechBubble text={`Oops! ${WRONG_REASONS[qIdx % WRONG_REASONS.length]}`} />
        )}
      </div>

      {/* Picture */}
      <div style={{ textAlign: 'center', fontSize: 100, margin: '12px 0' }}>
        {current.emoji}
      </div>

      {/* Thumbs buttons — shown during feedback phase */}
      {phase === 'feedback' && !playerFeedback && (
        <div style={{ display: 'flex', gap: 32, justifyContent: 'center', marginTop: 16 }}>
          <ThumbButton emoji="👍" label={isHe ? 'נכון!' : 'Right!'} color="#3DB5A0" onTap={() => handleFeedback(true)} />
          <ThumbButton emoji="👎" label={isHe ? 'טעות!' : 'Wrong!'} color="#FF6B5B" onTap={() => handleFeedback(false)} />
        </div>
      )}
    </div>
  );
}

function ThumbButton({ emoji, label, color, onTap }) {
  return (
    <button
      onClick={onTap}
      style={{
        width: 90,
        height: 90,
        borderRadius: 20,
        background: 'white',
        border: `3px solid ${color}`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        boxShadow: `0 4px 0 ${color}44`,
        fontSize: 36,
        fontFamily: "'Baloo 2', system-ui",
        color,
        fontWeight: 700,
        gap: 4,
      }}
    >
      <span>{emoji}</span>
      <span style={{ fontSize: 13 }}>{label}</span>
    </button>
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
  background: 'linear-gradient(180deg, #EDE7F6 0%, #E8F5E0 100%)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '0 24px 40px',
};
