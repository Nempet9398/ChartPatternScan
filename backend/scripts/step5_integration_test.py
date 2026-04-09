"""
Step 5 통합 테스트 — FastAPI TestClient 기반.

외부 네트워크 없이 in-process HTTP 시뮬레이션으로 전체 흐름을 검증한다.
fetch_ohlcv 는 unittest.mock 으로 합성 데이터를 주입해 테스트한다.

검증 항목:
  [1] 헬스체크      GET /
  [2] 검색          GET /api/search
  [3] 차트          GET /api/chart/{symbol}  (mock)
  [4] 패턴 분석     POST /api/analyze        (mock)
  [5] 에러 처리     404 / 405 / 422
  [6] CORS 헤더     Origin 헤더 포함 요청
  [7] 비즈니스 규칙  유사도 내림차순 / rank 순서 / signal 유효값
  [8] pattern_geometry 구조 및 좌표 유효성 (18패턴 전체)
"""

import sys
import os
import time
import unittest.mock
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from main import app
import routers.pattern as pattern_router
import routers.chart    as chart_router

client = TestClient(app, raise_server_exceptions=False)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"

results: list[bool] = []

ALL_PATTERN_NAMES = [
    "Head and Shoulders",
    "Inverse Head and Shoulders",
    "Double Top",
    "Double Bottom",
    "Golden Cross",
    "Dead Cross",
    "Symmetrical Triangle",
    "Ascending Triangle",
    "Descending Triangle",
    "Triple Top",
    "Triple Bottom",
    "Rectangle",
    "Rising Wedge",
    "Falling Wedge",
    "Bull Flag",
    "Bear Flag",
    "Bull Pennant",
    "Bear Pennant",
]


def check(label: str, cond: bool, detail: str = ""):
    verdict = PASS if cond else FAIL
    print(f"  [{verdict}] {label}" + (f"  ({detail})" if detail else ""))
    results.append(cond)


def make_synthetic_df(n: int = 120, seed: int = 42) -> pd.DataFrame:
    """120거래일 합성 OHLCV — 골든크로스 / 깃발 패턴 유도."""
    np.random.seed(seed)
    dates = pd.date_range("2024-01-02", periods=n, freq="B")
    price = 70000.0
    closes = []
    for i in range(n):
        if i < 40:
            price += np.random.randn() * 300 - 200
        elif i < 60:
            price += np.random.randn() * 300
        else:
            price += np.random.randn() * 300 + 150
        closes.append(max(price, 50000))
    closes = np.array(closes)
    return pd.DataFrame(
        {
            "Open":   closes * 0.99,
            "High":   closes * 1.01,
            "Low":    closes * 0.98,
            "Close":  closes,
            "Volume": np.random.randint(10_000_000, 50_000_000, n).astype(float),
        },
        index=dates,
    )


SYNTHETIC_DF = make_synthetic_df()


# ─── 테스트 함수 ──────────────────────────────────────────────────────────────

def test_healthcheck():
    print("\n[1] 헬스체크  GET /")
    resp = client.get("/")
    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("service 키 존재", "service" in body)
    check("algorithm_ref Lo(2000) 포함", "Lo" in body.get("algorithm_ref", ""))


def test_search():
    print("\n[2] GET /api/search")

    resp = client.get("/api/search?q=AAPL")
    check("status 200", resp.status_code == 200)
    symbols = [r["symbol"] for r in resp.json().get("results", [])]
    check("AAPL 포함", "AAPL" in symbols, str(symbols))

    resp = client.get("/api/search?q=삼성")
    check("삼성 status 200", resp.status_code == 200)
    check("삼성전자 포함",
          any("삼성" in r["name"] for r in resp.json().get("results", [])))

    resp = client.get("/api/search?q=bitcoin")
    check("bitcoin → BTC-USD 포함",
          any(r["symbol"] == "BTC-USD" for r in resp.json().get("results", [])))

    resp = client.get("/api/search?q=XYZNOTEXIST")
    check("없는 종목 빈 결과", len(resp.json().get("results", [])) == 0)

    resp = client.get("/api/search")          # q 파라미터 누락
    check("q 없음 → 422", resp.status_code == 422)


def test_chart():
    print("\n[3] GET /api/chart/{symbol}  (mock)")
    with unittest.mock.patch.object(chart_router, "fetch_ohlcv", return_value=SYNTHETIC_DF):
        resp = client.get("/api/chart/SYNTHETIC?period=3mo")

    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("ohlcv 배열 존재", isinstance(body.get("ohlcv"), list))
    check("ohlcv 비어있지 않음", len(body.get("ohlcv", [])) > 0)
    if body.get("ohlcv"):
        bar = body["ohlcv"][0]
        check("ohlcv 키 구조",
              all(k in bar for k in ["time", "open", "high", "low", "close", "volume"]))
        check("close 값 양수", bar["close"] > 0, str(bar["close"]))

    resp = client.get("/api/chart/AAPL?timeframe=10y")  # 허용 목록 외 값
    check("잘못된 timeframe → 422", resp.status_code == 422)


