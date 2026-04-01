"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  createChart,
  ColorType,
  CandlestickSeries,
  LineSeries,
  LineStyle,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from "lightweight-charts";
import type { OHLCVBar, PatternItem } from "@/lib/api";
import type { SelectionRange } from "@/store/chartStore";

export interface PatternGeometry {
  points: { label: string; date: string; value: number }[];
  lines:  { type: string; x1: string; y1: number; x2: string; y2: number; color: string; style: string }[];
  levels: { type: string; value: number; color: string }[];
}

// lightweight-charts Time → ISO 문자열
function timeToIso(t: Time): string {
  if (typeof t === "number") return new Date(t * 1000).toISOString();
  if (typeof t === "string") return t;
  // BusinessDay: { year, month, day }
  return `${t.year}-${String(t.month).padStart(2, "0")}-${String(t.day).padStart(2, "0")}`;
}

// ISO 문자열 → lightweight-charts 가 받아들이는 Time 타입으로 변환
// "2024-01-02"          → "2024-01-02" (그대로)
// "2024-01-02T14:30Z"   → Unix 초 숫자
function isoToTime(iso: string): Time {
  return iso.includes("T")
    ? (Math.floor(new Date(iso).getTime() / 1000) as unknown as Time)
    : (iso as unknown as Time);
}

// 범위 비교용 Unix 초 변환
function timeToSeconds(t: Time | string | number): number {
  if (typeof t === "number") return t;
  if (typeof t === "string") return new Date(t).getTime() / 1000;
  if (typeof t === "object" && "year" in t) {
    return (
      new Date(
        `${t.year}-${String(t.month).padStart(2, "0")}-${String(t.day).padStart(2, "0")}`,
      ).getTime() / 1000
    );
  }
  return 0;
}

export interface RangeSelectEvent {
  startTime: string;
  endTime: string;
  candleCount: number;
}

interface Props {
  ohlcv: OHLCVBar[];
  patterns?: PatternItem[];
  activePatternGeometry?: PatternGeometry | null;
  height?: number;
  onRangeSelect?: (e: RangeSelectEvent) => void;
  selectionRange?: SelectionRange | null;
}

