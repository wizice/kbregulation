"""XLSX → PDF 변환 유틸리티 (openpyxl + reportlab)"""

import os
import glob
from pathlib import Path


def xlsx_to_pdf(xlsx_path, output_pdf_path):
    """
    XLSX 파일을 PDF로 변환

    Args:
        xlsx_path: 입력 XLSX 파일 경로
        output_pdf_path: 출력 PDF 파일 경로
    """
    import openpyxl
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # 한글 폰트 등록
    font_name = _register_korean_font(pdfmetrics, TTFont)

    wb = openpyxl.load_workbook(str(xlsx_path), data_only=True)
    ws = wb.active

    # 셀 데이터 추출
    data = []
    for row in ws.iter_rows(values_only=True):
        row_data = [str(cell) if cell is not None else "" for cell in row]
        if any(cell.strip() for cell in row_data):
            data.append(row_data)

    if not data:
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
        'CellStyle', parent=styles['Normal'],
        fontName=font_name, fontSize=8, leading=10, wordWrap='CJK',
    )
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Normal'],
        fontName=font_name, fontSize=11, leading=14, spaceAfter=6*mm,
    )

    elements = []
    sheet_title = ws.title or Path(xlsx_path).stem
    elements.append(Paragraph(sheet_title, title_style))
    elements.append(Spacer(1, 3*mm))

    table_data = [[Paragraph(cell, cell_style) for cell in row] for row in data]

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


def _register_korean_font(pdfmetrics, TTFont):
    """한글 폰트 등록, 폰트명 반환"""
    font_paths = [
        "/usr/share/fonts/google-noto-sans-cjk-ttc/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/google-noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("NotoSansCJK", fp, subfontIndex=0))
                return "NotoSansCJK"
            except Exception:
                continue

    noto_fonts = glob.glob("/usr/share/fonts/**/NotoSans*CJK*.tt[cf]", recursive=True)
    if noto_fonts:
        try:
            pdfmetrics.registerFont(TTFont("NotoSansCJK", noto_fonts[0], subfontIndex=0))
            return "NotoSansCJK"
        except Exception:
            pass

    return "Helvetica"
