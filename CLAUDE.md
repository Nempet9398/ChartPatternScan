# CLAUDE.md — ChartPattern.io 개발 가이드

> Claude Code가 이 파일을 읽고 프로젝트 전체를 구현한다.
> 모든 구현 결정은 이 문서를 최우선 기준으로 삼는다.
> 모르는 것이 있으면 구현하기 전에 이 문서를 다시 읽어라.

-----

## 🎯 프로젝트 한 줄 정의

**종목 + 기간 선택 → 현재 차트가 어떤 고전 패턴과 가장 유사한지 Top 3를 유사도(%)로 보여주는 무료 웹 서비스**

서비스명: **ChartPattern.io**  
GitHub description: `Rule-based chart pattern similarity analyzer for stocks and crypto. No LLM — pure algorithmic pattern matching.`

-----

## 🏗️ 전체 아키텍처

```
[Browser: Next.js 14 + TypeScript]
         ↓ HTTP REST API
[FastAPI Backend: Python 3.11+]
         ↓
[Data Layer: yfinance / ccxt(Binance)]
         ↓
[Pattern Engine: Lo(2000) 논문 기반 알고리즘]
```

-----

## 📁 디렉토리 구조

```
chartpattern/
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── chart.py             # GET /api/chart/{symbol}
│   │   ├── pattern.py           # POST /api/analyze
│   │   └── search.py            # GET /api/search
│   ├── services/
│   │   ├── data_fetcher.py      # yfinance / ccxt 데이터 수집
│   │   └── pattern_engine.py    # 패턴 분석 오케스트레이터
│   ├── patterns/
│   │   ├── config.py            # 허용 오차 상수 (Lo 2000 기준)
│   │   ├── base.py              # BasePattern 추상 클래스
│   │   ├── preprocessor.py      # 공통 전처리 (스무딩 + 극값 탐지)
│   │   ├── head_and_shoulders.py
│   │   ├── inverse_head_and_shoulders.py
│   │   ├── double_top.py
│   │   ├── double_bottom.py
│   │   ├── golden_cross.py
│   │   ├── dead_cross.py
│   │   └── triangle.py          # 대칭/상승/하락 삼각수렴 통합
│   └── requirements.txt
│
└── frontend/
    ├── app/
    │   ├── page.tsx             # 메인 검색 페이지
    │   └── result/[symbol]/page.tsx
    ├── components/
    │   ├── SearchBar.tsx
    │   ├── PeriodSelector.tsx
    │   ├── CandlestickChart.tsx
    │   └── PatternCard.tsx
    └── lib/
        └── api.ts
```

-----

## 🔧 기술 스택

### Backend

```
Python 3.11+
fastapi
uvicorn
pandas
numpy
scipy          # find_peaks, linregress
yfinance       # 한국/미국 주식 (종목코드.KS / .KQ / AAPL)
ccxt           # 암호화폐 (Binance)
python-dotenv
```

### Frontend

```
Next.js 14 (App Router)
TypeScript
Tailwind CSS
lightweight-charts   # TradingView 오픈소스 캔들스틱 차트
zustand              # 전역 상태관리
```

### 배포

```
Frontend : Vercel
Backend  : Railway (또는 Render) — 무료 티어
```

-----

## 📚 알고리즘 이론적 근거 (필독)

> 이 섹션은 패턴 구현의 학문적 기반이다.
> 구현 전 반드시 읽고 이해한 뒤 코딩하라.

### 핵심 논문 3개

**[1] Lo, Mamaysky & Wang (2000) — “Foundations of Technical Analysis”**

- 저널: Journal of Finance, Vol.55 No.4, pp.1705-1765 (MIT Sloan)
- 핵심: 차트 패턴을 최초로 수학적으로 형식화.
  커널 회귀(Kernel Regression)로 노이즈 제거 후
  극값(Local Extrema) 시퀀스 E1,E2,…,En 으로 패턴을 수치 정의.
- 역할: 우리 패턴 조건 수식의 바이블. 허용 오차 수치(1.5%, 22일 등)의 출처.

**[2] Bulkowski, Thomas (2005) — “Encyclopedia of Chart Patterns” 2nd ed.**

- 출판사: Wiley
- 핵심: 1,000개 이상 실제 차트 패턴 실증 분석. 패턴별 성공률 통계.
- 역할: 각 패턴 카드에 표시할 historical_success_rate 수치의 출처.

**[3] Edwards & Magee (1966) — “Technical Analysis of Stock Trends”**

