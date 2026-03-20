"""
Data fetcher: yfinance (주식) / ccxt (암호화폐)

심볼 규칙:
  - 코스피 : 005930.KS
  - 코스닥 : 035720.KQ
  - 미국주식: AAPL
  - 암호화폐: BTC-USD
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

PERIOD_MAP = {
    "1w":  "5d",
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "6mo",
    "1y":  "1y",
}

MIN_TRADING_DAYS = 60


def fetch_ohlcv(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """
    symbol 과 period 를 받아 OHLCV DataFrame 반환.

    Parameters
    ----------
    symbol : str  예) "AAPL", "005930.KS", "BTC-USD"
    period : str  "1w" | "1mo" | "3mo" | "6mo" | "1y"

    Returns
    -------
    pd.DataFrame  columns: Open, High, Low, Close, Volume
                  index  : DatetimeIndex (거래일)

    Raises
    ------
    ValueError  심볼 미존재 / 데이터 부족 / 지원하지 않는 기간
    RuntimeError API 타임아웃 등 네트워크 오류
    """
    yf_period = PERIOD_MAP.get(period)
    if yf_period is None:
        raise ValueError(f"지원하지 않는 기간: {period}. 허용값: {list(PERIOD_MAP.keys())}")

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=yf_period, auto_adjust=True)
    except Exception as exc:
        raise RuntimeError(f"데이터 수집 실패 ({symbol}): {exc}") from exc

    if df is None or df.empty:
        raise ValueError(f"심볼을 찾을 수 없거나 데이터가 없습니다: {symbol}")

    # 필요한 컬럼만 선택
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)  # timezone 제거
    df = df.dropna(subset=["Close"])

    if len(df) < MIN_TRADING_DAYS:
        raise ValueError(
            f"데이터 부족: {len(df)}거래일 (최소 {MIN_TRADING_DAYS}거래일 필요). "
            f"더 긴 기간을 선택하세요."
        )

    return df


def to_api_format(df: pd.DataFrame) -> list[dict]:
    """DataFrame → API 응답용 리스트 변환."""
    records = []
    for date, row in df.iterrows():
        records.append({
            "time":   date.strftime("%Y-%m-%d"),
            "open":   round(float(row["Open"]),  4),
            "high":   round(float(row["High"]),  4),
            "low":    round(float(row["Low"]),   4),
            "close":  round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        })
    return records
