"""
Triple Bottom (트리플바텀) 패턴.

출처: Edwards & Magee (1966) / Bulkowski (2005) 성공률 77%

구조: trough - peak - trough - peak - trough
      세 저점이 비슷한 깊이에서 지지받은 뒤 상승 반전

조건:
  [C1] 세 트로프 깊이 유사 (TRIPLE_TOLERANCE 이내)       (40점)
  [C2] 각 트로프 간격 최소 TRIPLE_MIN_DAYS 이상           (20점)
  [C3] 두 피크 사이 트로프가 세 저점보다 높음              (20점)
  [C4] 마지막 트로프 이후 neckline 상향 돌파 시 가점       (20점)
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
from .geometry import build_geometry, make_point, make_level, pos_to_date, pos_to_price


class TripleBottom(BasePattern):
    name = "Triple Bottom"
    name_ko = "트리플바텀"
    signal = "bullish"
    description = "세 번의 비슷한 저점 지지 후 상승 반전하는 강한 상승 신호 패턴"
    historical_success_rate = 77.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        peaks   = prep["peaks"]
        troughs = prep["troughs"]
        norm    = prep["normalized"]
        dates   = prep["dates"]

        if len(troughs) < 3 or len(peaks) < 2:
            return self._zero_result()

        best_score = 0.0
        best_t1 = best_t3 = None

        # 연속된 세 트로프 조합 탐색
        for i in range(len(troughs) - 2):
            t1, t2, t3 = troughs[i], troughs[i + 1], troughs[i + 2]
            e1 = norm.values[t1]
            e2 = norm.values[t2]
            e3 = norm.values[t3]
            avg_trough = (e1 + e2 + e3) / 3.0

            # [C1] 세 저점 깊이 유사
            max_diff = max(abs(e1 - e2), abs(e2 - e3), abs(e1 - e3))
            depth_ratio = max_diff / (avg_trough + 1e-10)
            if depth_ratio < TRIPLE_TOLERANCE:
                c1 = (1.0 - depth_ratio / TRIPLE_TOLERANCE) * 40.0
            else:
                c1 = max(0.0, (1.0 - depth_ratio / (TRIPLE_TOLERANCE * 3)) * 20.0)

            # [C2] 각 트로프 간격
            gap12 = abs(t2 - t1)
            gap23 = abs(t3 - t2)
            min_gap = min(gap12, gap23)
            c2 = 20.0 if min_gap >= TRIPLE_MIN_DAYS else (min_gap / TRIPLE_MIN_DAYS) * 20.0

            # [C3] 두 피크 존재 & 트로프보다 높음
            p12 = [p for p in peaks if t1 < p < t2]
            p23 = [p for p in peaks if t2 < p < t3]
            if p12 and p23:
                peak12_val = norm.values[p12].max() if len(p12) > 0 else avg_trough
                peak23_val = norm.values[p23].max() if len(p23) > 0 else avg_trough
                neckline = (peak12_val + peak23_val) / 2.0
                c3 = 20.0 if neckline > avg_trough * 1.02 else 10.0
            else:
                c3 = 0.0

            # [C4] 마지막 트로프 이후 neckline 상향 돌파
            c4 = 0.0
            if p12 and p23:
                neckline_val = (norm.values[p12].max() + norm.values[p23].max()) / 2.0
                after_t3 = norm.values[t3:]
                if len(after_t3) >= 3:
                    recent_high = after_t3.max()
                    if recent_high > neckline_val * (1 + BREAKOUT_EPSILON):
                        c4 = 20.0
                    else:
                        c4 = max(0.0, (recent_high - neckline_val) / (neckline_val + 1e-10)) * 20.0

            score = c1 + c2 + c3 + c4
            if score > best_score:
                best_score = score
                best_t1 = t1
                best_t3 = t3

        if best_t1 is None:
            return self._zero_result()

        close = prep["close"]
        best_i = next(i for i in range(len(troughs) - 2) if troughs[i] == best_t1)
        t1, t2, t3 = troughs[best_i], troughs[best_i + 1], troughs[best_i + 2]
        p12 = [p for p in peaks if t1 < p < t2]
        p23 = [p for p in peaks if t2 < p < t3]
        neckline_price = None
        geo_points = [
            make_point("trough1", pos_to_date(t1, dates), pos_to_price(t1, dates, close)),
            make_point("trough2", pos_to_date(t2, dates), pos_to_price(t2, dates, close)),
            make_point("trough3", pos_to_date(t3, dates), pos_to_price(t3, dates, close)),
        ]
        if p12:
            p12_pos = max(p12, key=lambda p: norm.values[p])
            geo_points.append(make_point("peak1", pos_to_date(p12_pos, dates), pos_to_price(p12_pos, dates, close)))
        if p23:
            p23_pos = max(p23, key=lambda p: norm.values[p])
            geo_points.append(make_point("peak2", pos_to_date(p23_pos, dates), pos_to_price(p23_pos, dates, close)))
        if p12 and p23:
            neckline_price = (pos_to_price(max(p12, key=lambda p: norm.values[p]), dates, close) +
                              pos_to_price(max(p23, key=lambda p: norm.values[p]), dates, close)) / 2.0

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
            highlight_start=pd.Timestamp(dates[best_t1]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[best_t3]).strftime("%Y-%m-%d"),
            pattern_geometry=geometry,
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
