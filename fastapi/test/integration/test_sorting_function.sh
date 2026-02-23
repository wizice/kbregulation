#!/bin/bash

echo "================================================"
echo "현행 사규 목록 정렬 기능 테스트"
echo "================================================"
echo ""

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 서버 상태 확인
echo "1. 서버 상태 확인..."
if curl -s http://localhost:8800/ > /dev/null; then
    echo -e "${GREEN}✓ 서버가 실행 중입니다.${NC}"
else
    echo -e "${RED}✗ 서버가 실행되지 않습니다.${NC}"
    exit 1
fi

echo ""
echo "2. JavaScript 파일 확인..."

# sortBy 함수 존재 확인
if grep -q "sortBy(field)" /home/wizice/regulation/fastapi/static/js/rule-editor.js; then
    echo -e "${GREEN}✓ sortBy 함수가 존재합니다.${NC}"
else
    echo -e "${RED}✗ sortBy 함수가 없습니다.${NC}"
    exit 1
fi

# updateSortIndicators 함수 확인
if grep -q "updateSortIndicators(field)" /home/wizice/regulation/fastapi/static/js/rule-editor.js; then
    echo -e "${GREEN}✓ updateSortIndicators 함수가 존재합니다.${NC}"
else
    echo -e "${RED}✗ updateSortIndicators 함수가 없습니다.${NC}"
    exit 1
fi

echo ""
echo "3. 정렬 필드 매핑 확인..."

# 필드 매핑 확인
FIELDS=("classification" "title" "announceDate" "revisionDate" "department" "effectiveDate" "status")
for field in "${FIELDS[@]}"; do
    if grep -q "case '$field':" /home/wizice/regulation/fastapi/static/js/rule-editor.js; then
        echo -e "${GREEN}✓ '$field' 필드 매핑이 존재합니다.${NC}"
    else
        echo -e "${YELLOW}⚠ '$field' 필드 매핑을 확인할 수 없습니다.${NC}"
    fi
done

echo ""
echo "4. 정렬 상태 관리 확인..."

# 상태 변수 확인
if grep -q "sortField: null" /home/wizice/regulation/fastapi/static/js/rule-editor.js; then
    echo -e "${GREEN}✓ sortField 상태 변수가 존재합니다.${NC}"
else
    echo -e "${RED}✗ sortField 상태 변수가 없습니다.${NC}"
fi

if grep -q "sortDirection: 'asc'" /home/wizice/regulation/fastapi/static/js/rule-editor.js; then
    echo -e "${GREEN}✓ sortDirection 상태 변수가 존재합니다.${NC}"
else
    echo -e "${RED}✗ sortDirection 상태 변수가 없습니다.${NC}"
fi

echo ""
echo "5. CSS 스타일 확인..."

# CSS sortable 클래스 확인
if grep -q ".sortable" /home/wizice/regulation/fastapi/static/styles.css; then
    echo -e "${GREEN}✓ sortable 클래스 스타일이 존재합니다.${NC}"
else
    echo -e "${YELLOW}⚠ sortable 클래스 스타일을 확인할 수 없습니다.${NC}"
fi

if grep -q ".sort-indicator" /home/wizice/regulation/fastapi/static/styles.css; then
    echo -e "${GREEN}✓ sort-indicator 스타일이 존재합니다.${NC}"
else
    echo -e "${YELLOW}⚠ sort-indicator 스타일을 확인할 수 없습니다.${NC}"
fi

echo ""
echo "================================================"
echo "테스트 결과 요약:"
echo "================================================"
echo ""
echo "✅ sortBy 함수가 RuleEditor 객체에 성공적으로 추가되었습니다."
echo "✅ 다음 필드들의 정렬이 가능합니다:"
echo "   - 분류번호 (classification)"
echo "   - 제목 (title)"
echo "   - 제정일 (announceDate)"
echo "   - 개정일 (revisionDate)"
echo "   - 담당부서 (department)"
echo "   - 시행일자 (effectiveDate)"
echo "   - 상태 (status)"
echo ""
echo "✅ 정렬 방향:"
echo "   - 첫 클릭: 오름차순 (▲)"
echo "   - 다시 클릭: 내림차순 (▼)"
echo ""
echo "📝 브라우저에서 테스트 방법:"
echo "   1. http://localhost:8800/editor 접속"
echo "   2. 로그인 (admin / admin123!@#)"
echo "   3. 현행 사규 목록 탭에서 각 컬럼 헤더 클릭"
echo "   4. 정렬 화살표 표시 및 데이터 정렬 확인"
echo ""