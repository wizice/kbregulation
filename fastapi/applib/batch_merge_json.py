#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
txt_json 폴더와 docx_json 폴더의 모든 JSON 파일을 병합
같은 이름의 파일끼리 매칭하여 병합

사용법:
    python batch_merge_json.py
    python batch_merge_json.py --txt-dir /path/to/txt_json --docx-dir /path/to/docx_json --output-dir /path/to/output
"""

import json
import os
import sys
from pathlib import Path
import argparse
from datetime import datetime
import logging

# fastapi 경로를 sys.path에 추가하여 settings 사용 가능하게 함
sys.path.insert(0, str(Path(__file__).parent.parent))
from settings import settings

# merge_json 모듈 import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from merge_json import JSONMerger

# 로깅 설정
log_dir = Path(f'{settings.APPLIB_DIR}/logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'batch_merge_{datetime.now():%Y%m%d_%H%M%S}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def find_matching_files(txt_json_dir, docx_json_dir):
    """
    txt_json과 docx_json 폴더에서 같은 이름의 파일 쌍 찾기

    Args:
        txt_json_dir: txt에서 변환된 JSON 파일들이 있는 폴더
        docx_json_dir: docx에서 변환된 JSON 파일들이 있는 폴더

    Returns:
        list: (txt_json_path, docx_json_path, base_name) 튜플 리스트
    """
    txt_files = {f.stem: f for f in Path(txt_json_dir).glob('*.json')}
    docx_files = {f.stem: f for f in Path(docx_json_dir).glob('*.json')}

    matched_pairs = []

    # 같은 이름의 파일 찾기
    for base_name in txt_files:
        if base_name in docx_files:
            matched_pairs.append((
                txt_files[base_name],
                docx_files[base_name],
                base_name
            ))
            logger.info(f"매칭 발견: {base_name}")
        else:
            logger.warning(f"DOCX 파일 없음: {base_name}")

    # DOCX만 있고 TXT가 없는 파일 체크
    for base_name in docx_files:
        if base_name not in txt_files:
            logger.warning(f"TXT 파일 없음: {base_name}")

    return matched_pairs

def merge_files(txt_json_path, docx_json_path, output_path):
    """
    두 JSON 파일을 병합

    Args:
        txt_json_path: TXT에서 변환된 JSON 파일 경로 (PDF 파싱 결과)
        docx_json_path: DOCX에서 변환된 JSON 파일 경로
        output_path: 출력 파일 경로

    Returns:
        bool: 성공 여부
    """
    try:
        logger.info(f"병합 시작: {txt_json_path.name} + {docx_json_path.name}")

        # JSON 파일 읽기
        with open(txt_json_path, 'r', encoding='utf-8') as f:
            txt_json_data = json.load(f)

        with open(docx_json_path, 'r', encoding='utf-8') as f:
            docx_json_data = json.load(f)

        # JSONMerger 사용하여 병합
        merger = JSONMerger(
            pdf_json_data=txt_json_data,  # txt_json은 PDF 파싱 결과
            docx_json_data=docx_json_data
        )

        # 병합 실행
        merged_data = merger.merge_regulation()

        if not merged_data:
            logger.error(f"병합 실패: {txt_json_path.name}")
            return False

        # 결과 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)

        logger.info(f"병합 성공: {output_path.name}")
        logger.info(f"  - 조문 개수: {len(merged_data.get('조문내용', []))}")

        return True

    except Exception as e:
        logger.error(f"병합 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='txt_json과 docx_json 폴더의 파일들을 일괄 병합')
    parser.add_argument('--txt-dir', type=str,
                       default=f'{settings.APPLIB_DIR}/txt_json',
                       help='TXT JSON 폴더 경로')
    parser.add_argument('--docx-dir', type=str,
                       default=f'{settings.APPLIB_DIR}/docx_json',
                       help='DOCX JSON 폴더 경로')
    parser.add_argument('--output-dir', type=str,
                       default=settings.MERGE_JSON_DIR,
                       help='출력 폴더 경로')

    args = parser.parse_args()

    # 경로 확인
    txt_json_dir = Path(args.txt_dir)
    docx_json_dir = Path(args.docx_dir)
    output_dir = Path(args.output_dir)

    if not txt_json_dir.exists():
        print(f"❌ TXT JSON 폴더가 없습니다: {txt_json_dir}")
        return

    if not docx_json_dir.exists():
        print(f"❌ DOCX JSON 폴더가 없습니다: {docx_json_dir}")
        return

    # 출력 폴더 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 폴더 정보:")
    print(f"  - TXT JSON: {txt_json_dir}")
    print(f"  - DOCX JSON: {docx_json_dir}")
    print(f"  - 출력 폴더: {output_dir}")
    print()

    # 매칭되는 파일 찾기
    matched_pairs = find_matching_files(txt_json_dir, docx_json_dir)

    if not matched_pairs:
        print("❌ 매칭되는 파일이 없습니다.")
        return

    print(f"📊 총 {len(matched_pairs)}개의 파일 쌍을 병합합니다.")
    print("="*60)

    # 통계
    success_count = 0
    fail_count = 0

    # 각 파일 쌍 병합
    for i, (txt_path, docx_path, base_name) in enumerate(matched_pairs, 1):
        print(f"\n[{i}/{len(matched_pairs)}] 처리 중: {base_name}")

        # 타임스탬프 추가된 출력 파일명
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"merged_{base_name}_{timestamp}.json"
        output_path = output_dir / output_filename

        # 병합 실행
        if merge_files(txt_path, docx_path, output_path):
            success_count += 1
            print(f"  ✅ 성공: {output_filename}")
        else:
            fail_count += 1
            print(f"  ❌ 실패: {base_name}")

    # 결과 요약
    print("\n" + "="*60)
    print("📈 처리 결과:")
    print(f"  - 성공: {success_count}개")
    print(f"  - 실패: {fail_count}개")
    print(f"  - 출력 폴더: {output_dir}")
    print(f"  - 로그 파일: {log_file}")

    if success_count > 0:
        print(f"\n✅ {success_count}개의 파일이 성공적으로 병합되었습니다!")

    if fail_count > 0:
        print(f"\n⚠️ {fail_count}개의 파일 병합에 실패했습니다. 로그를 확인하세요.")

if __name__ == '__main__':
    main()