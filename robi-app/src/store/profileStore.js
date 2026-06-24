import { create } from 'zustand';
import {
  loadProfiles,
  saveProfiles,
  loadActiveProfileId,
  saveActiveProfileId,
  resetProfile as storageResetProfile,
} from '../engine/storage.js';
import { calcLevel } from '../engine/progression.js';

const useProfileStore = create((set, get) => ({
  profiles: null,       // { amy: ProfileObject, lian: ProfileObject }
  activeId: 'amy',
  hydrated: false,

  // ── Selectors ─────────────────────────────────────────────────────────────

  activeProfile: () => get().profiles?.[get().activeId] ?? null,

  levelInfo: () => {
    const p = get().activeProfile();
    return p ? calcLevel(p.totalXp) : { level: 1, currentXp: 0, neededXp: 60 };
  },

  // ── Actions ───────────────────────────────────────────────────────────────

  hydrate: async () => {
    const [profiles, activeId] = await Promise.all([
      loadProfiles(),
      loadActiveProfileId(),
    ]);
    set({ profiles, activeId, hydrated: true });
  },

  switchProfile: async (id) => {
    set({ activeId: id });
    await saveActiveProfileId(id);
  },

  setLang: async (lang) => {
    const { profiles, activeId } = get();
    const updated = {
      ...profiles,
      [activeId]: { ...profiles[activeId], lang },
    };
    set({ profiles: updated });
    await saveProfiles(updated);
  },

  addXp: async (xp) => {
    const { profiles, activeId } = get();
    const prev = profiles[activeId];
    const updated = {
      ...profiles,
      [activeId]: { ...prev, totalXp: prev.totalXp + xp },
    };
    set({ profiles: updated });
    await saveProfiles(updated);
  },

  markStopComplete: async (categoryId) => {
    const { profiles, activeId } = get();
    const prev = profiles[activeId];
    if (prev.completedStops.includes(categoryId)) return;
    const updated = {
      ...profiles,
      [activeId]: {
        ...prev,
        completedStops: [...prev.completedStops, categoryId],
      },
    };
    set({ profiles: updated });
    await saveProfiles(updated);
  },

  earnBadge: async (badgeId) => {
    const { profiles, activeId } = get();
    const prev = profiles[activeId];
    if (prev.badges.includes(badgeId)) return;
    const updated = {
      ...profiles,
      [activeId]: { ...prev, badges: [...prev.badges, badgeId] },
    };
    set({ profiles: updated });
    await saveProfiles(updated);
  },

  markConceptSeen: async (conceptId) => {
    const { profiles, activeId } = get();
    const prev = profiles[activeId];
    if (prev.seenConcepts.includes(conceptId)) return;
    const updated = {
      ...profiles,
      [activeId]: {
        ...prev,
        seenConcepts: [...prev.seenConcepts, conceptId],
      },
    };
    set({ profiles: updated });
    await saveProfiles(updated);
  },

  resetProfile: async (profileId) => {
    const updated = await storageResetProfile(profileId);
    set({ profiles: updated });
  },
}));

export default useProfileStore;
