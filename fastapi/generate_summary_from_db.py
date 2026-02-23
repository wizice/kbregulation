#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB로부터 직접 summary_kbregulation.json 생성
규정 추가/삭제 시 자동으로 summary 업데이트

사용법:
    python generate_summary_from_db.py
    python generate_summary_from_db.py --output /path/to/summary.json
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
import logging
import os

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from api.timescale_dbv1 import TimescaleDB
from settings import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_category_for_regulation(rule_name, dept_name):
    """
    규정명과 담당부서를 기반으로 카테고리 결정

    KB신용정보 규정은 별도 카테고리로 분류
    """
    # KB 규정은 "KB규정" 카테고리
    # '인사' 키워드 제거 (세브란스 규정과 중복됨)
    if any(keyword in rule_name for keyword in ['여비', 'KB', '급여', '복리']):
        return "KB규정"

    # 세브란스 규정은 기존 분류 유지 (임시로 "기타" 사용)
    return "기타"


def generate_summary_from_db(output_file):
    """
    DB에서 직접 summary_kbregulation.json 생성
    """
    db = TimescaleDB(
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )

    try:
        db.connect()
        logger.info("DB 연결 성공")

        # 현행 규정 조회
        query = """
        SELECT
            wzruleseq,
            wzruleid,
            wzname,
            wzpubno,
            wzestabdate,
            wzlastrevdate,
            wzexecdate,
            wzmgrdptnm,
            wzfilejson,
            wzfilepdf,
            wzfiledocx
        FROM wz_rule
        WHERE wznewflag = '현행'
        ORDER BY wzruleid ASC
        """

        regulations = db.query(query)
        logger.info(f"DB에서 {len(regulations)}개 규정 조회 완료")

        # 카테고리별로 분류
        categories = {}
        kb_regulations = []
        other_regulations = []

        for reg in regulations:
            rule_name = reg['wzname'] or ''
            dept_name = reg['wzmgrdptnm'] or ''
            category = get_category_for_regulation(rule_name, dept_name)

            # 규정 정보 구성
            regulation_data = {
                'code': reg['wzpubno'] or '',
                'name': rule_name,
                'wzRuleSeq': reg['wzruleseq'],
                'appendix': [],  # 부록은 별도 조회 필요
                'detail': {
                    'documentInfo': {
                        '규정명': rule_name,
                        '내규종류': '규정',
                        '제정일': reg['wzestabdate'] or '',
                        '최종개정일': reg['wzlastrevdate'] or '',
                        '시행일': reg['wzexecdate'] or '',
                        '담당부서': dept_name,
                        '파일명': reg['wzfilejson'] or '',
                        '현행내규PDF': reg['wzfilepdf'] or None,
                        '신구대비표PDF': None
                    }
                }
            }

            if category == "KB규정":
                kb_regulations.append(regulation_data)
            else:
                other_regulations.append(regulation_data)

        # Summary 구조 생성
        summary = {}

        # KB규정 카테고리 추가
        if kb_regulations:
            summary["KB규정"] = {
                "title": "KB신용정보 사규",
                "icon": "fas fa-building",
                "regulations": kb_regulations
            }
            logger.info(f"KB규정 카테고리 생성: {len(kb_regulations)}개 규정")

        # 기타 규정은 "세브란스규정" 카테고리로
        if other_regulations:
            summary["세브란스규정"] = {
                "title": "세브란스병원 내규 (백업)",
                "icon": "fas fa-hospital",
                "regulations": other_regulations
            }
            logger.info(f"세브란스규정 카테고리 생성: {len(other_regulations)}개 규정")

        # 파일 저장
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 백업 생성
        if output_path.exists():
            backup_path = output_path.with_suffix('.json.backup')
            with open(output_path, 'r', encoding='utf-8') as f:
                backup_data = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_data)
            logger.info(f"기존 파일 백업: {backup_path}")

        # 새 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        output_size = output_path.stat().st_size / 1024

        logger.info(f"✅ Summary 생성 완료: {output_file}")
        logger.info(f"📊 총 {len(summary)}개 카테고리, {len(regulations)}개 규정")
        logger.info(f"💾 파일 크기: {output_size:.2f}KB")

        return True

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def update_summary_add_regulation(wzruleseq, output_file=None):
    """
    규정 추가 시 summary 업데이트
    """
    if output_file is None:
        output_file = f'{settings.WWW_STATIC_FILE_DIR}/summary_kbregulation.json'

    # 전체 재생성 (간단하고 안전)
    return generate_summary_from_db(output_file)


def update_summary_remove_regulation(wzruleseq, output_file=None):
    """
    규정 삭제 시 summary 업데이트
    """
    if output_file is None:
        output_file = f'{settings.WWW_STATIC_FILE_DIR}/summary_kbregulation.json'

    # 전체 재생성 (간단하고 안전)
    return generate_summary_from_db(output_file)


def main():
    parser = argparse.ArgumentParser(
        description='DB로부터 summary_kbregulation.json 생성'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=f'{settings.WWW_STATIC_FILE_DIR}/summary_kbregulation.json',
        help='출력 summary JSON 파일 경로'
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print("DB로부터 Summary JSON 생성")
    print(f"{'='*70}")
    print(f"출력: {args.output}")
    print(f"{'='*70}\n")

    success = generate_summary_from_db(args.output)

    if success:
        print(f"\n✅ Summary 파일이 생성되었습니다!")
        print(f"📁 {args.output}")
    else:
        print(f"\n❌ 생성 실패. 로그를 확인하세요.")

    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