def test_analyze():
    print("\n[4] POST /api/analyze  (mock)")
    with unittest.mock.patch.object(pattern_router, "fetch_ohlcv", return_value=SYNTHETIC_DF):
        t0 = time.time()
        resp = client.post("/api/analyze",
                           json={"symbol": "SYNTHETIC", "period": "3mo"})
        elapsed = time.time() - t0

    check("status 200", resp.status_code == 200, resp.text[:100])
    body = resp.json()
    pats = body.get("top_patterns", [])
    check("top_patterns 3개", len(pats) == 3, str(len(pats)))
    check("rank 1·2·3 순서",
          [p["rank"] for p in pats] == [1, 2, 3])
    check("유사도 내림차순",
          [p["similarity"] for p in pats] == sorted([p["similarity"] for p in pats], reverse=True))

    p = pats[0]
    check("similarity 0~100", 0 <= p.get("similarity", -1) <= 100)
    check("signal 유효값", p.get("signal") in ("bullish", "bearish", "neutral"))
    check("name_ko 존재", bool(p.get("name_ko")))
    check("historical_success_rate 존재", p.get("historical_success_rate") is not None)
    check("algorithm_ref Lo(2000) 포함", "Lo" in body.get("algorithm_ref", ""))
    check("응답 시간 3초 이내", elapsed < 3.0, f"{elapsed:.2f}s")

    # 빈 body → 422
    resp = client.post("/api/analyze", json={})
    check("빈 body → 422", resp.status_code == 422)


def test_errors():
    print("\n[5] 에러 처리")
    resp = client.get("/api/notexist")
    check("없는 엔드포인트 → 404", resp.status_code == 404)

    resp = client.get("/api/analyze")
    check("GET /api/analyze → 405", resp.status_code == 405)

    # 60캔들 미만 구간 → 422
    with unittest.mock.patch.object(pattern_router, "fetch_ohlcv", return_value=SYNTHETIC_DF):
        resp = client.post("/api/analyze", json={
            "symbol": "SYNTHETIC",
            "period": "3mo",
            "start_time": "2024-01-02",
            "end_time":   "2024-01-20",   # 약 13거래일
        })
    check("60캔들 미만 → 422", resp.status_code == 422, str(resp.status_code))


def test_cors():
    print("\n[6] CORS 헤더")
    resp = client.get(
        "/api/search?q=AAPL",
        headers={"Origin": "http://localhost:3000"},
    )
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    check("CORS Allow-Origin 헤더 존재", bool(allow_origin),
          allow_origin or "헤더 없음")

    # Vercel preview URL
    resp = client.get(
        "/api/search?q=AAPL",
        headers={"Origin": "https://chartpattern-abc123.vercel.app"},
    )
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    check("Vercel preview URL CORS 허용", bool(allow_origin),
          allow_origin or "헤더 없음")


def test_geometry():
    print("\n[7+8] 패턴 엔진 18개 등록 + pattern_geometry 구조 검증")

    # 패턴 18개 등록 확인
    from services.pattern_engine import ALL_PATTERNS
    check("패턴 엔진 18개 등록", len(ALL_PATTERNS) == 18, f"현재 {len(ALL_PATTERNS)}개")

    # 각 패턴명이 허용 목록 안에 있는지
    registered_names = {p.name for p in ALL_PATTERNS}
    for name in ALL_PATTERN_NAMES:
        check(f"  패턴 등록 확인: {name}", name in registered_names)

    # 합성 데이터로 analyze 실행
    with unittest.mock.patch.object(pattern_router, "fetch_ohlcv", return_value=SYNTHETIC_DF):
        resp = client.post("/api/analyze",
                           json={"symbol": "SYNTHETIC", "period": "3mo"})

    check("geometry 테스트 status 200", resp.status_code == 200)
    if resp.status_code != 200:
        return

    pats = resp.json().get("top_patterns", [])

    # 적어도 1개 geometry non-null
    geo_count = sum(1 for p in pats if p.get("pattern_geometry") is not None)
    check(f"pattern_geometry 1개 이상 non-null", geo_count >= 1,
          f"{geo_count}/{len(pats)} non-null")

    # 각 패턴 geometry 상세 검증
    for p in pats:
        geo  = p.get("pattern_geometry")
        name = p["name"]

        if geo is None:
            print(f"  [{SKIP}] {name} — geometry null (유사도 {p['similarity']:.0f}%)")
            continue

        check(f"[{name}] 최상위 키 존재",
              all(k in geo for k in ("points", "lines", "levels")))

        for pt in geo.get("points", []):
            check(f"[{name}] point 키 완전",
                  all(k in pt for k in ("label", "date", "value")), str(pt))
            check(f"[{name}] point.value 양수",
                  isinstance(pt["value"], (int, float)) and pt["value"] > 0,
                  str(pt["value"]))
            check(f"[{name}] point.date ISO 형식",
                  isinstance(pt["date"], str) and len(pt["date"]) == 10,
                  pt["date"])

        for ln in geo.get("lines", []):
            check(f"[{name}] line 키 완전",
                  all(k in ln for k in ("type", "x1", "y1", "x2", "y2", "color", "style")),
                  str(list(ln.keys())))
            check(f"[{name}] line y1/y2 양수 (실제 가격)",
                  ln["y1"] > 0 and ln["y2"] > 0,
                  f"y1={ln['y1']:.1f} y2={ln['y2']:.1f}")
            check(f"[{name}] line style 유효",
                  ln["style"] in ("solid", "dashed", "dotted"), ln["style"])

        for lv in geo.get("levels", []):
            check(f"[{name}] level 키 완전",
                  all(k in lv for k in ("type", "value", "color")), str(lv))
            check(f"[{name}] level.value 양수",
                  isinstance(lv["value"], (int, float)) and lv["value"] > 0,
                  str(lv["value"]))


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    print("=== Step 5: 통합 테스트 (TestClient) ===\n")

    test_healthcheck()
    test_search()
    test_chart()
    test_analyze()
    test_errors()
    test_cors()
    test_geometry()

    total  = len(results)
    passed = sum(results)
    failed = total - passed
    print(f"\n{'='*55}")
    print(f"통합 테스트 결과: {passed}/{total} PASS  ({failed} FAIL)")
    if failed:
        print("일부 테스트 실패 — 위 로그 확인")
        sys.exit(1)
    else:
        print("모든 통합 테스트 통과 ✓")
    print("=== Step 5 완료 ===")


if __name__ == "__main__":
    main()
