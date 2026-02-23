#!/usr/bin/env python3
"""
merge_json 폴더의 파일을 분석하여 wz_rule 테이블의 wzFileJson 컬럼 업데이트

파일명 패턴: merged_{규정번호}_{규정명}_{날짜시간}.json
예시: merged_9.4.1._윤리적_관리_체계_20250923_203132.json
"""

import os
import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)


def extract_rule_number(filename: str) -> str:
    """
    파일명에서 규정 번호 추출

    Args:
        filename: 파일명 (예: merged_9.4.1._윤리적_관리_체계_20250923_203132.json)

    Returns:
        규정 번호 (예: 9.4.1.)
    """
    # merged_ 제거
    if filename.startswith('merged_'):
        filename = filename[7:]  # 'merged_' 길이

    # 규정 번호 패턴 매칭 (숫자.숫자.숫자. 또는 숫자.숫자.숫자.숫자.)
    # 더 정확한 패턴: 시작 부분의 숫자와 점으로 구성된 부분
    pattern = r'^(\d+(?:\.\d+)*\.)'
    match = re.match(pattern, filename)

    if match:
        return match.group(1)

    return None


def get_json_files_mapping() -> Dict[str, List[str]]:
    """
    merge_json 폴더의 파일을 규정 번호별로 매핑

    Returns:
        {규정번호: [파일경로 리스트]}
    """
    merge_json_dir = settings.MERGE_JSON_DIR
    mapping = {}

    if not os.path.exists(merge_json_dir):
        logger.error(f"Directory not found: {merge_json_dir}")
        return mapping

    # JSON 파일 목록 가져오기
    json_files = [f for f in os.listdir(merge_json_dir) if f.endswith('.json')]

    for filename in json_files:
        rule_number = extract_rule_number(filename)
        if rule_number:
            full_path = os.path.join(merge_json_dir, filename)

            if rule_number not in mapping:
                mapping[rule_number] = []

            # 파일 수정 시간과 함께 저장
            file_stat = os.stat(full_path)
            mapping[rule_number].append({
                'path': full_path,
                'filename': filename,
                'mtime': file_stat.st_mtime
            })

    # 각 규정별로 최신 파일만 선택
    for rule_number in mapping:
        # 수정 시간 기준 정렬 (최신순)
        mapping[rule_number].sort(key=lambda x: x['mtime'], reverse=True)
        # 최신 파일의 전체 경로만 저장
        mapping[rule_number] = mapping[rule_number][0]['path']

    return mapping


