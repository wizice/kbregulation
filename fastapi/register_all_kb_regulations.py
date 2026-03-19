#!/usr/bin/env python3
"""
KB신용정보 전체 규정 일괄 등록 스크립트
- extracted/ 폴더의 92개 규정 본문 DOCX/DOC → DB 등록
- doc → docx 변환 (LibreOffice)
- DOCX → JSON 파싱 (docx2json 파이프라인)
- DB 삽입 (wz_rule)
- 별표/서식 PDF 변환 및 wz_appendix 등록
- www/static/file/ JSON 복사
- summary JSON 갱신
"""

import os
import sys
import re
import json
import shutil
import subprocess
import glob
import psycopg2
from datetime import datetime

# 경로 설정
BASE_DIR = "/home/wizice/kbregulation"
FASTAPI_DIR = os.path.join(BASE_DIR, "fastapi")
EXTRACTED_DIR = os.path.join(FASTAPI_DIR, "applib/docx/test/extracted")
DOCX_DIR = os.path.join(FASTAPI_DIR, "applib/docx")
STATIC_FILE_DIR = os.path.join(BASE_DIR, "www/static/file")
STATIC_PDF_DIR = os.path.join(BASE_DIR, "www/static/pdf")
MERGE_JSON_DIR = os.path.join(FASTAPI_DIR, "applib/merge_json")
PYTHON = "/home/wizice/venv3/bin/python"

sys.path.insert(0, FASTAPI_DIR)
sys.path.insert(0, os.path.join(FASTAPI_DIR, "applib"))

# DB 설정
DB_CONFIG = {
    "host": "localhost",
    "port": 35432,
    "dbname": "kbregulation",
    "user": "kbregulation",
    "password": "rhj3r>PLsXO#t0>E"
}

# 카테고리 매핑 (pubno 첫번째 숫자 → wzcateseq)
CATE_MAP = {
    "1": 1,   # 정관·이사회
    "2": 2,   # 직제·윤리
    "3": 3,   # 협의회(위원회)
    "4": 4,   # 재무·회계
    "5": 5,   # 기획·리스크관리
    "6": 6,   # 인사·복지
    "7": 7,   # 총무·경영지원
    "8": 8,   # IT·정보보호
    "9": 9,   # 영업
    "10": 10, # 브랜드·ESG
    "11": 11, # 감사·준법·법무
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_existing_rules():
    """현재 등록된 규정 목록 조회"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT wzpubno, wzname, wzruleseq, wznewflag FROM wz_rule WHERE wznewflag='현행'")
    existing = {row[0]: {"name": row[1], "seq": row[2]} for row in cur.fetchall()}
    conn.close()
    return existing

def parse_folder_name(folder_name):
    """폴더명에서 pubno와 규정명 추출: '(6-8) 여비규정' → ('6-8', '여비규정')"""
    m = re.match(r'\((\d+-\d+)\)\s+(.+)', folder_name)
    if m:
        return m.group(1), m.group(2).strip()
    return None, None

def parse_filename_date(filename):
    """파일명에서 날짜 추출: '_250305.docx' → '2025.03.05'"""
    m = re.search(r'_(\d{6})\.(?:docx?|pdf)$', filename, re.IGNORECASE)
    if m:
        d = m.group(1)
        yy = d[:2]
        year = f"20{yy}" if int(yy) < 50 else f"19{yy}"
        return f"{year}.{d[2:4]}.{d[4:6]}"
    return ""

def find_main_docx(folder_path, pubno):
    """폴더에서 규정 본문 파일 찾기 (별표/서식 제외)"""
    pattern_pubno = pubno.replace("-", "-")
    for f in os.listdir(folder_path):
        if not (f.lower().endswith('.docx') or f.lower().endswith('.doc')):
            continue
        # 별표/서식/별첨/붙임/첨부/샘플 제외
        if any(kw in f for kw in ['별표', '별첨', '서식', '붙임', '첨부', '샘플']):
            continue
        # pubno 패턴 매칭
        if f.startswith(f"({pubno})"):
            return os.path.join(folder_path, f)
    return None

def find_appendix_files(folder_path, pubno):
    """폴더에서 별표/서식/별첨 파일 목록"""
    appendix_files = []
    for f in sorted(os.listdir(folder_path)):
        if any(kw in f for kw in ['별표', '별첨', '서식', '붙임', '첨부']):
            if any(f.lower().endswith(ext) for ext in ['.docx', '.doc', '.xlsx', '.xls']):
                appendix_files.append(os.path.join(folder_path, f))
    return appendix_files

def convert_doc_to_docx(doc_path):
    """doc → docx 변환 (LibreOffice)"""
    output_dir = os.path.dirname(doc_path)
    try:
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "docx", doc_path, "--outdir", output_dir],
            capture_output=True, timeout=60
        )
        docx_path = doc_path.rsplit('.', 1)[0] + '.docx'
        if os.path.exists(docx_path):
            return docx_path
    except Exception as e:
        print(f"  [WARN] doc→docx 변환 실패: {e}")
    return None

def convert_to_pdf(file_path, output_dir):
    """DOCX/DOC/XLSX → PDF 변환"""
    os.makedirs(output_dir, exist_ok=True)
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.xlsx', '.xls']:
        # openpyxl + reportlab 변환 시도
        try:
            from applib.utils._xlsx_to_pdf import convert_xlsx_to_pdf
            basename = os.path.splitext(os.path.basename(file_path))[0]
            pdf_path = os.path.join(output_dir, f"{basename}.pdf")
            convert_xlsx_to_pdf(file_path, pdf_path)
            if os.path.exists(pdf_path):
                return pdf_path
        except Exception:
            pass

    # LibreOffice 변환
    try:
        # 한글 파일명 이슈 → temp 파일 사용
        import tempfile
        temp_dir = tempfile.mkdtemp()
        temp_name = f"input{ext}"
        temp_path = os.path.join(temp_dir, temp_name)
        shutil.copy2(file_path, temp_path)

        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", temp_path, "--outdir", temp_dir],
            capture_output=True, timeout=120
        )
        temp_pdf = os.path.join(temp_dir, "input.pdf")
        if os.path.exists(temp_pdf):
            basename = os.path.splitext(os.path.basename(file_path))[0]
            # 파일명 정리 (공백 → _)
            clean_name = re.sub(r'\s+', '_', basename)
            final_pdf = os.path.join(output_dir, f"{clean_name}.pdf")
            shutil.move(temp_pdf, final_pdf)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return final_pdf
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print(f"  [WARN] PDF 변환 실패: {e}")
    return None

def register_rule(conn, pubno, name, cate_seq, estab_date, docx_filename, wzruleid):
    """wz_rule에 규정 등록"""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO wz_rule (
            wzlevel, wzruleid, wzname, wzedittype, wzpubno,
            wzestabdate, wzlastrevdate, wzmgrdptnm, wzmgrdptorgcd,
            wzreldptnm, wzreldptorgcd, wzcateseq, wzexecdate,
            wzlkndname, wzfiledocx, wzfilepdf, wzfilejson,
            content_text, wznewflag, wzcreatedby, wzmodifiedby
        ) VALUES (
            1, %s, %s, '규정', %s,
            %s, %s, '', '',
            '', '', %s, %s,
            '', %s, '', '',
            '', '현행', 'bulk_register', 'bulk_register'
        ) RETURNING wzruleseq
    """, (wzruleid, name, pubno, estab_date, estab_date, cate_seq, estab_date, docx_filename))
    new_seq = cur.fetchone()[0]
    return new_seq

