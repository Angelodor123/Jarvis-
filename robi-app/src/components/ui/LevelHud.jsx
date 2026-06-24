import React from 'react';
import useProfileStore from '../../store/profileStore.js';

export default function LevelHud() {
  const levelInfo = useProfileStore(s => s.levelInfo());
  const profile   = useProfileStore(s => s.activeProfile());

  if (!profile) return null;

  const { level, currentXp, neededXp } = levelInfo;
  const pct = Math.min(100, Math.round((currentXp / neededXp) * 100));

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      background: 'rgba(255,255,255,0.85)',
      borderRadius: 20,
      padding: '6px 14px',
      backdropFilter: 'blur(4px)',
    }}>
      <span style={{ fontSize: 13, fontWeight: 800, color: '#5B4B8A', fontFamily: "'Baloo 2', system-ui" }}>
        ⭐ {level}
      </span>
      <div style={{ width: 60, height: 7, background: '#e8deff', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: 'linear-gradient(90deg, #FFB648, #FFD976)',
          borderRadius: 4,
          transition: 'width 0.5s ease',
        }} />
      </div>
      <span style={{ fontSize: 11, color: '#888', fontFamily: "'Nunito', system-ui" }}>
        {currentXp}/{neededXp}
      </span>
    </div>
  );
}
