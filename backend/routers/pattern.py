"""
POST /api/analyze

종목 + 타임프레임 + 선택 구간(선택) → 패턴 유사도 Top 3 반환.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.data_fetcher import fetch_ohlcv, MIN_CANDLES
from services.pattern_engine import analyze

router = APIRouter()

Timeframe = Literal["15m", "30m", "1h", "6h", "12h", "1D", "1W"]


# ── 요청 / 응답 모델 ──────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    symbol:     str       = Field(..., examples=["AAPL"], description="종목 코드")
    timeframe:  Timeframe = Field(default="1D", description="캔들 단위")
    start_time: str | None = Field(
        default=None,
        description="구간 분석 시작 (ISO 날짜/시간, 예: 2024-01-02 또는 2024-01-02T14:30:00)",
    )
    end_time:   str | None = Field(
        default=None,
        description="구간 분석 끝 (ISO 날짜/시간)",
    )


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
    timeframe:     str
    analyzed_at:   str
    algorithm_ref: str
    top_patterns:  list[PatternItem]


ALGORITHM_REF = "Lo, Mamaysky & Wang (2000), Journal of Finance Vol.55 No.4"


# ── 라우터 ───────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse, summary="차트 패턴 분석")
def post_analyze(body: AnalyzeRequest):
    """
    종목 코드와 타임프레임을 받아 차트 패턴 유사도 Top 3를 반환합니다.

    - start_time / end_time 을 지정하면 해당 구간만 분석합니다.
    - 선택 구간이 60캔들 미만이면 422 에러를 반환합니다.

    알고리즘: Lo, Mamaysky & Wang (2000) 논문 기반 규칙 매칭.
    LLM 미사용 — 모든 판단은 수치 규칙으로만 수행합니다.

    ⚠️ 본 서비스의 분석 결과는 투자 권유가 아닙니다.
       투자 손익의 책임은 전적으로 본인에게 있습니다.
    """
    symbol = body.symbol.upper()

    try:
        df = fetch_ohlcv(symbol, body.timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"데이터 수집 오류: {exc}")

    # ── 구간 슬라이싱 ────────────────────────────────────────────────────────
    analysis_df = df
    if body.start_time or body.end_time:
        try:
            def parse_ts(s: str) -> pd.Timestamp:
                ts = pd.Timestamp(s)
                # timezone-aware → naive 로 변환 (DataFrame 인덱스가 tz-naive)
                if ts.tzinfo is not None:
                    ts = ts.tz_convert("UTC").tz_localize(None)
                return ts

            if body.start_time:
                analysis_df = analysis_df[
                    analysis_df.index >= parse_ts(body.start_time)
                ]
            if body.end_time:
                analysis_df = analysis_df[
                    analysis_df.index <= parse_ts(body.end_time)
                ]
        except Exception as slice_exc:
            raise HTTPException(
                status_code=422,
                detail=f"잘못된 날짜/시간 형식입니다. start={body.start_time!r}, end={body.end_time!r}, error={slice_exc}",
            )

        if len(analysis_df) < MIN_CANDLES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"패턴 분석을 위해 최소 {MIN_CANDLES}개의 캔들이 필요합니다. "
                    f"현재 선택 구간: {len(analysis_df)}캔들"
                ),
            )

    try:
        results = analyze(analysis_df, top_n=3)
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
        timeframe=body.timeframe,
        analyzed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        algorithm_ref=ALGORITHM_REF,
        top_patterns=top_patterns,
    )
