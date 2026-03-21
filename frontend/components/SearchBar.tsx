"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { searchSymbol } from "@/lib/api";
import type { SearchResult } from "@/lib/api";
import { useChartStore } from "@/store/chartStore";

export default function SearchBar() {
  const router = useRouter();
  const { symbol, setSymbol } = useChartStore();

  const [query, setQuery] = useState(symbol);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // 디바운스 검색
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 1) {
      setResults([]);
      setOpen(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchSymbol(query);
        setResults(res.results);
        setOpen(res.results.length > 0);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, [query]);

  const handleSelect = (result: SearchResult) => {
    setQuery(result.symbol);
    setSymbol(result.symbol);
    setOpen(false);
    router.push(`/result/${encodeURIComponent(result.symbol)}`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSymbol(query.trim().toUpperCase());
    setOpen(false);
    router.push(`/result/${encodeURIComponent(query.trim().toUpperCase())}`);
  };

  const marketBadgeColor: Record<string, string> = {
    NASDAQ: "bg-blue-100 text-blue-700",
    NYSE:   "bg-purple-100 text-purple-700",
    KOSPI:  "bg-green-100 text-green-700",
    KOSDAQ: "bg-teal-100 text-teal-700",
    Crypto: "bg-orange-100 text-orange-700",
    ETF:    "bg-gray-100 text-gray-600",
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-xl">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => results.length > 0 && setOpen(true)}
            placeholder="종목 검색 (예: AAPL, 삼성전자, BTC-USD)"
            className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 pr-10
                       text-sm shadow-sm outline-none transition
                       focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            autoComplete="off"
          />
          {loading && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs animate-pulse">
              ...
            </span>
          )}
        </div>
        <button
          type="submit"
          className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white
                     shadow-sm transition hover:bg-blue-700 active:scale-95"
        >
          분석
        </button>
      </form>

      {/* 드롭다운 */}
      {open && (
        <ul className="absolute left-0 right-0 top-[calc(100%+6px)] z-50
                       rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden">
          {results.map((r) => (
            <li
              key={r.symbol}
              onClick={() => handleSelect(r)}
              className="flex items-center justify-between px-4 py-2.5 cursor-pointer
                         hover:bg-blue-50 transition"
            >
              <div>
                <span className="font-semibold text-sm text-gray-800">{r.symbol}</span>
                <span className="ml-2 text-sm text-gray-500">{r.name}</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                               ${marketBadgeColor[r.market] ?? "bg-gray-100 text-gray-500"}`}>
                {r.market}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
