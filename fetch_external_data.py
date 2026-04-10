"""
외부 데이터 수집기 — 로컬에서 실행 후 GitHub에 푸시
수집 항목:
  1. BTC 1h OHLCV        → btc_1h.csv        (CryptoCompare)
  2. ETH 펀딩비           → eth_funding.csv   (Binance Futures)
  3. ETH 미체결약정(OI)   → eth_oi.csv        (Binance Futures)
  4. 공포탐욕지수         → fear_greed.csv    (Alternative.me)

사용법:
  pip install requests pandas
  python fetch_external_data.py
"""

import time
import json
import requests
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

SINCE    = "2023-01-01"
OUT_DIR  = Path(".")   # 실행 디렉토리에 저장


# ══════════════════════════════════════════
# 1. BTC 1h OHLCV (CryptoCompare)
# ══════════════════════════════════════════
def fetch_btc_1h():
    print("\n[1/4] BTC 1h OHLCV 수집 중 (CryptoCompare)...")
    since_ts  = int(datetime.strptime(SINCE, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    now_ts    = int(datetime.now(tz=timezone.utc).timestamp())
    all_candles = []
    to_ts = now_ts

    while True:
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=USDT&limit=2000&toTs={to_ts}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()

        if data.get("Response") != "Success":
            print(f"  [오류] {data.get('Message')}")
            break

        chunk = [c for c in data["Data"]["Data"] if c["open"] > 0 and c["time"] >= since_ts]
        all_candles.extend(chunk)

        oldest_ts = data["Data"]["Data"][0]["time"]
        dt_str = datetime.fromtimestamp(oldest_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"  {dt_str} ~ | {len(all_candles):,}개", end="\r")

        if oldest_ts <= since_ts:
            break
        to_ts = oldest_ts - 1
        time.sleep(0.3)

    df = pd.DataFrame(all_candles)
    df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_localize(None)
    df = df.rename(columns={"open": "open", "high": "high", "low": "low",
                             "close": "close", "volumefrom": "volume"})
    df = df[["datetime","open","high","low","close","volume"]]
    df = df.drop_duplicates("datetime").sort_values("datetime").reset_index(drop=True)
    path = OUT_DIR / "btc_1h.csv"
    df.to_csv(path, index=False)
    print(f"\n  완료: {len(df):,}개 → {path}")
    return df


# ══════════════════════════════════════════
# 2. ETH 펀딩비 (Binance Futures)
# ══════════════════════════════════════════
def fetch_eth_funding():
    print("\n[2/4] ETH 펀딩비 수집 중 (Binance Futures)...")
    since_ms = int(datetime.strptime(SINCE, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    all_rows = []

    while True:
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": "ETHUSDT", "startTime": since_ms, "limit": 1000}
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        if not data or isinstance(data, dict):
            print(f"  [오류] {data}")
            break

        all_rows.extend(data)
        last_ts = data[-1]["fundingTime"]
        dt_str  = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"  ~ {dt_str} | {len(all_rows):,}개", end="\r")

        if len(data) < 1000:
            break
        since_ms = last_ts + 1
        time.sleep(0.2)

    df = pd.DataFrame(all_rows)
    df["datetime"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True).dt.tz_localize(None)
    df["funding_rate"] = df["fundingRate"].astype(float)
    df = df[["datetime","funding_rate"]].drop_duplicates("datetime").sort_values("datetime").reset_index(drop=True)
    path = OUT_DIR / "eth_funding.csv"
    df.to_csv(path, index=False)
    print(f"\n  완료: {len(df):,}개 → {path}")
    return df


# ══════════════════════════════════════════
# 3. ETH 미체결약정 OI (Binance Futures, 1h)
# ══════════════════════════════════════════
def fetch_eth_oi():
    print("\n[3/4] ETH 미체결약정 수집 중 (Binance Futures)...")
    # Binance OI hist는 최대 30일 과거만 지원 → endTime 기준 청크
    now_ms   = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    since_ms = int(datetime.strptime(SINCE, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    CHUNK_MS = 500 * 3600 * 1000  # 500시간 단위 청크
    all_rows = []

    end_ms = now_ms
    while end_ms > since_ms:
        start_ms = max(end_ms - CHUNK_MS, since_ms)
        url = "https://fapi.binance.com/futures/data/openInterestHist"
        params = {
            "symbol":    "ETHUSDT",
            "period":    "1h",
            "startTime": start_ms,
            "endTime":   end_ms,
            "limit":     500,
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        if isinstance(data, dict):
            # 오류 응답
            print(f"\n  [오류] {data.get('msg', data)}")
            break

        if data:
            all_rows.extend(data)
            dt_str = datetime.fromtimestamp(data[0]["timestamp"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            print(f"  ~ {dt_str} | {len(all_rows):,}개", end="\r")

        end_ms = start_ms - 1
        time.sleep(0.2)

    if not all_rows:
        raise ValueError("OI 데이터 없음")

    df = pd.DataFrame(all_rows)
    df["datetime"]      = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
    df["open_interest"] = df["sumOpenInterest"].astype(float)
    df["oi_usd"]        = df["sumOpenInterestValue"].astype(float)
    df = df[["datetime","open_interest","oi_usd"]].drop_duplicates("datetime").sort_values("datetime").reset_index(drop=True)
    path = OUT_DIR / "eth_oi.csv"
    df.to_csv(path, index=False)
    print(f"\n  완료: {len(df):,}개 → {path}")
    return df


# ══════════════════════════════════════════
# 4. 공포탐욕지수 (Alternative.me)
# ══════════════════════════════════════════
def fetch_fear_greed():
    print("\n[4/4] 공포탐욕지수 수집 중 (Alternative.me)...")
    # date_format 없이 요청 → timestamp는 unix 초 단위 문자열로 옴
    url  = "https://api.alternative.me/fng/?limit=0"
    resp = requests.get(url, timeout=15)
    data = resp.json()["data"]

    df = pd.DataFrame(data)
    # timestamp = unix 초 단위 문자열 (e.g. "1672531200")
    df["date"]       = pd.to_datetime(df["timestamp"].astype(int), unit="s", utc=True).dt.date.astype(str)
    df["fear_greed"] = df["value"].astype(int)
    df["fg_class"]   = df["value_classification"]
    df = df[["date","fear_greed","fg_class"]]
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)

    # 2023년 이후만
    df = df[df["date"] >= SINCE[:10]].reset_index(drop=True)

    path = OUT_DIR / "fear_greed.csv"
    df.to_csv(path, index=False)
    print(f"  완료: {len(df):,}개 → {path}")
    return df


# ══════════════════════════════════════════
# 메인
# ══════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 50)
    print("  외부 데이터 수집기")
    print(f"  기간: {SINCE} ~ 현재")
    print("=" * 50)

    results = {}
    try:
        results["btc"]        = fetch_btc_1h()
    except Exception as e:
        print(f"  [실패] BTC: {e}")

    try:
        results["funding"]    = fetch_eth_funding()
    except Exception as e:
        print(f"  [실패] 펀딩비: {e}")

    try:
        results["oi"]         = fetch_eth_oi()
    except Exception as e:
        print(f"  [실패] OI: {e}")

    try:
        results["fear_greed"] = fetch_fear_greed()
    except Exception as e:
        print(f"  [실패] 공포탐욕: {e}")

    print("\n" + "=" * 50)
    print("  수집 완료 — 아래 파일을 GitHub에 푸시해주세요:")
    for fname in ["btc_1h.csv", "eth_funding.csv", "eth_oi.csv", "fear_greed.csv"]:
        path = OUT_DIR / fname
        if path.exists():
            size = path.stat().st_size / 1024
            print(f"  ✓ {fname:25s} ({size:.0f} KB)")
        else:
            print(f"  ✗ {fname:25s} (생성 실패)")
    print("=" * 50)
