"""
Wedge (쐐기형) 패턴 — Rising Wedge / Falling Wedge.

출처: Edwards & Magee (1966) / Bulkowski (2005)
  Rising Wedge  성공률 81% (bearish)
  Falling Wedge 성공률 74% (bullish)

Rising Wedge:
  - 상단/하단 추세선 모두 우상향
  - 하단 기울기 > 상단 기울기 (더 가파름 → 수렴)
  - bearish bias

Falling Wedge:
  - 상단/하단 추세선 모두 우하향
  - 상단 기울기 절댓값 > 하단 기울기 절댓값 (더 가파름 → 수렴)
  - bullish bias

조건 공통:
  [C1] 두 추세선 방향 조건 (40점)
  [C2] 수렴성 — 두 선 기울기 차이 (30점)
  [C3] R² 선형 적합도 (30점)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .base import BasePattern, PatternResult
from .config import WEDGE_MIN_BARS, WEDGE_CONVERGENCE_MIN
from .preprocessor import preprocess


def _wedge_scores(
    peaks: np.ndarray,
    troughs: np.ndarray,
    norm: pd.Series,
) -> tuple[float, float, float, float, float]:
    """
    상단(peak)/하단(trough) 추세선 회귀.
    Returns: upper_slope, lower_slope, upper_r2, lower_r2, convergence_ratio
    """
    if len(peaks) < 2 or len(troughs) < 2:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    peak_x = np.array(peaks, dtype=float)
    peak_y = norm.values[peaks]
    us, ui, ur, _, _ = stats.linregress(peak_x, peak_y)

    trough_x = np.array(troughs, dtype=float)
    trough_y = norm.values[troughs]
    ls, li, lr, _, _ = stats.linregress(trough_x, trough_y)

    # 수렴 비율: 시작 폭 대비 끝 폭 감소
    start_x = max(peaks[0], troughs[0])
    end_x   = min(peaks[-1], troughs[-1])
    if end_x <= start_x:
        conv = 0.0
    else:
        width_start = (ui + us * start_x) - (li + ls * start_x)
        width_end   = (ui + us * end_x)   - (li + ls * end_x)
        if abs(width_start) < 1e-10:
            conv = 0.0
        else:
            conv = max(0.0, (width_start - width_end) / abs(width_start))

    return us, ls, ur ** 2, lr ** 2, conv


class RisingWedge(BasePattern):
    name = "Rising Wedge"
    name_ko = "상승 쐐기"
    signal = "bearish"
    description = "상단/하단 모두 우상향하지만 하단이 더 가파르게 수렴하는 하락 반전 패턴"
    historical_success_rate = 81.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        peaks   = prep["peaks"]
        troughs = prep["troughs"]
        norm    = prep["normalized"]
        dates   = prep["dates"]

        if len(peaks) < 2 or len(troughs) < 2 or len(norm) < WEDGE_MIN_BARS:
            return self._zero_result()

        us, ls, ur2, lr2, conv = _wedge_scores(peaks, troughs, norm)

        # [C1] 두 선 모두 우상향 & 하단 기울기 > 상단 기울기
        rising_both = (us > 0) and (ls > 0)
        lower_steeper = ls > us
        if rising_both and lower_steeper:
            c1 = 40.0
        elif rising_both:
            c1 = 20.0
        else:
            c1 = 0.0

        # [C2] 수렴성
        c2 = min(conv / WEDGE_CONVERGENCE_MIN, 1.0) * 30.0

        # [C3] R² 적합도
        avg_r2 = (ur2 + lr2) / 2.0
        c3 = avg_r2 * 30.0

        similarity = round(c1 + c2 + c3, 1)

        start_pos = max(peaks[0], troughs[0])
        end_pos   = min(peaks[-1], troughs[-1])
        if start_pos >= len(dates) or end_pos >= len(dates):
            end_pos = len(dates) - 1

        return PatternResult(
            name=self.name, name_ko=self.name_ko,
            similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[start_pos]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[end_pos]).strftime("%Y-%m-%d"),
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )


class FallingWedge(BasePattern):
    name = "Falling Wedge"
    name_ko = "하락 쐐기"
    signal = "bullish"
    description = "상단/하단 모두 우하향하지만 상단이 더 가파르게 수렴하는 상승 반전 패턴"
    historical_success_rate = 74.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        peaks   = prep["peaks"]
        troughs = prep["troughs"]
        norm    = prep["normalized"]
        dates   = prep["dates"]

        if len(peaks) < 2 or len(troughs) < 2 or len(norm) < WEDGE_MIN_BARS:
            return self._zero_result()

        us, ls, ur2, lr2, conv = _wedge_scores(peaks, troughs, norm)

        # [C1] 두 선 모두 우하향 & 상단 기울기 절댓값 > 하단 기울기 절댓값
        falling_both = (us < 0) and (ls < 0)
        upper_steeper = abs(us) > abs(ls)
        if falling_both and upper_steeper:
            c1 = 40.0
        elif falling_both:
            c1 = 20.0
        else:
            c1 = 0.0

        # [C2] 수렴성
        c2 = min(conv / WEDGE_CONVERGENCE_MIN, 1.0) * 30.0

        # [C3] R² 적합도
        avg_r2 = (ur2 + lr2) / 2.0
        c3 = avg_r2 * 30.0

        similarity = round(c1 + c2 + c3, 1)

        start_pos = max(peaks[0], troughs[0])
        end_pos   = min(peaks[-1], troughs[-1])
        if start_pos >= len(dates) or end_pos >= len(dates):
            end_pos = len(dates) - 1

        return PatternResult(
            name=self.name, name_ko=self.name_ko,
            similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[start_pos]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[end_pos]).strftime("%Y-%m-%d"),
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
