#!/usr/bin/env python3
"""
부록 파싱 테스트 스크립트
PDF 파일의 부록 내용이 올바르게 파싱되는지 검증
"""

import sys
import os
import tempfile
import re

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from applib.pdf2txt import extract_text_from_pdf, optimize_line_breaks

def create_test_text():
    """테스트용 텍스트 생성"""
    test_text = """제1조 (목적) 이 규정은 테스트를 위한 것이다.

2.1.2.2. 부록4. 검사실 업무 절차
이것은 부록 내용입니다. 분류번호가 아닌 내용으로 처리되어야 합니다.

(부록) 참고사항
이것도 부록 내용입니다.

[부록 1] 서식 양식
부록 1의 내용입니다.

부록 2. 업무 프로세스
부록 2의 내용입니다.

제2조 (정의) 용어의 정의는 다음과 같다.
1. 첫 번째 항목
2. 두 번째 항목
   (1) 세부 항목 1
   (2) 세부 항목 2

별표 1. 조직도
별표의 내용입니다.
"""
    return test_text

def test_appendix_parsing():
    """부록 파싱 테스트 실행"""
    print("="*60)
    print("부록 파싱 테스트 시작")
    print("="*60)

    # 테스트 텍스트 생성
    test_text = create_test_text()
    print("\n[원본 텍스트]")
    print("-"*40)
    print(test_text)
    print("-"*40)

    # optimize_line_breaks 함수 테스트
    optimized = optimize_line_breaks(test_text)
    print("\n[최적화된 텍스트]")
    print("-"*40)
    print(optimized)
    print("-"*40)

    # 부록 관련 패턴 검증
    print("\n[부록 패턴 검증]")
    print("-"*40)

    test_patterns = [
        ("2.1.2.2. 부록4.", "내용으로 처리되어야 함"),
        ("(부록) 참고사항", "내용으로 처리되어야 함"),
        ("[부록 1] 서식 양식", "제목으로 처리되어야 함"),
        ("부록 2. 업무 프로세스", "제목으로 처리되어야 함"),
        ("별표 1. 조직도", "제목으로 처리되어야 함"),
    ]

    for pattern, expected in test_patterns:
        if pattern in optimized:
            # 해당 패턴이 포함된 줄 찾기
            lines = optimized.split('\n')
            pattern_line = None
            for line in lines:
                if pattern in line:
                    pattern_line = line
                    break

            if pattern_line:
                # 패턴 뒤에 다른 내용이 같은 줄에 있는지 확인
                # 제목이면 패턴만 있거나 짧은 제목만 있어야 함
                # 내용이면 패턴 뒤에 긴 텍스트가 있어야 함
                pattern_index = pattern_line.find(pattern)
                text_after_pattern = pattern_line[pattern_index + len(pattern):].strip()

                if "제목으로" in expected:
                    # 제목은 패턴 뒤에 내용이 적거나 없어야 함
                    if len(text_after_pattern) < 20:
                        print(f"✅ '{pattern}': 제목으로 올바르게 처리됨")
                    else:
                        print(f"❌ '{pattern}': 제목으로 처리되어야 하는데 내용과 합쳐짐")
                elif "내용으로" in expected:
                    # 내용은 패턴 뒤에 다른 텍스트가 연결되어야 함
                    if len(text_after_pattern) > 10:
                        print(f"✅ '{pattern}': 내용으로 올바르게 처리됨 (연결된 텍스트: {len(text_after_pattern)}자)")
                    else:
                        print(f"❌ '{pattern}': 내용으로 처리되어야 하는데 독립된 줄로 처리됨")
        else:
            print(f"⚠️ '{pattern}': 텍스트에서 찾을 수 없음")

    print("\n[줄바꿈 처리 확인]")
    print("-"*40)

    # 줄바꿈이 올바르게 처리되었는지 확인
    lines = optimized.split('\n')
    for i, line in enumerate(lines, 1):
        if line.strip():
            print(f"{i:3}: {line[:60]}{'...' if len(line) > 60 else ''}")

    print("\n테스트 완료!")
    return optimized

def test_with_sample_pdf():
    """실제 PDF 파일로 테스트 (있는 경우)"""
    # PDF 파일 찾기
    pdf_dir = "/home/wizice/regulation/pdf"
    if os.path.exists(pdf_dir):
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        if pdf_files:
            print("\n" + "="*60)
            print("실제 PDF 파일 테스트")
            print("="*60)

            # 첫 번째 PDF 파일 선택
            sample_pdf = os.path.join(pdf_dir, pdf_files[0])
            print(f"\n테스트 파일: {pdf_files[0]}")

            # 임시 출력 파일
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                output_file = tmp.name

            try:
                # PDF 변환
                result = extract_text_from_pdf(sample_pdf, output_file)

                if result:
                    # 결과 파일 읽기
                    with open(output_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 부록 관련 내용 검색
                    print("\n[부록 관련 내용 검색]")
                    print("-"*40)

                    appendix_patterns = [
                        r'부록\s*\d+',
                        r'\[부록.*?\]',
                        r'\(부록\)',
                        r'별표\s*\d+',
                        r'\d+\.\d+.*?부록'
                    ]

                    found_any = False
                    for pattern in appendix_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            found_any = True
                            print(f"패턴 '{pattern}' 발견:")
                            for match in matches[:3]:  # 처음 3개만 표시
                                print(f"  - {match}")

                    if not found_any:
                        print("부록 관련 내용을 찾을 수 없음")

                    # 첫 500자 출력
                    print("\n[변환된 텍스트 미리보기 (처음 500자)]")
                    print("-"*40)
                    print(content[:500])
                    print("...")

            finally:
                # 임시 파일 삭제
                if os.path.exists(output_file):
                    os.remove(output_file)

if __name__ == "__main__":
    # 부록 파싱 테스트
    test_appendix_parsing()

    # 실제 PDF 파일 테스트
    test_with_sample_pdf()