- 핵심: 이동평균 교차, 삼각수렴, 더블탑 등 고전 패턴의 원조 정의.
- 역할: Lo(2000)가 직접 인용한 패턴 정의의 원천.

### Lo(2000) 패턴 정의 원칙

Lo(2000)는 패턴을 연속된 극값 시퀀스 E1, E2, …, En 으로 정의한다.

```
극값 탐지 전제:
  - 가격 시계열 P(t)에 커널 회귀 적용 → 스무딩된 m(t) 추출
  - m(t)의 로컬 맥시마 = 피크(Peak)
  - m(t)의 로컬 미니마 = 트로프(Trough)
  - 피크와 트로프는 반드시 교대로 등장

우리 구현에서 커널 회귀 대신:
  - scipy.signal.find_peaks() 로 극값 탐지
  - 스무딩: 5일 단순이동평균(MA5)
  → 논문 정신 유지 + 구현 단순화
```

-----

## 📊 패턴 엔진 구현 명세

### 공통 원칙

- **LLM 절대 사용 금지** — 모든 판단은 수치 규칙으로만
- 입력: OHLCV pandas DataFrame
- 출력: 각 패턴별 PatternResult (similarity 0.0~1.0)
- 유사도 = 각 조건 충족 정도의 가중 합산

### patterns/config.py — 허용 오차 상수

```python
# Lo(2000) 논문 기준값. 변경 시 반드시 주석에 근거 명시.

SHOULDER_TOLERANCE   = 0.015   # 어깨 높이 허용 오차 1.5%  (Lo 2000)
NECKLINE_TOLERANCE   = 0.015   # 넥라인 수평 허용 오차 1.5% (Lo 2000)
DOUBLE_TOLERANCE     = 0.015   # 더블탑/바텀 두 극값 오차  (Lo 2000)
DOUBLE_MIN_DAYS      = 22      # 더블탑/바텀 최소 간격(거래일) (Lo 2000, Edwards&Magee)
SMOOTH_WINDOW        = 5       # 스무딩 MA 윈도우
PEAK_MIN_DISTANCE    = 5       # 최소 피크 간격 (거래일)
PEAK_MIN_PROMINENCE  = 0.02    # 최소 피크 돌출도 (정규화 기준)
TRIANGLE_SLOPE_FLAT  = 0.001   # 수평으로 간주할 기울기 임계값
```

### patterns/base.py

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd

@dataclass
class PatternResult:
    name: str
    name_ko: str
    similarity: float            # 0.0 ~ 100.0
    signal: str                  # "bearish" | "bullish" | "neutral"
    description: str
    historical_success_rate: float  # Bulkowski(2005) 기준 %
    source: str                  # 논문 출처
    highlight_start: str | None  # ISO date
    highlight_end: str | None

class BasePattern(ABC):
    name: str
    name_ko: str
    signal: str
    description: str
    historical_success_rate: float
    source: str

    @abstractmethod
    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        pass
```

### patterns/preprocessor.py

```python
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from .config import SMOOTH_WINDOW, PEAK_MIN_DISTANCE, PEAK_MIN_PROMINENCE

def preprocess(df: pd.DataFrame) -> dict:
    """
    Lo(2000) 커널 회귀를 이동평균으로 단순화한 전처리.

    Returns dict:
      close         : 원본 종가 Series
      smoothed      : 스무딩된 종가 Series
      normalized    : Min-Max 정규화 Series (0~1)
      peaks         : 피크 인덱스 배열 (정수)
      troughs       : 트로프 인덱스 배열 (정수)
      peak_values   : 정규화된 피크 값 배열
      trough_values : 정규화된 트로프 값 배열
      dates         : 날짜 인덱스
    """
    close = df['Close'].copy()
    smoothed = close.rolling(window=SMOOTH_WINDOW, center=True).mean().dropna()
    norm = (smoothed - smoothed.min()) / (smoothed.max() - smoothed.min() + 1e-10)

    peak_idx, _   = find_peaks(norm.values,  distance=PEAK_MIN_DISTANCE, prominence=PEAK_MIN_PROMINENCE)
    trough_idx, _ = find_peaks(-norm.values, distance=PEAK_MIN_DISTANCE, prominence=PEAK_MIN_PROMINENCE)

    return {
        "close":         close,
        "smoothed":      smoothed,
        "normalized":    norm,
        "peaks":         peak_idx,
        "troughs":       trough_idx,
        "peak_values":   norm.values[peak_idx],
        "trough_values": norm.values[trough_idx],
        "dates":         norm.index,
    }