export default function CandlestickChart({
  ohlcv,
  patterns = [],
  activePatternGeometry,
  height = 420,
  onRangeSelect,
  selectionRange,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  // geometry 라인 시리즈 목록 (geometry 변경 시 제거)
  const geoSeriesRef = useRef<ISeriesApi<"Line">[]>([]);

  const [isSelectMode, setIsSelectMode] = useState(false);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const [dragBox, setDragBox] = useState<{ left: number; width: number } | null>(null);

  // ── 차트 생성 ───────────────────────────────────────────────────────────
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

  // ── 데이터 + 패턴 마커 업데이트 ─────────────────────────────────────────
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

    const top1 = patterns[0];
    if (top1?.highlight_start && top1?.highlight_end) {
      const color =
        top1.signal === "bullish" ? "#22c55e" :
        top1.signal === "bearish" ? "#ef4444" :
        "#94a3b8";
      createSeriesMarkers(seriesRef.current, [
        {
          time:     top1.highlight_start as Time,
          position: "aboveBar",
          color,
          shape:    "arrowDown",
          text:     top1.name_ko,
          size:     1,
        },
        {
          time:     top1.highlight_end as Time,
          position: "aboveBar",
          color,
          shape:    "circle",
          size:     1,
        },
      ]);
    }

    chartRef.current.timeScale().fitContent();
  }, [ohlcv, patterns]);

  // ── 패턴 geometry 렌더링 ────────────────────────────────────────────────
  useEffect(() => {
    if (!chartRef.current) return;

    // 기존 geometry 라인 제거
    geoSeriesRef.current.forEach((s) => {
      try { chartRef.current!.removeSeries(s); } catch { /* 이미 제거됨 */ }
    });
    geoSeriesRef.current = [];

    if (!activePatternGeometry || ohlcv.length === 0) return;

    const chart = chartRef.current;
    const newSeries: ISeriesApi<"Line">[] = [];

    // lines: 시작~끝 두 점으로 직선 렌더
    activePatternGeometry.lines.forEach((line) => {
      const s = chart.addSeries(LineSeries, {
        color:      line.color,
        lineWidth:  2,
        lineStyle:  line.style === "dashed" ? LineStyle.Dashed : LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      s.setData([
        { time: line.x1 as Time, value: line.y1 },
        { time: line.x2 as Time, value: line.y2 },
      ]);
      newSeries.push(s);
    });

    // levels: 전체 구간 수평선
    if (activePatternGeometry.levels.length > 0 && ohlcv.length >= 2) {
      const firstTime = ohlcv[0].time as Time;
      const lastTime  = ohlcv[ohlcv.length - 1].time as Time;
      activePatternGeometry.levels.forEach((level) => {
        const s = chart.addSeries(LineSeries, {
          color:     level.color,
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          priceLineVisible:       false,
          lastValueVisible:       false,
          crosshairMarkerVisible: false,
        });
        s.setData([
          { time: firstTime, value: level.value },
          { time: lastTime,  value: level.value },
        ]);
        newSeries.push(s);
      });
    }

    geoSeriesRef.current = newSeries;
  }, [activePatternGeometry, ohlcv]);

  // 모드 전환 시 드래그 상태 초기화
  useEffect(() => {
    if (!isSelectMode) {
      isDragging.current = false;
      setDragBox(null);
    }
  }, [isSelectMode]);

  // ── 드래그 핸들러 ──────────────────────────────────────────────────────
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const rect = containerRef.current!.getBoundingClientRect();
    dragStartX.current = e.clientX - rect.left;
    isDragging.current = true;
    setDragBox({ left: dragStartX.current, width: 0 });
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging.current) return;
    const rect = containerRef.current!.getBoundingClientRect();
    const curX = e.clientX - rect.left;
    setDragBox({
      left:  Math.min(dragStartX.current, curX),
      width: Math.abs(curX - dragStartX.current),
    });
  }, []);

  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging.current || !chartRef.current || !onRangeSelect) return;
      isDragging.current = false;

      const rect = containerRef.current!.getBoundingClientRect();
      const x1 = dragStartX.current;
      const x2 = e.clientX - rect.left;
      setDragBox(null);

      if (Math.abs(x2 - x1) < 5) return; // 너무 짧은 드래그 무시

      const t1 = chartRef.current.timeScale().coordinateToTime(Math.min(x1, x2));
      const t2 = chartRef.current.timeScale().coordinateToTime(Math.max(x1, x2));
      if (!t1 || !t2) return;

      const startIso = timeToIso(t1);
      const endIso   = timeToIso(t2);
      const startSec = timeToSeconds(t1);
      const endSec   = timeToSeconds(t2);

      const count = ohlcv.filter((bar) => {
        const s = timeToSeconds(bar.time as Time);
        return s >= startSec && s <= endSec;
      }).length;

      onRangeSelect({ startTime: startIso, endTime: endIso, candleCount: count });
    },
    [ohlcv, onRangeSelect],
  );

  const handleMouseLeave = useCallback(() => {
    if (isDragging.current) {
      isDragging.current = false;
      setDragBox(null);
    }
  }, []);

  // 선택된 구간의 픽셀 좌표 계산
  const selBox = (() => {
    if (!isSelectMode || !selectionRange || dragBox || !chartRef.current) return null;
    const ts = chartRef.current.timeScale();
    const l  = ts.timeToCoordinate(isoToTime(selectionRange.startTime));
    const r  = ts.timeToCoordinate(isoToTime(selectionRange.endTime));
    if (l === null || r === null) return null;
    return { left: Math.min(l, r), width: Math.abs(r - l) };
  })();

  return (
    <div
      className="relative w-full rounded-xl overflow-hidden border border-gray-200 bg-white"
      style={{ height }}
    >
      {/* 차트 캔버스 */}
      <div ref={containerRef} className="w-full h-full" />

      {/* 이벤트 캡처 오버레이 — 구간 선택 모드일 때만 pointer-events 활성 */}
      <div
        className="absolute inset-0"
        style={{
          zIndex: 10,
          cursor: isSelectMode ? "crosshair" : "default",
          pointerEvents: isSelectMode ? "all" : "none",
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      >
        {/* 드래그 중 선택 박스 */}
        {dragBox && dragBox.width > 2 && (
          <div
            className="absolute top-0 bottom-0 bg-blue-400/20 border-x border-blue-500"
            style={{ left: dragBox.left, width: dragBox.width }}
          />
        )}

        {/* 완료된 선택 구간 */}
        {selBox && (
          <div
            className="absolute top-0 bottom-0 bg-blue-400/10 border-x-2 border-blue-400"
            style={{ left: selBox.left, width: selBox.width }}
          />
        )}
      </div>

      {/* 구간 선택 모드 토글 버튼 */}
      {onRangeSelect && (
        <button
          className={`absolute top-2 right-2 z-20 px-3 py-1 rounded-lg text-xs font-medium shadow-sm transition select-none
            ${isSelectMode
              ? "bg-blue-600 text-white"
              : "bg-white text-slate-600 border border-slate-200 hover:border-blue-400"
            }`}
          onClick={() => setIsSelectMode((m) => !m)}
        >
          {isSelectMode ? "↩ 탐색 모드" : "◻ 구간 선택"}
        </button>
      )}

      {/* 구간 선택 안내 문구 */}
      {isSelectMode && !dragBox && (
        <div
          className="absolute bottom-2 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded text-xs text-slate-500 bg-white/90 pointer-events-none select-none"
          style={{ zIndex: 20 }}
        >
          드래그로 분석할 구간을 선택하세요
        </div>
      )}
    </div>
  );
}
