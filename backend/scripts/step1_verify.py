"""
Step 1 검증 스크립트.

네트워크가 없는 환경에서는 합성 OHLCV 데이터로 전처리 로직을 검증합니다.

1. 합성 AAPL-like OHLCV 생성 (헤드앤숄더 패턴 포함)
2. preprocessor.py 실행 → 극값 탐지
3. matplotlib으로 시각화 → step1_result.png 저장
"""

import sys
import os

# backend/ 를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")   # GUI 없는 환경
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import numpy as np
import pandas as pd

from patterns.preprocessor import preprocess


def make_synthetic_ohlcv(n_days: int = 180, seed: int = 42) -> pd.DataFrame:
    """
    헤드앤숄더 형태가 포함된 합성 OHLCV 생성.

    가격 경로:
      0~30일  : 완만한 상승 (좌측 어깨 전)
      30~60일 : 고점 형성 (좌측 어깨)
      60~90일 : 하락 (넥라인)
      90~120일: 더 높은 고점 (머리)
      120~150일: 하락 (넥라인)
      150~180일: 중간 고점 후 하락 (우측 어깨 + 이탈)
    """
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 1, n_days)

    # 헤드앤숄더 기저 가격 (정규화 편의상 100 기준)
    base = (
        100
        + 10 * np.sin(np.pi * t * 2)           # 좌어깨
        + 15 * np.exp(-((t - 0.55) ** 2) / 0.005)  # 머리
        + 8  * np.sin(np.pi * (t - 0.1) * 2) * (t > 0.6)  # 우어깨
        - 12 * t                                 # 전체 완만한 하락 추세
    )

    noise = rng.normal(0, 0.5, n_days)
    close = base + noise

    high  = close + rng.uniform(0.5, 2.0, n_days)
    low   = close - rng.uniform(0.5, 2.0, n_days)
    open_ = close + rng.normal(0, 0.3, n_days)
    volume = rng.integers(1_000_000, 5_000_000, n_days)

    dates = pd.date_range(end="2026-03-20", periods=n_days, freq="B")  # 영업일

    df = pd.DataFrame({
        "Open":   open_,
        "High":   high,
        "Low":    low,
        "Close":  close,
        "Volume": volume,
    }, index=dates)

    return df


def main():
    print("=== Step 1: 전처리 + 극값 탐지 검증 (합성 데이터) ===\n")

    # 1) 합성 OHLCV 생성
    print("[1] 합성 OHLCV 데이터 생성 중... (헤드앤숄더 패턴 포함)")
    df = make_synthetic_ohlcv(n_days=180)
    print(f"    → {len(df)}거래일 생성 ({df.index[0].date()} ~ {df.index[-1].date()})")
    print(f"    Close 최솟값: {df['Close'].min():.2f}  최댓값: {df['Close'].max():.2f}\n")

    # 2) 전처리 + 극값 탐지
    print("[2] 전처리 (MA5 스무딩 + 극값 탐지) 실행 중...")
    result = preprocess(df)

    peaks   = result["peaks"]
    troughs = result["troughs"]
    dates   = result["dates"]
    norm    = result["normalized"]
    smoothed = result["smoothed"]

    print(f"    → 피크(고점) 수: {len(peaks)}")
    print(f"    → 트로프(저점) 수: {len(troughs)}")

    peak_dates   = dates[peaks]
    trough_dates = dates[troughs]
    print(f"\n    피크 날짜: {[str(d.date()) for d in peak_dates]}")
    print(f"    트로프 날짜: {[str(d.date()) for d in trough_dates]}\n")

    # 3) 시각화
    print("[3] 시각화 생성 중...")
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # 상단: 원본 종가 + 스무딩 + 극값
    ax1 = axes[0]
    ax1.plot(df.index, df["Close"], color="#aaaaaa", linewidth=0.8, label="Close (원본)")
    ax1.plot(smoothed.index, smoothed, color="#2196F3", linewidth=1.5, label="MA5 (스무딩)")
    ax1.scatter(dates[peaks],   smoothed.values[peaks],
                color="red",   zorder=5, s=80, label="Peak (고점)", marker="^")
    ax1.scatter(dates[troughs], smoothed.values[troughs],
                color="green", zorder=5, s=80, label="Trough (저점)", marker="v")
    ax1.set_title("합성 OHLCV — 원본 종가 + MA5 스무딩 + 극값 탐지 (Lo 2000)", fontsize=13)
    ax1.set_ylabel("Price")
    ax1.legend(fontsize=9)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.grid(alpha=0.3)

    # 하단: 정규화된 값 + 극값
    ax2 = axes[1]
    ax2.plot(dates, norm, color="#FF9800", linewidth=1.2, label="Normalized (0~1)")
    ax2.scatter(dates[peaks],   norm.values[peaks],
                color="red",   zorder=5, s=80, marker="^")
    ax2.scatter(dates[troughs], norm.values[troughs],
                color="green", zorder=5, s=80, marker="v")
    ax2.axhline(y=0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax2.set_title("Min-Max 정규화 + 극값 (피크=빨강△, 트로프=초록▽)", fontsize=13)
    ax2.set_ylabel("Normalized Price")
    ax2.set_xlabel("Date")
    ax2.legend(fontsize=9)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(os.path.dirname(__file__), "step1_result.png")
    plt.savefig(out_path, dpi=120)
    print(f"    → 시각화 저장: {out_path}")

    # 4) 전처리 결과 요약
    print("\n[4] 전처리 결과 요약:")
    print(f"    smoothed 길이: {len(smoothed)} (원본 {len(df)}에서 MA5 적용)")
    print(f"    normalized 범위: [{norm.min():.4f}, {norm.max():.4f}]")
    for i, (p, v) in enumerate(zip(dates[peaks], norm.values[peaks])):
        print(f"    Peak {i+1}: {p.date()} (정규화값={v:.3f})")
    for i, (t, v) in enumerate(zip(dates[troughs], norm.values[troughs])):
        print(f"    Trough {i+1}: {t.date()} (정규화값={v:.3f})")

    print("\n=== Step 1 완료 ✓ ===")
    print("    preprocessor.py 정상 동작 확인")
    print("    다음: Step 2 — 패턴 엔진 구현 (GoldenCross → DoubleTop → HeadAndShoulders → Triangle)")


if __name__ == "__main__":
    main()
