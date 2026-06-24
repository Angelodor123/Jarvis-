import React, { useState } from 'react';
import useProfileStore from '../../store/profileStore.js';
import useGameStore from '../../store/gameStore.js';
import { WORDS } from '../../data/categories.js';
import { calcRoundXp } from '../../engine/progression.js';
import { speak } from '../../engine/speech.js';
import { sfx } from '../../engine/audio.js';
import Robi from '../../components/Robi/Robi.jsx';
import LevelHud from '../../components/ui/LevelHud.jsx';
import SpeechBubble from '../../components/ui/SpeechBubble.jsx';
import PrimaryButton from '../../components/ui/PrimaryButton.jsx';

// AI Game 1: Feed Robi Examples.
// Teach: AI learns from data. Brain fills up as more examples are fed.

export default function FeedRobiExamples() {
  const profile       = useProfileStore(s => s.activeProfile());
  const markConceptSeen = useProfileStore(s => s.markConceptSeen);
  const earnBadge     = useProfileStore(s => s.earnBadge);
  const finishRound   = useGameStore(s => s.finishRound);
  const setRobiMood   = useGameStore(s => s.setRobiMood);
  const robiMood      = useGameStore(s => s.robiMood);

  const targetCat = 'animals';
  const allExamples = WORDS[targetCat];

  const [fed, setFed] = useState([]);       // examples fed so far
  const [canGuess, setCanGuess] = useState(false);
  const [guessResult, setGuessResult] = useState(null);   // null | 'right' | 'wrong'
  const [finished, setFinished] = useState(false);

  const confidence = Math.min((fed.length / 3) * 100, 100);  // 3 examples = 100% confidence
  const remaining  = allExamples.filter(w => !fed.find(f => f.en === w.en));

  function feedExample(word) {
    if (fed.find(f => f.en === word.en)) return;
    sfx.tap();
    speak(word.en, 'en-US');
    const newFed = [...fed, word];
    setFed(newFed);
    setRobiMood('happy');

    if (newFed.length >= 3) {
      setCanGuess(true);
      setRobiMood('thinking');
      speak("I think I'm ready to guess now!", 'en-US');
    }
  }

  function handleGuessReveal() {
    // Pick a new unseen example to test Robi on
    const test = remaining[0];
    if (!test) return;

    const isRight = fed.length >= 3;
    setGuessResult(isRight ? 'right' : 'wrong');
    setRobiMood(isRight ? 'happy' : 'oops');
    speak(isRight
      ? `Yes! That's a ${test.en}! I learned from your examples!`
      : `Hmm... I'm not sure. I need more examples to learn!`,
      'en-US',
    );
    if (isRight) sfx.correct();
    else sfx.wrong();
  }

  function handleFinish() {
    markConceptSeen('learns_from_examples');
    earnBadge('learns_from_examples');
    finishRound({ correct: fed.length, total: 3, xpEarned: calcRoundXp(fed.length, 3, 1.0), stars: fed.length >= 3 ? 3 : 2, leveledUp: false });
  }

  const isHe = profile?.lang === 'he';

  return (
    <div style={gameWrap}>
      <div style={{ position: 'fixed', top: 12, left: 12, right: 12, display: 'flex', justifyContent: 'space-between', zIndex: 10 }}>
        <LevelHud />
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 70, gap: 16, alignItems: 'center' }}>
        <Robi mood={robiMood} size={90} />
        <SpeechBubble
          text={
            guessResult === 'right'   ? "I learned! 🎉"
            : guessResult === 'wrong' ? "I need more examples... 😅"
            : canGuess               ? "I think I can guess now!"
            : fed.length === 0       ? (isHe ? 'הראי לי חיות! 🐾' : 'Show me animals! 🐾')
            :                          `${fed.length} ${isHe ? 'דוגמאות עד כה...' : 'examples so far...'}`
          }
        />
      </div>

      {/* Brain confidence bar */}
      <div style={{ width: '100%', maxWidth: 300, margin: '20px auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: "'Nunito', system-ui", fontSize: 13, color: '#888', marginBottom: 6 }}>
          <span>{isHe ? 'המוח של רובי' : "Robi's Brain"}</span>
          <span>{Math.round(confidence)}%</span>
        </div>
        <div style={{ height: 20, background: '#e8deff', borderRadius: 10, overflow: 'hidden' }}>
          <div style={{
            width: `${confidence}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #5B4B8A, #8B7BC8)',
            borderRadius: 10,
            transition: 'width 0.5s ease',
          }} />
        </div>
        <div style={{ fontFamily: "'Nunito', system-ui", fontSize: 12, color: '#aaa', marginTop: 4, textAlign: 'center' }}>
          {confidence < 100
            ? (isHe ? `עוד ${Math.max(0, 3 - fed.length)} דוגמאות נדרשות` : `${Math.max(0, 3 - fed.length)} more examples needed`)
            : (isHe ? 'מוכן לנחש!' : 'Ready to guess!')
          }
        </div>
      </div>

      {/* Fed examples */}
      {fed.length > 0 && (
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap', margin: '0 0 16px' }}>
          {fed.map(w => (
            <div key={w.en} style={{
              background: '#5B4B8A',
              borderRadius: 12,
              padding: '8px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              animation: 'popIn 0.3s ease-out',
            }}>
              <span style={{ fontSize: 24 }}>{w.emoji}</span>
              <span style={{ fontFamily: "'Baloo 2', system-ui", fontSize: 13, color: 'white', fontWeight: 700 }}>{w.en}</span>
            </div>
          ))}
        </div>
      )}

      {/* Animal grid to feed */}
      {!guessResult && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 90px)', gap: 12, justifyContent: 'center' }}>
          {allExamples.slice(0, 6).map(word => {
            const isFed = !!fed.find(f => f.en === word.en);
            return (
              <button
                key={word.en}
                onClick={() => feedExample(word)}
                disabled={isFed}
                style={{
                  width: 90, height: 90,
                  borderRadius: 16,
                  background: isFed ? '#e8deff' : 'white',
                  border: `3px solid ${isFed ? '#5B4B8A' : '#e8deff'}`,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                  cursor: isFed ? 'default' : 'pointer',
                  opacity: isFed ? 0.5 : 1,
                  transition: 'opacity 0.2s',
                }}
              >
                <span style={{ fontSize: 38 }}>{word.emoji}</span>
                <span style={{ fontFamily: "'Baloo 2', system-ui", fontSize: 12, fontWeight: 700, color: '#5B4B8A', marginTop: 3 }}>{word.en}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Guess reveal button */}
      {canGuess && !guessResult && (
        <PrimaryButton color="#5B4B8A" onClick={handleGuessReveal} style={{ marginTop: 20 }}>
          {isHe ? 'נסה לנחש!' : 'Let Robi Guess!'}
        </PrimaryButton>
      )}

      {/* Finish */}
      {guessResult && (
        <PrimaryButton color="#3DB5A0" onClick={handleFinish} style={{ marginTop: 20 }}>
          {isHe ? 'סיימנו!' : 'Finish!'}
        </PrimaryButton>
      )}
    </div>
  );
}

const gameWrap = {
  minHeight: '100vh',
  background: 'linear-gradient(180deg, #EDE7F6 0%, #E8F5E0 100%)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '0 24px 40px',
};
