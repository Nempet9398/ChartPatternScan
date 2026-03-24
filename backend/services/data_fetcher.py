"""
Data fetcher: yfinance (주식) / ccxt Binance (암호화폐)

심볼 규칙:
  - 코스피 : 005930.KS
  - 코스닥 : 035720.KQ
  - 미국주식: AAPL
  - 암호화폐: BTC-USD  (내부에서 BTC/USDT 로 변환 → Binance)

타임프레임: 15m | 30m | 1h | 6h | 12h | 1D | 1W
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import ccxt
import pandas as pd
import yfinance as yf

MIN_CANDLES = 60  # 패턴 분석 최소 캔들 수

# ── 타임프레임 → yfinance interval 매핑 ─────────────────────────────────────
# 6h / 12h 는 yfinance 미지원 → 1h 데이터를 리샘플링
_YF_INTERVAL: dict[str, str] = {
    "15m": "15m",
    "30m": "30m",
    "1h":  "1h",
    "6h":  "1h",    # resample
    "12h": "1h",    # resample
    "1D":  "1d",
    "1W":  "1wk",
}

# ── 타임프레임 → ccxt timeframe ────────────────────────────────────────────
_CCXT_TF: dict[str, str] = {
    "15m": "15m",
    "30m": "30m",
    "1h":  "1h",
    "6h":  "6h",
    "12h": "12h",
    "1D":  "1d",
    "1W":  "1w",
}

# ── 타임프레임 → 기본 fetch limit (맥락 데이터용) ─────────────────────────────
DEFAULT_LIMIT: dict[str, int] = {
    "15m": 672,   # 7일 × 96캔들
    "30m": 336,   # 7일 × 48캔들
    "1h":  720,   # 30일 × 24캔들
    "6h":  360,   # 90일 × 4캔들
    "12h": 360,   # 180일 × 2캔들
    "1D":  504,   # 약 2년 거래일
    "1W":  104,   # 2년 주봉
}

# ── 타임프레임 → 분 단위 ────────────────────────────────────────────────────
_TF_MINUTES: dict[str, int] = {
    "15m": 15, "30m": 30, "1h": 60,
    "6h": 360, "12h": 720, "1D": 1440, "1W": 10080,
}


def _is_crypto(symbol: str) -> bool:
    """BTC-USD, ETH-USD 등 암호화폐 심볼 판별."""
    return "-" in symbol and not symbol.endswith((".KS", ".KQ"))


def _to_ccxt_symbol(symbol: str) -> str:
    """BTC-USD → BTC/USDT (Binance 형식)."""
    base = symbol.split("-")[0]
    return f"{base}/USDT"


def _calc_start_date(timeframe: str, limit: int) -> datetime:
    """limit 캔들을 커버하는 시작 날짜 계산 (50% 버퍼 포함)."""
    minutes = _TF_MINUTES[timeframe]
    delta = timedelta(minutes=limit * minutes * 1.5)
    return datetime.now(timezone.utc) - delta


# ── yfinance fetch ──────────────────────────────────────────────────────────

def _fetch_yfinance(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    interval = _YF_INTERVAL[timeframe]
    start = _calc_start_date(timeframe, limit)

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, interval=interval, auto_adjust=True)
    except Exception as exc:
        raise RuntimeError(f"yfinance 오류 ({symbol}): {exc}") from exc

    if df is None or df.empty:
        raise ValueError(f"심볼을 찾을 수 없거나 데이터가 없습니다: {symbol}")

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.dropna(subset=["Close"])

    # 6h / 12h 리샘플링
    if timeframe in ("6h", "12h"):
        df = df.resample(timeframe).agg({
            "Open": "first", "High": "max",
            "Low": "min", "Close": "last", "Volume": "sum",
        }).dropna()

    return df.tail(limit)


# ── ccxt fetch ──────────────────────────────────────────────────────────────

def _fetch_ccxt(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    ccxt_symbol = _to_ccxt_symbol(symbol)
    ccxt_tf = _CCXT_TF[timeframe]

    try:
        exchange = ccxt.binance({"enableRateLimit": True})
        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe=ccxt_tf, limit=limit)
    except Exception as exc:
        raise RuntimeError(f"Binance 데이터 수집 실패 ({symbol}): {exc}") from exc

    if not ohlcv:
        raise ValueError(f"데이터 없음: {symbol}")

    df = pd.DataFrame(ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
    df.index = pd.to_datetime(df["timestamp"], unit="ms").dt.tz_localize(None)
    df = df.drop(columns=["timestamp"])

    return df


# ── 공개 API ────────────────────────────────────────────────────────────────

def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1D",
    limit: int | None = None,
) -> pd.DataFrame:
    """
    symbol + timeframe + limit 으로 OHLCV DataFrame 반환.

    Parameters
    ----------
    symbol    : "AAPL", "005930.KS", "BTC-USD"
    timeframe : "15m" | "30m" | "1h" | "6h" | "12h" | "1D" | "1W"
    limit     : 캔들 수 (None 이면 DEFAULT_LIMIT 사용)

    Raises
    ------
    ValueError   심볼 미존재 / 데이터 부족
    RuntimeError API 오류
    """
    if timeframe not in DEFAULT_LIMIT:
        raise ValueError(
            f"지원하지 않는 타임프레임: {timeframe}. "
            f"허용값: {list(DEFAULT_LIMIT.keys())}"
        )

    n = limit or DEFAULT_LIMIT[timeframe]

    if _is_crypto(symbol):
        df = _fetch_ccxt(symbol, timeframe, n)
    else:
        df = _fetch_yfinance(symbol, timeframe, n)

    if len(df) < MIN_CANDLES:
        raise ValueError(
            f"데이터 부족: {len(df)}캔들 (최소 {MIN_CANDLES}캔들 필요). "
            f"더 긴 타임프레임을 선택하거나 다른 종목을 시도해보세요."
        )

    return df


def to_api_format(df: pd.DataFrame, timeframe: str = "1D") -> list[dict]:
    """DataFrame → API 응답 리스트 변환.

    일봉/주봉: time = "YYYY-MM-DD" 문자열
    분봉/시봉: time = Unix 초 정수 (lightweight-charts UTC timestamp)
    """
    is_intraday = timeframe not in ("1D", "1W")
    records = []
    for ts, row in df.iterrows():
        time_val: str | int = (
            int(pd.Timestamp(ts).timestamp())
            if is_intraday
            else ts.strftime("%Y-%m-%d")
        )
        records.append({
            "time":   time_val,
            "open":   round(float(row["Open"]),  4),
            "high":   round(float(row["High"]),  4),
            "low":    round(float(row["Low"]),   4),
            "close":  round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        })
    return records
