import React, { useEffect, useRef } from 'react';
import { MOODS } from './Robi.moods.js';

// Layered SVG Robi character. Size controlled by `size` prop (default 80px).
// mood: 'idle' | 'happy' | 'thinking' | 'oops'

export default function Robi({ mood = 'idle', size = 80 }) {
  const spinRef = useRef(null);

  // Spin ring animation for thinking mood
  useEffect(() => {
    if (!spinRef.current) return;
    if (mood === 'thinking') {
      spinRef.current.style.animation = 'spin 1.6s linear infinite';
    } else {
      spinRef.current.style.animation = 'none';
    }
  }, [mood]);

  const m = MOODS[mood] ?? MOODS.idle;
  const isOops = mood === 'oops';

  return (
    <svg
      width={size}
      height={size}
      viewBox="-50 -80 100 120"
      style={{
        filter: 'drop-shadow(0 4px 8px rgba(91,75,138,0.4))',
        animation: mood === 'happy' ? 'robiBounce 0.6s ease-out' : 'robiFloat 3s ease-in-out infinite',
        overflow: 'visible',
      }}
    >
      <defs>
        <radialGradient id="robiBody" cx="40%" cy="35%">
          <stop offset="0%" stopColor="#8B7BC8" />
          <stop offset="100%" stopColor="#5B4B8A" />
        </radialGradient>
        <radialGradient id="robiMushroom" cx="50%" cy="20%">
          <stop offset="0%" stopColor="#D4734A" />
          <stop offset="100%" stopColor="#A8522E" />
        </radialGradient>
      </defs>

      {/* Mushroom seat */}
      <ellipse cx="0" cy="35" rx="28" ry="8" fill="#C0693A" opacity="0.6" />
      <path d="M -22 35 Q 0 18 22 35" fill="url(#robiMushroom)" />
      <ellipse cx="0" cy="35" rx="22" ry="5" fill="#E8865C" />
      {/* Mushroom spots */}
      <circle cx="-8" cy="26" r="3" fill="white" opacity="0.7" />
      <circle cx="6" cy="24" r="2" fill="white" opacity="0.7" />
      <circle cx="12" cy="29" r="2.5" fill="white" opacity="0.6" />

      {/* Body */}
      <circle cx="0" cy="0" r="28" fill="url(#robiBody)" />

      {/* Thinking spin ring */}
      {mood === 'thinking' && (
        <circle
          ref={spinRef}
          cx="0"
          cy="0"
          r="34"
          fill="none"
          stroke="#FFD976"
          strokeWidth="3"
          strokeDasharray="16 8"
          strokeLinecap="round"
        />
      )}

      {/* Leaf crown */}
      <g transform="translate(0,-26)">
        <ellipse cx="-12" cy="-6" rx="7" ry="12" fill="#4CAF50" transform="rotate(-25,-12,-6)" />
        <ellipse cx="0"   cy="-10" rx="6" ry="13" fill="#66BB6A" />
        <ellipse cx="12"  cy="-6"  rx="7" ry="12" fill="#4CAF50" transform="rotate(25,12,-6)" />
      </g>

      {/* Eyes */}
      <g transform="translate(0, -4)" stroke={isOops ? '#FF6B5B' : '#fff'} strokeWidth={isOops ? 2.5 : 0} fill={isOops ? 'none' : '#fff'}>
        <path d={m.leftEye} />
        <path d={m.rightEye} />
        {!isOops && (
          <>
            <circle cx="-4" cy="-4" r="2" fill="#5B4B8A" />
            <circle cx="8"  cy="-4" r="2" fill="#5B4B8A" />
          </>
        )}
      </g>

      {/* Cheek blushes */}
      <ellipse cx="-18" cy="8" rx="6" ry="4" fill="#FF9FBE" opacity="0.5" />
      <ellipse cx="18"  cy="8" rx="6" ry="4" fill="#FF9FBE" opacity="0.5" />

      {/* Mouth */}
      <path
        d={m.mouth}
        fill="none"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
      />

      {/* Firefly companion */}
      <g style={{ animation: 'fireflyDrift 3s ease-in-out infinite' }}>
        <circle cx="38" cy="-20" r="4" fill="#FFD976" opacity="0.9" />
        <circle cx="38" cy="-20" r="7" fill="#FFD976" opacity="0.2" />
      </g>
    </svg>
  );
}
