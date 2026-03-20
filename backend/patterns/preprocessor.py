"""
Lo(2000) 커널 회귀를 이동평균으로 단순화한 공통 전처리 모듈.

참고: Lo, Mamaysky & Wang (2000) "Foundations of Technical Analysis"
      Journal of Finance, Vol.55 No.4
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from .config import SMOOTH_WINDOW, PEAK_MIN_DISTANCE, PEAK_MIN_PROMINENCE


def preprocess(df: pd.DataFrame) -> dict:
    """
    Lo(2000) 커널 회귀를 이동평균으로 단순화한 전처리.

    Parameters
    ----------
    df : pd.DataFrame  OHLCV DataFrame (Close 컬럼 필수)

    Returns
    -------
    dict:
      close         : 원본 종가 Series
      smoothed      : 스무딩된 종가 Series (MA5, NaN 제거)
      normalized    : Min-Max 정규화 Series (0~1)
      peaks         : 피크 인덱스 배열 (smoothed 기준 정수 인덱스)
      troughs       : 트로프 인덱스 배열
      peak_values   : 정규화된 피크 값 배열
      trough_values : 정규화된 트로프 값 배열
      dates         : smoothed 의 날짜 인덱스
    """
    close = df["Close"].copy()

    # 1) 스무딩 (Lo 2000 커널 회귀 대체: 5일 중심 이동평균)
    smoothed = close.rolling(window=SMOOTH_WINDOW, center=True).mean().dropna()

    # 2) Min-Max 정규화 (0~1)
    _min, _max = smoothed.min(), smoothed.max()
    norm = (smoothed - _min) / (_max - _min + 1e-10)

    # 3) 극값 탐지 (Lo 2000: 피크-트로프 교대 등장)
    peak_idx, _   = find_peaks(
        norm.values,
        distance=PEAK_MIN_DISTANCE,
        prominence=PEAK_MIN_PROMINENCE,
    )
    trough_idx, _ = find_peaks(
        -norm.values,
        distance=PEAK_MIN_DISTANCE,
        prominence=PEAK_MIN_PROMINENCE,
    )

    return {
        "close":         close,
        "smoothed":      smoothed,
        "normalized":    norm,
        "peaks":         peak_idx,
        "troughs":       trough_idx,
        "peak_values":   norm.values[peak_idx],
        "trough_values": norm.values[trough_idx],
        "dates":         norm.index,
    }
