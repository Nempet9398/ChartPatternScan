/**
 * API 클라이언트 — 백엔드 FastAPI 와의 통신 담당.
 *
 * 환경변수:
 *   NEXT_PUBLIC_API_URL  (기본: http://localhost:8000)
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── 타입 정의 ──────────────────────────────────────────────────────────────────

export type Timeframe = "15m" | "30m" | "1h" | "6h" | "12h" | "1D" | "1W";

export interface OHLCVBar {
  time: string | number;  // 일봉/주봉: "YYYY-MM-DD", 분봉/시봉: Unix 초
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartResponse {
  symbol: string;
  timeframe: Timeframe;
  ohlcv: OHLCVBar[];
}

export interface PatternItem {
  rank: number;
  name: string;
  name_ko: string;
  similarity: number;
  signal: "bullish" | "bearish" | "neutral";
  description: string;
  historical_success_rate: number;
  source: string;
  highlight_start: string | null;
  highlight_end: string | null;
}

export interface AnalyzeResponse {
  symbol: string;
  timeframe: Timeframe;
  analyzed_at: string;
  algorithm_ref: string;
  top_patterns: PatternItem[];
}

export interface SearchResult {
  symbol: string;
  name: string;
  market: string;
}

export interface SearchResponse {
  results: SearchResult[];
}

// ── API 함수 ───────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `API 오류 ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export async function fetchChart(
  symbol: string,
  timeframe: Timeframe,
): Promise<ChartResponse> {
  return apiFetch<ChartResponse>(
    `/api/chart/${encodeURIComponent(symbol)}?timeframe=${timeframe}`,
  );
}

export async function analyzePattern(
  symbol: string,
  timeframe: Timeframe,
  startTime?: string | null,
  endTime?: string | null,
): Promise<AnalyzeResponse> {
  return apiFetch<AnalyzeResponse>("/api/analyze", {
    method: "POST",
    body: JSON.stringify({
      symbol,
      timeframe,
      start_time: startTime ?? null,
      end_time: endTime ?? null,
    }),
  });
}

export async function searchSymbol(query: string): Promise<SearchResponse> {
  return apiFetch<SearchResponse>(`/api/search?q=${encodeURIComponent(query)}`);
}
