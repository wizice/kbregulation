# KB신용정보 사규관리 시스템 (KB Regulation Management System)

KB신용정보의 사내 규정을 관리하는 웹 애플리케이션.
규정 원본(docx/pdf) 업로드, JSON 변환, DB 저장, Elasticsearch 색인, 웹 열람/검색을 지원한다.

## 기술 스택

| 구성요소 | 기술 | 포트 |
|----------|------|------|
| Backend | FastAPI (Python 3.9, uvicorn) | 8800 (127.0.0.1) |
| Database | PostgreSQL 17 | 35432 (127.0.0.1) |
| Search | Elasticsearch 8.x | 9200 (localhost) |
| Session | Redis 6.x | 6379 (127.0.0.1) |
| Web Server | Apache httpd (reverse proxy) | 80, 443 |

- OS: Rocky Linux 9.7 (x86_64)
- 운영 서버: 오프라인 (USB 이관)
- 개발 서버: DigitalOcean

## 디렉토리 구조

```
kbregulation/
├── fastapi/                    # 백엔드 애플리케이션
│   ├── app.py                  # FastAPI 메인 (라우터 등록, 미들웨어, 페이지 엔드포인트)
│   ├── settings.py             # 설정 (pydantic Settings, .env 로드)
│   ├── .env                    # 환경변수 (ES_HOST, DB_HOST 등)
│   ├── app_logger.py           # 로깅 설정
│   ├── index_sev.py            # Elasticsearch 색인 스크립트 (rule/article/appendix)
│   ├── api/                    # API 모듈 (~70개 파일)
│   │   ├── auth_middleware.py   # 인증 미들웨어
│   │   ├── auth_router.py      # 로그인/로그아웃 라우터
│   │   ├── router_*.py         # 기능별 라우터 (regulations, search, synonyms 등)
│   │   ├── service_*.py        # 비즈니스 로직 서비스
│   │   ├── query_*.py          # DB 쿼리 모듈
│   │   ├── redis_session_manager.py  # Redis 세션 관리
│   │   └── settings.py         # API 레벨 설정
│   ├── applib/                 # 데이터 처리 라이브러리
│   │   ├── utils/              # 유틸리티 모듈
│   │   │   ├── docx_parser.py          # DOCX 파싱
│   │   │   ├── pdf_parser.py           # PDF 파싱
│   │   │   ├── pdf_extractor.py        # PDF 텍스트 추출
│   │   │   ├── json_converter.py       # JSON 변환
│   │   │   ├── docx_image_extractor.py # DOCX 이미지 추출
│   │   │   ├── docx_table_renderer.py  # DOCX 테이블 렌더링
│   │   │   └── number_parser.py        # 조항 번호 파싱
│   │   ├── docx/               # 원본 DOCX 파일 (KB신용정보 규정)
│   │   ├── pdf/                # 원본 PDF 파일 (KB신용정보 규정)
│   │   ├── docx_json/          # DOCX→JSON 변환 결과
│   │   ├── pdf_txt/            # PDF→텍스트 추출 결과
│   │   ├── txt_json/           # 텍스트→JSON 변환 결과
│   │   ├── merge_json/         # 규정별 병합 JSON (규정ID.json)
│   │   ├── merged/             # 최종 병합 파일
│   │   ├── edited/             # 편집기로 수정된 파일
│   │   ├── synonyms/           # Elasticsearch 동의어 사전
│   │   ├── docx2json.py        # DOCX→JSON 변환 스크립트
│   │   ├── pdf2txt.py          # PDF→텍스트 변환 스크립트
│   │   ├── txt2json.py         # 텍스트→JSON 변환 스크립트
│   │   ├── merge_json.py       # 규정별 JSON 병합
│   │   ├── batch_merge_json.py # 일괄 병합
│   │   ├── json2db.py          # JSON→DB 삽입
│   │   ├── JSON_ALL.py         # 전체 처리 파이프라인
│   │   └── create_summary.py   # 요약 생성
│   ├── db/                     # DB 관련 파일
│   ├── sql/                    # SQL 스키마 (WZ_RULE, WZ_CATE, WZ_DEPT, WZ_APPENDIX 등)
│   ├── templates/              # Jinja2 템플릿 (admin, editor, search 등)
│   ├── static/                 # 정적 파일 (CSS, JS)
│   └── scripts/                # 운영 스크립트
├── www/                        # 프론트엔드 웹 애플리케이션
│   ├── kbregulation.html       # 메인 규정 페이지
│   ├── kbregulation_page.html  # 규정 상세 페이지
│   ├── index.html              # 인덱스 페이지
│   └── static/                 # 정적 리소스
│       ├── file/               # 규정 JSON 파일 (서비스용)
│       ├── pdf/                # 규정 PDF 파일 (서비스용)
│       ├── pdf_txt/            # PDF 텍스트 (서비스용)
│       ├── css/, js/, lib/     # 프론트엔드 라이브러리
│       ├── images/, img/       # 이미지
│       └── extracted_images/   # DOCX에서 추출된 이미지
├── deploy.sh                   # 증분 배포 패키지 생성 (md5 스냅샷 기반)
├── reindex_es.sh               # Elasticsearch 재색인 스크립트
├── create_deploy_package.sh    # 배포 패키지 생성
├── docs/                       # 참고 문서 (CI, 설계서 등)
├── utils/                      # 유틸리티 (그룹웨어 연동 등)
├── .deploy_state/              # 배포 상태 (스냅샷, 이력)
└── .deploy_backups/            # 배포 백업
```

