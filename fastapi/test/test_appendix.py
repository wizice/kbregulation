#!/usr/bin/env python3
"""
부록 파일 업로드 기능 테스트
"""
import requests
import os
import json

# 테스트 서버 URL
BASE_URL = "http://localhost:8800"

# 테스트용 파일 생성
def create_test_files():
    """테스트용 파일들을 생성"""
    test_files = []

    # 텍스트 파일
    with open("/tmp/test_appendix_1.txt", "w") as f:
        f.write("This is test appendix file 1")
        test_files.append("/tmp/test_appendix_1.txt")

    # CSV 파일
    with open("/tmp/test_appendix_2.csv", "w") as f:
        f.write("header1,header2\nvalue1,value2")
        test_files.append("/tmp/test_appendix_2.csv")

    print(f"✅ Created {len(test_files)} test files")
    return test_files

def test_appendix_upload(rule_id=1):
    """부록 파일 업로드 테스트"""
    print(f"\n📤 Testing appendix upload for rule_id={rule_id}")

    # 테스트 파일 생성
    test_files = create_test_files()

    # 파일 업로드
    files = []
    for filepath in test_files:
        files.append(('files', (os.path.basename(filepath), open(filepath, 'rb'))))

    response = requests.post(
        f"{BASE_URL}/api/v1/appendix/upload/{rule_id}",
        files=files
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   - Uploaded: {result.get('uploaded_count', 0)} files")
        print(f"   - Failed: {result.get('failed_count', 0)} files")

        if result.get('uploaded_files'):
            print("\n📁 Uploaded files:")
            for file in result['uploaded_files']:
                print(f"   - {file['filename']} ({file.get('size', 0)} bytes)")

        return True
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_list_appendix(rule_id=1):
    """부록 파일 목록 조회 테스트"""
    print(f"\n📋 Testing appendix list for rule_id={rule_id}")

    response = requests.get(f"{BASE_URL}/api/v1/appendix/list/{rule_id}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ List retrieved successfully!")
        print(f"   - Total files: {result.get('total_count', 0)}")

        if result.get('files'):
            print("\n📁 Files in appendix:")
            for file in result['files']:
                print(f"   - {file['filename']} ({file.get('size', 0)} bytes)")

        return True
    else:
        print(f"❌ List failed: {response.status_code}")
        return False

def test_delete_appendix(rule_id=1, filename="test_appendix_1.txt"):
    """부록 파일 삭제 테스트"""
    print(f"\n🗑️ Testing appendix delete: {filename}")

    response = requests.delete(
        f"{BASE_URL}/api/v1/appendix/delete/{rule_id}/{filename}"
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Delete successful!")
        print(f"   - {result.get('message', '')}")
        return True
    else:
        print(f"❌ Delete failed: {response.status_code}")
        return False

def cleanup_test_files():
    """테스트 파일 정리"""
    for filepath in ["/tmp/test_appendix_1.txt", "/tmp/test_appendix_2.csv"]:
        if os.path.exists(filepath):
            os.remove(filepath)
    print("🧹 Test files cleaned up")

if __name__ == "__main__":
    print("=" * 50)
    print("부록 파일 업로드 기능 테스트")
    print("=" * 50)

    try:
        # 1. 업로드 테스트
        if test_appendix_upload(1):
            # 2. 목록 조회 테스트
            test_list_appendix(1)

            # 3. 파일 삭제 테스트
            # test_delete_appendix(1, "test_appendix_1.txt")

            # 4. 삭제 후 목록 확인
            # test_list_appendix(1)

    finally:
        # 테스트 파일 정리
        cleanup_test_files()

    print("\n✅ 테스트 완료!")