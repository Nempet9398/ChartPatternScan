"""
Step 3 단위 테스트 — FastAPI TestClient 사용 (네트워크 불필요).

/api/chart, /api/analyze, /api/search 엔드포인트 검증.
fetch_ohlcv 는 합성 데이터를 반환하도록 monkeypatch.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ── 합성 OHLCV ────────────────────────────────────────────────────────────────

def _make_synthetic_df(n=180) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    t = np.linspace(0, np.pi * 2, n)
    close = 100 + 15 * np.sin(t * 0.5) + rng.normal(0, 0.5, n)
    high  = close + rng.uniform(0.5, 2, n)
    low   = close - rng.uniform(0.5, 2, n)
    open_ = close + rng.normal(0, 0.3, n)
    vol   = rng.integers(1_000_000, 5_000_000, n)
    dates = pd.date_range(end="2026-03-20", periods=n, freq="B")
    return pd.DataFrame({"Open": open_, "High": high, "Low": low,
                         "Close": close, "Volume": vol}, index=dates)

SYNTHETIC_DF = _make_synthetic_df()

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results = []

def check(label: str, condition: bool, detail: str = ""):
    verdict = PASS if condition else FAIL
    print(f"  [{verdict}] {label}" + (f" — {detail}" if detail else ""))
    results.append(condition)


# ── /api/search 테스트 (네트워크 불필요) ─────────────────────────────────────

def test_search():
    print("\n[1] GET /api/search")

    # 영문 심볼 검색
    r = client.get("/api/search?q=AAPL")
    check("status 200", r.status_code == 200)
    data = r.json()
    check("results 키 존재", "results" in data)
    symbols = [x["symbol"] for x in data["results"]]
    check("AAPL 포함", "AAPL" in symbols, str(symbols))

    # 한글 이름 검색
    r = client.get("/api/search?q=삼성")
    check("삼성 검색 status 200", r.status_code == 200)
    names = [x["name"] for x in r.json()["results"]]
    check("삼성전자 포함", any("삼성" in n for n in names), str(names))

    # 암호화폐 검색
    r = client.get("/api/search?q=BTC")
    check("BTC 검색", any(x["symbol"] == "BTC-USD" for x in r.json()["results"]))

    # 숫자 코드 → KS/KQ 제안
    r = client.get("/api/search?q=005930")
    check("005930 KS 제안", any("005930.KS" in x["symbol"] for x in r.json()["results"]))

    # 존재하지 않는 검색어
    r = client.get("/api/search?q=ZZZZNOTEXIST")
    check("없는 종목 빈 결과", r.status_code == 200 and len(r.json()["results"]) == 0)


# ── /api/chart 테스트 ─────────────────────────────────────────────────────────

def test_chart():
    print("\n[2] GET /api/chart/{symbol}")

    with patch("routers.chart.fetch_ohlcv", return_value=SYNTHETIC_DF):
        r = client.get("/api/chart/AAPL?period=3mo")
        check("status 200", r.status_code == 200)
        data = r.json()
        check("symbol 필드", data.get("symbol") == "AAPL")
        check("period 필드", data.get("period") == "3mo")
        check("ohlcv 배열", isinstance(data.get("ohlcv"), list) and len(data["ohlcv"]) > 0)

        bar = data["ohlcv"][0]
        check("ohlcv 키 구조", all(k in bar for k in ["time","open","high","low","close","volume"]),
              str(list(bar.keys())))
        check("time 날짜 형식", len(bar["time"]) == 10 and bar["time"][4] == "-")

    # 잘못된 기간
    with patch("routers.chart.fetch_ohlcv", side_effect=ValueError("지원하지 않는 기간")):
        r = client.get("/api/chart/AAPL?period=5y")
        check("잘못된 기간 422 or 404", r.status_code in (404, 422))

    # 존재하지 않는 심볼
    with patch("routers.chart.fetch_ohlcv", side_effect=ValueError("심볼 없음")):
        r = client.get("/api/chart/NOTEXIST?period=3mo")
        check("없는 심볼 404", r.status_code == 404)


# ── /api/analyze 테스트 ───────────────────────────────────────────────────────

def test_analyze():
    print("\n[3] POST /api/analyze")

    with patch("routers.pattern.fetch_ohlcv", return_value=SYNTHETIC_DF):
        r = client.post("/api/analyze", json={"symbol": "AAPL", "period": "3mo"})
        check("status 200", r.status_code == 200)
        data = r.json()
        check("symbol 필드", data.get("symbol") == "AAPL")
        check("algorithm_ref 존재", "Lo" in data.get("algorithm_ref", ""))
        check("top_patterns 배열", isinstance(data.get("top_patterns"), list))
        check("top_patterns 3개", len(data["top_patterns"]) == 3)

        p = data["top_patterns"][0]
        check("rank=1", p.get("rank") == 1)
        check("similarity 0~100", 0.0 <= p.get("similarity", -1) <= 100.0,
              str(p.get("similarity")))
        check("signal 유효값", p.get("signal") in ("bullish", "bearish", "neutral"),
              str(p.get("signal")))
        check("name_ko 존재", bool(p.get("name_ko")))
        check("historical_success_rate 존재", isinstance(p.get("historical_success_rate"), float))

        # rank 순서 검증
        sims = [x["similarity"] for x in data["top_patterns"]]
        check("유사도 내림차순", sims == sorted(sims, reverse=True), str(sims))

    # 데이터 부족 오류
    with patch("routers.pattern.fetch_ohlcv", side_effect=ValueError("데이터 부족")):
        r = client.post("/api/analyze", json={"symbol": "AAPL", "period": "1w"})
        check("데이터 부족 404", r.status_code == 404)

    # 네트워크 오류
    with patch("routers.pattern.fetch_ohlcv", side_effect=RuntimeError("타임아웃")):
        r = client.post("/api/analyze", json={"symbol": "AAPL", "period": "3mo"})
        check("네트워크 오류 502", r.status_code == 502)


# ── 루트 엔드포인트 ───────────────────────────────────────────────────────────

def test_root():
    print("\n[4] GET /")
    r = client.get("/")
    check("status 200", r.status_code == 200)
    check("service 키", "service" in r.json())
    check("algorithm_ref 키", "algorithm_ref" in r.json())


# ── 실행 ─────────────────────────────────────────────────────────────────────

def main():
    print("=== Step 3: FastAPI 엔드포인트 단위 테스트 ===")
    test_root()
    test_search()
    test_chart()
    test_analyze()

    total  = len(results)
    passed = sum(results)
    failed = total - passed
    print(f"\n{'='*50}")
    print(f"결과: {passed}/{total} PASS  ({failed} FAIL)")
    if failed:
        print("일부 테스트가 실패했습니다. 위 로그를 확인하세요.")
        sys.exit(1)
    else:
        print("모든 테스트 통과 ✓")
    print("=== Step 3 완료 ===")


if __name__ == "__main__":
    main()
