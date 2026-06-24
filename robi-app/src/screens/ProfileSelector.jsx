import React from 'react';
import useProfileStore from '../store/profileStore.js';
import useGameStore from '../store/gameStore.js';
import Robi from '../components/Robi/Robi.jsx';

export default function ProfileSelector() {
  const { profiles, switchProfile, hydrated } = useProfileStore();
  const goTo = useGameStore(s => s.goTo);

  if (!hydrated) {
    return (
      <div style={centeredStyle}>
        <Robi mood="thinking" size={100} />
        <p style={{ fontFamily: "'Baloo 2', system-ui", color: '#5B4B8A', marginTop: 20 }}>
          Loading…
        </p>
      </div>
    );
  }

  async function selectProfile(id) {
    await switchProfile(id);
    goTo('home');
  }

  return (
    <div style={centeredStyle}>
      <Robi mood="happy" size={110} />
      <h1 style={{
        fontFamily: "'Baloo 2', 'Varela Round', system-ui",
        fontSize: 28,
        color: '#5B4B8A',
        margin: '20px 0 8px',
        textAlign: 'center',
      }}>
        Who's playing? 🌟
      </h1>
      <p style={{
        fontFamily: "'Nunito', system-ui",
        color: '#888',
        fontSize: 15,
        marginBottom: 32,
      }}>
        בחרי מי משחקת
      </p>

      <div style={{ display: 'flex', gap: 24 }}>
        <ProfileChip
          id="amy"
          profile={profiles?.amy}
          emoji="🌟"
          color="#FF6B5B"
          onTap={() => selectProfile('amy')}
        />
        <ProfileChip
          id="lian"
          profile={profiles?.lian}
          emoji="🌸"
          color="#3DB5A0"
          onTap={() => selectProfile('lian')}
        />
      </div>
    </div>
  );
}

function ProfileChip({ profile, emoji, color, onTap }) {
  return (
    <button
      onClick={onTap}
      style={{
        background: 'white',
        border: `3px solid ${color}`,
        borderRadius: 20,
        padding: '20px 24px',
        cursor: 'pointer',
        textAlign: 'center',
        boxShadow: `0 6px 0 ${color}44`,
        transition: 'transform 0.1s',
        fontFamily: "'Baloo 2', system-ui",
        WebkitTapHighlightColor: 'transparent',
      }}
      onPointerDown={e => { e.currentTarget.style.transform = 'translateY(3px)'; e.currentTarget.style.boxShadow = 'none'; }}
      onPointerUp={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = `0 6px 0 ${color}44`; }}
    >
      <div style={{ fontSize: 48 }}>{emoji}</div>
      <div style={{ fontSize: 20, fontWeight: 800, color: '#3a2f5b', marginTop: 8 }}>{profile?.name}</div>
      <div style={{ fontSize: 13, color: '#888', marginTop: 4 }}>
        {profile?.ageMode === 'amy' ? 'גיל 5' : 'גיל 3'}
      </div>
    </button>
  );
}

const centeredStyle = {
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'linear-gradient(180deg, #FFD5A8 0%, #FFF0D4 60%, #E8F5E0 100%)',
  padding: 24,
};
