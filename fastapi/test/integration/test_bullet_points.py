#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
글머리 기호 보존 테스트
PDF의 글머리 기호가 병합 후에도 제대로 표시되는지 확인
"""

import json
import os
import sys

# applib 경로 추가
sys.path.append('/home/wizice/regulation/fastapi')
sys.path.append('/home/wizice/regulation/fastapi/applib')

def test_bullet_preservation():
    """글머리 기호 보존 테스트"""

    print("=" * 50)
    print("글머리 기호 보존 테스트")
    print("=" * 50)

    # 테스트용 PDF JSON 데이터 (글머리 기호 포함)
    pdf_json_data = {
        "문서정보": {
            "규정명": "테스트 규정",
            "제정일": "2025.01.01",
            "최종개정일": "2025.09.18"
        },
        "조문내용": [
            {
                "seq": 1,
                "레벨": 1,
                "번호": "제1조",
                "제목": "(목적)",
                "내용": "이 규정은 글머리 기호 테스트를 위한 것이다."
            },
            {
                "seq": 2,
                "레벨": 2,
                "번호": "①",
                "제목": "",
                "내용": "첫 번째 항목입니다."
            },
            {
                "seq": 3,
                "레벨": 3,
                "번호": "1.",
                "제목": "",
                "내용": "세부 항목 1번입니다."
            },
            {
                "seq": 4,
                "레벨": 3,
                "번호": "2.",
                "제목": "",
                "내용": "세부 항목 2번입니다."
            },
            {
                "seq": 5,
                "레벨": 2,
                "번호": "②",
                "제목": "",
                "내용": "두 번째 항목입니다."
            },
            {
                "seq": 6,
                "레벨": 1,
                "번호": "제2조",
                "제목": "(적용범위)",
                "내용": "이 규정은 모든 부서에 적용된다."
            }
        ]
    }

    # 테스트용 DOCX JSON 데이터 (내용 더 상세)
    docx_json_data = {
        "문서정보": {
            "규정명": "테스트 규정",
            "담당부서": "정보팀",
            "내규종류": "규정"
        },
        "조문내용": [
            {
                "제목": "제1조 (목적)",
                "내용": "이 규정은 글머리 기호가 정확하게 보존되는지 테스트하기 위한 것이다."
            },
            {
                "제목": "",
                "내용": "첫 번째 항목입니다. 이것은 더 자세한 설명이 포함된 버전입니다."
            },
            {
                "제목": "",
                "내용": "세부 항목 1번입니다. 추가 설명이 여기 있습니다."
            },
            {
                "제목": "",
                "내용": "세부 항목 2번입니다. 또 다른 추가 설명입니다."
            },
            {
                "제목": "",
                "내용": "두 번째 항목입니다. 이것도 상세한 설명이 추가되었습니다."
            },
            {
                "제목": "제2조 (적용범위)",
                "내용": "이 규정은 모든 부서 및 직원에게 적용된다."
            }
        ]
    }

    # merge_json 모듈 import
    try:
        import merge_json

        # 병합 실행
        merger = merge_json.JSONMerger(
            pdf_json_data=pdf_json_data,
            docx_json_data=docx_json_data
        )

        merged_data = merger.merge_regulation()

        # 결과 확인
        print("\n병합 결과:")
        print("-" * 30)

        if merged_data and '조문내용' in merged_data:
            for item in merged_data['조문내용']:
                번호 = item.get('번호', '')
                제목 = item.get('제목', '')
                내용 = item.get('내용', '')[:50] + '...' if len(item.get('내용', '')) > 50 else item.get('내용', '')

                if 번호:
                    print(f"[✓] 번호: {번호}")
                else:
                    print(f"[✗] 번호 없음")

                print(f"    제목: {제목}")
                print(f"    내용: {내용}")
                print()

            # 글머리 기호 보존 검증
            bullets_found = []
            for item in merged_data['조문내용']:
                if item.get('번호'):
                    bullets_found.append(item['번호'])

            expected_bullets = ["제1조", "①", "1.", "2.", "②", "제2조"]

            print("\n검증 결과:")
            print("-" * 30)
            print(f"예상 글머리: {expected_bullets}")
            print(f"실제 글머리: {bullets_found}")

            if bullets_found == expected_bullets:
                print("\n✅ 성공: 모든 글머리 기호가 정확하게 보존되었습니다!")
            else:
                print("\n❌ 실패: 글머리 기호가 일치하지 않습니다!")
                missing = set(expected_bullets) - set(bullets_found)
                if missing:
                    print(f"   누락된 항목: {missing}")
                extra = set(bullets_found) - set(expected_bullets)
                if extra:
                    print(f"   추가된 항목: {extra}")
        else:
            print("❌ 병합 실패: 조문내용이 없습니다")

    except ImportError as e:
        print(f"❌ merge_json 모듈 import 실패: {e}")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bullet_preservation()