# -*- coding: utf-8 -*-
"""
    index_sev.py
    ~~~~~~~~~~~~

    세브란스병원 규정 Elasticsearch 색인 생성 도구
    연세대 index_yonsei.py v1.1 기반

    :copyright: (c) 2017-2025 by wizice.
    :license: BSD
    :author: Yun Joung Won
    :email: wizice100@gmail.com
    :homepage: http://www.wizice.com
"""
from __future__ import with_statement

VERSION = (1, 1)
__version__ = '.'.join(map(str, VERSION[0:2]))
__description__ = 'Indexer for Severance Hospital Regulations'
__author__ = 'Yun Joung Won'
__author_email__ = 'wizice100@gmail.com'
__homepage__ = 'http://www.wizice.com'
__license__ = 'BSD'

import os
import sys
import json
import argparse
import codecs
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, MultiSearch
from hanparse import HanParse
from app_logger import get_logger
from settings import settings


def create_es_client(**kwargs) -> Elasticsearch:
    """settings 기반으로 Elasticsearch 클라이언트 생성"""
    conn = {
        'host': ES_IP,
        'port': int(ES_PORT),
        'scheme': 'https' if settings.ES_USE_SSL else 'http'
    }
    extra = {}
    if settings.ES_USE_SSL:
        if settings.ES_USER and settings.ES_PASSWORD:
            extra['http_auth'] = (settings.ES_USER, settings.ES_PASSWORD)
        if settings.ES_CA_CERT:
            extra['ca_certs'] = settings.ES_CA_CERT
            extra['verify_certs'] = settings.ES_VERIFY_CERTS
        else:
            extra['verify_certs'] = False
    extra.update(kwargs)
    return Elasticsearch([conn], **extra)

# =============================================================================
# 로거 초기화
# =============================================================================

logger = get_logger(__name__)

# =============================================================================
# 명령행 인자 파싱
# =============================================================================

parser = argparse.ArgumentParser(
    description='index_sev.py v%s - 세브란스병원 규정 Elasticsearch 색인' % __version__
)

ROOT_PATH = settings.BASE_DIR
JSON_PATH = settings.WWW_STATIC_FILE_DIR

parser.add_argument('--root_path', default=ROOT_PATH, help='프로젝트 루트 경로')
parser.add_argument('--json_path', default=JSON_PATH, help='JSON 파일 경로')
parser.add_argument('--log_level', default='info', help='로그 레벨')
parser.add_argument('--cmd', default='', help='명령어 (CRM, CRI, CAM, CAI, CAIA)')
parser.add_argument('--index', default='', help='인덱스명')
parser.add_argument('--doc_type', default='_doc', help='문서 타입')
parser.add_argument('--rule_seq', default='', help='규정 시퀀스')
parser.add_argument('--reindex', default='', help='재색인 플래그 (REINDEX)')
parser.add_argument('--es_ip', default=None, help='Elasticsearch IP (기본값: settings.py에서 가져옴)')
parser.add_argument('--es_port', default=None, help='Elasticsearch Port (기본값: settings.py에서 가져옴)')

args = parser.parse_args()

# =============================================================================
# 전역 변수 (settings.py에서 기본값 가져오기)
# =============================================================================
try:
    from settings import settings
    ES_IP = args.es_ip if args.es_ip else settings.ES_HOST
    ES_PORT = args.es_port if args.es_port else settings.ES_PORT
except ImportError:
    # settings 없을 경우 args 또는 기본값
    ES_IP = args.es_ip if args.es_ip else "localhost"
    ES_PORT = args.es_port if args.es_port else 9200
INDEX = args.index
DOC_TYPE = args.doc_type
gParse = HanParse()

# =============================================================================
# JSON 파일 처리 클래스
# =============================================================================

