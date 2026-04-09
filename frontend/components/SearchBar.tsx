"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setHighlightedIndex(-1);
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
      setHighlightedIndex(-1);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchSymbol(query);
        setResults(res.results);
        setOpen(res.results.length > 0);
        setHighlightedIndex(-1);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, [query]);

  // 하이라이트된 항목이 뷰포트에 보이도록 스크롤
  useEffect(() => {
    if (highlightedIndex < 0 || !listRef.current) return;
    const item = listRef.current.children[highlightedIndex] as HTMLElement | undefined;
    item?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex]);

  const handleSelect = useCallback((result: SearchResult) => {
    setQuery(result.symbol);
    setSymbol(result.symbol);
    setOpen(false);
    setHighlightedIndex(-1);
    router.push(`/result/${encodeURIComponent(result.symbol)}`);
  }, [router, setSymbol]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // 하이라이트된 항목이 있으면 해당 항목 선택
    if (open && highlightedIndex >= 0 && results[highlightedIndex]) {
      handleSelect(results[highlightedIndex]);
      return;
    }
    if (!query.trim()) return;
    setSymbol(query.trim().toUpperCase());
    setOpen(false);
    setHighlightedIndex(-1);
    router.push(`/result/${encodeURIComponent(query.trim().toUpperCase())}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || results.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
        break;
      case "Escape":
        e.preventDefault();
        setOpen(false);
        setHighlightedIndex(-1);
        break;
      case "Enter":
        if (highlightedIndex >= 0 && results[highlightedIndex]) {
          e.preventDefault();
          handleSelect(results[highlightedIndex]);
        }
        break;
    }
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
            onKeyDown={handleKeyDown}
            placeholder="종목 검색 (예: AAPL, 삼성전자, BTC-USD)"
            className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 pr-10
                       text-sm shadow-sm outline-none transition
                       focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            autoComplete="off"
            aria-autocomplete="list"
            aria-expanded={open}
            aria-activedescendant={
              highlightedIndex >= 0 ? `search-option-${highlightedIndex}` : undefined
            }
          />
          {loading && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2">
              <svg
                className="animate-spin text-gray-400"
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <circle
                  cx="7"
                  cy="7"
                  r="5.5"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeDasharray="26"
                  strokeDashoffset="10"
                />
              </svg>
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
      <div
        className={`absolute left-0 right-0 top-[calc(100%+6px)] z-50
                    overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg
                    transition-all duration-150 ease-out origin-top
                    ${open ? "opacity-100 scale-y-100 pointer-events-auto" : "opacity-0 scale-y-95 pointer-events-none"}`}
        aria-live="polite"
      >
        <ul ref={listRef} role="listbox">
          {results.map((r, idx) => (
            <li
              key={r.symbol}
              id={`search-option-${idx}`}
              role="option"
              aria-selected={idx === highlightedIndex}
              onClick={() => handleSelect(r)}
              onMouseEnter={() => setHighlightedIndex(idx)}
              className={`flex items-center justify-between px-4 py-2.5 cursor-pointer transition
                         ${idx === highlightedIndex ? "bg-blue-50" : "hover:bg-blue-50"}`}
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
      </div>
    </div>
  );
}
