"""
Dead Cross (데드크로스) 패턴 — 골든크로스의 반전.

출처: Edwards & Magee (1966)
성공률: Bulkowski (2005) 68%

조건:
  [C1] 최근 5거래일 내 MA20이 MA60 위→아래 교차   (60점)
  [C2] 이격도: (MA60-MA20)/MA60 가 클수록 ↑        (40점)
"""

from __future__ import annotations

import pandas as pd

from .base import BasePattern, PatternResult

CROSS_LOOKBACK = 5


class DeadCross(BasePattern):
    name = "Dead Cross"
    name_ko = "데드크로스"
    signal = "bearish"
    description = "단기 이동평균(MA20)이 장기 이동평균(MA60)을 위에서 아래로 이탈하는 하락 신호"
    historical_success_rate = 68.0
    source = "Edwards & Magee (1966) / Bulkowski (2005)"

    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        close = df["Close"]

        if len(close) < 60:
            return self._zero_result(df)

        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        valid = ma20.notna() & ma60.notna()
        ma20v = ma20[valid]
        ma60v = ma60[valid]

        if len(ma20v) < CROSS_LOOKBACK + 1:
            return self._zero_result(df)

        # [C1] 최근 CROSS_LOOKBACK 거래일 내 데드크로스 발생 여부
        cross_idx = None
        tail = ma20v.iloc[-(CROSS_LOOKBACK + 1):]
        tail60 = ma60v.iloc[-(CROSS_LOOKBACK + 1):]

        for i in range(1, len(tail)):
            if tail.iloc[i - 1] >= tail60.iloc[i - 1] and tail.iloc[i] < tail60.iloc[i]:
                cross_idx = i
                break

        c1_score = 60.0 if cross_idx is not None else 0.0

        # [C2] 현재 이격도: (MA60_last - MA20_last) / MA60_last
        spread = (ma60v.iloc[-1] - ma20v.iloc[-1]) / (ma60v.iloc[-1] + 1e-10)
        c2_score = min(spread / 0.05, 1.0) * 40.0 if spread > 0 else 0.0

        similarity = round(c1_score + c2_score, 1)

        highlight_start = highlight_end = None
        if cross_idx is not None:
            cross_date = ma20v.index[-(CROSS_LOOKBACK + 1) + cross_idx]
            highlight_start = pd.Timestamp(cross_date).strftime("%Y-%m-%d")
            highlight_end = pd.Timestamp(df.index[-1]).strftime("%Y-%m-%d")

        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=similarity,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source,
            highlight_start=highlight_start, highlight_end=highlight_end,
        )

    def _zero_result(self, df: pd.DataFrame) -> PatternResult:
        return PatternResult(
            name=self.name, name_ko=self.name_ko, similarity=0.0,
            signal=self.signal, description=self.description,
            historical_success_rate=self.historical_success_rate,
            source=self.source, highlight_start=None, highlight_end=None,
        )
