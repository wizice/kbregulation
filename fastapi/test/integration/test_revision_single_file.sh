#!/bin/bash

# Test script for revision workflow - verifies single file update behavior
# This test ensures that revision mode updates existing files instead of creating duplicates

echo "=========================================="
echo "Revision Workflow Test"
echo "Testing single file update and structure preservation"
echo "=========================================="

# Configuration
API_URL="http://localhost:8800"
TEST_REGULATION="12.4.1"
MERGE_JSON_DIR="/home/wizice/regulation/fastapi/applib/merge_json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Login first
echo -e "\n${YELLOW}1. Logging in...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST \
  "${API_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123!@#"}' \
  -c cookies.txt)

if echo "$LOGIN_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ Login successful${NC}"
else
    echo -e "${RED}✗ Login failed${NC}"
    exit 1
fi

# Function to count JSON files for a regulation
count_json_files() {
    local regulation=$1
    local count=$(ls -1 ${MERGE_JSON_DIR}/merged_${regulation}_*.json 2>/dev/null | wc -l)
    echo $count
}

# Function to check for seq and level fields in JSON
check_json_structure() {
    local file=$1
    if [ -f "$file" ]; then
        # Check for seq field
        has_seq=$(grep -c '"seq"' "$file")
        # Check for level field
        has_level=$(grep -c '"level"' "$file")

        if [ $has_seq -gt 0 ] && [ $has_level -gt 0 ]; then
            return 0
        else
            return 1
        fi
    else
        return 1
    fi
}

# Clean up old test files
echo -e "\n${YELLOW}2. Cleaning up old test files...${NC}"
rm -f ${MERGE_JSON_DIR}/merged_${TEST_REGULATION}_*.json
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Create initial JSON file (simulate merge operation)
echo -e "\n${YELLOW}3. Creating initial merged JSON file...${NC}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
INITIAL_FILE="${MERGE_JSON_DIR}/merged_${TEST_REGULATION}_개인정보_보호_및_보안_${TIMESTAMP}.json"

cat > "$INITIAL_FILE" << 'EOF'
{
    "documentInfo": {
        "제정": "1994-12-15",
        "규정번호": "12.4.1",
        "최근개정일": "2024-06-01",
        "규정명": "개인정보 보호 및 보안",
        "주무부서": "정보팀"
    },
    "articles": [
        {
            "seq": 1,
            "level": 1,
            "content": "제1조(목적) 이 규정은 개인정보 보호를 위한 사항을 정한다.",
            "조문": "제1조",
            "조문내용": "이 규정은 개인정보 보호를 위한 사항을 정한다.",
            "조문제목": "목적"
        },
        {
            "seq": 2,
            "level": 1,
            "content": "제2조(적용범위) 병원 전체에 적용된다.",
            "조문": "제2조",
            "조문내용": "병원 전체에 적용된다.",
            "조문제목": "적용범위"
        }
    ]
}
EOF

echo -e "${GREEN}✓ Initial file created: $(basename $INITIAL_FILE)${NC}"

# Count initial files
INITIAL_COUNT=$(count_json_files $TEST_REGULATION)
echo -e "Initial file count: ${INITIAL_COUNT}"

# Simulate revision operation
echo -e "\n${YELLOW}4. Simulating revision operation...${NC}"

# Prepare edited content
EDITED_CONTENT="제1조(목적) 이 규정은 개인정보 보호 및 보안을 위한 사항을 정한다.
제2조(적용범위) 병원 전체 및 협력업체에 적용된다.
제3조(책임) 정보보안팀이 주관한다."

# Call the save API in revision mode
SAVE_RESPONSE=$(curl -s -X POST \
  "${API_URL}/api/v1/rule/save-edited-content" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d "{
    \"regulation_number\": \"${TEST_REGULATION}\",
    \"edited_content\": \"${EDITED_CONTENT}\",
    \"mode\": \"revision\",
    \"use_merged_json\": \"true\",
    \"merged_json_path\": \"${INITIAL_FILE}\"
  }")

