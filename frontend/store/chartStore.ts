/**
 * Zustand 전역 상태 — 검색어 + 타임프레임 + 구간 선택 공유.
 */

import { create } from "zustand";
import type { Timeframe } from "@/lib/api";

export interface SelectionRange {
  startTime: string;   // ISO 문자열 (백엔드 전송용)
  endTime: string;
  candleCount: number; // 선택 구간 내 캔들 수 (UI 표시용)
}

interface ChartState {
  symbol: string;
  timeframe: Timeframe;
  selectionRange: SelectionRange | null;
  setSymbol: (s: string) => void;
  setTimeframe: (t: Timeframe) => void;
  setSelectionRange: (r: SelectionRange | null) => void;
}

export const useChartStore = create<ChartState>((set) => ({
  symbol: "AAPL",
  timeframe: "1D",
  selectionRange: null,
  setSymbol: (symbol) => set({ symbol }),
  // 타임프레임 변경 시 이전 구간 선택 초기화
  setTimeframe: (timeframe) => set({ timeframe, selectionRange: null }),
  setSelectionRange: (selectionRange) => set({ selectionRange }),
}));
