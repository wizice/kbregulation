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


def generate_summary_from_db(output_file):
    """
    DB에서 직접 summary_kbregulation.json 생성
    wz_cate 분류 기반으로 카테고리별 규정 그룹핑
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

        # 분류 목록 조회
        cate_query = """
        SELECT wzcateseq, wzcatename, wzorder
        FROM wz_cate
        WHERE wzvisible = 'Y' OR wzvisible IS NULL
        ORDER BY wzorder, wzcateseq
        """
        categories_list = db.query(cate_query)
        logger.info(f"분류 {len(categories_list)}개 조회")

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
            wzfiledocx,
            wzcateseq
        FROM wz_rule
        WHERE wznewflag = '현행'
        ORDER BY wzcateseq,
            CASE WHEN split_part(wzpubno, '-', 1) ~ '^\d+$'
                 THEN CAST(split_part(wzpubno, '-', 1) AS INTEGER) ELSE 9999 END,
            CASE WHEN split_part(wzpubno, '-', 2) ~ '^\d+$'
                 THEN CAST(split_part(wzpubno, '-', 2) AS INTEGER) ELSE 9999 END
        """

        regulations = db.query(query)
        logger.info(f"DB에서 {len(regulations)}개 규정 조회 완료")

        # 부록 목록 조회 (wz_appendix)
        appendix_query = """
        SELECT wzruleseq, wzappendixno, wzappendixname
        FROM wz_appendix
        ORDER BY wzruleseq, wzappendixno::integer
        """
        try:
            appendix_list = db.query(appendix_query)
            logger.info(f"부록 {len(appendix_list)}개 조회")
        except Exception as e:
            logger.warning(f"부록 조회 실패 (무시): {e}")
            appendix_list = []

        # 규정별 부록 매핑 {wzruleseq: ["별표 제1호 ...", ...]}
        appendix_map = {}
        for ap in appendix_list:
            rseq = ap['wzruleseq']
            name = ap['wzappendixname'] or f"부록 {ap['wzappendixno']}"
            if rseq not in appendix_map:
                appendix_map[rseq] = []
            appendix_map[rseq].append(name)

        # 카테고리별로 분류
        cate_map = {c['wzcateseq']: c['wzcatename'].strip() for c in categories_list}
        cate_regulations = {}

        for reg in regulations:
            rule_name = reg['wzname'] or ''
            dept_name = reg['wzmgrdptnm'] or ''
            cate_seq = reg['wzcateseq'] or 0
            cate_name = cate_map.get(cate_seq, '미분류')
            cate_key = f"{cate_seq}편 {cate_name}"

            regulation_data = {
                'code': reg['wzpubno'] or '',
                'name': rule_name,
                'wzRuleSeq': reg['wzruleseq'],
                'appendix': appendix_map.get(reg['wzruleseq'], []),
                'detail': {
                    'documentInfo': {
                        '규정명': rule_name,
                        '내규종류': '규정',
                        '제정일': reg['wzestabdate'] or '',
                        '최종개정일': reg['wzlastrevdate'] or '',
                        '시행일': reg['wzexecdate'] or '',
                        '소관부서': dept_name,
                        '파일명': reg['wzfilejson'] or '',
                        '현행내규PDF': reg['wzfilepdf'] or None,
                        '신구대비표PDF': None
                    }
                }
            }

            if cate_key not in cate_regulations:
                cate_regulations[cate_key] = []
            cate_regulations[cate_key].append(regulation_data)

        # Summary 구조 생성
        # JS가 기대하는 2단계 중첩: { "KB규정": { "1편 정관·이사회": { regulations }, ... } }
        chapters = {}

        for cate in categories_list:
            cate_seq = cate['wzcateseq']
            cate_name = cate['wzcatename'].strip()
            cate_key = f"{cate_seq}편 {cate_name}"

            regs = cate_regulations.get(cate_key, [])
            chapters[cate_key] = {
                "title": f"제{cate_seq}편 {cate_name}",
                "icon": "fas fa-building",
                "regulations": regs
            }
            logger.info(f"{cate_key}: {len(regs)}개 규정")

        summary = {
            "KB규정": chapters
        }

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
