# CLAUDE_APPENDIX_PATTERN_ENGINE.md

> 이 문서는 기존 `CLAUDE.md`를 **대체하지 않는다**.
>  
> 목적은 기존 구조를 유지한 상태에서,
> - 기존 9개 패턴 감지 정확도를 높이고
> - 추가 패턴을 자연스럽게 확장할 수 있게
> 하는 **보완 명세(Addendum)** 를 제공하는 것이다.
>
> Claude Code / Codex는 반드시 `CLAUDE.md`를 최우선으로 따르고,
> 본 문서는 **그 위에 얹는 확장 지침**으로만 사용한다.

---

## 0. 적용 원칙

### 절대 원칙
1. 기존 `CLAUDE.md`의 디렉토리 구조를 최대한 유지한다.
2. 기존 `BasePattern`, `PatternResult`, `preprocess()` 인터페이스를 깨지 않는다.
3. 기존 9개 패턴 클래스 파일명을 바꾸지 않는다.
4. 기존 `/api/analyze` 응답 스키마를 깨지 않는다.
5. 기존 `config.py` 상수 체계를 유지한다.
6. 기존 룰 기반 철학은 유지하고, 딥러닝/LLM은 도입하지 않는다.

### 허용되는 변경
1. 기존 파일 내부 로직 고도화
2. `config.py` 상수 추가
3. `preprocessor.py` 반환값 확장
4. `triangle.py` 내부 기능 확장
5. 새로운 패턴 파일 추가
6. 기존 응답 필드는 유지한 채 선택적 필드 추가

---

## 1. 기존 구조를 해치지 않는 확장 전략

현재 구조:

```text
backend/
  services/pattern_engine.py
  patterns/
    config.py
    base.py
    preprocessor.py
    head_and_shoulders.py
    inverse_head_and_shoulders.py
    double_top.py
    double_bottom.py
    golden_cross.py
    dead_cross.py
    triangle.py
```

이 구조를 유지하면서 아래만 추가한다:

```text
backend/
  patterns/
    utils.py                  # 선택: 공통 유틸
    triple_top.py             # 추가
    triple_bottom.py          # 추가
    rectangle.py              # 추가
    wedge.py                  # 추가
    flag_pennant.py           # 추가
    breakout.py               # 선택: 공통 breakout 유틸
    volume_rules.py           # 선택: 거래량 보조 규칙
```

중요:
- `triangle.py`는 삭제/분리하지 말고 유지한다.
- wedge를 triangle.py에 통합할 수도 있으나, 가독성을 위해 별도 파일 권장.
- flag/pennant는 한 파일에서 bullish/bearish 모두 처리 권장.

---

## 2. 기존 엔진 고도화 원칙

기존 9개 패턴은 유지하되, 아래 방식으로만 업그레이드한다.

### 2.1 전처리 업그레이드
기존 `preprocess()` 함수 이름과 기본 반환 구조는 유지한다.
단, 반환값을 확장하는 것은 허용한다.

### 현재 유지 필드
- close
- smoothed
- normalized
- peaks
- troughs
- peak_values
- trough_values
- dates

### 추가 허용 필드
- merged_extrema
- peak_meta
- trough_meta
- rolling_volatility
- volume_ma20
- raw_close_aligned

즉, 기존 consumer 코드가 안 깨지도록 **기존 key는 그대로 유지하고 새 key만 추가**한다.

---

## 3. preprocessor.py 보완 명세

### 현재 구조 유지
```python
def preprocess(df: pd.DataFrame) -> dict:
    ...
```

### 개선 내용
1. MA5 기본 유지
2. 단, config 옵션으로 Savitzky-Golay smoothing 지원 추가
3. `find_peaks()` 사용은 유지하되, width/prominence/distance 활용 강화
4. peak/trough significance 계산 추가
5. peak/trough merge 후 교대 extrema 시퀀스 생성 추가

### 구현 방침
- 기본값은 현재와 동일하게 MA5
- 옵션이 켜질 때만 Savitzky-Golay 사용
- 기존 사용자 기대를 깨지 않기 위해 기본 동작은 바꾸지 않는다

### config 추가 예시
```python
USE_SAVGOL_SMOOTHING = False
SAVGOL_WINDOW = 7
SAVGOL_POLYORDER = 2

PEAK_MIN_WIDTH = 1
PEAK_MIN_DISTANCE = 5
PEAK_MIN_PROMINENCE = 0.02

USE_EXTREMA_SIGNIFICANCE = True
```

---

## 4. config.py 확장 원칙

기존 상수는 삭제/이름변경 금지.

### 기존 유지
```python
SHOULDER_TOLERANCE
NECKLINE_TOLERANCE
DOUBLE_TOLERANCE
DOUBLE_MIN_DAYS
SMOOTH_WINDOW
PEAK_MIN_DISTANCE
PEAK_MIN_PROMINENCE
TRIANGLE_SLOPE_FLAT
```

