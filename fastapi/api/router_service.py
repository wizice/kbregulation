"""
서비스 페이지 라우터
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from api.auth_middleware import get_current_user, login_required
import logging

router = APIRouter(prefix="/service", tags=["service"])
logger = logging.getLogger(__name__)

# 템플릿 설정
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader("templates"))
templates = Jinja2Templates(env=env)

@router.get("/dashboard", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def service_dashboard(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """서비스 대시보드 페이지"""
    return templates.TemplateResponse(
        "service/dashboard.html",
        {
            "request": request,
            "user": user,
            "page_title": "서비스 대시보드"
        }
    )

@router.get("/settings", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def service_settings(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """서비스 설정 페이지"""
    return templates.TemplateResponse(
        "service/settings.html",
        {
            "request": request,
            "user": user,
            "page_title": "서비스 설정"
        }
    )