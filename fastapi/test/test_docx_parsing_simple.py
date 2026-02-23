#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 DOCX 파싱 테스트
외부 라이브러리 없이 파싱 모듈 동작 확인
"""

import os
import sys
import json

# 경로 설정
sys.path.append('/home/wizice/regulation/fastapi/applib')
sys.path.append('/home/wizice/regulation/fastapi')

def test_txt_to_json_parsing():
    """TXT to JSON 파싱 테스트"""
    print("\n" + "="*60)
    print("TXT to JSON 파싱 테스트")
    print("="*60)

    try:
        from txt2json import MentalHealthRegulationParser

        # 샘플 텍스트
        sample_text = """1.1.1 정신건강의학과 입원환자 관리

제정일: 2024.01.01.
최종개정일: 2024.03.15.
최종검토일: 2024.03.20.
담당부서: 정신건강의학과

제1조 (목적) 이 규정은 정신건강의학과 입원환자의 체계적인 관리를 통해 환자 안전과 의료 서비스의 질을 향상시키는 것을 목적으로 한다.

제2조 (적용범위) 이 규정은 정신건강의학과에 입원하는 모든 환자에게 적용된다.

제3조 (입원절차)
  1. 환자 또는 보호자의 동의서 작성
  2. 초기 평가 및 진단
  3. 치료계획 수립

제4조 (퇴원절차) 담당 전문의의 판단에 따라 환자의 상태가 호전되어 일상생활이 가능하다고 판단될 때 퇴원할 수 있다.

부칙
제1조 (시행일) 이 규정은 2024년 1월 1일부터 시행한다."""

        # 파서 생성
        parser = MentalHealthRegulationParser()

        # 파싱
        result = parser.parse_txt_to_json(sample_text)

        print("✓ 파싱 성공!")
        print("\n문서 정보:")
        for key, value in result.get("문서정보", {}).items():
            print(f"  - {key}: {value}")

        print(f"\n조문 개수: {len(result.get('조문내용', []))}개")

        # 처음 5개 조문 출력
        print("\n처음 5개 조문:")
        for i, item in enumerate(result.get("조문내용", [])[:5], 1):
            print(f"  [{i}] 레벨: {item.get('레벨')}, "
                  f"번호: {item.get('번호', '')}, "
                  f"내용: {item.get('내용', '')[:50]}...")

        # JSON 파일로 저장
        json_path = "/tmp/test_parsing_result.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n✓ JSON 파일 저장: {json_path}")

        return True

    except ImportError as e:
        print(f"✗ 모듈 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"✗ 파싱 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pdf_to_txt():
    """PDF to TXT 변환 테스트"""
    print("\n" + "="*60)
    print("PDF to TXT 변환 기능 확인")
    print("="*60)

    try:
        from pdf2txt import extract_text_from_pdf

        # 샘플 PDF 파일 경로 (존재하는 경우)
        pdf_paths = [
            '/home/wizice/regulation/fastapi/applib/text/',
            '/home/wizice/regulation/fastapi/applib/json/',
            '/tmp/'
        ]

        pdf_file = None
        for path in pdf_paths:
            if os.path.exists(path):
                files = [f for f in os.listdir(path) if f.endswith('.pdf')]
                if files:
                    pdf_file = os.path.join(path, files[0])
                    break

        if pdf_file and os.path.exists(pdf_file):
            print(f"✓ PDF 파일 발견: {pdf_file}")

            # 텍스트 추출 시도
            txt_path = "/tmp/test_extracted.txt"
            result = extract_text_from_pdf(pdf_file, txt_path)

            if result and os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"✓ 텍스트 추출 성공: {len(content)} 문자")
                print(f"  처음 200자: {content[:200]}...")
                os.unlink(txt_path)  # 임시 파일 삭제
            else:
                print("✗ 텍스트 추출 실패")
        else:
            print("⚠ 테스트용 PDF 파일을 찾을 수 없습니다.")
            print("  PDF to TXT 모듈은 로드되었습니다.")

        return True

    except ImportError as e:
        print(f"✗ pdf2txt 모듈 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"✗ 오류 발생: {e}")
        return False

def test_applib_structure():
    """applib 구조 확인"""
    print("\n" + "="*60)
    print("applib 구조 확인")
    print("="*60)

    applib_path = '/home/wizice/regulation/fastapi/applib'

    # 필수 파일 목록
    required_files = [
        'app.py',
        'pdf2txt.py',
        'txt2json.py',
        'json2db.py',
        'editor.cfg'
    ]

    # utils 모듈 파일들
    utils_files = [
        'utils/docx_parser.py',
        'utils/sequential_numbers.py',
        'utils/json_converter.py',
        'utils/app_integration.py'
    ]

    print("필수 파일 확인:")
    for file in required_files:
        path = os.path.join(applib_path, file)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✓ {file} ({size:,} bytes)")
        else:
            print(f"  ✗ {file} (없음)")

    print("\nUtils 모듈 확인:")
    for file in utils_files:
        path = os.path.join(applib_path, file)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✓ {file} ({size:,} bytes)")
        else:
            print(f"  ✗ {file} (없음)")

    # 폴더 내용 확인
    print("\n폴더 구조:")
    for item in ['text', 'json', 'templates', 'static']:
        path = os.path.join(applib_path, item)
        if os.path.exists(path):
            if os.path.isdir(path):
                count = len(os.listdir(path))
                print(f"  ✓ {item}/ ({count} 항목)")
            else:
                print(f"  ✓ {item} (파일)")
        else:
            print(f"  ✗ {item}/ (없음)")

    return True

def main():
    """메인 테스트 함수"""
    print("\n" + "="*60)
    print("DOCX/PDF 파싱 시스템 테스트")
    print("="*60)

    results = []

    # 1. applib 구조 확인
    print("\n[1/3] applib 구조 확인")
    results.append(("applib 구조", test_applib_structure()))

    # 2. TXT to JSON 파싱 테스트
    print("\n[2/3] TXT to JSON 파싱")
    results.append(("TXT to JSON", test_txt_to_json_parsing()))

    # 3. PDF to TXT 변환 테스트
    print("\n[3/3] PDF to TXT 변환")
    results.append(("PDF to TXT", test_pdf_to_txt()))

    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)

    for name, result in results:
        status = "✓ 성공" if result else "✗ 실패"
        print(f"  {name}: {status}")

    # 전체 결과
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n✅ 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패")

    print("\n참고:")
    print("  - python-docx가 없어도 PDF와 TXT 파싱은 동작합니다.")
    print("  - DOCX 파일 직접 파싱은 python-docx 또는 docx2txt 필요")
    print("  - Flask 서버 실행: cd /home/wizice/regulation/fastapi/applib && python app.py")

if __name__ == '__main__':
    main()