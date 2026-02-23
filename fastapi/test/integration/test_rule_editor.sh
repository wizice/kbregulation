#!/bin/bash

# 규정 편집기 통합 테스트
# 삭제, 수정, 파일 파싱 기능 테스트

echo "🧪 규정 편집기 통합 테스트 시작"
echo "================================"

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# API URL
BASE_URL="http://localhost:8800"
API_URL="${BASE_URL}/api/v1"

# 테스트 결과 카운터
PASS=0
FAIL=0

# 함수: 테스트 결과 출력
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $2"
        ((FAIL++))
    fi
}

# 1. 로그인
echo -e "\n${YELLOW}1. 로그인${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"admin\",\"password\":\"admin123!@#\"}" \
    -c cookies.txt)

if echo "$LOGIN_RESPONSE" | grep -q '"access_token"'; then
    print_result 0 "로그인 성공"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
else
    print_result 1 "로그인 실패"
    echo "  응답: $LOGIN_RESPONSE"
    exit 1
fi

# 2. 규정 목록 조회
echo -e "\n${YELLOW}2. 규정 목록 조회${NC}"
RULES_RESPONSE=$(curl -s -X GET "${API_URL}/regulation/current?limit=1" \
    -H "Content-Type: application/json" \
    -b cookies.txt)

if echo "$RULES_RESPONSE" | grep -q '"wzruleseq"'; then
    print_result 0 "규정 목록 조회 성공"
    # 첫 번째 규정 ID 추출
    RULE_ID=$(echo "$RULES_RESPONSE" | grep -o '"wzruleseq":[0-9]*' | head -1 | cut -d':' -f2)
    echo "  테스트할 규정 ID: $RULE_ID"
else
    print_result 1 "규정 목록 조회 실패"
    echo "  응답: $RULES_RESPONSE"
    RULE_ID=1  # 기본값 설정
fi

# 3. 규정 수정 테스트
echo -e "\n${YELLOW}3. 규정 수정 테스트${NC}"
UPDATE_RESPONSE=$(curl -s -X PUT "${API_URL}/rule/update" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d '{
        "wzruleseq": '$RULE_ID',
        "wzname": "테스트 규정 - 수정됨",
        "wzpubno": "TEST-001",
        "wzmgrdptnm": "정보팀",
        "wzestabdate": "2024-01-01",
        "wzexecdate": "2024-01-02",
        "content_text": "수정된 규정 내용입니다."
    }')

if echo "$UPDATE_RESPONSE" | grep -q '"success":true'; then
    print_result 0 "규정 수정 성공"
else
    print_result 1 "규정 수정 실패"
    echo "  응답: $UPDATE_RESPONSE"
fi

# 4. DOCX 파일 파싱 테스트 (샘플 파일 생성)
echo -e "\n${YELLOW}4. DOCX 파일 파싱 테스트${NC}"

# Python으로 간단한 DOCX 파일 생성
python3 -c "
try:
    import docx
    doc = docx.Document()
    doc.add_heading('테스트 규정', 0)
    doc.add_paragraph('제1조 (목적) 이 규정은 테스트를 위한 것입니다.')
    doc.add_paragraph('제2조 (적용범위) 모든 부서에 적용됩니다.')
    doc.save('/tmp/test_regulation.docx')
    print('DOCX 파일 생성 완료')
except ImportError:
    print('python-docx 라이브러리가 설치되지 않았습니다.')
    exit(1)
"

if [ -f "/tmp/test_regulation.docx" ]; then
    PARSE_RESPONSE=$(curl -s -X POST "${API_URL}/rule/parse-revision" \
        -b cookies.txt \
        -F "file=@/tmp/test_regulation.docx" \
        -F "rule_id=$RULE_ID" \
        -F "reason=테스트 개정" \
        -F "revision_date=2024-01-01")

    if echo "$PARSE_RESPONSE" | grep -q '"success":true'; then
        print_result 0 "DOCX 파싱 성공"
        echo "  파싱된 텍스트 길이: $(echo "$PARSE_RESPONSE" | grep -o '"total_length":[0-9]*' | cut -d':' -f2)"
    else
        print_result 1 "DOCX 파싱 실패"
        echo "  응답: $PARSE_RESPONSE"
    fi
