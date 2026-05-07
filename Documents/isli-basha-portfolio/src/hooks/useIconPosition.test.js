import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import {
  useIconPosition,
  clearIconPositions,
  __TEST__,
} from './useIconPosition.js';

const { STORAGE_KEY } = __TEST__;
const DEFAULT = { x: 16, y: 16 };

describe('useIconPosition', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('returns the default position when nothing is stored', () => {
    const { result } = renderHook(() => useIconPosition('about', DEFAULT));
    expect(result.current.pos).toEqual(DEFAULT);
  });

  it('persists a saved position to localStorage', () => {
    const { result } = renderHook(() => useIconPosition('about', DEFAULT));
    act(() => {
      result.current.savePosition({ x: 120, y: 200 });
    });
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    expect(stored.about).toEqual({ x: 120, y: 200 });
  });

  it('restores a saved position on next mount', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ about: { x: 50, y: 80 } }));
    const { result } = renderHook(() => useIconPosition('about', DEFAULT));
    expect(result.current.pos).toEqual({ x: 50, y: 80 });
  });

  it('preserves other icon positions when saving one', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ snake: { x: 20, y: 100 } }));
    const { result } = renderHook(() => useIconPosition('about', DEFAULT));
    act(() => {
      result.current.savePosition({ x: 5, y: 5 });
    });
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    expect(stored).toEqual({ snake: { x: 20, y: 100 }, about: { x: 5, y: 5 } });
  });

  it('does not write to localStorage when disabled', () => {
    const { result } = renderHook(() =>
      useIconPosition('about', DEFAULT, { enabled: false }),
    );
    act(() => {
      result.current.savePosition({ x: 99, y: 99 });
    });
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('falls back to default when stored payload is malformed', () => {
    localStorage.setItem(STORAGE_KEY, 'not valid json{{{');
    const { result } = renderHook(() => useIconPosition('about', DEFAULT));
    expect(result.current.pos).toEqual(DEFAULT);
  });

  it('clearIconPositions removes the storage key entirely', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ about: { x: 1, y: 2 } }));
    clearIconPositions();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('setPos updates position in-place without persisting', () => {
    const { result } = renderHook(() => useIconPosition('about', DEFAULT));
    act(() => {
      result.current.setPos({ x: 77, y: 88 });
    });
    expect(result.current.pos).toEqual({ x: 77, y: 88 });
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});