def update_database(mapping: Dict[str, str], dry_run: bool = True):
    """
    데이터베이스 업데이트

    Args:
        mapping: {규정번호: 파일경로} 매핑
        dry_run: True면 실제 업데이트 없이 쿼리만 출력
    """
    # DB 연결
    db_config = {
        'host': settings.DB_HOST,
        'port': settings.DB_PORT,
        'database': settings.DB_NAME,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
    }

    db_manager = DatabaseConnectionManager(**db_config)

    try:

        # 규정 번호 길이 순으로 정렬 (긴 것부터 처리하여 정확한 매칭)
        sorted_rules = sorted(mapping.keys(), key=lambda x: (len(x), x), reverse=True)

        update_count = 0
        skip_count = 0

        for rule_number in sorted_rules:
            file_path = mapping[rule_number]

            # 규정 번호로 정확히 매칭되는 규정 찾기
            # wzpubno (분류번호) 또는 wzname (규정명)에서 매칭

            # 먼저 정확한 wzpubno 매칭 시도
            check_query = """
                SELECT wzruleseq, wzname, wzpubno, wzFileJson
                FROM wz_rule
                WHERE wzpubno = %s
            """

            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(check_query, (rule_number,))
                    rows = cursor.fetchall()
                    result = [{k: v for k, v in zip([desc[0] for desc in cursor.description], row)} for row in rows] if rows else None

            # wzpubno에서 못 찾으면 wzname에서 시작 부분 매칭
            if not result:
                # 규정 번호가 wzname의 시작 부분에 있는지 확인
                # 예: '1.1.1.' 은 '1.1.1. 정확한 환자 확인'과 매칭되어야 하지만
                #     '1.1.1.1. 다른 규정'과는 매칭되지 않아야 함
                check_query = """
                    SELECT wzruleseq, wzname, wzpubno, wzFileJson
                    FROM wz_rule
                    WHERE wzname LIKE %s
                    AND NOT EXISTS (
                        SELECT 1 FROM wz_rule r2
                        WHERE r2.wzname LIKE %s
                        AND length(r2.wzname) < length(wz_rule.wzname)
                        AND r2.wzpubno = %s
                    )
                    ORDER BY length(wzname)
                    LIMIT 1
                """

                # 규정 번호로 시작하는 wzname 검색
                like_pattern = f"{rule_number}%"
                with db_manager.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(check_query, (like_pattern, like_pattern, rule_number))
                        rows = cursor.fetchall()
                        result = [{k: v for k, v in zip([desc[0] for desc in cursor.description], row)} for row in rows] if rows else None

            if result:
                rule_id = result[0]['wzruleseq']
                rule_name = result[0]['wzname']
                current_path = result[0].get('wzfilejson')

                # 이미 동일한 경로가 설정되어 있으면 스킵
                if current_path == file_path:
                    logger.info(f"Skip (already set): {rule_number} - {rule_name}")
                    skip_count += 1
                    continue

                if dry_run:
                    print(f"[DRY RUN] Would update:")
                    print(f"  Rule: {rule_number} - {rule_name} (ID: {rule_id})")
                    print(f"  Path: {file_path}")
                    print(f"  Current: {current_path or 'NULL'}")
                    print()
                else:
                    # 실제 업데이트
                    update_query = """
                        UPDATE wz_rule
                        SET wzFileJson = %s
                        WHERE wzruleseq = %s
                    """

                    with db_manager.get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute(update_query, (file_path, rule_id))
                            conn.commit()
                    logger.info(f"Updated: {rule_number} - {rule_name} -> {file_path}")
                    update_count += 1
            else:
                logger.warning(f"No match found for rule number: {rule_number}")

        # DatabaseConnectionManager는 자동으로 커넥션을 관리함

        print(f"\n=== Summary ===")
        print(f"Total rules in mapping: {len(mapping)}")
        print(f"Updated: {update_count}")
        print(f"Skipped (already set): {skip_count}")
        print(f"Not found: {len(mapping) - update_count - skip_count}")

    except Exception as e:
        logger.error(f"Database error: {e}")
        raise


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Update wzFileJson column in wz_rule table')
    parser.add_argument('--execute', action='store_true',
                       help='실제로 DB를 업데이트 (이 옵션 없으면 dry-run)')
    parser.add_argument('--show-mapping', action='store_true',
                       help='파일 매핑 정보만 출력')

    args = parser.parse_args()

    print("=== Analyzing merge_json folder ===")
    mapping = get_json_files_mapping()

    if not mapping:
        print("No JSON files found in merge_json folder")
        return

    if args.show_mapping:
        print("\n=== File Mapping ===")
        for rule_number in sorted(mapping.keys()):
            print(f"{rule_number:15s} -> {os.path.basename(mapping[rule_number])}")
        print(f"\nTotal: {len(mapping)} rules")
        return

    print(f"Found {len(mapping)} unique rule numbers with JSON files")

    # 샘플 출력
    print("\n=== Sample mappings (first 5) ===")
    for i, (rule_number, file_path) in enumerate(list(mapping.items())[:5]):
        print(f"{rule_number:15s} -> {os.path.basename(file_path)}")

    if len(mapping) > 5:
        print(f"... and {len(mapping) - 5} more")

    print("\n=== Starting database update ===")
    update_database(mapping, dry_run=not args.execute)

    if not args.execute:
        print("\n[NOTE] This was a dry-run. Use --execute flag to actually update the database.")


if __name__ == "__main__":
    main()