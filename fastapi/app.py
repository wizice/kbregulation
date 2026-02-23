"""
FastAPI Application

"""

import os
import sys
import json 
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, FileSystemBytecodeCache

from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# 인증 관련 임포트
from api.auth_middleware import (
    AuthMiddleware,
    get_current_user,
    get_current_active_user,
    get_optional_user,
    require_role,
    login_required
)
from api.auth_router import router as auth_router

# 서비스 라우터 임포트 (기존 파일들)
from api.service_users_v2 import router as users_router
from api.service_user_sessions_v2 import router as sessions_router
from api.service_monitor_v1 import router as monitor_router
from api import service_wz_rule_v1
from api import service_wz_dept_v1
from api import service_search_engine

# 새로 분리된 페이지 라우터
from api import router_regulations
from api import router_merge_only
# Removed unnecessary router imports - all functionality is in router_regulations

# 접속 로그 관련 임포트
from api.access_logger import AccessLoggerMiddleware
from api.service_access_logs_v1 import router as access_logs_router

# Import database
from api.timescale_dbv1 import TimescaleDB

# Configure logging
from settings import settings
from app_logger import setup_logging, get_logger

setup_logging('app.log')
logger = get_logger(__name__)

# Project configuration
PROJECT_CONFIG = {
    "name": "세브란스 세칙편집기",
    "description": "세브란스 세칙편집기",
    "version": "0.1.1",
}

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {PROJECT_CONFIG['name']}...")
    
    # Redis 연결 확인
    try:
        from api.auth_middleware import get_redis_manager
        redis_manager = get_redis_manager()
        logger.info("Redis 연결 정상")
    except Exception as e:
        logger.error(f"Redis 연결 실퍠: {e}")
    
    # Test database connection
    try:
        gDB = TimescaleDB(
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT )
        )
        gDB.connect()
        logger.info("Database 연결 성공 ")
        gDB.close()
    except Exception as e:
        logger.error(f"Database 연결 실퍠: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")

# 캐시 디렉토리 생성 확인
cache_dir = Path("/tmp/jinja_cache")
if not cache_dir.exists():
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(cache_dir, 0o777)  # 읽기/쓰기 권한 부여

# Create FastAPI app with increased file upload limits
app = FastAPI(
    title=PROJECT_CONFIG['name'],
    description=PROJECT_CONFIG['description'],
    version=PROJECT_CONFIG['version'],
    lifespan=lifespan
)
# templates 디렉토리 지정
templates = Jinja2Templates(directory="templates")



# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 접속 로그 미들웨어 (비동기 처리)
app.add_middleware(AccessLoggerMiddleware)

# Static files mounting
app.mount("/static", StaticFiles(directory="static"), name="static")

# WZ_RULE 테이블 API
app.include_router(service_wz_rule_v1.router,
    dependencies=[Depends(get_current_user)]  # admin이 아닌 일반 인증 사용자도 접근 가능
)

# WZ_DEPT 테이블 API
app.include_router(service_wz_dept_v1.router,
    dependencies=[Depends(get_current_user)]  # admin이 아닌 일반 인증 사용자도 접근 가능
)

# 부서별 규정 수 API
from api import service_dept_regulation
app.include_router(service_dept_regulation.router,
    dependencies=[Depends(get_current_user)]
)

# 규정 내용 조회 API
from api import service_regulation_content, service_classification
app.include_router(service_regulation_content.router)
app.include_router(service_classification.router)

# 규정 관리 (현행/연혁)
from api import service_regulation
app.include_router(service_regulation.router,
    dependencies=[Depends(get_current_user)]
)

# 검색 엔진 API (PostgreSQL FTS)
app.include_router(service_search_engine.router,
    dependencies=[Depends(get_current_user)]
)

# Elasticsearch 검색 API (임시 비활성화 - elasticsearch_dsl 모듈 없음)
# from api import router_search_es
# app.include_router(router_search_es.router,
#     dependencies=[Depends(get_current_user)]
# )

# 접속 로그 API (관리자 전용)
app.include_router(access_logs_router)

# 사용자 화면용 공개 검색 API (/api/search)
from api import router_public_search
app.include_router(router_public_search.router)  # 인증 불필요

# Elasticsearch 검색 API (실험용 - /api/search/es)
from api import router_public_search_es
app.include_router(router_public_search_es.router)  # 인증 불필요