### 추가 권장 상수
```python
PEAK_MIN_WIDTH = 1
BREAKOUT_EPSILON = 0.005
BREAKOUT_FOLLOWTHROUGH_BARS = 3
FAILED_BREAKOUT_PENALTY = 0.15

VOLUME_MA_WINDOW = 20
VOLUME_SURGE_RATIO = 1.2

USE_SAVGOL_SMOOTHING = False
SAVGOL_WINDOW = 7
SAVGOL_POLYORDER = 2

USE_DTW_SHAPE_SCORE = False
DTW_WEIGHT = 0.10
```

주의:
- 기존 tolerance는 hard cutoff로만 쓰지 말고, 가능하면 score scale로 활용
- 하지만 완전한 hard rule 제거가 아니라, **최소 후보 필터 + 점수화** 혼합 구조 허용

---

## 5. PatternResult 확장 원칙

기존 `PatternResult` dataclass를 **깨지 않는 범위 내에서** 선택 필드를 추가할 수 있다.

### 기존 유지 필드
```python
name
name_ko
similarity
signal
description
historical_success_rate
source
highlight_start
highlight_end
```

### 선택적 추가 필드 권장
```python
breakout_state: str | None = None
subscores: dict | None = None
explanation: list[str] | None = None
```

### 목적
- API 호환성 유지
- 프론트는 기존 필드만 써도 동작
- 추후 UI 고도화 시 explanation/subscores 사용 가능

---

## 6. BasePattern은 유지하되 내부 유틸 허용

`BasePattern` 인터페이스는 바꾸지 않는다.

```python
class BasePattern(ABC):
    ...
    @abstractmethod
    def calculate_similarity(self, df: pd.DataFrame) -> PatternResult:
        pass
```

단, 패턴 구현체 내부에서 다음 private helper를 사용하는 것은 허용한다.

```python
def _build_result(...)
def _score_tolerance(...)
def _score_breakout(...)
def _score_volume(...)
```

---

## 7. 기존 9개 패턴별 보완 지침

## 7.1 HeadAndShoulders / InverseHeadAndShoulders
기존 5-extrema 구조 유지.

### 추가할 것
1. 어깨 대칭을 hard pass/fail이 아니라 연속 점수화
2. 머리 prominence 점수 추가
3. neckline 완전 수평만 허용하지 말고 약한 기울기 허용
4. neckline breakout 여부 보조 점수 추가
5. 거래량 보조 점수 추가 가능

### 기존 로직을 깨지 않는 구현 방식
- 기존 similarity 계산식 유지
- 단, 내부적으로 score clamp를 더 안정화
- 추가 점수는 최대 10~20점 범위의 보정치로 반영

---

## 7.2 DoubleTop / DoubleBottom
기존 구조 유지.

### 추가할 것
1. 두 고점/저점 유사도 점수화 강화
2. 중간 골/봉우리 깊이 점수 추가
3. neckline 돌파 확인 점수 추가
4. breakout 이후 재진입 시 감점 추가

---

## 7.3 GoldenCross / DeadCross
기존 MA20/MA60 규칙 유지.

### 추가할 것
1. cross가 발생한 뒤 separation strength 반영
2. 교차 직후 3~5봉 유지 여부 확인
3. whipsaw 감점 규칙 추가
4. 선택적으로 EMA 교차 모드 지원 가능
   - 단, 기본은 SMA 유지

---

## 7.4 Triangle
기존 `triangle.py` 파일 유지.

현재:
- symmetrical
- ascending
- descending

여기에 아래를 추가 가능:

### Triangle 내부 고도화
1. upper/lower trendline fit score 분리
2. gap contraction score 추가
3. apex proximity score 추가
4. breakout_up / breakout_down 상태 반환
5. volume contraction + breakout surge 점수 추가

### Triangle가 감지해야 하는 상태
- forming
- breakout_up
- breakout_down
- failed_breakout

중요:
- 기존 3개 패턴 클래스명은 유지
- breakout 상태는 PatternResult의 선택 필드로만 제공

---

## 8. 새로 추가할 패턴 우선순위

기존 구조와 가장 잘 맞는 패턴부터 추가한다.

### Priority 1
1. `triple_top.py`
2. `triple_bottom.py`
3. `rectangle.py`
4. `wedge.py`
5. `flag_pennant.py`

### Priority 2
6. `rounding.py` 또는 `rounding_bottom.py`, `rounding_top.py`
7. `cup_and_handle.py`
8. `broadening.py`

현재 단계에서는 Priority 1까지만 우선 구현 권장.

---

## 9. 추가 패턴별 구체 지침

## 9.1 Triple Top
파일: `patterns/triple_top.py`

### 구조
- peak-trough-peak-trough-peak

### 조건
1. 세 peak 높이 유사
2. 두 trough가 존재
3. 마지막 이후 neckline 하향 이탈 시 가점

### signal
- bearish

---

## 9.2 Triple Bottom
파일: `patterns/triple_bottom.py`

### 구조
- trough-peak-trough-peak-trough

### 조건
1. 세 trough 깊이 유사
2. 두 peak 존재
3. neckline 상향 돌파 시 가점

### signal
- bullish

---

## 9.3 Rectangle
파일: `patterns/rectangle.py`

### 구조
- 상단 저항선 수평
- 하단 지지선 수평
- 가격 범위 유지

