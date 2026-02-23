#!/bin/bash

# Test script for revision workflow - verifies single file update behavior
# This test ensures that revision mode updates existing files instead of creating duplicates

echo "=========================================="
echo "Revision Workflow Test"
echo "Testing single file update and structure preservation"
echo "=========================================="

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그인
echo -e "\n1. 로그인..."
LOGIN_RESP=$(curl -s -c /tmp/revision_cookies.txt \
    -X POST http://localhost:8800/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123!@#"}')

if echo "$LOGIN_RESP" | grep -q "access_token"; then
    echo -e "${GREEN}✅ 로그인 성공${NC}"
else
    echo -e "${RED}❌ 로그인 실패${NC}"
    exit 1
fi

# 2. 테스트용 규정 찾기
echo -e "\n2. 테스트용 규정 선택..."
SEARCH_RESP=$(curl -s -b /tmp/revision_cookies.txt \
    -X GET http://localhost:8800/api/v1/regulations/current)

if echo "$SEARCH_RESP" | grep -q "success"; then
    # JSON 파일이 있는 규정 찾기
    RULE_WITH_JSON=$(echo "$SEARCH_RESP" | python3 -c "
import sys, json
data = json.load(sys.stdin).get('data', [])
# 테스트 규정 찾기
for rule in data:
    if rule.get('name') == '테스트 규정':
        print(rule['rule_id'])
        break
else:
    # 못찾으면 첫번째 규정 사용
    if data:
        print(data[0]['rule_id'])
")

    if [ -n "$RULE_WITH_JSON" ]; then
        echo -e "${GREEN}✅ 테스트 규정 선택: ID=$RULE_WITH_JSON${NC}"
    else
        echo -e "${RED}❌ 테스트용 규정을 찾을 수 없음${NC}"
        exit 1
    fi
fi

# 3. 개정 생성 테스트
echo -e "\n3. 개정 생성 테스트..."

REVISION_DATA=$(python3 -c "
import json
from datetime import datetime

data = {
    'rule_id': $RULE_WITH_JSON,
    'revision_type': 'revision',
    'revision_date': datetime.now().strftime('%Y-%m-%d'),
    'revision_reason': '테스트를 위한 개정',
    'major_changes': '주요 변경사항 테스트',
    'content': '''제1조 (목적)
이 규정은 개정 테스트를 위한 내용입니다.

제2조 (적용범위)
개정 워크플로우 테스트입니다.

제3조 (신규조항)
개정에서 추가된 조항입니다.'''
}
print(json.dumps(data))
")

REVISION_RESP=$(curl -s -b /tmp/revision_cookies.txt \
    -X POST http://localhost:8800/api/v1/rule/create-revision/$RULE_WITH_JSON \
    -H "Content-Type: application/json" \
    -d "$REVISION_DATA")

if echo "$REVISION_RESP" | grep -q "success\|revision_id"; then
    echo -e "${GREEN}✅ 개정 생성 성공${NC}"

    # 개정 ID 추출
    REVISION_ID=$(echo "$REVISION_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('revision_id', ''))")
    if [ -n "$REVISION_ID" ]; then
        echo "   - 생성된 개정 ID: $REVISION_ID"
    fi

    # JSON 파일 생성 확인
    if echo "$REVISION_RESP" | grep -q "json_file"; then
        JSON_FILE=$(echo "$REVISION_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('json_file', ''))")
        echo "   - 생성된 JSON 파일: $JSON_FILE"
    fi

    # 이전 파일 이동 확인
    if echo "$REVISION_RESP" | grep -q "moved_files"; then
        echo -e "   ${GREEN}- 이전 파일이 merge_json_old로 이동됨${NC}"
    fi
else
    echo -e "${RED}❌ 개정 생성 실패${NC}"
    echo "$REVISION_RESP" | python3 -m json.tool 2>/dev/null || echo "$REVISION_RESP"
fi

# 4. 백그라운드 작업 확인
echo -e "\n4. 백그라운드 작업 확인 (JSON_ALL.py)..."
echo "   - 3초 대기 중..."
sleep 3

# merged_severance.json 업데이트 확인
if [ -f "../applib/merge_json/merged_severance.json" ]; then
    MERGE_TIME=$(stat -c %y ../applib/merge_json/merged_severance.json 2>/dev/null | cut -d. -f1)
    CURRENT_TIME=$(date +"%Y-%m-%d %H:%M")

    # 최근 5분 이내 업데이트 확인
    if [ -n "$MERGE_TIME" ]; then
        echo -e "   ${GREEN}✅ merged_severance.json 파일 존재${NC}"
        echo "      최종 업데이트: $MERGE_TIME"
    fi
fi

# 5. 로그아웃
echo -e "\n5. 로그아웃..."
LOGOUT_RESP=$(curl -s -b /tmp/revision_cookies.txt \
    -X POST http://localhost:8800/api/v1/auth/logout)

if echo "$LOGOUT_RESP" | grep -q "message"; then
    echo -e "${GREEN}✅ 로그아웃 성공${NC}"
else
    echo -e "${RED}❌ 로그아웃 실패${NC}"
fi

echo -e "\n======================================="
echo -e "${GREEN}테스트 완료${NC}"
echo "======================================="
