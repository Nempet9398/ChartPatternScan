"""
Double Top (더블탑) 패턴.

출처: Lo, Mamaysky & Wang (2000) Definition 4
      Bulkowski (2005) 성공률 65%

극값: E1(피크) ... Ea(피크)  — 가장 큰 두 피크 선택

Lo(2000) 필수 조건:
  [C1] |E1-Ea| / avg(E1,Ea) < DOUBLE_TOLERANCE   두 고점 1.5% 이내  (50점)
  [C2] |index(Ea)-index(E1)| >= DOUBLE_MIN_DAYS   최소 22 거래일 간격 (20점)
  [C3] (avg_peak - trough_between) / avg_peak > 0.05  중간 하락 5% 이상 (30점)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BasePattern, PatternResult
from .config import DOUBLE_TOLERANCE, DOUBLE_MIN_DAYS
from .preprocessor import preprocess
from .geometry import build_geometry, make_point, make_line, make_level, pos_to_date, pos_to_price


class DoubleTop(BasePattern):
    name = "Double Top"
    name_ko = "더블탑"
    signal = "bearish"
    description = "비슷한 높이의 두 고점이 형성된 후 하락 반전하는 패턴 (M자형)"
    historical_success_rate = 65.0
    source = "Lo, Mamaysky & Wang (2000) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        peaks     = prep["peaks"]
        norm      = prep["normalized"]
        smoothed  = prep["smoothed"]
        dates     = prep["dates"]

        if len(peaks) < 2:
            return self._zero_result()

        # 가장 높은 두 피크 선택
        peak_vals = norm.values[peaks]
        top2_idx  = np.argsort(peak_vals)[-2:]          # 상위 2개 정수 인덱스 (peaks 배열 기준)
        top2_idx  = sorted(top2_idx, key=lambda i: peaks[i])  # 시간순 정렬
        i1, i2    = top2_idx[0], top2_idx[1]

        p1_pos, p2_pos = peaks[i1], peaks[i2]   # smoothed 배열 상의 위치
        e1 = norm.values[p1_pos]
        ea = norm.values[p2_pos]
        avg_peak = (e1 + ea) / 2.0

        # [C1] 두 고점 높이 차이 <= 1.5%
        height_diff = abs(e1 - ea) / (avg_peak + 1e-10)
        if height_diff < DOUBLE_TOLERANCE:
            c1_score = (1.0 - height_diff / DOUBLE_TOLERANCE) * 50.0
        else:
            c1_score = 0.0

        # [C2] 최소 22 거래일 간격
        day_gap = abs(p2_pos - p1_pos)
        c2_score = 20.0 if day_gap >= DOUBLE_MIN_DAYS else (day_gap / DOUBLE_MIN_DAYS) * 20.0

        # [C3] 두 피크 사이의 최저점 하락 5% 이상
        between = norm.values[p1_pos:p2_pos + 1]
        trough_val = between.min() if len(between) > 0 else avg_peak
        drop_ratio = (avg_peak - trough_val) / (avg_peak + 1e-10)
        if drop_ratio >= 0.05:
            c3_score = min(drop_ratio / 0.15, 1.0) * 30.0
        else:
            c3_score = (drop_ratio / 0.05) * 30.0 * 0.5  # 조건 미달시 절반 점수

        similarity = round(c1_score + c2_score + c3_score, 1)

        close = prep["close"]
        highlight_start = pd.Timestamp(dates[p1_pos]).strftime("%Y-%m-%d")
        highlight_end   = pd.Timestamp(dates[p2_pos]).strftime("%Y-%m-%d")

        peak1_price  = pos_to_price(p1_pos, dates, close)
        peak2_price  = pos_to_price(p2_pos, dates, close)
        trough_price = float(close.loc[dates[p1_pos]:dates[p2_pos]].min())
        geometry = build_geometry(
            points=[
                make_point("peak1",  pos_to_date(p1_pos, dates), peak1_price),
                make_point("peak2",  pos_to_date(p2_pos, dates), peak2_price),
            ],
            lines=[
                make_line(
                    pos_to_date(p1_pos, dates), peak1_price,
                    pos_to_date(p2_pos, dates), peak2_price,
                    "resistance", "#ef4444", "dashed",
                ),
            ],
            levels=[make_level("neckline", trough_price, "#888888")],
        )

        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=highlight_start, highlight_end=highlight_end,
            pattern_geometry=geometry if similarity > 0 else None,
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
