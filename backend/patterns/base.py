"""
BasePattern 추상 클래스 및 PatternResult 데이터 클래스.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class PatternResult:
    name: str
    name_ko: str
    similarity: float                  # 0.0 ~ 100.0
    signal: str                        # "bearish" | "bullish" | "neutral"
    description: str
    historical_success_rate: float     # Bulkowski (2005) 기준 %
    source: str                        # 논문 출처
    highlight_start: str | None        # ISO date (YYYY-MM-DD)
    highlight_end: str | None          # ISO date (YYYY-MM-DD)
    pattern_geometry: dict | None = field(default=None)
    # pattern_geometry 구조:
    # {
    #   "points": [{"label": str, "date": "YYYY-MM-DD", "value": float}, ...],
    #   "lines":  [{"type": str, "x1": "YYYY-MM-DD", "y1": float,
    #                             "x2": "YYYY-MM-DD", "y2": float,
    #                             "color": str, "style": "solid"|"dashed"}, ...],
    #   "levels": [{"type": str, "value": float, "color": str}, ...]
    # }
    # 모든 y/value는 실제 원본 가격 기준


class BasePattern(ABC):
    name: str
    name_ko: str
    signal: str
    description: str
    historical_success_rate: float
    source: str

    @abstractmethod
    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        """
        OHLCV DataFrame을 받아 PatternResult 반환.

        Parameters
        ----------
        df : pd.DataFrame  columns: Open, High, Low, Close, Volume

        Returns
        -------
        PatternResult  similarity 는 0.0 ~ 100.0 범위
        """
