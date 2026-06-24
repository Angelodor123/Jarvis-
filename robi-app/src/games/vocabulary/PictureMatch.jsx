import React, { useState, useEffect, useCallback } from 'react';
import useProfileStore from '../../store/profileStore.js';
import useGameStore from '../../store/gameStore.js';
import { getWordsForCategory, AGE_CONFIGS } from '../../data/curriculum.js';
import { calcRoundXp, calcStars } from '../../engine/progression.js';
import { speak } from '../../engine/speech.js';
import { sfx } from '../../engine/audio.js';
import Robi from '../../components/Robi/Robi.jsx';
import AnswerTile from '../../components/ui/AnswerTile.jsx';
import LevelHud from '../../components/ui/LevelHud.jsx';

// Game: see one picture emoji prompt, tap the correct English word from 4 choices.

export default function PictureMatch() {
  const profile     = useProfileStore(s => s.activeProfile());
  const finishRound = useGameStore(s => s.finishRound);
  const setRobiMood = useGameStore(s => s.setRobiMood);
  const activeCategory = useGameStore(s => s.activeCategory);

  const ageMode = profile?.ageMode ?? 'amy';
  const config  = AGE_CONFIGS[ageMode];
  const words   = getWordsForCategory(activeCategory, ageMode);

  const [queue, setQueue]     = useState(() => shuffle([...words]).slice(0, config.roundSize));
  const [qIdx, setQIdx]       = useState(0);
  const [choices, setChoices] = useState([]);
  const [tileState, setTileState] = useState({});  // { wordEn: 'correct'|'wrong' }
  const [correct, setCorrect] = useState(0);
  const [answered, setAnswered] = useState(false);

  const current = queue[qIdx];

  // Build 4 answer choices whenever the question changes
  useEffect(() => {
    if (!current) return;
    const distractors = shuffle(words.filter(w => w.en !== current.en)).slice(0, 3);
    setChoices(shuffle([current, ...distractors]));
    setTileState({});
    setAnswered(false);
    speak(`Which one is the ${current.en}?`, 'en-US');
    setRobiMood('idle');
  }, [qIdx]);

  function handleTap(word) {
    if (answered) return;
    setAnswered(true);

    if (word.en === current.en) {
      sfx.correct();
      speak(current.en, 'en-US');
      setTileState({ [word.en]: 'correct' });
      setCorrect(c => c + 1);
      setRobiMood('happy');
    } else {
      sfx.wrong();
      setTileState({ [word.en]: 'wrong', [current.en]: 'correct' });
      setRobiMood('oops');
    }

    setTimeout(() => advance(), 1200);
  }

  function advance() {
    if (qIdx + 1 >= queue.length) {
      const total    = queue.length;
      const xpEarned = calcRoundXp(correct + (tileState[current.en] === undefined ? 0 : 0), total, config.xpMultiplier);
      finishRound({ correct, total, xpEarned, stars: calcStars(correct, total), leveledUp: false });
    } else {
      setQIdx(i => i + 1);
    }
  }

  if (!current) return null;

  const scale = config.tileScale;

  return (
    <div style={gameWrap}>
      {/* HUD */}
      <div style={{ position: 'fixed', top: 12, left: 12, right: 12, display: 'flex', justifyContent: 'space-between', zIndex: 10 }}>
        <LevelHud />
        <ProgressPips total={queue.length} current={qIdx} />
      </div>

      {/* Robi */}
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 70 }}>
        <Robi mood={useGameStore(s => s.robiMood)} size={80} />
      </div>

      {/* Prompt */}
      <div style={{
        textAlign: 'center',
        margin: '16px 0 8px',
        fontSize: 13,
        fontFamily: "'Nunito', system-ui",
        color: '#888',
      }}>
        {profile?.lang === 'he' ? 'איזה מהם הוא' : 'Which one is the'}
      </div>
      <div style={{ textAlign: 'center', fontSize: 80, lineHeight: 1 }}>
        {current.emoji}
      </div>

      {/* Choices */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(2, ${80 * scale}px)`,
        gap: 16 * scale,
        marginTop: 28,
        justifyContent: 'center',
      }}>
        {choices.map(word => (
          <AnswerTile
            key={word.en}
            word={word}
            showText={config.showWordText}
            state={tileState[word.en] ?? null}
            onTap={() => handleTap(word)}
            scale={scale}
          />
        ))}
      </div>
    </div>
  );
}

function ProgressPips({ total, current }) {
  return (
    <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{
          width: i === current ? 16 : 8,
          height: 8,
          borderRadius: 4,
          background: i < current ? '#3DB5A0' : i === current ? '#FFB648' : 'rgba(255,255,255,0.5)',
          transition: 'width 0.2s, background 0.2s',
        }} />
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