if echo "$SAVE_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ Revision save successful${NC}"
else
    echo -e "${RED}✗ Revision save failed${NC}"
    echo "Response: $SAVE_RESPONSE"
fi

# Wait for file operations to complete
sleep 2

# Count files after revision
echo -e "\n${YELLOW}5. Checking results...${NC}"
FINAL_COUNT=$(count_json_files $TEST_REGULATION)
echo -e "Final file count: ${FINAL_COUNT}"

# Test 1: Check if only one file exists (no duplicate created)
if [ $FINAL_COUNT -eq 1 ]; then
    echo -e "${GREEN}✓ Test 1 PASSED: No duplicate file created${NC}"
else
    echo -e "${RED}✗ Test 1 FAILED: Found ${FINAL_COUNT} files (expected 1)${NC}"
    ls -la ${MERGE_JSON_DIR}/merged_${TEST_REGULATION}_*.json
fi

# Test 2: Check if seq and level fields are preserved
LATEST_FILE=$(ls -t ${MERGE_JSON_DIR}/merged_${TEST_REGULATION}_*.json 2>/dev/null | head -n1)
if check_json_structure "$LATEST_FILE"; then
    echo -e "${GREEN}✓ Test 2 PASSED: seq and level fields preserved${NC}"

    # Show sample of the structure
    echo -e "\n${YELLOW}Sample of preserved structure:${NC}"
    python3 -c "
import json
with open('$LATEST_FILE', 'r') as f:
    data = json.load(f)
    if 'articles' in data and len(data['articles']) > 0:
        article = data['articles'][0]
        print(f'  First article:')
        print(f'    seq: {article.get(\"seq\", \"MISSING\")}')
        print(f'    level: {article.get(\"level\", \"MISSING\")}')
        print(f'    content: {article.get(\"content\", \"\")[:50]}...')
"
else
    echo -e "${RED}✗ Test 2 FAILED: seq and level fields missing${NC}"
fi

# Test 3: Check if content was actually updated
if [ -f "$LATEST_FILE" ]; then
    if grep -q "개인정보 보호 및 보안을 위한" "$LATEST_FILE"; then
        echo -e "${GREEN}✓ Test 3 PASSED: Content was updated${NC}"
    else
        echo -e "${RED}✗ Test 3 FAILED: Content was not updated${NC}"
    fi
fi

# Test 4: Check if file timestamp is preserved (same filename)
if [ "$LATEST_FILE" = "$INITIAL_FILE" ]; then
    echo -e "${GREEN}✓ Test 4 PASSED: Same file was updated (no new timestamp)${NC}"
else
    echo -e "${YELLOW}⚠ Test 4 WARNING: Different file found${NC}"
    echo "  Initial: $(basename $INITIAL_FILE)"
    echo "  Latest:  $(basename $LATEST_FILE)"
fi

# Clean up cookies
rm -f cookies.txt

echo -e "\n${YELLOW}=========================================="
echo "Test Summary:"
echo "==========================================${NC}"

# Calculate pass rate
TESTS_PASSED=0
[ $FINAL_COUNT -eq 1 ] && ((TESTS_PASSED++))
check_json_structure "$LATEST_FILE" && ((TESTS_PASSED++))
grep -q "개인정보 보호 및 보안을 위한" "$LATEST_FILE" 2>/dev/null && ((TESTS_PASSED++))
[ "$LATEST_FILE" = "$INITIAL_FILE" ] && ((TESTS_PASSED++))

if [ $TESTS_PASSED -eq 4 ]; then
    echo -e "${GREEN}All tests PASSED (4/4)${NC}"
    echo -e "${GREEN}✓ Revision workflow is working correctly${NC}"
    exit 0
else
    echo -e "${RED}Some tests FAILED ($TESTS_PASSED/4)${NC}"
    echo -e "${RED}✗ Revision workflow needs attention${NC}"
    exit 1
fi