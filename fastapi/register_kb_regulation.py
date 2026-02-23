#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KB신용정보 여비규정을 데이터베이스에 등록하는 스크립트
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'applib'))

import docx
from applib.utils.sequential_numbers import extract_numbers_from_docx, convert_to_sections_format
from applib.utils.docx_parser import extract_metadata
from api.timescale_dbv1 import TimescaleDB
from settings import settings

def parse_kb_regulation(docx_path: str):
    """KB 규정 DOCX 파일 파싱"""
    print(f"[1/6] DOCX 파일 파싱 중: {docx_path}")

    doc = docx.Document(docx_path)

    # 메타데이터 추출
    metadata = extract_metadata(doc)
    print(f"  - 규정명: {metadata['문서제목']}")
    print(f"  - 제정일: {metadata['제정일']}")
    print(f"  - 최종개정일: {metadata['최종개정일']}")

    # 조문 추출
    results = extract_numbers_from_docx(docx_path)
    sections = convert_to_sections_format(results)
    print(f"  - 조문 개수: {len(sections)}개")

    # JSON 구조 생성
    document_info = {
        "규정명": metadata['문서제목'],
        "제정일": metadata['제정일'],
        "최종개정일": metadata['최종개정일'],
        "시행일": metadata.get('시행일', ''),
        "소관부서": metadata.get('소관부서', ''),
        "조문갯수": len(sections),
        "개정이력": metadata.get('개정일_이력_텍스트', '')
    }

    document_structure = {
        "문서정보": document_info,
        "조문내용": sections
    }

    return document_structure, metadata

def save_json_file(data: dict, output_path: str):
    """JSON 파일 저장"""
    print(f"[2/6] JSON 파일 저장 중: {output_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  - 저장 완료: {os.path.getsize(output_path):,} bytes")

def copy_files_to_service(docx_path: str, json_path: str):
    """DOCX 및 JSON 파일을 서비스 디렉토리로 복사"""
    print(f"[3/6] 파일을 서비스 디렉토리로 복사 중...")

    # 파일명 생성
    docx_filename = os.path.basename(docx_path)
    json_filename = os.path.basename(json_path)

    # 대상 디렉토리
    docx_dest = os.path.join(settings.DOCX_DIR, docx_filename)
    json_dest = os.path.join(settings.WWW_STATIC_FILE_DIR, json_filename)

    # 디렉토리 생성
    os.makedirs(settings.DOCX_DIR, exist_ok=True)
    os.makedirs(settings.WWW_STATIC_FILE_DIR, exist_ok=True)

    # 파일 복사
    shutil.copy2(docx_path, docx_dest)
    shutil.copy2(json_path, json_dest)

    print(f"  - DOCX 복사: {docx_dest}")
    print(f"  - JSON 복사: {json_dest}")

    return docx_filename, json_filename

def register_to_database(metadata: dict, docx_filename: str, json_filename: str):
    """데이터베이스에 규정 등록"""
    print(f"[4/6] 데이터베이스에 규정 등록 중...")

    db = TimescaleDB(
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )

    try:
        db.connect()

        # 다음 wzruleid 조회
        next_rule_id_query = "SELECT COALESCE(MAX(wzruleid), 0) + 1 as next_id FROM wz_rule"
        result = db.query(next_rule_id_query, one=True)
        next_rule_id = result['next_id']

        print(f"  - 새 규정 ID: {next_rule_id}")

        # 규정명에서 공백 제거
        rule_name = metadata['문서제목'].replace(' ', '')

        # INSERT 쿼리
        insert_query = """
        INSERT INTO wz_rule (
            wzlevel, wzruleid, wzname, wzedittype,
            wzestabdate, wzlastrevdate, wzexecdate,
            wzmgrdptnm, wzcateseq,
            wzfiledocx, wzfilejson, wzfilepdf,
            wzcreatedby, wzmodifiedby, wznewflag,
            content_text, index_status
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s
        ) RETURNING wzruleseq
        """

        data = (
            1,  # wzlevel
            next_rule_id,  # wzruleid
            rule_name,  # wzname
            '규정',  # wzedittype
            metadata.get('제정일', ''),  # wzestabdate
            metadata.get('최종개정일', ''),  # wzlastrevdate
            metadata.get('시행일', ''),  # wzexecdate
            metadata.get('소관부서', 'KB신용정보'),  # wzmgrdptnm
            1,  # wzcateseq (기본 카테고리)
            docx_filename,  # wzfiledocx
            json_filename,  # wzfilejson
            '',  # wzfilepdf
            'system',  # wzcreatedby
            'system',  # wzmodifiedby
            '현행',  # wznewflag
            f"{rule_name} {metadata.get('개정일_이력_텍스트', '')}",  # content_text
            'indexed'  # index_status
        )

        result = db.query(insert_query, data, one=True, commit=True)

        # result가 dict인 경우와 int인 경우 모두 처리
        if isinstance(result, dict):
            wzruleseq = result['wzruleseq']
        elif isinstance(result, int):
            wzruleseq = result
        else:
            # 마지막으로 삽입된 규정 조회
            last_query = "SELECT wzruleseq FROM wz_rule WHERE wzruleid = %s AND wznewflag = '현행' ORDER BY wzruleseq DESC LIMIT 1"
            last_result = db.query(last_query, (next_rule_id,), one=True)
            wzruleseq = last_result['wzruleseq']

        print(f"  - 등록 완료: wzruleseq = {wzruleseq}")

        return wzruleseq

    finally:
        db.close()

def main():
    """메인 함수"""
    print("="*70)
    print("KB신용정보 여비규정 등록 스크립트")
    print("="*70)

    # 파일 경로
    docx_path = '/home/wizice/kbregulation/test/(6-8)_여비규정_250305.docx'
    json_output_path = '/home/wizice/kbregulation/test/(6-8)_여비규정_250305.json'

    # 파일 존재 확인
    if not os.path.exists(docx_path):
        print(f"오류: DOCX 파일을 찾을 수 없습니다: {docx_path}")
        return 1

    try:
        # 1. DOCX 파싱
        document_structure, metadata = parse_kb_regulation(docx_path)

        # 2. JSON 저장
        save_json_file(document_structure, json_output_path)

        # 3. 파일 복사
        docx_filename, json_filename = copy_files_to_service(docx_path, json_output_path)

        # 4. DB 등록
        wzruleseq = register_to_database(metadata, docx_filename, json_filename)

        print("\n[5/6] 등록 결과 확인")
        print(f"  - wzruleseq: {wzruleseq}")
        print(f"  - 규정명: {metadata['문서제목'].replace(' ', '')}")
        print(f"  - DOCX 파일: {docx_filename}")
        print(f"  - JSON 파일: {json_filename}")

        print("\n[6/6] 완료!")
        print("="*70)
        print("KB 여비규정이 성공적으로 등록되었습니다.")
        print(f"웹 브라우저에서 확인: http://localhost:8000/regulations/{wzruleseq}")
        print("="*70)

        return 0

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
