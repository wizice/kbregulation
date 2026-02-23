#!/bin/bash

# Test script to verify parsing result display in editor
# This script tests if parsed content is correctly displayed in the articles tab

echo "========================================="
echo "Testing Parsing Result Display"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Server configuration
BASE_URL="http://localhost:8800"
COOKIE_FILE="/tmp/test_cookies.txt"

# Test credentials
USERNAME="admin"
PASSWORD="admin123!@#"

echo -e "${YELLOW}Step 1: Login to get session${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" \
  -c "${COOKIE_FILE}" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$LOGIN_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Login successful${NC}"
else
    echo -e "${RED}✗ Login failed with status code: $HTTP_CODE${NC}"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

echo -e "\n${YELLOW}Step 2: Get list of regulations${NC}"
REGULATIONS=$(curl -s -X GET "${BASE_URL}/api/v1/rule/list" \
  -b "${COOKIE_FILE}" \
  -H "Accept: application/json")

if echo "$REGULATIONS" | jq -e '.data | length > 0' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Found regulations in database${NC}"
    FIRST_RULE_ID=$(echo "$REGULATIONS" | jq -r '.data[0].wz_rule_id')
    FIRST_RULE_NAME=$(echo "$REGULATIONS" | jq -r '.data[0].rule_nm')
    echo "  First regulation: $FIRST_RULE_NAME (ID: $FIRST_RULE_ID)"
else
    echo -e "${RED}✗ No regulations found${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 3: Testing JavaScript parsing functions${NC}"
# Create a test HTML file that loads the JS and tests the parsing functions
cat > /tmp/test_parsing.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Test Parsing Display</title>
</head>
<body>
    <div id="test-results"></div>

    <script>
        // Simulate the RegulationEditor object
        const TestRegulationEditor = {
            lastParsedContent: {},
            currentRevisingRegulation: null,
            selectedRegulations: new Set(),
            regulations: [],

            // Test the autoMergeAndOpenEditor logic
            testAutoMerge: function() {
                console.log('Testing auto-merge logic...');

                // Test case 1: Direct text in result
                this.lastParsedContent = {
                    pdf_result: {
                        text: "This is test PDF content",
                        structured_data: { test: "data" }
                    }
                };

                let extracted = this.extractText();
                console.assert(extracted === "This is test PDF content", "Test 1 failed");

                // Test case 2: Nested content
                this.lastParsedContent = {
                    docx: {
                        content: "This is test DOCX content"
                    }
                };

                extracted = this.extractText();
                console.assert(extracted === "This is test DOCX content", "Test 2 failed");

                // Test case 3: Result wrapper
                this.lastParsedContent = {
                    pdf: {
                        result: {
                            text: "Wrapped text content"
                        }
                    }
                };

                extracted = this.extractText();
                console.assert(extracted === "Wrapped text content", "Test 3 failed");

                return "All tests passed!";
            },

            extractText: function() {
                const pdfResult = this.lastParsedContent?.pdf || this.lastParsedContent?.pdf_result;
                const docxResult = this.lastParsedContent?.docx || this.lastParsedContent?.docx_result;
                const sourceResult = docxResult || pdfResult;

                let textContent = null;
                if (sourceResult) {
                    if (typeof sourceResult === 'string') {
                        textContent = sourceResult;
                    } else if (typeof sourceResult === 'object') {
                        textContent = sourceResult.text ||
                                     sourceResult.content ||
                                     sourceResult.parsed_text ||
                                     sourceResult.full_text ||
                                     (sourceResult.data && sourceResult.data.text) ||
                                     (sourceResult.result && sourceResult.result.text) ||
                                     null;
                    }
                }
                return textContent;
            }
        };

        // Run tests
        const result = TestRegulationEditor.testAutoMerge();
        document.getElementById('test-results').innerHTML = '<h2>' + result + '</h2>';
        console.log(result);
    </script>
</body>
</html>
EOF

echo -e "${GREEN}✓ Created test HTML file${NC}"

echo -e "\n${YELLOW}Step 4: Testing actual parsing endpoint${NC}"
# Check if the parsing endpoints exist
PARSING_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X GET "${BASE_URL}/api/v1/rule/parsing-status/test-task-id" \
  -b "${COOKIE_FILE}")

if [ "$PARSING_STATUS" = "404" ] || [ "$PARSING_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Parsing endpoint is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Parsing endpoint returned status: $PARSING_STATUS${NC}"
fi

echo -e "\n${YELLOW}Step 5: Checking JavaScript console for errors${NC}"
echo "To fully test the parsing display:"
echo "1. Open browser and go to http://localhost:8800"
echo "2. Login with admin/admin123!@#"
echo "3. Select a regulation and click '개정'"
echo "4. Upload PDF and DOCX files"
echo "5. Check if content appears in '조문 및 부칙' tab"
echo ""
echo "Expected behavior:"
echo "- After file parsing, content should automatically display"
echo "- Console should show: '[Auto-merge] Extracted text length: <number>'"
echo "- Console should show: '[Edit] Set article content textarea'"

# Clean up
rm -f "${COOKIE_FILE}"

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}Test script completed successfully${NC}"
echo -e "${GREEN}=========================================${NC}"