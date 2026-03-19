# -*- coding: utf-8 -*-
"""
    router_public_search_es.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Elasticsearch 기반 검색 API (실험용)
    기존 /api/search 서비스에 영향 없이 독립적으로 운영

    엔드포인트:
    - GET /api/search/es/health     : ES 서버 상태 확인
    - GET /api/search/es            : ES 검색 (실험용)
    - GET /api/search/compare       : PostgreSQL vs ES 비교

    :copyright: (c) 2024 by wizice.
    :license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks
from typing import Dict, Any, List, Optional
import logging
import time
import re
from datetime import datetime

from .timescaledb_manager_v2 import DatabaseConnectionManager
from .service_synonym import SynonymService, get_synonym_service
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

# 유사어 서비스 (지연 초기화)
synonym_service = None

router = APIRouter(
    prefix="/api/search",
    tags=["search-elasticsearch-experimental"],
    responses={404: {"description": "Not found"}},
)

# Elasticsearch 설정 (settings.py에서 가져오기)
from settings import settings

ES_IP = settings.ES_HOST
ES_PORT = settings.ES_PORT
INDEX_RULE = settings.ES_INDEX_RULE
INDEX_ARTICLE = settings.ES_INDEX_ARTICLE
INDEX_APPENDIX = settings.ES_INDEX_APPENDIX

# 전역 ES 클라이언트 (지연 초기화)
es_client = None
hanparse = None


def get_db_connection():
    """데이터베이스 연결 생성"""
    db_config = {
        'database': settings.DB_NAME,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
        'host': settings.DB_HOST,
        'port': settings.DB_PORT
    }
    return DatabaseConnectionManager(**db_config)


def init_synonym_service():
    """유사어 서비스 초기화 (지연 초기화)"""
    global synonym_service

    if synonym_service is not None:
        return synonym_service

    try:
        db_manager = get_db_connection()
        synonym_service = get_synonym_service(db_manager)
        logger.info("유사어 서비스 초기화 완료")
        return synonym_service
    except Exception as e:
        logger.error(f"유사어 서비스 초기화 실패: {e}")
        return None


def init_es_client():
    """Elasticsearch 클라이언트 초기화 (지연 초기화)"""
    global es_client, hanparse

    if es_client is not None:
        return es_client

    try:
        from lib_es_sev import LibEs
        from hanparse import HanParse

        es_client = LibEs(
            index=INDEX_RULE,
            doc_type="list",
            es_ip=ES_IP,
            es_port=ES_PORT
        )
        es_client.Log = logger
        hanparse = HanParse()

        logger.info(f"Elasticsearch client initialized: {ES_IP}:{ES_PORT}")
        return es_client
    except ImportError as e:
        logger.error(f"Elasticsearch libraries not installed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Elasticsearch is not configured. Please install required packages."
        )
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Elasticsearch connection failed: {str(e)}"
        )


@router.get("/es/health")
async def elasticsearch_health():
    """Elasticsearch 서버 상태 확인

    Returns:
        ES 클러스터 정보 및 인덱스 통계
    """
    try:
        client = init_es_client()

        # ES 서버 정보
        info = client.es.info()

        # 인덱스 통계
        rule_count = client.es.count(index=INDEX_RULE).get("count", 0)
        article_count = client.es.count(index=INDEX_ARTICLE).get("count", 0)

        # 클러스터 상태
        cluster_health = client.es.cluster.health()

        return {
            "success": True,
            "status": "healthy",
            "elasticsearch": {
                "cluster_name": info.get("cluster_name"),
                "version": info.get("version", {}).get("number"),
                "tagline": info.get("tagline")
            },
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ES health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Elasticsearch is not available: {str(e)}"
        )


@router.get("/es")
async def search_with_elasticsearch(
    q: str = Query(..., min_length=1, max_length=200, description="검색어"),
    search_type: str = Query("content", description="검색 타입: title, content, all, department, appendix"),
    limit: int = Query(50, ge=1, le=200, description="최대 결과 수"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    expand_synonyms: bool = Query(True, description="유사어 확장 검색 사용 여부")
):
    """Elasticsearch 기반 검색 (실험용)

    기존 /api/search와 동일한 API 포맷 유지

    Args:
        q: 검색어
        search_type: 검색 타입
            - title: 내규명 검색
            - content: 내규본문 검색 (형태소 분석)
            - all: 통합 검색
            - department: 담당부서 검색
            - appendix: 부록명 검색
        limit: 최대 결과 수
        page: 페이지 번호

    Returns:
        검색 결과 (기존 API와 동일한 포맷)
    """
    try:
        start_time = time.time()

        logger.info(f"[ES Search] q='{q}', type='{search_type}', limit={limit}, page={page}")

        # ES 클라이언트 초기화
        client = init_es_client()
        offset = (page - 1) * limit

        # 검색 타입 검증
        valid_types = ['title', 'content', 'all', 'department', 'appendix']
        if search_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search_type. Must be one of {valid_types}"
            )

        # 검색 쿼리 구성
        if search_type == 'title':
            # 내규명 검색: 와일드카드 사용
            # ES 규정명 필드가 text 타입이므로 keyword 서브필드로 전체 문자열 매칭
            # 규정명에 문자 사이 공백이 있을 수 있음 (예: "여  비  규  정")
            # 각 문자 사이에 와일드카드 삽입하여 매칭
            q_chars = list(q.replace(' ', ''))
            if len(q_chars) > 1:
                wild_pattern = '*'.join(q_chars)
                q_string = f'+규정명.keyword:*{wild_pattern}*'
            else:
                q_string = f'+규정명.keyword:*{q}*'

        elif search_type == 'content':
            # 내규본문 검색: 형태소 분석 사용
            keywords = hanparse.parse(q)
            logger.debug(f"[ES Search] Parsed keywords: {keywords}")

            # 유사어 확장 처리
            synonym_expansion_info = {}
            if expand_synonyms:
                syn_service = init_synonym_service()
                if syn_service:
                    expansion_result = syn_service.expand_query(keywords)
                    synonym_expansion_info = expansion_result.get('expansion_info', {})
                    if expansion_result.get('was_expanded'):
                        logger.info(f"[ES Search] 유사어 확장: {keywords} -> {len(expansion_result['expanded_terms'])}개")

            # tags 필드에서 모든 키워드 검색 (AND 조건)
            query_parts = [f"+tags:{kw}" for kw in keywords]
            q_string = " ".join(query_parts)

        elif search_type == 'department':
            # 담당부서 검색: 담당부서 필드에서 와일드카드 검색
            q_string = f'+담당부서:*{q}*'

        elif search_type == 'appendix':
            # 부록명 검색: 부록명목록 필드에서 와일드카드 검색
            q_string = f'+부록명목록:*{q}*'

        else:  # all
            # 통합 검색: 규정명, 담당부서, 부록명, tags 모두 검색
            keywords = hanparse.parse(q)
            # 통합 검색은 query string으로 처리하되, tags는 간단히 포함
            q_string = f'규정명:*{q}* OR 담당부서:*{q}* OR 부록명목록:*{q}* OR tags:{q}'

        logger.debug(f"[ES Search] Query string: {q_string}")

        # Elasticsearch 검색 실행
        # content 검색은 match 쿼리 사용 (형태소 분석 결과 검색을 위해)
        if search_type == 'content':
            # match 쿼리 사용: tags 필드에서 검색 (AND 방식)
            query_text = ' '.join(keywords)

            # AND 검색: 모든 키워드가 포함되어야 함
            # 유사어 확장 시: 각 키워드에 대해 유사어들은 OR, 키워드 그룹 간에는 AND
            must_clauses = []
            for keyword in keywords:
                if expand_synonyms and keyword in synonym_expansion_info:
                    # 유사어가 있는 경우: OR로 확장
                    synonyms = synonym_expansion_info[keyword].get('synonyms', [keyword])
                    should_clauses = []
                    for synonym in synonyms:
                        should_clauses.append({
                            "match": {"tags": synonym}
                        })
                    must_clauses.append({
                        "bool": {
                            "should": should_clauses,
                            "minimum_should_match": 1
                        }
                    })
                else:
                    # 유사어가 없는 경우: 원본 키워드만 사용
                    must_clauses.append({
                        "match": {
                            "tags": keyword
                        }
                    })

            results = client.es.search(
                index=INDEX_RULE,
                from_=offset,
                size=limit,
                # content 검색은 관련도 순으로 정렬 (score 사용)
                body={
                    "query": {
                        "bool": {
                            "must": must_clauses,  # 모든 키워드 포함 필수 (AND)
                            "should": [
                                # 구문 매칭 (연속된 단어 매칭 시 높은 점수)
                                {
                                    "match_phrase": {
                                        "tags": {
                                            "query": query_text,
                                            "slop": 2,
                                            "boost": 2.0
                                        }
                                    }
                                }
                            ]
                        }
                    },
                    "sort": [
                        {"_score": {"order": "desc"}}
                    ]
                }
            )
        elif search_type == 'all':
            # 통합 검색: 규정 인덱스 + 부록 내용 검색
            # 1. 규정 인덱스 검색
            results = client.search_q(
                q_string=q_string,
                index=INDEX_RULE,
                from_=offset,
                size=limit,
                sort=None,
                debug=False
            )

            # 2. 부록 내용(pdf_text/tags) 검색 - 부록에서 매칭되는 규정 찾기
            keywords = hanparse.parse(q)
            appendix_must_clauses = []
            for keyword in keywords:
                appendix_must_clauses.append({
                    "bool": {
                        "should": [
                            {"match": {"tags": keyword}},
                            {"wildcard": {"wzappendixname": {"value": f"*{keyword}*", "case_insensitive": True}}}
                        ],
                        "minimum_should_match": 1
                    }
                })

            try:
                appendix_results = client.es.search(
                    index=INDEX_APPENDIX,
                    size=100,
                    body={
                        "query": {
                            "bool": {
                                "must": appendix_must_clauses
                            }
                        },
                        "sort": [{"_score": {"order": "desc"}}]
                    }
                )

                # 부록에서 매칭된 규정 seq 수집 (점수와 함께)
                appendix_matched_rules = {}  # {규정표기명: {"score": max_score, "appendix_names": [...]}}
                for hit in appendix_results.get("hits", {}).get("hits", []):
                    source = hit.get("_source", {})
                    pubno = source.get("규정표기명", "").rstrip('.')
                    score = hit.get("_score", 0)
                    appendix_name = source.get("wzappendixname", "")

                    if pubno:
                        if pubno not in appendix_matched_rules:
                            appendix_matched_rules[pubno] = {"score": score, "appendix_names": [appendix_name]}
                        else:
                            appendix_matched_rules[pubno]["score"] = max(appendix_matched_rules[pubno]["score"], score)
                            if appendix_name not in appendix_matched_rules[pubno]["appendix_names"]:
                                appendix_matched_rules[pubno]["appendix_names"].append(appendix_name)

                if appendix_matched_rules:
                    logger.info(f"[ES Search] 통합검색 - 부록에서 {len(appendix_matched_rules)}개 규정 매칭됨")

            except Exception as e:
                logger.warning(f"[ES Search] 부록 검색 오류 (무시): {e}")
                appendix_matched_rules = {}

        else:
            # 다른 검색 타입은 query string 사용
            appendix_matched_rules = {}
            results = client.search_q(
                q_string=q_string,
                index=INDEX_RULE,
                from_=offset,
                size=limit,
                sort=None,
                debug=False
            )

        # 결과 파싱
        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {})

        # ES 7.x+ 호환 (total이 dict인 경우)
        if isinstance(total, dict):
            total_count = total.get("value", 0)
        else:
            total_count = total

        # 결과 포맷팅 (기존 API와 동일한 포맷)
        # 중복 제거: 같은 규정표기명의 경우 seq가 큰 것(최신)만 유지
        unique_results = {}
        for hit in hits:
            source = hit.get("_source", {})
            seq = source.get('seq', '0')

            # pubno를 _id에서 추출 (규정표기명 필드는 잘못된 데이터가 있음)
            # _id 형식: "6_8" → pubno: "6-8"
            doc_id = hit.get("_id", "")
            pubno_code = doc_id.replace("_", "-")
            regulation_name = re.sub(r'\s+', ' ', source.get('규정명', '')).strip()

            result = {
                'id': seq,
                'name': regulation_name,  # 규정명
                'pubno': pubno_code,  # 규정 코드 (N-M 형식)
                'department': source.get('담당부서'),
                'establishedDate': source.get('제정일'),
                'executionDate': source.get('최종개정일'),
                'revisionDate': source.get('최종검토일'),
                'filePath': source.get('json_파일경로'),
                'matchType': search_type,
                'score': hit.get('_score')  # ES 관련도 점수 추가
            }

            # 같은 pubno가 있으면 seq가 더 큰 것만 유지
            if pubno_code in unique_results:
                existing_seq = unique_results[pubno_code]['id']
                if seq > existing_seq:
                    unique_results[pubno_code] = result
            else:
                unique_results[pubno_code] = result

        search_results = list(unique_results.values())

        # all 검색 시 부록 매칭 정보 적용
        if search_type == 'all' and appendix_matched_rules:
            # 기존 결과에 부록 매칭 정보 추가 및 점수 부스트
            for result in search_results:
                pubno = result.get('pubno', '')
                if pubno in appendix_matched_rules:
                    appendix_info = appendix_matched_rules[pubno]
                    original_score = result.get('score') or 0
                    # 부록 점수의 20%를 문서 점수에 추가
                    result['score'] = original_score + (appendix_info['score'] * 0.2)
                    result['original_score'] = original_score
                    result['appendix_boost'] = appendix_info['score'] * 0.2
                    result['matching_appendix'] = appendix_info['appendix_names'][:3]  # 최대 3개
                    # appendix_matched_rules에서 처리됨 표시
                    appendix_matched_rules[pubno]['added'] = True

            # 부록에서만 발견된 규정 추가 (기존 결과에 없는 경우)
            existing_pubnos = {r['pubno'] for r in search_results}
            for pubno, appendix_info in appendix_matched_rules.items():
                if pubno not in existing_pubnos and not appendix_info.get('added'):
                    # 규정 정보 조회하여 추가
                    try:
                        # pubno는 "6-8" 형식, _id는 "6_8" 형식
                        rule_doc_id = pubno.replace("-", "_")
                        rule_result = client.es.search(
                            index=INDEX_RULE,
                            size=1,
                            body={
                                "query": {
                                    "ids": {"values": [rule_doc_id]}
                                }
                            }
                        )
                        rule_hits = rule_result.get("hits", {}).get("hits", [])
                        if rule_hits:
                            source = rule_hits[0].get("_source", {})
                            seq = source.get('seq', '0')
                            regulation_name = re.sub(r'\s+', ' ', source.get('규정명', '')).strip()

                            search_results.append({
                                'id': seq,
                                'name': regulation_name,
                                'pubno': pubno,
                                'department': source.get('담당부서'),
                                'establishedDate': source.get('제정일'),
                                'executionDate': source.get('최종개정일'),
                                'revisionDate': source.get('최종검토일'),
                                'filePath': source.get('json_파일경로'),
                                'matchType': 'appendix_content',  # 부록 내용에서 발견됨 표시
                                'score': appendix_info['score'] * 0.2,
                                'appendix_boost': appendix_info['score'] * 0.2,
                                'matching_appendix': appendix_info['appendix_names'][:3]
                            })
                    except Exception as e:
                        logger.warning(f"[ES Search] 부록 매칭 규정 조회 실패 ({pubno}): {e}")

            # 부스트된 점수로 재정렬
            search_results.sort(key=lambda x: x.get('score') or 0, reverse=True)
            logger.debug(f"[ES Search] 통합검색 - 부록 부스트 적용 후 {len(search_results)}개 결과")

        # content 검색 시 Article 인덱스에서 조 정보 가져오기
        if search_type == 'content':
            # Article 인덱스 검색하여 매칭된 조 찾기 (AND 방식)
            article_query_text = ' '.join(keywords)

            # AND 검색: 모든 키워드가 포함되어야 함
            # 유사어 확장 적용 (Rule 검색과 동일한 방식)
            article_must_clauses = []
            for keyword in keywords:
                if expand_synonyms and keyword in synonym_expansion_info:
                    # 유사어가 있는 경우: OR로 확장
                    synonyms = synonym_expansion_info[keyword].get('synonyms', [keyword])
                    should_clauses = []
                    for synonym in synonyms:
                        should_clauses.append({
                            "match": {"tags": synonym}
                        })
                    article_must_clauses.append({
                        "bool": {
                            "should": should_clauses,
                            "minimum_should_match": 1
                        }
                    })
                else:
                    article_must_clauses.append({
                        "match": {
                            "tags": keyword
                        }
                    })

            article_results = client.es.search(
                index=INDEX_ARTICLE,
                size=500,  # 충분한 조문 가져오기
                body={
                    "query": {
                        "bool": {
                            "must": article_must_clauses,  # 모든 키워드 포함 필수 (AND)
                            "should": [
                                {
                                    "match_phrase": {
                                        "tags": {
                                            "query": article_query_text,
                                            "slop": 2,
                                            "boost": 2.0
                                        }
                                    }
                                }
                            ]
                        }
                    },
                    "sort": [
                        {"_score": {"order": "desc"}},
                        {"조문seq": {"order": "asc"}}
                    ]
                }
            )

            # 규정seq별로 매칭된 조 목록 생성
            articles_by_rule = {}
            for article_hit in article_results.get("hits", {}).get("hits", []):
                article_source = article_hit.get("_source", {})
                rule_seq = article_source.get('규정seq', '')

                if rule_seq not in articles_by_rule:
                    articles_by_rule[rule_seq] = []

                articles_by_rule[rule_seq].append({
                    'article_seq': article_source.get('조문seq', 0),
                    'article_number': article_source.get('조문번호', ''),
                    'article_content': article_source.get('조문내용', ''),
                    'article_level': article_source.get('조문레벨', 0),
                    'score': article_hit.get('_score', 0)
                })

            # 각 규정 결과에 매칭된 조 목록 추가
            for result in search_results:
                rule_seq = str(result.get('id', ''))
                matching_articles = articles_by_rule.get(rule_seq, [])

                # 스코어 기준 상위 3개 조만 포함 (60% threshold 적용)
                if matching_articles:
                    max_article_score = max([a['score'] for a in matching_articles])
                    threshold = max_article_score * 0.6
                    matching_articles = [a for a in matching_articles if a['score'] >= threshold]
                    matching_articles = matching_articles[:3]  # 최대 3개만

                # 조 제목 추출 및 표시 형식 생성
                for article in matching_articles:
                    # 조 내용에서 제목 부분 추출
                    content = article['article_content']
                    article_title = ''

                    # 패턴 1: 괄호 안의 내용 (예: "(목적)")
                    match = re.search(r'^\(([^)]+)\)', content)
                    if match:
                        article_title = f"({match.group(1)})"
                    # 패턴 2: 괄호가 없으면 내용의 첫 30자 사용
                    elif content and len(content) > 5:
                        preview = content[:30]
                        if len(content) > 30:
                            preview += '...'
                        article_title = preview

                    # 표시 형식: "규정코드 규정명:조번호 제목"
                    # 예: "1.1.1. 정확한 환자 확인:제1조 (목적)"
                    display_text = f"{result['pubno']} {result['name']}:{article['article_number']} {article_title}".strip()
                    article['display_text'] = display_text

                result['matching_articles'] = matching_articles
                result['matching_article_count'] = len(articles_by_rule.get(rule_seq, []))

            # 조문 점수를 문서 점수에 반영하여 재정렬
            # 정확한 구문이 조문에서 발견되면 해당 문서가 상위로 올라가야 함
            for result in search_results:
                matching_articles = result.get('matching_articles', [])
                if matching_articles:
                    # 최고 조문 점수를 문서 점수에 가중치 적용하여 합산
                    max_article_score = max([a.get('score', 0) for a in matching_articles])
                    original_score = result.get('score', 0) or 0
                    # 조문 점수의 30%를 문서 점수에 추가 (조문 점수가 높으면 문서 순위 상승)
                    result['score'] = original_score + (max_article_score * 0.3)
                    result['original_score'] = original_score
                    result['article_boost'] = max_article_score * 0.3

            # 결합된 점수로 재정렬
            search_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            logger.debug(f"[ES Search] Re-sorted by combined score (doc + article*0.3)")

        # content 검색 시 최고 score의 60% 이상만 필터링
        if search_type == 'content' and search_results:
            # 최고 score 찾기
            max_score = max([r.get('score', 0) or 0 for r in search_results])

            if max_score > 0:
                # 최고 score의 60% 계산
                relative_threshold = max_score * 0.6

                # 필터링 전 개수
                before_count = len(search_results)

                # 최고 score의 60% 이상인 결과만 유지
                search_results = [
                    r for r in search_results
                    if (r.get('score', 0) or 0) >= relative_threshold
                ]

                # 필터링 후 개수
                after_count = len(search_results)

                logger.info(f"[ES Search] Score filtering: max={max_score:.2f}, threshold={relative_threshold:.2f} (60% of max), {before_count} → {after_count} results")

        elapsed_time = (time.time() - start_time) * 1000  # ms

        logger.info(f"[ES Search] Found {total_count} results in {elapsed_time:.2f}ms")

        # 응답 생성
        response = {
            "success": True,
            "results": search_results,
            "total": total_count,
            "page": page,
            "limit": limit,
            "search_type": search_type,
            "query": q,
            "engine": "elasticsearch",
            "took_ms": round(elapsed_time, 2),
            "es_took_ms": results.get("took", 0)
        }

        # content 검색 시 유사어 확장 정보 추가
        if search_type == 'content':
            response["expand_synonyms"] = expand_synonyms
            if expand_synonyms and synonym_expansion_info:
                response["synonym_expansion"] = {
                    "was_expanded": True,
                    "expansions": {
                        term: {
                            "group_name": info.get('group_name', ''),
                            "synonyms": info.get('synonyms', [])
                        }
                        for term, info in synonym_expansion_info.items()
                    }
                }
            else:
                response["synonym_expansion"] = {
                    "was_expanded": False,
                    "expansions": {}
                }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ES Search] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/compare")
async def compare_search_engines(
    q: str = Query(..., min_length=1, max_length=200, description="검색어"),
    search_type: str = Query("content", description="검색 타입: title, content, all"),
    limit: int = Query(20, ge=1, le=100, description="최대 결과 수")
):
    """PostgreSQL vs Elasticsearch 검색 결과 비교 (개발자용)

    동일한 검색어로 두 엔진을 동시 실행하여 결과 비교

    Args:
        q: 검색어
        search_type: 검색 타입
        limit: 결과 수 제한

    Returns:
        {
            "query": "검색어",
            "postgres": {...},
            "elasticsearch": {...},
            "analysis": {...}
        }
    """
    try:
        logger.info(f"[Compare] Comparing search engines for query: '{q}'")

        # PostgreSQL 검색
        postgres_start = time.time()
        postgres_result = await _search_with_postgres(q, search_type, limit, page=1)
        postgres_time = (time.time() - postgres_start) * 1000

        # Elasticsearch 검색
        es_start = time.time()
        try:
            es_result = await search_with_elasticsearch(q, search_type, limit, page=1)
            es_time = (time.time() - es_start) * 1000
            es_error = None
        except Exception as e:
            es_result = None
            es_time = (time.time() - es_start) * 1000
            es_error = str(e)
            logger.error(f"[Compare] ES failed: {e}")

        # 분석
        analysis = {
            "speed_comparison": {
                "postgres_ms": round(postgres_time, 2),
                "elasticsearch_ms": round(es_time, 2) if es_result else None,
                "improvement": f"{postgres_time / es_time:.1f}x faster" if es_result and es_time > 0 else "N/A"
            },
            "result_comparison": {
                "postgres_count": postgres_result.get("total", 0),
                "elasticsearch_count": es_result.get("total", 0) if es_result else 0,
                "difference": (es_result.get("total", 0) if es_result else 0) - postgres_result.get("total", 0)
            },
            "elasticsearch_status": "success" if es_result else "failed",
            "elasticsearch_error": es_error
        }

        return {
            "success": True,
            "query": q,
            "search_type": search_type,
            "postgres": {
                "engine": "postgresql",
                "took_ms": round(postgres_time, 2),
                "total": postgres_result.get("total", 0),
                "results": postgres_result.get("results", [])[:5]  # 처음 5개만
            },
            "elasticsearch": {
                "engine": "elasticsearch",
                "took_ms": round(es_time, 2) if es_result else None,
                "total": es_result.get("total", 0) if es_result else 0,
                "results": es_result.get("results", [])[:5] if es_result else [],
                "error": es_error
            },
            "analysis": analysis
        }

    except Exception as e:
        logger.error(f"[Compare] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"비교 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/es/articles")
async def search_articles(
    q: str = Query(..., min_length=1, max_length=200, description="검색어"),
    limit: int = Query(50, ge=1, le=200, description="최대 결과 수"),
    page: int = Query(1, ge=1, description="페이지 번호")
):
    """조문 단위 검색 (Article 인덱스)

    내규 본문을 조 단위로 검색하여, 어느 조에서 검색어가 나타나는지 보여줍니다.

    Args:
        q: 검색어
        limit: 최대 결과 수
        page: 페이지 번호

    Returns:
        {
            "success": true,
            "results": [
                {
                    "rule_seq": "1003",
                    "rule_name": "4.3.9. 의약품 회수",
                    "article_seq": 2,
                    "article_number": "제1조",
                    "article_content": "(목적) 의약품의 안전성...",
                    "article_level": 1,
                    "department": "약무국",
                    "score": 6.4167
                }
            ],
            "total": 2801,
            "page": 1,
            "limit": 50
        }
    """
    try:
        start_time = time.time()

        logger.info(f"[Article Search] q='{q}', limit={limit}, page={page}")

        # ES 클라이언트 초기화
        client = init_es_client()
        offset = (page - 1) * limit

        # 형태소 분석
        keywords = hanparse.parse(q)
        logger.debug(f"[Article Search] Parsed keywords: {keywords}")

        # Article 인덱스 검색 (AND 방식)
        query_text = ' '.join(keywords)

        # AND 검색: 모든 키워드가 포함되어야 함
        must_clauses = []
        for keyword in keywords:
            must_clauses.append({
                "match": {
                    "tags": keyword
                }
            })

        results = client.es.search(
            index=INDEX_ARTICLE,
            from_=offset,
            size=limit * 2,  # 중복 제거 고려하여 2배 가져오기
            body={
                "query": {
                    "bool": {
                        "must": must_clauses,  # 모든 키워드 포함 필수 (AND)
                        "should": [
                            {
                                "match_phrase": {
                                    "tags": {
                                        "query": query_text,
                                        "slop": 2,
                                        "boost": 2.0
                                    }
                                }
                            }
                        ]
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"규정명.keyword": {"order": "asc"}},
                    {"조문seq": {"order": "asc"}}
                ]
            }
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
            source = hit.get("_source", {})
            score = hit.get("_score", 0)

            # 규정명에서 코드와 이름 분리 (예: "1.1.1. 정확한 환자 확인" → "1.1.1.", "정확한 환자 확인")
            full_rule_name = source.get('규정명', '')
            rule_code = ''
            rule_name = full_rule_name

            match = re.match(r'^([\d.]+)\.?\s*(.*)$', full_rule_name)
            if match:
                rule_code = match.group(1).rstrip('.')  # trailing dot 제거
                rule_name = match.group(2).strip()

            # 조 제목 추출
            article_content = source.get('조문내용', '')
            article_title = ''

            # 패턴 1: 괄호 안의 내용 (예: "(목적)")
            title_match = re.search(r'^\(([^)]+)\)', article_content)
            if title_match:
                article_title = f"({title_match.group(1)})"
            # 패턴 2: 괄호가 없으면 내용의 첫 30자 사용
            elif article_content and len(article_content) > 5:
                preview = article_content[:30]
                if len(article_content) > 30:
                    preview += '...'
                article_title = preview

            # 표시 형식: "규정코드 규정명:조번호 제목"
            display_text = f"{rule_code} {rule_name}:{source.get('조문번호', '')} {article_title}".strip()

            result = {
                "rule_seq": source.get('규정seq', ''),
                "rule_code": rule_code,
                "rule_name": rule_name,
                "article_seq": source.get('조문seq', 0),
                "article_number": source.get('조문번호', ''),
                "article_content": article_content,
                "article_level": source.get('조문레벨', 0),
                "department": source.get('담당부서', ''),
                "score": score,
                "display_text": display_text
            }
            search_results.append(result)

        # 스코어 필터링 (60% of max)
        if search_results:
            max_score = max([r.get('score', 0) or 0 for r in search_results])

            if max_score > 0:
                relative_threshold = max_score * 0.6
                before_count = len(search_results)

                search_results = [
                    r for r in search_results
                    if (r.get('score', 0) or 0) >= relative_threshold
                ]

                after_count = len(search_results)
                logger.info(f"[Article Search] Score filtering: max={max_score:.2f}, threshold={relative_threshold:.2f} (60% of max), {before_count} → {after_count} results")

        # limit 적용
        search_results = search_results[:limit]

        elapsed_time = (time.time() - start_time) * 1000
        logger.info(f"[Article Search] Found {total_count} total, returned {len(search_results)} results in {elapsed_time:.2f}ms")

        return {
            "success": True,
            "results": search_results,
            "total": total_count,
            "page": page,
            "limit": limit,
            "query": q,
            "engine": "elasticsearch-article",
            "took_ms": round(elapsed_time, 2)
        }

    except Exception as e:
        logger.error(f"[Article Search] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"조문 검색 중 오류가 발생했습니다: {str(e)}"
        )


async def _search_with_postgres(q: str, search_type: str, limit: int, page: int):
    """PostgreSQL 검색 (기존 로직 복사)"""
    try:
        db_manager = get_db_connection()
        offset = (page - 1) * limit

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                search_pattern = f'%{q}%'

                if search_type == 'title':
                    query = """
                        SELECT
                            wzruleseq, wzname, wzpubno, wzmgrdptnm,
                            wzestabdate, wzexecdate, wzlastrevdate,
                            wzcontent_path, 'title' as match_type
                        FROM wz_rule
                        WHERE wzNewFlag = '현행' AND wzname ILIKE %s
                        ORDER BY wzname
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(query, (search_pattern, limit, offset))

                elif search_type == 'content':
                    query = """
                        SELECT
                            wzruleseq, wzname, wzpubno, wzmgrdptnm,
                            wzestabdate, wzexecdate, wzlastrevdate,
                            wzcontent_path, 'content' as match_type
                        FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND index_status = 'completed'
                        AND content_text ILIKE %s
                        ORDER BY
                            CASE WHEN wzname ILIKE %s THEN 1 ELSE 2 END,
                            wzname
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(query, (search_pattern, search_pattern, limit, offset))

                else:  # all
                    query = """
                        SELECT
                            wzruleseq, wzname, wzpubno, wzmgrdptnm,
                            wzestabdate, wzexecdate, wzlastrevdate,
                            wzcontent_path,
                            CASE
                                WHEN wzname ILIKE %s THEN 'title'
                                WHEN content_text ILIKE %s THEN 'content'
                                ELSE 'other'
                            END as match_type
                        FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND (
                            wzname ILIKE %s
                            OR (index_status = 'completed' AND content_text ILIKE %s)
                        )
                        ORDER BY
                            CASE
                                WHEN wzname ILIKE %s THEN 1
                                WHEN content_text ILIKE %s THEN 2
                                ELSE 3
                            END,
                            wzname
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(query, (
                        search_pattern, search_pattern,
                        search_pattern, search_pattern,
                        search_pattern, search_pattern,
                        limit, offset
                    ))

                results = cur.fetchall()

                # 전체 결과 수 조회
                if search_type == 'title':
                    count_query = "SELECT COUNT(*) FROM wz_rule WHERE wzNewFlag = '현행' AND wzname ILIKE %s"
                    cur.execute(count_query, (search_pattern,))
                elif search_type == 'content':
                    count_query = """
                        SELECT COUNT(*) FROM wz_rule
                        WHERE wzNewFlag = '현행' AND index_status = 'completed'
                        AND content_text ILIKE %s
                    """
                    cur.execute(count_query, (search_pattern,))
                else:  # all
                    count_query = """
                        SELECT COUNT(*) FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND (wzname ILIKE %s OR (index_status = 'completed' AND content_text ILIKE %s))
                    """
                    cur.execute(count_query, (search_pattern, search_pattern))

                total_count = cur.fetchone()[0]

                # 결과 포맷팅
                search_results = []
                for row in results:
                    result = {
                        'id': row[0],
                        'name': row[1],
                        'pubno': row[2],
                        'department': row[3],
                        'establishedDate': row[4],
                        'executionDate': row[5],
                        'revisionDate': row[6],
                        'filePath': row[7],
                        'matchType': row[8]
                    }
                    search_results.append(result)

                return {
                    "success": True,
                    "results": search_results,
                    "total": total_count,
                    "page": page,
                    "limit": limit,
                    "search_type": search_type,
                    "query": q
                }

    except Exception as e:
        logger.error(f"PostgreSQL search error: {e}")
        raise


