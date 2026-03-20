"""
POST /api/analyze

종목 + 기간 → 패턴 유사도 Top 3 반환.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.data_fetcher import fetch_ohlcv
from services.pattern_engine import analyze

router = APIRouter()

Period = Literal["1w", "1mo", "3mo", "6mo", "1y"]


# ── 요청 / 응답 모델 ──────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    symbol: str  = Field(..., examples=["AAPL"], description="종목 코드")
    period: Period = Field(default="3mo", description="조회 기간")


class PatternItem(BaseModel):
    rank:                    int
    name:                    str
    name_ko:                 str
    similarity:              float   = Field(..., description="유사도 0~100")
    signal:                  str     = Field(..., description="bullish | bearish | neutral")
    description:             str
    historical_success_rate: float   = Field(..., description="Bulkowski(2005) 기준 %")
    source:                  str
    highlight_start:         str | None
    highlight_end:           str | None


class AnalyzeResponse(BaseModel):
    symbol:        str
    period:        str
    analyzed_at:   str
    algorithm_ref: str
    top_patterns:  list[PatternItem]


ALGORITHM_REF = "Lo, Mamaysky & Wang (2000), Journal of Finance Vol.55 No.4"


# ── 라우터 ───────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse, summary="차트 패턴 분석")
def post_analyze(body: AnalyzeRequest):
    """
    종목 코드와 기간을 받아 차트 패턴 유사도 Top 3를 반환합니다.

    알고리즘: Lo, Mamaysky & Wang (2000) 논문 기반 규칙 매칭.
    LLM 미사용 — 모든 판단은 수치 규칙으로만 수행합니다.

    ⚠️ 본 서비스의 분석 결과는 투자 권유가 아닙니다.
       투자 손익의 책임은 전적으로 본인에게 있습니다.
    """
    symbol = body.symbol.upper()

    try:
        df = fetch_ohlcv(symbol, body.period)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"데이터 수집 오류: {exc}")

    try:
        results = analyze(df, top_n=3)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"패턴 분석 오류: {exc}")

    top_patterns = [
        PatternItem(
            rank=rank,
            name=r.name,
            name_ko=r.name_ko,
            similarity=r.similarity,
            signal=r.signal,
            description=r.description,
            historical_success_rate=r.historical_success_rate,
            source=r.source,
            highlight_start=r.highlight_start,
            highlight_end=r.highlight_end,
        )
        for rank, r in enumerate(results, start=1)
    ]

    return AnalyzeResponse(
        symbol=symbol,
        period=body.period,
        analyzed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        algorithm_ref=ALGORITHM_REF,
        top_patterns=top_patterns,
    )