### 상태
- forming
- breakout_up
- breakout_down

### signal
- 기본 neutral
- 돌파 후 방향 부여 가능

---

## 9.4 Wedge
파일: `patterns/wedge.py`

한 파일에서 두 패턴 처리 권장:
- Rising Wedge
- Falling Wedge

### Rising Wedge
- 상단/하단 모두 상승
- 하단 기울기가 더 큼
- 수렴
- 일반적으로 bearish bias

### Falling Wedge
- 상단/하단 모두 하락
- 상단 절댓값이 더 큼
- 수렴
- 일반적으로 bullish bias

---

## 9.5 Flag / Pennant
파일: `patterns/flag_pennant.py`

### 공통 구조
1. pole 존재
2. 짧은 조정 구간 존재
3. 원래 방향으로 breakout

### 분리 기준
- 평행 채널이면 Flag
- 작은 수렴이면 Pennant

### 분류
- Bull Flag
- Bear Flag
- Bull Pennant
- Bear Pennant

---

## 10. breakout 공통 규칙

새 파일로 분리 가능:
- `patterns/breakout.py`

혹은 각 detector 내부 helper로 둬도 됨.

### 상방 돌파
```python
close_t > upper_line_t * (1 + BREAKOUT_EPSILON)
```

### 하방 이탈
```python
close_t < lower_line_t * (1 - BREAKOUT_EPSILON)
```

### 추가 확인
1. 종가 기준
2. follow-through 2~3봉
3. 바로 재진입 시 failed_breakout 처리

---

## 11. volume_rules.py 보조 규칙

거래량은 필수는 아니지만 강력한 보조 점수로 사용.

### 기본 규칙
```python
volume_ratio = breakout_volume / avg_volume_20
```

### 점수화
- ratio >= 1.2 이면 가점
- ratio >= 1.5 이면 강한 가점

### 적용 우선 패턴
1. Triangle breakout
2. Head & Shoulders neckline break
3. Double Top/Bottom breakout
4. Flag / Pennant breakout
5. Rectangle breakout

---

## 12. services/pattern_engine.py 수정 지침

현재:
```python
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
```

이 구조 유지 가능.

단, 아래 추가:
```python
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
    TripleTop(),
    TripleBottom(),
    Rectangle(),
    RisingWedge(),
    FallingWedge(),
    BullFlag(),
    BearFlag(),
    BullPennant(),
    BearPennant(),
]
```

### 주의
- 새 패턴 추가 후에도 기존 Top 3 반환 구조는 유지
- 기존 프론트는 새 패턴명이 와도 그대로 표시 가능해야 함

---

## 13. 60거래일 규칙 유지 원칙

기존 `CLAUDE.md`의 최소 데이터 요건:

> 60거래일 미만이면 분석 불가

이 규칙은 유지한다.

### 이유
1. MA60 계산 필요
2. double/triangle/head-shoulders 구조 확보
3. 전체 서비스 동작의 일관성 유지

### 단, 내부적으로는 허용
- 60일 이상 데이터가 들어오면
- detector별로 최근 20/30/40/60일 구간을 따로 훑는 것은 가능

즉:
- **입력 최소 요건 60일 유지**
- **내부 탐지 스케일은 더 짧게 허용**

---

## 14. 구현 순서 재정리

기존 개발 순서를 깨지 않고, 아래처럼 확장한다.

### Phase A — 기존 9개 고도화
1. preprocessor 개선
2. breakout helper 도입
3. volume 보조 규칙 도입
4. triangle breakout 상태 추가
5. H&S / Double 패턴 보완

### Phase B — 새 패턴 추가
1. Triple Top / Bottom
2. Rectangle
3. Wedge
4. Flag / Pennant

### Phase C — 선택 확장
1. Rounding
2. Cup and Handle
3. Broadening

---

## 15. Codex / Claude에게 줄 직접 지시문

아래 문장을 그대로 사용 가능:

> 기존 `CLAUDE.md`를 절대 깨지 말고, 현재 디렉토리 구조와 인터페이스를 유지한 상태에서 패턴 엔진만 보완하라.  
> 기존 9개 패턴은 그대로 유지하되 정확도를 높이고, 새로운 패턴은 추가 파일로 확장하라.  
> `BasePattern`, `PatternResult`, `preprocess(df)`, `/api/analyze` 응답 형식은 가능한 한 유지하라.  
> 새 기능은 기존 코드 위에 additive하게 얹어라.  
> breaking change를 만들지 마라.

---

## 16. 최종 요약

이 문서의 목적은 기존 `CLAUDE.md`를 부정하는 것이 아니다.

핵심은 아래 두 가지다.

1. **기존 구조를 보존**
2. **패턴 엔진만 더 똑똑하게 확장**

즉, 이 프로젝트는 다음 방향으로 간다:

- 기존 9개 패턴 유지
- 감지 로직 정교화
- breakout / breakdown 감지 추가
- 거래량 보조 점수 추가
- Triple / Rectangle / Wedge / Flag / Pennant 추가
- 기존 API와 프론트는 최대한 그대로 유지

이 문서는 반드시 **보완 문서**로만 사용한다.
