# 부록 PDF 조회 로깅 - 별도 스크립트 방식

## 🎯 설계 원칙

**기존 시스템에 영향 없이 별도의 로깅 시스템 구축**

- ✅ 기존 JavaScript 파일 수정 안 함
- ✅ 기존 부록 열기 기능 그대로 유지
- ✅ PDF Viewer에 별도 스크립트 추가만으로 로깅 구현

---

## 📂 구현 파일

### 1. 새로 생성된 파일

#### `/home/wizice/regulation/www/static/js/pdf-view-logger.js`
- **역할**: PDF Viewer가 로드될 때 자동으로 부록 조회 로깅
- **동작 방식**:
  1. PDF Viewer HTML에서 자동 실행
  2. URL 파라미터에서 PDF 파일명 추출
  3. 파일명이 부록 패턴인지 확인
  4. 부록이면 FastAPI 로깅 API 호출
  5. 로깅 실패해도 PDF는 정상 표시

#### `/home/wizice/regulation/www/static/viewer/web/viewer.html` (수정)
- **수정 내용**: `pdf-view-logger.js` 스크립트 추가 (line 43)
- **영향**: PDF Viewer 로드 시 자동으로 로깅 스크립트 실행

---

## 🔄 동작 흐름

```
사용자가 부록 클릭
    ↓
[기존 코드] openAppendixPdf() 실행
    ↓
[기존 코드] getAppendixPdfUrl() 호출
    ↓
[기존 코드] PDF Viewer 열림
    URL: /static/viewer/web/viewer.html?file=/static/pdf/파일명.pdf
    ↓
[신규] PDF Viewer HTML 로드
    ↓
[신규] pdf-view-logger.js 실행
    ↓
[신규] URL에서 파일명 추출: "1.2.1._부록1._구두처방_의약품_목록.pdf"
    ↓
[신규] 파일명 파싱: rule_pubno="1.2.1.", appendix_name="부록1. 구두처방 의약품 목록"
    ↓
[신규] FastAPI 로깅 API 호출 (백그라운드)
    URL: https://policyeditor.wizice.com:8443/api/v1/pdf-file/파일명.pdf
    ↓
[신규] regulation_view_logs 테이블에 INSERT
    ↓
✅ PDF 정상 표시 + 로그 기록 완료
```

---

## 📝 코드 분석

### pdf-view-logger.js 핵심 로직

#### 1. URL에서 PDF 파일명 추출
```javascript
function getPdfFileFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const fileParam = urlParams.get('file');

    // /static/pdf/파일명.pdf → 파일명.pdf
    const match = decodedFile.match(/\/static\/pdf\/(.+\.pdf)$/i);
    return match ? match[1] : null;
}
```

#### 2. 부록 파일명 파싱
```javascript
function parseAppendixFilename(fileName) {
    // 예: "1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf"
    const pattern = /^([0-9.]+)\.?_부록(\d+)\._(.+?)(?:_\d{8})?(?:개정|검토)?\.pdf$/;
    const match = fileName.match(pattern);

    return {
        rulePubno: '1.2.1.',
        appendixNo: '1',
        appendixName: '부록1. 구두처방 의약품 목록',
        fullName: '1.2.1. 부록1. 구두처방 의약품 목록',
        isAppendix: true
    };
}
```

