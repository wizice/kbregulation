#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_filename_in_json.py
merge_json 폴더의 모든 JSON 파일에서 "파일명" 필드를 {wzruleid}.json 형식으로 업데이트
"""

import json
import os
import sys
import re
from pathlib import Path
import logging

# fastapi 경로를 sys.path에 추가하여 settings 사용 가능하게 함
sys.path.insert(0, str(Path(__file__).parent.parent))
from settings import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_wzruleid_from_filename(filename):
    """
    파일명에서 wzruleid 추출
    예: 5440.json -> 5440
    예: 5440_12.1.4._의무기록_사본발급_및_열람_20251027_201848.json -> 5440
    """
    # 파일명에서 숫자로 시작하는 패턴 찾기
    match = re.match(r'^(\d+)', filename)
    if match:
        return match.group(1)
    return None

def update_json_filename_field(json_path):
    """
    JSON 파일의 문서정보 -> 파일명 필드를 {wzruleid}.json 형식으로 업데이트

    Args:
        json_path: JSON 파일 경로

    Returns:
        bool: 업데이트 성공 여부
    """
    try:
        # JSON 파일 로드
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 파일명에서 wzruleid 추출
        filename = os.path.basename(json_path)
        wzruleid = extract_wzruleid_from_filename(filename)

        if not wzruleid:
            logger.warning(f"wzruleid를 추출할 수 없습니다: {filename}")
            return False

        # 새 파일명 형식
        new_filename = f"{wzruleid}.json"

        # 문서정보에 파일명 필드가 있는지 확인
        if '문서정보' not in data:
            logger.warning(f"'문서정보' 필드가 없습니다: {filename}")
            return False

        # 현재 파일명 확인
        old_filename = data['문서정보'].get('파일명', '')

        # 이미 올바른 형식이면 건너뛰기
        if old_filename == new_filename:
            logger.info(f"이미 올바른 형식입니다: {filename} -> {new_filename}")
            return True

        # 파일명 업데이트
        data['문서정보']['파일명'] = new_filename

        # 파일 저장
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 업데이트: {filename}")
        logger.info(f"   이전: {old_filename}")
        logger.info(f"   이후: {new_filename}")

        return True

    except Exception as e:
        logger.error(f"❌ 오류 발생 ({json_path}): {e}")
        return False

def main():
    """메인 함수"""
    merge_json_dir = Path(settings.MERGE_JSON_DIR)

    if not merge_json_dir.exists():
        logger.error(f"디렉토리를 찾을 수 없습니다: {merge_json_dir}")
        return

    logger.info("="*60)
    logger.info("merge_json 파일 파일명 필드 업데이트")
    logger.info("="*60)
    logger.info(f"대상 디렉토리: {merge_json_dir}")
    logger.info("")

    # 모든 JSON 파일 처리
    json_files = list(merge_json_dir.glob('*.json'))
    total_files = len(json_files)
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for json_file in sorted(json_files):
        # merged_severance.json은 건너뛰기
        if json_file.name == 'merged_severance.json':
            logger.info(f"⏭️  건너뛰기: {json_file.name} (병합 파일)")
            skipped_count += 1
            continue

        result = update_json_filename_field(json_file)
        if result:
            updated_count += 1
        else:
            error_count += 1

    logger.info("")
    logger.info("="*60)
    logger.info("처리 완료")
    logger.info("="*60)
    logger.info(f"전체 파일 수: {total_files}")
    logger.info(f"업데이트: {updated_count}")
    logger.info(f"건너뛰기: {skipped_count}")
    logger.info(f"오류: {error_count}")
    logger.info("="*60)

    if error_count == 0:
        logger.info("✅ 모든 파일이 성공적으로 처리되었습니다!")
    else:
        logger.warning(f"⚠️  {error_count}개 파일에서 오류가 발생했습니다.")

if __name__ == '__main__':
    main()
