#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException
from applib.pdf2docx import PDFConverter
from applib.docx_to_json_processor import DocxProcessor
from applib.merge_json import JSONMerger
from app_logger import get_logger

logger = get_logger(__name__)


class FileUploadService:
    """파일 업로드 및 병합 서비스"""

    def __init__(self):
        self.upload_base = Path("uploads")
        self.temp_dir = Path("temp_processing")
        self.json_output = Path("applib/merge_json")

        # 디렉토리 생성
        self.upload_base.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.json_output.mkdir(exist_ok=True)

    async def process_file_upload(
        self,
        regulation_id: str,
        pdf_file: Optional[UploadFile] = None,
        docx_file: Optional[UploadFile] = None
    ) -> Dict[str, Any]:
        """
        1.1.1 파일에 대한 PDF/DOCX 업로드 및 병합 처리
        """

        if not pdf_file and not docx_file:
            raise HTTPException(status_code=400, detail="최소 하나의 파일이 필요합니다")

        # 임시 작업 디렉토리 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = self.temp_dir / f"{regulation_id}_{timestamp}"
        work_dir.mkdir(exist_ok=True)

        try:
            pdf_json_path = None
            docx_json_path = None

            # PDF 처리
            if pdf_file:
                pdf_json_path = await self._process_pdf(pdf_file, work_dir, regulation_id)
                logger.info(f"PDF 처리 완료: {pdf_json_path}")

            # DOCX 처리
            if docx_file:
                docx_json_path = await self._process_docx(docx_file, work_dir, regulation_id)
                logger.info(f"DOCX 처리 완료: {docx_json_path}")

            # JSON 병합
            merged_content = await self._merge_jsons(
                pdf_json_path,
                docx_json_path,
                regulation_id,
                timestamp
            )

            return {
                "success": True,
                "regulation_id": regulation_id,
                "timestamp": timestamp,
                "pdf_processed": pdf_json_path is not None,
                "docx_processed": docx_json_path is not None,
                "merged_content": merged_content,
                "message": "파일 업로드 및 병합 완료"
            }

        except Exception as e:
            logger.error(f"파일 처리 중 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # 임시 파일 정리 (옵션)
            # shutil.rmtree(work_dir, ignore_errors=True)
            pass

    async def _process_pdf(self, pdf_file: UploadFile, work_dir: Path, regulation_id: str) -> str:
        """PDF 파일을 처리하고 JSON으로 변환"""

        # PDF 파일 저장
        pdf_path = work_dir / pdf_file.filename
        with open(pdf_path, "wb") as f:
            content = await pdf_file.read()
            f.write(content)

        # PDF -> DOCX 변환
        converter = PDFConverter()
        docx_path = work_dir / f"{regulation_id}.docx"
        converter.convert(str(pdf_path), str(docx_path))

        # DOCX -> JSON 변환
        processor = DocxProcessor()
        json_path = work_dir / f"{regulation_id}_pdf.json"

        # DOCX 파일 처리
        processor.process_docx(str(docx_path))

        # JSON 저장
        json_data = processor.to_dict()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        return str(json_path)

    async def _process_docx(self, docx_file: UploadFile, work_dir: Path, regulation_id: str) -> str:
        """DOCX 파일을 처리하고 JSON으로 변환"""

        # DOCX 파일 저장
        docx_path = work_dir / docx_file.filename
        with open(docx_path, "wb") as f:
            content = await docx_file.read()
            f.write(content)

        # DOCX -> JSON 변환
        processor = DocxProcessor()
        json_path = work_dir / f"{regulation_id}_docx.json"

        # DOCX 파일 처리
        processor.process_docx(str(docx_path))

        # JSON 저장
        json_data = processor.to_dict()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        return str(json_path)

    async def _merge_jsons(
        self,
        pdf_json_path: Optional[str],
        docx_json_path: Optional[str],
        regulation_id: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """PDF와 DOCX에서 생성된 JSON 파일 병합"""

        if not pdf_json_path and not docx_json_path:
            return {}

        # JSONMerger 인스턴스 생성
        merger = JSONMerger(
            pdf_json_path=pdf_json_path,
            docx_json_path=docx_json_path
        )

        # JSON 파일 로드
        merger.load_json_files()

        # 병합
        merged_data = merger.merge_json()

        # 병합 결과 저장
        if merged_data:
            output_path = self.json_output / f"merged_{regulation_id}_{timestamp}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)

            logger.info(f"병합 완료: {output_path}")

        return merged_data or {}


# 서비스 인스턴스 생성
file_upload_service = FileUploadService()