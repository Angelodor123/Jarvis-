import React, { useRef, useState } from 'react';
import useProfileStore from '../store/profileStore.js';
import useGameStore from '../store/gameStore.js';
import { calcLevel } from '../engine/progression.js';
import { getUnlockedCategories } from '../data/curriculum.js';
import ParallaxForest from '../components/forest/ParallaxForest.jsx';
import PathTrail from '../components/forest/PathTrail.jsx';
import Robi from '../components/Robi/Robi.jsx';
import LevelHud from '../components/ui/LevelHud.jsx';

export default function ForestPath() {
  const profile      = useProfileStore(s => s.activeProfile());
  const activeId     = useProfileStore(s => s.activeId);
  const switchProfile = useProfileStore(s => s.switchProfile);
  const goTo         = useGameStore(s => s.goTo);
  const startNarration = useGameStore(s => s.startNarration);

  const [scrollY, setScrollY] = useState(0);
  const [holdProgress, setHoldProgress] = useState(0);
  const holdTimer = useRef(null);
  const holdInterval = useRef(null);

  const { level } = calcLevel(profile?.totalXp ?? 0);
  const unlocked  = getUnlockedCategories(level);
  const completed = profile?.completedStops ?? [];

  function handleScroll(e) {
    setScrollY(e.currentTarget.scrollTop);
  }

  function handleStopTap(categoryId) {
    startNarration(categoryId);
  }

  // Parent gate — 3-second press-and-hold
  function startHold() {
    let progress = 0;
    holdInterval.current = setInterval(() => {
      progress += 100 / 30; // ~3 seconds at 100ms intervals
      setHoldProgress(Math.min(progress, 100));
    }, 100);
    holdTimer.current = setTimeout(() => {
      clearInterval(holdInterval.current);
      setHoldProgress(0);
      goTo('parent');
    }, 3000);
  }

  function cancelHold() {
    clearTimeout(holdTimer.current);
    clearInterval(holdInterval.current);
    setHoldProgress(0);
  }

  if (!profile) return null;

  const otherProfileId = activeId === 'amy' ? 'lian' : 'amy';

  return (
    <div style={{ height: '100vh', overflow: 'hidden', position: 'relative' }}>
      <ParallaxForest scrollY={scrollY}>
        {/* HUD */}
        <div style={{
          position: 'fixed',
          top: 12,
          left: 12,
          right: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 10,
        }}>
          <LevelHud />

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {/* Language toggle */}
            <LangToggle profile={profile} />

            {/* Profile switcher chips */}
            <ProfileChip
              id={activeId}
              emoji={activeId === 'amy' ? '🌟' : '🌸'}
              active
            />
            <ProfileChip
              id={otherProfileId}
              emoji={otherProfileId === 'amy' ? '🌟' : '🌸'}
              active={false}
              onTap={() => switchProfile(otherProfileId)}
            />

            {/* Settings gear (parent gate) */}
            <button
              onPointerDown={startHold}
              onPointerUp={cancelHold}
              onPointerLeave={cancelHold}
              style={gearStyle}
            >
              <SettingsGear progress={holdProgress} />
            </button>
          </div>
        </div>

        {/* Scrollable path */}
        <div
          onScroll={handleScroll}
          style={{
            height: '100vh',
            overflowY: 'auto',
            paddingTop: 70,
            paddingBottom: 40,
            scrollbarWidth: 'none',
          }}
        >
          {/* Robi introduction area */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            padding: '20px 24px',
            marginBottom: 8,
          }}>
            <Robi mood="idle" size={90} />
            <div style={{
              background: 'white',
              borderRadius: 16,
              padding: '12px 18px',
              boxShadow: '0 4px 16px rgba(91,75,138,0.15)',
              fontFamily: "'Nunito', system-ui",
              fontSize: 15,
              color: '#3a2f5b',
              lineHeight: 1.5,
              maxWidth: 200,
              position: 'relative',
            }}>
              <div style={{ position: 'absolute', left: -10, top: 16, width: 0, height: 0, borderTop: '8px solid transparent', borderBottom: '8px solid transparent', borderRight: '12px solid white' }} />
              {profile.lang === 'he'
                ? `שלום ${profile.name}! 🌟 בחרי עצירה לשחק!`
                : `Hi ${profile.name}! 🌟 Tap a stop to play!`
              }
            </div>
          </div>

          <PathTrail
            unlockedIds={unlocked}
            completedIds={completed}
            currentId={unlocked[unlocked.length - 1]}
            onStopTap={handleStopTap}
          />
        </div>
      </ParallaxForest>
    </div>
  );
}

function LangToggle({ profile }) {
  const setLang = useProfileStore(s => s.setLang);
  return (
    <button
      onClick={() => setLang(profile.lang === 'he' ? 'en' : 'he')}
      style={{
        background: 'rgba(255,255,255,0.85)',
        border: '2px solid #5B4B8A',
        borderRadius: 12,
        padding: '4px 10px',
        fontFamily: "'Baloo 2', system-ui",
        fontWeight: 700,
        fontSize: 13,
        color: '#5B4B8A',
        cursor: 'pointer',
      }}
    >
      {profile.lang === 'he' ? 'EN' : 'עב'}
    </button>
  );
}

function ProfileChip({ id, emoji, active, onTap }) {
  return (
    <button
      onClick={onTap}
      disabled={active}
      style={{
        background: active ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.85)',
        border: '2px solid rgba(255,255,255,0.8)',
        borderRadius: 12,
        padding: '4px 8px',
        fontSize: 18,
        cursor: active ? 'default' : 'pointer',
        opacity: active ? 0.4 : 1,
      }}
    >
      {emoji}
    </button>
  );
}

function SettingsGear({ progress }) {
  return (
    <div style={{ position: 'relative', width: 36, height: 36 }}>
      <svg width="36" height="36" viewBox="0 0 36 36">
        {/* Background circle */}
        <circle cx="18" cy="18" r="16" fill="rgba(255,255,255,0.85)" />
        {/* Progress ring */}
        {progress > 0 && (
          <circle
            cx="18" cy="18" r="15"
            fill="none"
            stroke="#5B4B8A"
            strokeWidth="3"
            strokeDasharray={`${(progress / 100) * 94} 94`}
            strokeLinecap="round"
            transform="rotate(-90 18 18)"
          />
        )}
        {/* Gear icon */}
        <text x="18" y="23" textAnchor="middle" fontSize="16">⚙️</text>
      </svg>
    </div>
  );
}

const gearStyle = {
  background: 'none',
  border: 'none',
  padding: 0,
  cursor: 'pointer',
  WebkitTapHighlightColor: 'transparent',
};
