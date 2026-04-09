"use client";

import { useState, useEffect } from "react";
import type { PatternItem } from "@/lib/api";

interface Props {
  pattern: PatternItem;
  isSelected?: boolean;
  onClick?: () => void;
  animationDelay?: number;
}

// CLAUDE.md 기준: 70+ 초록, 40+ 노랑, 미만 회색
function getBarColor(score: number): string {
  if (score >= 70) return "bg-green-500";
  if (score >= 40) return "bg-yellow-400";
  return "bg-gray-400";
}

const SIGNAL_BADGE: Record<string, { label: string; className: string }> = {
  bullish: { label: "상승",  className: "bg-green-100 text-green-700 border border-green-200" },
  bearish: { label: "하락",  className: "bg-red-100 text-red-700 border border-red-200" },
  neutral: { label: "중립",  className: "bg-gray-100 text-gray-600 border border-gray-200" },
};

const RANK_COLORS = ["text-yellow-500", "text-gray-400", "text-amber-700"];

export default function PatternCard({ pattern, isSelected = false, onClick, animationDelay = 0 }: Props) {
  const badge = SIGNAL_BADGE[pattern.signal] ?? SIGNAL_BADGE["neutral"];
  const barColor = getBarColor(pattern.similarity);
  const rankColor = RANK_COLORS[(pattern.rank - 1)] ?? "text-gray-400";

  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), animationDelay);
    return () => clearTimeout(timer);
  }, [animationDelay]);

  return (
    <div
      className={`rounded-2xl border bg-white p-5 shadow-sm cursor-pointer
        transition-all duration-500
        ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"}
        ${isSelected
          ? "border-blue-400 ring-2 ring-blue-200 shadow-md"
          : "border-gray-200 hover:shadow-md hover:border-blue-200"
        }`}
      onClick={onClick}
    >
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`text-2xl font-black ${rankColor}`}>#{pattern.rank}</span>
          <div>
            <p className="font-bold text-gray-900 text-base leading-tight">{pattern.name_ko}</p>
            <p className="text-xs text-gray-400 mt-0.5">{pattern.name}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${badge.className}`}>
            {badge.label}
          </span>
          {isSelected && (
            <span className="flex items-center gap-1 text-xs font-medium text-blue-600
                             bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24"
                   stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round"
                      d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
              </svg>
              차트 표시 중
            </span>
          )}
        </div>
      </div>

      {/* 유사도 바 */}
      <div className="mt-4">
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-xs text-gray-500 font-medium">유사도</span>
          <span className={`text-lg font-black ${
            pattern.similarity >= 70 ? "text-green-600"
            : pattern.similarity >= 40 ? "text-yellow-500"
            : "text-gray-400"
          }`}>
            {pattern.similarity.toFixed(1)}%
          </span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-gray-100 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${barColor}`}
            style={{ width: `${Math.min(pattern.similarity, 100)}%` }}
          />
        </div>
      </div>

      {/* 설명 */}
      <p className="mt-3 text-sm text-gray-600 leading-relaxed">{pattern.description}</p>

      {/* 메타 */}
      <div className="mt-3 flex items-center gap-1.5 text-xs text-gray-400">
        <span>역사적 성공률</span>
        <span className="font-semibold text-gray-700">{pattern.historical_success_rate}%</span>
        <span>·</span>
        <span>{pattern.source}</span>
      </div>

      {/* 하이라이트 기간 */}
      {pattern.highlight_start && pattern.highlight_end && (
        <div className="mt-2 text-xs text-blue-500 font-medium">
          탐지 구간: {pattern.highlight_start} ~ {pattern.highlight_end}
        </div>
      )}
    </div>
  );
}
