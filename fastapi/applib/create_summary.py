#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_summary.py
merged_severance.json에서 summary_kbregulation.json 형식으로 변환
articles 필드를 제외한 경량 버전 생성

사용법:
    python create_summary.py
    python create_summary.py --input /path/to/merged.json --output /path/to/summary.json
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
import logging
import re

# fastapi 경로를 sys.path에 추가하여 settings 사용 가능하게 함
sys.path.insert(0, str(Path(__file__).parent.parent))
from settings import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def natural_sort_key(code):
    """
    자연스러운 정렬을 위한 키 함수
    "2.1.3.10"을 ["2.1.3.2"] 뒤에 정렬

    예:
        "2.1.3.1" → [2, 1, 3, 1]
        "2.1.3.10" → [2, 1, 3, 10]
        "2.1.3.2" → [2, 1, 3, 2]
    """
    if not code:
        return []

    # "2.1.3.10" → ['2', '1', '3', '10']
    parts = re.split(r'\.', str(code))

    # 각 부분을 숫자로 변환 (숫자가 아니면 문자열 그대로)
    result = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))
        else:
            result.append(part)

    return result

def create_summary(input_file, output_file):
    """
    전체 JSON에서 summary 버전 생성
    articles 필드 제외하고 나머지 정보만 유지
    """
    try:
        # 입력 파일 읽기
        logger.info(f"읽기: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # DB 조회 불필요 - JSON 파일에서 직접 가져옴

        # summary 데이터 생성
        summary = {}
        total_regulations = 0

        for chapter_key, chapter_data in data.items():
            summary[chapter_key] = {
                'title': chapter_data.get('title', ''),
                'icon': chapter_data.get('icon', ''),
                'regulations': []
            }

            # 각 규정에서 articles 제외
            regulations_list = []
            for regulation in chapter_data.get('regulations', []):
                doc_info = regulation.get('detail', {}).get('documentInfo', {})

                # 날짜 형식 변환 (yyyy-mm-dd → yyyy.mm.dd.)
                if doc_info:
                    for date_field in ['최종개정일', '최종검토일', '제정일', '시행일']:
                        if date_field in doc_info and doc_info[date_field]:
                            date_value = doc_info[date_field]
                            # yyyy-mm-dd 형식이면 yyyy.mm.dd. 로 변환
                            if isinstance(date_value, str) and '-' in date_value and '.' not in date_value:
                                doc_info[date_field] = date_value.replace('-', '.') + '.'

                # wzRuleSeq 가져오기
                wz_rule_seq = regulation.get('wzRuleSeq')

                summary_reg = {
                    'code': regulation.get('code', ''),
                    'name': regulation.get('name', ''),
                    'wzRuleSeq': wz_rule_seq,  # 부록 조회에 필수
                    'appendix': regulation.get('appendix', []),
                    'detail': {
                        'documentInfo': doc_info  # 현행내규PDF, 신구대비표PDF 포함됨
                    }
                }
                regulations_list.append(summary_reg)
                total_regulations += 1

            # 자연스러운 정렬 적용 (code 기준)
            regulations_list.sort(key=lambda x: natural_sort_key(x.get('code', '')))
            summary[chapter_key]['regulations'] = regulations_list

            logger.info(f"✓ {chapter_key} 처리 완료: {len(regulations_list)}개 규정 (자연 정렬 적용)")

        # 결과 저장
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # 파일 크기 비교
        input_size = Path(input_file).stat().st_size / 1024 / 1024
        output_size = output_path.stat().st_size / 1024 / 1024
        reduction = ((input_size - output_size) / input_size) * 100

        logger.info(f"✅ Summary 생성 완료: {output_file}")
        logger.info(f"📊 총 {len(summary)}개 장, {total_regulations}개 규정")
        logger.info(f"💾 파일 크기: {input_size:.2f}MB → {output_size:.2f}MB (크기 {reduction:.1f}% 감소)")

        return True

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='merged_severance.json을 summary 형식으로 변환'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default=f'{settings.APPLIB_DIR}/merged_severance.json',
        help='입력 JSON 파일 경로'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=f'{settings.WWW_STATIC_FILE_DIR}/summary_kbregulation.json',
        help='출력 summary JSON 파일 경로'
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("Summary JSON 생성")
    print(f"{'='*60}")
    print(f"입력: {args.input}")
    print(f"출력: {args.output}")
    print(f"{'='*60}\n")

    success = create_summary(args.input, args.output)

    if success:
        print(f"\n✅ Summary 파일이 생성되었습니다!")
        print(f"📁 {args.output}")
    else:
        print(f"\n❌ 생성 실패. 로그를 확인하세요.")

    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()