def register_appendix(conn, rule_seq, pubno, appendix_name, appendix_no, pdf_filename, pdf_size):
    """wz_appendix에 별표/서식 등록"""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO wz_appendix (
            wzruleseq, wzappendixname, wzappendixno,
            wzfilepath, wzfiletype, wzcreatedby, wzmodifiedby
        ) VALUES (%s, %s, %s, %s, %s, 'bulk_register', 'bulk_register')
    """, (rule_seq, appendix_name, appendix_no, pdf_filename, 'pdf'))

def parse_appendix_info(filename):
    """별표/서식 파일명에서 유형과 번호 추출"""
    basename = os.path.splitext(filename)[0]
    # 패턴: "(N-M) 별표 제X호_제목" 또는 "(N-M) 서식 제X호_제목"
    m = re.search(r'(별표|별첨|서식|붙임|첨부)\s*제?\s*(\d+)\s*호', basename)
    if m:
        type_name = m.group(1)
        number = m.group(2)
        # 제목 추출
        title_match = re.search(r'호[_\s]*(.+)$', basename)
        title = title_match.group(1).strip() if title_match else ""
        return f"{type_name} 제{number}호", int(number), title

    # 첨부 제N호 패턴
    m = re.search(r'(첨부|샘플)\s*제?\s*(\d+)\s*호', basename)
    if m:
        return f"{m.group(1)} 제{m.group(2)}호", int(m.group(2)), ""

    # 번호 없는 경우
    for kw in ['별표', '별첨', '서식', '붙임', '첨부', '샘플']:
        if kw in basename:
            return kw, 0, basename
    return "부록", 0, basename

def main():
    print("=" * 60)
    print("KB신용정보 전체 규정 일괄 등록")
    print("=" * 60)

    # 기존 등록 확인
    existing = get_existing_rules()
    print(f"\n현재 등록된 규정: {len(existing)}개")
    for p, info in sorted(existing.items()):
        print(f"  {p}: {info['name']} (seq={info['seq']})")

    # extracted 폴더 스캔
    folders = sorted([d for d in os.listdir(EXTRACTED_DIR)
                      if os.path.isdir(os.path.join(EXTRACTED_DIR, d)) and d.startswith('(')])
    print(f"\n스캔된 규정 폴더: {len(folders)}개")

    conn = get_db_connection()
    conn.autocommit = True

    # 현재 최대 wzruleid
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(wzruleid), 10004) FROM wz_rule")
    next_rule_id = cur.fetchone()[0] + 1

    registered = 0
    skipped = 0
    appendix_count = 0
    errors = []

    for folder_name in folders:
        folder_path = os.path.join(EXTRACTED_DIR, folder_name)
        pubno, reg_name = parse_folder_name(folder_name)

        if not pubno:
            print(f"\n[SKIP] 파싱 불가: {folder_name}")
            continue

        # 이미 등록된 경우 스킵
        if pubno in existing:
            print(f"\n[SKIP] 이미 등록: {pubno} {reg_name}")
            skipped += 1
            rule_seq = existing[pubno]['seq']
        else:
            print(f"\n[NEW] {pubno} {reg_name}")

            # 본문 파일 찾기
            main_file = find_main_docx(folder_path, pubno)
            if not main_file:
                print(f"  [ERROR] 본문 파일 없음")
                errors.append(f"{pubno}: 본문 파일 없음")
                continue

            main_basename = os.path.basename(main_file)
            print(f"  본문: {main_basename}")

            # doc → docx 변환
            if main_file.lower().endswith('.doc'):
                print(f"  doc→docx 변환 중...")
                converted = convert_doc_to_docx(main_file)
                if converted:
                    main_file = converted
                    main_basename = os.path.basename(converted)
                    print(f"  변환 완료: {main_basename}")
                else:
                    print(f"  [ERROR] 변환 실패")
                    errors.append(f"{pubno}: doc→docx 변환 실패")
                    continue

            # docx를 applib/docx/에 복사
            dest_docx = os.path.join(DOCX_DIR, main_basename)
            if not os.path.exists(dest_docx):
                shutil.copy2(main_file, dest_docx)
                print(f"  복사: {main_basename} → applib/docx/")

            # 날짜 추출
            estab_date = parse_filename_date(main_basename)

            # 카테고리 결정
            cate_num = pubno.split('-')[0]
            cate_seq = CATE_MAP.get(cate_num, 11)

            # DB 등록
            try:
                rule_seq = register_rule(conn, pubno, reg_name, cate_seq, estab_date, main_basename, next_rule_id)
                print(f"  DB 등록: wzruleseq={rule_seq}, wzruleid={next_rule_id}, cate={cate_seq}")
                next_rule_id += 1
                registered += 1
            except Exception as e:
                print(f"  [ERROR] DB 등록 실패: {e}")
                errors.append(f"{pubno}: DB 등록 실패 - {e}")
                continue

        # 별표/서식 처리
        appendix_files = find_appendix_files(folder_path, pubno)
        if appendix_files:
            print(f"  별표/서식: {len(appendix_files)}개")

            for ap_file in appendix_files:
                ap_basename = os.path.basename(ap_file)
                ap_type, ap_no, ap_title = parse_appendix_info(ap_basename)

                # PDF 변환
                pdf_dir = os.path.join(STATIC_PDF_DIR)
                pdf_result = convert_to_pdf(ap_file, pdf_dir)

                if pdf_result:
                    pdf_filename = os.path.basename(pdf_result)
                    pdf_size = os.path.getsize(pdf_result)

                    # 이름 생성
                    ap_name = f"{ap_type}"
                    if ap_title:
                        ap_name += f" {ap_title}"

                    try:
                        register_appendix(conn, rule_seq, pubno, ap_name, ap_no, pdf_filename, pdf_size)
                        appendix_count += 1
                        print(f"    ✓ {ap_type}: {pdf_filename}")
                    except Exception as e:
                        print(f"    [ERROR] 부록 등록 실패: {e}")
                else:
                    print(f"    [WARN] PDF 변환 실패: {ap_basename}")

    print(f"\n{'=' * 60}")
    print(f"완료!")
    print(f"  신규 등록: {registered}개")
    print(f"  기존 스킵: {skipped}개")
    print(f"  별표/서식: {appendix_count}개")
    print(f"  오류: {len(errors)}개")
    if errors:
        print(f"\n오류 목록:")
        for e in errors:
            print(f"  - {e}")
    conn.close()

if __name__ == "__main__":
    main()