@router.post("/pdf/extract-appendix")
async def extract_appendix_pdf_texts():
    """
    부록 PDF 파일에서 텍스트 추출하여 저장 (www/static/pdf)

    Returns:
        추출 결과 정보
    """
    from pathlib import Path
    import sys

    # pdf_extractor 모듈 임포트
    sys.path.insert(0, str(Path(__file__).parent.parent / 'applib' / 'utils'))
    from pdf_extractor import PDFTextExtractor

    try:
        pdf_path = Path(settings.WWW_STATIC_PDF_DIR)
        output_path = Path(f"{settings.WWW_STATIC_DIR}/pdf_txt")

        # 출력 디렉토리 생성
        output_path.mkdir(parents=True, exist_ok=True)

        # PDF 추출기 초기화
        extractor = PDFTextExtractor()

        if not extractor.supported_libraries:
            raise HTTPException(
                status_code=500,
                detail="No PDF extraction library available. Install: pip install pymupdf"
            )

        # 모든 PDF 파일 찾기
        pdf_files = list(pdf_path.glob("*.pdf"))

        if not pdf_files:
            return {
                "success": True,
                "message": "No PDF files found",
                "processed": 0,
                "results": []
            }

        results = []
        success_count = 0
        error_count = 0

        # 각 PDF 처리
        for pdf_file in pdf_files:
            try:
                # 출력 파일 경로 생성
                txt_file = output_path / f"{pdf_file.stem}.txt"

                # 텍스트 추출 및 저장
                result = extractor.extract_and_save(
                    str(pdf_file),
                    str(txt_file),
                    method='auto'
                )

                if result['success']:
                    success_count += 1
                    logger.info(f"✓ Extracted: {pdf_file.name} ({result['text_length']} chars)")
                else:
                    error_count += 1
                    logger.error(f"✗ Failed: {pdf_file.name} - {result.get('error', 'Unknown error')}")

                results.append({
                    "filename": pdf_file.name,
                    "success": result['success'],
                    "text_length": result['text_length'],
                    "output_file": txt_file.name if result['success'] else None,
                    "error": result.get('error')
                })

            except Exception as e:
                error_count += 1
                logger.error(f"✗ Exception processing {pdf_file.name}: {e}")
                results.append({
                    "filename": pdf_file.name,
                    "success": False,
                    "text_length": 0,
                    "output_file": None,
                    "error": str(e)
                })

        return {
            "success": True,
            "message": f"Appendix PDF extraction completed: {success_count} success, {error_count} errors",
            "total_files": len(pdf_files),
            "success_count": success_count,
            "error_count": error_count,
            "library_used": extractor.supported_libraries[0] if extractor.supported_libraries else None,
            "results": results
        }

    except Exception as e:
        logger.error(f"Appendix PDF extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf/extract-all")
