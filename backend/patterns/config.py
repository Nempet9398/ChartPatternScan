"""
Lo, Mamaysky & Wang (2000) 논문 기반 허용 오차 상수.

변경 시 반드시 주석에 근거 명시.
"""

# ── 헤드앤숄더 / 역헤드앤숄더 ──────────────────────────────────────────────
SHOULDER_TOLERANCE = 0.015   # 어깨 높이 허용 오차 1.5%  (Lo 2000)
NECKLINE_TOLERANCE = 0.015   # 넥라인 수평 허용 오차 1.5% (Lo 2000)

# ── 더블탑 / 더블바텀 ──────────────────────────────────────────────────────
DOUBLE_TOLERANCE   = 0.015   # 두 극값 가격 허용 오차 1.5% (Lo 2000)
DOUBLE_MIN_DAYS    = 22      # 두 극값 최소 간격(거래일)   (Lo 2000, Edwards & Magee)

# ── 전처리 공통 ─────────────────────────────────────────────────────────────
SMOOTH_WINDOW      = 5       # 스무딩 MA 윈도우 (Lo 2000 커널회귀 대체)
PEAK_MIN_DISTANCE  = 5       # 최소 피크 간격 (거래일)
PEAK_MIN_PROMINENCE = 0.02   # 최소 피크 돌출도 (정규화 기준 0~1)

# ── 삼각수렴 ────────────────────────────────────────────────────────────────
TRIANGLE_SLOPE_FLAT = 0.001  # 수평으로 간주할 기울기 임계값 (Lo 2000)

# ── 확장 상수 (CLAUDE_APPENDIX_PATTERN_ENGINE.md) ────────────────────────────
PEAK_MIN_WIDTH              = 1      # 최소 피크 너비
BREAKOUT_EPSILON            = 0.005  # 돌파 판정 여유율 0.5%
BREAKOUT_FOLLOWTHROUGH_BARS = 3      # 돌파 후 유지 확인 봉 수
FAILED_BREAKOUT_PENALTY     = 0.15   # 실패 돌파 감점 비율

VOLUME_MA_WINDOW            = 20     # 거래량 이동평균 윈도우
VOLUME_SURGE_RATIO          = 1.2    # 거래량 급증 기준 비율 (1.2배 이상)

# ── 트리플 패턴 ──────────────────────────────────────────────────────────────
TRIPLE_TOLERANCE            = 0.02   # 세 극값 높이 허용 오차 2%
TRIPLE_MIN_DAYS             = 10     # 각 극값 간 최소 간격(거래일)

# ── 직사각형(박스권) ─────────────────────────────────────────────────────────
RECTANGLE_SLOPE_FLAT        = 0.0015 # 상/하단선 수평 허용 기울기
RECTANGLE_MIN_TOUCHES       = 2      # 상/하단선 최소 터치 횟수

# ── 쐐기형(Wedge) ────────────────────────────────────────────────────────────
WEDGE_MIN_BARS              = 10     # 웨지 최소 길이(봉 수)
WEDGE_CONVERGENCE_MIN       = 0.3    # 수렴 최소 비율 (30% 이상 좁아져야 함)

# ── 깃발/페넌트(Flag/Pennant) ────────────────────────────────────────────────
FLAG_POLE_MIN_MOVE          = 0.05   # 폴 최소 이동폭 5%
FLAG_CONSOLIDATION_MAX_BARS = 30     # 조정 구간 최대 봉 수
FLAG_CONSOLIDATION_MIN_BARS = 5      # 조정 구간 최소 봉 수
