#!/bin/bash

# 1.1.1 파일 업로드 테스트 스크립트
# Usage: ./test_111_upload.sh

echo "======================================="
echo "1.1.1 파일 업로드 기능 테스트"
echo "======================================="

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8800"
LOGIN_URL="$BASE_URL/api/v1/auth/login"
TEST_URL="$BASE_URL/api/v1/file-upload/test/1.1.1"
UPLOAD_URL="$BASE_URL/api/v1/file-upload/process/1.1.1"

# 1. 관리자 로그인
echo -e "\n1. 관리자 로그인..."
LOGIN_RESPONSE=$(curl -s -X POST "$LOGIN_URL" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123!@#"}' \
    -c cookie.txt)

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ 로그인 성공${NC}"
else
    echo -e "${RED}✗ 로그인 실패${NC}"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

# 2. 테스트 엔드포인트 확인
echo -e "\n2. 테스트 엔드포인트 확인..."
TEST_RESPONSE=$(curl -s -X GET "$TEST_URL" \
    -b cookie.txt)

if echo "$TEST_RESPONSE" | grep -q "ready"; then
    echo -e "${GREEN}✓ 엔드포인트 준비 완료${NC}"
    echo "$TEST_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TEST_RESPONSE"
else
    echo -e "${RED}✗ 엔드포인트 확인 실패${NC}"
    echo "$TEST_RESPONSE"
fi

# 3. 파일 경로 확인
echo -e "\n3. 테스트 파일 확인..."
PDF_FILE="applib/pdf/1.1.1._정확한_환자_확인_202503개정.pdf"
DOCX_FILE="applib/docx/1.1.1._정확한_환자_확인_202503개정.docx"

if [ -f "$PDF_FILE" ]; then
    echo -e "${GREEN}✓ PDF 파일 존재: $PDF_FILE${NC}"
else
    echo -e "${RED}✗ PDF 파일 없음: $PDF_FILE${NC}"
fi

if [ -f "$DOCX_FILE" ]; then
    echo -e "${GREEN}✓ DOCX 파일 존재: $DOCX_FILE${NC}"
else
    echo -e "${RED}✗ DOCX 파일 없음: $DOCX_FILE${NC}"
fi

# 4. 파일 업로드 테스트 (실제 파일이 있는 경우만)
if [ -f "$PDF_FILE" ] && [ -f "$DOCX_FILE" ]; then
    echo -e "\n4. 파일 업로드 및 병합 테스트..."
    UPLOAD_RESPONSE=$(curl -s -X POST "$UPLOAD_URL" \
        -b cookie.txt \
        -F "pdf_file=@$PDF_FILE" \
        -F "docx_file=@$DOCX_FILE")

    if echo "$UPLOAD_RESPONSE" | grep -q "success"; then
        echo -e "${GREEN}✓ 업로드 및 병합 성공${NC}"
        echo "$UPLOAD_RESPONSE" | python3 -m json.tool | head -50
    else
        echo -e "${RED}✗ 업로드 실패${NC}"
        echo "$UPLOAD_RESPONSE"
    fi
else
    echo -e "\n4. 파일 업로드 테스트 스킵 (파일 없음)"
fi

# 5. 웹 UI 테스트 페이지 정보
echo -e "\n5. 웹 UI 테스트 페이지"
echo "======================================="
echo "브라우저에서 다음 주소로 접속하세요:"
echo -e "${GREEN}$BASE_URL/test/upload/111${NC}"
echo "관리자 계정으로 로그인 후 테스트 가능합니다."

# 쿠키 파일 삭제
rm -f cookie.txt

echo -e "\n테스트 완료!"