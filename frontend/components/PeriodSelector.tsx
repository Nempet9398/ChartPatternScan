"use client";

import type { Timeframe } from "@/lib/api";
import { useChartStore } from "@/store/chartStore";

const TIMEFRAMES: { value: Timeframe; label: string }[] = [
  { value: "15m", label: "15분" },
  { value: "30m", label: "30분" },
  { value: "1h",  label: "1시간" },
  { value: "6h",  label: "6시간" },
  { value: "12h", label: "12시간" },
  { value: "1D",  label: "일봉" },
  { value: "1W",  label: "주봉" },
];

interface Props {
  onChange?: (timeframe: Timeframe) => void;
}

export default function PeriodSelector({ onChange }: Props) {
  const { timeframe, setTimeframe } = useChartStore();

  const handleClick = (t: Timeframe) => {
    setTimeframe(t);
    onChange?.(t);
  };

  return (
    <div className="flex gap-1.5 flex-wrap">
      {TIMEFRAMES.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => handleClick(value)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition
            ${timeframe === value
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
