# Elasticsearch 검색엔진 이식 분석서

## 개요
세브란스병원 규정관리시스템의 Elasticsearch 기반 검색엔진 소스 분석 결과입니다.
새 서버에 이식할 때 이 문서를 참고하세요.

---

## 1. 핵심 파일 구조

```
search_engine_src/
├── core/                          # 핵심 라이브러리
│   ├── lib_es_sev.py              # ES 클라이언트 래퍼 (검색/인덱싱 API)
│   ├── hanparse.py                # 한국어 형태소 분석 & 토큰화
│   ├── settings.py                # ES 접속정보, 인덱스명 설정
│   └── requirements_current.txt   # Python 의존성 목록
│
├── indexing/                      # 인덱싱 관련
│   ├── index_sev.py               # CLI 인덱싱 도구 (메인)
│   ├── indexing_service.py        # FastAPI 인덱싱 서비스
│   ├── bulk_index_appendix_pdfs.py # 부록 PDF 벌크 인덱싱
│   └── elasticsearch_index_production.sh # 프로덕션 인덱싱 스크립트
│
├── api/                           # 검색 API 엔드포인트
│   ├── router_public_search_es.py # 메인 ES 검색 API (2178줄, 핵심)
│   ├── router_search_es.py        # 인증 기반 ES 검색 API
│   ├── router_public_search.py    # 공개 검색 (PostgreSQL+ES)
│   └── router_search.py           # 기본 검색 라우터
│
├── synonym/                       # 동의어 관리
│   ├── service_synonym.py         # 동의어 확장 서비스
│   ├── router_synonyms.py         # 동의어 CRUD API
│   └── query_synonym.py           # 동의어 DB 쿼리
│
├── templates/                     # 프론트엔드 템플릿
│   ├── search-engine.html
│   ├── search-engine_full.html
│   ├── search.html
│   ├── search_full.html
│   └── admin/indexing_management.html
│
├── static/js/                     # 프론트엔드 JS
│   └── search-engine.js
│
├── sql/                           # DB 스크립트
│   └── 001_add_fts_index.sql      # PostgreSQL FTS 인덱스
│
└── tests/                         # 테스트
    ├── test_hanparse.py
    ├── verify_code.py
    └── test_synonyms_api.py
```

---

## 2. ES 인덱스 구조

### 인덱스 3개 운영
| 인덱스명 | 용도 |
|---------|------|
| `severance_policy_rule` | 규정 단위 검색 (규정명, 담당부서, 관련기준 등) |
| `severance_policy_article` | 조항 단위 검색 (세부 내용 검색) |
| `severance_policy_appendix` | 부록 검색 (PDF 텍스트 포함) |

### ES 설정 (settings.py)
- **ES_HOST**: 167.71.217.249 (개발) / localhost (운영)
- **ES_PORT**: 9200
- **ES_USE_SSL**: False

---

## 3. 검색 흐름

```
사용자 쿼리 입력
    ↓
hanparse.py: 한국어 토큰화 & 레퍼런스 패턴 감지 (COP.3, 3.2.2 등)
    ↓
service_synonym.py: 동의어 확장 (DB에서 로드)
    ↓
router_public_search_es.py: ES bool 쿼리 구성
  - 따옴표 검색 → exact match
  - 레퍼런스 패턴 → keyword 필드 매칭
  - 일반 검색 → multi_match + 가중치 부여
    ↓
lib_es_sev.py: ES 서버에 쿼리 실행
    ↓
결과 집계 (규정+조항+부록) → JSON 응답
```

---

## 4. 인덱싱 흐름

```
www/static/file/*.json (규정 원본 데이터)
    ↓
index_sev.py 또는 indexing_service.py
    ↓
hanparse.py로 텍스트 토큰화 → "tags" 필드 생성
    ↓
elasticsearch.helpers.bulk()로 벌크 인덱싱
```

---

## 5. 핵심 의존성 (pip)

```
elasticsearch==8.15.1
elasticsearch-dsl==8.15.1
elastic-transport==8.15.1
```

기타 FastAPI 관련: fastapi, uvicorn, jinja2, python-multipart 등
(전체 목록은 requirements_current.txt 참조)

---

## 6. 이식 시 주의사항

1. **ES 서버 필요**: Elasticsearch 8.x 설치 필요
2. **settings.py 수정**: ES_HOST, ES_PORT를 새 서버에 맞게 변경
3. **PostgreSQL 필요**: 동의어(search_synonyms 테이블)와 규정 메타데이터 저장
4. **JSON 데이터**: `www/static/file/*.json` 규정 원본 데이터 필요 (인덱싱 소스)
5. **hanparse.py**: 외부 의존성 없이 순수 Python으로 동작 (이식 용이)
6. **DB 연결**: `timescaledb_manager_v2.py`의 DB 접속정보 수정 필요
7. **app.py 라우터 등록**: 검색 관련 라우터를 FastAPI app에 include 필요

---

## 7. 최소 이식 파일 (검색만 동작시킬 경우)

필수:
- `lib_es_sev.py` - ES 클라이언트
- `hanparse.py` - 토큰화
- `settings.py` - 설정
- `router_public_search_es.py` - 검색 API
- `index_sev.py` - 인덱싱 도구

권장:
- `service_synonym.py` + `query_synonym.py` + `router_synonyms.py` - 동의어 기능
- `indexing_service.py` - 웹 기반 인덱싱 관리
