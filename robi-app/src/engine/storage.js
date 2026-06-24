// Storage abstraction layer.
// Tries window.storage (Claude artifact API) first, falls back to localStorage.
// All reads/writes go through this module — never call storage APIs directly elsewhere.

const KEYS = {
  profiles:      'robi_profiles_v1',
  activeProfile: 'robi_active_profile_v1',
  legacy:        'robi_profile_v1',
};

function isClaudeStorage() {
  return typeof window !== 'undefined' && typeof window.storage?.get === 'function';
}

async function rawGet(key) {
  try {
    if (isClaudeStorage()) {
      return await window.storage.get(key, false);
    }
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (err) {
    console.error('[storage] get failed', key, err);
    return null;
  }
}

async function rawSet(key, value) {
  try {
    if (isClaudeStorage()) {
      await window.storage.set(key, value, false);
    } else {
      localStorage.setItem(key, JSON.stringify(value));
    }
  } catch (err) {
    console.error('[storage] set failed', key, err);
  }
}

async function rawDelete(key) {
  try {
    if (isClaudeStorage()) {
      await window.storage.delete(key, false);
    } else {
      localStorage.removeItem(key);
    }
  } catch (err) {
    console.error('[storage] delete failed', key, err);
  }
}

// ─── Public API ───────────────────────────────────────────────────────────────

export async function loadProfiles() {
  let profiles = await rawGet(KEYS.profiles);

  // Migrate legacy single-profile key
  if (!profiles) {
    const legacy = await rawGet(KEYS.legacy);
    if (legacy) {
      profiles = {
        amy: { ...makeDefaultProfile('Amy', 'amy'), ...legacy },
        lian: makeDefaultProfile('Lian', 'lian'),
      };
      await rawSet(KEYS.profiles, profiles);
      await rawDelete(KEYS.legacy);
    }
  }

  if (!profiles) {
    profiles = {
      amy:  makeDefaultProfile('Amy',  'amy'),
      lian: makeDefaultProfile('Lian', 'lian'),
    };
    await rawSet(KEYS.profiles, profiles);
  }

  return profiles;
}

export async function saveProfiles(profiles) {
  await rawSet(KEYS.profiles, profiles);
}

export async function loadActiveProfileId() {
  return (await rawGet(KEYS.activeProfile)) ?? 'amy';
}

export async function saveActiveProfileId(id) {
  await rawSet(KEYS.activeProfile, id);
}

export async function resetProfile(profileId) {
  const profiles = await loadProfiles();
  const name = profiles[profileId]?.name ?? profileId;
  profiles[profileId] = makeDefaultProfile(name, profileId);
  await rawSet(KEYS.profiles, profiles);
  return profiles;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function makeDefaultProfile(name, ageMode) {
  return {
    name,
    lang: 'he',
    ageMode,         // 'amy' | 'lian'
    totalXp: 0,
    seenConcepts: [],
    badges: [],
    completedStops: [],
    createdAt: Date.now(),
  };
}

export { KEYS };