## 데이터 처리 파이프라인

```
[원본 파일]                    [변환]                      [저장소]
docx/ ──→ docx2json.py ──→ docx_json/ ─┐
pdf/  ──→ pdf2txt.py   ──→ pdf_txt/    │
          txt2json.py  ──→ txt_json/ ──┤
                                       ├──→ merge_json.py ──→ merge_json/
                                       │                         │
                                       │    json2db.py ──────→ PostgreSQL
                                       │    index_sev.py ────→ Elasticsearch
                                       │
                                       └──→ www/static/file/   (서비스용 JSON)
                                            www/static/pdf/    (서비스용 PDF)
                                            www/static/pdf_txt/(서비스용 텍스트)
```

## Elasticsearch 인덱스

| 인덱스 | 소스 | 설명 |
|--------|------|------|
| `kbregulation_policy_rule` | merge_json/*.json | 규정 본문 (조/항/목) |
| `kbregulation_policy_article` | merge_json/*.json | 규정 조항 단위 |
| `kbregulation_policy_appendix` | DB + pdf_txt/ | 별표/서식 (PDF 텍스트 포함) |

## DB 테이블 (PostgreSQL)

주요 테이블: `WZ_RULE` (규정), `WZ_CATE` (분류), `WZ_DEPT` (부서), `WZ_APPENDIX` (부록/별표)

## 주요 설정

- **settings.py**: pydantic Settings 기반, `.env` 파일로 오버라이드
- **ES_HOST**: 개발 `167.71.217.249`, 운영 `localhost` (.env로 설정)
- **DB_PORT**: `35432` (비표준 포트)
- **BASE_DIR**: `/home/wizice/kbregulation`

## 배포

- **최초 이관**: `/root/offline-pkg/install.sh` (오프라인 서버에 전체 설치)
- **증분 배포**: `deploy.sh` (변경된 파일만 패키징)
- **방화벽**: `/root/offline-pkg/firewall.sh` (80/443 개방)
- **ES 재색인**: `reindex_es.sh`

## 개발 서버 실행

```bash
# FastAPI 실행
cd /home/wizice/kbregulation/fastapi
/home/wizice/kbregulation/venv3/bin/uvicorn app:app --host 127.0.0.1 --port 8800 --reload

# Elasticsearch 색인
/home/wizice/kbregulation/venv3/bin/python index_sev.py
```

## 코드 컨벤션

- Python 3.9 호환 (venv3)
- 한글 주석/변수명 혼용
- API 경로: `/api/v1/` 또는 `/api/v2/` 접두사
- 템플릿: Jinja2 (fastapi/templates/)
- 프론트엔드: 바닐라 JS + jQuery + Bootstrap
