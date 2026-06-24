import React, { useState } from 'react';
import { CATEGORIES, PATH_ORDER } from '../../data/categories.js';
import { sfx } from '../../engine/audio.js';

// The winding dirt path with stop nodes. onStopTap(categoryId) called on tap.

export default function PathTrail({ unlockedIds = [], completedIds = [], currentId = null, onStopTap }) {
  const [burstId, setBurstId] = useState(null);

  function handleStopTap(id) {
    if (!unlockedIds.includes(id)) return;
    sfx.tap();
    setBurstId(id);
    setTimeout(() => setBurstId(null), 400);
    onStopTap?.(id);
  }

  return (
    <svg
      viewBox="0 0 320 900"
      style={{ width: '100%', maxWidth: 360, display: 'block', margin: '0 auto' }}
      preserveAspectRatio="xMidYMin meet"
    >
      {/* Winding dirt path — shadow then main */}
      <path
        d={WINDING_PATH}
        fill="none"
        stroke="#C4974A"
        strokeWidth="28"
        strokeLinecap="round"
        opacity="0.35"
        transform="translate(2,6)"
      />
      <path
        d={WINDING_PATH}
        fill="none"
        stroke="#E8C07A"
        strokeWidth="22"
        strokeLinecap="round"
      />
      {/* Dirt texture dashes */}
      <path
        d={WINDING_PATH}
        fill="none"
        stroke="#D4A960"
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray="8 18"
        opacity="0.5"
      />

      {/* Stops */}
      {PATH_ORDER.map((id, i) => {
        const cat = CATEGORIES[id];
        const pos = STOP_POSITIONS[i];
        const unlocked = unlockedIds.includes(id);
        const completed = completedIds.includes(id);
        const isCurrent = id === currentId;
        const burst = burstId === id;

        return (
          <g key={id} transform={`translate(${pos.x}, ${pos.y})`} onClick={() => handleStopTap(id)} style={{ cursor: unlocked ? 'pointer' : 'default' }}>
            {/* Vine connector between stops (above, visual only) */}

            {/* Glow ring for current */}
            {isCurrent && (
              <>
                <circle r="52" fill="none" stroke="#FFD976" strokeWidth="4" opacity="0.3" style={{ animation: 'pathGlow 2s ease-in-out infinite' }} />
                <circle r="44" fill="none" stroke="#FFD976" strokeWidth="3" opacity="0.5" style={{ animation: 'pathGlow 2s ease-in-out infinite 0.3s' }} />
                {/* Floating particles */}
                {[0,60,120,180,240,300].map((angle, j) => (
                  <circle
                    key={j}
                    cx={Math.cos((angle * Math.PI) / 180) * 52}
                    cy={Math.sin((angle * Math.PI) / 180) * 52}
                    r="3"
                    fill="#FFD976"
                    style={{ animation: `floatUp 2s ease-in-out ${j * 0.33}s infinite` }}
                  />
                ))}
              </>
            )}

            {/* 3D orb shadow */}
            <circle r="41" fill={cat.color} opacity="0.3" transform="translate(0, 6)" />

            {/* Main orb */}
            <circle
              r="38"
              fill={unlocked ? cat.color : '#bbb'}
              style={{
                filter: unlocked ? `drop-shadow(0 4px 8px ${cat.color}88)` : 'none',
                animation: burst ? 'magicBurst 0.4s ease-out' : undefined,
              }}
            />

            {/* Completed checkmark */}
            {completed && (
              <g>
                <circle r="38" fill="rgba(0,0,0,0.2)" />
                <text textAnchor="middle" dominantBaseline="middle" fontSize="20" y="1">✓</text>
              </g>
            )}

            {/* Emoji */}
            <text textAnchor="middle" dominantBaseline="middle" fontSize="28" y={completed ? -40 : 0}>
              {cat.emoji}
            </text>

            {/* Label */}
            <text
              textAnchor="middle"
              y="54"
              fontSize="12"
              fontFamily="'Baloo 2', system-ui"
              fontWeight="700"
              fill={unlocked ? '#5B4B8A' : '#999'}
            >
              {cat.labelEn}
            </text>

            {/* Burst particles on tap */}
            {burst && (
              <g style={{ animation: 'magicBurst 0.4s ease-out forwards' }}>
                {[0,60,120,180,240,300].map((angle, j) => (
                  <circle
                    key={j}
                    cx={Math.cos((angle * Math.PI) / 180) * 50}
                    cy={Math.sin((angle * Math.PI) / 180) * 50}
                    r="5"
                    fill={cat.color}
                    opacity="0.8"
                  />
                ))}
              </g>
            )}

            {/* Lock icon for locked stops */}
            {!unlocked && (
              <text textAnchor="middle" dominantBaseline="middle" fontSize="20" y="0" opacity="0.5">🔒</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

// Winding path SVG data through the 900-height canvas
const WINDING_PATH = `
  M 160 870
  C 160 820, 220 800, 220 740
  C 220 680, 100 660, 100 600
  C 100 540, 220 520, 220 460
  C 220 400, 100 380, 100 320
  C 100 260, 220 240, 220 180
  C 220 120, 160 100, 160 50
`;

// Stop positions along the winding path (8 stops)
const STOP_POSITIONS = [
  { x: 160, y: 840 },  // animals
  { x: 220, y: 720 },  // colors
  { x: 100, y: 620 },  // vehicles
  { x: 220, y: 480 },  // numbers
  { x: 100, y: 360 },  // food
  { x: 220, y: 240 },  // shapes
  { x: 100, y: 160 },  // bodyParts
  { x: 160, y: 60 },   // family
];
