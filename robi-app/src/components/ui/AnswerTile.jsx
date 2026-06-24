import React, { useState } from 'react';
import { sfx } from '../../engine/audio.js';

// A tappable answer tile used in vocabulary games.
// showText: false for Lian's picture-only mode.
// state: null | 'correct' | 'wrong'

export default function AnswerTile({ word, showText = true, state = null, onTap, scale = 1.0 }) {
  const [pressed, setPressed] = useState(false);

  const bg = state === 'correct' ? '#3DB5A0'
           : state === 'wrong'   ? '#FF6B5B'
           : pressed             ? '#f0e8ff'
           :                       '#fff';

  const border = state === 'correct' ? '3px solid #2a9080'
               : state === 'wrong'   ? '3px solid #e05545'
               :                       '3px solid #e8deff';

  const baseSize = 80 * scale;
  const fontSize = 42 * scale;
  const textSize = 15 * scale;

  function handlePointerDown() {
    if (state) return;
    setPressed(true);
    sfx.tap();
  }

  function handlePointerUp() {
    setPressed(false);
    if (!state) onTap?.();
  }

  return (
    <div
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={() => setPressed(false)}
      style={{
        width: baseSize,
        height: baseSize,
        background: bg,
        border,
        borderRadius: 16 * scale,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: state ? 'default' : 'pointer',
        transform: pressed ? 'scale(0.95)' : 'scale(1)',
        transition: 'transform 0.1s, background 0.2s',
        animation: state === 'wrong' ? 'shake 0.4s ease-out' : undefined,
        userSelect: 'none',
        WebkitTapHighlightColor: 'transparent',
        boxShadow: state ? 'none' : '0 3px 8px rgba(0,0,0,0.1)',
      }}
    >
      <span style={{ fontSize }}>{word.emoji}</span>
      {showText && (
        <span style={{
          fontSize: textSize,
          fontFamily: "'Baloo 2', system-ui",
          fontWeight: 700,
          color: state ? '#fff' : '#5B4B8A',
          marginTop: 4,
          textAlign: 'center',
          lineHeight: 1.1,
        }}>
          {word.en}
        </span>
      )}
    </div>
  );
}
