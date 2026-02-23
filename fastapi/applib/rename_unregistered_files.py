#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rename_unregistered_files.py
DB에 등록되지 않은 merged_ 파일들도 이름 변경 (wzruleid는 코드로 조회)

사용법:
    python rename_unregistered_files.py --dry-run
    python rename_unregistered_files.py
"""

import os
import re
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from settings import settings

# 로깅 설정
log_dir = Path(f'{settings.APPLIB_DIR}/logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'rename_unregistered_{datetime.now():%Y%m%d_%H%M%S}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """데이터베이스 연결"""
    import psycopg2
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD
    )


def extract_regulation_code(filename: str) -> Optional[str]:
    """
    파일명에서 규정 코드 추출
    """
    # merged_ 접두사 제거
    if filename.startswith('merged_'):
        filename = filename[7:]

    # wzruleid_ 접두사 제거
    wzruleid_match = re.match(r'^\d+_(.+)', filename)
    if wzruleid_match:
        filename = wzruleid_match.group(1)

    # 파일명에서 숫자.숫자.숫자 또는 숫자.숫자.숫자.숫자 패턴 찾기
    match = re.match(r'^(\d+(?:\.\d+){2,3})', filename)
    if match:
        return match.group(1)
    return None


def get_wzruleid_by_code(cursor, code: str) -> Optional[int]:
    """규정 코드로 wzruleid 조회"""
    cursor.execute("""
        SELECT wzruleid, wzruleseq, wzname
        FROM wz_rule
        WHERE wzpubno LIKE %s
        ORDER BY wzruleseq DESC
        LIMIT 1
    """, (f'{code}%',))

    result = cursor.fetchone()
    if result:
        wzruleid, wzruleseq, wzname = result
        logger.info(f"  - 코드 {code} → wzruleid={wzruleid}, wzname={wzname}")
        return wzruleid

    logger.warning(f"  ⚠️ 코드 {code}에 해당하는 규정을 찾을 수 없습니다.")
    return None


def rename_file(old_path: Path, wzruleid: int, dry_run: bool = False) -> bool:
    """파일명 변경"""
    try:
        old_name = old_path.name
        new_name = f"{wzruleid}_{old_name[7:]}"  # "merged_" 제거하고 wzruleid 추가
        new_path = old_path.parent / new_name

        if new_path.exists():
            logger.warning(f"  ⚠️ 대상 파일이 이미 존재합니다: {new_name}")
            return False

        if dry_run:
            logger.info(f"  [DRY-RUN] {old_name} → {new_name}")
            return True

        # 실제 파일 이름 변경
        old_path.rename(new_path)
        logger.info(f"  ✅ {old_name} → {new_name}")
        return True

    except Exception as e:
        logger.error(f"  ❌ 오류 발생: {e}")
        return False


def process_unregistered_files(dry_run: bool = False):
    """DB에 등록되지 않은 merged_ 파일들 처리"""
    merge_json_dir = Path(settings.MERGE_JSON_DIR)

    if not merge_json_dir.exists():
        logger.error(f"❌ 폴더가 존재하지 않습니다: {merge_json_dir}")
        return False

    # merged_로 시작하는 모든 JSON 파일 찾기
    merged_files = list(merge_json_dir.glob('merged_*.json'))
    merged_files = [f for f in merged_files if '.backup' not in f.name]

    logger.info(f"\n{'='*60}")
    logger.info(f"총 {len(merged_files)}개의 merged_ 파일 발견")
    logger.info(f"{'='*60}\n")

    if len(merged_files) == 0:
        logger.info("✅ 변경할 파일이 없습니다.")
        return True

    # DB 연결
    conn = get_db_connection()
    cursor = conn.cursor()

    success_count = 0
    fail_count = 0
    skip_count = 0

    try:
        for merged_file in merged_files:
            logger.info(f"\n처리 중: {merged_file.name}")

            # 규정 코드 추출
            code = extract_regulation_code(merged_file.name)
            if not code:
                logger.warning(f"  ⚠️ 코드를 추출할 수 없습니다. 스킵합니다.")
                skip_count += 1
                continue

            logger.info(f"  - 규정 코드: {code}")

            # wzruleid 조회
            wzruleid = get_wzruleid_by_code(cursor, code)
            if not wzruleid:
                skip_count += 1
                continue

            # 파일명 변경
            if rename_file(merged_file, wzruleid, dry_run):
                success_count += 1
            else:
                fail_count += 1

    except Exception as e:
        logger.error(f"\n❌ 처리 중 오류 발생: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

    # 결과 요약
    logger.info(f"\n{'='*60}")
    logger.info(f"처리 완료 요약")
    logger.info(f"{'='*60}")
    logger.info(f"✅ 성공: {success_count}개")
    logger.info(f"❌ 실패: {fail_count}개")
    logger.info(f"⏭️ 스킵: {skip_count}개")
    logger.info(f"📋 로그 파일: {log_file}")
    logger.info(f"{'='*60}\n")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='DB에 등록되지 않은 merged_ 파일들도 이름 변경'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 변경 없이 시뮬레이션만 수행'
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("DB 미등록 파일 이름 변경 스크립트")
    print(f"{'='*60}")
    print(f"모드: {'DRY-RUN (시뮬레이션)' if args.dry_run else '실제 변경'}")
    print(f"대상: merge_json/merged_*.json (DB에 없는 파일)")
    print(f"로그 파일: {log_file}")
    print(f"{'='*60}\n")

    if not args.dry_run:
        confirm = input("⚠️ 실제로 파일명을 변경합니다. 계속하시겠습니까? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ 취소되었습니다.")
            return

    success = process_unregistered_files(dry_run=args.dry_run)

    if success:
        if args.dry_run:
            print(f"\n✅ DRY-RUN 완료! 실제 변경하려면 --dry-run 옵션 없이 실행하세요.")
        else:
            print(f"\n✅ 파일명 변경 완료!")
    else:
        print(f"\n❌ 처리 중 오류가 발생했습니다. 로그를 확인하세요.")

    print(f"📋 로그 파일: {log_file}\n")


if __name__ == '__main__':
    main()
