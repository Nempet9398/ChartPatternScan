"use client";

import { use, useState, useEffect, useCallback } from "react";
import { fetchChart, analyzePattern } from "@/lib/api";
import type { OHLCVBar, PatternItem, Timeframe } from "@/lib/api";
import { useChartStore } from "@/store/chartStore";
import type { SelectionRange } from "@/store/chartStore";
import SearchBar from "@/components/SearchBar";
import PeriodSelector from "@/components/PeriodSelector";
import CandlestickChart from "@/components/CandlestickChart";
import type { RangeSelectEvent, PatternGeometry } from "@/components/CandlestickChart";
import PatternCard from "@/components/PatternCard";

const MIN_CANDLES = 60;

interface Props {
  params: Promise<{ symbol: string }>;
}

export default function ResultClient({ params }: Props) {
  const { symbol: routeSymbol } = use(params);
  const decodedSymbol = decodeURIComponent(routeSymbol);

  const { timeframe, selectionRange, setSymbol, setSelectionRange } = useChartStore();

  const [ohlcv,             setOhlcv]            = useState<OHLCVBar[]>([]);
  const [patterns,          setPatterns]          = useState<PatternItem[]>([]);
  const [selectedPatternIdx, setSelectedPatternIdx] = useState<number>(0);
  const [loading,           setLoading]           = useState(false);
  const [analyzeLoading,    setAnalyzeLoading]    = useState(false);
  const [error,             setError]             = useState<string | null>(null);
  const [rangeWarning,      setRangeWarning]      = useState<string | null>(null);
  const [analyzedAt,        setAnalyzedAt]        = useState("");

  useEffect(() => {
    setSymbol(decodedSymbol);
  }, [decodedSymbol, setSymbol]);

  // ── 차트 + 초기 분석 로드 ────────────────────────────────────────────────
  const loadChart = useCallback(
    async (sym: string, tf: Timeframe) => {
      setLoading(true);
      setError(null);
      setSelectionRange(null);
      setRangeWarning(null);
      try {
        const [chartRes, analyzeRes] = await Promise.all([
          fetchChart(sym, tf),
          analyzePattern(sym, tf),  // 구간 미선택 → 전체 데이터 분석
        ]);
        setOhlcv(chartRes.ohlcv);
        setPatterns(analyzeRes.top_patterns);
        setAnalyzedAt(analyzeRes.analyzed_at);
        setSelectedPatternIdx(0); // 새 분석 시 Top1 선택
      } catch (err) {
        setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    },
    [setSelectionRange],
  );

  useEffect(() => {
    loadChart(decodedSymbol, timeframe);
  }, [decodedSymbol, timeframe, loadChart]);

  const handleTimeframeChange = (tf: Timeframe) => {
    loadChart(decodedSymbol, tf);
  };

  // ── 드래그 구간 선택 ────────────────────────────────────────────────────
  const handleRangeSelect = useCallback(
    (e: RangeSelectEvent) => {
      if (e.candleCount < MIN_CANDLES) {
        setRangeWarning(
          `패턴 분석을 위해 최소 ${MIN_CANDLES}개의 캔들이 필요합니다. 현재 선택: ${e.candleCount}개`,
        );
        setSelectionRange(null);
      } else {
        setRangeWarning(null);
        setSelectionRange({
          startTime:   e.startTime,
          endTime:     e.endTime,
          candleCount: e.candleCount,
        });
      }
    },
    [setSelectionRange],
  );

  // ── 구간 분석 실행 ──────────────────────────────────────────────────────
  const handleAnalyze = useCallback(async () => {
    if (!selectionRange) return;
    setAnalyzeLoading(true);
    setError(null);
    console.log("[분석하기] 전송 값:", {
      symbol: decodedSymbol,
      timeframe,
      startTime: selectionRange.startTime,
      endTime: selectionRange.endTime,
      candleCount: selectionRange.candleCount,
    });
    try {
      const res = await analyzePattern(
        decodedSymbol,
        timeframe,
        selectionRange.startTime,
        selectionRange.endTime,
      );
      setPatterns(res.top_patterns);
      setAnalyzedAt(res.analyzed_at);
      setSelectedPatternIdx(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "분석 오류가 발생했습니다.");
    } finally {
      setAnalyzeLoading(false);
    }
  }, [decodedSymbol, timeframe, selectionRange]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* 헤더 */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-4 flex-wrap">
          <a href="/" className="text-xl font-black text-slate-900 shrink-0">
            Chart<span className="text-blue-600">Pattern</span>.io
          </a>
          <div className="flex-1 min-w-[240px]">
            <SearchBar />
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6">
        {/* 심볼 + 타임프레임 선택 */}
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div>
            <h2 className="text-2xl font-black text-slate-900">{decodedSymbol}</h2>
            {analyzedAt && (
              <p className="text-xs text-slate-400 mt-0.5">
                분석 시각: {new Date(analyzedAt).toLocaleString("ko-KR")}
              </p>
            )}
          </div>
          <PeriodSelector onChange={handleTimeframeChange} />
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 text-red-700 p-4 mb-4 text-sm">
            <strong>오류:</strong> {error}
          </div>
        )}

        {/* 60캔들 미만 경고 */}
        {rangeWarning && (
          <div className="rounded-xl bg-yellow-50 border border-yellow-200 text-yellow-800 p-3 mb-4 text-sm">
            ⚠️ {rangeWarning}
          </div>
        )}

        {/* 선택 구간 정보 + 분석하기 버튼 */}
        {selectionRange && (
          <div className="flex items-center gap-3 mb-4 p-3 rounded-xl bg-blue-50 border border-blue-200">
            <span className="text-sm text-blue-800 flex-1">
              선택 구간: <strong>{selectionRange.candleCount}캔들</strong>
              {" "}({selectionRange.startTime.slice(0, 10)} ~ {selectionRange.endTime.slice(0, 10)})
            </span>
            <button
              onClick={handleAnalyze}
              disabled={analyzeLoading}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 transition"
            >
              {analyzeLoading ? "분석 중..." : "분석하기"}
            </button>
            <button
              onClick={() => { setSelectionRange(null); setRangeWarning(null); }}
              className="px-3 py-1.5 text-slate-500 text-sm rounded-lg hover:bg-slate-100 transition"
            >
              초기화
            </button>
          </div>
        )}

        {/* 로딩 스피너 */}
        {loading && (
          <div className="flex items-center justify-center py-20 text-slate-400 text-sm gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            데이터 로딩 중...
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* 차트 (2/3) */}
            <div className="lg:col-span-2">
              {ohlcv.length > 0 ? (
                <CandlestickChart
                  ohlcv={ohlcv}
                  patterns={patterns}
                  activePatternGeometry={
                    (patterns[selectedPatternIdx]?.pattern_geometry as PatternGeometry | undefined) ?? null
                  }
                  height={440}
                  onRangeSelect={handleRangeSelect}
                  selectionRange={selectionRange}
                />
              ) : (
                <div className="rounded-xl border border-slate-200 bg-white
                                flex items-center justify-center h-[440px] text-slate-400 text-sm">
                  차트 데이터 없음
                </div>
              )}
            </div>

            {/* 패턴 카드 (1/3) */}
            <div className="flex flex-col gap-4">
              {analyzeLoading ? (
                <div className="flex items-center justify-center h-40 text-slate-400 text-sm gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                            stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  패턴 분석 중...
                </div>
              ) : patterns.length > 0 ? (
                patterns.map((p, idx) => (
                  <PatternCard
                    key={p.rank}
                    pattern={p}
                    isSelected={selectedPatternIdx === idx}
                    onClick={() => setSelectedPatternIdx(idx)}
                  />
                ))
              ) : (
                <div className="rounded-xl border border-slate-200 bg-white p-6
                                text-slate-400 text-sm text-center">
                  패턴 정보 없음
                </div>
              )}
            </div>
          </div>
        )}

        {/* 알고리즘 출처 */}
        {!loading && (
          <p className="mt-6 text-xs text-slate-400 text-center">
            Algorithm: Lo, Mamaysky &amp; Wang (2000), <em>Journal of Finance</em> Vol.55 No.4
            &nbsp;·&nbsp; 성공률 출처: Bulkowski (2005), <em>Encyclopedia of Chart Patterns</em>
          </p>
        )}
      </main>

      {/* 푸터 면책 고지 */}
      <footer className="border-t border-slate-200 bg-white py-4 px-4">
        <p className="text-center text-xs text-slate-400">
          본 서비스의 분석 결과는 투자 권유가 아닙니다. 투자 손익의 책임은 전적으로 본인에게 있습니다.
        </p>
      </footer>
    </div>
  );
}
