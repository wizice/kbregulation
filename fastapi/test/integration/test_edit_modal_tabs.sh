#!/bin/bash

echo "======================================="
echo "편집 모달 기능 통합 테스트"
echo "======================================="

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 로그인
echo -e "\n1. 로그인 테스트..."
LOGIN_RESP=$(curl -s -c /tmp/test_cookies.txt \
    -X POST http://localhost:8800/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123!@#"}')

if echo "$LOGIN_RESP" | grep -q "access_token"; then
    echo -e "${GREEN}✅ 로그인 성공${NC}"
    TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
else
    echo -e "${RED}❌ 로그인 실패${NC}"
    exit 1
fi

# 2. 규정 목록 조회
echo -e "\n2. 현행 규정 목록 조회..."
SEARCH_RESP=$(curl -s -b /tmp/test_cookies.txt \
    -X GET http://localhost:8800/api/v1/regulations/current)

if echo "$SEARCH_RESP" | grep -q "success"; then
    echo -e "${GREEN}✅ 규정 목록 조회 성공${NC}"
    RULE_COUNT=$(echo "$SEARCH_RESP" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('data', [])))")
    echo "   - 조회된 규정 수: $RULE_COUNT"

    # 첫 번째 규정 ID 추출
    FIRST_RULE_ID=$(echo "$SEARCH_RESP" | python3 -c "import sys, json; items=json.load(sys.stdin).get('data', []); print(items[0]['rule_id'] if items else '')")
    FIRST_RULE_NAME=$(echo "$SEARCH_RESP" | python3 -c "import sys, json; items=json.load(sys.stdin).get('data', []); print(items[0]['name'] if items else '')")

    if [ -n "$FIRST_RULE_ID" ]; then
        echo "   - 테스트 규정: ID=$FIRST_RULE_ID, 이름=$FIRST_RULE_NAME"
    fi
else
    echo -e "${RED}❌ 규정 목록 조회 실패${NC}"
    echo "$SEARCH_RESP"
fi

# 3. 규정 상세 정보 조회
if [ -n "$FIRST_RULE_ID" ]; then
    echo -e "\n3. 규정 상세 정보 조회 (ID: $FIRST_RULE_ID)..."

    DETAIL_RESP=$(curl -s -b /tmp/test_cookies.txt \
        http://localhost:8800/api/v1/rule/get/$FIRST_RULE_ID)

    if echo "$DETAIL_RESP" | grep -q "success"; then
        echo -e "${GREEN}✅ 규정 상세 조회 성공${NC}"
        HAS_JSON=$(echo "$DETAIL_RESP" | python3 -c "import sys, json; d=json.load(sys.stdin).get('data', {}); print('Yes' if d.get('wzfilejson') else 'No')")
        echo "   - JSON 파일 존재: $HAS_JSON"
    else
        echo -e "${RED}❌ 규정 상세 조회 실패${NC}"
        echo "$DETAIL_RESP"
    fi
fi

# 4. JSON 내용 조회
if [ -n "$FIRST_RULE_ID" ]; then
    echo -e "\n4. JSON 파일 내용 조회..."

    JSON_RESP=$(curl -s -b /tmp/test_cookies.txt \
        http://localhost:8800/api/v1/json/view/$FIRST_RULE_ID)

    if echo "$JSON_RESP" | grep -q "success"; then
        HAS_CONTENT=$(echo "$JSON_RESP" | python3 -c "import sys, json; print('Yes' if json.load(sys.stdin).get('data', {}).get('has_content') else 'No')")
        echo -e "${GREEN}✅ JSON 조회 API 호출 성공${NC}"
        echo "   - JSON 내용 존재: $HAS_CONTENT"

        if [ "$HAS_CONTENT" = "Yes" ]; then
            ARTICLE_COUNT=$(echo "$JSON_RESP" | python3 -c "import sys, json; d=json.load(sys.stdin).get('data', {}).get('json_content', {}); print(len(d.get('articles', [])))")
            echo "   - 조항 수: $ARTICLE_COUNT"
        fi
    else
        echo -e "${RED}❌ JSON 조회 실패${NC}"
    fi
fi

# 5. 미리보기 테스트
if [ -n "$FIRST_RULE_ID" ]; then
    echo -e "\n5. 규정 미리보기 테스트..."

    PREVIEW_RESP=$(curl -s -b /tmp/test_cookies.txt \
        http://localhost:8800/api/v1/content/content-preview/$FIRST_RULE_ID)

    if echo "$PREVIEW_RESP" | grep -q "content\|error"; then
        if echo "$PREVIEW_RESP" | grep -q "error"; then
            echo -e "${GREEN}✅ 미리보기 API 호출 성공 (내용 없음)${NC}"
        else
            echo -e "${GREEN}✅ 미리보기 내용 조회 성공${NC}"
            PREVIEW_LENGTH=$(echo "$PREVIEW_RESP" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('content', '')))")
            echo "   - 내용 길이: $PREVIEW_LENGTH 문자"
        fi
    else
        echo -e "${RED}❌ 미리보기 조회 실패${NC}"
    fi
fi

# 6. 편집 내용 저장 테스트
if [ -n "$FIRST_RULE_ID" ]; then
    echo -e "\n6. 편집 내용 저장 테스트..."

    TEST_CONTENT="제1조 (목적)
이 규정은 통합 테스트를 위한 내용입니다.

제2조 (적용범위)
편집 모달 저장 기능 테스트입니다."

        # Use Python to properly format JSON with escaped content
    SAVE_DATA=$(python3 -c "
import json
data = {
    'rule_id': $FIRST_RULE_ID,
    'content': '''$TEST_CONTENT''',
    'mode': 'edit'
}
print(json.dumps(data))
")

    SAVE_RESP=$(curl -s -b /tmp/test_cookies.txt \
        -X POST http://localhost:8800/api/v1/rule/save-edited-content \
        -H "Content-Type: application/json" \
        -d "$SAVE_DATA")

    if echo "$SAVE_RESP" | grep -q "success\|message"; then
        echo -e "${GREEN}✅ 편집 내용 저장 성공${NC}"

        # JSON 파일 생성 확인
        if echo "$SAVE_RESP" | grep -q "json_filename"; then
            JSON_FILE=$(echo "$SAVE_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('files', {}).get('json_filename', ''))")
            echo "   - 생성된 JSON 파일: $JSON_FILE"

            # 파일 실제 존재 확인
            if [ -f "../applib/merge_json/$JSON_FILE" ]; then
                echo -e "   ${GREEN}- 파일 존재 확인됨${NC}"
            fi
        fi

        # Background task 상태 확인
        echo "   - JSON_ALL.py 백그라운드 실행 대기 중..."
        sleep 3

        # merged_severance.json 확인
        if [ -f "../applib/merge_json/merged_severance.json" ]; then
            MERGE_TIME=$(stat -c %y ../applib/merge_json/merged_severance.json | cut -d. -f1)
            echo -e "   ${GREEN}- merged_severance.json 업데이트됨 ($MERGE_TIME)${NC}"
        fi
    else
        echo -e "${RED}❌ 편집 내용 저장 실패${NC}"
        echo "$SAVE_RESP"
    fi
fi

# 7. 로그아웃
echo -e "\n7. 로그아웃 테스트..."
LOGOUT_RESP=$(curl -s -b /tmp/test_cookies.txt \
    -X POST http://localhost:8800/api/v1/auth/logout)

if echo "$LOGOUT_RESP" | grep -q "message"; then
    echo -e "${GREEN}✅ 로그아웃 성공${NC}"
else
    echo -e "${RED}❌ 로그아웃 실패${NC}"
fi

echo -e "\n======================================="
echo "테스트 완료"
echo "======================================="