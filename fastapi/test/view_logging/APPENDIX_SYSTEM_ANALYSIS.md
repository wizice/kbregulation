# 📊 부록 PDF 시스템 현황 분석

## 🎯 Step 1: 부록 PDF 파일 구조

### 파일 위치
```
/home/wizice/regulation/www/static/pdf/
```

### 파일 개수
```bash
총 269개의 PDF 파일
```

### 파일명 형식
```
1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf
10.2.1._부록2._임상권한 관리절차 가이드라인_2022503검토.pdf
```

**패턴**:
```
{규정코드}._부록{번호}._{부록명}_{날짜}.pdf
```

---

## 🎯 Step 2: 부록 열람 방식

### JavaScript 함수 (severance_comm.js)
```javascript
// 694줄: openAppendixPdf() 함수
async function openAppendixPdf(regulationCode, appendixIndex, appendixName)
```

### 열람 플로우
```
사용자 클릭
 ↓
openAppendixPdf(regulationCode, appendixIndex, appendixName)
 ↓
Step 1: API에서 파일명 찾기 (getAppendixFileFromAPI)
 ↓
Step 2: PDF 파일명 획득
 ↓
Step 3: summary_severance.json에서 wzRuleSeq 찾기
 ↓
Step 4: API URL 생성
  /api/v1/appendix/download/{ruleSeq}/{fileName}
 ↓
Step 5: API 실패 시 Fallback (getAppendixPdfUrl)
  /static/pdf/{fileName} 직접 접근
 ↓
Step 6: PDF Viewer로 열기
  /static/viewer/web/viewer.html?file={pdfUrl}
```

### 실제 사용되는 경로

**API 방식** (우선):
```javascript
const downloadUrl = `/api/v1/appendix/download/${ruleSeq}/${encodeURIComponent(fileNameWithTimestamp)}`;
pdfUrl = `${currentDomain}/static/viewer/web/viewer.html?file=${encodeURIComponent(downloadUrl)}`;
```

**Fallback 방식** (API 실패 시):
```javascript
pdfUrl = getAppendixPdfUrl(regulationCode, appendixIndex, appendixName);
// 결과: /static/pdf/{fileName}
```

---

## 🎯 Step 3: 문제점

### 1. API 엔드포인트 미존재
```
/api/v1/appendix/download/{ruleSeq}/{fileName}
```
이 엔드포인트가 실제로 존재하지 않음!

**확인 결과**:
- `fastapi/api/router_appendix.py`: 업로드 관련만 있음
- `fastapi/app.py`: 해당 라우트 없음

### 2. 실제로는 Fallback 사용 중
```javascript
// severance_comm.js 801줄
pdfUrl = getAppendixPdfUrl(regulationCode, appendixIndex, appendixName);
// → /static/pdf/ 직접 접근
```

nginx가 `/static/pdf/`를 직접 서빙하고 있음!

---

## 🎯 Step 4: 로깅 필요성

### 현재 상황
```
사용자 부록 클릭
 ↓
nginx가 /static/pdf/파일.pdf 직접 서빙
 ↓
로그 기록 없음 ❌
```

### 목표
```
사용자 부록 클릭
 ↓
FastAPI를 통해 PDF 서빙 + 자동 로깅
 ↓
regulation_view_logs 테이블에 기록 ✅
```

---

## 🎯 Step 5: 로깅 시스템 설계

### Option 1: JSON 파일 방식과 동일하게 (권장)

**FastAPI API 생성**:
```python
# fastapi/api/service_pdf_file_logging.py (신규)

@router.get("/pdf/{file_name}")
async def serve_pdf_with_logging(file_name: str):
    # 1. PDF 파일 읽기
    # 2. 파일명에서 규정 정보 추출
    #    예: "1.2.1._부록1._구두처방_의약품_목록.pdf"
    #    → rule_pubno: "1.2.1."
    #    → appendix_no: "1"
    #    → appendix_name: "부록1. 구두처방 의약품 목록"
    # 3. regulation_view_logs에 INSERT
    # 4. PDF 파일 반환 (FileResponse)
```

