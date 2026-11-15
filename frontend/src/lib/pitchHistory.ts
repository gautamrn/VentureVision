import type { MemoOutput, ShareSeal } from "./types";

const STORAGE_KEY = "vv_pitch_history";
const MAX_ENTRIES = 20;

export interface PitchHistoryEntry {
  id: string;
  pitch: string;
  pitchScore: number;
  mode: string;
  date: string;
  memo: MemoOutput;
  /** Server signature that makes the memo shareable; absent for analyses saved before sharing existed. */
  seal?: ShareSeal;
}

export function getPitchHistory(): PitchHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as PitchHistoryEntry[];
  } catch {
    return [];
  }
}

export function savePitchResult(pitch: string, memo: MemoOutput, mode: string = "market_scan", seal?: ShareSeal): void {
  const history = getPitchHistory();

  const entry: PitchHistoryEntry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    pitch,
    pitchScore: memo.pitch_score,
    mode,
    date: seal?.generated_at ?? new Date().toISOString(),
    memo,
    seal,
  };

  history.unshift(entry);

  if (history.length > MAX_ENTRIES) {
    history.length = MAX_ENTRIES;
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

export function deletePitch(id: string): void {
  const history = getPitchHistory().filter((e) => e.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

export function getPitchById(id: string): PitchHistoryEntry | null {
  const history = getPitchHistory();
  return history.find((e) => e.id === id) ?? null;
}
