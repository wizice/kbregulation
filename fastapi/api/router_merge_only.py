#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from api.auth_middleware import get_current_user
from api.service_merge_only import merge_only_service
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/merge",
    tags=["merge"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/1.1.1")
async def merge_111_regulation(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    1.1.1 정확한 환자 확인 규정 병합
    - 업로드/파싱 없이 기존 JSON 파일만 병합
    - docx_json과 txt_json 폴더에서 최신 파일 자동 선택
    """

    logger.info(f"1.1.1 병합 요청 - 사용자: {current_user.get('username')}")

    try:
        result = await merge_only_service.merge_regulation_111()
        logger.info(f"병합 성공: {result.get('output_file')}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"병합 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/1.1.1/files")
async def get_111_files(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    1.1.1 규정 관련 파일 목록 조회
    """

    try:
        files = await merge_only_service.get_available_111_files()
        return {
            "status": "success",
            "files": files,
            "message": "사용 가능한 1.1.1 파일 목록"
        }

    except Exception as e:
        logger.error(f"파일 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))