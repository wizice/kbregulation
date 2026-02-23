# -*- coding: utf-8 -*-
"""
    pdf_extractor.py
    ~~~~~~~~~~~~~~~~

    PDF 파일에서 텍스트를 추출하는 유틸리티

    :copyright: (c) 2025 by wizice.
    :license: MIT LICENSE 2.0
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import re

logger = logging.getLogger(__name__)

class PDFTextExtractor:
    """PDF 텍스트 추출 클래스"""

    def __init__(self):
        self.supported_libraries = []
        self._init_libraries()

    def _init_libraries(self):
        """사용 가능한 PDF 라이브러리 확인"""
        # PyMuPDF (fitz) 시도
        try:
            import fitz
            self.supported_libraries.append('pymupdf')
            logger.info("PyMuPDF (fitz) library available")
        except ImportError:
            pass

        # pdfplumber 시도
        try:
            import pdfplumber
            self.supported_libraries.append('pdfplumber')
            logger.info("pdfplumber library available")
        except ImportError:
            pass

        # PyPDF2 시도
        try:
            import PyPDF2
            self.supported_libraries.append('pypdf2')
            logger.info("PyPDF2 library available")
        except ImportError:
            pass

        if not self.supported_libraries:
            logger.warning("No PDF libraries available. Please install: pip install pymupdf")

    def extract_text_from_pdf(self, pdf_path: str, method: str = 'auto') -> str:
        """
        PDF 파일에서 텍스트 추출

        Args:
            pdf_path: PDF 파일 경로
            method: 추출 방법 ('auto', 'pymupdf', 'pdfplumber', 'pypdf2')

        Returns:
            추출된 텍스트
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return ""

        # auto인 경우 사용 가능한 첫 번째 라이브러리 사용
        if method == 'auto':
            if 'pymupdf' in self.supported_libraries:
                method = 'pymupdf'
            elif 'pdfplumber' in self.supported_libraries:
                method = 'pdfplumber'
            elif 'pypdf2' in self.supported_libraries:
                method = 'pypdf2'
            else:
                logger.error("No PDF library available")
                return ""

        try:
            if method == 'pymupdf':
                return self._extract_with_pymupdf(pdf_path)
            elif method == 'pdfplumber':
                return self._extract_with_pdfplumber(pdf_path)
            elif method == 'pypdf2':
                return self._extract_with_pypdf2(pdf_path)
            else:
                logger.error(f"Unknown extraction method: {method}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""

    def _extract_with_pymupdf(self, pdf_path: str) -> str:
        """PyMuPDF (fitz)로 텍스트 추출"""
        import fitz

        text = ""
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF extraction error: {e}")

        return text.strip()

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """pdfplumber로 텍스트 추출"""
        import pdfplumber

        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"pdfplumber extraction error: {e}")

        return text.strip()

    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """PyPDF2로 텍스트 추출"""
        import PyPDF2

        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {e}")

        return text.strip()

    def save_text_to_file(self, text: str, output_path: str) -> bool:
        """
        추출된 텍스트를 파일로 저장

        Args:
            text: 저장할 텍스트
            output_path: 출력 파일 경로

        Returns:
            성공 여부
        """
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)

            logger.info(f"Text saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving text to {output_path}: {e}")
            return False

    def extract_and_save(self, pdf_path: str, output_path: str, method: str = 'auto') -> Dict[str, Any]:
        """
        PDF에서 텍스트 추출 후 파일로 저장

        Args:
            pdf_path: PDF 파일 경로
            output_path: 출력 txt 파일 경로
            method: 추출 방법

        Returns:
            결과 정보 딕셔너리
        """
        result = {
            "success": False,
            "pdf_path": pdf_path,
            "output_path": output_path,
            "text_length": 0,
            "method": method,
            "error": None
        }

        try:
            # 텍스트 추출
            text = self.extract_text_from_pdf(pdf_path, method)
            result["text_length"] = len(text)

            if not text:
                result["error"] = "No text extracted from PDF"
                return result

            # 파일 저장
            if self.save_text_to_file(text, output_path):
                result["success"] = True
            else:
                result["error"] = "Failed to save text file"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error in extract_and_save: {e}")

        return result


# 전역 인스턴스
pdf_extractor = PDFTextExtractor()


def extract_pdf_text(pdf_path: str, output_path: str = None, method: str = 'auto') -> Dict[str, Any]:
    """
    편의 함수: PDF 텍스트 추출

    Args:
        pdf_path: PDF 파일 경로
        output_path: 출력 경로 (None이면 자동 생성)
        method: 추출 방법

    Returns:
        결과 딕셔너리
    """
    if output_path is None:
        # PDF 경로에서 txt 경로 자동 생성
        pdf_file = Path(pdf_path)
        output_path = pdf_file.parent / "pdf_txt" / f"{pdf_file.stem}.txt"

    return pdf_extractor.extract_and_save(pdf_path, str(output_path), method)


if __name__ == '__main__':
    # 테스트
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_file>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    result = extract_pdf_text(pdf_file)

    print(f"Success: {result['success']}")
    print(f"Text length: {result['text_length']}")
    if result['error']:
        print(f"Error: {result['error']}")
