import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# fastapi 경로를 sys.path에 추가하여 settings 사용 가능하게 함
sys.path.insert(0, str(Path(__file__).parent.parent))
from settings import settings

# 경로 설정
docx_dir = settings.DOCX_DIR
merge_json_dir = settings.MERGE_JSON_DIR
docx_json_dir = f"{settings.APPLIB_DIR}/docx_json"

# docx_json 디렉토리 생성
os.makedirs(docx_json_dir, exist_ok=True)

# 모든 docx 파일 찾기
docx_files = [f for f in os.listdir(docx_dir) if f.endswith('.docx')]
print(f"Found {len(docx_files)} docx files")

success_count = 0
error_count = 0
errors = []

for i, docx_file in enumerate(docx_files, 1):
    try:
        docx_path = os.path.join(docx_dir, docx_file)
        print(f"\n[{i}/{len(docx_files)}] Processing: {docx_file}")
        
        # docx2json 실행
        result = subprocess.run(
            ["python3", "docx2json.py", docx_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # 생성된 json 파일 찾기
            json_filename = docx_file.replace('.docx', '.json')
            temp_json_path = os.path.join(docx_dir, json_filename)
            
            if os.path.exists(temp_json_path):
                # JSON 파일 읽기
                with open(temp_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 형식 변환
                transformed_data = {
                    "문서정보": data.get("document_info", {}),
                    "조문내용": data.get("sections", [])
                }
                
                # docx_json 디렉토리에 저장
                output_path = os.path.join(docx_json_dir, json_filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(transformed_data, f, ensure_ascii=False, indent=2)
                
                # 임시 json 파일 삭제
                os.remove(temp_json_path)
                
                print(f"  ✓ Converted and saved to: {output_path}")
                success_count += 1
            else:
                print(f"  ✗ JSON file not created for: {docx_file}")
                error_count += 1
                errors.append(f"{docx_file}: JSON file not created")
        else:
            print(f"  ✗ Error converting: {docx_file}")
            print(f"    Error: {result.stderr}")
            error_count += 1
            errors.append(f"{docx_file}: {result.stderr[:100]}")
            
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout converting: {docx_file}")
        error_count += 1
        errors.append(f"{docx_file}: Timeout")
    except Exception as e:
        print(f"  ✗ Exception for {docx_file}: {str(e)}")
        error_count += 1
        errors.append(f"{docx_file}: {str(e)[:100]}")

# 결과 출력
print(f"\n{'='*50}")
print(f"Conversion Complete!")
print(f"{'='*50}")
print(f"Total files: {len(docx_files)}")
print(f"Success: {success_count}")
print(f"Errors: {error_count}")

if errors:
    print(f"\nError details:")
    for error in errors[:10]:  # 첫 10개 에러만 출력
        print(f"  - {error}")
    if len(errors) > 10:
        print(f"  ... and {len(errors) - 10} more errors")

print(f"\nConverted files saved to: {docx_json_dir}")
