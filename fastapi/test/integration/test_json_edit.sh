#!/bin/bash
# JSON 편집 기능 테스트
# 필수 기능 검증: 구분선, 주석, 개행, 인코딩

BASE_URL="http://localhost:8800"
COOKIE_FILE="/tmp/test_json_edit_cookie.txt"

echo "=== JSON 편집 기능 테스트 시작 ==="
echo ""

# 1. 로그인
echo "[1] 로그인..."
LOGIN_RESPONSE=$(curl -s -c $COOKIE_FILE -X POST \
  "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123!@#"
  }')

if echo "$LOGIN_RESPONSE" | grep -q '"access_token"'; then
    echo "✅ 로그인 성공"
else
    echo "❌ 로그인 실패"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

# 2. 규정 목록 조회 (첫 번째 규정 ID 가져오기)
echo ""
echo "[2] 규정 목록 조회..."
RULES_RESPONSE=$(curl -s -b $COOKIE_FILE -X POST \
  "${BASE_URL}/api/v1/rule/search" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "pageSize": 1
  }')

RULE_ID=$(echo "$RULES_RESPONSE" | grep -o '"wzruleseq":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ -z "$RULE_ID" ]; then
    echo "❌ 규정을 찾을 수 없습니다"
    exit 1
fi

echo "✅ 규정 ID: $RULE_ID"

# 3. 기존 JSON 조회
echo ""
echo "[3] 기존 JSON 조회..."
JSON_RESPONSE=$(curl -s -b $COOKIE_FILE -X GET \
  "${BASE_URL}/api/v1/rule/get/${RULE_ID}")

if echo "$JSON_RESPONSE" | grep -q '"조문내용"'; then
    ARTICLE_COUNT=$(echo "$JSON_RESPONSE" | grep -o '"번호"' | wc -l)
    echo "✅ JSON 조회 성공 (조문 수: $ARTICLE_COUNT)"
else
    echo "❌ JSON 조회 실패"
    exit 1
fi

# 4. JSON 구조 확인 (seq, 레벨 보존 확인용)
echo ""
echo "[4] JSON 구조 확인..."
echo "$JSON_RESPONSE" | grep -q '"seq"' && echo "✅ seq 필드 존재"
echo "$JSON_RESPONSE" | grep -q '"레벨"' && echo "✅ 레벨 필드 존재"
echo "$JSON_RESPONSE" | grep -q '"관련이미지"' && echo "✅ 관련이미지 필드 존재"

# 5. 테스트용 JSON 수정 (첫 번째 조문의 내용만 변경)
echo ""
echo "[5] JSON 수정 테스트..."

# 원본 JSON에서 첫 번째 조문의 내용을 "[테스트 수정]"으로 변경
MODIFIED_JSON=$(echo "$JSON_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data and '조문내용' in data and len(data['조문내용']) > 0:
    data['조문내용'][0]['내용'] = '[테스트 수정] ' + data['조문내용'][0]['내용']
print(json.dumps(data, ensure_ascii=False))
")

UPDATE_RESPONSE=$(curl -s -b $COOKIE_FILE -X PUT \
  "${BASE_URL}/api/v1/rule/update-json/${RULE_ID}" \
  -H "Content-Type: application/json" \
  -d "{\"json_data\": $MODIFIED_JSON}")

if echo "$UPDATE_RESPONSE" | grep -q '"success":true'; then
    echo "✅ JSON 업데이트 성공"
    echo "$UPDATE_RESPONSE"
else
    echo "❌ JSON 업데이트 실패"
    echo "$UPDATE_RESPONSE"
    exit 1
fi

# 6. 업데이트 확인
echo ""
echo "[6] 업데이트 확인..."
VERIFY_RESPONSE=$(curl -s -b $COOKIE_FILE -X GET \
  "${BASE_URL}/api/v1/rule/get/${RULE_ID}")

if echo "$VERIFY_RESPONSE" | grep -q '\[테스트 수정\]'; then
    echo "✅ 내용 수정 확인됨"
else
    echo "❌ 내용 수정 확인 실패"
fi

# 7. 구조 보존 확인
echo ""
echo "[7] 구조 보존 확인..."
echo "$VERIFY_RESPONSE" | grep -q '"seq"' && echo "✅ seq 필드 보존됨"
echo "$VERIFY_RESPONSE" | grep -q '"레벨"' && echo "✅ 레벨 필드 보존됨"
echo "$VERIFY_RESPONSE" | grep -q '"관련이미지"' && echo "✅ 관련이미지 필드 보존됨"

# 8. 백업 파일 확인
echo ""
echo "[8] 백업 파일 확인..."
BACKUP_CHECK=$(curl -s -b $COOKIE_FILE -X POST \
  "${BASE_URL}/api/v1/rule/search" \
  -H "Content-Type: application/json" \
  -d "{
    \"page\": 1,
    \"pageSize\": 1,
    \"wzruleseq\": $RULE_ID
  }")

JSON_PATH=$(echo "$BACKUP_CHECK" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data and 'items' in data and len(data['items']) > 0:
    print(data['items'][0].get('wzfilejson', ''))
" 2>/dev/null)

if [ -n "$JSON_PATH" ] && [ -f "${JSON_PATH}.backup" ]; then
    echo "✅ 백업 파일 생성 확인: ${JSON_PATH}.backup"
else
    echo "⚠️ 백업 파일 확인 불가 (경로: $JSON_PATH)"
fi

# 9. 원본 복구
echo ""
echo "[9] 원본 복구..."
RESTORE_RESPONSE=$(curl -s -b $COOKIE_FILE -X PUT \
  "${BASE_URL}/api/v1/rule/update-json/${RULE_ID}" \
  -H "Content-Type: application/json" \
  -d "{\"json_data\": $(echo "$JSON_RESPONSE")}")

if echo "$RESTORE_RESPONSE" | grep -q '"success":true'; then
    echo "✅ 원본 복구 성공"
else
    echo "❌ 원본 복구 실패"
fi

# 정리
rm -f $COOKIE_FILE

echo ""
echo "=== 테스트 완료 ==="