else
    print_result 1 "DOCX 테스트 파일 생성 실패"
fi

# 5. PDF 파일 파싱 테스트
echo -e "\n${YELLOW}5. PDF 파일 파싱 테스트${NC}"

# PDF 테스트는 파일이 있는 경우만
if [ -f "/tmp/test_regulation.pdf" ]; then
    PARSE_PDF_RESPONSE=$(curl -s -X POST "${API_URL}/rule/parse-revision" \
        -b cookies.txt \
        -F "file=@/tmp/test_regulation.pdf" \
        -F "rule_id=$RULE_ID" \
        -F "reason=PDF 테스트 개정")

    if echo "$PARSE_PDF_RESPONSE" | grep -q '"success":true'; then
        print_result 0 "PDF 파싱 성공"
    else
        print_result 1 "PDF 파싱 실패"
    fi
else
    echo "  PDF 테스트 파일이 없어 스킵합니다."
fi

# 6. 개정판 생성 테스트
echo -e "\n${YELLOW}6. 개정판 생성 테스트${NC}"
REVISION_RESPONSE=$(curl -s -X POST "${API_URL}/rule/create-revision/$RULE_ID" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d '{
        "wzname": "테스트 규정 - 개정판",
        "wzpubno": "TEST-002",
        "wzmgrdptnm": "정보팀",
        "wzestabdate": "2024-02-01",
        "wzexecdate": "2024-02-02",
        "content_text": "개정된 규정 내용입니다."
    }')

if echo "$REVISION_RESPONSE" | grep -q '"success":true'; then
    print_result 0 "개정판 생성 성공"
    NEW_RULE_ID=$(echo "$REVISION_RESPONSE" | grep -o '"new_rule_id":[0-9]*' | cut -d':' -f2)
    echo "  새 규정 ID: $NEW_RULE_ID"
else
    print_result 1 "개정판 생성 실패"
    echo "  응답: $REVISION_RESPONSE"
fi

# 7. 규정 삭제 테스트 (새로 생성된 개정판 삭제)
echo -e "\n${YELLOW}7. 규정 삭제 테스트${NC}"
if [ ! -z "$NEW_RULE_ID" ]; then
    DELETE_RESPONSE=$(curl -s -X DELETE "${API_URL}/rule/delete/$NEW_RULE_ID" \
        -H "Content-Type: application/json" \
        -b cookies.txt)

    if echo "$DELETE_RESPONSE" | grep -q '"success":true'; then
        print_result 0 "규정 삭제 성공"
    else
        print_result 1 "규정 삭제 실패"
        echo "  응답: $DELETE_RESPONSE"
    fi
else
    echo "  삭제할 규정 ID가 없어 스킵합니다."
fi

# 8. 로그아웃
echo -e "\n${YELLOW}8. 로그아웃${NC}"
LOGOUT_RESPONSE=$(curl -s -X POST "${API_URL}/auth/logout" \
    -H "Content-Type: application/json" \
    -b cookies.txt)

if echo "$LOGOUT_RESPONSE" | grep -q '"message"'; then
    print_result 0 "로그아웃 성공"
else
    print_result 1 "로그아웃 실패"
fi

# 테스트 결과 요약
echo -e "\n================================"
echo -e "${YELLOW}테스트 결과 요약${NC}"
echo -e "성공: ${GREEN}$PASS${NC}"
echo -e "실패: ${RED}$FAIL${NC}"

# 쿠키 파일 삭제
rm -f cookies.txt
rm -f /tmp/test_regulation.docx

if [ $FAIL -eq 0 ]; then
    echo -e "\n${GREEN}✨ 모든 테스트가 성공했습니다!${NC}"
    exit 0
else
    echo -e "\n${RED}⚠️  일부 테스트가 실패했습니다.${NC}"
    exit 1
fi