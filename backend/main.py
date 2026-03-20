"""
ChartPattern.io — FastAPI 메인 애플리케이션.

실행:
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chart, pattern, search

app = FastAPI(
    title="ChartPattern.io API",
    description=(
        "Rule-based chart pattern similarity analyzer. "
        "Algorithm: Lo, Mamaysky & Wang (2000) Journal of Finance."
    ),
    version="0.1.0",
)

# CORS — 개발: localhost, 배포: Vercel 도메인 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
        "https://chartpattern.io",
    ],
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
