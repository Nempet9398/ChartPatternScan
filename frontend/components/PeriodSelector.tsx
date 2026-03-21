"use client";

import type { Period } from "@/lib/api";
import { useChartStore } from "@/store/chartStore";

const PERIODS: { value: Period; label: string }[] = [
  { value: "1w",  label: "1주" },
  { value: "1mo", label: "1개월" },
  { value: "3mo", label: "3개월" },
  { value: "6mo", label: "6개월" },
  { value: "1y",  label: "1년" },
];

interface Props {
  onChange?: (period: Period) => void;
}

export default function PeriodSelector({ onChange }: Props) {
  const { period, setPeriod } = useChartStore();

  const handleClick = (p: Period) => {
    setPeriod(p);
    onChange?.(p);
  };

  return (
    <div className="flex gap-1.5">
      {PERIODS.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => handleClick(value)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition
            ${period === value
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
