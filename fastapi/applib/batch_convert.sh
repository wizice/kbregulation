#!/bin/bash

# 색상 코드 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "DOCX to JSON 일괄 변환 시작"
echo "=========================================="

# 경로 설정
DOCX_DIR="/home/wizice/regulation/fastapi/applib/upload_docx"
JSON_DIR="/home/wizice/regulation/fastapi/applib/docx_json"
LOG_FILE="/home/wizice/regulation/fastapi/applib/conversion_$(date +%Y%m%d_%H%M%S).log"

# 디렉토리 생성
mkdir -p "$JSON_DIR"

# 카운터 초기화
TOTAL=0
SUCCESS=0
FAILED=0

# 모든 docx 파일 개수 확인
TOTAL=$(find "$DOCX_DIR" -name "*.docx" -type f | wc -l)
echo "총 $TOTAL 개의 DOCX 파일을 발견했습니다."
echo ""

# 각 docx 파일에 대해 변환 실행
COUNT=0
for docx_file in "$DOCX_DIR"/*.docx; do
    if [ -f "$docx_file" ]; then
        COUNT=$((COUNT + 1))
        filename=$(basename "$docx_file")
        json_filename="${filename%.docx}.json"

        echo -n "[$COUNT/$TOTAL] $filename 변환 중... "

        # docx2json.py 실행
        cd /home/wizice/regulation/fastapi/applib

        if timeout 30 python3 docx2json.py "$docx_file" "$JSON_DIR" >> "$LOG_FILE" 2>&1; then
            # JSON 파일이 생성되었는지 확인
            if [ -f "$JSON_DIR/$json_filename" ]; then
                echo -e "${GREEN}✓ 성공${NC}"
                SUCCESS=$((SUCCESS + 1))
            else
                echo -e "${RED}✗ 실패 (JSON 파일 생성 안됨)${NC}"
                FAILED=$((FAILED + 1))
                echo "ERROR: $filename - JSON file not created" >> "$LOG_FILE"
            fi
        else
            echo -e "${RED}✗ 실패 (오류 또는 타임아웃)${NC}"
            FAILED=$((FAILED + 1))
            echo "ERROR: $filename - Conversion failed or timeout" >> "$LOG_FILE"
        fi
    fi
done

echo ""
echo "=========================================="
echo -e "변환 완료!"
echo -e "  ${GREEN}성공: $SUCCESS${NC}"
echo -e "  ${RED}실패: $FAILED${NC}"
echo -e "  전체: $TOTAL"
echo ""
echo "로그 파일: $LOG_FILE"
echo "JSON 파일 위치: $JSON_DIR"
echo "=========================================="

# 실패한 파일이 있으면 로그에서 에러 표시
if [ $FAILED -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}실패한 파일 목록 (자세한 내용은 로그 파일 확인):${NC}"
    grep "ERROR:" "$LOG_FILE" | head -10

    if [ $(grep -c "ERROR:" "$LOG_FILE") -gt 10 ]; then
        echo "... 외 $(( $(grep -c "ERROR:" "$LOG_FILE") - 10 ))개"
    fi
fi