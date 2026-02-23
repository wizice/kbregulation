# 신구대비표 파일 관리 기능 - 테스트 및 사용 가이드

## 📋 목차
1. [기능 개요](#기능-개요)
2. [아키텍처](#아키텍처)
3. [API 문서](#api-문서)
4. [사용자 가이드](#사용자-가이드)
5. [테스트 가이드](#테스트-가이드)
6. [문제 해결](#문제-해결)

## 🎯 기능 개요

세브란스 편집기에 **신구대비표(Comparison Table) 파일 관리 기능**이 추가되었습니다.

### 주요 특징

- **버전별 관리**: 각 규정 개정판마다 개별 신구대비표 PDF 파일 관리
- **데이터베이스 추적**: `wz_rule` 테이블의 `wzFileComparison` 컬럼에 파일 경로 저장
- **자동 백업**: 기존 파일 덮어쓰기 시 자동으로 백업 폴더에 보관
- **레거시 호환**: 기존 `comparisonTable_{규정코드}.pdf` 형식도 계속 지원
- **파일 명명 규칙**: `{wzRuleId}_{wzRuleSeq}_{개정일자}.pdf`

### 구현 날짜
- **개발 완료**: 2025년 11월 13일
- **테스트 완료**: 2025년 11월 13일

---

## 🏗 아키텍처

### 데이터베이스 변경

```sql
-- wz_rule 테이블에 신구대비표 파일 경로 저장용 컬럼 추가
ALTER TABLE wz_rule
ADD COLUMN IF NOT EXISTS wzFileComparison TEXT;
```

- **컬럼명**: `wzFileComparison`
- **타입**: TEXT
- **용도**: 신구대비표 PDF 파일 상대 경로 저장
- **예시 값**: `comparisonTable/7421_308_20250909.pdf`

### 파일 저장 구조

```
/home/wizice/regulation/www/static/pdf/
├── comparisonTable/                          # 신규 방식 (버전별)
│   ├── 7421_308_20250909.pdf                # {wzRuleId}_{wzRuleSeq}_{date}
│   ├── 7421_286_20230315.pdf
│   └── 7421_285_20220810.pdf
│
├── comparisonTable_backup/                   # 자동 백업 폴더
│   └── 7421_308_20250909_backup_20251113.pdf
│
└── (레거시 파일 - 기존 방식)
    ├── comparisonTable_11.5.1.pdf           # comparisonTable_{규정코드}
    ├── comparisonTable_2.1.4.2.pdf
    └── ...
```

### 파일 명명 규칙

#### 신규 방식 (버전별 관리)
```
{wzRuleId}_{wzRuleSeq}_{개정일자}.pdf
```

- **wzRuleId**: 규정 계통 ID (같은 규정의 모든 버전이 공유)
- **wzRuleSeq**: 규정 레코드 고유 ID (각 버전마다 다름)
- **개정일자**: wzLastRevDate (yyyy.mm.dd → yyyymmdd 형식)

**예시**:
- `7421_308_20250909.pdf` → 규정 7421의 308번 레코드, 2025년 9월 9일 개정

**파일명 생성 로직** (service_rule_editor.py:1984-1986):
```python
revision_date_str = wzlastrevdate.replace('.', '').replace('-', '') if wzlastrevdate else 'nodate'
filename = f"{wzruleid}_{wzruleseq}_{revision_date_str}.pdf"
```

#### 레거시 방식 (하위 호환)
```
comparisonTable_{규정코드}.pdf
```

- **규정코드**: wzPubNo (예: 11.5.1)

**예시**:
- `comparisonTable_11.5.1.pdf`

### 파일 접근 방식

#### 프론트엔드에서 파일 찾기

사용자가 "신구대비표" 버튼을 클릭하면:

1. **wzRuleSeq가 있으면** (신규 방식):
   - API 호출: `GET /api/v1/rule-public/comparison-table/{wzRuleSeq}`
   - DB에서 `wzFileComparison` 컬럼 값을 가져옴
   - 예: `comparisonTable/7421_308_20250909.pdf`
   - 실제 경로: `/static/pdf/comparisonTable/7421_308_20250909.pdf`

2. **wzRuleSeq가 없으면** (레거시 방식):
   - 직접 파일 경로 구성: `/static/pdf/comparisonTable/comparisonTable_{규정코드}.pdf`
   - 예: `/static/pdf/comparisonTable/comparisonTable_11.5.1.pdf`

**JavaScript 구현** (severance.js:5707-5762):
```javascript
async function openComparisonTablePdf(regulationCode, regulationName, wzRuleSeq) {
    if (wzRuleSeq) {
        // 1. API로 DB에서 파일 경로 조회
        const response = await fetch(`/api/v1/rule-public/comparison-table/${wzRuleSeq}`);
        const data = await response.json();

        if (data.success && data.file_exists) {
            pdfPath = `/static/pdf/${data.file_path}`;  // DB에서 가져온 경로
        }
    } else {
        // 2. 레거시 방식 - 규정코드로 직접 구성
        pdfPath = `/static/pdf/comparisonTable/comparisonTable_${regulationCode}.pdf`;
    }
}
```

### 왜 이렇게 복잡한가?

**문제**: 파일명이 `7421_308_20250909.pdf`인데, JavaScript에서 wzRuleSeq만 알고 있으면 파일을 찾을 수 없음

**해결 방안 비교**:

| 방안 | 장점 | 단점 |
|------|------|------|
| **DB 조회 (채택)** | • DB와 항상 동기화<br>• 파일명 변경 가능<br>• 추가 메타데이터 제공 | • API 호출 필요 (약간의 지연) |
| 심볼릭 링크 | • 빠른 접근<br>• 웹 서버에서 직접 처리 | • 파일 시스템 관리 복잡<br>• 동기화 이슈 가능 |
| wzRuleSeq.pdf로 저장 | • 가장 단순 | • 파일명에 의미 없음<br>• 디버깅 어려움 |

**채택 이유**: DB 조회 방식이 가장 안전하고 유연하며, 약간의 지연은 무시할 수 있는 수준

---

## 🔌 API 문서

### 1. 신구대비표 파일 업로드

**Endpoint**: `POST /api/v1/rule/upload-comparison-table/{rule_id}`

**인증**: 관리자 권한 필요 (`@login_required`)

**파라미터**:
- `rule_id` (path): wzRuleSeq 값
- `comparison_file` (multipart/form-data): PDF 파일

**응답** (성공 - 200):
```json
{
  "success": true,
  "message": "신구대비표가 업로드되었습니다.",
  "file_path": "comparisonTable/7421_308_20250909.pdf",
  "filename": "7421_308_20250909.pdf",
  "wzRuleSeq": 308,
  "wzRuleId": 7421,
  "backup_path": "comparisonTable_backup/7421_308_20250909_backup_20251113.pdf"
}
```

**응답** (실패 - 404):
```json
{
  "detail": "규정을 찾을 수 없습니다.",
  "status_code": 404
}
```

**cURL 예시**:
```bash
curl -X POST \
  'http://localhost:8800/api/v1/rule/upload-comparison-table/308' \
  -H 'Cookie: session_token=YOUR_TOKEN' \
  -F 'comparison_file=@/path/to/comparison.pdf'
```

### 2. 신구대비표 파일 조회

**Endpoint**: `GET /api/v1/rule-public/comparison-table/{rule_id}`

**인증**: 불필요 (공개 API - 사용자 화면에서 접근)

**파라미터**:
- `rule_id` (path): wzRuleSeq 값

**응답** (성공 - 200):
```json
{
  "success": true,
  "has_file": true,
  "file_path": "comparisonTable/7421_308_20250909.pdf",
  "full_path": "/home/wizice/regulation/www/static/pdf/comparisonTable/7421_308_20250909.pdf",
  "file_exists": true,
  "wzRuleSeq": 308,
  "wzRuleId": 7421,
  "wzPubNo": "11.5.1.",
  "wzRuleName": "의료기기 관리",
  "revision_date": "2025.09.09."
}
```

**응답** (파일 없음 - 404):
```json
{
  "success": false,
  "has_file": false,
  "message": "신구대비표가 등록되지 않았습니다.",
  "wzRuleSeq": 308
}
```

**cURL 예시**:
```bash
curl -X GET \
  'http://localhost:8800/api/v1/rule-public/comparison-table/308'
# 인증 불필요!
```

---

## 👥 사용자 가이드

### 관리자 화면 사용법

#### 1. 신규 규정에 신구대비표 추가

아직 관리자 UI에는 업로드 버튼이 없습니다. API를 직접 호출하거나, 향후 UI 개선 시 추가될 예정입니다.

**임시 방안 (API 직접 호출)**:
```bash
# 1. 로그인하여 세션 쿠키 얻기
curl -X POST 'http://localhost:8800/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"username":"sevpolicy","password":"sevpolicy123!@#"}' \
  -c cookies.txt

# 2. 신구대비표 업로드
curl -X POST \
  'http://localhost:8800/api/v1/rule/upload-comparison-table/308' \
  -b cookies.txt \
  -F 'comparison_file=@/path/to/comparison.pdf'
```

#### 2. 규정 개정 시 신구대비표 업로드

1. 관리자 화면에서 **"개정" 버튼** 클릭
2. 개정 정보 입력 및 DOCX/PDF 파일 업로드
3. 개정 완료 후, 새로 생성된 `wzRuleSeq` 확인
4. API를 통해 신구대비표 업로드 (위 임시 방안 참조)

### 사용자 화면에서 확인하기

#### 현행 규정에서 조회
- **위치**: 사용자 화면 → 규정 상세보기
- **버튼**: "신구대비표" 버튼 클릭
- **동작**:
  - 신규 방식: `/static/pdf/comparisonTable/{wzRuleSeq}.pdf`
  - 레거시 방식: `/static/pdf/comparisonTable/comparisonTable_{규정코드}.pdf`

#### 개정이력에서 조회
- **위치**: 사용자 화면 → 개정이력 탭
- **동작**: 각 개정판마다 개별 신구대비표 PDF 확인 가능
- **구현**: `severance.js:5707` - `openComparisonTablePdf()` 함수

**JavaScript 함수 시그니처**:
```javascript
async function openComparisonTablePdf(regulationCode, regulationName, wzRuleSeq) {
    // wzRuleSeq가 있으면 신규 방식 사용
    // 없으면 레거시 방식으로 폴백
}
```

---

## 🧪 테스트 가이드

### 자동 테스트 실행

#### Shell 스크립트 방식 (권장)

```bash
cd /home/wizice/regulation/fastapi
./test/comparison_table_test.sh
```

**테스트 항목**:
1. ✅ 로그인 테스트
2. ✅ 테스트 규정 설정 (wzRuleSeq=308)
3. ✅ 더미 PDF 파일 생성
4. ✅ 신구대비표 파일 업로드
5. ✅ 신구대비표 파일 조회
6. ✅ 레거시 파일 호환성 확인
7. ✅ 데이터베이스 wzFileComparison 컬럼 확인

**예상 출력**:
```
================================================
신구대비표 파일 관리 기능 통합 테스트
================================================

[1] 로그인 테스트
✅ 로그인 성공
   사용자: sevpolicy, 역할: admin

[2] 테스트 규정 설정
✅ 테스트 규정:
   - wzRuleSeq: 308
   - wzRuleCode: 11.5.1
   - wzRuleName: 의료기기 관리

...

✅ 모든 테스트 통과!
```

#### Python 스크립트 방식

```bash
cd /home/wizice/regulation/fastapi
python3 test/comparison_table_test.py
```

### 수동 테스트

#### 1. 데이터베이스 확인

```bash
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance
```

```sql
-- wzFileComparison 컬럼 확인
SELECT wzruleseq, wzruleid, wzpubno, wzfilecomparison
FROM wz_rule
WHERE wzfilecomparison IS NOT NULL
LIMIT 10;

-- 특정 규정 조회
SELECT * FROM wz_rule WHERE wzruleid = 7421 ORDER BY wzruleseq DESC;
```

#### 2. 파일 시스템 확인

```bash
# 신규 파일 확인
ls -lh /home/wizice/regulation/www/static/pdf/comparisonTable/*.pdf

# 레거시 파일 확인
ls -lh /home/wizice/regulation/www/static/pdf/comparisonTable/comparisonTable_*.pdf

# 백업 폴더 확인
ls -lh /home/wizice/regulation/www/static/pdf/comparisonTable_backup/
```

#### 3. API 엔드포인트 테스트

**Postman / Insomnia 사용**:

1. **로그인**:
   ```
   POST http://localhost:8800/api/v1/auth/login
   Content-Type: application/json

   {
     "username": "sevpolicy",
     "password": "sevpolicy123!@#"
   }
   ```

2. **파일 업로드**:
   ```
   POST http://localhost:8800/api/v1/rule/upload-comparison-table/308
   Cookie: [로그인에서 받은 쿠키]
   Content-Type: multipart/form-data

   comparison_file: [PDF 파일 선택]
   ```

3. **파일 조회** (인증 불필요):
   ```
   GET http://localhost:8800/api/v1/rule-public/comparison-table/308
   ```

---

## 🔧 문제 해결

### 문제 1: 파일 업로드 실패 (404 오류)

**증상**:
```json
{"detail": "규정을 찾을 수 없습니다.", "status_code": 404}
```

**원인**:
- 잘못된 `wzRuleSeq` 사용
- 규정이 삭제되었거나 존재하지 않음

**해결 방법**:
```bash
# 올바른 wzRuleSeq 확인
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -c \
  "SELECT wzruleseq, wzruleid, wzpubno FROM wz_rule WHERE wzruleid = 7421;"
```

### 문제 2: 인증 오류 (401 Unauthorized)

**증상**:
```json
{"detail": "Not authenticated", "status_code": 401}
```

**원인**:
- 세션 쿠키가 만료됨
- 쿠키가 전송되지 않음

**해결 방법**:
1. 다시 로그인하여 새 세션 쿠키 받기
2. API 호출 시 쿠키 포함 확인 (`-b cookies.txt` 또는 `-H "Cookie: ..."`)

### 문제 3: 파일이 보이지 않음

**증상**: 업로드는 성공했지만 사용자 화면에서 신구대비표 버튼이 작동하지 않음

**원인**:
- 파일 경로가 잘못됨
- 파일 권한 문제

**해결 방법**:
```bash
# 파일 존재 확인
ls -la /home/wizice/regulation/www/static/pdf/comparisonTable/7421_308_*.pdf

# 권한 확인 및 수정
chmod 644 /home/wizice/regulation/www/static/pdf/comparisonTable/7421_308_*.pdf
```

### 문제 4: 레거시 파일과 신규 파일 충돌

**증상**: 같은 규정에 대해 레거시 파일과 신규 파일이 모두 있을 때 어떤 파일이 표시되는지 모름

**동작 방식**:
1. **wzRuleSeq가 있으면**: 신규 방식 우선
   - 경로: `/static/pdf/comparisonTable/{wzRuleSeq}.pdf`
2. **wzRuleSeq가 없거나 신규 파일이 없으면**: 레거시 방식으로 폴백
   - 경로: `/static/pdf/comparisonTable/comparisonTable_{규정코드}.pdf`

**권장 사항**:
- 새로 개정하는 규정은 신규 방식 사용
- 기존 레거시 파일은 그대로 유지 (하위 호환성)

---

## 📝 추가 개선 사항 (향후 계획)

### 1. 관리자 UI에 업로드 버튼 추가

현재는 API 직접 호출로만 업로드 가능합니다. 향후 다음 기능 추가 예정:

- **위치**: 규정 상세 페이지 또는 개정 모달
- **기능**: 드래그 앤 드롭으로 PDF 업로드
- **미리보기**: 업로드 전 PDF 미리보기
- **이력**: 기존에 업로드한 신구대비표 목록 표시

### 2. JSON 서비스 파일 통합

`applib/JSON_ALL.py`를 수정하여 병합된 JSON에 신구대비표 정보 포함:

```python
"신구대비표": {
    "파일경로": "comparisonTable/7421_308_20250909.pdf",
    "업로드일시": "2025-11-13 15:30:00",
    "파일크기": "2.5MB"
}
```

### 3. 다중 파일 버전 관리

같은 규정에 대해 여러 신구대비표를 업로드할 수 있도록:
- 버전 히스토리 테이블 추가
- 사용자 화면에서 버전 선택 가능

---

## 📚 참고 자료

### 관련 파일
- **백엔드 API**: `/home/wizice/regulation/fastapi/api/service_rule_editor.py` (lines 1935-2102)
- **프론트엔드 JS**: `/home/wizice/regulation/www/static/js/severance.js` (lines 5707-5774)
- **데이터베이스 스키마**: `wz_rule` 테이블 (wzFileComparison 컬럼)
- **테스트 스크립트**:
  - Shell: `/home/wizice/regulation/fastapi/test/comparison_table_test.sh`
  - Python: `/home/wizice/regulation/fastapi/test/comparison_table_test.py`

### Git Commit
개발 완료 후 커밋 메시지:
```
feat: 신구대비표 버전별 파일 관리 기능 추가

- wzFileComparison 컬럼 추가 (wz_rule 테이블)
- POST /api/v1/rule/upload-comparison-table/{rule_id} 엔드포인트
- GET /api/v1/rule/comparison-table/{rule_id} 엔드포인트
- 파일명: {wzRuleId}_{wzRuleSeq}_{date}.pdf 형식
- 자동 백업 기능 (comparisonTable_backup/)
- 레거시 파일 하위 호환성 유지
- JavaScript openComparisonTablePdf() 함수 수정
- 통합 테스트 스크립트 작성 (Shell, Python)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

**최종 업데이트**: 2025년 11월 13일
**작성자**: Claude AI Assistant
**검토자**: wizice
