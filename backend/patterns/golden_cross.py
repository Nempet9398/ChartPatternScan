"""
Golden Cross (골든크로스) 패턴.

출처: Edwards & Magee (1966) "Technical Analysis of Stock Trends"
성공률: Bulkowski (2005) 72%

조건:
  [C1] 최근 5거래일 내 MA20이 MA60 아래→위 교차        (60점)
  [C2] 교차 이후 이격도: (MA20-MA60)/MA60 가 클수록 ↑  (40점)
"""

from __future__ import annotations

import pandas as pd

from .base import BasePattern, PatternResult


CROSS_LOOKBACK = 5   # 교차 탐지 윈도우 (거래일)


class GoldenCross(BasePattern):
    name = "Golden Cross"
    name_ko = "골든크로스"
    signal = "bullish"
    description = "단기 이동평균(MA20)이 장기 이동평균(MA60)을 아래에서 위로 돌파하는 상승 신호"
    historical_success_rate = 72.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        close = df["Close"]

        if len(close) < 60:
            return self._zero_result(df)

        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        # 유효 구간만 (NaN 제거 후)
        valid = ma20.notna() & ma60.notna()
        ma20v = ma20[valid]
        ma60v = ma60[valid]

        if len(ma20v) < CROSS_LOOKBACK + 1:
            return self._zero_result(df)

        # [C1] 최근 CROSS_LOOKBACK 거래일 내 골든크로스 발생 여부
        # : i-1 에서 MA20 < MA60, i 에서 MA20 >= MA60
        cross_idx = None
        tail = ma20v.iloc[-(CROSS_LOOKBACK + 1):]
        tail60 = ma60v.iloc[-(CROSS_LOOKBACK + 1):]

        for i in range(1, len(tail)):
            if tail.iloc[i - 1] < tail60.iloc[i - 1] and tail.iloc[i] >= tail60.iloc[i]:
                cross_idx = i
                break

        c1_score = 60.0 if cross_idx is not None else 0.0

        # [C2] 현재 이격도: (MA20_last - MA60_last) / MA60_last
        spread = (ma20v.iloc[-1] - ma60v.iloc[-1]) / (ma60v.iloc[-1] + 1e-10)
        # spread가 0~5% 범위를 40점으로 선형 매핑 (5% 이상이면 만점)
        c2_score = min(spread / 0.05, 1.0) * 40.0 if spread > 0 else 0.0

        similarity = round(c1_score + c2_score, 1)

        # highlight: 교차 시점 ~ 최근일
        highlight_start = highlight_end = None
        if cross_idx is not None:
            dates_valid = ma20v.index
            cross_date = dates_valid[-(CROSS_LOOKBACK + 1) + cross_idx]
            highlight_start = pd.Timestamp(cross_date).strftime("%Y-%m-%d")
            highlight_end = pd.Timestamp(df.index[-1]).strftime("%Y-%m-%d")

        return PatternResult(
            name=self.name,
            name_ko=self.name_ko,
            similarity=similarity,
            signal=self.signal,
            description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=highlight_start,
            highlight_end=highlight_end,
        )

    def _zero_result(self, df: pd.DataFrame) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
