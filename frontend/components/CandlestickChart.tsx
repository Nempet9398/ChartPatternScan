"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CandlestickSeries,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from "lightweight-charts";
import type { OHLCVBar, PatternItem } from "@/lib/api";

interface Props {
  ohlcv: OHLCVBar[];
  patterns?: PatternItem[];
  height?: number;
}

export default function CandlestickChart({ ohlcv, patterns = [], height = 420 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  // 차트 생성 (lightweight-charts v5: addSeries(CandlestickSeries))
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#374151",
        fontFamily: "'Inter', sans-serif",
      },
      grid: {
        vertLines: { color: "#f3f4f6" },
        horzLines: { color: "#f3f4f6" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#e5e7eb" },
      timeScale: {
        borderColor: "#e5e7eb",
        timeVisible: true,
        secondsVisible: false,
      },
      width: containerRef.current.clientWidth,
      height,
    });

    // v5 API: addSeries 사용
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor:         "#22c55e",
      downColor:       "#ef4444",
      borderUpColor:   "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor:     "#22c55e",
      wickDownColor:   "#ef4444",
    });

    chartRef.current  = chart;
    seriesRef.current = candleSeries;

    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current  = null;
      seriesRef.current = null;
    };
  }, [height]);

  // 데이터 + 마커 업데이트
  useEffect(() => {
    if (!seriesRef.current || !chartRef.current || ohlcv.length === 0) return;

    const data: CandlestickData<Time>[] = ohlcv.map((bar) => ({
      time:  bar.time as Time,
      open:  bar.open,
      high:  bar.high,
      low:   bar.low,
      close: bar.close,
    }));

    seriesRef.current.setData(data);

    // Top1 패턴 하이라이트 (v5: createSeriesMarkers)
    const top1 = patterns[0];
    if (top1?.highlight_start && top1?.highlight_end) {
      const color = top1.signal === "bullish" ? "#22c55e"
                  : top1.signal === "bearish" ? "#ef4444"
                  : "#94a3b8";
      createSeriesMarkers(seriesRef.current, [
        {
          time: top1.highlight_start as Time,
          position: "aboveBar",
          color,
          shape: "arrowDown",
          text: top1.name_ko,
          size: 1,
        },
        {
          time: top1.highlight_end as Time,
          position: "aboveBar",
          color,
          shape: "circle",
          size: 1,
        },
      ]);
    }

    chartRef.current.timeScale().fitContent();
  }, [ohlcv, patterns]);

  return (
    <div
      ref={containerRef}
      className="w-full rounded-xl overflow-hidden border border-gray-200 bg-white"
      style={{ height }}
    />
  );
}
