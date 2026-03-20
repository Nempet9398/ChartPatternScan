"""
GET /api/search?q={query}

종목명 / 심볼 검색 → 자동완성용 결과 반환.

구현 전략:
  1. 로컬 정적 딕셔너리(인기 종목)에서 먼저 검색 — 오프라인/빠른 응답
  2. 쿼리가 숫자로만 이루어진 경우 KS/KQ suffix 자동 제안
  3. 암호화폐: BTC/ETH/XRP 등 정적 목록
"""

from __future__ import annotations

import re
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


# ── 정적 종목 목록 ─────────────────────────────────────────────────────────────
#    실제 서비스에서는 별도 DB/파일로 관리 권장

_STOCK_DB: list[dict] = [
    # 미국 주식
    {"symbol": "AAPL",   "name": "Apple Inc.",              "market": "NASDAQ"},
    {"symbol": "MSFT",   "name": "Microsoft Corp.",          "market": "NASDAQ"},
    {"symbol": "GOOGL",  "name": "Alphabet Inc.",            "market": "NASDAQ"},
    {"symbol": "AMZN",   "name": "Amazon.com Inc.",          "market": "NASDAQ"},
    {"symbol": "NVDA",   "name": "NVIDIA Corp.",             "market": "NASDAQ"},
    {"symbol": "META",   "name": "Meta Platforms Inc.",      "market": "NASDAQ"},
    {"symbol": "TSLA",   "name": "Tesla Inc.",               "market": "NASDAQ"},
    {"symbol": "JPM",    "name": "JPMorgan Chase & Co.",     "market": "NYSE"},
    {"symbol": "V",      "name": "Visa Inc.",                "market": "NYSE"},
    {"symbol": "JNJ",    "name": "Johnson & Johnson",        "market": "NYSE"},
    {"symbol": "WMT",    "name": "Walmart Inc.",             "market": "NYSE"},
    {"symbol": "DIS",    "name": "Walt Disney Co.",          "market": "NYSE"},
    {"symbol": "NFLX",   "name": "Netflix Inc.",             "market": "NASDAQ"},
    {"symbol": "AMD",    "name": "Advanced Micro Devices",   "market": "NASDAQ"},
    {"symbol": "INTC",   "name": "Intel Corp.",              "market": "NASDAQ"},
    {"symbol": "PYPL",   "name": "PayPal Holdings Inc.",     "market": "NASDAQ"},
    {"symbol": "UBER",   "name": "Uber Technologies Inc.",   "market": "NYSE"},
    {"symbol": "BABA",   "name": "Alibaba Group",            "market": "NYSE"},
    {"symbol": "SPY",    "name": "SPDR S&P 500 ETF",         "market": "ETF"},
    {"symbol": "QQQ",    "name": "Invesco QQQ Trust",        "market": "ETF"},
    # 한국 주식 (KOSPI)
    {"symbol": "005930.KS", "name": "삼성전자",              "market": "KOSPI"},
    {"symbol": "000660.KS", "name": "SK하이닉스",            "market": "KOSPI"},
    {"symbol": "005380.KS", "name": "현대자동차",            "market": "KOSPI"},
    {"symbol": "035420.KS", "name": "NAVER",                 "market": "KOSPI"},
    {"symbol": "051910.KS", "name": "LG화학",                "market": "KOSPI"},
    {"symbol": "006400.KS", "name": "삼성SDI",               "market": "KOSPI"},
    {"symbol": "068270.KS", "name": "셀트리온",              "market": "KOSPI"},
    {"symbol": "105560.KS", "name": "KB금융",                "market": "KOSPI"},
    {"symbol": "055550.KS", "name": "신한지주",              "market": "KOSPI"},
    {"symbol": "003550.KS", "name": "LG",                    "market": "KOSPI"},
    # 한국 주식 (KOSDAQ)
    {"symbol": "035720.KQ", "name": "카카오",                "market": "KOSDAQ"},
    {"symbol": "247540.KQ", "name": "에코프로비엠",          "market": "KOSDAQ"},
    {"symbol": "086900.KQ", "name": "메디오젠",              "market": "KOSDAQ"},
    {"symbol": "039030.KQ", "name": "이오테크닉스",          "market": "KOSDAQ"},
    # 암호화폐
    {"symbol": "BTC-USD",  "name": "Bitcoin",                "market": "Crypto"},
    {"symbol": "ETH-USD",  "name": "Ethereum",               "market": "Crypto"},
    {"symbol": "BNB-USD",  "name": "BNB",                    "market": "Crypto"},
    {"symbol": "XRP-USD",  "name": "XRP",                    "market": "Crypto"},
    {"symbol": "SOL-USD",  "name": "Solana",                 "market": "Crypto"},
    {"symbol": "ADA-USD",  "name": "Cardano",                "market": "Crypto"},
    {"symbol": "DOGE-USD", "name": "Dogecoin",               "market": "Crypto"},
]


class SearchResult(BaseModel):
    symbol: str
    name:   str
    market: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


@router.get("/search", response_model=SearchResponse, summary="종목 검색 (자동완성)")
def get_search(
    q: str = Query(..., min_length=1, description="검색어 (종목명 또는 심볼)"),
):
    """
    종목명 또는 심볼 코드로 검색합니다.

    - 대소문자 무관
    - 부분 일치 지원
    - 최대 10개 반환
    """
    q_lower = q.lower().strip()
    matches: list[dict] = []

    for item in _STOCK_DB:
        sym_lower  = item["symbol"].lower()
        name_lower = item["name"].lower()
        if q_lower in sym_lower or q_lower in name_lower:
            matches.append(item)

    # 한국 종목코드 숫자만 입력한 경우 (예: "005930") KS/KQ 자동 제안
    if re.fullmatch(r"\d{5,6}", q.strip()):
        code = q.strip()
        for suffix, market in [(".KS", "KOSPI"), (".KQ", "KOSDAQ")]:
            candidate = {"symbol": code + suffix, "name": f"{code}{suffix}", "market": market}
            if not any(m["symbol"] == candidate["symbol"] for m in matches):
                matches.append(candidate)

    return SearchResponse(
        results=[SearchResult(**m) for m in matches[:10]]
    )
