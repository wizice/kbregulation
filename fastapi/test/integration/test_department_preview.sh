#!/bin/bash

# 부서 페이지 규정 미리보기 테스트

echo "========================================="
echo "부서 페이지 규정 미리보기 기능 테스트"
echo "========================================="

# 세션 파일
SESSION_FILE="/tmp/test_cat_session.txt"

# 1. 부서 페이지 접근
echo -e "\n1. 부서 페이지 접근 확인..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8800/regulations/department -b $SESSION_FILE)
if [ "$RESPONSE" = "200" ]; then
    echo "✓ 부서 페이지 접근 성공"
else
    echo "✗ 부서 페이지 접근 실패 (HTTP $RESPONSE)"
fi

# 2. 모달 HTML 존재 확인
echo -e "\n2. 미리보기 모달 HTML 확인..."
MODAL_CHECK=$(curl -s http://localhost:8800/regulations/department -b $SESSION_FILE | grep -c "regulationPreviewModal")
if [ "$MODAL_CHECK" -gt 0 ]; then
    echo "✓ 미리보기 모달 HTML 존재"
else
    echo "✗ 미리보기 모달 HTML 없음"
fi

# 3. JavaScript 함수 확인
echo -e "\n3. JavaScript 함수 확인..."
JS_CHECK=$(curl -s http://localhost:8800/static/js/department-manager.js | grep -c "showRegulationDetail")
if [ "$JS_CHECK" -gt 0 ]; then
    echo "✓ showRegulationDetail 함수 존재"
else
    echo "✗ showRegulationDetail 함수 없음"
fi

# 4. 부서별 규정 API 테스트
echo -e "\n4. 부서별 규정 목록 API 테스트..."
TEST_DEPT="정보관리부"
API_RESPONSE=$(curl -s -X GET "http://localhost:8800/api/v1/dept/${TEST_DEPT}/regulations" \
    -H "Content-Type: application/json" \
    -b $SESSION_FILE)

if echo "$API_RESPONSE" | grep -q "success"; then
    echo "✓ 부서별 규정 API 응답 성공"
    echo "$API_RESPONSE" | python3 -m json.tool | head -20
else
    echo "✗ 부서별 규정 API 응답 실패"
    echo "$API_RESPONSE"
fi

echo -e "\n========================================="
echo "테스트 완료"
echo "========================================="
echo ""
echo "브라우저 테스트 방법:"
echo "1. https://policyeditor.wizice.com:8443/regulations/department 접속"
echo "2. 부서명을 클릭하여 우측 패널에 규정 목록 표시 확인"
echo "3. 규정을 클릭하여 미리보기 모달이 열리는지 확인"
echo "4. ESC 키 또는 X 버튼으로 모달이 닫히는지 확인"