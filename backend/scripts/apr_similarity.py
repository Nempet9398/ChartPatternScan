"""
에이피알(278470.KS) 15분봉 유사일 탐색기
=========================================
사용법:
  # 1) 데이터 수집 (최초 또는 매일 장 마감 후 실행)
  python apr_similarity.py collect

  # 2) 특정 날짜와 가장 유사한 날 찾기
  python apr_similarity.py find 2026-04-08

  # 3) 저장된 날짜 목록 확인
  python apr_similarity.py dates

저장 위치: backend/data/apr_15m.csv
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

# ── 설정 ────────────────────────────────────────────────────────────────────
SYMBOL = "278470.KS"           # 에이피알 KOSPI
DB_PATH = Path(__file__).parent.parent / "data" / "apr_15m.csv"
MIN_CANDLES_PER_DAY = 20       # 유효 거래일 최소 캔들 수 (전체 26개 중)
TOP_N = 5                      # 출력할 유사일 수


# ── 데이터 저장/로드 ─────────────────────────────────────────────────────────

def _load_stored() -> pd.DataFrame:
    """저장된 전체 15분봉 데이터 로드."""
    if not DB_PATH.exists():
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "date"])
    df = pd.read_csv(DB_PATH, parse_dates=["datetime"])
    return df


def _save(df: pd.DataFrame):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DB_PATH, index=False)


def collect(bootstrap: bool = False):
    """
    yfinance에서 에이피알 15분봉 데이터를 가져와 누적 저장.
    bootstrap=True 이면 최대 60일치 (약 1,560캔들) 요청.
    """
    limit = 2000 if bootstrap else 672   # 672 ≈ 7일 × 96캔들

    print(f"[수집] {SYMBOL} 15분봉 fetch 중 (limit={limit}) ...")
    try:
        ticker = yf.Ticker(SYMBOL)
        # yfinance 15분봉은 period 파라미터로 최대 60d
        period = "60d" if bootstrap else "7d"
        raw = ticker.history(period=period, interval="15m", auto_adjust=True)
    except Exception as e:
        print(f"[오류] yfinance 접속 실패: {e}")
        sys.exit(1)

    if raw is None or raw.empty:
        print("[오류] 데이터 없음 — 심볼을 확인하세요.")
        sys.exit(1)

    raw = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    raw.index = pd.to_datetime(raw.index)

    # KST 시간이 tz-aware로 오면 naive로 변환
    if raw.index.tz is not None:
        raw.index = raw.index.tz_convert("Asia/Seoul").tz_localize(None)

    new_df = pd.DataFrame({
        "datetime": raw.index,
        "open":     raw["Open"].values,
        "high":     raw["High"].values,
        "low":      raw["Low"].values,
        "close":    raw["Close"].values,
        "volume":   raw["Volume"].values.astype(int),
        "date":     [str(t.date()) for t in raw.index],
    })

    # 기존 데이터와 합치고 중복 제거 (datetime 기준)
    existing = _load_stored()
    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["datetime"]).sort_values("datetime")
    _save(combined)

    new_rows = len(combined) - len(existing)
    dates = combined["date"].nunique()
    print(f"[완료] 새 캔들: {new_rows}개 | 전체 저장: {len(combined)}캔들 ({dates}거래일)")


# ── 유사도 계산 ──────────────────────────────────────────────────────────────

def _returns(day_df: pd.DataFrame) -> np.ndarray:
    """15분봉 수익률 시퀀스 계산."""
    closes = day_df["close"].values
    opens  = day_df["open"].values
    ret = np.empty(len(closes))
    ret[0] = (closes[0] - opens[0]) / (opens[0] + 1e-10)    # 첫봉: 시가→종가
    ret[1:] = np.diff(closes) / (closes[:-1] + 1e-10)        # 이후: 전봉 종가 대비
    return ret


def _pearson_score(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson 상관계수 → 0~100점으로 변환."""
    n = min(len(a), len(b))
    if n < 5:
        return 0.0
    r = np.corrcoef(a[:n], b[:n])[0, 1]
    if np.isnan(r):
        return 0.0
    return round((r + 1) / 2 * 100, 1)


def find_similar(query_date: str, top_n: int = TOP_N):
    """
    query_date와 가장 유사한 거래일 top_n개를 출력.
    """
    all_df = _load_stored()
    if all_df.empty:
        print("[오류] 저장된 데이터 없음 — 먼저 'collect' 실행하세요.")
        sys.exit(1)

    # 날짜별 그룹
    groups = {
        date: group.sort_values("datetime").reset_index(drop=True)
        for date, group in all_df.groupby("date")
        if len(group) >= MIN_CANDLES_PER_DAY
    }

    if query_date not in groups:
        available = sorted(groups.keys())
        print(f"[오류] '{query_date}' 날짜 데이터 없음.")
        print(f"      사용 가능한 날짜: {available[0]} ~ {available[-1]} ({len(available)}일)")
        sys.exit(1)

    query_ret = _returns(groups[query_date])

    candidates = {
        date: _pearson_score(query_ret, _returns(df))
        for date, df in groups.items()
        if date != query_date
    }

    if not candidates:
        print("[오류] 비교할 다른 날짜가 없습니다. 더 많은 데이터를 수집하세요.")
        sys.exit(1)

    ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:top_n]

    print(f"\n── 기준일: {query_date} ──────────────────────────────")
    print(f"   (전체 {len(candidates)}거래일 중 유사도 Top {top_n})\n")
    print(f"  순위   날짜          유사도")
    print(f"  ─────  ────────────  ──────")
    for rank, (date, score) in enumerate(ranked, 1):
        bar = "█" * int(score / 5)
        print(f"  {rank:2d}위   {date}    {score:5.1f}%  {bar}")
    print()


# ── 날짜 목록 ────────────────────────────────────────────────────────────────

def list_dates():
    """저장된 거래일 목록과 캔들 수 출력."""
    all_df = _load_stored()
    if all_df.empty:
        print("[오류] 저장된 데이터 없음 — 먼저 'collect' 실행하세요.")
        sys.exit(1)

    counts = all_df.groupby("date").size().sort_index()
    valid = counts[counts >= MIN_CANDLES_PER_DAY]

    print(f"\n저장된 거래일 ({len(valid)}일, 유효 캔들 >= {MIN_CANDLES_PER_DAY}):\n")
    for date, cnt in valid.items():
        flag = "✓" if cnt >= 25 else "△"
        print(f"  {flag} {date}  ({cnt}캔들)")
    print()


# ── 진입점 ───────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args or args[0] == "help":
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "collect":
        bootstrap = "--bootstrap" in args or "-b" in args
        collect(bootstrap=bootstrap)

    elif cmd == "find":
        if len(args) < 2:
            print("사용법: python apr_similarity.py find YYYY-MM-DD [top_n]")
            sys.exit(1)
        query_date = args[1]
        top_n = int(args[2]) if len(args) >= 3 else TOP_N
        find_similar(query_date, top_n)

    elif cmd == "dates":
        list_dates()

    else:
        print(f"알 수 없는 명령: {cmd}")
        print("사용법: collect | find YYYY-MM-DD | dates")
        sys.exit(1)


if __name__ == "__main__":
    main()
