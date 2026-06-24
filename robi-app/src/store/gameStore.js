import { create } from 'zustand';

const useGameStore = create((set, get) => ({
  // Navigation
  screen: 'profile',  // 'profile' | 'home' | 'narration' | 'game' | 'complete'

  // Active game session
  activeCategory: null,
  activeGame: null,
  roundResults: null,     // { correct, total, xpEarned, leveledUp, stars }

  // Robi mood
  robiMood: 'idle',       // 'idle' | 'happy' | 'thinking' | 'oops'

  // Streak tracking for AI literacy commentary
  streak: 0,

  // ── Navigation ───────────────────────────────────────────────────────────

  goTo: (screen) => set({ screen }),

  startNarration: (categoryId) => set({
    screen: 'narration',
    activeCategory: categoryId,
    activeGame: null,
    roundResults: null,
  }),

  startGame: (categoryId, gameId) => set({
    screen: 'game',
    activeCategory: categoryId,
    activeGame: gameId,
    roundResults: null,
  }),

  finishRound: (results) => set({
    screen: 'complete',
    roundResults: results,
    streak: 0,
  }),

  // ── Robi mood ─────────────────────────────────────────────────────────────

  setRobiMood: (mood) => set({ robiMood: mood }),

  // ── Streak ────────────────────────────────────────────────────────────────

  incrementStreak: () => set(s => ({ streak: s.streak + 1 })),
  resetStreak: () => set({ streak: 0 }),
}));

export default useGameStore;
