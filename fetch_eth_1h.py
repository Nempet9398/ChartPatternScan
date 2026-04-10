"""
ETH/USDT 1시간봉 수집기 (CryptoCompare)
2023-01-01 ~ 현재, ML용 피처 포함 저장
저장: eth_1h.csv
"""

import time
import json
import urllib.request
import numpy as np
import pandas as pd
from datetime import datetime, timezone

CSV_PATH = "/home/user/ChartPatternScan/eth_1h.csv"
API_BASE = "https://min-api.cryptocompare.com/data/v2/histohour"
SINCE    = "2023-01-01"
LIMIT    = 2000  # CryptoCompare 1회 최대


def fetch_all() -> pd.DataFrame:
    since_ts  = int(datetime.strptime(SINCE, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    now_ts    = int(datetime.now(tz=timezone.utc).timestamp())

    all_candles = []
    to_ts = now_ts

    print(f"[수집] ETH/USDT 1h | {SINCE} ~ 현재")

    while True:
        url = f"{API_BASE}?fsym=ETH&tsym=USDT&limit={LIMIT}&toTs={to_ts}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            r   = urllib.request.urlopen(req, timeout=15)
            data = json.loads(r.read())
        except Exception as e:
            print(f"\n  [재시도] {e}")
            time.sleep(5)
            continue

        if data.get("Response") != "Success":
            print(f"\n  [오류] {data.get('Message')}")
            break

        chunk = data["Data"]["Data"]
        # 빈 캔들(거래 없음) 제거
        chunk = [c for c in chunk if c["open"] > 0]
        if not chunk:
            break

        # since 이전 데이터는 버림
        chunk = [c for c in chunk if c["time"] >= since_ts]
        all_candles.extend(chunk)

        oldest_ts = data["Data"]["Data"][0]["time"]
        oldest_dt = datetime.fromtimestamp(oldest_ts, tz=timezone.utc)
        print(f"  {oldest_dt.strftime('%Y-%m-%d %H:%M')} ~ | {len(all_candles):,}개 누적", end="\r")

        if oldest_ts <= since_ts:
            break

        to_ts = oldest_ts - 1
        time.sleep(0.3)

    print(f"\n[완료] 총 {len(all_candles):,}개 캔들")

    df = pd.DataFrame(all_candles)
    df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_localize(None)
    df = df.rename(columns={
        "open": "open", "high": "high", "low": "low",
        "close": "close", "volumefrom": "volume"
    })
    df = df[["datetime","open","high","low","close","volume"]].copy()
    df = df.drop_duplicates(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]
    h = df["high"]
    l = df["low"]
    o = df["open"]
    v = df["volume"]

    # ── 이동평균 (단순)
    for w in [5, 10, 20, 50, 100, 200]:
        df[f"ma{w}"] = c.rolling(w).mean()

    # ── EMA
    for w in [9, 12, 26]:
        df[f"ema{w}"] = c.ewm(span=w, adjust=False).mean()

    # ── MACD
    df["macd"]        = df["ema12"] - df["ema26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    # ── RSI (14)
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / (loss + 1e-10)
    df["rsi14"] = 100 - 100 / (1 + rs)

    # ── Bollinger Bands (20, 2σ)
    bb_mid        = c.rolling(20).mean()
    bb_std        = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_mid"]   = bb_mid
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_pct"]   = (c - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (bb_mid + 1e-10)

    # ── ATR (14)
    tr = pd.concat([
        h - l,
        (h - c.shift()).abs(),
        (l - c.shift()).abs()
    ], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14).mean()
    df["atr_pct"] = df["atr14"] / (c + 1e-10) * 100  # 변동성 비율

    # ── 스토캐스틱 (14, 3)
    low14  = l.rolling(14).min()
    high14 = h.rolling(14).max()
    df["stoch_k"] = (c - low14) / (high14 - low14 + 1e-10) * 100
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # ── 캔들 구조
    df["body"]       = (c - o).abs()
    df["body_pct"]   = df["body"] / (o + 1e-10) * 100
    df["upper_wick"] = h - pd.concat([c, o], axis=1).max(axis=1)
    df["lower_wick"] = pd.concat([c, o], axis=1).min(axis=1) - l
    df["hl_range"]   = h - l
    df["is_bull"]    = (c > o).astype(int)

    # ── 수익률 (%)
    df["ret_1h"]   = c.pct_change(1)   * 100
    df["ret_4h"]   = c.pct_change(4)   * 100
    df["ret_24h"]  = c.pct_change(24)  * 100
    df["ret_7d"]   = c.pct_change(168) * 100

    # ── 거래량 피처
    df["vol_ma20"]  = v.rolling(20).mean()
    df["vol_ratio"] = v / (df["vol_ma20"] + 1e-10)  # 평균 대비 거래량 비율
    df["vol_ma_ratio"] = v / (v.rolling(200).mean() + 1e-10)

    # ── 가격 위치 (52주 고저 대비, 1h 기준 365*24=8760개)
    df["high_52w"]  = h.rolling(8760).max()
    df["low_52w"]   = l.rolling(8760).min()
    df["pos_52w"]   = (c - df["low_52w"]) / (df["high_52w"] - df["low_52w"] + 1e-10)

    # ── MA 크로스 신호
    df["ma20_above_ma50"]  = (df["ma20"] > df["ma50"]).astype(int)
    df["ma50_above_ma200"] = (df["ma50"] > df["ma200"]).astype(int)
    df["golden_cross"]     = ((df["ma20"] > df["ma50"]) & (df["ma20"].shift() <= df["ma50"].shift())).astype(int)
    df["dead_cross"]       = ((df["ma20"] < df["ma50"]) & (df["ma20"].shift() >= df["ma50"].shift())).astype(int)

    # ── MA 이격도
    df["dist_ma20"]  = (c - df["ma20"])  / (df["ma20"]  + 1e-10) * 100
    df["dist_ma50"]  = (c - df["ma50"])  / (df["ma50"]  + 1e-10) * 100
    df["dist_ma200"] = (c - df["ma200"]) / (df["ma200"] + 1e-10) * 100

    # ── 시간 피처 (ML용 주기성)
    df["hour"]      = df["datetime"].dt.hour
    df["dayofweek"] = df["datetime"].dt.dayofweek   # 0=월요일
    df["month"]     = df["datetime"].dt.month
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)

    return df


def main():
    df = fetch_all()
    print("[피처] 기술지표 계산 중...")
    df = add_features(df)
    df.to_csv(CSV_PATH, index=False)

    import os
    size_mb = os.path.getsize(CSV_PATH) / 1024 / 1024
    print(f"\n[저장 완료] {CSV_PATH}")
    print(f"  행:   {len(df):,}개")
    print(f"  열:   {len(df.columns)}개")
    print(f"  기간: {df['datetime'].iloc[0]} ~ {df['datetime'].iloc[-1]}")
    print(f"  크기: {size_mb:.1f} MB")
    print(f"\n  컬럼 목록 ({len(df.columns)}개):")
    for i, col in enumerate(df.columns, 1):
        print(f"    {i:2d}. {col}")


if __name__ == "__main__":
    main()