# 규정 편집 API
from api import service_rule_editor
app.include_router(service_rule_editor.router,
    dependencies=[Depends(get_current_user)]
)
# 공개 API (인증 불필요)
app.include_router(service_rule_editor.public_router)

# 개선된 규정 편집 API (JSON 구조 보존)
from api import service_rule_editor_enhanced
app.include_router(service_rule_editor_enhanced.router,
    dependencies=[Depends(get_current_user)]
)

# 색인 관리 API
from api import indexing_service
app.include_router(indexing_service.router,
    dependencies=[Depends(get_current_user)]
)

# JSON 파일 뷰어 API
from api import service_json_viewer
app.include_router(service_json_viewer.router,
    dependencies=[Depends(get_current_user)]
)

# JSON 파일 서빙 + 로깅 API (공개 - 사용자 화면에서 사용)
from api.service_json_file_logging import router as json_file_logging_router
app.include_router(json_file_logging_router)

# 새로 분리된 페이지 라우터 등록
app.include_router(router_regulations.router)
# All regulation-related routes are now in router_regulations

# 병합 전용 라우터 등록
app.include_router(router_merge_only.router)

# 부록 파일 다운로드 및 공개 API 라우터 (인증 불필요)
from api.router_appendix_download import router as appendix_download_router
app.include_router(appendix_download_router)

# 부록 파일 업로드 라우터 (인증 필요)
from api.router_appendix import router as appendix_router
app.include_router(appendix_router,
    dependencies=[Depends(get_current_user)]
)

# 비동기 작업 API
from api import async_endpoints
async_endpoints.register_handlers()  # 작업 핸들러 등록
app.include_router(async_endpoints.router,
    prefix="/api/v1/async",
    tags=["async"],
    dependencies=[Depends(get_current_user)]
)

# 공지사항 관리 API
from api.router_notices import router as notices_router
app.include_router(notices_router)

# FAQ 관리 API
from api.router_faqs import router as faqs_router
app.include_router(faqs_router)

# 지원 페이지 관리 API
from api.router_support import router as support_router
app.include_router(support_router)

# 연혁 파일 관리 API
from api.router_history_files import router as history_files_router
app.include_router(history_files_router)

# View Stats API (내규 조회 통계)
from api import service_regulation_view_stats
app.include_router(service_regulation_view_stats.router,
    dependencies=[Depends(get_current_user)]
)

# Download Logs API (다운로드 이력 관리)
from api.service_download_logs import router as download_logs_router
app.include_router(download_logs_router)

# Watermark PDF API (워터마크 PDF 다운로드)
from api.service_watermark import router as watermark_router
app.include_router(watermark_router)

# Approval API (다단계 결재 시스템)
from api.service_approval import router as approval_router
app.include_router(approval_router)

# API Keys API (API 키 관리)
from api.service_api_keys import router as api_keys_router
app.include_router(api_keys_router)

# 규정별 안내사항 API
from api.router_regulation_notices import router as regulation_notices_router
app.include_router(regulation_notices_router)

# 유사어 관리 API
from api.router_synonyms import router as synonyms_router
app.include_router(synonyms_router,
    dependencies=[Depends(get_current_user)]
)

