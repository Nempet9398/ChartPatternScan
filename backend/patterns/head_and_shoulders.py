"""
Head and Shoulders (헤드앤숄더) 패턴.

출처: Lo, Mamaysky & Wang (2000) Definition 1
      Bulkowski (2005) 성공률 81%

극값 시퀀스: E1(피크) E2(트로프) E3(피크) E4(트로프) E5(피크)

Lo(2000) 필수 조건:
  [C1] E3 > E1 AND E3 > E5            머리가 양 어깨보다 높음   (40점)
  [C2] |E1-E5| / E3 < SHOULDER_TOLERANCE  어깨 높이 대칭       (30점)
  [C3] |E2-E4| / E3 < NECKLINE_TOLERANCE  넥라인 수평          (30점)

유사도 = C1충족*0.40 + (1 - |E1-E5|/E3/0.15)*0.30 + (1 - |E2-E4|/E3/0.15)*0.30
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BasePattern, PatternResult
from .config import SHOULDER_TOLERANCE, NECKLINE_TOLERANCE
from .preprocessor import preprocess
from .geometry import (
    build_geometry, make_point, make_line, make_level,
    pos_to_date, pos_to_price,
)


class HeadAndShoulders(BasePattern):
    name = "Head and Shoulders"
    name_ko = "헤드앤숄더"
    signal = "bearish"
    description = "세 고점 중 가운데(머리)가 가장 높은 하락 반전 패턴"
    historical_success_rate = 81.0
    source = "Lo, Mamaysky & Wang (2000) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep   = preprocess(df)
        peaks   = prep["peaks"]
        troughs = prep["troughs"]
        norm    = prep["normalized"]
        dates   = prep["dates"]

        best = self._find_best(peaks, troughs, norm)
        if best is None:
            return self._zero_result()

        e1, e2, e3, e4, e5, positions = best
        c1_score = 40.0 if (e3 > e1 and e3 > e5) else 0.0

        shoulder_diff = abs(e1 - e5) / (e3 + 1e-10)
        c2_score = max(0.0, (1.0 - shoulder_diff / SHOULDER_TOLERANCE)) * 30.0

        neckline_diff = abs(e2 - e4) / (e3 + 1e-10)
        c3_score = max(0.0, (1.0 - neckline_diff / NECKLINE_TOLERANCE)) * 30.0

        similarity = round(c1_score + c2_score + c3_score, 1)

        p1_pos, t2_pos, p3_pos, t4_pos, p5_pos = positions
        close    = prep["close"]
        smoothed = prep["smoothed"]
        highlight_start = pd.Timestamp(dates[p1_pos]).strftime("%Y-%m-%d")
        highlight_end   = pd.Timestamp(dates[p5_pos]).strftime("%Y-%m-%d")

        # ── geometry ─────────────────────────────────────────────────────────
        neckline_y1 = pos_to_price(t2_pos, dates, close)
        neckline_y2 = pos_to_price(t4_pos, dates, close)
        geometry = build_geometry(
            points=[
                make_point("left_shoulder",  pos_to_date(p1_pos, dates), pos_to_price(p1_pos, dates, close)),
                make_point("left_trough",    pos_to_date(t2_pos, dates), neckline_y1),
                make_point("head",           pos_to_date(p3_pos, dates), pos_to_price(p3_pos, dates, close)),
                make_point("right_trough",   pos_to_date(t4_pos, dates), neckline_y2),
                make_point("right_shoulder", pos_to_date(p5_pos, dates), pos_to_price(p5_pos, dates, close)),
            ],
            lines=[
                make_line(
                    pos_to_date(t2_pos, dates), neckline_y1,
                    pos_to_date(t4_pos, dates), neckline_y2,
                    "neckline", "#888888", "dashed",
                ),
            ],
        )

        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=highlight_start, highlight_end=highlight_end,
            pattern_geometry=geometry if similarity > 0 else None,
        )

    def _find_best(self, peaks, troughs, norm):
        """
        교대하는 피크-트로프 시퀀스에서 가장 점수 높은 H&S 후보 탐색.
        반환: (e1, e2, e3, e4, e5, (p1_pos, t2_pos, p3_pos, t4_pos, p5_pos)) 또는 None
        """
        if len(peaks) < 3 or len(troughs) < 2:
            return None

        best_score = -1.0
        best = None

        # 연속된 피크 3개 + 그 사이 트로프 2개를 모두 시도
        for i in range(len(peaks) - 2):
            p1_pos = peaks[i]
            p3_pos = peaks[i + 1]
            p5_pos = peaks[i + 2]

            # p1 < p3 사이에 있는 트로프 중 최솟값
            t2_candidates = [t for t in troughs if p1_pos < t < p3_pos]
            t4_candidates = [t for t in troughs if p3_pos < t < p5_pos]

            if not t2_candidates or not t4_candidates:
                continue

            t2_pos = min(t2_candidates, key=lambda t: norm.values[t])
            t4_pos = min(t4_candidates, key=lambda t: norm.values[t])

            e1 = norm.values[p1_pos]
            e2 = norm.values[t2_pos]
            e3 = norm.values[p3_pos]
            e4 = norm.values[t4_pos]
            e5 = norm.values[p5_pos]

            c1 = 1.0 if (e3 > e1 and e3 > e5) else 0.0
            sd = abs(e1 - e5) / (e3 + 1e-10)
            nd = abs(e2 - e4) / (e3 + 1e-10)
            score = c1 * 0.4 + max(0, 1 - sd / SHOULDER_TOLERANCE) * 0.3 + max(0, 1 - nd / NECKLINE_TOLERANCE) * 0.3

            if score > best_score:
                best_score = score
                best = (e1, e2, e3, e4, e5, (p1_pos, t2_pos, p3_pos, t4_pos, p5_pos))

        return best

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
