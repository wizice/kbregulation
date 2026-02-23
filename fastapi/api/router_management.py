"""
부서/분류 관리 라우터
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from api.auth_middleware import get_current_user, login_required
import logging

router = APIRouter(prefix="/management", tags=["management"])
logger = logging.getLogger(__name__)

# 템플릿 설정
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader("templates"))
templates = Jinja2Templates(env=env)

@router.get("/departments", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def department_management(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """부서관리 페이지"""
    return templates.TemplateResponse(
        "management/departments.html",
        {
            "request": request,
            "user": user,
            "page_title": "부서관리"
        }
    )

@router.get("/classifications", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def classification_management(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """분류관리 페이지"""
    return templates.TemplateResponse(
        "management/classifications.html",
        {
            "request": request,
            "user": user,
            "page_title": "분류관리"
        }
    )