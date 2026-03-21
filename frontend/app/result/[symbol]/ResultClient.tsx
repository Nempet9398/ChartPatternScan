"use client";

import { use, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchChart, analyzePattern } from "@/lib/api";
import type { OHLCVBar, PatternItem, Period } from "@/lib/api";
import { useChartStore } from "@/store/chartStore";
import SearchBar from "@/components/SearchBar";
import PeriodSelector from "@/components/PeriodSelector";
import CandlestickChart from "@/components/CandlestickChart";
import PatternCard from "@/components/PatternCard";

interface Props {
  params: Promise<{ symbol: string }>;
}

export default function ResultClient({ params }: Props) {
  const { symbol: routeSymbol } = use(params);
  const decodedSymbol = decodeURIComponent(routeSymbol);

  const router = useRouter();
  const { period, setSymbol } = useChartStore();

  const [ohlcv,    setOhlcv]    = useState<OHLCVBar[]>([]);
  const [patterns, setPatterns] = useState<PatternItem[]>([]);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const [analyzedAt, setAnalyzedAt] = useState<string>("");

  // 심볼이 URL에서 왔으면 store에도 동기화
  useEffect(() => {
    setSymbol(decodedSymbol);
  }, [decodedSymbol, setSymbol]);

  const load = useCallback(
    async (sym: string, p: Period) => {
      setLoading(true);
      setError(null);
      try {
        const [chartRes, analyzeRes] = await Promise.all([
          fetchChart(sym, p),
          analyzePattern(sym, p),
        ]);
        setOhlcv(chartRes.ohlcv);
        setPatterns(analyzeRes.top_patterns);
        setAnalyzedAt(analyzeRes.analyzed_at);
      } catch (err) {
        setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // 초기 로드
  useEffect(() => {
    load(decodedSymbol, period);
  }, [decodedSymbol, period, load]);

  const handlePeriodChange = (p: Period) => {
    load(decodedSymbol, p);
  };

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

      {/* 메인 */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6">
        {/* 심볼 + 기간 선택 */}
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div>
            <h2 className="text-2xl font-black text-slate-900">{decodedSymbol}</h2>
            {analyzedAt && (
              <p className="text-xs text-slate-400 mt-0.5">
                분석 시각: {new Date(analyzedAt).toLocaleString("ko-KR")}
              </p>
            )}
          </div>
          <PeriodSelector onChange={handlePeriodChange} />
        </div>

        {/* 에러 */}
        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 text-red-700
                          p-4 mb-4 text-sm">
            <strong>오류:</strong> {error}
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
            분석 중...
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* 차트 (2/3) */}
            <div className="lg:col-span-2">
              {ohlcv.length > 0 ? (
                <CandlestickChart ohlcv={ohlcv} patterns={patterns} height={440} />
              ) : (
                <div className="rounded-xl border border-slate-200 bg-white
                                flex items-center justify-center h-[440px] text-slate-400 text-sm">
                  차트 데이터 없음
                </div>
              )}
            </div>

            {/* 패턴 카드 (1/3) */}
            <div className="flex flex-col gap-4">
              {patterns.length > 0 ? (
                patterns.map((p) => <PatternCard key={p.rank} pattern={p} />)
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
