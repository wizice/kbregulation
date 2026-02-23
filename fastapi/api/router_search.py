"""
상세검색 라우터
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from api.auth_middleware import get_current_user, login_required
import logging

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)

# 템플릿 설정
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader("templates"))
templates = Jinja2Templates(env=env)

@router.get("/advanced", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def advanced_search(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """상세검색 페이지"""
    return templates.TemplateResponse(
        "search/advanced.html",
        {
            "request": request,
            "user": user,
            "page_title": "상세검색"
        }
    )

@router.get("/engine", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def search_engine_management(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """검색 엔진 관리 페이지"""
    return templates.TemplateResponse(
        "search/engine_management.html",
        {
            "request": request,
            "user": user,
            "page_title": "검색 엔진 관리"
        }
    )