class JsonFileProcessor:
    """JSON 파일 처리 클래스 (연세대 MyDB 클래스 대체)"""

    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        self.re_remove_ptn = re.compile(
            r"([\u318d\u00B7\u2024\uFF65\u2027\u2219\u30FB]|[^.0-9가-힣a-zA-Z])"
        )

    def strip_text(self, in_str: str) -> str:
        """한글, 영문, 숫자가 아닌 모든 문자 제거"""
        if not in_str:
            return ""
        try:
            new_str = self.re_remove_ptn.sub("", in_str)
            return new_str
        except Exception as e:
            logger.error(f"Error in strip_text: {e}")
            return in_str

    def parse_filename(self, filename: str) -> Optional[Dict[str, str]]:
        """
        파일명에서 정보 추출
        지원 패턴:
        0. (숫자-숫자)_규정명_날짜_merged.json (예: (6-8)_여비규정_250305_merged.json)
        1. {seq}.json (예: 1003.json)
        2. merged_{pubno}. {규정명}_{날짜}.json (예: merged_1.1.1. 정확한 환자 확인_202503개정_20251013_114427.json)
        3. {seq}_{규정명}_{개정일시}.json (기존 패턴)
        """
        try:
            # summary 파일 건너뛰기
            if filename.startswith('summary_'):
                return None

            # _merged가 아닌 원본이 있으면 _merged 버전만 사용
            if not filename.endswith('_merged.json'):
                merged_name = filename.replace('.json', '_merged.json')
                if (self.json_path / merged_name).exists():
                    return None

            # 패턴 0: (숫자-숫자)_규정명_날짜_merged.json 또는 (숫자-숫자)_규정명_날짜.json
            match = re.match(r'^\((\d+-\d+)\)_(.+?)_(\d{6})(?:_merged)?\.json$', filename)
            if match:
                pubno = match.group(1)  # "6-8"
                name = match.group(2)   # "여비규정"
                date_str = match.group(3)  # "250305"
                seq = pubno.replace('-', '_')  # "6_8"
                return {
                    "seq": seq,
                    "pubno": pubno,
                    "name": name,
                    "filename": filename,
                    "indexed_at": date_str
                }

            # 패턴 1: 숫자만 (예: 1003.json)
            match = re.match(r'^(\d+)\.json$', filename)
            if match:
                return {
                    "seq": match.group(1),
                    "name": "",
                    "filename": filename,
                    "indexed_at": ""
                }

            # 패턴 2: merged 형식 (예: merged_1.1.1. 규정명_날짜.json)
            match = re.match(r'^merged_(.+?)\.?\s*(.+?)_(\d{8}_\d{6})\.json$', filename)
            if match:
                pubno = match.group(1)
                name = match.group(2)
                date_str = match.group(3)
                # pubno에서 seq 생성 (예: 1.1.1 -> 111)
                seq = pubno.replace('.', '')
                return {
                    "seq": seq,
                    "pubno": pubno,
                    "name": name,
                    "filename": filename,
                    "indexed_at": date_str
                }

            # 패턴 3: 기존 형식 (예: 123_규정명_20251013_114427.json)
            match = re.match(r'^(\d+)_(.+)\.json$', filename)
            if match:
                seq = match.group(1)
                rest = match.group(2)

                # 날짜 패턴 찾기
                date_match = re.search(r'_(\d{8}_\d{6})$', rest)
                if date_match:
                    date_str = date_match.group(1)
                    name = rest[:date_match.start()]
                else:
                    date_str = ""
                    name = rest

                return {
                    "seq": seq,
                    "name": name,
                    "filename": filename,
                    "indexed_at": date_str
                }

            logger.warning(f"Unrecognized filename format: {filename}")
            return None
        except Exception as e:
            logger.error(f"Error parsing filename {filename}: {e}")
            return None

    def load_json_file(self, filepath: Path) -> Optional[Dict]:
        """JSON 파일 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file {filepath}: {e}")
            return None

    def extract_rule_info(self, json_data: Dict, file_info: Dict) -> Dict:
        """
        JSON 데이터에서 규정 정보 추출 (연세대 rule 데이터 형식과 유사하게)
        """
        doc_info = json_data.get('문서정보', {})

        # 규정명: JSON에 없으면 파일명에서 가져오기
        rule_name = doc_info.get('규정명', '') or file_info.get('name', '')
        tags_list = [rule_name]

        # 조문 내용 추가 (본문 검색을 위해)
        article_list = json_data.get('조문내용', [])
        for article in article_list:
            content = article.get('내용', '')
            if content:
                tags_list.append(content)

        # 전체 내용을 하나로 합쳐서 태그 생성
        full_text = ' '.join(tags_list)
        tags = gParse.parse_join(full_text)

        # 날짜 변환
        def convert_date(date_str: str) -> Optional[str]:
            if not date_str or date_str == '-':
                return None
            # yyyy.mm. 형식
            match = re.match(r'(\d{4})\.(\d{2})\.', date_str)
            if match:
                return f"{match.group(1)}-{match.group(2)}-01"
            # yyyy.mm.dd. 형식
            match = re.match(r'(\d{4})\.(\d{2})\.(\d{2})\.', date_str)
            if match:
                return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            return None

        rule_doc = {
            "seq": file_info.get('seq'),
            "규정명": rule_name,
            "규정표기명": doc_info.get('규정표기명', ''),
            "내규종류": doc_info.get('내규종류', ''),
            "제정일": convert_date(doc_info.get('제정일', '')),
            "최종개정일": convert_date(doc_info.get('최종개정일', '')),
            "최종검토일": convert_date(doc_info.get('최종검토일', '')),
            "담당부서": doc_info.get('담당부서', '') or doc_info.get('소관부서', ''),
            "유관부서": doc_info.get('유관부서', ''),
            "관련기준": ' '.join(doc_info.get('관련기준', [])),
            "조문갯수": doc_info.get('조문갯수', 0),
            "이미지개수": doc_info.get('이미지개수', 0),
            "json_파일경로": file_info.get('filename'),
            "tags": tags,
            "색인일시": datetime.now().isoformat()
        }

        return rule_doc

    def extract_articles(self, json_data: Dict, file_info: Dict) -> List[Dict]:
        """
        JSON 데이터에서 조문 정보 추출 (연세대 jo 데이터 형식과 유사하게)
        """
        articles = []
        doc_info = json_data.get('문서정보', {})
        rule_name = doc_info.get('규정명', '') or file_info.get('name', '')
        rule_seq = file_info.get('seq')
        dept = doc_info.get('담당부서', '') or doc_info.get('소관부서', '')

        article_list = json_data.get('조문내용', [])

        for article in article_list:
            content = article.get('내용', '')
            tags = gParse.parse_join(content)

            article_doc = {
                "규정seq": rule_seq,
                "규정명": rule_name,
                "조문seq": article.get('seq'),
                "조문레벨": article.get('레벨', 0),
                "조문번호": article.get('번호', ''),
                "조문내용": content,
                "관련이미지": article.get('관련이미지', []),
                "담당부서": dept,
                "tags": tags
            }

            articles.append(article_doc)

        return articles

# =============================================================================
# Elasticsearch 관리 함수 (연세대 방식 그대로)
# =============================================================================

def elasticsearch_health(restart=False) -> bool:
    """Elasticsearch 서버 상태 확인"""
    try:
        es = create_es_client(request_timeout=30)

        health = es.cluster.health()
        logger.info(f"Elasticsearch status: {health['status']}")
        return True
    except Exception as e:
        logger.warning(f"Elasticsearch health check failed: {e}")
        return False

# =============================================================================
# 매핑 생성 함수 (연세대 fn_create_rule_mapping, fn_create_jo_mapping 방식)
# =============================================================================

def fn_create_rule_mapping(index: str) -> bool:
    """규정 목록 인덱스 매핑 생성"""
    es = create_es_client()

    mapping = {
        "mappings": {
            "properties": {
                "seq": {"type": "keyword"},
                "규정명": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "규정표기명": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "내규종류": {"type": "keyword"},
                "제정일": {"type": "date", "format": "yyyy-MM-dd"},
                "최종개정일": {"type": "date", "format": "yyyy-MM-dd"},
                "최종검토일": {"type": "date", "format": "yyyy-MM-dd"},
                "담당부서": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "유관부서": {"type": "text"},
                "관련기준": {"type": "text"},
                "조문갯수": {"type": "integer"},
                "이미지개수": {"type": "integer"},
                "json_파일경로": {"type": "keyword"},
                "tags": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "부록명목록": {"type": "text"},
                "색인일시": {"type": "date"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }

    try:
        if es.indices.exists(index=index):
            es.indices.delete(index=index)
            logger.info(f"Deleted existing index: {index}")

        es.indices.create(index=index, body=mapping)
        logger.info(f"Created index mapping: {index}")
        return True

    except Exception as e:
        logger.error(f"Error creating rule mapping: {e}")
        traceback.print_exc()
        return False

def fn_create_article_mapping(index: str) -> bool:
    """조문 인덱스 매핑 생성"""
    es = create_es_client()

    mapping = {
        "mappings": {
            "properties": {
                "규정seq": {"type": "keyword"},
                "규정명": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "조문seq": {"type": "long"},
                "조문레벨": {"type": "integer"},
                "조문번호": {"type": "keyword"},
                "조문내용": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword", "ignore_above": 1024}
                    }
                },
                "관련이미지": {"type": "nested"},
                "담당부서": {"type": "keyword"},
                "tags": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                }
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }

    try:
        if es.indices.exists(index=index):
            es.indices.delete(index=index)
            logger.info(f"Deleted existing index: {index}")

        es.indices.create(index=index, body=mapping)
        logger.info(f"Created index mapping: {index}")
        return True

    except Exception as e:
        logger.error(f"Error creating article mapping: {e}")
        traceback.print_exc()
        return False

def fn_create_appendix_mapping(index: str) -> bool:
    """부록 인덱스 매핑 생성"""
    es = create_es_client()

    mapping = {
        "mappings": {
            "properties": {
                "wzappendixseq": {"type": "keyword"},
                "wzruleseq": {"type": "keyword"},
                "wzappendixno": {"type": "keyword"},
                "wzappendixname": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "wzfilepath": {"type": "keyword"},
                "wzfiletype": {"type": "keyword"},
                "규정명": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "규정표기명": {"type": "keyword"},
                "pdf_text": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword", "ignore_above": 10240}
                    }
                },
                "tags": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "색인일시": {"type": "date"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }

    try:
        if es.indices.exists(index=index):
            es.indices.delete(index=index)
            logger.info(f"Deleted existing index: {index}")

        es.indices.create(index=index, body=mapping)
        logger.info(f"Created appendix index mapping: {index}")
        return True

    except Exception as e:
        logger.error(f"Error creating appendix mapping: {e}")
        traceback.print_exc()
        return False

# =============================================================================
# 색인 생성 함수 (연세대 fn_index_rulebulk, fn_index_jobulk 방식)
# =============================================================================

def fn_index_rulebulk(index: str, doc_type: str) -> bool:
    """규정 목록 전체 색인 (PostgreSQL에서 부록명 포함)"""
    processor = JsonFileProcessor(args.json_path)
    es = create_es_client()

    # PostgreSQL 연결하여 부록명 가져오기 (규정명으로 매칭)
    appendix_map_by_name = {}
    try:
        from api.timescaledb_manager_v2 import DatabaseConnectionManager

        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        db = DatabaseConnectionManager(**db_config)
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 규정번호 + 규정명으로 부록 조회
                cur.execute("""
                    SELECT r.wzpubno, r.wzname, a.wzappendixname
                    FROM wz_appendix a
                    JOIN wz_rule r ON a.wzruleseq = r.wzruleseq
                    ORDER BY r.wzruleseq, a.wzappendixseq
                """)
                for row in cur.fetchall():
                    # wzpubno + " " + wzname 조합 (예: "9.1.5. 세브란스병원 내규 관리")
                    full_name = f"{row[0]} {row[1]}"
                    appendix_name = row[2]
                    if full_name not in appendix_map_by_name:
                        appendix_map_by_name[full_name] = []
                    appendix_map_by_name[full_name].append(appendix_name)

        logger.info(f"Loaded appendix data for {len(appendix_map_by_name)} regulations")
    except Exception as e:
        logger.warning(f"Failed to load appendix data from PostgreSQL: {e}")

    try:
        json_files = list(Path(args.json_path).glob('*.json'))
        logger.info(f"Found {len(json_files)} JSON files")

        indexed_count = 0
        error_count = 0
        bulk_actions = []

        for json_file in json_files:
            try:
                file_info = processor.parse_filename(json_file.name)
                if not file_info:
                    continue

                json_data = processor.load_json_file(json_file)
                if not json_data:
                    error_count += 1
                    continue

                rule_doc = processor.extract_rule_info(json_data, file_info)

                # 부록명 추가 (규정명으로 매칭)
                rule_name = rule_doc.get('규정명', '')
                if rule_name in appendix_map_by_name:
                    rule_doc['부록명목록'] = ' '.join(appendix_map_by_name[rule_name])
                else:
                    rule_doc['부록명목록'] = ''

                # Bulk API 형식
                bulk_actions.append({
                    "index": {
                        "_index": index,
                        "_id": file_info['seq']
                    }
                })
                bulk_actions.append(rule_doc)

                indexed_count += 1

                # 100개씩 배치 색인
                if len(bulk_actions) >= 200:  # 100개 * 2 (액션 + 문서)
                    from elasticsearch.helpers import bulk
                    actions = []
                    for i in range(0, len(bulk_actions), 2):
                        action = bulk_actions[i]
                        doc = bulk_actions[i+1]
                        actions.append({
                            '_op_type': 'index',
                            '_index': action['index']['_index'],
                            '_id': action['index']['_id'],
                            '_source': doc
                        })
                    bulk(es, actions)
                    logger.info(f"Indexed {indexed_count} regulations...")
                    bulk_actions = []

            except Exception as e:
                logger.error(f"Error processing {json_file.name}: {e}")
                error_count += 1

        # 나머지 색인
        if bulk_actions:
            from elasticsearch.helpers import bulk
            actions = []
            for i in range(0, len(bulk_actions), 2):
                action = bulk_actions[i]
                doc = bulk_actions[i+1]
                actions.append({
                    '_op_type': 'index',
                    '_index': action['index']['_index'],
                    '_id': action['index']['_id'],
                    '_source': doc
                })
            bulk(es, actions)

        logger.info(f"Completed: Indexed={indexed_count}, Errors={error_count}")
        return True

    except Exception as e:
        logger.error(f"Error in fn_index_rulebulk: {e}")
        traceback.print_exc()
        return False

def fn_index_articlebulk(rule_seq: str, index: str, doc_type: str, reindex: bool = False) -> bool:
    """단일 규정의 조문 색인"""
    processor = JsonFileProcessor(args.json_path)
    es = create_es_client()

    try:
        # 파일 패턴: {seq}.json 또는 {seq}_*.json
        json_files = list(Path(args.json_path).glob(f'{rule_seq}_*.json'))
        if not json_files:
            # _*.json 패턴이 없으면 {seq}.json 시도
            json_files = list(Path(args.json_path).glob(f'{rule_seq}.json'))

        if not json_files:
            logger.warning(f"No JSON file found for rule_seq: {rule_seq}")
            return False

        json_file = sorted(json_files)[-1]
        logger.info(f"Processing: {json_file.name}")

        file_info = processor.parse_filename(json_file.name)
        if not file_info:
            return False

        json_data = processor.load_json_file(json_file)
        if not json_data:
            return False

        articles = processor.extract_articles(json_data, file_info)
        logger.info(f"Extracted {len(articles)} articles")

        # 재색인이면 기존 삭제
        if reindex:
            es.delete_by_query(
                index=index,
                body={"query": {"match": {"규정seq": rule_seq}}}
            )

        # Bulk 색인
        from elasticsearch.helpers import bulk
        actions = []
        for article in articles:
            actions.append({
                '_op_type': 'index',
                '_index': index,
                '_id': f"{rule_seq}_{article['조문seq']}",
                '_source': article
            })

        bulk(es, actions)
        logger.info(f"Indexed {len(articles)} articles for rule_seq: {rule_seq}")
        return True

    except Exception as e:
        logger.error(f"Error in fn_index_articlebulk: {e}")
        traceback.print_exc()
        return False

def fn_index_articlebulk_all(index: str, doc_type: str) -> bool:
    """전체 규정의 조문 색인 (파일 직접 순회 방식)"""
    processor = JsonFileProcessor(args.json_path)
    es = create_es_client()

    try:
        json_files = list(Path(args.json_path).glob('*.json'))
        logger.info(f"Found {len(json_files)} JSON files")

        from elasticsearch.helpers import bulk

        success_count = 0
        error_count = 0
        total_articles = 0

        for json_file in sorted(json_files):
            file_info = processor.parse_filename(json_file.name)
            if not file_info:
                continue

            json_data = processor.load_json_file(json_file)
            if not json_data:
                error_count += 1
                continue

            rule_seq = file_info['seq']
            articles = processor.extract_articles(json_data, file_info)
            if not articles:
                logger.warning(f"No articles in {json_file.name}")
                continue

            # 기존 조문 삭제 후 재색인
            try:
                es.delete_by_query(
                    index=index,
                    body={"query": {"match": {"규정seq": rule_seq}}},
                    ignore=[404]
                )
            except Exception:
                pass

            actions = []
            for article in articles:
                actions.append({
                    '_op_type': 'index',
                    '_index': index,
                    '_id': f"{rule_seq}_{article['조문seq']}",
                    '_source': article
                })

            bulk(es, actions)
            total_articles += len(articles)
            success_count += 1
            logger.info(f"Indexed {len(articles)} articles for {json_file.name}")

        logger.info(f"Completed: {success_count} files, {total_articles} articles, {error_count} errors")
        return error_count == 0

    except Exception as e:
        logger.error(f"Error in fn_index_articlebulk_all: {e}")
        traceback.print_exc()
        return False

def fn_index_appendix_all(index: str, doc_type: str) -> bool:
    """전체 부록 색인 (PostgreSQL + PDF 텍스트)"""
    try:
        from api.timescaledb_manager_v2 import DatabaseConnectionManager

        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        db = DatabaseConnectionManager(**db_config)
        es = create_es_client()

        # PostgreSQL에서 부록 데이터 가져오기
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT a.wzappendixseq, a.wzruleseq, a.wzappendixno,
                           a.wzappendixname, a.wzfilepath, a.wzfiletype,
                           r.wzname, r.wzpubno
                    FROM wz_appendix a
                    LEFT JOIN wz_rule r ON a.wzruleseq = r.wzruleseq
                    WHERE r.wznewflag = '현행'
                    ORDER BY a.wzappendixseq
                """
                cur.execute(query)
                appendices = cur.fetchall()

        logger.info(f"Found {len(appendices)} appendices from database")

        # PDF 텍스트 파일 경로 (부록 PDFs는 www/static/pdf에 있음)
        pdf_txt_path = Path(args.root_path) / "www" / "static" / "pdf_txt"

        from elasticsearch.helpers import bulk
        actions = []
        success_count = 0
        error_count = 0

        for appendix in appendices:
            try:
                wzappendixseq, wzruleseq, wzappendixno, wzappendixname, \
                wzfilepath, wzfiletype, wzname, wzpubno = appendix

                # PDF 텍스트 파일 찾기
                pdf_text_content = ""

                if wzfilepath:
                    # 파일명 추출 (예: "4.3.5._부록2._고위험의약품 ...")
                    filename_base = Path(wzfilepath).stem

                    # pdf_txt 폴더에서 매칭되는 텍스트 파일 찾기
                    matching_files = list(pdf_txt_path.glob(f"{filename_base}*.txt"))

                    if matching_files:
                        # 가장 최근 파일 사용
                        txt_file = sorted(matching_files)[-1]
                        logger.debug(f"Found PDF text: {txt_file.name}")

                        with open(txt_file, 'r', encoding='utf-8') as f:
                            pdf_text_content = f.read()

                # 형태소 분석 (부록명 + PDF 내용)
                text_for_parsing = f"{wzappendixname} {pdf_text_content}"
                tags = gParse.parse_join(text_for_parsing)

                # Elasticsearch 문서 생성
                doc = {
                    "wzappendixseq": wzappendixseq,
                    "wzruleseq": wzruleseq,
                    "wzappendixno": wzappendixno,
                    "wzappendixname": wzappendixname,
                    "wzfilepath": wzfilepath,
                    "wzfiletype": wzfiletype or "",
                    "규정명": wzname or "",
                    "규정표기명": wzpubno or "",
                    "pdf_text": pdf_text_content,
                    "tags": tags,
                    "색인일시": datetime.now().isoformat()
                }

                actions.append({
                    '_op_type': 'index',
                    '_index': index,
                    '_id': wzappendixseq,
                    '_source': doc
                })

                success_count += 1

            except Exception as e:
                logger.error(f"Error processing appendix {wzappendixseq}: {e}")
                error_count += 1
                continue

        # Bulk 색인 (50개씩 나눠서 전송 - PDF 텍스트가 커서 한번에 보내면 실패)
        CHUNK_SIZE = 50
        bulk_errors = 0
        if actions:
            for i in range(0, len(actions), CHUNK_SIZE):
                chunk = actions[i:i + CHUNK_SIZE]
                try:
                    bulk(es, chunk, raise_on_error=False)
                    logger.info(f"Indexed chunk {i//CHUNK_SIZE + 1}/{(len(actions)-1)//CHUNK_SIZE + 1} ({len(chunk)} docs)")
                except Exception as bulk_e:
                    logger.error(f"Bulk chunk {i//CHUNK_SIZE + 1} failed: {bulk_e}")
                    bulk_errors += len(chunk)

        logger.info(f"Completed: {success_count} success, {error_count} process errors, {bulk_errors} bulk errors")
        return (error_count + bulk_errors) == 0

    except Exception as e:
        logger.error(f"Error in fn_index_appendix_all: {e}")
        traceback.print_exc()
        return False

