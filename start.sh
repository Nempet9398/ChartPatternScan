#!/usr/bin/env bash
# ChartPattern.io 로컬 실행 스크립트
# 사용법: bash start.sh

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== ChartPattern.io 로컬 실행 ==="
echo ""

# ── 백엔드 ────────────────────────────────────────────────────────────────────
echo "[1/3] 백엔드 의존성 확인..."
cd "$ROOT/backend"
pip install -q -r requirements.txt

echo "[2/3] 백엔드 서버 기동 (http://localhost:8000)..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 서버 준비 대기
for i in {1..20}; do
  if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "      백엔드 준비 완료"
    break
  fi
  sleep 0.5
done

# ── 프론트엔드 ────────────────────────────────────────────────────────────────
echo "[3/3] 프론트엔드 서버 기동 (http://localhost:3000)..."
cd "$ROOT/frontend"

# .env.local 없으면 생성
if [ ! -f .env.local ]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
  echo "      .env.local 생성됨"
fi

npm install -q 2>/dev/null || true
npm run dev &
FRONTEND_PID=$!

echo ""
echo "======================================="
echo "  백엔드  : http://localhost:8000"
echo "  프론트  : http://localhost:3000"
echo "  API 문서: http://localhost:8000/docs"
echo "======================================="
echo ""
echo "종료하려면 Ctrl+C 를 누르세요."

# Ctrl+C 시 두 서버 모두 종료
trap "echo ''; echo '서버 종료 중...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
