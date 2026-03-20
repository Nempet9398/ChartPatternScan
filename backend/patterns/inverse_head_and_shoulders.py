"""
Inverse Head and Shoulders (역헤드앤숄더) 패턴 — 헤드앤숄더 상하 반전.

출처: Lo, Mamaysky & Wang (2000) Definition 2
      Bulkowski (2005) 성공률 89%

극값 시퀀스: E1(트로프) E2(피크) E3(트로프) E4(피크) E5(트로프)

Lo(2000) 필수 조건:
  [C1] E3 < E1 AND E3 < E5            머리가 양 어깨보다 낮음   (40점)
  [C2] |E1-E5| / |E3| < SHOULDER_TOLERANCE  어깨 깊이 대칭     (30점)
  [C3] |E2-E4| / |E3| < NECKLINE_TOLERANCE  넥라인 수평        (30점)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BasePattern, PatternResult
from .config import SHOULDER_TOLERANCE, NECKLINE_TOLERANCE
from .preprocessor import preprocess


class InverseHeadAndShoulders(BasePattern):
    name = "Inverse Head and Shoulders"
    name_ko = "역헤드앤숄더"
    signal = "bullish"
    description = "세 저점 중 가운데(머리)가 가장 낮은 상승 반전 패턴"
    historical_success_rate = 89.0
    source = "Lo, Mamaysky & Wang (2000) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep    = preprocess(df)
        peaks   = prep["peaks"]
        troughs = prep["troughs"]
        norm    = prep["normalized"]
        dates   = prep["dates"]

        best = self._find_best(peaks, troughs, norm)
        if best is None:
            return self._zero_result()

        e1, e2, e3, e4, e5, positions = best
        c1_score = 40.0 if (e3 < e1 and e3 < e5) else 0.0

        shoulder_diff = abs(e1 - e5) / (abs(e3) + 1e-10)
        c2_score = max(0.0, (1.0 - shoulder_diff / SHOULDER_TOLERANCE)) * 30.0

        neckline_diff = abs(e2 - e4) / (abs(e3) + 1e-10)
        c3_score = max(0.0, (1.0 - neckline_diff / NECKLINE_TOLERANCE)) * 30.0

        similarity = round(c1_score + c2_score + c3_score, 1)

        t1_pos, _, _, _, t5_pos = positions
        highlight_start = pd.Timestamp(dates[t1_pos]).strftime("%Y-%m-%d")
        highlight_end   = pd.Timestamp(dates[t5_pos]).strftime("%Y-%m-%d")

        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=highlight_start, highlight_end=highlight_end,
        )

    def _find_best(self, peaks, troughs, norm):
        """연속된 트로프 3개 + 그 사이 피크 2개에서 최적 역H&S 후보 탐색."""
        if len(troughs) < 3 or len(peaks) < 2:
            return None

        best_score = -1.0
        best = None

        for i in range(len(troughs) - 2):
            t1_pos = troughs[i]
            t3_pos = troughs[i + 1]
            t5_pos = troughs[i + 2]

            p2_candidates = [p for p in peaks if t1_pos < p < t3_pos]
            p4_candidates = [p for p in peaks if t3_pos < p < t5_pos]

            if not p2_candidates or not p4_candidates:
                continue

            p2_pos = max(p2_candidates, key=lambda p: norm.values[p])
            p4_pos = max(p4_candidates, key=lambda p: norm.values[p])

            e1 = norm.values[t1_pos]
            e2 = norm.values[p2_pos]
            e3 = norm.values[t3_pos]
            e4 = norm.values[p4_pos]
            e5 = norm.values[t5_pos]

            c1 = 1.0 if (e3 < e1 and e3 < e5) else 0.0
            sd = abs(e1 - e5) / (abs(e3) + 1e-10)
            nd = abs(e2 - e4) / (abs(e3) + 1e-10)
            score = (c1 * 0.4
                     + max(0, 1 - sd / SHOULDER_TOLERANCE) * 0.3
                     + max(0, 1 - nd / NECKLINE_TOLERANCE) * 0.3)

            if score > best_score:
                best_score = score
                best = (e1, e2, e3, e4, e5, (t1_pos, p2_pos, t3_pos, p4_pos, t5_pos))

        return best

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
