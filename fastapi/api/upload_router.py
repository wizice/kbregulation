# -*- coding: utf-8 -*-
"""
    upload_router
    ~~~~~~~~~~

    파일 업로드 관련 API 라우터
    Cloudflare R2 업로드 기능 추가

    :copyright: (c) 2024 by wizice.
    :license: MIT, see LICENSE for more details.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query, Depends
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from typing import List, Optional
from datetime import datetime
import os
import tempfile
from pathlib import Path

# 기존 패턴에 맞춘 import
from api.service_cloudflare_r2_v1 import get_cloudflare_r2_table, CloudflareR2Table
from settings import settings


# API Router 생성 (기존 패턴)
router = APIRouter(
    prefix="/api/v1/upload",
    tags=["upload_v1"],
    responses={404: {"description": "Not found"}},
)


# 의존성: CloudflareR2Table 인스턴스 생성
def get_r2_service():
    """CloudflareR2Table 인스턴스를 생성하는 의존성"""
    return get_cloudflare_r2_table()


@router.get("/hello")
@router.post("/hello")
async def hello():
    """연결 확인"""
    return {
        "success": True,
        "service": "upload_router",
        "version": "v1"
    }


    

    
