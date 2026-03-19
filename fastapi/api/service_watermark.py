# -*- coding: utf-8 -*-
"""
워터마크 PDF 생성 API

PDF 다운로드 시 사용자 정보 워터마크를 추가하여 반환합니다.
생성된 PDF는 저장되지 않고 스트리밍으로 반환됩니다.

:copyright: (c) 2025 by wizice.
:license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from pathlib import Path
from io import BytesIO
from datetime import datetime
import os
import logging

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color

from settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/watermark",
    tags=["watermark"]
)

# 한글 폰트 등록
FONT_REGISTERED = False

def register_korean_font():
    """한글 폰트 등록 (KB금융체 우선)"""
    global FONT_REGISTERED
    if FONT_REGISTERED:
        return True

    import pathlib
    home = str(pathlib.Path.home())

    # KB금융체 우선, 기존 폰트 fallback
    font_paths = [
        f"{home}/.local/share/fonts/kb-finance/KBfgTextM.ttf",
        f"{home}/.local/share/fonts/kb-finance/KBfgTextB.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/malgun/malgun.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('KoreanFont', font_path))
                FONT_REGISTERED = True
                logger.info(f"[Watermark] 한글 폰트 등록 완료: {font_path}")
                return True
            except Exception as e:
                logger.warning(f"[Watermark] 폰트 등록 실패 ({font_path}): {e}")
                continue

    logger.warning("[Watermark] 한글 폰트를 찾을 수 없음, 기본 폰트 사용")
    return False


def create_watermark_pdf(page_width: float, page_height: float,
                         user_name: str, department: str, timestamp: str) -> BytesIO:
    """
    워터마크 PDF 페이지 생성

    대각선 반복 패턴으로 워터마크를 생성합니다.
    """
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # 한글 폰트 등록 시도
    has_korean_font = register_korean_font()
    font_name = 'KoreanFont' if has_korean_font else 'Helvetica'

    # 워터마크 텍스트 구성
    lines = [user_name]
    if department:
        lines.append(department)
    lines.append(timestamp)
    watermark_text = '\n'.join(lines)

    # 워터마크 스타일 설정
    c.setFont(font_name, 10)
    c.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.15))  # 연한 회색, 15% 투명도

    # 대각선 패턴으로 워터마크 배치
    c.saveState()
    c.translate(page_width / 2, page_height / 2)
    c.rotate(35)  # 35도 회전

    # 패턴 간격
    x_spacing = 200
    y_spacing = 100

    # 패턴 범위 계산 (회전 고려)
    max_dim = max(page_width, page_height) * 1.5

    for y in range(int(-max_dim), int(max_dim), y_spacing):
        for x in range(int(-max_dim), int(max_dim), x_spacing):
            c.saveState()
            c.translate(x, y)

            # 여러 줄 텍스트 그리기
            text_obj = c.beginText(0, 0)
            text_obj.setFont(font_name, 10)
            for i, line in enumerate(lines):
                text_obj.setTextOrigin(0, -i * 14)  # 줄 간격 14pt
                text_obj.textLine(line)
            c.drawText(text_obj)

            c.restoreState()

    c.restoreState()
    c.save()

    packet.seek(0)
    return packet


def add_watermark_to_pdf(input_pdf_path: str, user_name: str,
                         department: str, timestamp: str) -> BytesIO:
    """
    PDF 파일에 워터마크 추가

    원본 PDF의 각 페이지에 워터마크를 오버레이합니다.
    """
    try:
        # 원본 PDF 읽기
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()

        for page_num, page in enumerate(reader.pages):
            # 페이지 크기 가져오기
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            # 워터마크 PDF 생성
            watermark_pdf = create_watermark_pdf(
                page_width, page_height,
                user_name, department, timestamp
            )

            # 워터마크 페이지 읽기
            watermark_reader = PdfReader(watermark_pdf)
            watermark_page = watermark_reader.pages[0]

            # 원본 페이지에 워터마크 병합
            page.merge_page(watermark_page)
            writer.add_page(page)

        # 결과 PDF를 메모리에 저장
        output = BytesIO()
        writer.write(output)
        output.seek(0)

        logger.info(f"[Watermark] PDF 워터마크 추가 완료: {len(reader.pages)}페이지")
        return output

    except Exception as e:
        logger.error(f"[Watermark] PDF 워터마크 추가 실패: {e}")
        raise


@router.get("/download/{file_path:path}")
async def download_with_watermark(
    file_path: str,
    request: Request,
    user_name: str = Query(default="사용자", description="사용자명"),
    department: str = Query(default="", description="부서명"),
):
    """
    워터마크가 포함된 PDF 다운로드

    원본 PDF에 사용자 정보 워터마크를 추가하여 반환합니다.
    생성된 PDF는 저장되지 않고 스트리밍으로 반환됩니다.
    """
    try:
        # 파일 경로 검증 및 구성
        # 보안: 상위 디렉토리 접근 방지
        if '..' in file_path or file_path.startswith('/'):
            raise HTTPException(status_code=400, detail="잘못된 파일 경로입니다.")

        # PDF 디렉토리에서 파일 찾기
        pdf_dirs = [
            Path(settings.WWW_STATIC_PDF_DIR),
            Path(settings.WWW_STATIC_PDF_DIR) / "print",
            Path(__file__).parent.parent.parent / "www" / "static" / "pdf",
        ]

        pdf_file_path = None
        for pdf_dir in pdf_dirs:
            candidate = pdf_dir / file_path
            if candidate.exists():
                pdf_file_path = candidate
                break

        if not pdf_file_path or not pdf_file_path.exists():
            logger.warning(f"[Watermark] PDF 파일을 찾을 수 없음: {file_path}")
            raise HTTPException(status_code=404, detail="PDF 파일을 찾을 수 없습니다.")

        # 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 워터마크 추가
        watermarked_pdf = add_watermark_to_pdf(
            str(pdf_file_path),
            user_name,
            department,
            timestamp
        )

        # 파일명 추출
        from urllib.parse import quote
        original_filename = pdf_file_path.name
        encoded_filename = quote(original_filename)

        # 다운로드 이력 기록
        try:
            from . import query_download_logs
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent', '')
            referer = request.headers.get('referer', '')

            query_download_logs.insert_download_log(
                rule_id=0,
                rule_name=original_filename.replace('.pdf', ''),
                rule_pubno='',
                file_type='watermark_pdf',
                file_name=original_filename,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                session_id='',
                user_id=user_name
            )
            logger.info(f"[Watermark] 다운로드 이력 기록: {original_filename}")
        except Exception as log_error:
            logger.warning(f"[Watermark] 다운로드 이력 기록 실패: {log_error}")

        # 스트리밍 응답 반환
        return StreamingResponse(
            watermarked_pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Watermark] 워터마크 PDF 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"워터마크 PDF 생성 실패: {str(e)}")


@router.post("/download")
async def download_with_watermark_post(
    request: Request,
):
    """
    POST 방식 워터마크 PDF 다운로드

    JSON body로 파일 경로와 사용자 정보를 받습니다.
    """
    try:
        body = await request.json()
        file_path = body.get('file_path', '')
        user_name = body.get('user_name', '사용자')
        department = body.get('department', '')

        if not file_path:
            raise HTTPException(status_code=400, detail="file_path가 필요합니다.")

        # 보안: 상위 디렉토리 접근 방지
        if '..' in file_path:
            raise HTTPException(status_code=400, detail="잘못된 파일 경로입니다.")

        # file_path에서 실제 파일명 추출
        # /static/pdf/xxx.pdf 형식 또는 xxx.pdf 형식 모두 처리
        if file_path.startswith('/static/pdf/'):
            file_name = file_path.replace('/static/pdf/', '')
        elif file_path.startswith('static/pdf/'):
            file_name = file_path.replace('static/pdf/', '')
        else:
            file_name = file_path

        # PDF 디렉토리에서 파일 찾기
        pdf_dirs = [
            Path(settings.WWW_STATIC_PDF_DIR),
            Path(settings.WWW_STATIC_PDF_DIR) / "print",
            Path(__file__).parent.parent.parent / "www" / "static" / "pdf",
        ]

        pdf_file_path = None
        for pdf_dir in pdf_dirs:
            candidate = pdf_dir / file_name
            if candidate.exists():
                pdf_file_path = candidate
                break

        if not pdf_file_path or not pdf_file_path.exists():
            logger.warning(f"[Watermark] PDF 파일을 찾을 수 없음: {file_name}")
            raise HTTPException(status_code=404, detail="PDF 파일을 찾을 수 없습니다.")

        # 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 워터마크 추가
        watermarked_pdf = add_watermark_to_pdf(
            str(pdf_file_path),
            user_name,
            department,
            timestamp
        )

        # 파일명 추출
        from urllib.parse import quote
        original_filename = pdf_file_path.name
        encoded_filename = quote(original_filename)

        # 다운로드 이력 기록
        try:
            from . import query_download_logs
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent', '')
            referer = request.headers.get('referer', '')

            query_download_logs.insert_download_log(
                rule_id=0,
                rule_name=original_filename.replace('.pdf', ''),
                rule_pubno='',
                file_type='watermark_pdf',
                file_name=original_filename,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                session_id='',
                user_id=user_name
            )
        except Exception as log_error:
            logger.warning(f"[Watermark] 다운로드 이력 기록 실패: {log_error}")

        # 스트리밍 응답 반환
        return StreamingResponse(
            watermarked_pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Watermark] 워터마크 PDF 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"워터마크 PDF 생성 실패: {str(e)}")
