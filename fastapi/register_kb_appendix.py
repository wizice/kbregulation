#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KB신용정보 별표/별첨/서식 일괄 변환 및 등록 스크립트

1. applib/docx/ 에서 "(N-M) 별표/별첨/서식 제X호_*.docx|xlsx" 패턴 파일 검색
2. DOCX → PDF: libreoffice --headless --convert-to pdf
3. XLSX → PDF: openpyxl + reportlab
4. PDF를 www/static/pdf/ 에 정규화된 파일명으로 저장
5. wz_appendix 테이블에 INSERT
6. summary_kbregulation.json 업데이트
7. 규정별 JSON 파일 업데이트
"""

import os
import sys
import re
import json
import subprocess
import shutil
import tempfile
from pathlib import Path

# 프로젝트 경로
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'applib'))

from settings import settings

# 디렉토리 설정
DOCX_DIR = Path(settings.APPLIB_DIR) / "docx"
WWW_PDF_DIR = Path(settings.WWW_STATIC_PDF_DIR)
WWW_FILE_DIR = Path(settings.WWW_STATIC_FILE_DIR)
SUMMARY_JSON = WWW_FILE_DIR / "summary_kbregulation.json"

# 대상 규정 매핑: wzpubno → (wzruleseq, wzruleid, wzname)
REGULATION_MAP = {
    "5-5": (356, 10001, "운영리스크관리지침"),
    "6-8": (350, 9997, "여비규정"),
    "7-2": (358, 10003, "문서관리규정"),
    "7-6": (359, 10004, "열쇠관리지침"),
}

# 파일명 패턴: (N-M) 별표/별첨/서식 제X호_제목.docx|xlsx
FILENAME_PATTERN = re.compile(
    r'^\((\d+-\d+)\)\s*(별표|별첨|서식)\s*제(\d+)호[_\s]*(.*)\.(docx|xlsx)$',
    re.IGNORECASE
)


def parse_appendix_filename(filename):
    """
    파일명 파싱

    예: "(6-8) 별표 제1호_국내여비정액표.docx"
    → wzpubno="6-8", type="별표", number="1", title="국내여비정액표", ext="docx"
    """
    m = FILENAME_PATTERN.match(filename)
    if not m:
        return None
    return {
        "wzpubno": m.group(1),
        "type": m.group(2),
        "number": m.group(3),
        "title": m.group(4).strip().rstrip('_'),
        "ext": m.group(5).lower(),
    }


def normalize_pdf_filename(info):
    """
    정규화된 PDF 파일명 생성

    예: 6-8._별표제1호._국내여비정액표.pdf
    """
    title = info["title"].replace(" ", "_")
    if title:
        return f'{info["wzpubno"]}._{info["type"]}제{info["number"]}호._{title}.pdf'
    else:
        return f'{info["wzpubno"]}._{info["type"]}제{info["number"]}호.pdf'


def convert_docx_to_pdf(docx_path, output_dir):
    """DOCX → PDF 변환 (LibreOffice)"""
    # 한글 파일명 문제를 피하기 위해 임시 파일명으로 복사 후 변환
    tmp_docx = output_dir / "input.docx"
    shutil.copy2(str(docx_path), str(tmp_docx))

    cmd = [
        "libreoffice", "--headless", "--convert-to", "pdf",
        "--outdir", str(output_dir),
        str(tmp_docx)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice 변환 실패: {result.stderr}")

    # 변환된 파일 찾기
    pdf_path = output_dir / "input.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"변환된 PDF를 찾을 수 없음: {pdf_path}")
    return pdf_path


def convert_xlsx_to_pdf(xlsx_path, output_pdf_path):
    """XLSX → PDF 변환 (openpyxl + reportlab)"""
    import openpyxl
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # 한글 폰트 등록 (KB금융체 우선)
    import pathlib
    home = str(pathlib.Path.home())
    font_registered = False
    font_name = "Helvetica"

    # KB금융체 TTF 우선 시도
    kb_font_paths = [
        f"{home}/.local/share/fonts/kb-finance/KBfgTextM.ttf",
        f"{home}/.local/share/fonts/kb-finance/KBfgTextB.ttf",
    ]
    for fp in kb_font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("KBFont", fp))
                font_registered = True
                font_name = "KBFont"
                break
            except Exception:
                continue

    # Fallback: NotoSansCJK
    if not font_registered:
        noto_paths = [
            "/usr/share/fonts/google-noto-sans-cjk-ttc/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/google-noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/NotoSansCJK-Regular.ttc",
        ]
        for fp in noto_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("NotoSansCJK", fp, subfontIndex=0))
                    font_registered = True
                    font_name = "NotoSansCJK"
                    break
                except Exception:
                    continue

    if not font_registered:
        import glob
        noto_fonts = glob.glob("/usr/share/fonts/**/NotoSans*CJK*.tt[cf]", recursive=True)
        if noto_fonts:
            try:
                pdfmetrics.registerFont(TTFont("NotoSansCJK", noto_fonts[0], subfontIndex=0))
                font_registered = True
                font_name = "NotoSansCJK"
            except Exception:
                pass

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    # 셀 데이터 추출
    data = []
    for row in ws.iter_rows(values_only=True):
        row_data = [str(cell) if cell is not None else "" for cell in row]
        if any(cell.strip() for cell in row_data):
            data.append(row_data)

    if not data:
        # 빈 시트 → 빈 PDF
        data = [["(빈 시트)"]]

    # 열 수 통일
    max_cols = max(len(row) for row in data)
    for row in data:
        while len(row) < max_cols:
            row.append("")

    # PDF 생성
    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        leading=10,
        wordWrap='CJK',
    )
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        leading=14,
        spaceAfter=6*mm,
    )

    elements = []

    # 시트 이름을 제목으로
    sheet_title = ws.title or xlsx_path.stem
    elements.append(Paragraph(sheet_title, title_style))
    elements.append(Spacer(1, 3*mm))

    # 테이블 데이터를 Paragraph로 변환
    table_data = []
    for row in data:
        table_row = [Paragraph(cell, cell_style) for cell in row]
        table_data.append(table_row)

    # 컬럼 폭 계산
    available_width = A4[0] - 30*mm
    col_width = available_width / max_cols if max_cols > 0 else available_width

    table = Table(table_data, colWidths=[col_width]*max_cols)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    elements.append(table)
    doc.build(elements)
    print(f"  XLSX→PDF 변환 완료: {output_pdf_path.name}")


def get_db_connection():
    """DB 연결"""
    import psycopg2
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )


def insert_appendix(conn, wzruleseq, wzappendixno, wzappendixname, wzfilepath):
    """wz_appendix 테이블에 INSERT (중복 시 UPDATE)"""
    cur = conn.cursor()

    # 기존 레코드 확인
    cur.execute(
        "SELECT wzappendixseq FROM wz_appendix WHERE wzruleseq = %s AND wzappendixno = %s",
        (wzruleseq, wzappendixno)
    )
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE wz_appendix
            SET wzappendixname = %s, wzfiletype = %s, wzfilepath = %s, wzmodifiedby = %s
            WHERE wzappendixseq = %s
        """, (wzappendixname, '.pdf', wzfilepath, 'system', existing[0]))
        print(f"  DB UPDATE: wzappendixseq={existing[0]}")
    else:
        cur.execute("""
            INSERT INTO wz_appendix (wzruleseq, wzappendixno, wzappendixname, wzfiletype, wzcreatedby, wzmodifiedby, wzfilepath)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING wzappendixseq
        """, (wzruleseq, wzappendixno, wzappendixname, '.pdf', 'system', 'system', wzfilepath))
        seq = cur.fetchone()[0]
        print(f"  DB INSERT: wzappendixseq={seq}")

    conn.commit()
    cur.close()