async def extract_all_pdf_texts():
    """
    모든 PDF 파일에서 텍스트 추출하여 저장 (fastapi/applib/pdf)

    Returns:
        추출 결과 정보
    """
    from pathlib import Path
    import sys

    # pdf_extractor 모듈 임포트
    sys.path.insert(0, str(Path(__file__).parent.parent / 'applib' / 'utils'))
    from pdf_extractor import PDFTextExtractor

    try:
        pdf_path = Path(settings.PDF_DIR)
        output_path = Path(f"{settings.APPLIB_DIR}/pdf_txt")

        # 출력 디렉토리 생성
        output_path.mkdir(parents=True, exist_ok=True)

        # PDF 추출기 초기화
        extractor = PDFTextExtractor()

        if not extractor.supported_libraries:
            raise HTTPException(
                status_code=500,
                detail="No PDF extraction library available. Install: pip install pymupdf"
            )

        # 모든 PDF 파일 찾기
        pdf_files = list(pdf_path.glob("*.pdf"))

        if not pdf_files:
            return {
                "success": True,
                "message": "No PDF files found",
                "processed": 0,
                "results": []
            }

        results = []
        success_count = 0
        error_count = 0

        # 각 PDF 처리
        for pdf_file in pdf_files:
            try:
                # 출력 파일 경로 생성
                txt_file = output_path / f"{pdf_file.stem}.txt"

                # 텍스트 추출 및 저장
                result = extractor.extract_and_save(
                    str(pdf_file),
                    str(txt_file),
                    method='auto'
                )

                if result['success']:
                    success_count += 1
                    logger.info(f"✓ Extracted: {pdf_file.name} ({result['text_length']} chars)")
                else:
                    error_count += 1
                    logger.error(f"✗ Failed: {pdf_file.name} - {result.get('error', 'Unknown error')}")

                results.append({
                    "filename": pdf_file.name,
                    "success": result['success'],
                    "text_length": result['text_length'],
                    "output_file": txt_file.name if result['success'] else None,
                    "error": result.get('error')
                })

            except Exception as e:
                error_count += 1
                logger.error(f"✗ Exception processing {pdf_file.name}: {e}")
                results.append({
                    "filename": pdf_file.name,
                    "success": False,
                    "text_length": 0,
                    "output_file": None,
                    "error": str(e)
                })

        return {
            "success": True,
            "message": f"PDF extraction completed: {success_count} success, {error_count} errors",
            "total_files": len(pdf_files),
            "success_count": success_count,
            "error_count": error_count,
            "library_used": extractor.supported_libraries[0] if extractor.supported_libraries else None,
            "results": results
        }

    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/es/appendix")