**JavaScript 수정**:
```javascript
// severance_comm.js의 getAppendixPdfUrl() 수정
// Before
return `/static/pdf/${fileName}`;

// After
return `https://policyeditor.wizice.com:8443/api/v1/pdf-file/${fileName}`;
```

### Option 2: 부록 전용 테이블 생성 (더 상세한 분석 가능)

**새 테이블 생성**:
```sql
CREATE TABLE appendix_view_logs (
    log_id BIGSERIAL PRIMARY KEY,
    rule_id INTEGER,           -- 내규 ID
    rule_pubno VARCHAR(100),   -- 내규 공포번호
    appendix_no VARCHAR(10),   -- 부록 번호
    appendix_name VARCHAR(500),-- 부록 명칭
    file_name VARCHAR(500),    -- PDF 파일명
    viewed_at TIMESTAMPTZ DEFAULT NOW()
);
```

**장점**:
- 부록 전용 통계 가능
- 부록별 조회수 TOP 10
- 어떤 내규의 부록이 많이 조회되는지 분석

**단점**:
- 테이블 관리 추가
- 대시보드에 별도 섹션 필요

---

## 🎯 Step 6: 권장 방안

### 방안: Option 1 (기존 테이블 활용)

**이유**:
1. 단순함 - 기존 `regulation_view_logs` 테이블 재사용
2. 대시보드 통합 - 별도 섹션 불필요
3. 구현 빠름 - JSON 로깅과 동일한 패턴

**구현 방법**:
```python
# regulation_view_logs 테이블 구조
INSERT INTO regulation_view_logs
    (rule_id, rule_name, rule_pubno, viewed_at)
VALUES
    (NULL,  -- 부록은 rule_id 없음 (또는 파싱)
     '부록1. 구두처방 의약품 목록',  -- appendix_name
     '1.2.1.',  -- rule_pubno (파일명에서 추출)
     NOW())
```

**파일명 파싱**:
```python
# 예: "1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf"
import re

pattern = r'^([0-9.]+)\.?_부록(\d+)\._(.+?)(?:_\d{8})?(?:개정|검토)?\.pdf$'
match = re.match(pattern, file_name)

if match:
    rule_pubno = match.group(1)       # "1.2.1"
    appendix_no = match.group(2)      # "1"
    appendix_name = match.group(3)    # "구두처방_의약품_목록"
```

---

## 🎯 Step 7: 구현 계획

### 1. FastAPI PDF 서빙 API 생성
```python
# fastapi/api/service_pdf_file_logging.py
@router.get("/pdf-file/{file_name}")
async def serve_pdf_with_logging(file_name: str):
    # PDF 서빙 + 자동 로깅
```

### 2. app.py에 라우터 등록
```python
from api.service_pdf_file_logging import router as pdf_file_router
app.include_router(pdf_file_router)
```

### 3. JavaScript 수정
```javascript
// severance_comm.js의 getAppendixPdfUrl() 또는 fallback 부분
```

### 4. 테스트
```
1. 부록 클릭
2. 브라우저 콘솔 확인
3. DB 확인
4. 대시보드 확인
```

---

## 🎯 Step 8: 주의사항

### 1. 기존 시스템에 영향 없도록
- ✅ API 실패 시 fallback 유지
- ✅ PDF viewer는 그대로 사용
- ✅ 파일 경로만 변경

### 2. 파일명 파싱 실패 대비
- ✅ 파싱 실패 시에도 PDF는 반환
- ✅ 로깅만 실패 (silent fail)
- ✅ 에러 로그 남기기

### 3. 성능
- ✅ PDF 파일 크기 고려 (일부 500KB 이상)
- ✅ 캐시 헤더 설정
- ✅ nginx보다 느릴 수 있음 (FastAPI 경유)

---

## 📊 예상 효과

### Before (현재)
```
부록 269개 파일
조회 로그: 없음 ❌
```

### After (구현 후)
```
부록 269개 파일
조회 로그: regulation_view_logs 테이블에 기록 ✅

대시보드에서 확인 가능:
- TOP 10에 "부록1. 구두처방 의약품 목록" 등장
- 부록 조회 추이 확인
- 어떤 부록이 인기 있는지 분석
```

---

**작성일**: 2025-01-14
**다음 단계**: 로깅 시스템 구현
**작성자**: Claude AI Assistant
