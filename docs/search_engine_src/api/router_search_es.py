# -*- coding: utf-8 -*-
"""
    router_search_es.py
    ~~~~~~~~~~~~~~~~~~~

    Elasticsearch 기반 검색 라우터
    (연세대 lib_es.py 패턴 기반)

    :copyright: (c) 2024 by wizice.
    :license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from .auth_middleware import get_current_user
from lib_es_sev import LibEs
from hanparse import HanParse
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/search-es",
    tags=["search-elasticsearch"],
    responses={404: {"description": "Not found"}},
)

# Elasticsearch 설정 (settings.py에서 가져오기)
from settings import settings

ES_IP = settings.ES_HOST
ES_PORT = settings.ES_PORT
INDEX_RULE = settings.ES_INDEX_RULE
INDEX_ARTICLE = settings.ES_INDEX_ARTICLE

# 전역 Elasticsearch 인스턴스
es_rule_client = None
es_article_client = None
hanparse = HanParse()


def init_es_clients():
    """Elasticsearch 클라이언트 초기화"""
    global es_rule_client, es_article_client

    try:
        # 규정 검색용 클라이언트
        es_rule_client = LibEs(
            index=INDEX_RULE,
            doc_type="list",
            es_ip=ES_IP,
            es_port=ES_PORT
        )
        es_rule_client.Log = logger

        # 조문 검색용 클라이언트
        es_article_client = LibEs(
            index=INDEX_ARTICLE,
            doc_type="list",
            es_ip=ES_IP,
            es_port=ES_PORT
        )
        es_article_client.Log = logger

        logger.info(f"Elasticsearch clients initialized: {ES_IP}:{ES_PORT}")
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch clients: {e}")
        raise


def get_es_rule_client() -> LibEs:
    """규정 검색용 ES 클라이언트 반환"""
    if es_rule_client is None:
        init_es_clients()
    return es_rule_client


def get_es_article_client() -> LibEs:
    """조문 검색용 ES 클라이언트 반환"""
    if es_article_client is None:
        init_es_clients()
    return es_article_client


@router.get("/health")
async def health_check():
    """Elasticsearch 서버 상태 확인"""
    try:
        es_client = get_es_rule_client()
        info = es_client.es.info()

        return {
            "success": True,
            "status": "healthy",
            "elasticsearch": {
                "cluster_name": info.get("cluster_name"),
                "version": info.get("version", {}).get("number"),
                "tagline": info.get("tagline")
            },
            "config": {
                "host": ES_IP,
                "port": ES_PORT,
                "rule_index": INDEX_RULE,
                "article_index": INDEX_ARTICLE
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Elasticsearch is not available: {str(e)}"
        )


@router.get("/indices")
async def get_indices_info(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """인덱스 정보 조회"""
    try:
        es_client = get_es_rule_client()

        # 규정 인덱스 통계
        rule_stats = es_client.es.count(index=INDEX_RULE)
        rule_count = rule_stats.get("count", 0)

        # 조문 인덱스 통계
        article_stats = es_client.es.count(index=INDEX_ARTICLE)
        article_count = article_stats.get("count", 0)

        # 인덱스 상태
        cluster_health = es_client.es.cluster.health()

        return {
            "success": True,
            "indices": {
                "rules": {
                    "index": INDEX_RULE,
                    "document_count": rule_count
                },
                "articles": {
                    "index": INDEX_ARTICLE,
                    "document_count": article_count
                }
            },
            "cluster": {
                "status": cluster_health.get("status"),
                "number_of_nodes": cluster_health.get("number_of_nodes")
            }
        }
    except Exception as e:
        logger.error(f"Error getting indices info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/search")
async def search_rules(
    q: str = Query(..., min_length=2, description="검색어 (최소 2자)"),
    department: Optional[str] = Query(None, description="부서 필터"),
    size: int = Query(20, le=1000, description="결과 수 (최대 1000)"),
    from_: int = Query(0, ge=0, description="시작 위치", alias="from"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """규정 검색 (tags 필드 기반)

    Elasticsearch tags 필드를 사용한 한글 형태소 기반 검색

    Args:
        q: 검색어 (2자 이상)
        department: 부서명 필터 (선택)
        size: 반환할 결과 수
        from_: 시작 위치 (페이징용)

    Returns:
        검색 결과 목록
    """
    try:
        es_client = get_es_rule_client()

        # 검색어를 토큰으로 분해
        keywords = hanparse.parse(q)
        logger.debug(f"Search query '{q}' tokenized to: {keywords}")

        # Query String DSL 구성
        # tags 필드에서 토큰 검색 + 규정명에서 원문 검색
        query_parts = []

        # 토큰 기반 검색 (tags 필드)
        for keyword in keywords:
            query_parts.append(f"+tags:{keyword}")

        # 부서 필터 추가
        if department:
            query_parts.append(f'+wzdeptname:"{department}"')

        q_string = " ".join(query_parts)
        logger.debug(f"Elasticsearch query string: {q_string}")

        # Elasticsearch 검색 실행
        results = es_client.search_q(
            q_string=q_string,
            index=INDEX_RULE,
            from_=from_,
            size=size,
            sort="wzrulename:asc",
            debug=False
        )

        # 결과 파싱
        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {})

        # total이 dict 형식인 경우 (ES 7.x+)
        if isinstance(total, dict):
            total_count = total.get("value", 0)
        else:
            total_count = total

        # 결과 포맷팅
        search_results = []
        for hit in hits:
            source = hit.get("_source", {})
            search_results.append({
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "wzruleseq": source.get("wzruleseq"),
                "wzrulename": source.get("wzrulename"),
                "wzpubno": source.get("wzpubno"),
                "wzdeptname": source.get("wzdeptname"),
                "wzestabdate": source.get("wzestabdate"),
                "wzexecdate": source.get("wzexecdate"),
                "wzrevdate": source.get("wzrevdate"),
                "wzfilepath": source.get("wzfilepath")
            })

        return {
            "success": True,
            "query": q,
            "keywords": keywords,
            "total": total_count,
            "results": search_results,
            "size": size,
            "from": from_,
            "took": results.get("took", 0)
        }

    except Exception as e:
        logger.error(f"Error in search_rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/search")
async def search_articles(
    q: str = Query(..., min_length=2, description="검색어 (최소 2자)"),
    rule_name: Optional[str] = Query(None, description="규정명 필터"),
    size: int = Query(20, le=1000, description="결과 수 (최대 1000)"),
    from_: int = Query(0, ge=0, description="시작 위치", alias="from"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """조문 검색 (tags 필드 기반)

    Elasticsearch tags 필드를 사용한 조문 내용 검색

    Args:
        q: 검색어 (2자 이상)
        rule_name: 규정명 필터 (선택)
        size: 반환할 결과 수
        from_: 시작 위치 (페이징용)

    Returns:
        조문 검색 결과 목록
    """
    try:
        es_client = get_es_article_client()

        # 검색어를 토큰으로 분해
        keywords = hanparse.parse(q)
        logger.debug(f"Article search query '{q}' tokenized to: {keywords}")

        # Query String DSL 구성
        query_parts = []

        # 토큰 기반 검색 (tags 필드)
        for keyword in keywords:
            query_parts.append(f"+tags:{keyword}")

        # 규정명 필터
        if rule_name:
            query_parts.append(f'+wzrulename:"{rule_name}"')

        q_string = " ".join(query_parts)
        logger.debug(f"Article search query string: {q_string}")

        # Elasticsearch 검색 실행
        results = es_client.search_q(
            q_string=q_string,
            index=INDEX_ARTICLE,
            from_=from_,
            size=size,
            sort="wzruleseq:asc,wzseq:asc",
            debug=False
        )

        # 결과 파싱
        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {})

        # total이 dict 형식인 경우 (ES 7.x+)
        if isinstance(total, dict):
            total_count = total.get("value", 0)
        else:
            total_count = total

        # 결과 포맷팅
        search_results = []
        for hit in hits:
            source = hit.get("_source", {})
            search_results.append({
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "wzruleseq": source.get("wzruleseq"),
                "wzrulename": source.get("wzrulename"),
                "wzseq": source.get("wzseq"),
                "wzlevel": source.get("wzlevel"),
                "wzcont": source.get("wzcont"),
                "wzno": source.get("wzno")
            })

        return {
            "success": True,
            "query": q,
            "keywords": keywords,
            "total": total_count,
            "results": search_results,
            "size": size,
            "from": from_,
            "took": results.get("took", 0)
        }

    except Exception as e:
        logger.error(f"Error in search_articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/search")
async def advanced_search(
    q_string: str = Query(..., description="Elasticsearch Query String"),
    index: str = Query("severance_rule", description="검색 인덱스 (severance_rule or severance_article)"),
    size: int = Query(20, le=1000, description="결과 수"),
    from_: int = Query(0, ge=0, description="시작 위치", alias="from"),
    sort: str = Query("_score:desc", description="정렬 기준"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """고급 검색 (Query String DSL 직접 사용)

    Elasticsearch Query String 문법을 직접 사용하는 고급 검색

    Query String 예시:
    - "+wzrulename:(*환자* *안전*)" - 규정명에 환자와 안전 포함
    - "+tags:안전 +wzdeptname:의료질향상팀" - tags에 안전, 부서명 필터
    - "wzrulename:/.*레이저.*/" - 정규표현식 사용

    Args:
        q_string: Elasticsearch Query String
        index: 검색할 인덱스
        size: 결과 수
        from_: 시작 위치
        sort: 정렬 기준

    Returns:
        검색 결과
    """
    try:
        # 인덱스 선택
        if index == INDEX_RULE:
            es_client = get_es_rule_client()
        elif index == INDEX_ARTICLE:
            es_client = get_es_article_client()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid index. Use '{INDEX_RULE}' or '{INDEX_ARTICLE}'"
            )

        logger.info(f"Advanced search - index: {index}, query: {q_string}")

        # Elasticsearch 검색 실행
        results = es_client.search_q(
            q_string=q_string,
            index=index,
            from_=from_,
            size=size,
            sort=sort,
            debug=False
        )

        # 결과 파싱
        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {})

        if isinstance(total, dict):
            total_count = total.get("value", 0)
        else:
            total_count = total

        # 결과 포맷팅
        search_results = []
        for hit in hits:
            search_results.append({
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "source": hit.get("_source", {})
            })

        return {
            "success": True,
            "query_string": q_string,
            "index": index,
            "total": total_count,
            "results": search_results,
            "size": size,
            "from": from_,
            "took": results.get("took", 0)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in advanced_search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_search_stats(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """검색 통계 조회

    인덱스별 문서 수, 부서별 문서 수 등의 통계 제공
    """
    try:
        es_client = get_es_rule_client()

        # 규정 인덱스 통계
        rule_count_result = es_client.es.count(index=INDEX_RULE)
        rule_count = rule_count_result.get("count", 0)

        # 조문 인덱스 통계
        article_count_result = es_client.es.count(index=INDEX_ARTICLE)
        article_count = article_count_result.get("count", 0)

        # 부서별 집계 (규정)
        dept_agg = es_client.es.search(
            index=INDEX_RULE,
            body={
                "size": 0,
                "aggs": {
                    "departments": {
                        "terms": {
                            "field": "wzdeptname.keyword",
                            "size": 20
                        }
                    }
                }
            }
        )

        dept_stats = []
        buckets = dept_agg.get("aggregations", {}).get("departments", {}).get("buckets", [])
        for bucket in buckets:
            dept_stats.append({
                "department": bucket.get("key"),
                "count": bucket.get("doc_count")
            })

        return {
            "success": True,
            "stats": {
                "rule_count": rule_count,
                "article_count": article_count,
                "total_documents": rule_count + article_count
            },
            "department_stats": dept_stats
        }

    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 애플리케이션 시작 시 Elasticsearch 클라이언트 초기화
try:
    init_es_clients()
except Exception as e:
    logger.warning(f"Elasticsearch initialization failed at startup: {e}")
    logger.warning("Clients will be initialized on first request")
