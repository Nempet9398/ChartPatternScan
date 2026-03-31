"""
Flag / Pennant (깃발형 / 페넌트) 패턴.

출처: Edwards & Magee (1966) / Bulkowski (2005)
  Bull Flag    성공률 67%
  Bear Flag    성공률 72%
  Bull Pennant 성공률 63%
  Bear Pennant 성공률 65%

공통 구조:
  1. Pole  : 강한 단방향 이동 (급등 또는 급락)
  2. Consolidation : 짧은 조정/횡보 구간
  3. Breakout : 원래 방향으로 재개

Flag vs Pennant 구분:
  - Flag    : 조정 구간이 평행 채널 (기울기 반대 방향)
  - Pennant : 조정 구간이 수렴 삼각형

조건:
  [C1] Pole 크기 (FLAG_POLE_MIN_MOVE 이상)              (30점)
  [C2] 조정 구간 길이 (FLAG_CONSOLIDATION 범위 내)       (20점)
  [C3] 조정 구간 형태 (Flag=평행, Pennant=수렴)          (30점)
  [C4] 돌파 방향 확인                                    (20점)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .base import BasePattern, PatternResult
from .config import (
    FLAG_POLE_MIN_MOVE,
    FLAG_CONSOLIDATION_MAX_BARS,
    FLAG_CONSOLIDATION_MIN_BARS,
    BREAKOUT_EPSILON,
    TRIANGLE_SLOPE_FLAT,
)
from .preprocessor import preprocess


def _find_pole_and_consolidation(
    norm: pd.Series,
    direction: str,  # "bull" or "bear"
) -> tuple[int, int, int, float] | None:
    """
    Pole 구간(pole_start~pole_end)과 조정 구간(pole_end~consol_end)을 탐지.
    Returns (pole_start, pole_end, consol_end, pole_move) or None
    """
    vals = norm.values
    n = len(vals)
    min_pole = 10

    best = None
    best_pole_move = 0.0

    for pole_end in range(min_pole, n - FLAG_CONSOLIDATION_MIN_BARS):
        # pole 구간: pole_end 기준으로 뒤로 탐색
        for pole_start in range(max(0, pole_end - 40), pole_end - min_pole + 1):
            pole_move = vals[pole_end] - vals[pole_start]

            if direction == "bull" and pole_move < FLAG_POLE_MIN_MOVE:
                continue
            if direction == "bear" and pole_move > -FLAG_POLE_MIN_MOVE:
                continue

            abs_move = abs(pole_move)
            if abs_move < FLAG_POLE_MIN_MOVE:
                continue

            # 조정 구간
            consol_start = pole_end
            consol_end = min(
                consol_start + FLAG_CONSOLIDATION_MAX_BARS,
                n - 1,
            )

            if consol_end - consol_start < FLAG_CONSOLIDATION_MIN_BARS:
                continue

            if abs_move > best_pole_move:
                best_pole_move = abs_move
                best = (pole_start, pole_end, consol_end, pole_move)

    return best


def _consolidation_shape(norm_vals: np.ndarray) -> tuple[float, float, float]:
    """
    조정 구간 형태 분석.
    Returns (upper_slope, lower_slope, convergence_ratio)
    """
    n = len(norm_vals)
    if n < 4:
        return 0.0, 0.0, 0.0

    x = np.arange(n, dtype=float)
    mid = norm_vals.mean()

    upper_mask = norm_vals >= mid
    lower_mask = norm_vals <= mid

    upper_x = x[upper_mask]
    upper_y = norm_vals[upper_mask]
    lower_x = x[lower_mask]
    lower_y = norm_vals[lower_mask]

    if len(upper_x) < 2 or len(lower_x) < 2:
        return 0.0, 0.0, 0.0

    us, _, _, _, _ = stats.linregress(upper_x, upper_y)
    ls, _, _, _, _ = stats.linregress(lower_x, lower_y)

    # 수렴 비율
    width_start = (us * 0 + upper_y[0]) - (ls * 0 + lower_y[0])
    width_end   = (us * (n-1) + upper_y[0]) - (ls * (n-1) + lower_y[0])
    if abs(width_start) < 1e-10:
        conv = 0.0
    else:
        conv = max(0.0, (abs(width_start) - abs(width_end)) / abs(width_start))

    return us, ls, conv


class BullFlag(BasePattern):
    name = "Bull Flag"
    name_ko = "불 깃발"
    signal = "bullish"
    description = "급등 후 평행 채널로 조정한 뒤 상방 돌파하는 상승 지속 패턴"
    historical_success_rate = 67.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        norm  = prep["normalized"]
        dates = prep["dates"]

        result = _find_pole_and_consolidation(norm, "bull")
        if result is None:
            return self._zero_result()

        pole_start, pole_end, consol_end, pole_move = result

        # [C1] 폴 크기
        c1 = min(abs(pole_move) / (FLAG_POLE_MIN_MOVE * 3), 1.0) * 30.0

        # [C2] 조정 구간 길이
        consol_len = consol_end - pole_end
        if FLAG_CONSOLIDATION_MIN_BARS <= consol_len <= FLAG_CONSOLIDATION_MAX_BARS:
            c2 = 20.0
        else:
            c2 = 0.0

        # [C3] Flag 형태: 두 선 평행 (기울기 반대 방향, 수렴 없음)
        consol_vals = norm.values[pole_end:consol_end + 1]
        us, ls, conv = _consolidation_shape(consol_vals)
        # Flag: 두 선 모두 완만한 하향 기울기, 수렴 아님
        flag_like = (us < 0) and (ls < 0) and (conv < 0.3)
        if flag_like:
            c3 = 30.0
        else:
            c3 = max(0.0, 15.0 - conv * 20.0)

        # [C4] 돌파 확인
        c4 = 0.0
        if consol_end < len(norm) - 1:
            after = norm.values[consol_end:]
            consol_high = norm.values[pole_end:consol_end + 1].max()
            if len(after) >= 2 and after[-1] > consol_high * (1 + BREAKOUT_EPSILON):
                c4 = 20.0
            elif len(after) >= 1:
                c4 = max(0.0, (after[-1] - consol_high) / (consol_high + 1e-10)) * 20.0

        similarity = round(c1 + c2 + c3 + c4, 1)

        return PatternResult(
            name=self.name, name_ko=self.name_ko,
            similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[pole_start]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[min(consol_end, len(dates)-1)]).strftime("%Y-%m-%d"),
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )


class BearFlag(BasePattern):
    name = "Bear Flag"
    name_ko = "베어 깃발"
    signal = "bearish"
    description = "급락 후 평행 채널로 반등한 뒤 하방 이탈하는 하락 지속 패턴"
    historical_success_rate = 72.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        norm  = prep["normalized"]
        dates = prep["dates"]

        result = _find_pole_and_consolidation(norm, "bear")
        if result is None:
            return self._zero_result()

        pole_start, pole_end, consol_end, pole_move = result

        # [C1] 폴 크기
        c1 = min(abs(pole_move) / (FLAG_POLE_MIN_MOVE * 3), 1.0) * 30.0

        # [C2] 조정 구간 길이
        consol_len = consol_end - pole_end
        if FLAG_CONSOLIDATION_MIN_BARS <= consol_len <= FLAG_CONSOLIDATION_MAX_BARS:
            c2 = 20.0
        else:
            c2 = 0.0

        # [C3] Flag 형태: 두 선 모두 완만한 상향 기울기
        consol_vals = norm.values[pole_end:consol_end + 1]
        us, ls, conv = _consolidation_shape(consol_vals)
        flag_like = (us > 0) and (ls > 0) and (conv < 0.3)
        if flag_like:
            c3 = 30.0
        else:
            c3 = max(0.0, 15.0 - conv * 20.0)

        # [C4] 돌파 확인
        c4 = 0.0
        if consol_end < len(norm) - 1:
            after = norm.values[consol_end:]
            consol_low = norm.values[pole_end:consol_end + 1].min()
            if len(after) >= 2 and after[-1] < consol_low * (1 - BREAKOUT_EPSILON):
                c4 = 20.0
            elif len(after) >= 1:
                c4 = max(0.0, (consol_low - after[-1]) / (consol_low + 1e-10)) * 20.0

        similarity = round(c1 + c2 + c3 + c4, 1)

        return PatternResult(
            name=self.name, name_ko=self.name_ko,
            similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[pole_start]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[min(consol_end, len(dates)-1)]).strftime("%Y-%m-%d"),
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )


class BullPennant(BasePattern):
    name = "Bull Pennant"
    name_ko = "불 페넌트"
    signal = "bullish"
    description = "급등 후 수렴 삼각형으로 조정한 뒤 상방 돌파하는 상승 지속 패턴"
    historical_success_rate = 63.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        norm  = prep["normalized"]
        dates = prep["dates"]

        result = _find_pole_and_consolidation(norm, "bull")
        if result is None:
            return self._zero_result()

        pole_start, pole_end, consol_end, pole_move = result

        # [C1] 폴 크기
        c1 = min(abs(pole_move) / (FLAG_POLE_MIN_MOVE * 3), 1.0) * 30.0

        # [C2] 조정 구간 길이
        consol_len = consol_end - pole_end
        if FLAG_CONSOLIDATION_MIN_BARS <= consol_len <= FLAG_CONSOLIDATION_MAX_BARS:
            c2 = 20.0
        else:
            c2 = 0.0

        # [C3] Pennant 형태: 수렴 삼각형
        consol_vals = norm.values[pole_end:consol_end + 1]
        us, ls, conv = _consolidation_shape(consol_vals)
        pennant_like = (us <= 0) and (ls >= 0) and (conv >= 0.3)
        if pennant_like:
            c3 = 30.0
        else:
            c3 = min(conv / 0.3, 1.0) * 20.0

        # [C4] 상방 돌파
        c4 = 0.0
        if consol_end < len(norm) - 1:
            after = norm.values[consol_end:]
            consol_high = norm.values[pole_end:consol_end + 1].max()
            if len(after) >= 2 and after[-1] > consol_high * (1 + BREAKOUT_EPSILON):
                c4 = 20.0
            elif len(after) >= 1:
                c4 = max(0.0, (after[-1] - consol_high) / (consol_high + 1e-10)) * 20.0

        similarity = round(c1 + c2 + c3 + c4, 1)

        return PatternResult(
            name=self.name, name_ko=self.name_ko,
            similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[pole_start]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[min(consol_end, len(dates)-1)]).strftime("%Y-%m-%d"),
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )


class BearPennant(BasePattern):
    name = "Bear Pennant"
    name_ko = "베어 페넌트"
    signal = "bearish"
    description = "급락 후 수렴 삼각형으로 반등한 뒤 하방 이탈하는 하락 지속 패턴"
    historical_success_rate = 65.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        prep = preprocess(df)
        norm  = prep["normalized"]
        dates = prep["dates"]

        result = _find_pole_and_consolidation(norm, "bear")
        if result is None:
            return self._zero_result()

        pole_start, pole_end, consol_end, pole_move = result

        # [C1] 폴 크기
        c1 = min(abs(pole_move) / (FLAG_POLE_MIN_MOVE * 3), 1.0) * 30.0

        # [C2] 조정 구간 길이
        consol_len = consol_end - pole_end
        if FLAG_CONSOLIDATION_MIN_BARS <= consol_len <= FLAG_CONSOLIDATION_MAX_BARS:
            c2 = 20.0
        else:
            c2 = 0.0

        # [C3] Pennant 형태: 수렴 삼각형
        consol_vals = norm.values[pole_end:consol_end + 1]
        us, ls, conv = _consolidation_shape(consol_vals)
        pennant_like = (us <= 0) and (ls >= 0) and (conv >= 0.3)
        if pennant_like:
            c3 = 30.0
        else:
            c3 = min(conv / 0.3, 1.0) * 20.0

        # [C4] 하방 이탈
        c4 = 0.0
        if consol_end < len(norm) - 1:
            after = norm.values[consol_end:]
            consol_low = norm.values[pole_end:consol_end + 1].min()
            if len(after) >= 2 and after[-1] < consol_low * (1 - BREAKOUT_EPSILON):
                c4 = 20.0
            elif len(after) >= 1:
                c4 = max(0.0, (consol_low - after[-1]) / (consol_low + 1e-10)) * 20.0

        similarity = round(c1 + c2 + c3 + c4, 1)

        return PatternResult(
            name=self.name, name_ko=self.name_ko,
            similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=pd.Timestamp(dates[pole_start]).strftime("%Y-%m-%d"),
            highlight_end=pd.Timestamp(dates[min(consol_end, len(dates)-1)]).strftime("%Y-%m-%d"),
        )

    def _zero_result(self) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
