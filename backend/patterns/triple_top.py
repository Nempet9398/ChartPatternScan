"""
Triple Top (트리플탑) 패턴.

출처: Edwards & Magee (1966) / Bulkowski (2005) 성공률 70%

구조: peak - trough - peak - trough - peak
      세 고점이 비슷한 높이에서 저항받은 뒤 하락 반전

조건:
  [C1] 세 피크 높이 유사 (TRIPLE_TOLERANCE 이내)        (40점)
  [C2] 각 피크 간격 최소 TRIPLE_MIN_DAYS 이상            (20점)
  [C3] 두 트로프 사이 피크가 세 고점보다 낮음             (20점)
  [C4] 마지막 피크 이후 neckline 하향 돌파 시 가점        (20점)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BasePattern, PatternResult
from .config import (
    TRIPLE_TOLERANCE, TRIPLE_MIN_DAYS,
    BREAKOUT_EPSILON,
)
from .preprocessor import preprocess
from .geometry import build_geometry, make_point, make_line, make_level, pos_to_date, pos_to_price


class TripleTop(BasePattern):
    name = "Triple Top"
    name_ko = "트리플탑"
    signal = "bearish"
    description = "세 번의 비슷한 고점 저항 후 하락 반전하는 강한 하락 신호 패턴"
    historical_success_rate = 70.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        peaks   = prep["peaks"]
        troughs = prep["troughs"]
        norm    = prep["normalized"]
        dates   = prep["dates"]

        if len(peaks) < 3 or len(troughs) < 2:
            return self._zero_result()

        best_score = 0.0
        best_p1 = best_p3 = None

        # 연속된 세 피크 조합 탐색
        for i in range(len(peaks) - 2):
            p1, p2, p3 = peaks[i], peaks[i + 1], peaks[i + 2]
            e1 = norm.values[p1]
            e2 = norm.values[p2]
            e3 = norm.values[p3]
            avg_peak = (e1 + e2 + e3) / 3.0

            # [C1] 세 고점 높이 유사
            max_diff = max(abs(e1 - e2), abs(e2 - e3), abs(e1 - e3))
            height_ratio = max_diff / (avg_peak + 1e-10)
            if height_ratio < TRIPLE_TOLERANCE:
                c1 = (1.0 - height_ratio / TRIPLE_TOLERANCE) * 40.0
            else:
                c1 = max(0.0, (1.0 - height_ratio / (TRIPLE_TOLERANCE * 3)) * 20.0)

            # [C2] 각 피크 간격
            gap12 = abs(p2 - p1)
            gap23 = abs(p3 - p2)
            min_gap = min(gap12, gap23)
            c2 = 20.0 if min_gap >= TRIPLE_MIN_DAYS else (min_gap / TRIPLE_MIN_DAYS) * 20.0

            # [C3] 두 트로프 존재 & 피크보다 낮음
            # p1~p2 사이 트로프, p2~p3 사이 트로프 찾기
            t12 = [t for t in troughs if p1 < t < p2]
            t23 = [t for t in troughs if p2 < t < p3]
            if t12 and t23:
                trough12 = min(norm.values[t12], key=lambda _: norm.values[t12].min()
                               if hasattr(norm.values[t12], 'min') else _)
                trough12_val = norm.values[t12].min() if len(t12) > 0 else avg_peak
                trough23_val = norm.values[t23].min() if len(t23) > 0 else avg_peak
                neckline = (trough12_val + trough23_val) / 2.0
                c3 = 20.0 if neckline < avg_peak * 0.98 else 10.0
            else:
                c3 = 0.0

            # [C4] 마지막 피크 이후 neckline 하향 돌파
            c4 = 0.0
            if t12 and t23:
                neckline_val = (norm.values[t12].min() + norm.values[t23].min()) / 2.0
                after_p3 = norm.values[p3:]
                if len(after_p3) >= 3:
                    recent_low = after_p3.min()
                    if recent_low < neckline_val * (1 - BREAKOUT_EPSILON):
                        c4 = 20.0
                    else:
                        c4 = max(0.0, (neckline_val - recent_low) / (neckline_val + 1e-10)) * 20.0

            score = c1 + c2 + c3 + c4
            if score > best_score:
                best_score = score
                best_p1 = p1
                best_p3 = p3

        if best_p1 is None:
            return self._zero_result()

        close = prep["close"]
        best_i = next(
            i for i in range(len(peaks) - 2)
            if peaks[i] == best_p1
        )
        p1, p2, p3 = peaks[best_i], peaks[best_i + 1], peaks[best_i + 2]
        t12 = [t for t in troughs if p1 < t < p2]
        t23 = [t for t in troughs if p2 < t < p3]
        neckline_price = None
        geo_points = [
            make_point("peak1", pos_to_date(p1, dates), pos_to_price(p1, dates, close)),
            make_point("peak2", pos_to_date(p2, dates), pos_to_price(p2, dates, close)),
            make_point("peak3", pos_to_date(p3, dates), pos_to_price(p3, dates, close)),
        ]
        if t12:
            t12_pos = min(t12, key=lambda t: norm.values[t])
            geo_points.append(make_point("trough1", pos_to_date(t12_pos, dates), pos_to_price(t12_pos, dates, close)))
        if t23:
            t23_pos = min(t23, key=lambda t: norm.values[t])
            geo_points.append(make_point("trough2", pos_to_date(t23_pos, dates), pos_to_price(t23_pos, dates, close)))
        if t12 and t23:
            neckline_price = (pos_to_price(min(t12, key=lambda t: norm.values[t]), dates, close) +
                              pos_to_price(min(t23, key=lambda t: norm.values[t]), dates, close)) / 2.0

        geometry = build_geometry(
            points=geo_points,
            levels=[make_level("neckline", neckline_price, "#888888")] if neckline_price else [],
        )

        return PatternResult(
            name=self.name, name_ko=self.name_ko,
            similarity=round(best_score, 1),
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[best_p1]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[best_p3]).strftime("%Y-%m-%d"),
            pattern_geometry=geometry,
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