#### 3. 로깅 API 호출
```javascript
async function logPdfView(fileName, parsedInfo) {
    const apiUrl = `https://policyeditor.wizice.com:8443/api/v1/pdf-file/${encodeURIComponent(fileName)}`;

    // no-cors 모드로 요청 (CORS 에러 방지)
    fetch(apiUrl, {
        method: 'GET',
        mode: 'no-cors',
        credentials: 'omit'
    });

    // 로깅 실패해도 PDF는 정상 표시
}
```

---

## 🧪 테스트 방법

### 1. 브라우저 테스트

#### 부록 클릭
1. https://policy.wizice.com:8443/ 접속
2. **Ctrl + Shift + R** (강력 새로고침)
3. **1.2.2. PRN 처방** 확장
4. **부록 1. PRN 처방 의약품 목록** 클릭

#### 콘솔 로그 확인
```
[PDF Logger] PDF 파일 감지: 1.2.2._부록1._PRN_처방_의약품_목록.pdf
[PDF Logger] 부록 파일 확인: 1.2.2. 부록1. PRN 처방 의약품 목록
[PDF Logger] 로깅 시작: 1.2.2._부록1._PRN_처방_의약품_목록.pdf
[PDF Logger] API URL: https://policyeditor.wizice.com:8443/api/v1/pdf-file/...
[PDF Logger] ✅ 로깅 요청 전송: 1.2.2. 부록1. PRN 처방 의약품 목록
```

#### PDF 표시 확인
- ✅ PDF가 정상적으로 표시되어야 함
- ✅ 로깅 실패해도 PDF는 정상 표시

### 2. 데이터베이스 확인

```bash
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance --pset pager=off -c \
"SELECT log_id, rule_id, rule_name, rule_pubno, viewed_at
 FROM regulation_view_logs
 WHERE rule_id IS NULL
 ORDER BY viewed_at DESC
 LIMIT 5;"
```

**예상 결과**:
```
 log_id | rule_id |          rule_name          | rule_pubno |           viewed_at
--------+---------+-----------------------------+------------+-------------------------------
    465 |         | 부록1. PRN 처방 의약품 목록 | 1.2.2.     | 2025-11-17 13:00:00.000000+09
```

### 3. 대시보드 확인

- **URL**: https://policyeditor.wizice.com:8443/admin/view-analytics
- **TOP 10 테이블**: 부록 조회가 나타나야 함

---

## 🔍 문제 해결 가이드

### 문제 1: 로그가 기록되지 않음

**확인 사항**:
```bash
# 1. PDF Viewer HTML에 스크립트가 추가되었는지 확인
grep "pdf-view-logger.js" /home/wizice/regulation/www/static/viewer/web/viewer.html

# 2. JavaScript 파일이 존재하는지 확인
ls -lh /home/wizice/regulation/www/static/js/pdf-view-logger.js

# 3. FastAPI 서비스가 실행 중인지 확인
ps aux | grep uvicorn | grep 8800
```

**브라우저 콘솔 확인**:
- `[PDF Logger]` 로그가 나타나는지 확인
- 에러 메시지가 있는지 확인

### 문제 2: PDF가 열리지 않음

**원인**: 이 솔루션은 PDF 열기 기능을 수정하지 않음

**확인**:
```bash
# 기존 JavaScript 파일이 변경되지 않았는지 확인
git diff www/static/js/severance.js
git diff www/static/js/severance_comm.js

# 변경된 파일이 있다면 되돌리기
git checkout www/static/js/severance.js
git checkout www/static/js/severance_comm.js
```

### 문제 3: CORS 에러

**솔루션**: `mode: 'no-cors'` 사용으로 이미 해결됨

---

## 📊 장점

### ✅ 기존 시스템에 영향 없음
- 기존 JavaScript 파일 수정 안 함
- 기존 부록 열기 기능 그대로 유지
- 기존 PDF 경로 그대로 사용

### ✅ 확장성
- 다른 로깅 기능 추가 용이
- PDF Viewer에서 추가 기능 구현 가능
- 스크립트만 수정하면 됨

### ✅ 유지보수 용이
- 로깅 로직이 별도 파일로 분리
- 문제 발생 시 스크립트만 비활성화
- 기존 시스템에 영향 없이 수정 가능

---

## 📚 관련 파일

### 신규 파일
- `www/static/js/pdf-view-logger.js` - 부록 로깅 스크립트

### 수정 파일
- `www/static/viewer/web/viewer.html` - 스크립트 추가 (1줄)

### 백엔드 파일 (기존)
- `fastapi/api/service_pdf_file_logging.py` - PDF 로깅 API
- `fastapi/app.py` - 라우터 등록

---

## 🎯 다음 단계

1. **브라우저 테스트**: 부록 클릭 시 정상 작동 확인
2. **로그 확인**: 데이터베이스에 부록 로그 기록 확인
3. **대시보드 확인**: TOP 10에 부록 표시 확인

---

**작성일**: 2025-11-17
**방식**: 별도 스크립트 추가 (기존 코드 수정 없음)
**작성자**: Claude AI Assistant
