import React from 'react';
import useGameStore from '../store/gameStore.js';

// Vocabulary games
import PictureMatch   from '../games/vocabulary/PictureMatch.jsx';
import ListenFind     from '../games/vocabulary/ListenFind.jsx';
import AnimalHabitat  from '../games/vocabulary/AnimalHabitat.jsx';
import ColorPainter   from '../games/vocabulary/ColorPainter.jsx';
import MemoryPairs    from '../games/vocabulary/MemoryPairs.jsx';
import SortItOut      from '../games/vocabulary/SortItOut.jsx';

// AI literacy games
import AiSays           from '../games/ai-literacy/AiSays.jsx';
import FeedRobiExamples from '../games/ai-literacy/FeedRobiExamples.jsx';

const GAME_MAP = {
  PictureMatch,
  ListenFind,
  AnimalHabitat,
  ColorPainter,
  MemoryPairs,
  SortItOut,
  AiSays,
  FeedRobiExamples,
};

export default function GameRouter() {
  const activeGame = useGameStore(s => s.activeGame);
  const goTo       = useGameStore(s => s.goTo);

  const Game = GAME_MAP[activeGame];

  if (!Game) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#FFF8EC' }}>
        <div style={{ textAlign: 'center', fontFamily: "'Baloo 2', system-ui", color: '#5B4B8A' }}>
          <p>Unknown game: {activeGame}</p>
          <button onClick={() => goTo('home')} style={{ marginTop: 12, padding: '10px 20px', borderRadius: 12, border: 'none', background: '#5B4B8A', color: 'white', cursor: 'pointer', fontSize: 16 }}>
            ← Back to Home
          </button>
        </div>
      </div>
    );
  }

  return <Game />;
}