```

-----

### 패턴 1: Head & Shoulders (헤드앤숄더)

**출처: Lo(2000) Definition 1 / Bulkowski(2005) 성공률 81%**

```
극값 시퀀스: E1(피크) E2(트로프) E3(피크) E4(트로프) E5(피크)

Lo(2000) 필수 조건:
  [C1] E3 > E1 AND E3 > E5           머리가 양 어깨보다 높음       (40점)
  [C2] |E1-E5| / E3 < SHOULDER_TOLERANCE   어깨 높이 대칭        (30점)
  [C3] |E2-E4| / E3 < NECKLINE_TOLERANCE   넥라인 수평           (30점)

유사도 = C1충족*0.40 + (1 - |E1-E5|/E3/0.15)*0.30 + (1 - |E2-E4|/E3/0.15)*0.30
```

### 패턴 2: Inverse Head & Shoulders (역헤드앤숄더)

**출처: Lo(2000) Definition 2 / Bulkowski(2005) 성공률 89%**

```
헤드앤숄더를 상하 반전:
  [C1] E3 < E1 AND E3 < E5           머리가 양 어깨보다 낮음
  [C2] |E1-E5| / |E3| < SHOULDER_TOLERANCE
  [C3] |E2-E4| / |E3| < NECKLINE_TOLERANCE

유사도 계산 구조: 헤드앤숄더와 동일
```

### 패턴 3: Double Top (더블탑)

**출처: Lo(2000) Definition 4 / Bulkowski(2005) 성공률 65%**

```
극값: E1(피크) ... Ea(피크)  — E1 이후 가장 높은 피크

Lo(2000) 필수 조건:
  [C1] |E1-Ea| / avg(E1,Ea) < DOUBLE_TOLERANCE    두 고점 1.5% 이내  (50점)
  [C2] index(Ea) - index(E1) >= DOUBLE_MIN_DAYS   최소 22 거래일 간격 (20점)
  [C3] (avg_peak - trough_between) / avg_peak > 0.05  중간 하락 5% 이상 (30점)
```

### 패턴 4: Double Bottom (더블바텀)

**출처: Lo(2000) Definition 5 / Bulkowski(2005) 성공률 71%**

```
더블탑 상하 반전:
  [C1] |E1-Ea| / avg < DOUBLE_TOLERANCE
  [C2] 최소 DOUBLE_MIN_DAYS 간격
  [C3] (peak_between - avg_trough) / avg_trough > 0.05
```

### 패턴 5: Golden Cross (골든크로스)

**출처: Edwards & Magee (1966) / Bulkowski(2005) 성공률 72%**

```
MA20, MA60 계산 (원본 종가, 정규화 불필요)

조건:
  [C1] 최근 5거래일 내 MA20이 MA60 아래→위 교차      (60점)
  [C2] 교차 이후 이격도: (MA20-MA60)/MA60             (40점)
       → 이격이 클수록 신호 강도 ↑
```

### 패턴 6: Dead Cross (데드크로스)

**출처: Edwards & Magee (1966) / Bulkowski(2005) 성공률 68%**

```
골든크로스 반전:
  [C1] 최근 5거래일 내 MA20이 MA60 위→아래 교차
  [C2] 이격도: (MA60-MA20)/MA60
```

### 패턴 7-8-9: Triangle (삼각수렴)

**출처: Lo(2000) Definition 3 / Bulkowski(2005)**

```
극값 시퀀스: E1(피크) E2(트로프) E3(피크) E4(트로프) E5(피크)

대칭 삼각수렴 (Symmetrical) — Bulkowski 54%:
  상단 추세선 (E1,E3,E5): slope < 0   (고점 하향)
  하단 추세선 (E2,E4):    slope > 0   (저점 상향)

상승 삼각수렴 (Ascending) — Bulkowski 75%:
  상단 추세선: |slope| < TRIANGLE_SLOPE_FLAT   (수평)
  하단 추세선: slope > 0

하락 삼각수렴 (Descending) — Bulkowski 72%:
  상단 추세선: slope < 0
  하단 추세선: |slope| < TRIANGLE_SLOPE_FLAT   (수평)

유사도 공통 계산:
  기울기 조건 충족 여부                    (40점)
  선형회귀 R² 적합도 (scipy.stats.linregress) (30점)
  수렴 강도 = |upper_slope| + |lower_slope|  (30점)
```

-----

### 유사도 최종 집계

```python
# services/pattern_engine.py