def update_summary_json(regulation_appendix_map):
    """summary_kbregulation.json 업데이트"""
    if not SUMMARY_JSON.exists():
        print(f"  경고: summary JSON 없음: {SUMMARY_JSON}")
        return

    with open(SUMMARY_JSON, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    updated_count = 0

    # summary 구조: {"KB규정": {"1편 ...": {"regulations": [...]}, ...}}
    def search_and_update(data):
        nonlocal updated_count
        if isinstance(data, dict):
            if 'regulations' in data:
                for regulation in data['regulations']:
                    code = regulation.get('code', '')
                    if code in regulation_appendix_map:
                        regulation['appendix'] = regulation_appendix_map[code]
                        updated_count += 1
                        print(f"  Summary 업데이트: {code} → {len(regulation_appendix_map[code])}건")
            else:
                for v in data.values():
                    search_and_update(v)

    search_and_update(summary)

    with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"  Summary JSON: {updated_count}개 규정 업데이트 완료")


def update_rule_json(wzruleid, appendix_names):
    """개별 규정 JSON 파일 업데이트"""
    rule_json = WWW_FILE_DIR / f"{wzruleid}.json"
    if not rule_json.exists():
        print(f"  경고: 규정 JSON 없음: {rule_json}")
        return

    with open(rule_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data['부록'] = appendix_names

    # 조문내용에 (부록) 섹션이 있으면 업데이트
    if '조문내용' in data:
        articles = data['조문내용']
        appendix_section_idx = None
        for i, article in enumerate(articles):
            if article.get('내용') == '(부록)':
                appendix_section_idx = i
                break

        if appendix_section_idx is not None:
            # 기존 부록 하위 항목 제거
            next_section_idx = None
            for i in range(appendix_section_idx + 1, len(articles)):
                if articles[i].get('레벨') == 1:
                    next_section_idx = i
                    break
            if next_section_idx:
                del articles[appendix_section_idx + 1:next_section_idx]
            else:
                del articles[appendix_section_idx + 1:]

            # 새 부록 항목 추가
            base_seq = articles[appendix_section_idx].get('seq', 100)
            for idx, name in enumerate(appendix_names):
                articles.insert(appendix_section_idx + 1 + idx, {
                    "seq": base_seq + 1 + idx,
                    "레벨": 2,
                    "내용": name,
                    "번호": f"{idx + 1}.",
                    "관련이미지": []
                })

    with open(rule_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  규정 JSON 업데이트: {wzruleid}.json ({len(appendix_names)}건)")


def main():
    print("=" * 60)
    print("KB신용정보 별표/별첨/서식 일괄 변환 및 등록")
    print("=" * 60)

    # 출력 디렉토리 확인
    WWW_PDF_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 대상 파일 검색
    print("\n[Step 1] 대상 파일 검색...")
    files_by_regulation = {}  # wzpubno → [(info, filepath), ...]

    for f in sorted(DOCX_DIR.iterdir()):
        if not f.is_file():
            continue
        info = parse_appendix_filename(f.name)
        if info and info["wzpubno"] in REGULATION_MAP:
            pubno = info["wzpubno"]
            if pubno not in files_by_regulation:
                files_by_regulation[pubno] = []
            files_by_regulation[pubno].append((info, f))
            print(f"  발견: {f.name}")

    total_files = sum(len(v) for v in files_by_regulation.values())
    print(f"\n  총 {total_files}개 파일 발견 ({len(files_by_regulation)}개 규정)")

    if total_files == 0:
        print("변환할 파일이 없습니다.")
        return

    # 2. 변환 및 등록
    print("\n[Step 2] 변환 및 등록...")
    conn = get_db_connection()

    # 규정별 부록 이름 수집 (summary/JSON 업데이트용)
    regulation_appendix_map = {}  # wzpubno → [이름, ...]

    try:
        for wzpubno, files in sorted(files_by_regulation.items()):
            wzruleseq, wzruleid, wzname = REGULATION_MAP[wzpubno]
            print(f"\n--- {wzpubno} {wzname} (wzruleseq={wzruleseq}) ---")

            appendix_names = []

            for info, src_path in sorted(files, key=lambda x: int(x[0]["number"])):
                pdf_filename = normalize_pdf_filename(info)
                pdf_dest = WWW_PDF_DIR / pdf_filename
                appendix_type = info["type"]
                appendix_num = info["number"]
                title = info["title"].replace("_", " ")
                if title:
                    appendix_display_name = f'{appendix_type} 제{appendix_num}호 {title}'
                else:
                    appendix_display_name = f'{appendix_type} 제{appendix_num}호'
                wzfilepath = f'www/static/pdf/{pdf_filename}'

                print(f"\n  [{appendix_type} 제{appendix_num}호] {src_path.name}")
                print(f"    → {pdf_filename}")

                try:
                    if info["ext"] == "docx":
                        # DOCX → PDF (LibreOffice)
                        with tempfile.TemporaryDirectory() as tmpdir:
                            tmp_pdf = convert_docx_to_pdf(src_path, Path(tmpdir))
                            shutil.move(str(tmp_pdf), str(pdf_dest))
                        print(f"    DOCX→PDF 변환 완료")
                    elif info["ext"] == "xlsx":
                        # XLSX → PDF (openpyxl + reportlab)
                        convert_xlsx_to_pdf(src_path, pdf_dest)
                    else:
                        print(f"    지원하지 않는 형식: {info['ext']}")
                        continue

                    # DB 등록
                    insert_appendix(conn, wzruleseq, appendix_num, appendix_display_name, wzfilepath)
                    appendix_names.append(appendix_display_name)

                except Exception as e:
                    print(f"    오류: {e}")
                    continue

            regulation_appendix_map[wzpubno] = appendix_names

    finally:
        conn.close()

    # 3. Summary JSON 업데이트
    print("\n[Step 3] Summary JSON 업데이트...")
    update_summary_json(regulation_appendix_map)

    # 4. 개별 규정 JSON 업데이트
    print("\n[Step 4] 규정별 JSON 업데이트...")
    for wzpubno, names in regulation_appendix_map.items():
        _, wzruleid, _ = REGULATION_MAP[wzpubno]
        update_rule_json(wzruleid, names)

    # 5. 결과 요약
    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    total_success = sum(len(v) for v in regulation_appendix_map.values())
    print(f"  변환/등록 성공: {total_success}/{total_files}건")
    for wzpubno, names in sorted(regulation_appendix_map.items()):
        _, _, wzname = REGULATION_MAP[wzpubno]
        print(f"  {wzpubno} {wzname}: {len(names)}건")
        for name in names:
            print(f"    - {name}")

    # 생성된 PDF 파일 목록
    print(f"\nPDF 파일 위치: {WWW_PDF_DIR}")
    for wzpubno in sorted(regulation_appendix_map.keys()):
        for pdf in sorted(WWW_PDF_DIR.glob(f"{wzpubno}._*")):
            print(f"  {pdf.name} ({pdf.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
