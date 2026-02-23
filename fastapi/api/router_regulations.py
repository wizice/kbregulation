"""
현행 내규목록 라우터
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from api.auth_middleware import get_current_user, login_required
from api.query_wz_rule_v1 import WzRuleTable
import logging
import os
from settings import settings

router = APIRouter(prefix="/regulations", tags=["regulations"])
logger = logging.getLogger(__name__)

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

@router.get("/current", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def current_regulations(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """현행 내규목록 페이지"""
    try:
        # WZ_RULE 테이블 인스턴스 생성
        wz_rule = WzRuleTable(
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT)
        )

        # 데이터베이스 연결 및 조회
        wz_rule.connect()

        # 현행 내규목록 조회 (wzCloseDate가 NULL인 것만)
        query = f"""
        SELECT wzRuleSeq, wzLevel, wzRuleId, wzName, wzEditType,
               wzPubNo, wzEstabDate, wzLastRevDate, wzMgrDptNm,
               wzMgrDptOrgCd, wzRelDptNm, wzRelDptOrgCd, wzCateSeq,
               wzExecDate, wzLKndName, wzCloseDate, wzFileDocx, wzFilePdf
        FROM {wz_rule.TABLE_NAME}
        WHERE wzCloseDate IS NULL OR wzCloseDate = ''
        ORDER BY
            wzCateSeq ASC,
            string_to_array(regexp_replace(wzPubNo, '[^0-9.]', '', 'g'), '.')::int[] ASC,
            wzRuleSeq ASC
        """

        regulations = wz_rule.query(query)
        wz_rule.close()

        # 데이터 가공 (날짜 포맷팅 등)
        for reg in regulations:
            if reg.get('wzEstabDate'):
                reg['wzEstabDate'] = reg['wzEstabDate'][:10] if len(reg['wzEstabDate']) >= 10 else reg['wzEstabDate']
            if reg.get('wzLastRevDate'):
                reg['wzLastRevDate'] = reg['wzLastRevDate'][:10] if len(reg['wzLastRevDate']) >= 10 else reg['wzLastRevDate']
            if reg.get('wzExecDate'):
                reg['wzExecDate'] = reg['wzExecDate'][:10] if len(reg['wzExecDate']) >= 10 else reg['wzExecDate']

        return templates.TemplateResponse(
            "regulations/current_full.html",
            {
                "request": request,
                "user": user,
                "page_title": "세브란스병원 내규 편집기",
                "regulations": regulations,
                "total_count": len(regulations)
            }
        )

    except Exception as e:
        logger.error(f"현행 내규목록 조회 오류: {e}")
        return templates.TemplateResponse(
            "regulations/current_full.html",
            {
                "request": request,
                "user": user,
                "page_title": "세브란스병원 내규 편집기",
                "regulations": [],
                "total_count": 0,
                "error": str(e)
            }
        )

@router.get("/api/current")
async def get_current_regulations(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """현행 내규목록 API (JSON)"""
    try:
        # WZ_RULE 테이블 인스턴스 생성
        wz_rule = WzRuleTable(
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT)
        )

        # 데이터베이스 연결 및 조회
        wz_rule.connect()

        # 현행 내규목록 조회 (wzCloseDate가 NULL인 것만)
        query = f"""
        SELECT wzRuleSeq, wzLevel, wzRuleId, wzName, wzEditType,
               wzPubNo, wzEstabDate, wzLastRevDate, wzMgrDptNm,
               wzMgrDptOrgCd, wzRelDptNm, wzRelDptOrgCd, wzCateSeq,
               wzExecDate, wzLKndName, wzCloseDate, wzFileDocx, wzFilePdf
        FROM {wz_rule.TABLE_NAME}
        WHERE wzCloseDate IS NULL OR wzCloseDate = ''
        ORDER BY
            wzCateSeq ASC,
            string_to_array(regexp_replace(wzPubNo, '[^0-9.]', '', 'g'), '.')::int[] ASC,
            wzRuleSeq ASC
        """

        regulations = wz_rule.query(query)
        wz_rule.close()

        # 데이터 가공 (날짜 포맷팅 등)
        for reg in regulations:
            if reg.get('wzEstabDate'):
                reg['wzEstabDate'] = reg['wzEstabDate'][:10] if len(reg['wzEstabDate']) >= 10 else reg['wzEstabDate']
            if reg.get('wzLastRevDate'):
                reg['wzLastRevDate'] = reg['wzLastRevDate'][:10] if len(reg['wzLastRevDate']) >= 10 else reg['wzLastRevDate']
            if reg.get('wzExecDate'):
                reg['wzExecDate'] = reg['wzExecDate'][:10] if len(reg['wzExecDate']) >= 10 else reg['wzExecDate']

        return {
            "success": True,
            "data": regulations,
            "total_count": len(regulations)
        }

    except Exception as e:
        logger.error(f"현행 내규목록 조회 오류: {e}")
        return {
            "success": False,
            "data": [],
            "total_count": 0,
            "error": str(e)
        }

@router.get("/history", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def regulation_history(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """연혁목록 페이지"""
    return templates.TemplateResponse(
        "regulations/history_full.html",
        {
            "request": request,
            "user": user,
            "page_title": "세브란스병원 내규 편집기"
        }
    )

def format_date_for_input(date_str):
    """날짜를 HTML date input 형식(YYYY-MM-DD)으로 변환"""
    if not date_str:
        return ''
    # 이미 YYYY-MM-DD 형식인 경우
    if isinstance(date_str, str) and len(date_str) >= 10 and date_str[4] == '-':
        return date_str[:10]
    # YYYY.MM.DD 형식인 경우
    if isinstance(date_str, str) and '.' in date_str:
        parts = date_str.replace('.', '-').split('-')
        if len(parts) >= 3:
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
    return str(date_str)[:10] if date_str else ''


@router.get("/history/{rule_id}", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def regulation_history_detail(
    request: Request,
    rule_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """연혁 상세 페이지"""
    try:
        wz_rule = WzRuleTable(
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT)
        )

        wz_rule.connect()

        query = f"""
        SELECT wzRuleSeq, wzRuleId, wzName, wzPubNo, wzEditType,
               wzEstabDate, wzLastRevDate, wzExecDate, wzCloseDate,
               wzMgrDptNm, wzMgrDptOrgCd, wzRelDptNm, wzRelDptOrgCd,
               wzFileDocx, wzFilePdf, wzFileJson, wzNewFlag, wzFileHistory
        FROM {wz_rule.TABLE_NAME}
        WHERE wzRuleSeq = %s
        """

        results = wz_rule.query(query, (rule_id,))
        wz_rule.close()

        if not results:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        rule = results[0]

        # 소문자 키로 변환
        rule_data = {k.lower(): v for k, v in rule.items()}

        # 날짜 형식 변환 (HTML date input용)
        for date_field in ['wzestabdate', 'wzlastrevdate', 'wzexecdate', 'wzclosedate']:
            if rule_data.get(date_field):
                rule_data[date_field] = format_date_for_input(rule_data[date_field])

        return templates.TemplateResponse(
            "regulations/history_detail.html",
            {
                "request": request,
                "user": user,
                "rule": rule_data,
                "page_title": f"연혁 상세 - {rule_data.get('wzname', '')}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"연혁 상세 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/history")
async def get_regulation_history(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """연혁목록 API (JSON)"""
    try:
        wz_rule = WzRuleTable(
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT)
        )

        wz_rule.connect()

        # 연혁 규정 조회 (wzNewFlag='연혁')
        query = f"""
        SELECT wzRuleSeq, wzLevel, wzRuleId, wzName, wzEditType,
               wzPubNo, wzEstabDate, wzLastRevDate, wzMgrDptNm,
               wzMgrDptOrgCd, wzRelDptNm, wzRelDptOrgCd, wzCateSeq,
               wzExecDate, wzLKndName, wzCloseDate, wzFileDocx, wzFilePdf, wzNewFlag, wzFileHistory
        FROM {wz_rule.TABLE_NAME}
        WHERE wzNewFlag = '연혁'
        ORDER BY wzCloseDate DESC NULLS LAST, wzRuleSeq DESC
        """

        history = wz_rule.query(query)
        wz_rule.close()

        # 데이터 가공
        for reg in history:
            for date_field in ['wzEstabDate', 'wzLastRevDate', 'wzExecDate', 'wzCloseDate']:
                if reg.get(date_field):
                    reg[date_field] = reg[date_field][:10] if len(reg[date_field]) >= 10 else reg[date_field]

        return {
            "success": True,
            "data": history,
            "total_count": len(history)
        }

    except Exception as e:
        logger.error(f"연혁목록 조회 오류: {e}")
        return {
            "success": False,
            "data": [],
            "total_count": 0,
            "error": str(e)
        }

@router.get("/search", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def search_regulations(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """상세 검색 페이지"""
    return templates.TemplateResponse(
        "regulations/search_full.html",
        {
            "request": request,
            "user": user,
            "page_title": "상세 검색"
        }
    )

@router.get("/classification", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def classification_management(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """분류 관리 페이지"""
    return templates.TemplateResponse(
        "regulations/classification_full.html",
        {
            "request": request,
            "user": user,
            "page_title": "세브란스병원 내규 편집기"
        }
    )

@router.get("/department", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def department_management(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """부서 관리 페이지"""
    return templates.TemplateResponse(
        "regulations/department_full.html",
        {
            "request": request,
            "user": user,
            "page_title": "세브란스병원 내규 편집기"
        }
    )

@router.get("/search-engine", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def search_engine_management(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """검색 엔진 관리 페이지"""
    return templates.TemplateResponse(
        "regulations/search-engine_full.html",
        {
            "request": request,
            "user": user,
            "page_title": "세브란스병원 내규 편집기"
        }
    )

@router.get("/service", response_class=HTMLResponse)
@login_required(redirect_to="/login")
async def service_management(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """서비스 관리 페이지 (공지사항 + 지원페이지 통합)"""
    return templates.TemplateResponse(
        "regulations/support_full.html",
        {
            "request": request,
            "user": user,
            "page_title": "세브란스병원 내규 편집기"
        }
    )

@router.get("/api/view/{rule_id}")
async def get_regulation_detail(
    rule_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """규정 상세 정보 API (JSON)"""
    try:
        # WZ_RULE 테이블 인스턴스 생성
        wz_rule = WzRuleTable(
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT)
        )

        # 데이터베이스 연결 및 조회
        wz_rule.connect()

        # 특정 규정 조회
        query = f"""
        SELECT wzRuleSeq, wzLevel, wzRuleId, wzName, wzEditType,
               wzPubNo, wzEstabDate, wzLastRevDate, wzMgrDptNm,
               wzMgrDptOrgCd, wzRelDptNm, wzRelDptOrgCd, wzCateSeq,
               wzExecDate, wzLKndName, wzCloseDate, wzFileDocx, wzFilePdf,
               wzNewFlag, content_text
        FROM {wz_rule.TABLE_NAME}
        WHERE wzRuleSeq = %s
        """

        result = wz_rule.query(query, (rule_id,))
        wz_rule.close()

        if result and len(result) > 0:
            regulation = result[0]

            # 날짜 포맷팅
            for date_field in ['wzEstabDate', 'wzLastRevDate', 'wzExecDate', 'wzCloseDate']:
                if regulation.get(date_field):
                    regulation[date_field] = regulation[date_field][:10] if len(regulation[date_field]) >= 10 else regulation[date_field]

            return {
                "success": True,
                "data": regulation
            }
        else:
            return {
                "success": False,
                "error": "규정을 찾을 수 없습니다."
            }

    except Exception as e:
        logger.error(f"규정 상세 조회 오류: {e}")
        return {
            "success": False,
            "error": str(e)
        }