# =============================================================================
# CLI 명령어 처리 (연세대 방식 그대로)
# =============================================================================

def main():
    """메인 함수"""

    logger.info(f"index_sev.py v{__version__} started")
    logger.info(f"Command: {args.cmd}")
    logger.info(f"Elasticsearch: {ES_IP}:{ES_PORT}")

    # Elasticsearch 상태 확인
    if not elasticsearch_health():
        logger.warning("Elasticsearch is not running. Please start it first.")
        scheme = 'https' if settings.ES_USE_SSL else 'http'
        logger.info(f"Expected: {scheme}://{ES_IP}:{ES_PORT}/")

    # 기본값 설정
    index = args.index or "severance_rule"
    doc_type = args.doc_type or "_doc"

    # 명령어 처리
    if args.cmd == "CRM":
        # 규정 매핑 생성 (Create Rule Mapping)
        if fn_create_rule_mapping(index):
            logger.info("✓ Rule mapping created successfully")
        else:
            logger.error("✗ Failed to create rule mapping")
            sys.exit(1)

    elif args.cmd == "CAM":
        # 조문 매핑 생성 (Create Article Mapping)
        if fn_create_article_mapping(index):
            logger.info("✓ Article mapping created successfully")
        else:
            logger.error("✗ Failed to create article mapping")
            sys.exit(1)

    elif args.cmd == "CRI":
        # 규정 목록 색인 (Create Rule Index)
        if fn_index_rulebulk(index, doc_type):
            logger.info("✓ Rule indexing completed successfully")
        else:
            logger.error("✗ Failed to index rules")
            sys.exit(1)

    elif args.cmd == "CAI":
        # 단일 규정 조문 색인 (Create Article Index)
        if not args.rule_seq:
            logger.error("rule_seq is required for CAI command")
            sys.exit(1)

        reindex = (args.reindex == "REINDEX")
        if fn_index_articlebulk(args.rule_seq, index, doc_type, reindex):
            logger.info(f"✓ Article indexing completed for rule_seq: {args.rule_seq}")
        else:
            logger.error(f"✗ Failed to index articles for rule_seq: {args.rule_seq}")
            sys.exit(1)

    elif args.cmd == "CAIA":
        # 전체 규정 조문 색인 (Create Article Index All)
        if fn_index_articlebulk_all(index, doc_type):
            logger.info("✓ All articles indexed successfully")
        else:
            logger.error("✗ Failed to index all articles")
            sys.exit(1)

    elif args.cmd == "CPAM":
        # 부록 매핑 생성 (Create aPpendix Mapping)
        if fn_create_appendix_mapping(index):
            logger.info("✓ Appendix mapping created successfully")
        else:
            logger.error("✗ Failed to create appendix mapping")
            sys.exit(1)

    elif args.cmd == "CPAI":
        # 전체 부록 색인 (Create aPpendix Index)
        if fn_index_appendix_all(index, doc_type):
            logger.info("✓ All appendices indexed successfully")
        else:
            logger.error("✗ Failed to index appendices")
            sys.exit(1)

    else:
        logger.error(f"Unknown command: {args.cmd}")
        print("\n사용 가능한 명령어:")
        print("  CRM  - 규정 매핑 생성 (Create Rule Mapping)")
        print("  CAM  - 조문 매핑 생성 (Create Article Mapping)")
        print("  CRI  - 규정 목록 색인 (Create Rule Index)")
        print("  CAI  - 단일 조문 색인 (Create Article Index)")
        print("  CAIA - 전체 조문 색인 (Create Article Index All)")
        print("  CPAM - 부록 매핑 생성 (Create aPpendix Mapping)")
        print("  CPAI - 전체 부록 색인 (Create aPpendix Index)")
        print("\n예시:")
        print("  python3 index_sev.py --cmd=CRM --index=severance_rule")
        print("  python3 index_sev.py --cmd=CRI --index=severance_rule")
        print("  python3 index_sev.py --cmd=CPAM --index=severance_policy_appendix")
        print("  python3 index_sev.py --cmd=CPAI --index=severance_policy_appendix")
        sys.exit(1)

    logger.info("index_sev.py completed")

if __name__ == '__main__':
    main()
