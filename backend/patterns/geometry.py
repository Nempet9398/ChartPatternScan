"""
패턴 기하학 시각화를 위한 유틸리티 함수.

모든 좌표는 실제 원본 Close 가격 기준으로 변환하여 반환한다.
(프론트엔드 lightweight-charts 에서 바로 사용 가능)
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def pos_to_date(pos: int, dates: pd.Index) -> str:
    """배열 위치 → ISO 날짜 문자열."""
    return pd.Timestamp(dates[pos]).strftime("%Y-%m-%d")


def pos_to_price(pos: int, dates: pd.Index, close: pd.Series) -> float:
    """배열 위치 → 실제 Close 가격."""
    date = dates[pos]
    if date in close.index:
        return float(close.loc[date])
    return float(close.iloc[pos])


def norm_to_price(norm_val: float, close: pd.Series, smoothed: pd.Series) -> float:
    """
    정규화 값(0~1) → 실제 가격.
    smoothed의 min/max로 역정규화한 뒤 close 범위로 스케일.
    """
    s_min = float(smoothed.min())
    s_max = float(smoothed.max())
    return norm_val * (s_max - s_min) + s_min


def make_point(label: str, date: str, value: float) -> dict:
    return {"label": label, "date": date, "value": round(value, 4)}


def make_line(
    x1: str, y1: float,
    x2: str, y2: float,
    line_type: str,
    color: str = "#888888",
    style: str = "solid",
) -> dict:
    return {
        "type": line_type,
        "x1": x1, "y1": round(y1, 4),
        "x2": x2, "y2": round(y2, 4),
        "color": color,
        "style": style,
    }


def make_level(level_type: str, value: float, color: str = "#888888") -> dict:
    return {"type": level_type, "value": round(value, 4), "color": color}


def build_geometry(
    points: list[dict] | None = None,
    lines: list[dict] | None = None,
    levels: list[dict] | None = None,
) -> dict:
    return {
        "points": points or [],
        "lines": lines or [],
        "levels": levels or [],
    }


def trendline_endpoints(
    x_start: int,
    x_end: int,
    slope: float,
    intercept: float,
    dates: pd.Index,
    close: pd.Series,
    smoothed: pd.Series,
) -> tuple[str, float, str, float]:
    """
    회귀선의 시작/끝 좌표를 날짜 + 실제 가격으로 변환.
    slope/intercept는 normalized 공간 기준.
    """
    y_start_norm = slope * x_start + intercept
    y_end_norm   = slope * x_end   + intercept
    return (
        pos_to_date(x_start, dates),
        norm_to_price(y_start_norm, close, smoothed),
        pos_to_date(x_end, dates),
        norm_to_price(y_end_norm, close, smoothed),
    )
