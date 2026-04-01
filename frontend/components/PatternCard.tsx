import type { PatternItem } from "@/lib/api";

interface Props {
  pattern: PatternItem;
  isSelected?: boolean;
  onClick?: () => void;
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

export default function PatternCard({ pattern, isSelected = false, onClick }: Props) {
  const badge = SIGNAL_BADGE[pattern.signal] ?? SIGNAL_BADGE["neutral"];
  const barColor = getBarColor(pattern.similarity);
  const rankColor = RANK_COLORS[(pattern.rank - 1)] ?? "text-gray-400";

  return (
    <div
      className={`rounded-2xl border bg-white p-5 shadow-sm transition-all cursor-pointer
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
        <span className={`shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${badge.className}`}>
          {badge.label}
        </span>
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