async def search_appendix(
    q: str = Query(..., min_length=1, max_length=200, description="검색어"),
    search_type: str = Query("all", description="검색 타입: name(제목), content(내용), all(통합)"),
    limit: int = Query(50, ge=1, le=200, description="최대 결과 수"),
    page: int = Query(1, ge=1, description="페이지 번호")
):
    """
    부록 검색 (제목/내용 분리 검색)

    search_type:
    - name: 부록 제목에서만 검색 (wzappendixname)
    - content: 부록 내용(PDF 텍스트)에서만 검색 (pdf_text tags)
    - all: 제목 + 내용 통합 검색 (제목에 가중치 부여)
    """
    try:
        # ES 클라이언트 초기화
        client = init_es_client()

        # 형태소 분석
        keywords = hanparse.parse(q)
        logger.debug(f"[Appendix Search] Keywords: {keywords}, Type: {search_type}")

        # 페이징 계산
        offset = (page - 1) * limit

        # 검색 타입별 쿼리 구성
        if search_type == "name":
            # 제목 검색: wzappendixname 필드에서 wildcard 검색
            # (한국어 analyzer가 없으므로 wildcard 사용)
            must_clauses = []
            for keyword in keywords:
                must_clauses.append({
                    "wildcard": {
                        "wzappendixname": {
                            "value": f"*{keyword}*",
                            "case_insensitive": True
                        }
                    }
                })

            query_body = {
                "query": {
                    "bool": {
                        "must": must_clauses
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"wzappendixname.keyword": {"order": "asc"}}
                ]
            }

        elif search_type == "content":
            # 내용 검색: pdf_text의 tags 필드에서 검색
            must_clauses = []
            for keyword in keywords:
                must_clauses.append({
                    "match": {
                        "tags": keyword
                    }
                })

            # 스페이스로 구분된 원본 단어들 (형태소 분석 전)
            original_terms = [term.strip() for term in q.split() if term.strip()]

            # should 절: 정확한 구문 매칭에 높은 가중치
            should_clauses = [
                # pdf_text 원본에서 정확한 구문 매칭 (최고 우선순위)
                {
                    "match_phrase": {
                        "pdf_text": {
                            "query": q,
                            "slop": 0,
                            "boost": 10.0
                        }
                    }
                },
                # pdf_text에서 느슨한 구문 매칭
                {
                    "match_phrase": {
                        "pdf_text": {
                            "query": q,
                            "slop": 3,
                            "boost": 5.0
                        }
                    }
                },
                # tags에서 구문 매칭
                {
                    "match_phrase": {
                        "tags": {
                            "query": ' '.join(keywords),
                            "slop": 2,
                            "boost": 3.0
                        }
                    }
                }
            ]

            # 원본 단어들 각각이 pdf_text에 포함되면 추가 점수
            for term in original_terms:
                if len(term) >= 2:  # 2글자 이상만
                    should_clauses.append({
                        "match": {
                            "pdf_text": {
                                "query": term,
                                "boost": 1.5
                            }
                        }
                    })

            query_body = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "should": should_clauses
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"wzappendixname.keyword": {"order": "asc"}}
                ]
            }

        else:  # all
            # 통합 검색: 제목과 내용 모두 검색 (제목에 가중치 부여)
            must_clauses = []
            for keyword in keywords:
                must_clauses.append({
                    "bool": {
                        "should": [
                            {
                                "wildcard": {
                                    "wzappendixname": {
                                        "value": f"*{keyword}*",
                                        "boost": 3.0,  # 제목 매칭 시 높은 가중치
                                        "case_insensitive": True
                                    }
                                }
                            },
                            {
                                "match": {
                                    "tags": {
                                        "query": keyword,
                                        "boost": 1.0
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                })

            query_body = {
                "query": {
                    "bool": {
                        "must": must_clauses
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"wzappendixname.keyword": {"order": "asc"}}
                ]
            }

        # Elasticsearch 검색 실행
        results = client.es.search(
            index=INDEX_APPENDIX,
            from_=offset,
            size=limit,
            body=query_body
        )

        # 결과 파싱
        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {})

        if isinstance(total, dict):
            total_count = total.get("value", 0)
        else:
            total_count = total

        # 점수 필터링 (상위 60% 점수만 유지)
        if hits:
            max_score = hits[0].get("_score", 0)
            threshold = max_score * 0.6
            hits = [hit for hit in hits if hit.get("_score", 0) >= threshold]

        # 결과 포맷팅
        appendix_results = []
        for hit in hits:
            source = hit.get("_source", {})

            # PDF 텍스트 미리보기 (처음 200자)
            pdf_text = source.get("pdf_text", "")
            pdf_preview = pdf_text[:200] + "..." if len(pdf_text) > 200 else pdf_text

            # 규정표기명에서 trailing dot 제거 (summary_kbregulation.json과 일치시킴)
            raw_pubno = source.get("규정표기명", "")
            clean_pubno = raw_pubno.rstrip('.') if raw_pubno else ""

            appendix_results.append({
                "wzappendixseq": source.get("wzappendixseq"),
                "wzappendixname": source.get("wzappendixname"),
                "wzappendixno": source.get("wzappendixno"),
                "wzruleseq": source.get("wzruleseq"),
                "규정명": source.get("규정명"),
                "규정표기명": clean_pubno,  # trailing dot 제거
                "wzfiletype": source.get("wzfiletype"),
                "pdf_text_length": len(pdf_text),
                "pdf_preview": pdf_preview,
                "score": hit.get("_score"),
                "match_type": search_type,  # 검색 타입 추가 (name, content, all)
                # 표시 형식: "규정표기명 - 부록명"
                "display_text": f"{clean_pubno} - {source.get('wzappendixname', '')}".strip(" -")
            })

        return {
            "success": True,
            "results": appendix_results,
            "total": len(appendix_results),
            "total_before_filter": total_count,
            "page": page,
            "limit": limit,
            "search_type": search_type,
            "query": q,
            "keywords": keywords
        }

    except Exception as e:
        logger.error(f"Appendix search error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Elasticsearch 재색인 API (관리자용)
# ============================================================================

@router.post("/es/reindex/rule/{rule_seq}")
async def reindex_specific_rule(
    rule_seq: int = Path(..., description="규정 시퀀스 번호"),
    background_tasks: BackgroundTasks = None
):
    """
    특정 규정 재색인 (Rule + Articles)

    Args:
        rule_seq: 규정 시퀀스 번호

    Returns:
        재색인 작업 시작 확인 메시지
    """
    try:
        import sys
        import subprocess
        from pathlib import Path

        # index_sev.py 경로
        index_script = Path(f"{settings.FASTAPI_DIR}/index_sev.py")

        if not index_script.exists():
            raise HTTPException(status_code=500, detail="Index script not found")

        # 백그라운드에서 재색인 실행
        def run_reindex():
            try:
                # Rule 재색인
                subprocess.run([
                    sys.executable,
                    str(index_script),
                    "--cmd", "CRI",
                    "--index", INDEX_RULE,
                    "--rule_seq", str(rule_seq),
                    "--reindex", "REINDEX"
                ], check=True, capture_output=True, text=True)

                # Articles 재색인
                subprocess.run([
                    sys.executable,
                    str(index_script),
                    "--cmd", "CAI",
                    "--index", INDEX_ARTICLE,
                    "--rule_seq", str(rule_seq),
                    "--reindex", "REINDEX"
                ], check=True, capture_output=True, text=True)

                logger.info(f"Successfully reindexed rule {rule_seq}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Reindex failed for rule {rule_seq}: {e.stderr}")
            except Exception as e:
                logger.error(f"Reindex error for rule {rule_seq}: {e}")

        if background_tasks:
            background_tasks.add_task(run_reindex)
        else:
            # 동기 실행 (개발/테스트용)
            run_reindex()

        return {
            "success": True,
            "message": f"Reindexing started for rule {rule_seq}",
            "rule_seq": rule_seq,
            "indices": [INDEX_RULE, INDEX_ARTICLE]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindex API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/es/reindex/all-rules")
async def reindex_all_rules(background_tasks: BackgroundTasks = None):
    """
    모든 규정 재색인 (Rules only)

    Returns:
        재색인 작업 시작 확인 메시지
    """
    try:
        import sys
        import subprocess
        from pathlib import Path

        index_script = Path(f"{settings.FASTAPI_DIR}/index_sev.py")

        if not index_script.exists():
            raise HTTPException(status_code=500, detail="Index script not found")

        def run_reindex():
            try:
                result = subprocess.run([
                    sys.executable,
                    str(index_script),
                    "--cmd", "CRM",
                    "--index", INDEX_RULE
                ], check=True, capture_output=True, text=True)

                logger.info(f"Successfully reindexed all rules: {result.stdout}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Reindex all rules failed: {e.stderr}")
            except Exception as e:
                logger.error(f"Reindex all rules error: {e}")

        if background_tasks:
            background_tasks.add_task(run_reindex)
        else:
            run_reindex()

        return {
            "success": True,
            "message": "Reindexing started for all rules",
            "index": INDEX_RULE
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindex all rules API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/es/reindex/all-articles")
async def reindex_all_articles(background_tasks: BackgroundTasks = None):
    """
    모든 조문 재색인 (Articles only)

    Returns:
        재색인 작업 시작 확인 메시지
    """
    try:
        import sys
        import subprocess
        from pathlib import Path

        index_script = Path(f"{settings.FASTAPI_DIR}/index_sev.py")

        if not index_script.exists():
            raise HTTPException(status_code=500, detail="Index script not found")

        def run_reindex():
            try:
                result = subprocess.run([
                    sys.executable,
                    str(index_script),
                    "--cmd", "CAM",
                    "--index", INDEX_ARTICLE
                ], check=True, capture_output=True, text=True)

                logger.info(f"Successfully reindexed all articles: {result.stdout}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Reindex all articles failed: {e.stderr}")
            except Exception as e:
                logger.error(f"Reindex all articles error: {e}")

        if background_tasks:
            background_tasks.add_task(run_reindex)
        else:
            run_reindex()

        return {
            "success": True,
            "message": "Reindexing started for all articles",
            "index": INDEX_ARTICLE
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindex all articles API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/es/reindex/all-appendices")
async def reindex_all_appendices(background_tasks: BackgroundTasks = None):
    """
    모든 부록 재색인 (Appendices only)

    Returns:
        재색인 작업 시작 확인 메시지
    """
    try:
        import sys
        import subprocess
        from pathlib import Path

        index_script = Path(f"{settings.FASTAPI_DIR}/index_sev.py")

        if not index_script.exists():
            raise HTTPException(status_code=500, detail="Index script not found")

        def run_reindex():
            try:
                result = subprocess.run([
                    sys.executable,
                    str(index_script),
                    "--cmd", "CPAI",
                    "--index", INDEX_APPENDIX
                ], check=True, capture_output=True, text=True)

                logger.info(f"Successfully reindexed all appendices: {result.stdout}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Reindex all appendices failed: {e.stderr}")
            except Exception as e:
                logger.error(f"Reindex all appendices error: {e}")

        if background_tasks:
            background_tasks.add_task(run_reindex)
        else:
            run_reindex()

        return {
            "success": True,
            "message": "Reindexing started for all appendices",
            "index": INDEX_APPENDIX
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindex all appendices API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/es/reindex/all")
async def reindex_everything(background_tasks: BackgroundTasks = None):
    """
    전체 재색인 (Rules + Articles + Appendices)

    Returns:
        재색인 작업 시작 확인 메시지
    """
    try:
        import sys
        import subprocess
        from pathlib import Path

        index_script = Path(f"{settings.FASTAPI_DIR}/index_sev.py")

        if not index_script.exists():
            raise HTTPException(status_code=500, detail="Index script not found")

        def run_reindex():
            try:
                # Rules 재색인
                subprocess.run([
                    sys.executable,
                    str(index_script),
                    "--cmd", "CRM",
                    "--index", INDEX_RULE
                ], check=True, capture_output=True, text=True)

                # Articles 재색인
                subprocess.run([
                    sys.executable,
                    str(index_script),
                    "--cmd", "CAM",
                    "--index", INDEX_ARTICLE
                ], check=True, capture_output=True, text=True)

                # Appendices 재색인
                subprocess.run([
                    sys.executable,
                    str(index_script),
                    "--cmd", "CPAI",
                    "--index", INDEX_APPENDIX
                ], check=True, capture_output=True, text=True)

                logger.info("Successfully reindexed all data (rules, articles, appendices)")
            except subprocess.CalledProcessError as e:
                logger.error(f"Full reindex failed: {e.stderr}")
            except Exception as e:
                logger.error(f"Full reindex error: {e}")

        if background_tasks:
            background_tasks.add_task(run_reindex)
        else:
            run_reindex()

        return {
            "success": True,
            "message": "Full reindexing started",
            "indices": [INDEX_RULE, INDEX_ARTICLE, INDEX_APPENDIX]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full reindex API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/es/reindex/status")
async def get_reindex_status():
    """
    재색인 상태 조회

    Returns:
        각 인덱스의 문서 수 및 상태
    """
    try:
        client = init_es_client()

        # 각 인덱스 통계
        stats = {}

        for index_name, index_constant in [
            ("rules", INDEX_RULE),
            ("articles", INDEX_ARTICLE),
            ("appendices", INDEX_APPENDIX)
        ]:
            try:
                # LibEs wraps Elasticsearch client in .es attribute
                count_result = client.es.count(index=index_constant)
                stats[index_name] = {
                    "index": index_constant,
                    "count": count_result.get("count", 0),
                    "status": "available"
                }
            except Exception as e:
                stats[index_name] = {
                    "index": index_constant,
                    "count": 0,
                    "status": "error",
                    "error": str(e)
                }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "indices": stats
        }

    except Exception as e:
        logger.error(f"Reindex status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
