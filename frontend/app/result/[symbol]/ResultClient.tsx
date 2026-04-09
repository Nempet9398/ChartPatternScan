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
import { useToast } from "@/components/Toast";

const MIN_CANDLES = 60;

// 단계별 로딩 메시지
const LOAD_STEPS = [
  "데이터 수집 중...",
  "18개 패턴 분석 중...",
];

interface Props {
  params: Promise<{ symbol: string }>;
}

export default function ResultClient({ params }: Props) {
  const { symbol: routeSymbol } = use(params);
  const decodedSymbol = decodeURIComponent(routeSymbol);

  const { timeframe, selectionRange, setSymbol, setSelectionRange } = useChartStore();
  const { showToast } = useToast();

  const [ohlcv,              setOhlcv]             = useState<OHLCVBar[]>([]);
  const [patterns,           setPatterns]           = useState<PatternItem[]>([]);
  const [selectedPatternIdx, setSelectedPatternIdx] = useState<number>(0);
  const [loading,            setLoading]            = useState(false);
  const [loadStep,           setLoadStep]           = useState(0);
  const [analyzeLoading,     setAnalyzeLoading]     = useState(false);
  const [error,              setError]              = useState<string | null>(null);
  const [rangeWarning,       setRangeWarning]       = useState<string | null>(null);
  const [analyzedAt,         setAnalyzedAt]         = useState("");

  // 차트 페이드 전환용 — 새 데이터 로드 중에도 이전 차트 유지
  const [chartVisible, setChartVisible] = useState(true);

  useEffect(() => {
    setSymbol(decodedSymbol);
  }, [decodedSymbol, setSymbol]);

  // ── 차트 + 초기 분석 로드 ────────────────────────────────────────────────
  const loadChart = useCallback(
    async (sym: string, tf: Timeframe) => {
      setLoading(true);
      setLoadStep(0);
      setError(null);
      setSelectionRange(null);
      setRangeWarning(null);

      // 이전 차트 페이드 아웃
      setChartVisible(false);

      // 단계 1: 데이터 수집 중
      const stepTimer = setTimeout(() => setLoadStep(1), 800);

      try {
        const [chartRes, analyzeRes] = await Promise.all([
          fetchChart(sym, tf),
          analyzePattern(sym, tf),
        ]);
        clearTimeout(stepTimer);
        setOhlcv(chartRes.ohlcv);
        setPatterns(analyzeRes.top_patterns);
        setAnalyzedAt(analyzeRes.analyzed_at);
        setSelectedPatternIdx(0);

        // 페이드 인
        setTimeout(() => setChartVisible(true), 50);
        showToast("분석 완료!", "success");
      } catch (err) {
        clearTimeout(stepTimer);
        const msg = err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.";
        setError(msg);
        setChartVisible(true);
        showToast(msg, "error");
      } finally {
        setLoading(false);
      }
    },
    [setSelectionRange, showToast],
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
      showToast("구간 분석 완료!", "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "분석 오류가 발생했습니다.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setAnalyzeLoading(false);
    }
  }, [decodedSymbol, timeframe, selectionRange, showToast]);

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

        {/* 에러 메시지 + 재시도 버튼 */}
        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 text-red-700 p-4 mb-4 text-sm flex items-start justify-between gap-3">
            <span><strong>오류:</strong> {error}</span>
            <button
              onClick={() => loadChart(decodedSymbol, timeframe)}
              className="shrink-0 px-3 py-1 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-xs font-medium transition"
            >
              재시도
            </button>
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

        {/* 단계별 로딩 스피너 */}
        {loading && (
          <div className="flex items-center justify-center py-20 text-slate-400 text-sm gap-2">
            <svg className="animate-spin h-5 w-5 text-blue-400" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span className="transition-all duration-300">{LOAD_STEPS[loadStep]}</span>
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* 차트 (2/3) — 페이드 전환 */}
            <div
              className="lg:col-span-2 transition-opacity duration-300"
              style={{ opacity: chartVisible ? 1 : 0 }}
            >
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
                <div className="flex flex-col items-center justify-center h-52 gap-3 rounded-2xl
                                border border-slate-200 bg-white text-slate-400 text-sm">
                  <svg className="animate-spin h-7 w-7 text-blue-400" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                            stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>18개 패턴 분석 중...</span>
                </div>
              ) : patterns.length > 0 ? (
                <>
                  <p className="text-xs text-slate-400 text-center select-none">
                    카드를 클릭하면 차트에 패턴 특성선이 그려집니다
                  </p>
                  {patterns.map((p, idx) => (
                    <PatternCard
                      key={p.rank}
                      pattern={p}
                      isSelected={selectedPatternIdx === idx}
                      onClick={() => setSelectedPatternIdx(idx)}
                      animationDelay={idx * 100}
                    />
                  ))}
                </>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8
                                flex flex-col items-center gap-3 text-center">
                  <svg className="h-10 w-10 text-slate-300" fill="none" viewBox="0 0 24 24"
                       stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round"
                          d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-slate-500">패턴 분석 전</p>
                    <p className="mt-1 text-xs text-slate-400">
                      구간을 선택하거나 분석 버튼을 눌러<br />Top 3 패턴을 탐지하세요
                    </p>
                  </div>
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
