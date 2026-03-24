"""
GET /api/chart/{symbol}

종목 + 타임프레임 선택 → OHLCV 데이터 반환.
"""

from __future__ import annotations

from typing import Literal, Union

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.data_fetcher import fetch_ohlcv, to_api_format

router = APIRouter()

Timeframe = Literal["15m", "30m", "1h", "6h", "12h", "1D", "1W"]


class OHLCVBar(BaseModel):
    time:   Union[str, int]
    open:   float
    high:   float
    low:    float
    close:  float
    volume: int


class ChartResponse(BaseModel):
    symbol:    str
    timeframe: str
    ohlcv:     list[OHLCVBar]


@router.get("/chart/{symbol}", response_model=ChartResponse, summary="OHLCV 데이터 조회")
def get_chart(
    symbol: str,
    timeframe: Timeframe = Query(
        default="1D",
        description="캔들 단위: 15m | 30m | 1h | 6h | 12h | 1D | 1W",
    ),
    limit: int | None = Query(
        default=None,
        description="캔들 수 (생략 시 타임프레임별 기본값 사용)",
        ge=1,
    ),
):
    """
    심볼과 타임프레임을 받아 OHLCV 캔들스틱 데이터를 반환합니다.

    - **symbol**: 종목 코드 (예: AAPL, 005930.KS, BTC-USD)
    - **timeframe**: 캔들 단위 (기본 1D)
    - **limit**: 캔들 수 (생략 시 타임프레임별 기본값)

    데이터 소스:
    - 주식(AAPL, 005930.KS 등) → yfinance
    - 암호화폐(BTC-USD 등)     → Binance (ccxt)
    """
    try:
        df = fetch_ohlcv(symbol.upper(), timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"예기치 않은 오류: {exc}")

    return ChartResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        ohlcv=[OHLCVBar(**bar) for bar in to_api_format(df, timeframe)],
    )
