#!/bin/bash

# JSON 파일 경로 시스템 테스트
# wzFileJson 컬럼을 활용한 JSON 파일 저장/읽기 테스트

echo "======================================"
echo "JSON 파일 경로 시스템 통합 테스트"
echo "======================================"

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 서버 URL
BASE_URL="http://localhost:8800"

echo -e "${GREEN}[1단계] DB 컬럼 확인${NC}"
echo ""
echo "wzFileJson 컬럼이 추가되었는지 확인:"
echo "SQL: SELECT column_name FROM information_schema.columns WHERE table_name = 'wz_rule' AND column_name = 'wzfilejson';"
echo ""

echo -e "${GREEN}[2단계] 파일 업로드 및 병합${NC}"
echo ""
echo "1. 규정 편집 모달 열기"
echo "2. PDF/DOCX 파일 업로드"
echo "3. 파싱 완료 확인"
echo "4. DB에 JSON 경로 저장 확인:"
echo "   - /applib/merge_json/merged_{rule_id}_*.json"
echo ""

echo -e "${GREEN}[3단계] 미리보기 테스트${NC}"
echo ""
echo "1. 규정 목록에서 제목 클릭"
echo "2. 미리보기 모달 확인:"
echo "   - JSON 파일에서 내용 읽어오기"
echo "   - 조문 내용 표시 확인"
echo ""

echo -e "${GREEN}[4단계] 편집 저장 테스트${NC}"
echo ""
echo "1. 편집 모달에서 내용 수정"
echo "2. 저장 버튼 클릭"
echo "3. 새 JSON 파일 생성 확인:"
echo "   - /applib/edited/edited_{rule_id}_*.json"
echo "4. DB wzFileJson 컬럼 업데이트 확인"
echo ""

echo -e "${GREEN}[5단계] 제정/개정 테스트${NC}"
echo ""
echo "1. 제정 또는 개정 모드 실행"
echo "2. JSON 파일 생성 및 경로 저장 확인"
echo ""

echo -e "${YELLOW}API 엔드포인트:${NC}"
echo ""
echo "• 파일 병합: POST /api/v1/rule-editor/merge-json"
echo "• JSON 조회: GET /api/v1/json/view/{rule_id}"
echo "• 경로 업데이트: POST /api/v1/json/update-path"
echo "• 내용 저장: POST /api/v1/rule-editor/save-edited-content"
echo ""

echo -e "${YELLOW}JavaScript 콘솔 테스트:${NC}"
echo ""
cat << 'EOF'
// JSON 파일 경로 확인
fetch('/api/v1/json/view/1', {
    credentials: 'include'
}).then(r => r.json()).then(data => {
    console.log('JSON Path:', data.data.wzfilejson);
    console.log('Has Content:', data.data.has_content);
    console.log('Content Preview:', data.data.content_text?.substring(0, 200));
});

// 파일 업로드 후 경로 확인
console.log('Checking merged file path:', RuleEditor.currentRule);

// 미리보기 모달 테스트
showPreview(1, 'Test Regulation');
EOF

echo ""
echo -e "${GREEN}디렉토리 확인:${NC}"
echo ""
echo "ls -la /home/wizice/regulation/fastapi/applib/merge_json/ | tail -5"
echo "ls -la /home/wizice/regulation/fastapi/applib/edited/ | tail -5"
echo ""

echo -e "${GREEN}성공 기준:${NC}"
echo "✓ wzFileJson 컬럼에 JSON 파일 경로 저장"
echo "✓ 미리보기 시 JSON 파일에서 내용 읽기"
echo "✓ 편집 저장 시 새 JSON 파일 생성 및 경로 업데이트"
echo "✓ 제정/개정 시 JSON 경로 올바르게 저장"
echo ""

echo "======================================"
echo "테스트 준비 완료"
echo "======================================"