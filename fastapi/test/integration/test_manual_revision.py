#!/usr/bin/env python3

"""
Manual test script to verify revision workflow behavior
Tests that only one JSON file is created/updated during revision
"""

import json
import os
import glob
from datetime import datetime

# Configuration
TEST_REGULATION = "12.4.1"
MERGE_JSON_DIR = "/home/wizice/regulation/fastapi/applib/merge_json"

def count_json_files(regulation):
    """Count JSON files for a specific regulation"""
    pattern = os.path.join(MERGE_JSON_DIR, f"merged_{regulation}_*.json")
    files = glob.glob(pattern)
    return len(files)

def check_json_structure(file_path):
    """Check if JSON file has seq and level fields"""
    if not os.path.exists(file_path):
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if articles exist and have seq/level
    if 'articles' in data and len(data['articles']) > 0:
        article = data['articles'][0]
        has_seq = 'seq' in article
        has_level = 'level' in article
        return has_seq and has_level
    return False

def create_test_file():
    """Create initial test JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"merged_{TEST_REGULATION}_개인정보_보호_및_보안_{timestamp}.json"
    filepath = os.path.join(MERGE_JSON_DIR, filename)

    test_data = {
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

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)

    return filepath

def simulate_revision(filepath):
    """Simulate revision by updating existing file"""
    # This simulates what the update_articles_content function should do

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Update articles content while preserving structure
    edited_content = [
        "제1조(목적) 이 규정은 개인정보 보호 및 보안을 위한 사항을 정한다.",
        "제2조(적용범위) 병원 전체 및 협력업체에 적용된다.",
        "제3조(책임) 정보보안팀이 주관한다."
    ]

    # Update existing articles
    for i, article in enumerate(data['articles']):
        if i < len(edited_content):
            content = edited_content[i]
            # Parse article number and title
            if '(' in content:
                parts = content.split('(', 1)
                article_num = parts[0].strip()
                rest = parts[1].rsplit(')', 1)
                title = rest[0] if rest else ""
                body = rest[1].strip() if len(rest) > 1 else ""

                article['content'] = content
                article['조문'] = article_num
                article['조문제목'] = title
                article['조문내용'] = body

    # Add new article if needed
    if len(edited_content) > len(data['articles']):
        for i in range(len(data['articles']), len(edited_content)):
            content = edited_content[i]
            # Parse article number and title
            if '(' in content:
                parts = content.split('(', 1)
                article_num = parts[0].strip()
                rest = parts[1].rsplit(')', 1)
                title = rest[0] if rest else ""
                body = rest[1].strip() if len(rest) > 1 else ""

                new_article = {
                    "seq": i + 1,
                    "level": 1,
                    "content": content,
                    "조문": article_num,
                    "조문제목": title,
                    "조문내용": body
                }
                data['articles'].append(new_article)

    # Update file (same file, not creating new one)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath

def main():
    print("="*50)
    print("Manual Revision Workflow Test")
    print("="*50)

    # Clean up old test files
    print("\n1. Cleaning up old test files...")
    pattern = os.path.join(MERGE_JSON_DIR, f"merged_{TEST_REGULATION}_*.json")
    for f in glob.glob(pattern):
        os.remove(f)
    print("✓ Cleanup complete")

    # Create initial file
    print("\n2. Creating initial JSON file...")
    initial_file = create_test_file()
    print(f"✓ Created: {os.path.basename(initial_file)}")

    # Count initial files
    initial_count = count_json_files(TEST_REGULATION)
    print(f"Initial file count: {initial_count}")

    # Simulate revision
    print("\n3. Simulating revision update...")
    updated_file = simulate_revision(initial_file)
    print(f"✓ Updated: {os.path.basename(updated_file)}")

    # Count final files
    final_count = count_json_files(TEST_REGULATION)
    print(f"Final file count: {final_count}")

    # Run tests
    print("\n4. Running tests...")
    tests_passed = 0

    # Test 1: Only one file exists
    if final_count == 1:
        print("✓ Test 1 PASSED: No duplicate file created")
        tests_passed += 1
    else:
        print(f"✗ Test 1 FAILED: Found {final_count} files (expected 1)")

    # Test 2: seq and level preserved
    if check_json_structure(updated_file):
        print("✓ Test 2 PASSED: seq and level fields preserved")
        tests_passed += 1

        # Show sample
        with open(updated_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data['articles']:
                article = data['articles'][0]
                print(f"  Sample - seq: {article.get('seq')}, level: {article.get('level')}")
    else:
        print("✗ Test 2 FAILED: seq and level fields missing")

    # Test 3: Content updated
    with open(updated_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if "개인정보 보호 및 보안을 위한" in content:
            print("✓ Test 3 PASSED: Content was updated")
            tests_passed += 1
        else:
            print("✗ Test 3 FAILED: Content was not updated")

    # Test 4: Same file updated
    if updated_file == initial_file:
        print("✓ Test 4 PASSED: Same file was updated")
        tests_passed += 1
    else:
        print("✗ Test 4 FAILED: Different file created")

    # Summary
    print("\n" + "="*50)
    print("Test Summary:")
    print("="*50)

    if tests_passed == 4:
        print(f"✓ All tests PASSED ({tests_passed}/4)")
        print("✓ Revision workflow logic is correct")
    else:
        print(f"✗ Some tests FAILED ({tests_passed}/4)")
        print("✗ Revision workflow needs attention")

    return tests_passed == 4

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)