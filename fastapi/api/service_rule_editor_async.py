"""
비동기 PDF/DOCX 처리를 위한 서비스 모듈
"""
import os
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException, BackgroundTasks
import logging
from settings import settings

# 로깅 설정
logger = logging.getLogger(__name__)

# 작업 상태 저장소 (실제로는 Redis 사용 권장)
job_status_store: Dict[str, Dict[str, Any]] = {}


class AsyncDocumentProcessor:
    """비동기 문서 처리 클래스"""

    @staticmethod
    def create_job_id() -> str:
        """작업 ID 생성"""
        return str(uuid.uuid4())

    @staticmethod
    def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        return job_status_store.get(job_id)

    @staticmethod
    def update_job_status(job_id: str, status: str, progress: int = 0,
                         result: Optional[Dict] = None, error: Optional[str] = None):
        """작업 상태 업데이트"""
        job_status_store[job_id] = {
            "status": status,  # pending, processing, completed, failed
            "progress": progress,  # 0-100
            "result": result,
            "error": error,
            "updated_at": datetime.now().isoformat()
        }

    @staticmethod
    async def process_pdf_async(job_id: str, pdf_path: str, rule_id: int):
        """PDF 비동기 처리"""
        try:
            # 시작 상태
            AsyncDocumentProcessor.update_job_status(job_id, "processing", 10)

            # PDF → TXT 변환 (30%)
            await asyncio.sleep(0.1)  # 비동기 I/O 시뮬레이션
            AsyncDocumentProcessor.update_job_status(job_id, "processing", 30,
                                                    result={"stage": "PDF to TXT conversion"})

            # 실제 PDF 처리 로직을 여기에 구현
            from applib.pdf2txt import extract_text_from_pdf
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]

            # TXT 파일 경로
            txt_folder = f"{settings.APPLIB_DIR}/pdf_txt"
            os.makedirs(txt_folder, exist_ok=True)
            txt_filename = f"{base_name}_{timestamp}.txt"
            txt_path = os.path.join(txt_folder, txt_filename)

            # PDF → TXT 변환 (실제 처리)
            extract_text_from_pdf(pdf_path, txt_path)
            AsyncDocumentProcessor.update_job_status(job_id, "processing", 60,
                                                    result={"stage": "TXT to JSON parsing"})

            # TXT → JSON 변환 (60%)
            with open(txt_path, 'r', encoding='utf-8') as f:
                txt_content = f.read()

            from api.mental_health_parser import MentalHealthRegulationParser
            parser = MentalHealthRegulationParser()
            json_data = parser.parse_txt_to_json(txt_content)

            AsyncDocumentProcessor.update_job_status(job_id, "processing", 90,
                                                    result={"stage": "Saving JSON"})

            # JSON 저장
            json_folder = f"{settings.APPLIB_DIR}/txt_json"
            os.makedirs(json_folder, exist_ok=True)
            json_filename = f"{base_name}_{timestamp}.json"
            json_path = os.path.join(json_folder, json_filename)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            # 완료
            AsyncDocumentProcessor.update_job_status(job_id, "completed", 100,
                result={
                    "success": True,
                    "message": "PDF 파일 처리 완료",
                    "files": {
                        "pdf": os.path.basename(pdf_path),
                        "txt": txt_filename,
                        "json": json_filename
                    },
                    "json_path": json_path,
                    "parsed_data": json_data
                })

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            AsyncDocumentProcessor.update_job_status(job_id, "failed", 0,
                                                    error=str(e))

    @staticmethod
    async def process_docx_async(job_id: str, docx_path: str, rule_id: int):
        """DOCX 비동기 처리"""
        try:
            # 시작 상태
            AsyncDocumentProcessor.update_job_status(job_id, "processing", 10)

            # DOCX 처리 로직
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(os.path.basename(docx_path))[0]

            AsyncDocumentProcessor.update_job_status(job_id, "processing", 30,
                                                    result={"stage": "Extracting content from DOCX"})

            # DOCX → JSON 변환
            import sys
            sys.path.insert(0, settings.APPLIB_DIR)

            from utils.sequential_numbers import extract_numbers_from_docx, convert_to_sections_format
            from utils.docx_parser import extract_metadata

            # 번호 추출
            extract_results = extract_numbers_from_docx(docx_path)
            AsyncDocumentProcessor.update_job_status(job_id, "processing", 60,
                                                    result={"stage": "Parsing document structure"})

            # 메타데이터 추출
            metadata = extract_metadata(docx_path)

            # sections 형식으로 변환
            sections = convert_to_sections_format(extract_results)

            AsyncDocumentProcessor.update_job_status(job_id, "processing", 80,
                                                    result={"stage": "Generating JSON"})

            # JSON 데이터 구성
            json_data = {
                "문서정보": metadata,
                "조문내용": sections
            }

            # JSON 저장
            json_folder = f"{settings.APPLIB_DIR}/docx_json"
            os.makedirs(json_folder, exist_ok=True)
            json_filename = f"{base_name}_{timestamp}.json"
            json_path = os.path.join(json_folder, json_filename)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            # 완료
            AsyncDocumentProcessor.update_job_status(job_id, "completed", 100,
                result={
                    "success": True,
                    "message": "DOCX 파일 처리 완료",
                    "files": {
                        "docx": os.path.basename(docx_path),
                        "json": json_filename
                    },
                    "json_path": json_path,
                    "parsed_data": json_data
                })

        except Exception as e:
            logger.error(f"Error processing DOCX: {e}")
            AsyncDocumentProcessor.update_job_status(job_id, "failed", 0,
                                                    error=str(e))


