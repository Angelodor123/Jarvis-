// AI literacy concept ladder — ordered from simplest to most advanced.
// Each concept is a milestone in Robi's Brain progression.

export const AI_CONCEPTS = [
  {
    id: 'talks_back',
    order: 1,
    unlockLevel: 1,
    badge: '💬',
    titleEn: 'AI Talks With You',
    titleHe: 'AI מדבר איתך',
    descEn: 'You\'re talking to an AI right now! It listens and responds to you.',
    descHe: 'את מדברת עם AI עכשיו! הוא מקשיב ועונה לך.',
    game: null, // felt through all gameplay, no dedicated game
  },
  {
    id: 'can_be_wrong',
    order: 2,
    unlockLevel: 2,
    badge: '🙈',
    titleEn: 'AI Can Be Wrong',
    titleHe: 'AI יכול לטעות',
    descEn: 'Robi doesn\'t always know the right answer. When he gets it wrong, you can teach him!',
    descHe: 'רובי לא תמיד יודע את התשובה הנכונה. כשהוא טועה, את יכולה ללמד אותו!',
    game: 'AiSays',
  },
  {
    id: 'pays_attention',
    order: 3,
    unlockLevel: 4,
    badge: '👀',
    titleEn: 'AI Notices Patterns',
    titleHe: 'AI שם לב לדפוסים',
    descEn: 'Robi watches what you do and picks harder questions when you\'re on a roll!',
    descHe: 'רובי מתבונן במה שאת עושה ובוחר שאלות קשות יותר כשאת במגמת עלייה!',
    game: null, // revealed via commentary in other games
  },
  {
    id: 'learns_from_examples',
    order: 4,
    unlockLevel: 6,
    badge: '📚',
    titleEn: 'AI Learns From Examples',
    titleHe: 'AI לומד מדוגמאות',
    descEn: 'You can teach Robi by showing him examples. The more you show, the smarter he gets!',
    descHe: 'את יכולה ללמד את רובי על ידי הצגת דוגמאות. ככל שתראי יותר, הוא ייהפך לחכם יותר!',
    game: 'FeedRobiExamples',
  },
  {
    id: 'ai_vs_person',
    order: 5,
    unlockLevel: 8,
    badge: '🧑‍🤝‍🤖',
    titleEn: 'AI Learns Differently Than You',
    titleHe: 'AI לומד אחרת ממך',
    descEn: 'You learned "dog" by petting one. Robi needed to see thousands of pictures!',
    descHe: 'את למדת "כלב" על ידי ליטוף אחד. רובי היה צריך לראות אלפי תמונות!',
    game: 'RobiVsYou',
  },
];

export const AI_CONCEPT_IDS = AI_CONCEPTS.map(c => c.id);
