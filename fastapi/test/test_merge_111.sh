#!/bin/bash

# 1.1.1 병합 테스트 스크립트
# Usage: ./test_merge_111.sh

echo "======================================="
echo "1.1.1 병합 기능 테스트"
echo "======================================="

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8800"
LOGIN_URL="$BASE_URL/api/v1/auth/login"
FILES_URL="$BASE_URL/api/v1/merge/1.1.1/files"
MERGE_URL="$BASE_URL/api/v1/merge/1.1.1"

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

# 2. 사용 가능한 1.1.1 파일 목록 확인
echo -e "\n2. 사용 가능한 1.1.1 파일 확인..."
FILES_RESPONSE=$(curl -s -X GET "$FILES_URL" \
    -b cookie.txt)

if echo "$FILES_RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✓ 파일 목록 조회 성공${NC}"
    echo "$FILES_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20
else
    echo -e "${RED}✗ 파일 목록 조회 실패${NC}"
    echo "$FILES_RESPONSE"
fi

# 3. 로컬 파일 시스템 확인
echo -e "\n3. 로컬 파일 확인..."
echo -e "${YELLOW}DOCX JSON 최신 파일:${NC}"
ls -lt applib/docx_json/*1.1.1* 2>/dev/null | head -3

echo -e "\n${YELLOW}TXT JSON 최신 파일:${NC}"
ls -lt applib/txt_json/*1.1.1* 2>/dev/null | head -3

# 4. 1.1.1 병합 실행
echo -e "\n4. 1.1.1 병합 실행..."
MERGE_RESPONSE=$(curl -s -X POST "$MERGE_URL" \
    -b cookie.txt \
    -H "Content-Type: application/json")

if echo "$MERGE_RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✓ 병합 성공${NC}"

    # 결과 파일 경로 추출
    OUTPUT_FILE=$(echo "$MERGE_RESPONSE" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('output_file', ''))" 2>/dev/null)

    if [ -n "$OUTPUT_FILE" ]; then
        echo -e "\n${GREEN}출력 파일: $OUTPUT_FILE${NC}"

        # 파일 크기 확인
        if [ -f "$OUTPUT_FILE" ]; then
            FILE_SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
            echo -e "파일 크기: $FILE_SIZE"

            # 파일 내용 미리보기 (처음 30줄)
            echo -e "\n${YELLOW}병합된 내용 미리보기:${NC}"
            head -30 "$OUTPUT_FILE"
        fi
    fi

    # 사용된 파일 정보
    echo -e "\n${YELLOW}사용된 파일:${NC}"
    echo "$MERGE_RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data.get('docx_file'):
    print(f\"DOCX: {data['docx_file']}\")
if data.get('txt_file'):
    print(f\"TXT:  {data['txt_file']}\")
" 2>/dev/null

else
    echo -e "${RED}✗ 병합 실패${NC}"
    echo "$MERGE_RESPONSE"
fi

# 5. merge_json 디렉토리 확인
echo -e "\n5. 병합 결과 디렉토리 확인..."
echo -e "${YELLOW}최근 병합 파일:${NC}"
ls -lt applib/merge_json/*1.1.1* 2>/dev/null | head -5

# 쿠키 파일 삭제
rm -f cookie.txt

echo -e "\n======================================="
echo "테스트 완료!"
echo "======================================="