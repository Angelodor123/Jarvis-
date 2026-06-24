// Curriculum rules: age configs, unlock logic, game assignment per category.
// Import this to answer "what can this profile do / play right now?"

import { WORDS, LIAN_WORDS, CATEGORIES, PATH_ORDER } from './categories.js';

// Age mode configs
export const AGE_CONFIGS = {
  amy: {
    ageMode: 'amy',
    roundSize: 6,           // questions per round
    xpMultiplier: 1.0,
    tileScale: 1.0,
    showWordText: true,     // show English text on answer tiles
  },
  lian: {
    ageMode: 'lian',
    roundSize: 3,
    xpMultiplier: 1.4,
    tileScale: 1.25,
    showWordText: false,    // picture-only answers
  },
};

// Games that are always available (level 1)
const BASE_GAMES = ['PictureMatch', 'ListenFind'];

// Category-specific games (always available if category is unlocked)
const CATEGORY_GAMES = {
  animals: ['AnimalHabitat'],
  colors:  ['ColorPainter'],
};

// Level-gated games (Amy only)
const LEVEL_GAMES = [
  { game: 'AiSays',          minLevel: 2,  ageModes: ['amy'] },
  { game: 'MemoryPairs',     minLevel: 3,  ageModes: ['amy'] },
  { game: 'SortItOut',       minLevel: 4,  ageModes: ['amy'] },
  { game: 'TeachTheAI',      minLevel: 6,  ageModes: ['amy'] },
  { game: 'FeedRobiExamples',minLevel: 6,  ageModes: ['amy'] },
  { game: 'RobiVsYou',       minLevel: 8,  ageModes: ['amy'] },
  { game: 'BreakTheAI',      minLevel: 8,  ageModes: ['amy'] },
];

/**
 * Returns the word list for a given category and ageMode.
 * Lian gets simplified lists only for supported categories; others fall back to full list.
 */
export function getWordsForCategory(categoryId, ageMode) {
  if (ageMode === 'lian' && LIAN_WORDS[categoryId]) {
    return LIAN_WORDS[categoryId];
  }
  return WORDS[categoryId] ?? [];
}

/**
 * Returns available game IDs for a category, level, and ageMode.
 */
export function getGamesForCategory(categoryId, level, ageMode) {
  const games = [...BASE_GAMES];

  const catSpecific = CATEGORY_GAMES[categoryId] ?? [];
  games.push(...catSpecific);

  for (const { game, minLevel, ageModes } of LEVEL_GAMES) {
    if (level >= minLevel && ageModes.includes(ageMode)) {
      games.push(game);
    }
  }

  return games;
}

/**
 * Returns the list of unlocked category IDs for a given level.
 */
export function getUnlockedCategories(level) {
  return PATH_ORDER.filter(id => CATEGORIES[id].unlockLevel <= level);
}

/**
 * Picks a random game for a category, weighted toward variety.
 * Avoids repeating the lastGame if other options exist.
 */
export function pickGame(categoryId, level, ageMode, lastGame = null) {
  const available = getGamesForCategory(categoryId, level, ageMode);
  const pool = available.length > 1
    ? available.filter(g => g !== lastGame)
    : available;
  return pool[Math.floor(Math.random() * pool.length)];
}

/**
 * Returns the numbers word list based on level tiers.
 */
export function getNumbersForLevel(level) {
  const { WORDS: W } = { WORDS };
  const base = WORDS.numbers; // 1-10
  // Level 5+: extend to 11-20 (would need extended data — stub for now)
  return base;
}
