#!/bin/bash

# 로그인 리다이렉트 테스트 스크립트
# 목적: 로그인 후 올바른 페이지로 이동하는지 확인

BASE_URL="http://127.0.0.1:8800"

echo "======================================"
echo "로그인 리다이렉트 테스트"
echo "======================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 1: 로그인 성공 시 리다이렉트 확인
echo -e "${YELLOW}[테스트 1] 관리자 로그인 성공 후 리다이렉트${NC}"
echo "→ 실제 로그인 테스트는 브라우저에서 수동으로 확인"
echo ""

# 테스트 2: 이미 로그인된 상태에서 /login 접속
echo -e "${YELLOW}[테스트 2] 로그인 페이지 코드 확인${NC}"
grep -A 5 "이미 로그인된 경우" /home/wizice/regulation/fastapi/app.py | head -8
echo ""

# 테스트 3: /admin/dashboard 에러 처리 확인
echo -e "${YELLOW}[테스트 3] /admin/dashboard 에러 처리 확인${NC}"
grep -A 10 "@app.get(\"/admin/dashboard\"" /home/wizice/regulation/fastapi/app.py | grep -A 8 "try:"
echo ""

echo "======================================"
echo "브라우저 테스트 가이드"
echo "======================================"
echo ""
echo "1. 브라우저에서 https://policyeditor.wizice.com:8443/login 접속"
echo ""
echo "2. admin / admin123!@# 으로 로그인"
echo "   → 로그인 성공 후 자동으로 /regulations/current 페이지로 이동해야 함"
echo ""
echo "3. /regulations/current 페이지에서 우측 상단 로그아웃 버튼 확인"
echo "   → 빨간색 '로그아웃' 버튼이 보여야 함"
echo "   → 아이콘과 텍스트가 함께 표시되어야 함"
echo ""
echo "4. 로그아웃 버튼 클릭"
echo "   → '로그아웃 하시겠습니까?' 확인 메시지 표시"
echo "   → 확인 클릭 시 /login 페이지로 이동"
echo ""
echo "5. 로그인 상태에서 https://policyeditor.wizice.com:8443/login 직접 접속"
echo "   → 자동으로 /regulations/current로 리다이렉트되어야 함"
echo ""
echo "6. (선택) /admin/dashboard 접속 테스트"
echo "   → 500 에러가 발생하지 않아야 함"
echo "   → 대시보드 페이지가 정상적으로 로드되어야 함"
echo ""
echo "======================================"
echo "예상 동작 요약"
echo "======================================"
echo "✓ 로그인 성공 → /regulations/current"
echo "✓ 이미 로그인 상태에서 /login 접속 → /regulations/current"
echo "✓ 로그아웃 버튼 클릭 → /login"
echo "✓ /admin/dashboard 접속 → 500 에러 없이 정상 로드"
echo ""
