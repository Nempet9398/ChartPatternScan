"""
Rectangle (직사각형 / 박스권) 패턴.

출처: Edwards & Magee (1966) / Bulkowski (2005) 성공률 55%

구조:
  - 상단 저항선 수평 유지
  - 하단 지지선 수평 유지
  - 가격이 두 선 사이에서 반복 등락

상태:
  - forming    : 패턴 형성 중
  - breakout_up : 상방 돌파
  - breakout_down : 하방 이탈

조건:
  [C1] 상단선 기울기 ≈ 0 (수평)                   (25점)
  [C2] 하단선 기울기 ≈ 0 (수평)                   (25점)
  [C3] 최소 터치 횟수 (상단 2회, 하단 2회)         (25점)
  [C4] 돌파 방향 확인                              (25점)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .base import BasePattern, PatternResult
from .config import (
    RECTANGLE_SLOPE_FLAT, RECTANGLE_MIN_TOUCHES,
    BREAKOUT_EPSILON,
)
from .preprocessor import preprocess
from .geometry import build_geometry, make_line, make_level, pos_to_date, trendline_endpoints


class Rectangle(BasePattern):
    name = "Rectangle"
    name_ko = "직사각형"
    signal = "neutral"
    description = "수평 저항선과 지지선 사이의 박스권 횡보 후 방향성 돌파를 기다리는 패턴"
    historical_success_rate = 55.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        peaks   = prep["peaks"]
        troughs = prep["troughs"]
        norm    = prep["normalized"]
        dates   = prep["dates"]

        if len(peaks) < RECTANGLE_MIN_TOUCHES or len(troughs) < RECTANGLE_MIN_TOUCHES:
            return self._zero_result()

        # 상단선: 피크들에 대한 선형회귀
        peak_x = np.array(peaks, dtype=float)
        peak_y = norm.values[peaks]
        if len(peak_x) >= 2:
            upper_slope, upper_intercept, upper_r, _, _ = stats.linregress(peak_x, peak_y)
        else:
            return self._zero_result()

        # 하단선: 트로프들에 대한 선형회귀
        trough_x = np.array(troughs, dtype=float)
        trough_y = norm.values[troughs]
        if len(trough_x) >= 2:
            lower_slope, lower_intercept, lower_r, _, _ = stats.linregress(trough_x, trough_y)
        else:
            return self._zero_result()

        # [C1] 상단선 수평
        c1 = max(0.0, (1.0 - abs(upper_slope) / RECTANGLE_SLOPE_FLAT)) * 25.0
        c1 = min(c1, 25.0)

        # [C2] 하단선 수평
        c2 = max(0.0, (1.0 - abs(lower_slope) / RECTANGLE_SLOPE_FLAT)) * 25.0
        c2 = min(c2, 25.0)

        # [C3] 터치 횟수 점수
        peak_touch_score = min(len(peaks) / (RECTANGLE_MIN_TOUCHES * 2), 1.0)
        trough_touch_score = min(len(troughs) / (RECTANGLE_MIN_TOUCHES * 2), 1.0)
        c3 = (peak_touch_score + trough_touch_score) / 2.0 * 25.0

        # [C4] 돌파 확인
        last_n = norm.values[-5:] if len(norm) >= 5 else norm.values
        upper_level = upper_intercept + upper_slope * (len(norm) - 1)
        lower_level = lower_intercept + lower_slope * (len(norm) - 1)

        breakout_state = "forming"
        c4 = 0.0
        if len(last_n) > 0:
            recent_close = last_n[-1]
            if recent_close > upper_level * (1 + BREAKOUT_EPSILON):
                breakout_state = "breakout_up"
                c4 = 25.0
            elif recent_close < lower_level * (1 - BREAKOUT_EPSILON):
                breakout_state = "breakout_down"
                c4 = 25.0
            else:
                # 박스권 내에 있으면 부분 점수
                box_range = upper_level - lower_level
                if box_range > 0:
                    position = (recent_close - lower_level) / box_range
                    c4 = min(abs(position - 0.5) * 2, 1.0) * 15.0

        similarity = round(c1 + c2 + c3 + c4, 1)

        close    = prep["close"]
        smoothed = prep["smoothed"]
        x_start  = int(min(peaks[0], troughs[0]))
        x_end    = len(norm) - 1
        x1_d, y1_u, x2_d, y2_u = trendline_endpoints(
            x_start, x_end, upper_slope, upper_intercept, dates, close, smoothed)
        _, y1_l, _, y2_l = trendline_endpoints(
            x_start, x_end, lower_slope, lower_intercept, dates, close, smoothed)
        geometry = build_geometry(
            lines=[
                make_line(x1_d, y1_u, x2_d, y2_u, "resistance", "#ef4444", "solid"),
                make_line(x1_d, y1_l, x2_d, y2_l, "support",    "#22c55e", "solid"),
            ],
            levels=[make_level(breakout_state, (y2_u + y2_l) / 2, "#888888")],
        )

        return PatternResult(
            name=self.name, name_ko=self.name_ko,
            similarity=similarity,
            signal=self._get_signal(breakout_state),
            description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[peaks[0]]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[-1]).strftime("%Y-%m-%d"),
            pattern_geometry=geometry if similarity > 0 else None,
        )

    def _get_signal(self, state: str) -> str:
        if state == "breakout_up":
            return "bullish"
        elif state == "breakout_down":
            return "bearish"
        return "neutral"

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
