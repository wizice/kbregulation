# 규정 편집기 기능 명세서 (Editor Functional Specification)

> **목적**: 이 문서는 규정 편집기의 전체 기능을 분석한 명세서입니다. 다른 서버에서 동일한 편집기를 새로 개발할 때 참조 문서로 사용합니다.
> **데이터**: 새 서버의 데이터는 완전히 다릅니다. 파일/데이터 마이그레이션은 해당하지 않습니다.

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [DB 스키마](#2-db-스키마)
3. [JSON 데이터 구조](#3-json-데이터-구조)
4. [파일시스템 구조](#4-파일시스템-구조)
5. [인증 시스템](#5-인증-시스템)
6. [API 엔드포인트 명세](#6-api-엔드포인트-명세)
7. [파일 파싱 파이프라인](#7-파일-파싱-파이프라인)
8. [프론트엔드 구조](#8-프론트엔드-구조)
9. [주요 비즈니스 플로우](#9-주요-비즈니스-플로우)
10. [Python 패키지 의존성](#10-python-패키지-의존성)

---

## 1. 아키텍처 개요

```
[Browser (Vanilla JS)]
    ↓ HTTP
[FastAPI (uvicorn, 포트 8800)]
    ├── Jinja2 Templates (SSR 페이지)
    ├── REST API (JSON)
    ├── Static Files (JS, CSS, Images)
    ↓
[PostgreSQL (포트 35432)] ← 규정/분류/부서/이력 데이터
[Redis (포트 6379)]        ← 세션 스토어
[Elasticsearch (포트 9200)] ← 전문검색 (선택)
[LibreOffice (headless)]   ← DOCX→PDF 변환 (신구대비표)
```

### 기술 스택
- **백엔드**: Python 3 + FastAPI
- **프론트엔드**: Vanilla JavaScript (프레임워크 없음) + CSS
- **템플릿**: Jinja2
- **DB**: PostgreSQL (TimescaleDB 호환)
- **세션**: Redis
- **파일 처리**: python-docx, pdfplumber, reportlab, Pillow

---

## 2. DB 스키마

### 2.1 `wz_rule` — 핵심 규정 테이블

```sql
CREATE TABLE wz_rule (
    wzRuleSeq       INTEGER PRIMARY KEY,    -- 고유 시퀀스 (PK)
    wzLevel         INTEGER,                -- 계층 레벨
    wzRuleId        INTEGER,                -- 내규 그룹 ID (4자리, 동일 규정의 현행/연혁이 같은 값)
    wzName          TEXT,                    -- 규정명
    wzEditType      TEXT,                    -- 제개정구분 ('제정'/'개정'/'수정')
    wzPubNo         TEXT,                    -- 분류번호 (예: '1.1.1.')
    wzEstabDate     TEXT,                    -- 제정일 (YYYY-MM-DD)
    wzLastRevDate   TEXT,                    -- 최종 개정일
    wzLastRevwDate  TEXT,                    -- 최종 검토일
    wzMgrDptNm      TEXT,                    -- 담당부서명 1
    wzMgrDptOrgCd   TEXT,                    -- 담당부서코드 1
    wzMgrDptNm2     TEXT,                    -- 담당부서명 2
    wzMgrDptOrgCd2  TEXT,                    -- 담당부서코드 2
    wzMgrDptNm3     TEXT,                    -- 담당부서명 3
    wzMgrDptOrgCd3  TEXT,                    -- 담당부서코드 3
    wzRelDptNm      TEXT,                    -- 유관부서명 1
    wzRelDptOrgCd   TEXT,                    -- 유관부서코드 1
    wzRelDptNm2     TEXT,                    -- 유관부서명 2
    wzRelDptOrgCd2  TEXT,                    -- 유관부서코드 2
    wzRelDptNm3     TEXT,                    -- 유관부서명 3
    wzRelDptOrgCd3  TEXT,                    -- 유관부서코드 3
    wzCateSeq       INTEGER,                -- 분류(장) FK → wz_cate.wzCateSeq
    wzExecDate      TEXT,                    -- 시행일
    wzLKndName      TEXT,                    -- 관련기준/대분류명
    wzCloseDate     TEXT,                    -- 폐지일자 (연혁 규정에 설정)
    wzNewFlag       TEXT,                    -- '현행' 또는 '연혁'
    wzFileDocx      TEXT,                    -- DOCX 파일 상대경로
    wzFilePdf       TEXT,                    -- PDF 파일 상대경로
    wzFileJson      TEXT,                    -- JSON 파일 상대경로
    wzFileComparison     TEXT,               -- 신구대비표 PDF 경로
    wzFileComparisonDocx TEXT,               -- 신구대비표 DOCX 경로
    wzFileHistory   TEXT,                    -- 수정이력 파일 목록 (JSON 배열 문자열)
    content_text    TEXT,                    -- 규정 텍스트 내용 (전문검색용)
    wzCreatedBy     TEXT,
    wzModifiedBy    TEXT
);
```

**핵심 개념 - `wzRuleId`**:
- 동일 규정의 현행/연혁 버전이 같은 `wzRuleId`를 공유
- 4자리 랜덤 숫자 (1000~9999), 중복 체크 후 생성
- 개정 시: 기존 현행 → 연혁으로 변경, 새 레코드 생성 (같은 wzRuleId)

**핵심 개념 - `wzNewFlag`**:
- `'현행'`: 현재 유효한 규정 (wzRuleId당 1개만 현행)
- `'연혁'`: 과거 버전 (폐지됨, wzCloseDate 설정)

### 2.2 `wz_cate` — 분류(장) 테이블

```sql
CREATE TABLE wz_cate (
    wzCateSeq   INTEGER PRIMARY KEY,   -- 장 번호 (1~15)
    wzCateName  CHAR(40) NOT NULL,     -- 장 이름 (예: '환자안전보장활동')
    wzParentSeq INTEGER,
    wzOrder     INTEGER,
    wzVisible   CHAR(1) DEFAULT 'Y',
    wzCreatedBy TEXT NOT NULL,
    wzModifiedBy TEXT NOT NULL
);
```

### 2.3 `wz_dept` — 부서 테이블

```sql
CREATE TABLE wz_dept (
    wzDeptOrgCd  TEXT PRIMARY KEY,     -- 부서 코드
    wzDeptName   TEXT NOT NULL,         -- 부서명
    wzDeptTelNo  TEXT,
    wzMgrNm      TEXT,                  -- 담당자명
    wzMgrTelNo   TEXT,
    wzCreatedBy  TEXT NOT NULL,
    wzModifiedBy TEXT NOT NULL
);
```

### 2.4 `wz_rule_history` — 개정/수정 이력 테이블

```sql
CREATE TABLE wz_rule_history (
    wzhistoryseq         SERIAL PRIMARY KEY,
    wzruleseq            INTEGER,         -- FK → wz_rule.wzRuleSeq
    wzruleid             INTEGER,         -- 내규 그룹 ID
    wzpubno              TEXT,            -- 분류번호
    wzname               TEXT,            -- 규정명
    wzversion            INTEGER,         -- 버전 번호 (개정=+1, 수정=같은 버전)
    wzactiontype         TEXT,            -- 'revision' 또는 'modification'
    wzrevisiondate       TEXT,            -- 개정일
    wzmodificationdate   TEXT,            -- 수정일
    wzfiledocx           TEXT,            -- 백업 DOCX 경로
    wzfilepdf            TEXT,            -- 백업 PDF 경로
    wzfilecomparison     TEXT,            -- 신구대비표 경로
    wzfilecomparisondocx TEXT,            -- 신구대비표 DOCX 경로
    wznote               TEXT,            -- 비고/개정사유
    wzchangedby          TEXT,            -- 변경자
    wzchangeddate        TIMESTAMP,       -- 변경일시
    wzorigdocxname       TEXT,            -- 원본 DOCX 파일명
    wzorigpdfname        TEXT             -- 원본 PDF 파일명
);
```

### 2.5 `wz_appendix` — 부록 테이블

```sql
CREATE TABLE wz_appendix (
    wzAppendixSeq  SERIAL PRIMARY KEY,
    wzRuleSeq      INTEGER,              -- FK → wz_rule.wzRuleSeq
    wzAppendixNo   TEXT,                 -- 부록 번호
    wzAppendixName TEXT,                 -- 부록 파일명
    wzFileType     TEXT,                 -- 파일 타입
    wzCreatedBy    TEXT NOT NULL,
    wzModifiedBy   TEXT NOT NULL
);
```

### 2.6 `users` — 사용자 테이블

```sql
-- (인증용, 편집기 접근 관리)
CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    username      VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          VARCHAR(20) DEFAULT 'user',  -- 'admin' | 'user'
    created_at    TIMESTAMP DEFAULT NOW()
);
```

---

## 3. JSON 데이터 구조

### 3.1 개별 규정 JSON (merge_json/{wzruleid}.json)

편집기에서 사용하는 핵심 데이터 구조입니다.

```json
{
  "문서정보": {
    "규정명":      "정확한 환자 확인",
    "규정표기명":   "1.1.1. 정확한 환자 확인",
    "내규종류":     "규정",
    "제정일":       "2020.01.01.",
    "최종개정일":    "2025.03.15.",
    "최종검토일":    "2025.03.15.",
    "담당부서":     "간호부",
    "유관부서":     "진료지원부",
    "관련기준":     ["4주기 정신의료기관평가기준", "JCI Standard"],
    "조문갯수":     25,
    "이미지개수":    2,
    "규정ID":       1000,
    "분류번호":     "1.1.1."
  },
  "조문내용": [
    {
      "seq": 1,
      "레벨": 1,
      "번호": "제1조",
      "내용": "(목적) 이 내규는 환자 확인 절차를 정하기 위함이다.",
      "관련이미지": []
    },
    {
      "seq": 2,
      "레벨": 2,
      "번호": "1.",
      "내용": "환자 확인은 두 가지 이상의 방법으로 한다.",
      "관련이미지": []
    },
    {
      "seq": 3,
      "레벨": 3,
      "번호": "1)",
      "내용": "환자 이름을 직접 물어본다.",
      "관련이미지": []
    },
    {
      "seq": 4,
      "레벨": 1,
      "번호": "제2조",
      "내용": "(적용범위) ...",
      "관련이미지": [
        {
          "seq": 1,
          "file_name": "1000_image_seq4_1700000000.png",
          "file_path": "/static/extracted_images/1000/1000_image_seq4_1700000000.png",
          "title": "환자확인 플로우차트"
        }
      ]
    }
  ]
}
```

**레벨 체계**:

| 레벨 | 번호 형식 | 의미 | 예시 |
|------|----------|------|------|
| 1 | 제N조 | 조문 | 제1조, 제2조 |
| 2 | N. | 항 | 1., 2. |
| 3 | N) | 호 | 1), 2) |
| 4 | (N) 또는 (가) | 목 | (1), (가) |
| 5 | ①~㉟ | 세목 | ①, ② |
| 6 | a. | 세목이하1 | a., 가. |
| 7 | a) | 세목이하2 | a), 가) |
| 8 | (a) | 세목이하3 | (a), (가) |

### 3.2 통합 JSON (merged_severance.json)

모든 현행 규정을 장(chapter)별로 묶은 마스터 파일입니다.

```json
{
  "1장": {
    "title": "환자안전보장활동",
    "icon": "fas fa-shield-alt",
    "regulations": [
      {
        "code": "1.1.1",
        "name": "정확한 환자 확인",
        "wzRuleSeq": 8902,
        "appendix": ["별표 1. 환자확인 체크리스트"],
        "detail": {
          "documentInfo": {
            "규정명": "정확한 환자 확인",
            "내규종류": "규정",
            "제정일": "2020.01.01.",
            "최종개정일": "2025.03.15.",
            "최종검토일": "2025.03.15.",
            "담당부서": "간호부",
            "유관부서": "진료지원부",
            "관련기준": ["..."],
            "파일명": "1000.json",
            "현행내규PDF": "1000_8902_20250315.pdf",
            "신구대비표PDF": "comparisonTable/1000_8902_20250315.pdf"
          },
          "articles": [ /* ...조문내용 전체... */ ]
        }
      }
    ]
  },
  "2장": { ... },
  "3장": { ... }
}
```

### 3.3 요약 JSON (summary_severance.json)

`merged_severance.json`에서 `articles` 배열만 제거한 경량 버전입니다. 서비스 화면에서 목록 표시용으로 사용합니다.

---

## 4. 파일시스템 구조

```
{BASE_DIR}/
├── fastapi/
│   ├── app.py                          # FastAPI 진입점
│   ├── settings.py                     # 환경 설정
│   ├── api/                            # 백엔드 모듈
│   ├── templates/                      # Jinja2 템플릿
│   ├── static/
│   │   ├── js/                         # 프론트엔드 JS
│   │   ├── styles.css                  # 메인 CSS
│   │   └── extracted_images/{wzruleid}/ # 조문별 이미지 (편집기용)
│   └── applib/
│       ├── pdf/                        # 현행 PDF 원본
│       ├── pdf_old/                    # 연혁 PDF 백업 ({wzruleid}_{wzruleseq}.pdf)
│       ├── pdf_txt/                    # PDF→텍스트 변환 결과
│       ├── docx/                       # 현행 DOCX 원본
│       ├── docx_old/                   # 연혁 DOCX 백업
│       ├── docx_json/                  # DOCX→JSON 파싱 결과
│       ├── txt_json/                   # 텍스트→JSON 파싱 결과
│       ├── merge_json/                 # ★ 현행 규정 JSON ({wzruleid}.json)
│       ├── merge_json_old/             # 연혁 규정 JSON 백업
│       ├── edited/                     # 편집 텍스트 백업
│       ├── merged_severance.json       # 전체 통합 JSON
│       ├── pdf2txt.py                  # PDF→텍스트 변환
│       ├── txt2json.py                 # 텍스트→JSON 변환
│       ├── docx2json.py               # DOCX→JSON 변환
│       ├── JSON_ALL.py                 # JSON 전체 병합
│       └── create_summary.py           # 요약 JSON 생성
│
└── www/
    └── static/
        ├── file/                       # ★ 서비스 화면용 JSON ({wzruleid}.json)
        │   ├── summary_severance.json  # 요약 JSON (목록 표시용)
        │   └── file_old/               # 서비스 JSON 백업
        ├── pdf/
        │   └── comparisonTable/        # 신구대비표 PDF/DOCX
        ├── history/                    # 수정이력 파일
        │   └── {wzruleid}/VER{nn}_{type}_{ts}/  # 이력별 백업 폴더
        └── extracted_images/{wzruleid}/ # 조문별 이미지 (서비스용)
```

**핵심 파일 흐름**:
1. 업로드: `applib/pdf/` 또는 `applib/docx/`
2. 파싱: `applib/pdf_txt/` → `applib/txt_json/` 또는 `applib/docx_json/`
3. 병합: `applib/merge_json/{wzruleid}.json` (편집기 작업용)
4. 서비스 동기화: `www/static/file/{wzruleid}.json` (서비스 화면용 복사본)
5. 개정 시: 기존 파일 → `*_old/` 폴더로 이동

---

## 5. 인증 시스템

### 구조
- **방식**: Redis 세션 기반 + HTTP-only 쿠키
- **세션 TTL**: 2시간 (매 요청마다 자동 연장)
- **리프레시 TTL**: 8시간

### 인증 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/auth/login` | 로그인 (username, password) |
| POST | `/api/v1/auth/logout` | 로그아웃 |
| GET | `/api/v1/auth/me` | 현재 사용자 정보 |
| POST | `/api/v1/auth/register` | 회원가입 |

### 권한 체계
- **`get_current_user`**: 일반 인증 (모든 API 기본)
- **`require_role("admin")`**: 관리자 전용 (삭제, 복원 등)
- **`login_required(redirect_to="/login")`**: HTML 페이지 접근 제어

---

## 6. API 엔드포인트 명세

### 6.1 규정 CRUD (`/api/v1/rule/`)

#### GET `/api/v1/rule/get/{rule_id}` — 규정 상세 조회

- **Path**: `rule_id` (int) = wzruleseq
- **Response**: 규정 전체 필드 (날짜는 YYYY-MM-DD 형식)

```json
{
  "success": true,
  "data": {
    "wzruleseq": 8902, "wzruleid": 1000, "wzname": "...", "wzpubno": "1.1.1.",
    "wzestabdate": "2020-01-01", "wzlastrevdate": "2025-03-15",
    "wzmgrdptnm": "간호부", "wzmgrdptorgcd": "NUR",
    "wzmgrdptnm2": null, "wzmgrdptorgcd2": null,
    "wzmgrdptnm3": null, "wzmgrdptorgcd3": null,
    "wzreldptnm": null, "wzreldptorgcd": null,
    "wzcateseq": 1, "wzexecdate": "2025-03-15",
    "wzlkndname": "환자안전", "wzclosedate": null,
    "wzfiledocx": "applib/docx/...", "wzfilepdf": "applib/pdf/...",
    "wznewflag": "현행", "content_text": "...",
    "wzfilecomparison": "comparisonTable/...", "wzfilecomparisondocx": "..."
  }
}
```

#### POST `/api/v1/rule/create` — 신규 규정 생성 (제정)

- **Body (JSON)**:
  - `name` (str, 필수) — 규정명
  - `publication_no` (str, 필수) — 분류번호 (예: "1.1.1.")
  - `department`, `department_code` — 담당부서 1
  - `department2`, `department_code2` — 담당부서 2
  - `department3`, `department_code3` — 담당부서 3
  - `established_date`, `execution_date` — 날짜 (기본: 오늘)
  - `category` — 대분류 (기본: '규정')
  - `status` — 상태 (기본: '현행')
- **로직**:
  1. publication_no 첫 자리로 wz_cate 유효성 검증
  2. 현행 규정 중 동일 publication_no 중복 체크
  3. `generate_unique_wzruleid()`: 1000~9999 랜덤 생성, 중복 확인
  4. INSERT INTO wz_rule
- **Response**: `{"success": true, "rule_id": 123, "data": {...}}`

#### PUT `/api/v1/rule/update-basic/{rule_id}` — 기본정보 수정

- **Body (JSON)**: 변경할 필드만 전달 (동적 UPDATE)
  - `wzname`, `wzpubno`, `wzmgrdptnm/2/3`, `wzreldptnm/2/3`, `wzestabdate`, `wzlastrevdate`, `wzexecdate`, `wznewflag`, `wzcateseq` 등
- **로직**:
  1. 연혁→현행 전환 시: `_old` 폴더에서 파일 복원
  2. 동적 UPDATE 쿼리 실행
  3. `merge_json/{wzruleid}.json`의 `문서정보` 동기화
  4. `www/static/file/{wzruleid}.json`에 복사
  5. 백그라운드: `JSON_ALL.py` + `create_summary.py` 실행

#### PUT `/api/v1/rule/update-json/{rule_id}` — JSON 내용 저장

- **Body (JSON)**: `{"json_data": {"조문내용": [...], "문서정보": {...}}}`
- **로직**:
  1. DB에서 `wzFileJson` 경로 조회
  2. JSON 파일 덮어쓰기
  3. `www/static/file/` 동기화
  4. `조문내용`에서 `content_text` 추출하여 DB UPDATE
  5. 백그라운드: 전체 병합 실행

#### DELETE `/api/v1/rule/delete/{rule_id}` — 규정 삭제

- **로직**:
  1. DB에서 규정 정보 조회
  2. `merge_json/`, `merge_json_old/`, `www/static/file/` 관련 파일 삭제
  3. DB에서 DELETE
  4. `summary_severance.json`, `merged_severance.json`에서 해당 규정 제거

### 6.2 파일 업로드/파싱 (`/api/v1/rule/`)

#### POST `/api/v1/rule/upload-parse-pdf` — PDF 업로드 + 파싱

- **Form**: `pdf_file` (UploadFile), `rule_id` (int)
- **로직**:
  1. 저장: `applib/pdf/{wzruleid}_{name}_{timestamp}.pdf`
  2. PDF→텍스트: `applib/pdf_txt/{wzruleid}_{name}_{timestamp}.txt`
  3. 텍스트→JSON: `applib/txt_json/{wzruleid}_{name}_{timestamp}.json`
  4. DB UPDATE wzFilePdf

#### POST `/api/v1/rule/upload-parse-docx` — DOCX 업로드 + 파싱

- **Form**: `docx_file` (UploadFile), `rule_id` (int)
- **로직**:
  1. 저장: `applib/docx/{wzruleid}_{name}_{timestamp}.docx`
  2. DOCX→JSON: `applib/docx_json/{wzruleid}_{name}_{timestamp}.json`
  3. DB UPDATE wzFileDocx
  4. 자동 신구대비표 생성 시도 (이전 버전 JSON이 있으면)

#### POST `/api/v1/rule/merge-json` — PDF+DOCX JSON 병합

- **Form**: `pdf_json_path` (str), `docx_json_path` (str), `rule_id` (int)
- **로직**:
  1. `JSONMerger(pdf_path, docx_path).merge_regulation()`
  2. 저장: `applib/merge_json/{wzruleid}.json`
  3. 복사: `www/static/file/{wzruleid}.json`
  4. DB UPDATE wzFileJson

#### POST `/api/v1/rule/merge-json/{rule_id}` — 자동 병합 (최신 파일 사용)

- **로직**: `applib/txt_json/`과 `applib/docx_json/`에서 해당 wzruleid의 최신 파일을 찾아 자동 병합

### 6.3 개정 관리 (`/api/v1/rule/`)

#### POST `/api/v1/rule/create-revision/{rule_id}` — 개정본 생성

- **Body (JSON)**: `revision_date`, `execution_date`
- **로직**:
  1. 기존 규정 조회
  2. `merge_json/{wzruleid}.json` → `merge_json_old/{wzruleid}_{wzruleseq}.json` 복사
  3. PDF, DOCX → `_old` 폴더로 이동
  4. 기존 규정 UPDATE: `wzNewFlag='연혁'`, `wzCloseDate` 설정, 파일 경로 `_old`로
  5. 새 규정 INSERT: `wzEditType='개정'`, `wzNewFlag='현행'`

#### POST `/api/v1/rule/unified-revision/{rule_id}` — 통합 개정 (추천)

- **Form (multipart)**: 기본정보 + 파일 (PDF, DOCX, 신구대비표) 한번에 처리
  - `pub_no`, `name`, `dept_code/name` (1~3), `rel_dept1_code/name` (1~3)
  - `estab_date`, `revision_date`, `review_date`, `execution_date`
  - `status` (기본: '연혁'), `comment`, `history_note`
  - `pdf_file`, `docx_file`, `compare_file` (모두 optional)
- **로직**:
  1. 기존 파일 → `_old` 이동
  2. 기존 규정 UPDATE (파일 경로 _old로)
  3. 새 규정 INSERT
  4. 업로드 파일 저장 + DB UPDATE
  5. `save_history_on_revision()` 이력 기록
  6. 백그라운드: 파일 파싱 → 병합 → 신구대비표 생성 → 서비스 동기화

#### POST `/api/v1/rule/activate-revision/{rule_id}` — 현행 활성화

- **로직**: 해당 규정을 `'현행'`으로, 같은 wzRuleId의 다른 현행을 `'연혁'`으로 변경

#### POST `/api/v1/rule/save-edited-content` — 편집 내용 저장

- **Form**: `rule_id`, `content` (텍스트), `mode` ('new'/'edit'/'revision'), `merged_json_data`, 날짜 등
- **모드별 동작**:
  - **new**: JSON 생성, `www/static/file/` 동기화, `wzNewFlag='현행'`
  - **revision**: 기존 현행의 JSON 백업, 새 JSON 생성, 서비스 동기화
  - **edit**: 기존 JSON 덮어쓰기

### 6.4 JSON 뷰어 (`/api/v1/json/`)

#### GET `/api/v1/json/view/{rule_id}` — 규정 JSON 조회

- **로직**:
  1. DB에서 wzFileJson 경로 조회
  2. 연혁 규정이면 `merge_json_old/` 경로도 탐색
  3. JSON 파일 읽기
  4. `조문내용`에서 텍스트 추출하여 `content_text` 반환

### 6.5 신구대비표 (`/api/v1/compare/`)

#### GET `/api/v1/compare/versions/{rule_id}` — 비교 가능 버전 목록
#### GET `/api/v1/compare/diff` — 두 버전 비교 (JSON diff)
#### GET `/api/v1/compare/html` — 비교 결과 HTML 테이블

- 구 조문 / 신 조문 2단 비교표
- 변경 유형별 색상: 노랑(수정), 초록(추가), 빨강(삭제)

#### POST `/api/v1/compare/save-comparison` — 신구대비표 생성 및 저장

- **Form**: `rule_id`, `revision_date`, `remarks`, `pdf_file`, `docx_file`
- **로직**:
  1. PDF+DOCX 파싱 → 병합
  2. python-docx로 비교표 DOCX 생성 (5컬럼: 내규번호/내규제목/현행/개정/비고)
  3. LibreOffice headless로 DOCX→PDF 변환
  4. `www/static/pdf/comparisonTable/` 저장
  5. DB UPDATE wzFileComparison

#### POST `/api/v1/compare/replace-comparison` — 신구대비표 교체

- **Form**: `wzruleseq`, `docx_file` (사용자가 직접 작성한 DOCX)
- **로직**: DOCX 저장 → LibreOffice로 PDF 변환 → DB 업데이트

#### POST `/api/v1/rule/upload-comparison-table/{rule_id}` — 신구대비표 직접 업로드

- 지원 형식: `.pdf`, `.docx`, `.doc`, `.hwp`, `.hwpx`, `.xlsx`, `.xls`
- 저장 경로: `www/static/pdf/comparisonTable/{wzruleid}_{wzruleseq}_{YYYYMMDD}{ext}`

### 6.6 이력 관리 (`/api/v1/rule-history/`)

#### GET `/api/v1/rule-history/list/{rule_id}` — 이력 목록

- **Response**: 버전별 그룹화된 이력 (revision + modifications)
- 최초 등록(VER 0)은 wz_rule에서 합성
- 이후 개정(VER 1, 2, ...)은 wz_rule_history에서 조회

#### GET `/api/v1/rule-history/download/{history_id}` — 이력 파일 다운로드

- `file_type`: 'docx', 'pdf', 'comparison', 'comparison_docx'

#### POST `/api/v1/rule-history/create` — 이력 수동 생성

- **로직**:
  1. 버전 번호 결정: revision이면 MAX+1, modification이면 현재 MAX
  2. 파일 백업: `www/static/history/{wzruleid}/VER{nn}_{type}_{ts}/`
  3. INSERT INTO wz_rule_history

### 6.7 연혁 파일 관리 (`/api/v1/regulations/history/`)

| 메서드 | 경로 | 설명 | 권한 |
|--------|------|------|------|
| GET | `/{rule_id}/files` | 연혁 파일 목록 | user |
| GET | `/{rule_id}/download/{file_type}` | 연혁 파일 다운로드 | user |
| GET | `/{rule_id}/preview` | 연혁 JSON 미리보기 (readonly) | user |
| PUT | `/{rule_id}/content` | 연혁 내용 수정 (.backup 생성) | admin |
| DELETE | `/{rule_id}` | 연혁 규정 삭제 | admin |
| POST | `/{rule_id}/restore-to-current` | 연혁→현행 복원 | admin |
| PUT | `/{rule_id}` | 연혁 기본정보 수정 | user |
| POST | `/{rule_id}/upload/{file_type}` | 연혁 파일 업로드 | user |

### 6.8 이미지 관리 (`/api/v1/rule-enhanced/`)

#### POST `/api/v1/rule-enhanced/upload-image` — 이미지 업로드

- **Form**: `wzruleseq` (int), `article_seq` (int, 조문의 seq 값), `image` (UploadFile)
- **제한**: PNG/JPG/GIF, 최대 10MB
- **저장 경로**: `static/extracted_images/{wzruleseq}/{wzruleseq}_image_seq{article_seq}_{unix_ts}{ext}`
  - 두 곳에 동시 저장: `fastapi/static/` + `www/static/`
- **로직**: JSON 파일의 해당 조문 `관련이미지` 배열에 추가

#### DELETE `/api/v1/rule-enhanced/delete-image` — 이미지 삭제

- **Body**: `wzruleseq`, `article_seq`, `image_file_name`
- **로직**: JSON에서 제거, 파일을 `.deleted/` 하위 폴더로 이동 (소프트 삭제)

#### POST `/api/v1/rule-enhanced/resize-image` — 이미지 리사이즈

- **Body**: `wzruleseq`, `article_seq`, `image_file_name`, `width` (or `height`)
- **로직**: 원본 `.backup/`에 보관, Pillow LANCZOS 리사이즈, 종횡비 유지

#### GET `/api/v1/rule-enhanced/images/{rule_id}` — 조문별 이미지 목록

- `rule_id`는 `wzruleid` (그룹 ID)
- 가장 최근 wzruleseq의 JSON에서 조문 + 이미지 목록 반환

### 6.9 분류 관리 (`/api/v1/classification/`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/list` | 분류 목록 (장별 규정 수 포함) |
| POST | `/create` | 분류 생성: `{chapter_number, name}` |
| PUT | `/update/{cate_seq}` | 분류명 변경: `{new_name}` |
| DELETE | `/delete/{cate_seq}` | 분류 삭제 (하위 규정 있으면 거부) |
| GET | `/regulations/{cate_seq}` | 분류별 현행 규정 목록 |

호환 별칭: `GET /api/v1/cate/list`

### 6.10 부서 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/WZ_DEPT/api/v1/select` | 부서 목록 조회 |
| GET | `/api/v1/dept/list` | 부서 목록 |
| GET | `/api/v1/dept/regulation-counts` | 부서별 담당 규정 수 |
| POST | `/api/v1/dept/create` | 부서 생성 |
| PUT | `/api/v1/dept/update/{code}` | 부서 수정 |
| DELETE | `/api/v1/dept/delete/{code}` | 부서 삭제 |

### 6.11 규정 목록/검색 (`/regulations/`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/regulations/api/list?status=현행\|연혁\|전체` | 규정 목록 |
| GET | `/regulations/api/current` | 현행 규정만 |
| GET | `/regulations/api/history` | 연혁 규정만 |
| GET | `/regulations/api/view/{rule_id}` | 규정 상세 |

### 6.12 공개 API (`/api/v1/rule-public/`) — 인증 불필요

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/comparison-table/{rule_id}` | 신구대비표 정보 |
| GET | `/comparison-table/{rule_id}/download` | 신구대비표 다운로드 |
| GET | `/rule-file/{rule_id}/download/{file_type}` | PDF/DOCX 다운로드 |
| GET | `/history-file/{rule_id}` | 수정이력 파일 목록 |
| GET | `/history-file/{rule_id}/download` | 수정이력 파일 다운로드 |

### 6.13 부록 관리 (`/api/v1/appendix/`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/upload/{rule_seq}` | 부록 업로드 (PDF) |
| GET | `/list/{rule_seq}` | 부록 목록 |
| GET | `/download/{appendix_seq}` | 부록 다운로드 |
| DELETE | `/admin/delete/{appendix_seq}` | 부록 삭제 |
| PUT | `/admin/update/{appendix_seq}` | 부록 메타데이터 수정 |
| POST | `/admin/replace/{appendix_seq}` | 부록 파일 교체 |

---

## 7. 파일 파싱 파이프라인

### 7.1 전체 파이프라인

```
PDF 원본                           DOCX 원본
    ↓ pdf2txt.py (pdfplumber)         ↓ docx2json.py (python-docx)
텍스트 (.txt)                      JSON (문서정보 + 조문내용 + 이미지)
    ↓ txt2json.py (regex)
JSON (문서정보 + 조문내용)
    ↓                                  ↓
    └──────── JSONMerger ──────────────┘
                    ↓
        병합 JSON ({wzruleid}.json)
                    ↓
        ┌───────────┴───────────┐
   merge_json/ 저장      www/static/file/ 복사
                    ↓
            JSON_ALL.py (전체 병합)
                    ↓
          merged_severance.json
                    ↓
           create_summary.py
                    ↓
          summary_severance.json
```

### 7.2 pdf2txt.py — PDF → 텍스트

**입력**: PDF 파일 경로
**출력**: UTF-8 텍스트 파일

**핵심 처리**:
1. `pdfplumber`로 페이지별 텍스트 추출
2. 페이지 정보 제거 (페이지 번호, 헤더/푸터)
3. 줄바꿈 최적화: 번호가 있는 줄은 분리, 연속 텍스트는 병합
4. 부록/별표 참조 분리 복원 (`[부록 N.]`, `[별표 N.]` 줄 분리 수정)

### 7.3 txt2json.py — 텍스트 → JSON

**입력**: 텍스트 문자열 또는 파일
**출력**: `{문서정보, 조문내용}` JSON

**핵심 처리**:
1. `extract_document_info()`: 규정명, 날짜, 담당부서 등 메타데이터 추출 (정규식)
2. `parse_articles()`: `제1조`부터 시작하여 줄별로 레벨/번호 판별
3. `get_line_info()`: 정규식으로 레벨 판별 (조문/항/호/목/세목 8단계)
4. `관련이미지`는 항상 빈 배열 (이미지는 DOCX에서만 추출)

### 7.4 docx2json.py — DOCX → JSON

**입력**: DOCX 파일 경로
**출력**: `{문서정보, 조문내용}` JSON + 이미지 파일 추출

**핵심 처리**:
1. `extract_metadata()`: DOCX 테이블에서 메타데이터 추출 (제정일, 담당부서, 유관부서 등)
2. `extract_numbers_from_docx()`: Word 번호매기기 XML + 텍스트 패턴으로 레벨 판별
3. 이미지 추출: `extracted_images/{wzruleid}/` 경로에 저장, `관련이미지`에 링크
4. `txt2json.py`와 동일한 JSON 스키마 출력

### 7.5 JSONMerger — PDF+DOCX 병합

**목적**: PDF JSON의 번호 체계 + DOCX JSON의 내용 텍스트를 결합
**병합 규칙**:
- PDF JSON: 번호(번호) 정확도가 높음
- DOCX JSON: 내용(내용) 정확도가 높고, 이미지 포함
- `seq` 기반으로 매칭하여 최적 조합

### 7.6 JSON_ALL.py — 전체 병합

**입력**: `merge_json/` 폴더의 모든 `{wzruleid}.json`
**출력**: `merged_severance.json`

**핵심 처리**:
1. 파일명에서 분류번호 추출 (`N.N.N` 패턴)
2. 동일 코드 중복 시 최신 mtime 우선
3. DB에서 장 이름/아이콘, PDF/신구대비표 경로 조회
4. 장별로 그룹화하여 정렬

### 7.7 create_summary.py — 요약 생성

**입력**: `merged_severance.json`
**출력**: `summary_severance.json` (articles 배열만 제거)

---

## 8. 프론트엔드 구조

### 8.1 페이지 라우팅

모든 페이지는 로그인 필수 (`@login_required`).

| 경로 | 템플릿 | 설명 |
|------|--------|------|
| `/regulations/list` | `regulations/list_full.html` | **메인 편집기** |
| `/regulations/current` | `regulations/current_full.html` | 현행 규정 탭 |
| `/regulations/history` | `regulations/history_full.html` | 연혁 탭 |
| `/regulations/classification` | `regulations/classification_full.html` | 분류 관리 |
| `/regulations/department` | `regulations/department_full.html` | 부서 관리 |
| `/regulations/compare` | `regulations/compare_full.html` | 신구대비표 |
| `/regulations/search-engine` | `regulations/search-engine_full.html` | 검색 엔진 |
| `/regulations/service` | `regulations/support_full.html` | 서비스 관리 |

### 8.2 JavaScript 모듈

| 파일 | 크기 | 역할 |
|------|------|------|
| `rule-editor.js` | 339KB | **메인 편집기** — 목록, 편집 모달, 개정, 파일 업로드 |
| `regulation-editor.js` | 158KB | 구 버전 편집기 (비동기 파싱 등 일부 사용) |
| `edit-window.js` | 64KB | 팝업 편집 창 HTML 생성 |
| `classification-manager.js` | 27KB | 분류 관리 UI |
| `department-manager.js` | 35KB | 부서 관리 UI |
| `image-manager.js` | 21KB | 조문별 이미지 관리 |
| `service-manager.js` | - | 서비스 페이지 관리 |
| `search-engine.js` | - | 검색 엔진 설정 |
| `date-utils.js` | - | 날짜 포맷 유틸리티 |

### 8.3 메인 편집기 UI (rule-editor.js)

#### RuleEditor 객체 구조

```javascript
const RuleEditor = {
    currentRule: null,            // 현재 편집 중인 규정
    uploadedFiles: { pdf, docx }, // 업로드된 파일 캐시
    selectedComparisonFile: null, // 신구대비표 파일
    parsingResults: { pdf, docx },// 파싱 결과
    mode: 'edit',                 // 'new' | 'edit' | 'revision'
    departments: [],              // 부서 목록 캐시
    regulations: [],              // 전체 규정 목록
    sortField: null,
    sortDirection: 'asc'
}
```

#### 편집 모드 3가지

**1. 제정 (mode='new')**
- "제정" 버튼 → `openNewModal()` → 기본정보 입력 폼
- 입력: 규정명, 분류번호, 담당부서(1~3), 날짜, 상태
- 분류번호 중복 클라이언트 체크
- 저장 → `POST /api/v1/rule/create` → 파일 업로드 모달 자동 오픈

**2. 수정 (mode='edit')**
- 규정 클릭 → `openEditModal(ruleId)` → 탭 편집 모달
- 기본정보 탭: 규정명, 번호, 부서(1~3, 자동완성), 유관부서(1~3), 날짜, 상태
- 파일 탭: PDF/DOCX 업로드+파싱, 신구대비표, 수정이력
- 내용 탭: JSON 조문 편집 테이블 (레벨/번호/내용)
- 이미지 탭: 조문별 이미지 관리
- 부록 탭: 부록 파일 관리

**3. 개정 (mode='revision')**
- "개정" 버튼 → `openRevisionModal()` → 날짜/부서/파일 입력 폼
- 입력: 분류번호, 규정명, 담당부서(1~3), 유관부서(1~3), 날짜, 파일(PDF/DOCX/신구대비표), 비고
- 저장 → `POST /api/v1/rule/unified-revision/{id}` (한번에 처리)

#### 편집 모달 탭 구조

```
[편집 모달] (max-width: 900px, height: 85vh)
├── 헤더: 모드 배지 + 규정번호/이름 + 삭제 메뉴 + 닫기
├── 탭 네비게이션
│   ├── [기본정보] — 규정 메타데이터 편집
│   ├── [파일]    — PDF/DOCX 업로드 + 파싱 + 신구대비표 + 수정이력
│   ├── [내용편집] — 조문내용 JSON 테이블 편집 (Ctrl+S 지원)
│   ├── [이미지]  — ImageManager 위임
│   └── [부록]    — 부록 파일 관리
└── 하단: [저장] [닫기]
```

#### 파일 처리 플로우 (파일 탭)

1. PDF 파일 선택 → `uploadedFiles.pdf`에 캐시
2. DOCX 파일 선택 → `uploadedFiles.docx`에 캐시
3. 둘 다 선택되면 "파일처리" 버튼 활성화
4. `processFiles()`:
   - PDF 업로드+파싱 → `POST /api/v1/rule/upload-parse-pdf`
   - DOCX 업로드+파싱 → `POST /api/v1/rule/upload-parse-docx`
   - JSON 병합 → `POST /api/v1/rule/merge-json`
   - 성공 시: 내용 탭으로 전환, 편집 테이블 렌더링
   - 1.5초 후: 자동 저장 → `POST /api/v1/rule/save-edited-content`

#### 내용 편집 테이블

```html
<table>
  <thead><tr><th>레벨</th><th>번호</th><th>내용</th></tr></thead>
  <tbody>
    <tr data-seq="1">
      <td><input type="number" class="article-level-input" value="1"></td>
      <td><input type="text" class="article-number-input" value="제1조"></td>
      <td><textarea class="article-content-input">목적 ...</textarea></td>
    </tr>
    <!-- ... -->
  </tbody>
</table>
```

저장 시: 모든 행의 seq/레벨/번호/내용을 수집 → `PUT /api/v1/rule/update-json/{ruleId}`

#### 목록 기능

- 초기 로드: `GET /regulations/api/list?status=전체`
- 기본 필터: 현행만 표시
- 클라이언트 사이드 검색: 규정명/분류번호/내용 키워드
- 클라이언트 사이드 정렬: 자연 정렬 (1.1.1 < 1.1.2 < 1.2.1)
- 필터: 분류(장), 부서, 상태

#### 이력보기 모달

- `GET /api/v1/rule-history/list/{ruleId}`
- 버전별 그룹: VER 0(최초) → VER 01(1차 개정) → ...
- 각 버전: 개정일, 수정일, DOCX/PDF/신구대비표 다운로드, 비고

### 8.4 CSS 구조

- 스플릿 패널 레이아웃 (좌: 목록 420px, 우: 상세)
- 모달 시스템: `.modal.active` 오버레이
- 상태 배지: 현행(초록), 연혁(노랑)
- 탭 네비게이션: 상단 탭 + 콘텐츠 영역
- 폼 컴포넌트: `.form-group`, `.form-input`, `.btn-primary` (보라색 #667eea)

### 8.5 날짜 형식

- **DB 저장**: `YYYY-MM-DD`
- **화면 표시**: `YYYY.MM.DD.` (마침표 포함)
- **파일명**: `YYYYMMDD`

```javascript
// 표시용 변환
function formatDate(dateStr) {
    if (!dateStr || dateStr === '-') return '-';
    const match = dateStr.match(/(\d{4})-(\d{2})-(\d{2})/);
    if (match) return `${match[1]}.${match[2]}.${match[3]}.`;
    return dateStr;
}
// 저장용 역변환
function reverseDateFormat(dateStr) {
    // YYYY.MM.DD. → YYYY-MM-DD
}
```

---

## 9. 주요 비즈니스 플로우

### 9.1 신규 규정 등록 (제정)

```
사용자: "제정" 버튼 클릭
  → 기본정보 입력 (규정명, 분류번호, 부서, 날짜)
  → POST /api/v1/rule/create
  → 파일 업로드 모달 (PDF + DOCX)
  → PDF 업로드/파싱 + DOCX 업로드/파싱
  → JSON 병합
  → 내용 편집 (테이블)
  → 저장 (POST /api/v1/rule/save-edited-content, mode='new')
  → www/static/file/ 동기화
  → 백그라운드: merged_severance.json + summary_severance.json 갱신
```

### 9.2 규정 개정

```
사용자: "개정" 버튼 클릭
  → 개정 폼 (날짜, 부서, 파일, 비고)
  → POST /api/v1/rule/unified-revision/{id}

  서버 내부:
  1. 기존 현행 규정의 파일 → _old 폴더로 이동
  2. 기존 규정 DB: wzNewFlag='연혁', wzCloseDate 설정
  3. 새 규정 INSERT: wzEditType='개정', wzNewFlag='현행'(또는 '연혁')
  4. 업로드 파일 저장
  5. 이력 기록 (wz_rule_history INSERT)
  6. 백그라운드: 파싱 → 병합 → 신구대비표 생성 → 서비스 동기화
```

### 9.3 규정 내용 수정

```
사용자: 규정 클릭 → 편집 모달
  → [내용편집] 탭 → JSON 조문 테이블 편집
  → [저장] 또는 Ctrl+S
  → PUT /api/v1/rule/update-json/{ruleId}

  서버 내부:
  1. merge_json/{wzruleid}.json 덮어쓰기
  2. www/static/file/{wzruleid}.json 복사
  3. content_text 추출 → DB UPDATE
  4. 백그라운드: 전체 병합 갱신
```

### 9.4 신구대비표 생성

```
방법 1 (자동 생성):
  DOCX 업로드 시 이전 JSON이 있으면 자동으로 비교표 생성

방법 2 (수동 생성):
  POST /api/v1/compare/save-comparison (PDF+DOCX 업로드)
  → 파싱 → 조문 비교 → DOCX 비교표 생성 → LibreOffice→PDF → 저장

방법 3 (직접 업로드):
  POST /api/v1/rule/upload-comparison-table/{rule_id}
  → 사용자가 만든 파일 직접 업로드 (PDF/DOCX/HWP 등)

방법 4 (교체):
  POST /api/v1/compare/replace-comparison
  → 사용자 DOCX 업로드 → LibreOffice→PDF → DB 교체
```

### 9.5 파일 동기화 구조

```
편집/저장 시:
  applib/merge_json/{wzruleid}.json  (편집기 원본)
       ↓ shutil.copy2
  www/static/file/{wzruleid}.json    (서비스 화면용)

전체 병합 시 (백그라운드):
  applib/merge_json/*.json
       ↓ JSON_ALL.py
  applib/merged_severance.json       (전체 통합)
       ↓ create_summary.py
  www/static/file/summary_severance.json  (서비스 목록용)
```

---

## 10. Python 패키지 의존성

### 핵심 패키지

| 패키지 | 용도 |
|--------|------|
| `fastapi` | 웹 프레임워크 |
| `uvicorn` | ASGI 서버 |
| `psycopg2-binary` | PostgreSQL 연결 |
| `redis` | Redis 세션 |
| `python-multipart` | 파일 업로드 (multipart/form-data) |
| `python-docx` | DOCX 읽기/생성 |
| `pdfplumber` | PDF 텍스트 추출 |
| `reportlab` | PDF 생성 |
| `pillow` | 이미지 처리 (리사이즈) |
| `pydantic` + `pydantic-settings` | 데이터 검증/설정 |
| `Jinja2` | HTML 템플릿 |
| `PyJWT` | JWT 토큰 |
| `bcrypt` | 패스워드 해싱 |
| `mammoth` | DOCX→HTML (보조) |

### 시스템 의존성

| 소프트웨어 | 용도 |
|-----------|------|
| PostgreSQL | 데이터베이스 |
| Redis | 세션 스토어 |
| LibreOffice | DOCX→PDF 변환 (headless 모드) |
| NanumGothic 폰트 | 한글 PDF 생성 |

### 설정 파일 (`settings.py`) 주요 항목

```python
class Settings:
    BASE_DIR = "/path/to/project"
    APPLIB_RELATIVE_PATH = "fastapi/applib"
    JSON_SERVICE_RELATIVE_PATH = "www/static/file"

    DB_HOST = "localhost"
    DB_PORT = 35432
    DB_NAME = "severance"
    DB_USER = "severance"
    DB_PASSWORD = "***"

    redis_host = "localhost"
    redis_port = 6379

    ES_HOST = "localhost"  # Elasticsearch (선택)
    ES_PORT = 9200
```

---

## 부록: 핵심 개념 정리

### wzRuleId vs wzRuleSeq

- **wzRuleSeq**: 각 규정 레코드의 고유 PK (자동 증가)
- **wzRuleId**: 동일 규정의 버전 그룹 ID (현행 + 연혁이 같은 값)
- 개정 시: 새 wzRuleSeq 생성, 같은 wzRuleId 유지

### 현행 vs 연혁

- **현행** (`wzNewFlag='현행'`): 현재 유효한 규정. wzRuleId당 1개만 존재
- **연혁** (`wzNewFlag='연혁'`): 과거 버전. wzCloseDate 설정됨

### 파일 경로 관리

- DB에는 **상대 경로** 저장 (예: `applib/merge_json/1000.json`)
- `file_utils.get_absolute_path()`로 절대 경로 변환: `{BASE_DIR}/{relative_path}`
- 연혁 파일은 `*_old/` 폴더에 `{wzruleid}_{wzruleseq}.{ext}` 형식으로 저장

### 백그라운드 작업

`FastAPI BackgroundTasks`를 사용하여 비동기 실행:
1. `process_files_background()`: 파일 파싱 → 병합 → 동기화
2. `run_json_merge_and_summary()`: `JSON_ALL.py` → `create_summary.py`
3. Elasticsearch 색인 업데이트
