"""
GET /api/chart/{symbol}

종목 + 기간 선택 → OHLCV 데이터 반환.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.data_fetcher import fetch_ohlcv, to_api_format

router = APIRouter()

Period = Literal["1w", "1mo", "3mo", "6mo", "1y"]


class OHLCVBar(BaseModel):
    time:   str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: int


class ChartResponse(BaseModel):
    symbol: str
    period: str
    ohlcv:  list[OHLCVBar]


@router.get("/chart/{symbol}", response_model=ChartResponse, summary="OHLCV 데이터 조회")
def get_chart(
    symbol: str,
    period: Period = Query(default="3mo", description="조회 기간: 1w | 1mo | 3mo | 6mo | 1y"),
):
    """
    심볼과 기간을 받아 OHLCV 캔들스틱 데이터를 반환합니다.

    - **symbol**: 종목 코드 (예: AAPL, 005930.KS, BTC-USD)
    - **period**: 조회 기간 (기본 3mo)
    """
    try:
        df = fetch_ohlcv(symbol.upper(), period)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"예기치 않은 오류: {exc}")

    return ChartResponse(
        symbol=symbol.upper(),
        period=period,
        ohlcv=[OHLCVBar(**bar) for bar in to_api_format(df)],
    )
