"""
ChartPattern.io — FastAPI 메인 애플리케이션.

실행:
  uvicorn main:app --reload --port 8000

환경변수 (선택):
  ALLOWED_ORIGINS  콤마 구분 허용 오리진 (기본: localhost:3000)
                   예) https://chartpattern.io,https://my-app.vercel.app
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chart, pattern, search

# ALLOWED_ORIGINS 환경변수로 CORS 도메인 제어 (Railway 배포 시 설정)
_default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://*.vercel.app",
    "https://chartpattern.io",
]
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else _default_origins
)

app = FastAPI(
    title="ChartPattern.io API",
    description=(
        "Rule-based chart pattern similarity analyzer. "
        "Algorithm: Lo, Mamaysky & Wang (2000) Journal of Finance."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Vercel 프리뷰 URL 전체 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chart.router,   prefix="/api")
app.include_router(pattern.router, prefix="/api")
app.include_router(search.router,  prefix="/api")


@app.get("/")
def root():
    return {
        "service": "ChartPattern.io API",
        "docs": "/docs",
        "algorithm_ref": "Lo, Mamaysky & Wang (2000), Journal of Finance Vol.55 No.4",
    }