# 공지사항 관리자 페이지
@app.get("/admin/notices", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_notices_page(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """공지사항 관리 페이지"""
    return templates.TemplateResponse(
        "admin_notices.html",
        {"request": request, "user": user}
    )

# FAQ 관리자 페이지
@app.get("/admin/faqs", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_faqs_page(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """FAQ 관리 페이지"""
    return templates.TemplateResponse(
        "admin_faqs.html",
        {"request": request, "user": user}
    )

# 유사어 관리자 페이지
@app.get("/admin/synonyms", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_synonyms_page(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """유사어 관리 페이지"""
    return templates.TemplateResponse(
        "admin_synonyms.html",
        {"request": request, "user": user}
    )

# 접속 로그 대시보드 페이지
@app.get("/admin/access-logs", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def access_logs_dashboard(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """접속 로그 대시보드 페이지 (관리자 전용)"""
    return templates.TemplateResponse(
        "access_logs_dashboard.html",
        {"request": request, "user": user}
    )

# 다운로드 이력 대시보드 페이지
@app.get("/admin/download-logs", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def download_logs_dashboard(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """다운로드 이력 대시보드 페이지 (관리자 전용)"""
    return templates.TemplateResponse(
        "download_logs_dashboard.html",
        {"request": request, "user": user}
    )

# 내규 조회 통계 대시보드 페이지
@app.get("/admin/view-analytics", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def view_analytics_dashboard(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """내규 조회 통계 대시보드 페이지 (관리자 전용)"""
    return templates.TemplateResponse(
        "admin_view_analytics.html",
        {"request": request, "user": user}
    )

# API 키 관리 페이지
@app.get("/admin/api-keys", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_api_keys_page(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """API 키 관리 페이지"""
    return templates.TemplateResponse(
        "admin_api_keys.html",
        {"request": request, "user": user, "g": {"user": user}}
    )

# 기능 관리 대시보드 페이지
@app.get("/admin/features", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_feature_dashboard(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """기능 관리 대시보드 (워터마크, 다운로드 이력, 결재 관리)"""
    return templates.TemplateResponse(
        "admin_feature_dashboard.html",
        {"request": request, "user": user, "g": {"user": user}}
    )

# 지원 페이지 관리자 페이지 (공지사항 관리 통합)
@app.get("/regulations/service", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def regulations_service_page(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """지원 페이지 관리 페이지 (공지사항 포함)"""
    return templates.TemplateResponse(
        "regulations/support_full.html",
        {"request": request, "user": user}
    )

# 하위 호환성을 위한 리다이렉트
@app.get("/admin/support", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_support_redirect(request: Request):
    """이전 URL 호환성 유지"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/regulations/service", status_code=301)

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "project": PROJECT_CONFIG['name'],
        "version": PROJECT_CONFIG['version'],
        "timestamp": datetime.utcnow().isoformat()
    }

# Print PDF 파일 검색 API (인쇄 기능용)
@app.get("/api/v1/pdf/print-file/{reg_code}")
async def find_print_pdf(reg_code: str):
    """
    내규 코드로 print 폴더에서 PDF 파일을 찾습니다.
    reg_code: "1_1_1" 형태의 내규 코드
    """
    import glob

    # 내규 코드를 파일명 prefix로 변환: "1_1_1" → "1.1.1."
    prefix = reg_code.replace("_", ".") + "."

    # www/static/pdf/print 폴더 경로
    print_folder = Path(__file__).parent.parent / "www" / "static" / "pdf" / "print"

    if not print_folder.exists():
        logger.warning(f"[Print PDF] print 폴더가 없습니다: {print_folder}")
        return {"success": False, "error": "print 폴더를 찾을 수 없습니다."}

    # prefix로 시작하는 파일 검색
    pattern = str(print_folder / f"{prefix}*.pdf")
    matching_files = glob.glob(pattern)

    if not matching_files:
        logger.warning(f"[Print PDF] 파일을 찾을 수 없습니다: {prefix}*.pdf")
        return {"success": False, "error": f"내규 코드 {reg_code}에 해당하는 PDF 파일을 찾을 수 없습니다."}

    # 첫 번째 매칭 파일의 파일명만 반환
    filename = os.path.basename(matching_files[0])
    logger.info(f"[Print PDF] 파일 발견: {filename}")

    return {
        "success": True,
        "filename": filename,
        "path": f"/static/pdf/print/{filename}"
    }

# 특정 라우터만 템플릿 새로 로딩
@app.get("/force-reload", response_class=HTMLResponse)
def force_reload(request: Request):
    # 템플릿 캐시 제거
    env.cache.clear()
    # 또는 특정 템플릿만 다시 로드
    # env.get_template("index.html", globals=None) → 강제 재로드
    
    return templates.TemplateResponse("login.html", {"request": request, "g":{ "user":{}}})
# Root endpoint
@app.get("/", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def root(request: Request):
    """홈페이지"""
    return templates.TemplateResponse("login.html", {"request": request, "g":{ "user":{}}})
    return """
    <html>
        <head>
            <title>Welcome to """ + PROJECT_CONFIG['name'] + """</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 50px; }
                .container { max-width: 800px; margin: 0 auto; }
                .nav { background: #333; color: white; padding: 15px; }
                .nav a { color: white; text-decoration: none; margin-right: 20px; }
                .nav a:hover { text-decoration: underline; }
                .content { padding: 20px; }
                .feature { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="nav">
                    <a href="/">Home</a>
                    <a href="/dashboard/login">Login</a>
                    <a href="/register">Register</a>
                    <a href="/docs">API Docs</a>
                    <a href="/redoc">ReDoc</a>
                </div>
                
                <div class="content">
                    <h1>Welcome to WIZICE API</h1>
                    <p>A FastAPI application with Redis session management and PostgreSQL authentication.</p>
                    
                    <div class="feature">
                        <h3>Features:</h3>
                        <ul>
                            <li>JWT-like token authentication with Redis</li>
                            <li>PostgreSQL for user management and audit logs</li>
                            <li>Role-based access control</li>
                            <li>Multi-device session management</li>
                            <li>Automatic session expiration</li>
                        </ul>
                    </div>
                    
                    <div class="feature">
                        <h3>Quick Links:</h3>
                        <ul>
                            <li><a href="/dashboard/login">Login to your account</a></li>
                            <li><a href="/register">Create new account</a></li>
                            <li><a href="/dashboard">Go to Dashboard</a> (requires login)</li>
                        </ul>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: Optional[Dict[str, Any]] = Depends(get_optional_user)  ):
    """로그인 페이지"""
    # 이미 로그인된 경우 현행규정 페이지로 리다이렉트
    if user:
        logger.debug(f"login_page: user already logged in, redirecting to /regulations/current")
        return RedirectResponse(url="/regulations/current", status_code=302)

    return templates.TemplateResponse("login.html", {"request": request, "g":{ "user":{}}, "error_msg":""})

@app.get("/dashboard/login", response_class=HTMLResponse)
async def dashboard_login_page(request: Request, user: Optional[Dict[str, Any]] = Depends(get_optional_user)  ):
    """로그인 페이지"""
    # 이미 로그인된 경우 대시보드로 리다이렉트
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return """
    <html>
        <head>
            <title>Login - WIZICE</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 50px; background: #f5f5f5; }
                .login-form { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                h2 { text-align: center; color: #333; }
                input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                button:hover { background: #0056b3; }
                .error { color: #dc3545; margin: 10px 0; display: none; }
                .links { text-align: center; margin-top: 20px; }
                .links a { color: #007bff; text-decoration: none; }
                .links a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="login-form">
                <h2>Login to WIZICE</h2>
                <div id="error" class="error"></div>
                <form id="loginForm">
                    <input type="text" id="username" placeholder="Username or Email" required>
                    <input type="password" id="password" placeholder="Password" required>
                    <label style="display: block; margin: 10px 0;">
                        <input type="checkbox" id="remember_me"> Remember me for 7 days
                    </label>
                    <button type="submit">Login</button>
                </form>
                <div class="links">
                    <p>Don't have an account? <a href="/register">Register here</a></p>
                    <p><a href="/">Back to Home</a></p>
                </div>
            </div>
            
            <script>
                document.getElementById('loginForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const errorDiv = document.getElementById('error');
                    errorDiv.style.display = 'none';
                    
                    try {
                        const response = await fetch('/api/v1/auth/login', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                username: document.getElementById('username').value,
                                password: document.getElementById('password').value,
                                remember_me: document.getElementById('remember_me').checked
                            })
                        });
                        
                        if (response.ok) {
                            window.location.href = '/dashboard';
                        } else {
                            const error = await response.json();
                            errorDiv.textContent = error.detail || 'Login failed';
                            errorDiv.style.display = 'block';
                        }
                    } catch (error) {
                        errorDiv.textContent = 'Network error. Please try again.';
                        errorDiv.style.display = 'block';
                    }
                });
            </script>
        </body>
    </html>
    """

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """회원가입 페이지"""
    return """
    <html>
        <head>
            <title>Register - WIZICE</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 50px; background: #f5f5f5; }
                .register-form { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                h2 { text-align: center; color: #333; }
                input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                button:hover { background: #218838; }
                .error { color: #dc3545; margin: 10px 0; display: none; }
                .success { color: #28a745; margin: 10px 0; display: none; }
                .links { text-align: center; margin-top: 20px; }
                .links a { color: #007bff; text-decoration: none; }
                .links a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="register-form">
                <h2>Create Account</h2>
                <div id="error" class="error"></div>
                <div id="success" class="success"></div>
                <form id="registerForm">
                    <input type="text" id="username" placeholder="Username" required minlength="3">
                    <input type="email" id="email" placeholder="Email" required>
                    <input type="password" id="password" placeholder="Password (min 8 chars)" required minlength="8">
                    <input type="text" id="full_name" placeholder="Full Name" required>
                    <input type="tel" id="phone" placeholder="Phone (optional)">
                    <button type="submit">Register</button>
                </form>
                <div class="links">
                    <p>Already have an account? <a href="/dashboard/login">Login here</a></p>
                    <p><a href="/">Back to Home</a></p>
                </div>
            </div>
            
            <script>
                document.getElementById('registerForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const errorDiv = document.getElementById('error');
                    const successDiv = document.getElementById('success');
                    errorDiv.style.display = 'none';
                    successDiv.style.display = 'none';
                    
                    try {
                        const response = await fetch('/api/v1/auth/register', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                username: document.getElementById('username').value,
                                email: document.getElementById('email').value,
                                password: document.getElementById('password').value,
                                full_name: document.getElementById('full_name').value,
                                phone: document.getElementById('phone').value || null
                            })
                        });
                        
                        if (response.ok) {
                            successDiv.textContent = 'Registration successful! Redirecting to login...';
                            successDiv.style.display = 'block';
                            setTimeout(() => {
                                window.location.href = '/dashboard/login';
                            }, 2000);
                        } else {
                            const error = await response.json();
                            errorDiv.textContent = error.detail || 'Registration failed';
                            errorDiv.style.display = 'block';
                        }
                    } catch (error) {
                        errorDiv.textContent = 'Network error. Please try again.';
                        errorDiv.style.display = 'block';
                    }
                });
            </script>
        </body>
    </html>
    """

# ===== Protected Routes (인증 필요) =====


@app.get("/admin/api", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def dashboard(request: Request):
    """대시보드 페이지 (로그인 필요)"""
    user = request.state.user
    
    return f"""
    <html>
        <head>
            <title>Dashboard - WIZICE</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }}
                .navbar {{ background: #343a40; color: white; padding: 15px; }}
                .navbar a {{ color: white; text-decoration: none; margin-right: 20px; }}
                .navbar a:hover {{ text-decoration: underline; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                .card {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .logout-btn {{ background: #dc3545; color: white; padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; float: right; }}
                .logout-btn:hover {{ background: #c82333; }}
                .info-item {{ margin: 10px 0; }}
                .info-label {{ font-weight: bold; color: #666; }}
            </style>
        </head>
        <body>
            <div class="navbar">
                <a href="/dashboard">대시보드</a>
                <a href="/profile">프로필</a>
                <a href="/user">사용자관리</a>
                <a href="/sessions">Sessions</a>
                <a href="/docs">API Docs</a>
                <a href="/redoc">ReDoc</a>
                <button class="logout-btn" onclick="logout()">Logout</button>
            </div>
            
            <div class="container">
                <div class="header">
                    <h1>Welcome to your Dashboard, {user['full_name']}!</h1>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h2>User Information</h2>
                        <div class="info-item">
                            <span class="info-label">Username:</span> {user['username']}
                        </div>
                        <div class="info-item">
                            <span class="info-label">Email:</span> {user['email']}
                        </div>
                        <div class="info-item">
                            <span class="info-label">Phone:</span> {user.get('phone', 'Not provided')}
                        </div>
                        <div class="info-item">
                            <span class="info-label">Email Verified:</span> {'Yes' if user.get('is_email_verified') else 'No'}
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Quick Actions</h2>
                        <ul>
                            <li><a href="/profile">Update Profile</a></li>
                            <li><a href="/sessions">Manage Sessions</a></li>
                            <li><a href="/api/v1/auth/me">View API Profile</a></li>
                            <li><a href="#" onclick="changePassword()">Change Password</a></li>
                        </ul>
                    </div>
                    
                    <div class="card">
                        <h2>API Access</h2>
                        <p>Use your session token for API access:</p>
                        <code style="background: #f5f5f5; padding: 10px; display: block; border-radius: 5px;">
                            Authorization: Bearer YOUR_SESSION_TOKEN
                        </code>
                        <p style="margin-top: 10px;">
                            <a href="/docs" target="_blank">View API Documentation</a>
                        </p>
                    </div>
                </div>
            </div>
            
            <script>
                async function logout() {{
                    if (confirm('Are you sure you want to logout?')) {{
                        const response = await fetch('/api/v1/auth/logout', {{
                            method: 'POST',
                            credentials: 'include'
                        }});
                        
                        if (response.ok) {{
                            window.location.href = '/';
                        }}
                    }}
                }}
                
                function changePassword() {{
                    alert('Password change functionality would be implemented here');
                }}
            </script>
        </body>
    </html>
    """

@app.get("/profile")
async def profile_page(user: Dict[str, Any] = Depends(get_current_user)):
    """프로필 페이지 (API 방식)"""
    return {
        "page": "profile",
        "user": user,
        "message": "This is your profile page"
    }

@app.get("/sessions", response_class=HTMLResponse)
async def sessions_page(user: Dict[str, Any] = Depends(get_current_user)):
    """활성 세션 관리 페이지"""
    return f"""
    <html>
        <head>
            <title>Active Sessions - WIZICE</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }}
                .navbar {{ background: #343a40; color: white; padding: 15px; }}
                .navbar a {{ color: white; text-decoration: none; margin-right: 20px; }}
                .navbar a:hover {{ text-decoration: underline; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                .card {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .btn {{ padding: 8px 16px; margin: 5px; cursor: pointer; border: none; border-radius: 5px; }}
                .btn-danger {{ background: #dc3545; color: white; }}
                .btn-danger:hover {{ background: #c82333; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .btn-warning:hover {{ background: #e0a800; }}
                .current-session {{ background-color: #d4edda; }}
            </style>
        </head>
        <body>
            <div class="navbar">
                <a href="/dashboard">대시보드</a>
                <a href="/profile">프로필</a>
                <a href="/user">사용자관리</a>
                <a href="/sessions">Sessions</a>
                <a href="/docs">API Docs</a>
                <a href="/redoc">ReDoc</a>
            </div>
            
            <div class="container">
                <div class="card">
                    <h1>Your Active Sessions</h1>
                    <p>Manage your active login sessions across different devices.</p>
                    
                    <div style="margin: 20px 0;">
                        <button class="btn btn-danger" onclick="logoutAll()">Logout All Sessions</button>
                        <button class="btn btn-warning" onclick="logoutOthers()">Logout Other Sessions</button>
                    </div>
                    
                    <div id="sessions-container">
                        <p>Loading sessions...</p>
                    </div>
                </div>
            </div>
            
            <script>
                let currentSessionToken = null;
                
                async function loadSessions() {{
                    try {{
                        const response = await fetch('/api/v1/auth/sessions', {{
                            credentials: 'include'
                        }});
                        
                        if (response.ok) {{
                            const data = await response.json();
                            displaySessions(data.sessions);
                        }} else {{
                            document.getElementById('sessions-container').innerHTML = 
                                '<p style="color: red;">Failed to load sessions</p>';
                        }}
                    }} catch (error) {{
                        document.getElementById('sessions-container').innerHTML = 
                            '<p style="color: red;">Error loading sessions</p>';
                    }}
                }}
                
                function displaySessions(sessions) {{
                    const container = document.getElementById('sessions-container');
                    
                    if (!sessions || sessions.length === 0) {{
                        container.innerHTML = '<p>No active sessions found.</p>';
                        return;
                    }}
                    
                    let html = `
                        <table>
                            <thead>
                                <tr>
                                    <th>Session Token</th>
                                    <th>Created</th>
                                    <th>Last Access</th>
                                    <th>IP Address</th>
                                    <th>Device</th>
                                    <th>User Agent</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;
                    
                    sessions.forEach((session, index) => {{
                        const isCurrentSession = index === 0; // Assuming first session is current
                        html += `<tr class="${{isCurrentSession ? 'current-session' : ''}}">
                            <td>${{session.session_token}}</td>
                            <td>${{new Date(session.created_at).toLocaleString()}}</td>
                            <td>${{new Date(session.last_accessed).toLocaleString()}}</td>
                            <td>${{session.ip_address || 'N/A'}}</td>
                            <td>${{session.device_info || 'Unknown'}}</td>
                            <td title="${{session.user_agent || ''}}">${{session.user_agent || 'N/A'}}</td>
                        </tr>`;
                    }});
                    
                    html += '</tbody></table>';
                    html += '<p style="margin-top: 10px; color: #666;">* Highlighted row indicates your current session</p>';
                    
                    container.innerHTML = html;
                }}
                
                async function logoutAll() {{
                    if (confirm('Are you sure you want to logout from ALL sessions? You will need to login again.')) {{
                        try {{
                            const response = await fetch('/api/v1/auth/logout-all', {{
                                method: 'POST',
                                credentials: 'include'
                            }});
                            
                            if (response.ok) {{
                                alert('Successfully logged out from all sessions');
                                window.location.href = '/dashboard/login';
                            }} else {{
                                alert('Failed to logout from all sessions');
                            }}
                        }} catch (error) {{
                            alert('Error occurred while logging out');
                        }}
                    }}
                }}
                
                async function logoutOthers() {{
                    if (confirm('Are you sure you want to logout from all other sessions?')) {{
                        try {{
                            const response = await fetch('/api/v1/auth/logout-other', {{
                                method: 'POST',
                                credentials: 'include'
                            }});
                            
                            if (response.ok) {{
                                const data = await response.json();
                                alert(`Successfully logged out from ${{data.terminated_count}} other sessions`);
                                loadSessions(); // Reload the sessions list
                            }} else {{
                                alert('Failed to logout from other sessions');
                            }}
                        }} catch (error) {{
                            alert('Error occurred while logging out');
                        }}
                    }}
                }}
                
                // Load sessions on page load
                loadSessions();
                
                // Refresh sessions every 30 seconds
                setInterval(loadSessions, 30000);
            </script>
        </body>
    </html>
    """

# ===== Admin Routes (관리자 권한 필요) =====

@app.get("/admin/", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_dashboard(request: Request,
            user: Dict[str, Any] = Depends(require_role("admin"))
            ):
    data     = {}
    return templates.TemplateResponse("editor.html", 
            {"request": request,     # 필수 !
                "user": user,        # g.user 대체
                "g": {"user": user } #-- 기존 템플릿 호환성
            })

@app.get("/admin/article_page", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_article_page(request: Request,
            user: Dict[str, Any] = Depends(require_role("admin"))
            ):
    data     = {}
    return templates.TemplateResponse("app/admin_article_page.html", 
            {"request": request,     # 필수 !
                "user": user,        # g.user 대체
                "g": {"user": user } #-- 기존 템플릿 호환성
            })


@app.get("/admin/panel")
async def admin_panel(user: Dict[str, Any] = Depends(require_role("admin"))):
    """관리자 패널 (관리자 권한 필요)"""
    return {
        "page": "admin",
        "user": user,
        "message": "Welcome to admin panel",
        "permissions": ["user_management", "system_config", "audit_logs"]
    }

@app.get("/admin/dashboard", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_dashboard(request: Request,
            user: Dict[str, Any] = Depends(require_role("admin"))
            ):
    data     = {}
    file_path    = "/tmp/sample1.json"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Sample data file not found: {file_path}")
        data = {}
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        data = {}

    return templates.TemplateResponse("app/admin_index.html",
            {"request": request,     # 필수 !
                "user": user,        # g.user 대체
                "data": data,
                "g": {"user": user } #-- 기존 템플릿 호환성
            })


@app.get("/admin/accounts", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_accounts(request: Request,
            user: Dict[str, Any] = Depends(require_role("admin"))
            ):
    data     = {}
    return templates.TemplateResponse("admin/wz_admin_accounts.html", 
            {"request": request,     # 필수 !
                "user": user,        # g.user 대체
                "g": {"user": user } #-- 기존 템플릿 호환성
            })

@app.get("/admin/send/mgr", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_send_mgr(request: Request,
            user: Dict[str, Any] = Depends(require_role("admin"))
            ):
    data     = {}
    return templates.TemplateResponse("app/admin_send_mgr.html",
            {"request": request,     # 필수 !
                "user": user,        # g.user 대체
                "g": {"user": user } #-- 기존 템플릿 호환성
            })

@app.get("/admin/indexing", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_indexing(request: Request,
            user: Dict[str, Any] = Depends(require_role("admin"))
            ):
    """색인 관리 페이지"""
    data     = {}
    return templates.TemplateResponse("admin/indexing_management.html",
            {"request": request,     # 필수 !
                "user": user,        # g.user 대체
                "g": {"user": user } #-- 기존 템플릿 호환성
            })

@app.get("/admin/newsletter", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def admin_newsletter(request: Request,
            user: Dict[str, Any] = Depends(require_role("admin"))
            ):
    data     = {}
    return templates.TemplateResponse("app/admin_newsletter_page.html", 
            {"request": request,     # 필수 !
                "user": user,        # g.user 대체
                "g": {"user": user } #-- 기존 템플릿 호환성
            })


# ===== API Routes Registration =====

# 인증 라우터 (공개)
app.include_router(auth_router)

# 사용자 관리 라우터 (인증 필요)
app.include_router(
    users_router,
    dependencies=[Depends(get_current_active_user)]
)

# 세션 관리 라우터 (인증 필요)
app.include_router(
    sessions_router,
    dependencies=[Depends(get_current_active_user)]
)

# 모니터 라우터 (인증 필요)
app.include_router(
    monitor_router,
    dependencies=[Depends(get_current_active_user)]
)

# ===== Protected API Examples =====

@app.get("/api/v1/protected")
async def protected_route(user: Dict[str, Any] = Depends(get_current_user)):
    """보호된 API 엔드포인트 예제"""
    return {
        "message": "This is a protected endpoint",
        "user": user,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/optional-auth")
async def optional_auth_route(user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """선택적 인증 엔드포인트 예제"""
    if user:
        return {
            "message": f"Hello {user['username']}!",
            "authenticated": True,
            "user": user
        }
    else:
        return {
            "message": "Hello anonymous user!",
            "authenticated": False,
            "features": "Limited features available. Please login for full access."
        }

@app.get("/api/v1/admin-only")
async def admin_only_route(user: Dict[str, Any] = Depends(require_role("admin"))):
    """관리자 전용 API 엔드포인트"""
    return {
        "message": "This is an admin-only endpoint",
        "admin_user": user,
        "admin_features": ["user_management", "system_monitoring", "audit_logs"]
    }

# ===== Error Handlers =====

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    # HTML 요청인 경우 401 에러 페이지로 리다이렉트
    accept_header = request.headers.get("accept", "")
    logger.debug(f"http_exception_handler exc={exc}")
    if exc.status_code == 401 and "text/html" in accept_header:
        # 관리자 페이지(/admin, /ad)는 로그인 페이지로 리다이렉트
        request_path = request.url.path
        if request_path.startswith("/admin") or request_path.startswith("/ad"):
            return RedirectResponse(url="/login", status_code=302)

        # 인증 실패는 로그인 페이지로
        return RedirectResponse(url="/login", status_code=302)

    # API 요청인 경우 JSON 응답
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 처리"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500
        }
    )


@app.get("/api/v1/regulations/current", dependencies=[Depends(get_current_user)])
async def get_current_regulations(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """현행 규정 목록 조회"""
    try:
        db_config = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
        }

        from api.timescaledb_manager_v2 import DatabaseConnectionManager
        db_manager = DatabaseConnectionManager(**db_config)

        query = """
            SELECT
                wzruleseq as rule_id,
                wzname as name,
                wzpubno as publication_no,
                wzestabdate as established_date,
                wzlastrevdate as last_revised_date,
                wzexecdate as execution_date,
                wzmgrdptnm as department,
                wzedittype as edit_type,
                wzlkndname as large_category,
                wzcontent_path as content_path,
                wznewflag as status
            FROM wz_rule
            WHERE wznewflag = '현행'
            ORDER BY
                wzcateseq,
                -- wzpubno를 숫자로 정렬 (예: 2.1.3.2 → 2.1.3.10 순서)
                CAST(NULLIF(split_part(wzpubno, '.', 1), '') AS INTEGER) NULLS LAST,
                CAST(NULLIF(split_part(wzpubno, '.', 2), '') AS INTEGER) NULLS LAST,
                CAST(NULLIF(split_part(wzpubno, '.', 3), '') AS INTEGER) NULLS LAST,
                CAST(NULLIF(split_part(wzpubno, '.', 4), '') AS INTEGER) NULLS LAST
            LIMIT 1000
        """

        logger.debug(f"[DEBUG] Executing regulations query with numeric sort")
        results = db_manager.execute_query(query, fetch_all=True)
        if results and len(results) >= 10:
            logger.debug(f"[DEBUG] First 10 results: {[r.get('publication_no') if isinstance(r, dict) else r[2] for r in results[:10]]}")

        # 결과를 딕셔너리 리스트로 변환
        data = []
        if results:
            for row in results:
                data.append({
                    'rule_id': row[0],
                    'name': row[1],
                    'publication_no': row[2],
                    'established_date': str(row[3]) if row[3] else None,
                    'last_revised_date': str(row[4]) if row[4] else None,
                    'execution_date': str(row[5]) if row[5] else None,
                    'department': row[6],
                    'edit_type': row[7],
                    'large_category': row[8],
                    'content_path': row[9],
                    'status': row[10]
                })

        return {
            "success": True,
            "data": data,
            "total": len(data),
            "limit": 1000,
            "offset": 0
        }

    except Exception as e:
        logger.error(f"Error fetching current regulations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Load environment variables
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run server
    config  = uvicorn.Config(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8800")),
        reload=settings.debug,
        workers=1,
        reload_excludes=["logs/*", "data/*", "db/*", "*.pyc", "__pycache__/*"],
        log_level=settings.log_level.lower(),
        access_log=True, #   운영시 자원이 부족하면 False 처리할 것
    )
    server = uvicorn.Server(config)
    server.run()