ALL_PATTERNS = [
    HeadAndShoulders(),
    InverseHeadAndShoulders(),
    DoubleTop(),
    DoubleBottom(),
    GoldenCross(),
    DeadCross(),
    SymmetricalTriangle(),
    AscendingTriangle(),
    DescendingTriangle(),
]

def analyze(df: pd.DataFrame) -> list[PatternResult]:
    results = [p.calculate_similarity(df) for p in ALL_PATTERNS]
    return sorted(results, key=lambda x: x.similarity, reverse=True)[:3]
```

-----

## 🌐 API 명세

### GET /api/chart/{symbol}

```
Query: period = 1w | 1mo | 3mo | 6mo | 1y

Response:
{
  "symbol": "AAPL",
  "period": "3mo",
  "ohlcv": [
    {"time": "2024-01-02", "open": 185.0, "high": 188.0,
     "low": 183.0, "close": 187.0, "volume": 12345678}
  ]
}
```

### POST /api/analyze

```
Body: { "symbol": "AAPL", "period": "3mo" }

Response:
{
  "symbol": "AAPL",
  "period": "3mo",
  "analyzed_at": "2026-03-20T12:00:00Z",
  "algorithm_ref": "Lo, Mamaysky & Wang (2000), Journal of Finance",
  "top_patterns": [
    {
      "rank": 1,
      "name": "Head and Shoulders",
      "name_ko": "헤드앤숄더",
      "similarity": 87.3,
      "signal": "bearish",
      "description": "세 고점 중 가운데가 가장 높은 하락 반전 패턴",
      "historical_success_rate": 81.0,
      "source": "Bulkowski (2005)",
      "highlight_start": "2024-01-15",
      "highlight_end": "2024-03-10"
    }
  ]
}
```

### GET /api/search?q={query}

```
Response:
{
  "results": [
    {"symbol": "005930.KS", "name": "삼성전자", "market": "KOSPI"},
    {"symbol": "AAPL",      "name": "Apple Inc.", "market": "NASDAQ"},
    {"symbol": "BTC-USD",   "name": "Bitcoin",    "market": "Crypto"}
  ]
}
```

-----

## 🖥️ 프론트엔드 구현 지침

### 차트 (CandlestickChart.tsx)

```typescript
import { createChart } from 'lightweight-charts'
// 1. 캔들스틱 시리즈 렌더링
// 2. highlight_start ~ highlight_end 구간에 반투명 박스 오버레이
```

### PatternCard.tsx 표시 항목

```
패턴명 (한글 + 영문)
유사도 % + 컬러 프로그레스 바
신호 뱃지: 상승(green) / 하락(red) / 중립(gray)
"역사적 성공률 81% · Bulkowski (2005)"
패턴 설명 1줄
```

### 유사도 색상 기준

```typescript
const getBarColor = (score: number) => {
  if (score >= 70) return 'bg-green-500'
  if (score >= 40) return 'bg-yellow-400'
  return 'bg-gray-400'
}
```

-----

## ⚠️ 구현 시 반드시 지킬 것

1. **면책 고지 필수** — 모든 페이지 하단:
   “본 서비스의 분석 결과는 투자 권유가 아닙니다. 투자 손익의 책임은 전적으로 본인에게 있습니다.”
1. **yfinance 심볼 규칙**
- 코스피: `005930.KS`
- 코스닥: `035720.KQ`
- 미국주식: `AAPL`
- 암호화폐: `BTC-USD`
1. **데이터 최소 요건** — 60거래일 미만이면 분석 불가 메시지 반환
1. **허용 오차 하드코딩 금지** — 반드시 `config.py` 상수 사용
1. **CORS 설정** — FastAPI에서 프론트 도메인 명시적 허용
1. **에러 핸들링** — 상장폐지 / API 타임아웃 / 심볼 미존재 모두 명시적 처리

-----

## 🚀 개발 순서

```
Step 1 — 데이터 파이프라인
  yfinance로 AAPL 3개월치 OHLCV fetch 테스트
  preprocessor.py 구현 → matplotlib으로 극값 탐지 시각화 확인

Step 2 — 패턴 엔진 (쉬운 것 → 어려운 것 순)
  GoldenCross → DoubleTop → HeadAndShoulders → Triangle
  각 패턴: 알려진 패턴 차트에 적용해 similarity score 검증

Step 3 — FastAPI 백엔드
  /api/chart, /api/analyze, /api/search 구현 + 단위 테스트

Step 4 — Next.js 프론트엔드
  SearchBar → CandlestickChart → PatternCard 순으로 구현

Step 5 — 통합 테스트 & 배포
  Vercel(프론트) + Railway(백엔드)
```