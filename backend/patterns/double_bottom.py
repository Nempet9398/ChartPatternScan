"""
Double Bottom (더블바텀) 패턴 — 더블탑의 상하 반전.

출처: Lo, Mamaysky & Wang (2000) Definition 5
      Bulkowski (2005) 성공률 71%

극값: E1(트로프) ... Ea(트로프)

Lo(2000) 필수 조건:
  [C1] |E1-Ea| / avg < DOUBLE_TOLERANCE             두 저점 1.5% 이내  (50점)
  [C2] |index(Ea)-index(E1)| >= DOUBLE_MIN_DAYS     최소 22 거래일 간격 (20점)
  [C3] (peak_between - avg_trough) / avg_trough > 0.05  중간 반등 5% 이상 (30점)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BasePattern, PatternResult
from .config import DOUBLE_TOLERANCE, DOUBLE_MIN_DAYS
from .preprocessor import preprocess


class DoubleBottom(BasePattern):
    name = "Double Bottom"
    name_ko = "더블바텀"
    signal = "bullish"
    description = "비슷한 깊이의 두 저점이 형성된 후 상승 반전하는 패턴 (W자형)"
    historical_success_rate = 71.0
    source = "Lo, Mamaysky & Wang (2000) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        troughs  = prep["troughs"]
        norm     = prep["normalized"]
        dates    = prep["dates"]

        if len(troughs) < 2:
            return self._zero_result()

        # 가장 낮은 두 트로프 선택
        trough_vals = norm.values[troughs]
        bot2_idx    = np.argsort(trough_vals)[:2]               # 하위 2개
        bot2_idx    = sorted(bot2_idx, key=lambda i: troughs[i])  # 시간순
        i1, i2      = bot2_idx[0], bot2_idx[1]

        t1_pos, t2_pos = troughs[i1], troughs[i2]
        e1 = norm.values[t1_pos]
        ea = norm.values[t2_pos]
        avg_trough = (e1 + ea) / 2.0

        # [C1] 두 저점 깊이 차이 <= 1.5%
        depth_diff = abs(e1 - ea) / (avg_trough + 1e-10)
        if depth_diff < DOUBLE_TOLERANCE:
            c1_score = (1.0 - depth_diff / DOUBLE_TOLERANCE) * 50.0
        else:
            c1_score = 0.0

        # [C2] 최소 22 거래일 간격
        day_gap  = abs(t2_pos - t1_pos)
        c2_score = 20.0 if day_gap >= DOUBLE_MIN_DAYS else (day_gap / DOUBLE_MIN_DAYS) * 20.0

        # [C3] 두 트로프 사이 최고점 반등 5% 이상
        between   = norm.values[t1_pos:t2_pos + 1]
        peak_val  = between.max() if len(between) > 0 else avg_trough
        rise_ratio = (peak_val - avg_trough) / (avg_trough + 1e-10)
        if rise_ratio >= 0.05:
            c3_score = min(rise_ratio / 0.15, 1.0) * 30.0
        else:
            c3_score = (rise_ratio / 0.05) * 30.0 * 0.5

        similarity = round(c1_score + c2_score + c3_score, 1)

        highlight_start = pd.Timestamp(dates[t1_pos]).strftime("%Y-%m-%d")
        highlight_end   = pd.Timestamp(dates[t2_pos]).strftime("%Y-%m-%d")

        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=highlight_start, highlight_end=highlight_end,
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
