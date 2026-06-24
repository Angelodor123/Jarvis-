import React from 'react';
import useProfileStore from '../store/profileStore.js';
import useGameStore from '../store/gameStore.js';
import { calcLevel } from '../engine/progression.js';
import { CATEGORIES, PATH_ORDER } from '../data/categories.js';
import { AI_CONCEPTS } from '../data/aiConcepts.js';
import PrimaryButton from '../components/ui/PrimaryButton.jsx';

export default function ParentDashboard() {
  const { profiles, activeId, resetProfile } = useProfileStore();
  const goTo = useGameStore(s => s.goTo);

  if (!profiles) return null;

  return (
    <div style={{
      minHeight: '100vh',
      background: '#1a1025',
      color: 'white',
      padding: 24,
      fontFamily: "'Nunito', system-ui",
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontFamily: "'Baloo 2', system-ui", fontSize: 22, margin: 0, color: '#FFD976' }}>
            ⚙️ Parent Dashboard
          </h1>
          <p style={{ fontSize: 13, color: '#888', margin: '4px 0 0' }}>Long-press ⚙️ from home to access</p>
        </div>
        <PrimaryButton color="#5B4B8A" onClick={() => goTo('home')} style={{ fontSize: 14, padding: '10px 20px' }}>
          ← Back
        </PrimaryButton>
      </div>

      {/* Profile cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {['amy', 'lian'].map(id => {
          const p = profiles[id];
          if (!p) return null;
          const { level, currentXp, neededXp } = calcLevel(p.totalXp);
          const pct = Math.round((currentXp / neededXp) * 100);

          return (
            <div key={id} style={{
              background: 'rgba(255,255,255,0.06)',
              borderRadius: 20,
              padding: 20,
              border: activeId === id ? '2px solid #FFD976' : '2px solid rgba(255,255,255,0.1)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <span style={{ fontSize: 22, fontFamily: "'Baloo 2', system-ui", fontWeight: 800 }}>
                    {id === 'amy' ? '🌟' : '🌸'} {p.name}
                  </span>
                  <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
                    {id === 'amy' ? 'Age 5 · Full curriculum' : 'Age 3 · Simplified'}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontFamily: "'Baloo 2', system-ui", fontSize: 20, fontWeight: 800, color: '#FFB648' }}>
                    Level {level}
                  </div>
                  <div style={{ fontSize: 12, color: '#888' }}>{p.totalXp} XP total</div>
                </div>
              </div>

              {/* XP bar */}
              <div style={{ height: 8, background: 'rgba(255,255,255,0.1)', borderRadius: 4, marginBottom: 16 }}>
                <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #FFB648, #FFD976)', borderRadius: 4 }} />
              </div>

              {/* Vocabulary progress */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, color: '#aaa', marginBottom: 8, fontWeight: 600 }}>Vocabulary Stops</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {PATH_ORDER.map(catId => {
                    const cat = CATEGORIES[catId];
                    const done = p.completedStops.includes(catId);
                    return (
                      <span key={catId} style={{
                        padding: '4px 10px',
                        borderRadius: 20,
                        background: done ? cat.color : 'rgba(255,255,255,0.08)',
                        fontSize: 12,
                        fontWeight: 600,
                        color: done ? 'white' : '#666',
                      }}>
                        {done ? '✓ ' : ''}{cat.labelEn}
                      </span>
                    );
                  })}
                </div>
              </div>

              {/* AI badges */}
              {id === 'amy' && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 13, color: '#aaa', marginBottom: 8, fontWeight: 600 }}>AI Literacy Badges</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {AI_CONCEPTS.map(concept => {
                      const earned = p.badges.includes(concept.id);
                      return (
                        <span key={concept.id} style={{
                          fontSize: 22,
                          opacity: earned ? 1 : 0.2,
                          title: concept.titleEn,
                        }}>
                          {concept.badge}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Reset button */}
              <button
                onClick={() => {
                  if (confirm(`Reset ${p.name}'s progress? This cannot be undone.`)) {
                    resetProfile(id);
                  }
                }}
                style={{
                  background: 'rgba(255,100,80,0.15)',
                  border: '1px solid rgba(255,100,80,0.3)',
                  borderRadius: 10,
                  padding: '8px 16px',
                  color: '#FF6B5B',
                  fontSize: 13,
                  cursor: 'pointer',
                  fontFamily: "'Nunito', system-ui",
                  fontWeight: 600,
                }}
              >
                Reset {p.name}'s Progress
              </button>
            </div>
          );
        })}
      </div>

      {/* Language note */}
      <div style={{ marginTop: 24, padding: 16, background: 'rgba(255,255,255,0.04)', borderRadius: 12, fontSize: 13, color: '#666', lineHeight: 1.6 }}>
        <strong style={{ color: '#888' }}>About TTS:</strong> Speech synthesis works in real Chrome/Safari. It is blocked inside Claude artifact iframes — use the published link for full audio.
      </div>
    </div>
  );
}
