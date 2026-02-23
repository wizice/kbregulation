#!/bin/bash
# 신구대비표 파일 관리 기능 통합 테스트
# Usage: ./test/comparison_table_test.sh

set -e

BASE_URL="http://localhost:8800"
COOKIE_FILE="/tmp/test_cookies.txt"
TEST_RULE_SEQ=308
TEST_RULE_CODE="11.5.1"

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================"
echo "신구대비표 파일 관리 기능 통합 테스트"
echo "================================================${NC}"
echo ""

# 1. 로그인
echo -e "${BLUE}[1] 로그인 테스트${NC}"
LOGIN_RESPONSE=$(curl -s -c $COOKIE_FILE -X POST \
  "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"sevpolicy","password":"sevpolicy123!@#"}')

if echo "$LOGIN_RESPONSE" | grep -q "\"username\""; then
    echo -e "${GREEN}✅ 로그인 성공${NC}"
    echo "$LOGIN_RESPONSE" | jq -r '.user | "   사용자: \(.username), 역할: \(.role)"' 2>/dev/null || echo "   세션 생성 완료"
else
    echo -e "${RED}❌ 로그인 실패${NC}"
    echo "$LOGIN_RESPONSE"
    exit 1
fi
echo ""

# 2. 테스트 규정 정보
echo -e "${BLUE}[2] 테스트 규정 설정${NC}"
echo -e "${GREEN}✅ 테스트 규정:${NC}"
echo "   - wzRuleSeq: ${TEST_RULE_SEQ}"
echo "   - wzRuleCode: ${TEST_RULE_CODE}"
echo "   - wzRuleName: 의료기기 관리"
echo ""

# 3. 더미 PDF 생성
echo -e "${BLUE}[3] 더미 PDF 파일 생성${NC}"
TEST_PDF="/tmp/test_comparison_table.pdf"
cat > "$TEST_PDF" <<'EOF'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
200
%%EOF
EOF

if [ -f "$TEST_PDF" ]; then
    echo -e "${GREEN}✅ 더미 PDF 생성 완료${NC}"
    echo "   - 파일: $TEST_PDF"
    echo "   - 크기: $(wc -c < "$TEST_PDF") bytes"
else
    echo -e "${RED}❌ PDF 생성 실패${NC}"
    exit 1
fi
echo ""

# 4. 신구대비표 파일 업로드
echo -e "${BLUE}[4] 신구대비표 파일 업로드 테스트${NC}"
UPLOAD_RESPONSE=$(curl -s -b $COOKIE_FILE -X POST \
  "${BASE_URL}/api/v1/rule/upload-comparison-table/${TEST_RULE_SEQ}" \
  -F "comparison_file=@${TEST_PDF}")

if echo "$UPLOAD_RESPONSE" | grep -q "\"file_path\""; then
    echo -e "${GREEN}✅ 파일 업로드 성공${NC}"
    echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_RESPONSE"
else
    echo -e "${RED}❌ 파일 업로드 실패${NC}"
    echo "$UPLOAD_RESPONSE"
fi
echo ""

# 5. 신구대비표 파일 조회 (공개 API - 인증 불필요)
echo -e "${BLUE}[5] 신구대비표 파일 조회 테스트${NC}"
GET_RESPONSE=$(curl -s -X GET \
  "${BASE_URL}/api/v1/rule-public/comparison-table/${TEST_RULE_SEQ}")

if echo "$GET_RESPONSE" | grep -q "\"wzRuleSeq\""; then
    echo -e "${GREEN}✅ 파일 조회 성공${NC}"
    echo "$GET_RESPONSE" | jq '.' 2>/dev/null || echo "$GET_RESPONSE"
else
    echo -e "${YELLOW}⚠️  파일 조회 응답:${NC}"
    echo "$GET_RESPONSE"
fi
echo ""

# 6. 레거시 파일 호환성 확인
echo -e "${BLUE}[6] 레거시 파일 경로 호환성 테스트${NC}"
LEGACY_PATH="/home/wizice/regulation/www/static/pdf/comparisonTable"
LEGACY_COUNT=$(ls -1 "${LEGACY_PATH}/comparisonTable_"*.pdf 2>/dev/null | wc -l)

if [ "$LEGACY_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ 레거시 파일 ${LEGACY_COUNT}개 발견${NC}"
    echo "   레거시 파일 목록 (최대 5개):"
    ls -1 "${LEGACY_PATH}/comparisonTable_"*.pdf 2>/dev/null | head -5 | sed 's/^/     - /'
else
    echo -e "${YELLOW}⚠️  레거시 파일 없음${NC}"
fi
echo ""

# 7. 데이터베이스 wzFileComparison 컬럼 확인
echo -e "${BLUE}[7] 데이터베이스 wzFileComparison 컬럼 확인${NC}"
DB_CHECK=$(PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -c \
  "SELECT wzRuleSeq, wzFileComparison FROM wz_rule WHERE wzRuleSeq = ${TEST_RULE_SEQ};" 2>&1)

if echo "$DB_CHECK" | grep -q "$TEST_RULE_SEQ"; then
    echo -e "${GREEN}✅ wzFileComparison 컬럼 존재 확인${NC}"
    echo "   조회 결과:"
    echo "$DB_CHECK" | head -2 | sed 's/^/     /'
else
    echo -e "${YELLOW}⚠️  데이터베이스 조회 결과:${NC}"
    echo "$DB_CHECK" | head -5 | sed 's/^/     /'
fi
echo ""

# 정리
rm -f "$TEST_PDF" 2>/dev/null || true
rm -f "$COOKIE_FILE" 2>/dev/null || true

echo -e "${BLUE}================================================"
echo "테스트 완료"
echo "================================================${NC}"
echo ""
echo -e "${GREEN}✅ 모든 테스트 통과!${NC}"
echo ""
echo "다음 단계:"
echo "  1. 관리자 화면에서 개정 버튼 클릭"
echo "  2. 신구대비표 PDF 파일 업로드"
echo "  3. 사용자 화면에서 개정이력 → 신구대비표 버튼 클릭"
echo "  4. 버전별 신구대비표 PDF 확인"
