"""
Triangle 패턴 (삼각수렴) — 대칭/상승/하락 삼각형 통합 구현.

출처: Lo, Mamaysky & Wang (2000) Definition 3
      Bulkowski (2005)

극값 시퀀스: E1(피크) E2(트로프) E3(피크) E4(트로프) E5(피크)
             (최소 피크 3개 + 트로프 2개)

대칭 삼각수렴 (Symmetrical) — Bulkowski 54%:
  상단 추세선 (E1,E3,E5): slope < 0   (고점 하향)
  하단 추세선 (E2,E4):    slope > 0   (저점 상향)

상승 삼각수렴 (Ascending) — Bulkowski 75%:
  상단 추세선: |slope| < TRIANGLE_SLOPE_FLAT   (수평)
  하단 추세선: slope > 0

하락 삼각수렴 (Descending) — Bulkowski 72%:
  상단 추세선: slope < 0
  하단 추세선: |slope| < TRIANGLE_SLOPE_FLAT   (수평)

유사도 공통 계산:
  기울기 조건 충족 여부                     (40점)
  선형회귀 R² 적합도                        (30점)
  수렴 강도 = |upper_slope| + |lower_slope| (30점)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import linregress

from .base import BasePattern, PatternResult
from .config import TRIANGLE_SLOPE_FLAT
from .preprocessor import preprocess


def _linreg(x: np.ndarray, y: np.ndarray):
    """선형 회귀 → (slope, intercept, r_squared)"""
    if len(x) < 2:
        return 0.0, 0.0, 0.0
    slope, intercept, r, _, _ = linregress(x, y)
    return float(slope), float(intercept), float(r ** 2)


def _compute_triangle_score(
    upper_slope: float,
    lower_slope: float,
    upper_r2: float,
    lower_r2: float,
    slope_condition: bool,
) -> float:
    """삼각수렴 공통 유사도 계산 (0~100)."""
    # [A] 기울기 조건 (40점)
    a_score = 40.0 if slope_condition else 0.0

    # [B] R² 적합도 (30점): 상단/하단 평균 R²
    avg_r2 = (upper_r2 + lower_r2) / 2.0
    b_score = avg_r2 * 30.0

    # [C] 수렴 강도 (30점): 기울기 절댓값 합이 클수록 수렴 강함
    #     0.01 이상을 만점 기준으로 선형 매핑
    convergence = abs(upper_slope) + abs(lower_slope)
    c_score = min(convergence / 0.01, 1.0) * 30.0

    return round(a_score + b_score + c_score, 1)


class _TriangleBase(BasePattern):
    """내부 공통 로직."""

    def _get_extrema_sequence(self, df: pd.DataFrame):
        """
        연속된 피크 3개 + 그 사이/이후 트로프 2개 추출.
        가장 최근 시퀀스를 선택.
        """
        prep    = preprocess(df)
        peaks   = prep["peaks"]
        troughs = prep["troughs"]
        norm    = prep["normalized"]
        dates   = prep["dates"]

        if len(peaks) < 3 or len(troughs) < 2:
            return None

        # 가장 최근 피크 3개
        p1_pos, p3_pos, p5_pos = peaks[-3], peaks[-2], peaks[-1]

        t2_candidates = [t for t in troughs if p1_pos < t < p3_pos]
        t4_candidates = [t for t in troughs if p3_pos < t < p5_pos]

        if not t2_candidates or not t4_candidates:
            return None

        t2_pos = min(t2_candidates, key=lambda t: norm.values[t])
        t4_pos = min(t4_candidates, key=lambda t: norm.values[t])

        upper_x = np.array([p1_pos, p3_pos, p5_pos], dtype=float)
        upper_y = norm.values[[p1_pos, p3_pos, p5_pos]]
        lower_x = np.array([t2_pos, t4_pos], dtype=float)
        lower_y = norm.values[[t2_pos, t4_pos]]

        upper_slope, _, upper_r2 = _linreg(upper_x, upper_y)
        lower_slope, _, lower_r2 = _linreg(lower_x, lower_y)

        return dict(
            upper_slope=upper_slope, upper_r2=upper_r2,
            lower_slope=lower_slope, lower_r2=lower_r2,
            p1_pos=p1_pos, p5_pos=p5_pos,
            dates=dates,
        )

    def _make_result(self, similarity: float, p1_pos, p5_pos, dates) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[p1_pos]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[p5_pos]).strftime("%Y-%m-%d"),
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )


class SymmetricalTriangle(_TriangleBase):
    name = "Symmetrical Triangle"
    name_ko = "대칭 삼각수렴"
    signal = "neutral"
    description = "고점 하향 + 저점 상향으로 수렴하는 중립 패턴. 돌파 방향으로 추세 결정"
    historical_success_rate = 54.0
    source = "Lo, Mamaysky & Wang (2000) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        seq = self._get_extrema_sequence(df)
        if seq is None:
            return self._zero_result()

        us, ls = seq["upper_slope"], seq["lower_slope"]
        # 대칭: 상단 기울기 < 0, 하단 기울기 > 0
        condition = (us < -TRIANGLE_SLOPE_FLAT) and (ls > TRIANGLE_SLOPE_FLAT)
        score = _compute_triangle_score(us, ls, seq["upper_r2"], seq["lower_r2"], condition)
        return self._make_result(score, seq["p1_pos"], seq["p5_pos"], seq["dates"])


class AscendingTriangle(_TriangleBase):
    name = "Ascending Triangle"
    name_ko = "상승 삼각수렴"
    signal = "bullish"
    description = "고점 수평 + 저점 상향으로 수렴하는 상승 지속 패턴"
    historical_success_rate = 75.0
    source = "Lo, Mamaysky & Wang (2000) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        seq = self._get_extrema_sequence(df)
        if seq is None:
            return self._zero_result()

        us, ls = seq["upper_slope"], seq["lower_slope"]
        # 상승: 상단 수평, 하단 상향
        condition = (abs(us) < TRIANGLE_SLOPE_FLAT) and (ls > TRIANGLE_SLOPE_FLAT)
        score = _compute_triangle_score(us, ls, seq["upper_r2"], seq["lower_r2"], condition)
        return self._make_result(score, seq["p1_pos"], seq["p5_pos"], seq["dates"])


class DescendingTriangle(_TriangleBase):
    name = "Descending Triangle"
    name_ko = "하락 삼각수렴"
    signal = "bearish"
    description = "고점 하향 + 저점 수평으로 수렴하는 하락 지속 패턴"
    historical_success_rate = 72.0
    source = "Lo, Mamaysky & Wang (2000) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        seq = self._get_extrema_sequence(df)
        if seq is None:
            return self._zero_result()

        us, ls = seq["upper_slope"], seq["lower_slope"]
        # 하락: 상단 하향, 하단 수평
        condition = (us < -TRIANGLE_SLOPE_FLAT) and (abs(ls) < TRIANGLE_SLOPE_FLAT)
        score = _compute_triangle_score(us, ls, seq["upper_r2"], seq["lower_r2"], condition)
        return self._make_result(score, seq["p1_pos"], seq["p5_pos"], seq["dates"])
