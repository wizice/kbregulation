#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from api.auth_middleware import get_current_user
from api.service_file_upload import file_upload_service
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/file-upload",
    tags=["file-upload"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/process/1.1.1")
async def upload_and_process_111_files(
    pdf_file: Optional[UploadFile] = File(None),
    docx_file: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    1.1.1 정확한 환자 확인 파일의 PDF/DOCX 업로드 및 병합
    """

    logger.info(f"파일 업로드 요청 - 사용자: {current_user.get('username')}")

    try:
        # 파일 검증
        if pdf_file:
            if not pdf_file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="PDF 파일만 허용됩니다")

        if docx_file:
            if not docx_file.filename.endswith(('.docx', '.doc')):
                raise HTTPException(status_code=400, detail="DOCX 파일만 허용됩니다")

        # 서비스 호출
        result = await file_upload_service.process_file_upload(
            regulation_id="1.1.1_정확한_환자_확인",
            pdf_file=pdf_file,
            docx_file=docx_file
        )

        logger.info(f"파일 처리 성공: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/1.1.1")
async def test_111_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    1.1.1 파일 업로드 테스트 엔드포인트
    """
    return {
        "status": "ready",
        "regulation_id": "1.1.1_정확한_환자_확인",
        "user": current_user.get("username"),
        "message": "파일 업로드 준비 완료"
    }