"""
Step 2 검증 스크립트.

각 패턴에 맞는 합성 OHLCV 데이터를 생성해 similarity score 검증.
기대: 해당 패턴이 들어있는 데이터는 다른 패턴보다 높은 점수를 받아야 함.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

from services.pattern_engine import analyze, ALL_PATTERNS
from services.data_fetcher import MIN_TRADING_DAYS


# ─── 합성 데이터 생성 헬퍼 ────────────────────────────────────────────────────

def _make_df(close: np.ndarray, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(close)
    noise = rng.normal(0, close.std() * 0.01, n)
    c = close + noise
    h = c + rng.uniform(0.5, 1.5, n)
    l = c - rng.uniform(0.5, 1.5, n)
    o = c + rng.normal(0, 0.3, n)
    v = rng.integers(1_000_000, 5_000_000, n)
    dates = pd.date_range(end="2026-03-20", periods=n, freq="B")
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}, index=dates)


def make_head_and_shoulders(n=180) -> pd.DataFrame:
    """뚜렷한 H&S: 좌어깨(10) → 넥라인(7) → 머리(14) → 넥라인(7) → 우어깨(10)"""
    t = np.linspace(0, np.pi * 2, n)
    base = 100 + 10 * np.sin(t * 0.5)          # 완만한 기저
    left_shoulder  = 10 * np.exp(-((t - 1.5)**2) / 0.08)
    head           = 14 * np.exp(-((t - np.pi)**2) / 0.08)
    right_shoulder = 10 * np.exp(-((t - 4.8)**2) / 0.08)
    close = base + left_shoulder + head + right_shoulder
    return _make_df(close)


def make_inverse_hs(n=180) -> pd.DataFrame:
    """역H&S: H&S 상하 반전"""
    df = make_head_and_shoulders(n)
    df["Close"] = df["Close"].max() + df["Close"].min() - df["Close"]
    df["High"]  = df["Close"] + 1.0
    df["Low"]   = df["Close"] - 1.0
    return df


def make_double_top(n=180) -> pd.DataFrame:
    """더블탑: 두 고점이 비슷한 높이, 충분한 간격"""
    t = np.linspace(0, np.pi * 2, n)
    p1 = int(n * 0.30)
    p2 = int(n * 0.70)
    close = np.full(n, 100.0)
    # 두 피크를 가우시안으로
    for i in range(n):
        close[i] = (100
                    + 15 * np.exp(-((i - p1)**2) / (2 * 10**2))
                    + 15 * np.exp(-((i - p2)**2) / (2 * 10**2)))
    return _make_df(close)


def make_double_bottom(n=180) -> pd.DataFrame:
    """더블바텀: 더블탑 상하 반전"""
    df = make_double_top(n)
    df["Close"] = df["Close"].max() + df["Close"].min() - df["Close"]
    df["High"]  = df["Close"] + 1.0
    df["Low"]   = df["Close"] - 1.0
    return df


def make_golden_cross(n=180) -> pd.DataFrame:
    """골든크로스: MA20이 MA60을 최근에 상향 돌파"""
    # 앞부분 하락, 최근 상승 → MA20이 MA60 위로
    t = np.linspace(0, 1, n)
    close = 100 - 10 * t + 20 * (t > 0.75) * (t - 0.75) * 4
    return _make_df(close)


def make_dead_cross(n=180) -> pd.DataFrame:
    """데드크로스: MA20이 MA60을 최근에 하향 돌파"""
    t = np.linspace(0, 1, n)
    close = 100 + 10 * t - 20 * (t > 0.75) * (t - 0.75) * 4
    return _make_df(close)


def make_symmetrical_triangle(n=180) -> pd.DataFrame:
    """대칭 삼각수렴: 고점 하향 + 저점 상향"""
    t = np.linspace(0, 1, n)
    envelope = 15 * (1 - t)           # 진폭 축소
    osc = envelope * np.sin(t * np.pi * 6)
    close = 100 + osc
    return _make_df(close)


def make_ascending_triangle(n=180) -> pd.DataFrame:
    """상승 삼각수렴: 고점 수평 + 저점 상향"""
    t = np.linspace(0, 1, n)
    upper_flat = 115.0
    lower_rising = 95 + 10 * t
    # 가격: 두 경계 사이에서 진동하되 상단은 flat
    osc = np.sin(t * np.pi * 5)
    mid = (upper_flat + lower_rising) / 2
    amp = (upper_flat - lower_rising) / 2
    close = mid + amp * osc
    return _make_df(close)


def make_descending_triangle(n=180) -> pd.DataFrame:
    """하락 삼각수렴: 고점 하향 + 저점 수평"""
    t = np.linspace(0, 1, n)
    lower_flat  = 85.0
    upper_falling = 115 - 10 * t
    osc = np.sin(t * np.pi * 5)
    mid = (upper_falling + lower_flat) / 2
    amp = (upper_falling - lower_flat) / 2
    close = mid + amp * osc
    return _make_df(close)


# ─── 검증 실행 ────────────────────────────────────────────────────────────────

TESTS = [
    ("HeadAndShoulders",        make_head_and_shoulders,    "Head and Shoulders"),
    ("InverseHeadAndShoulders", make_inverse_hs,            "Inverse Head and Shoulders"),
    ("DoubleTop",               make_double_top,            "Double Top"),
    ("DoubleBottom",            make_double_bottom,         "Double Bottom"),
    ("GoldenCross",             make_golden_cross,          "Golden Cross"),
    ("DeadCross",               make_dead_cross,            "Dead Cross"),
    ("SymmetricalTriangle",     make_symmetrical_triangle,  "Symmetrical Triangle"),
    ("AscendingTriangle",       make_ascending_triangle,    "Ascending Triangle"),
    ("DescendingTriangle",      make_descending_triangle,   "Descending Triangle"),
]


def main():
    print("=== Step 2: 패턴 엔진 검증 ===\n")
    print(f"{'케이스':<28} {'Top1 패턴':<32} {'Top1 점수':>9}  {'기대 패턴 점수':>14}  {'판정'}")
    print("-" * 100)

    pass_count = 0
    for label, make_fn, expected_name in TESTS:
        df = make_fn()
        top3 = analyze(df, top_n=3)

        top1 = top3[0]

        # 기대 패턴이 Top3 안에 있는지 확인
        expected_score = next((r.similarity for r in top3 if r.name == expected_name), None)
        if expected_score is None:
            # Top3 밖에 있으면 전체 실행해서 찾기
            from services.pattern_engine import ALL_PATTERNS
            for p in ALL_PATTERNS:
                if p.name == expected_name:
                    r = p.calculate_similarity(df)
                    expected_score = r.similarity
                    break

        in_top3 = any(r.name == expected_name for r in top3)
        is_top1 = top1.name == expected_name
        verdict = "PASS" if in_top3 else "WARN"
        if in_top3:
            pass_count += 1

        marker = "✓" if is_top1 else ("△" if in_top3 else "✗")
        print(f"{label:<28} {top1.name:<32} {top1.similarity:>9.1f}  {expected_score or 0:>14.1f}  {marker} {verdict}")

    print("-" * 100)
    print(f"\n결과: {pass_count}/{len(TESTS)} 패턴이 Top3 이내 탐지\n")

    # Top3 상세 출력
    print("=== 각 케이스 Top3 상세 ===\n")
    for label, make_fn, expected_name in TESTS:
        df = make_fn()
        top3 = analyze(df, top_n=3)
        print(f"[{label}]")
        for rank, r in enumerate(top3, 1):
            marker = "★" if r.name == expected_name else " "
            print(f"  {rank}. {marker}{r.name_ko} ({r.name})  {r.similarity:.1f}점  [{r.signal}]")
        print()

    print("=== Step 2 완료 ===")


if __name__ == "__main__":
    main()
