/**
 * Zustand 전역 상태 — 검색어 + 기간 공유.
 */

import { create } from "zustand";
import type { Period } from "@/lib/api";

interface ChartState {
  symbol: string;
  period: Period;
  setSymbol: (s: string) => void;
  setPeriod: (p: Period) => void;
}

export const useChartStore = create<ChartState>((set) => ({
  symbol: "AAPL",
  period: "3mo",
  setSymbol: (symbol) => set({ symbol }),
  setPeriod: (period) => set({ period }),
}));