# FastAPI 라우터 함수들
async def upload_and_parse_pdf_async(
    pdf_file_content: bytes,
    pdf_filename: str,
    rule_id: int,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """PDF 파일 비동기 업로드 및 파싱"""

    # 작업 ID 생성
    job_id = AsyncDocumentProcessor.create_job_id()

    # PDF 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(pdf_filename)[0]
    pdf_folder = settings.PDF_DIR
    os.makedirs(pdf_folder, exist_ok=True)
    pdf_filename_new = f"{base_name}_{timestamp}.pdf"
    pdf_path = os.path.join(pdf_folder, pdf_filename_new)

    with open(pdf_path, 'wb') as f:
        f.write(pdf_file_content)

    # 초기 상태 설정
    AsyncDocumentProcessor.update_job_status(job_id, "pending", 0)

    # 백그라운드 작업 추가
    background_tasks.add_task(
        AsyncDocumentProcessor.process_pdf_async,
        job_id, pdf_path, rule_id
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "PDF 처리가 시작되었습니다. job_id로 진행 상태를 확인하세요."
    }


async def upload_and_parse_docx_async(
    docx_file_content: bytes,
    docx_filename: str,
    rule_id: int,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """DOCX 파일 비동기 업로드 및 파싱"""

    # 작업 ID 생성
    job_id = AsyncDocumentProcessor.create_job_id()

    # DOCX 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(docx_filename)[0]
    docx_folder = settings.DOCX_DIR
    os.makedirs(docx_folder, exist_ok=True)
    docx_filename_new = f"{base_name}_{timestamp}.docx"
    docx_path = os.path.join(docx_folder, docx_filename_new)

    with open(docx_path, 'wb') as f:
        f.write(docx_file_content)

    # 초기 상태 설정
    AsyncDocumentProcessor.update_job_status(job_id, "pending", 0)

    # 백그라운드 작업 추가
    background_tasks.add_task(
        AsyncDocumentProcessor.process_docx_async,
        job_id, docx_path, rule_id
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "DOCX 처리가 시작되었습니다. job_id로 진행 상태를 확인하세요."
    }


async def get_job_status(job_id: str) -> Dict[str, Any]:
    """작업 상태 조회"""
    status = AsyncDocumentProcessor.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return status