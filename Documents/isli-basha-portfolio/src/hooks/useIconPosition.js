import { useCallback, useState } from 'react';

const STORAGE_KEY = 'win95:icons:v1';

function readAll() {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object') return parsed;
    return {};
  } catch {
    return {};
  }
}

function writeAll(map) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    /* quota exceeded or unavailable */
  }
}

export function useIconPosition(id, defaultPos, { enabled = true } = {}) {
  const [pos, setPos] = useState(() => {
    if (!enabled) return defaultPos;
    const stored = readAll()[id];
    if (stored && typeof stored.x === 'number' && typeof stored.y === 'number') {
      return { x: stored.x, y: stored.y };
    }
    return defaultPos;
  });

  const savePosition = useCallback(
    (next) => {
      setPos(next);
      if (!enabled) return;
      const map = readAll();
      map[id] = next;
      writeAll(map);
    },
    [id, enabled],
  );

  return { pos, setPos, savePosition };
}

export function clearIconPositions() {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* fail silently */
  }
}

export const __TEST__ = { STORAGE_KEY };
