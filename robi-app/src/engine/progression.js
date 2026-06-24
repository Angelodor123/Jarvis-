// XP math and level calculation — pure functions, no side effects.

/**
 * XP awarded for a single round.
 * @param {number} correct - correct answers
 * @param {number} total   - total questions
 * @param {number} xpMultiplier - age mode multiplier (1.0 for Amy, 1.4 for Lian)
 */
export function calcRoundXp(correct, total, xpMultiplier = 1.0) {
  const base = Math.round((correct / total) * 40 + 10);
  return Math.round(base * xpMultiplier);
}

/**
 * XP required to reach a given level from zero at that level.
 * Level N requires (60 + (N-1)*25) XP to advance to N+1.
 */
export function xpToNextLevel(level) {
  return 60 + (level - 1) * 25;
}

/**
 * Calculates level and XP-within-level from total accumulated XP.
 * Returns { level, currentXp, neededXp }.
 */
export function calcLevel(totalXp) {
  let level = 1;
  let remaining = totalXp;

  while (true) {
    const needed = xpToNextLevel(level);
    if (remaining < needed) break;
    remaining -= needed;
    level++;
  }

  return {
    level,
    currentXp: remaining,
    neededXp: xpToNextLevel(level),
  };
}

/**
 * Star rating for a round result.
 * 3 stars = perfect, 2 = 2/3+, 1 = below 2/3.
 */
export function calcStars(correct, total) {
  const ratio = correct / total;
  if (ratio === 1) return 3;
  if (ratio >= 0.67) return 2;
  return 1;
}
