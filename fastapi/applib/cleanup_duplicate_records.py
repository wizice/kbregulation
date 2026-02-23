#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_duplicate_records.py
중복된 규정 레코드를 정리하고 올바른 파일 경로를 설정

사용법:
    python cleanup_duplicate_records.py --dry-run
    python cleanup_duplicate_records.py
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from settings import settings

# 로깅 설정
log_dir = Path(f'{settings.APPLIB_DIR}/logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'cleanup_duplicates_{datetime.now():%Y%m%d_%H%M%S}.log'

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


def find_duplicate_wzruleid(cursor):
    """wzruleid별 중복 레코드 찾기"""
    cursor.execute("""
        SELECT wzruleid, wzpubno, COUNT(*) as cnt
        FROM wz_rule
        WHERE wzruleid IS NOT NULL
        GROUP BY wzruleid, wzpubno
        HAVING COUNT(*) > 1
        ORDER BY wzpubno
    """)

    return cursor.fetchall()


def get_records_for_wzruleid(cursor, wzruleid, wzpubno):
    """특정 wzruleid의 모든 레코드 조회"""
    cursor.execute("""
        SELECT wzruleseq, wzruleid, wzname, wzpubno, wzfilejson, wznewflag,
               wzlastrevdate, wzmodifiedby
        FROM wz_rule
        WHERE wzruleid = %s AND wzpubno = %s
        ORDER BY wzruleseq DESC
    """, (wzruleid, wzpubno))

    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    return [dict(zip(columns, row)) for row in results]


def select_primary_record(records):
    """현행 레코드 선택 (wzNewFlag='현행' 또는 최신 레코드)"""
    # 1순위: wzNewFlag='현행'
    for rec in records:
        if rec.get('wznewflag') == '현행':
            return rec

    # 2순위: wzfilejson이 있는 최신 레코드
    for rec in records:
        if rec.get('wzfilejson') and rec['wzfilejson'].strip():
            # NULL이나 빈 값이 아닌 경우
            return rec

    # 3순위: 가장 최신 레코드 (wzruleseq가 큰 것)
    return records[0]


def verify_json_file_match(record):
    """레코드의 wzruleid와 파일명의 wzruleid가 일치하는지 확인"""
    wzruleid = record['wzruleid']
    wzfilejson = record.get('wzfilejson', '')

    if not wzfilejson:
        return True, "파일 경로 없음"

    # 파일명에서 wzruleid 추출
    filename = os.path.basename(wzfilejson)

    # merged_ 제거
    if filename.startswith('merged_'):
        return False, f"파일명이 merged_로 시작: {filename}"

    # wzruleid_ 패턴 확인
    import re
    match = re.match(r'^(\d+)_', filename)
    if match:
        file_wzruleid = int(match.group(1))
        if file_wzruleid != wzruleid:
            return False, f"wzruleid 불일치: DB={wzruleid}, 파일={file_wzruleid}"
        return True, "일치"
    else:
        return False, f"wzruleid가 파일명에 없음: {filename}"


def cleanup_duplicates(dry_run=False):
    """중복 레코드 정리"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 중복 wzruleid 찾기
        duplicates = find_duplicate_wzruleid(cursor)

        logger.info(f"\n{'='*60}")
        logger.info(f"중복된 wzruleid 발견: {len(duplicates)}개")
        logger.info(f"{'='*60}\n")

        if len(duplicates) == 0:
            logger.info("✅ 중복 레코드가 없습니다.")
            return True

        for wzruleid, wzpubno, count in duplicates:
            logger.info(f"\n처리 중: wzruleid={wzruleid}, wzpubno={wzpubno}, 중복={count}개")

            # 모든 레코드 조회
            records = get_records_for_wzruleid(cursor, wzruleid, wzpubno)

            # 현행 레코드 선택
            primary = select_primary_record(records)
            logger.info(f"  선택된 현행 레코드: wzruleseq={primary['wzruleseq']}")

            # 파일 경로 검증
            is_valid, message = verify_json_file_match(primary)
            if not is_valid:
                logger.warning(f"  ⚠️ 파일 경로 문제: {message}")
                logger.warning(f"     wzfilejson={primary.get('wzfilejson')}")
            else:
                logger.info(f"  ✅ 파일 경로 검증: {message}")

            # 다른 레코드들 출력
            for rec in records:
                if rec['wzruleseq'] != primary['wzruleseq']:
                    logger.info(f"  - 삭제 대상: wzruleseq={rec['wzruleseq']}, "
                              f"wznewflag={rec.get('wznewflag')}, "
                              f"wzfilejson={rec.get('wzfilejson')}")

                    if not dry_run:
                        # 레코드 삭제
                        cursor.execute("""
                            DELETE FROM wz_rule WHERE wzruleseq = %s
                        """, (rec['wzruleseq'],))
                        logger.info(f"  ✅ 삭제 완료: wzruleseq={rec['wzruleseq']}")

        if not dry_run:
            conn.commit()
            logger.info("\n✅ DB 변경사항 커밋 완료")
        else:
            logger.info("\n[DRY-RUN] 실제 변경은 수행되지 않았습니다.")

        return True

    except Exception as e:
        logger.error(f"\n❌ 오류 발생: {e}")
        if not dry_run:
            conn.rollback()
            logger.info("🔄 DB 변경사항 롤백")
        return False
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='중복 레코드 정리 및 파일 경로 검증'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 변경 없이 시뮬레이션만 수행'
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("중복 레코드 정리 스크립트")
    print(f"{'='*60}")
    print(f"모드: {'DRY-RUN (시뮬레이션)' if args.dry_run else '실제 변경'}")
    print(f"로그 파일: {log_file}")
    print(f"{'='*60}\n")

    if not args.dry_run:
        confirm = input("⚠️ 실제로 중복 레코드를 삭제합니다. 계속하시겠습니까? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ 취소되었습니다.")
            return

    success = cleanup_duplicates(dry_run=args.dry_run)

    if success:
        if args.dry_run:
            print(f"\n✅ DRY-RUN 완료! 실제 변경하려면 --dry-run 옵션 없이 실행하세요.")
        else:
            print(f"\n✅ 중복 레코드 정리 완료!")
    else:
        print(f"\n❌ 처리 중 오류가 발생했습니다. 로그를 확인하세요.")

    print(f"📋 로그 파일: {log_file}\n")


if __name__ == '__main__':
    main()
