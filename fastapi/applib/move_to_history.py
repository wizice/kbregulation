#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
move_to_history.py
연혁으로 변경된 규정의 JSON 파일을 merge_json_old 폴더로 이동

사용법:
    python move_to_history.py --file /path/to/json/file
    python move_to_history.py --rule-id 123
    python move_to_history.py --all  # 모든 연혁 파일 이동
"""

import os
import sys
import shutil
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoryMover:
    """연혁 JSON 파일 이동 관리 클래스"""

    def __init__(self):
        """초기화"""
        # 경로 설정
        self.merge_json_dir = Path(settings.MERGE_JSON_DIR)
        self.merge_json_old_dir = Path(f'{settings.APPLIB_DIR}/merge_json_old')

        # merge_json_old 폴더 생성
        self.merge_json_old_dir.mkdir(exist_ok=True)

        # DB 연결 설정
        self.db_config = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
        }

        logger.info(f"Source directory: {self.merge_json_dir}")
        logger.info(f"Target directory: {self.merge_json_old_dir}")

    def move_file_to_history(self, file_path: str, update_db: bool = True) -> Dict[str, Any]:
        """
        특정 JSON 파일을 merge_json_old로 이동

        Args:
            file_path: 이동할 JSON 파일 경로
            update_db: DB의 wzFileJson 경로 업데이트 여부

        Returns:
            이동 결과 정보
        """
        try:
            source_path = Path(file_path)

            if not source_path.exists():
                logger.error(f"File not found: {file_path}")
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }

            # 대상 경로 생성
            target_path = self.merge_json_old_dir / source_path.name

            # 파일명 중복 처리
            if target_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                stem = source_path.stem
                suffix = source_path.suffix
                target_path = self.merge_json_old_dir / f"{stem}_backup_{timestamp}{suffix}"

            # 파일 이동
            shutil.move(str(source_path), str(target_path))
            logger.info(f"Moved file: {source_path} -> {target_path}")

            # DB 업데이트
            if update_db:
                self._update_db_path(str(source_path), str(target_path))

            return {
                'success': True,
                'source': str(source_path),
                'target': str(target_path),
                'message': 'File moved successfully'
            }

        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def move_by_rule_id(self, rule_id: int) -> Dict[str, Any]:
        """
        특정 규정 ID의 JSON 파일을 이동

        Args:
            rule_id: 규정 ID

        Returns:
            이동 결과 정보
        """
        try:
            # DB에서 현재 JSON 경로 조회
            db_manager = DatabaseConnectionManager(**self.db_config)

            query = """
                SELECT wzFileJson, wzname, wzpubno
                FROM wz_rule
                WHERE wzruleseq = %s
            """

            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (rule_id,))
                    result = cursor.fetchone()

            if not result:
                return {
                    'success': False,
                    'error': f'Rule not found: {rule_id}'
                }

            json_path = result[0]
            rule_name = result[1]
            rule_pubno = result[2]

            if not json_path:
                return {
                    'success': False,
                    'error': f'No JSON file for rule {rule_id}'
                }

            # 파일 이동
            move_result = self.move_file_to_history(json_path, update_db=True)

            if move_result['success']:
                move_result['rule_id'] = rule_id
                move_result['rule_name'] = rule_name
                move_result['rule_pubno'] = rule_pubno

            return move_result

        except Exception as e:
            logger.error(f"Error moving by rule ID: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def move_all_history_files(self) -> Dict[str, Any]:
        """
        모든 연혁(wzNewFlag != '현행') 규정의 JSON 파일을 이동

        Returns:
            이동 결과 정보
        """
        try:
            db_manager = DatabaseConnectionManager(**self.db_config)

            # 연혁 규정 조회
            query = """
                SELECT wzruleseq, wzFileJson, wzname, wzpubno
                FROM wz_rule
                WHERE wzNewFlag != '현행'
                AND wzNewFlag IS NOT NULL
                AND wzFileJson IS NOT NULL
                AND wzFileJson LIKE '%merge_json/%'
            """

            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()

            if not rows:
                logger.info("No history files to move")
                return {
                    'success': True,
                    'message': 'No history files to move',
                    'moved': 0
                }

            logger.info(f"Found {len(rows)} history files to move")

            results = {
                'success': True,
                'total': len(rows),
                'moved': 0,
                'failed': 0,
                'details': []
            }

            for row in rows:
                rule_id = row[0]
                json_path = row[1]
                rule_name = row[2]
                rule_pubno = row[3]

                logger.info(f"Moving history file for rule {rule_id}: {rule_name}")

                move_result = self.move_file_to_history(json_path, update_db=True)

                if move_result['success']:
                    results['moved'] += 1
                    results['details'].append({
                        'rule_id': rule_id,
                        'rule_name': rule_name,
                        'rule_pubno': rule_pubno,
                        'status': 'success',
                        'new_path': move_result['target']
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'rule_id': rule_id,
                        'rule_name': rule_name,
                        'rule_pubno': rule_pubno,
                        'status': 'failed',
                        'error': move_result.get('error')
                    })

            logger.info(f"Move completed: {results['moved']} success, {results['failed']} failed")
            return results

        except Exception as e:
            logger.error(f"Error moving all history files: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _update_db_path(self, old_path: str, new_path: str):
        """
        DB의 wzFileJson 경로 업데이트

        Args:
            old_path: 이전 경로
            new_path: 새 경로
        """
        try:
            db_manager = DatabaseConnectionManager(**self.db_config)

            query = """
                UPDATE wz_rule
                SET wzFileJson = %s
                WHERE wzFileJson = %s
            """

            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (new_path, old_path))
                    conn.commit()

                    if cursor.rowcount > 0:
                        logger.info(f"Updated DB path for {cursor.rowcount} records")
                    else:
                        logger.warning(f"No DB records updated for path: {old_path}")

        except Exception as e:
            logger.error(f"Error updating DB path: {e}")

    def restore_from_history(self, file_path: str) -> Dict[str, Any]:
        """
        merge_json_old에서 merge_json으로 파일 복원

        Args:
            file_path: 복원할 파일 경로

        Returns:
            복원 결과 정보
        """
        try:
            source_path = Path(file_path)

            if not source_path.exists():
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }

            # 대상 경로 생성
            target_path = self.merge_json_dir / source_path.name

            # 파일명 중복 처리
            if target_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                stem = source_path.stem
                suffix = source_path.suffix
                target_path = self.merge_json_dir / f"{stem}_restored_{timestamp}{suffix}"

            # 파일 이동
            shutil.move(str(source_path), str(target_path))
            logger.info(f"Restored file: {source_path} -> {target_path}")

            # DB 업데이트
            self._update_db_path(str(source_path), str(target_path))

            return {
                'success': True,
                'source': str(source_path),
                'target': str(target_path),
                'message': 'File restored successfully'
            }

        except Exception as e:
            logger.error(f"Error restoring file: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='연혁 JSON 파일을 merge_json_old 폴더로 이동'
    )
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='이동할 JSON 파일 경로'
    )
    parser.add_argument(
        '--rule-id', '-r',
        type=int,
        help='이동할 규정 ID'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='모든 연혁 파일 이동'
    )
    parser.add_argument(
        '--restore',
        type=str,
        help='merge_json_old에서 복원할 파일 경로'
    )

    args = parser.parse_args()

    # HistoryMover 인스턴스 생성
    mover = HistoryMover()

    print(f"\n{'='*60}")
    print("연혁 JSON 파일 이동 프로그램")
    print(f"{'='*60}\n")

    # 실행 모드 선택
    if args.restore:
        # 파일 복원
        print(f"복원할 파일: {args.restore}")
        result = mover.restore_from_history(args.restore)

    elif args.file:
        # 특정 파일 이동
        print(f"이동할 파일: {args.file}")
        result = mover.move_file_to_history(args.file)

    elif args.rule_id:
        # 특정 규정 ID로 이동
        print(f"이동할 규정 ID: {args.rule_id}")
        result = mover.move_by_rule_id(args.rule_id)

    elif args.all:
        # 모든 연혁 파일 이동
        print("모든 연혁 파일을 이동합니다...")
        result = mover.move_all_history_files()

    else:
        print("옵션을 선택해주세요:")
        print("  --file FILE      특정 파일 이동")
        print("  --rule-id ID     특정 규정 ID로 이동")
        print("  --all            모든 연혁 파일 이동")
        print("  --restore FILE   파일 복원")
        return

    # 결과 출력
    print(f"\n{'='*60}")
    if result['success']:
        print("✅ 작업이 완료되었습니다!")

        if 'moved' in result:
            print(f"📊 이동 결과: {result['moved']}개 성공, {result['failed']}개 실패")
        elif 'target' in result:
            print(f"📁 새 경로: {result['target']}")
    else:
        print(f"❌ 작업 실패: {result.get('error')}")

    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()