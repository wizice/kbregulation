#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON_ALL.py
모든 JSON 파일을 severance.json 형식으로 병합하는 프로그램

사용법:
    python JSON_ALL.py --input-dir /path/to/json/folder --output merged_all.json
    python JSON_ALL.py  # 기본값 사용
"""

import json
import os
import sys
import re
from pathlib import Path
import argparse
from datetime import datetime
from typing import Dict, List, Any
import logging

# fastapi 경로를 sys.path에 추가하여 settings 사용 가능하게 함
sys.path.insert(0, str(Path(__file__).parent.parent))
from settings import settings

# 로깅 설정
log_dir = Path(f'{settings.APPLIB_DIR}/logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'json_all_{datetime.now():%Y%m%d_%H%M%S}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# DB 연결을 위한 import
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.query_wz_cate_v1 import WzCateTable
from settings import settings

# 기본 장 카테고리 매핑 (DB 조회 실패 시 사용)
DEFAULT_CHAPTER_MAPPING = {
    '1': {'title': '환자안전보장활동', 'icon': 'fas fa-shield-alt'},
    '2': {'title': '진료체계', 'icon': 'fas fa-stethoscope'},
    '3': {'title': '진료지원체계', 'icon': 'fas fa-procedures'},
    '4': {'title': '약물관리', 'icon': 'fas fa-pills'},
    '5': {'title': '수술 및 마취진정관리', 'icon': 'fas fa-procedures'},
    '6': {'title': '환자의 권리존중 및 보호', 'icon': 'fas fa-users'},
    '7': {'title': '지속적 질 향상', 'icon': 'fas fa-chart-line'},
    '8': {'title': '감염관리', 'icon': 'fas fa-shield-virus'},
    '9': {'title': '경영 및 조직관리', 'icon': 'fas fa-building'},
    '10': {'title': '인적자원관리', 'icon': 'fas fa-users-cog'},
    '11': {'title': '시설환경관리', 'icon': 'fas fa-hospital'},
    '12': {'title': '의료정보/의무기록 관리', 'icon': 'fas fa-file-medical'},
    '13': {'title': '교육', 'icon': 'fas fa-graduation-cap'}
}

# 아이콘 매핑 (title과 별도로 관리)
CHAPTER_ICONS = {
    '1': 'fas fa-shield-alt',
    '2': 'fas fa-stethoscope',
    '3': 'fas fa-procedures',
    '4': 'fas fa-pills',
    '5': 'fas fa-procedures',
    '6': 'fas fa-users',
    '7': 'fas fa-chart-line',
    '8': 'fas fa-shield-virus',
    '9': 'fas fa-building',
    '10': 'fas fa-users-cog',
    '11': 'fas fa-hospital',
    '12': 'fas fa-file-medical',
    '13': 'fas fa-graduation-cap'
}

def load_chapter_mapping_from_db():
    """
    DB의 WZ_CATE 테이블에서 장별 title 로드
    wzParentSeq가 NULL인 최상위 카테고리만 조회
    """
    try:
        wz_cate = WzCateTable(
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT)
        )

        wz_cate.connect()

        # 최상위 카테고리 조회 (wzParentSeq IS NULL)
        query = """
            SELECT wzCateSeq, wzCateName
            FROM WZ_CATE
            WHERE wzParentSeq IS NULL AND wzVisible = 'Y'
            ORDER BY wzOrder, wzCateSeq
        """

        results = wz_cate.query(query)
        wz_cate.close()

        chapter_mapping = {}

        if results:
            for row in results:
                seq = str(row.get('wzcateseq', ''))
                name = row.get('wzcatename', '').strip()

                if seq and name:
                    # 아이콘은 기존 매핑에서 가져오거나 기본값 사용
                    icon = CHAPTER_ICONS.get(seq, 'fas fa-folder')
                    chapter_mapping[seq] = {
                        'title': name,
                        'icon': icon
                    }
                    logger.info(f"DB에서 로드: {seq}장 - {name}")

        # 로드된 매핑이 있으면 반환, 없으면 기본값 사용
        if chapter_mapping:
            logger.info(f"DB에서 {len(chapter_mapping)}개 장 카테고리 로드 완료")
            return chapter_mapping
        else:
            logger.warning("DB에서 카테고리를 찾을 수 없어 기본값 사용")
            return DEFAULT_CHAPTER_MAPPING

    except Exception as e:
        logger.error(f"DB에서 카테고리 로드 실패: {e}")
        logger.info("기본 카테고리 매핑 사용")
        return DEFAULT_CHAPTER_MAPPING

def extract_regulation_code(filename, json_data=None):
    """
    파일명 또는 JSON 데이터에서 규정 코드 추출
    예: 1.1.1._정확한_환자_확인_202503개정.json -> 1.1.1
    예: merged_1.1.1._정확한_환자_확인_202503개정.json -> 1.1.1
    예: 2.1.1.1._세브란스병원_이용_외래_202503개정.json -> 2.1.1.1
    예: 1234_1.1.1._정확한_환자_확인_202503개정.json -> 1.1.1 (wzruleid 건너뛰기)
    예: 5440.json (JSON 내부의 규정명에서 추출) -> 12.1.4
    """
    # merged_ 접두사 제거
    if filename.startswith('merged_'):
        filename = filename[7:]  # 'merged_' 길이만큼 제거

    # wzruleid_ 접두사 제거 (숫자_로 시작하는 경우)
    wzruleid_match = re.match(r'^\d+_(.+)', filename)
    if wzruleid_match:
        filename = wzruleid_match.group(1)

    # 파일명에서 숫자.숫자.숫자 또는 숫자.숫자.숫자.숫자 패턴 찾기
    # \d+(\.\d+){2,3} : 숫자 다음에 .숫자가 2번 또는 3번 반복
    match = re.match(r'^(\d+(?:\.\d+){2,3})', filename)
    if match:
        return match.group(1)

    # 파일명에서 코드를 찾지 못한 경우, JSON 데이터에서 추출 시도
    if json_data:
        doc_info = json_data.get('문서정보', json_data.get('document_info', {}))
        regulation_name = doc_info.get('규정명', '') or doc_info.get('규정표기명', '')

        if regulation_name:
            # 규정명 앞부분에서 코드 패턴 추출 (예: "12.1.4. 의무기록 사본발급 및 열람" -> "12.1.4")
            code_match = re.match(r'^(\d+(?:\.\d+){2,3})\.?\s', regulation_name)
            if code_match:
                logger.info(f"파일명에서 추출 실패 ({filename}), JSON 데이터에서 코드 추출: {code_match.group(1)}")
                return code_match.group(1)

    return None

def extract_chapter_from_code(code):
    """
    규정 코드에서 장 번호 추출
    예: 1.1.1 -> 1
    """
    if code:
        parts = code.split('.')
        if parts:
            return parts[0]
    return None

def extract_appendix_from_articles(articles):
    """
    sections에서 제4조(부록) 추출
    """
    appendix_list = []
    found_je4_burok = False

    for i, article in enumerate(articles):
        # sections 형식의 필드명
        article_content = article.get('내용', '')
        article_number = article.get('번호', '')

        # 제4조 부록 패턴 체크
        if '제4조' in article_number and '부록' in article_content:
            found_je4_burok = True
            continue

        # 제4조(부록) 이후 1., 2., 3. 등으로 시작하는 항목들 수집
        if found_je4_burok:
            # 다음 조(제5조 등)가 나오면 중단
            if article_number and '제' in article_number and '조' in article_number:
                break

            # 1., 2., 3. 등의 번호 항목들 수집
            if article_number and re.match(r'^\d+\.$', article_number):
                if article_content and len(appendix_list) < 50:  # 너무 많은 항목 방지
                    appendix_list.append(article_content.strip())

    return appendix_list

def parse_json_file(filepath, pdf_map=None, comparison_map=None, pubno_to_seq_map=None):
    """
    JSON 파일 파싱 및 규정 정보 추출

    Args:
        filepath: JSON 파일 경로
        pdf_map: wzRuleSeq -> 현행내규 PDF 파일명 매핑
        comparison_map: wzRuleSeq -> 신구대비표 PDF 파일명 매핑
        pubno_to_seq_map: wzpubno -> wzRuleSeq 매핑 (DB fallback용)
    """
    if pdf_map is None:
        pdf_map = {}
    if comparison_map is None:
        comparison_map = {}
    if pubno_to_seq_map is None:
        pubno_to_seq_map = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        filename = os.path.basename(filepath)
        # JSON 데이터를 함께 전달하여 파일명에서 추출 실패 시 JSON에서 추출
        code = extract_regulation_code(filename, data)

        if not code:
            logger.warning(f"코드를 추출할 수 없는 파일: {filename}")
            return None

        # 새로운 형식: 문서정보와 조문내용 (merge_json 폴더의 형식)
        # 또는 이전 형식: document_info와 sections
        doc_info = data.get('문서정보', data.get('document_info', {}))
        articles = data.get('조문내용', data.get('sections', []))

        # name에서 코드 번호 제거
        regulation_name = doc_info.get('규정명', filename.replace('.json', '').replace('_', ' '))
        # 코드 패턴 제거 (예: "2.1.1.1. 세브란스병원 이용 - 외래" -> "세브란스병원 이용 - 외래")
        # 점이 있든 없든 코드 제거: "6.1.2 일관된 진료" or "6.1.2. 일관된 진료" -> "일관된 진료"
        import re
        name_without_code = re.sub(r'^\d+(?:\.\d+){2,3}\.?\s*', '', regulation_name)

        # 부록 추출
        appendix = extract_appendix_from_articles(articles)

        # 날짜 형식 변환 함수 (yyyy-mm-dd → yyyy.mm.dd.)
        def format_date(date_str):
            if date_str and isinstance(date_str, str) and '-' in date_str and '.' not in date_str:
                return date_str.replace('-', '.') + '.'
            return date_str

        # wzRuleSeq 추출 (규정ID)
        wz_rule_seq = doc_info.get('규정ID')

        # 규정ID가 없으면 DB에서 분류번호(wzpubno)로 조회 (fallback)
        if not wz_rule_seq and code and pubno_to_seq_map:
            wz_rule_seq = pubno_to_seq_map.get(code)
            if wz_rule_seq:
                logger.info(f"  ✓ DB fallback: {code} -> wzRuleSeq={wz_rule_seq}")

        # PDF 파일명 추출 (DB 매핑에서)
        pdf_filename = pdf_map.get(wz_rule_seq) if wz_rule_seq else None
        comparison_filename = comparison_map.get(wz_rule_seq) if wz_rule_seq else None

        # severance.json 형식의 regulation 객체 생성
        regulation = {
            'code': code,
            'name': name_without_code,
            'wzRuleSeq': wz_rule_seq,  # 규정 ID 추가
            'appendix': appendix,  # 추출한 부록 정보
            'detail': {
                'documentInfo': {
                    '규정명': doc_info.get('규정명', doc_info.get('규정표기명', '')),
                    '내규종류': doc_info.get('내규종류', '규정'),
                    '제정일': format_date(doc_info.get('제정일', '')),
                    '최종개정일': format_date(doc_info.get('최종개정일', '')),
                    '최종검토일': format_date(doc_info.get('최종검토일', '')),
                    '담당부서': doc_info.get('담당부서', ''),
                    '유관부서': doc_info.get('유관부서', ''),
                    '관련기준': doc_info.get('관련기준', []),
                    '파일명': filename,  # 파일명 추가
                    '현행내규PDF': pdf_filename,  # 현행내규 PDF 파일명
                    '신구대비표PDF': comparison_filename  # 신구대비표 PDF 파일명
                },
                'articles': articles  # sections를 articles로
            }
        }

        logger.info(f"  - 규정코드: {code}, 부록 {len(appendix)}개 항목 추출")

        return {
            'code': code,
            'chapter': extract_chapter_from_code(code),
            'regulation': regulation
        }

    except Exception as e:
        logger.error(f"파일 파싱 오류 {filepath}: {e}")
        return None

def merge_json_files(input_dir, output_file):
    """
    폴더 내 모든 JSON 파일을 severance.json 형식으로 병합
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        logger.error(f"입력 폴더가 존재하지 않습니다: {input_dir}")
        return False

    # DB에서 장 카테고리 매핑 로드
    logger.info("DB에서 장 카테고리 정보 로드 중...")
    CHAPTER_MAPPING = load_chapter_mapping_from_db()

    # DB에서 PDF 파일명 매핑 로드 (wzRuleSeq -> PDF 파일명)
    # 그리고 wzpubno -> wzRuleSeq 매핑 로드 (fallback용)
    logger.info("DB에서 PDF 파일명 및 분류번호 매핑 로드 중...")
    pdf_filename_map = {}
    comparison_filename_map = {}
    pubno_to_seq_map = {}  # wzpubno -> wzRuleSeq 매핑 (fallback용)
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT),
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wzRuleSeq, wzFilePdf, wzFileComparison, wzpubno
            FROM wz_rule
            WHERE wzNewFlag = '현행'
        """)
        for row in cursor.fetchall():
            wz_rule_seq = row[0]
            wz_file_pdf = row[1]
            wz_file_comparison = row[2]
            wz_pubno = row[3]

            if wz_file_pdf:
                pdf_filename_map[wz_rule_seq] = wz_file_pdf
            if wz_file_comparison:
                # comparisonTable/{wzruleid}_{wzruleseq}_{date}.pdf 형식에서 파일명만 추출
                comparison_filename_map[wz_rule_seq] = wz_file_comparison.split('/')[-1] if '/' in wz_file_comparison else wz_file_comparison

            # 분류번호 -> wzRuleSeq 매핑 (fallback용)
            # 점 있는/없는 버전 모두 저장 (매칭 보장)
            if wz_pubno and wz_rule_seq:
                pubno_to_seq_map[wz_pubno] = wz_rule_seq
                # 점 있는 버전이면 점 없는 버전도 추가
                if wz_pubno.endswith('.'):
                    pubno_to_seq_map[wz_pubno.rstrip('.')] = wz_rule_seq
                # 점 없는 버전이면 점 있는 버전도 추가
                else:
                    pubno_to_seq_map[wz_pubno + '.'] = wz_rule_seq

        # 중복 wzpubno 체크 (동일 분류번호에 여러 현행 규정이 있는지 확인)
        cursor.execute("""
            SELECT wzpubno, COUNT(*) as cnt, array_agg(wzRuleSeq) as seqs
            FROM wz_rule
            WHERE wzNewFlag = '현행' AND wzpubno IS NOT NULL
            GROUP BY wzpubno
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            logger.warning(f"⚠️ 중복 분류번호 발견 (현행 규정):")
            for wzpubno, cnt, seqs in duplicates:
                logger.warning(f"  - {wzpubno}: {cnt}개 규정 (wzRuleSeq: {seqs})")
                # 첫 번째 것만 매핑 (나머지는 무시)
                logger.warning(f"    → wzRuleSeq={seqs[0]}만 매핑에 사용")

        cursor.close()
        conn.close()
        logger.info(f"✓ DB에서 {len(pdf_filename_map)}개 현행내규, {len(comparison_filename_map)}개 신구대비표, {len(pubno_to_seq_map)}개 분류번호 매핑 로드 완료")
    except Exception as e:
        logger.warning(f"⚠️ DB에서 매핑 정보 로드 실패: {e}")

    # 결과 저장할 구조
    result = {}

    # 통계
    processed = 0
    failed = 0

    # JSON 파일 목록 가져오기
    json_files = list(input_path.glob('*.json'))

    if not json_files:
        logger.warning(f"JSON 파일이 없습니다: {input_dir}")
        return False

    logger.info(f"총 {len(json_files)}개의 JSON 파일 발견")

    # 코드별로 파일 그룹화 (중복 코드 처리)
    code_to_files = {}
    for json_file in json_files:
        # 파일명에서 코드 추출 시도
        code = extract_regulation_code(json_file.name)

        # 파일명에서 추출 실패 시 JSON 데이터 로드하여 재시도
        if not code:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                code = extract_regulation_code(json_file.name, data)
            except Exception as e:
                logger.warning(f"파일 읽기 실패 ({json_file.name}): {e}")

        if code:
            if code not in code_to_files:
                code_to_files[code] = []
            code_to_files[code].append(json_file)

    # 각 코드별로 최신 파일만 선택
    selected_files = []
    for code, files in code_to_files.items():
        if len(files) == 1:
            selected_files.append(files[0])
        else:
            # 타임스탬프나 수정시간으로 정렬하여 최신 파일 선택
            # 파일명에 타임스탬프가 있으면 그것 사용, 없으면 수정시간 사용
            latest_file = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
            selected_files.append(latest_file)
            logger.info(f"코드 {code}: {len(files)}개 파일 중 최신 파일 선택 - {latest_file.name}")

    logger.info(f"중복 제거 후 {len(selected_files)}개 파일 처리")

    # 각 JSON 파일 처리
    for json_file in selected_files:
        logger.info(f"처리 중: {json_file.name}")

        parsed = parse_json_file(json_file, pdf_filename_map, comparison_filename_map, pubno_to_seq_map)

        if parsed:
            chapter = parsed['chapter']

            # 장 키 생성 (예: "1장")
            chapter_key = f"{chapter}장"

            # 해당 장이 없으면 생성
            if chapter_key not in result:
                chapter_info = CHAPTER_MAPPING.get(chapter, {
                    'title': f'{chapter}장',
                    'icon': 'fas fa-folder'
                })
                result[chapter_key] = {
                    'title': chapter_info['title'],
                    'icon': chapter_info['icon'],
                    'regulations': []
                }

            # 규정 추가
            result[chapter_key]['regulations'].append(parsed['regulation'])
            processed += 1
        else:
            failed += 1

    # 각 장의 규정을 코드 순으로 정렬
    for chapter_key in result:
        result[chapter_key]['regulations'].sort(key=lambda x: x['code'])

    # 장 순서대로 정렬된 딕셔너리 생성
    sorted_result = {}
    for i in range(1, 14):  # 1장부터 13장까지
        chapter_key = f"{i}장"
        if chapter_key in result:
            sorted_result[chapter_key] = result[chapter_key]

    # 나머지 장들 추가 (14장 이상이 있을 경우)
    for key in sorted(result.keys()):
        if key not in sorted_result:
            sorted_result[key] = result[key]

    # 결과 저장
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_result, f, ensure_ascii=False, indent=2)

        logger.info(f"병합 완료: {output_file}")
        logger.info(f"처리된 파일: {processed}개")
        logger.info(f"실패한 파일: {failed}개")

        # 각 장별 통계
        for chapter_key, chapter_data in sorted_result.items():
            count = len(chapter_data['regulations'])
            logger.info(f"  {chapter_key} ({chapter_data['title']}): {count}개 규정")

        return True

    except Exception as e:
        logger.error(f"결과 저장 실패: {e}")
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='JSON 파일들을 severance.json 형식으로 병합'
    )
    parser.add_argument(
        '--input-dir', '-i',
        type=str,
        default=settings.MERGE_JSON_DIR,
        help='입력 JSON 파일들이 있는 폴더 경로'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=f'{settings.APPLIB_DIR}/merged_severance.json',
        help='출력 파일 경로'
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("JSON 파일 병합 프로그램")
    print(f"{'='*60}")
    print(f"입력 폴더: {args.input_dir}")
    print(f"출력 파일: {args.output}")
    print(f"로그 파일: {log_file}")
    print(f"{'='*60}\n")

    # 병합 실행
    success = merge_json_files(args.input_dir, args.output)

    if success:
        print(f"\n✅ 병합이 완료되었습니다!")
        print(f"📁 출력 파일: {args.output}")

        # 파일 크기 확인
        output_size = os.path.getsize(args.output) / 1024 / 1024  # MB
        print(f"📊 파일 크기: {output_size:.2f} MB")
    else:
        print(f"\n❌ 병합 중 오류가 발생했습니다.")
        print(f"📋 로그 파일을 확인하세요: {log_file}")

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()