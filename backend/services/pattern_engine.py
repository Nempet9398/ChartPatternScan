"""
패턴 분석 오케스트레이터.

모든 패턴을 실행하고 유사도 Top 3를 반환한다.
"""

from __future__ import annotations

import pandas as pd

from patterns.base import PatternResult
from patterns.golden_cross import GoldenCross
from patterns.dead_cross import DeadCross
from patterns.double_top import DoubleTop
from patterns.double_bottom import DoubleBottom
from patterns.head_and_shoulders import HeadAndShoulders
from patterns.inverse_head_and_shoulders import InverseHeadAndShoulders
from patterns.triangle import SymmetricalTriangle, AscendingTriangle, DescendingTriangle

ALL_PATTERNS = [
    HeadAndShoulders(),
    InverseHeadAndShoulders(),
    DoubleTop(),
    DoubleBottom(),
    GoldenCross(),
    DeadCross(),
    SymmetricalTriangle(),
    AscendingTriangle(),
    DescendingTriangle(),
]


def analyze(df: pd.DataFrame, top_n: int = 3) -> list[PatternResult]:
    """
    OHLCV DataFrame에 대해 모든 패턴의 유사도를 계산하고 상위 N개 반환.

    Parameters
    ----------
    df    : OHLCV DataFrame (Close 컬럼 필수)
    top_n : 반환할 패턴 수 (기본 3)

    Returns
    -------
    list[PatternResult]  유사도 내림차순 정렬
    """
    results: list[PatternResult] = []
    for pattern in ALL_PATTERNS:
        try:
            result = pattern.calculate_similarity(df)
            results.append(result)
        except Exception as exc:
            # 개별 패턴 오류가 전체 분석을 막지 않도록
            results.append(PatternResult(
                name=pattern.name,
                name_ko=pattern.name_ko,
                similarity=0.0,
                signal=pattern.signal,
                description=pattern.description,
                historical_success_rate=pattern.historical_success_rate,
                source=pattern.source,
                highlight_start=None,
                highlight_end=None,
            ))

    results.sort(key=lambda r: r.similarity, reverse=True)
    return results[:top_n]
