# 📊 부록 PDF 조회 로깅 시스템 - 테스트 가이드

## 🎯 구현 완료 사항

### 1. FastAPI PDF 서빙 API
- **파일**: `fastapi/api/service_pdf_file_logging.py`
- **엔드포인트**: `GET /api/v1/pdf-file/{file_name}`
- **기능**:
  - PDF 파일 서빙 (FileResponse)
  - 파일명 파싱 (규정코드, 부록번호, 부록명)
  - 자동 조회 로그 기록 (regulation_view_logs 테이블)
  - UTF-8 인코딩 처리 (한글 파일명 지원)

### 2. 파일명 파싱 로직
```python
# 입력 예시
"1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf"

# 파싱 결과
{
    'rule_pubno': '1.2.1.',
    'appendix_no': '1',
    'appendix_name': '부록1. 구두처방 의약품 목록',
    'full_name': '1.2.1. 부록1. 구두처방 의약품 목록'
}
```

### 3. 데이터베이스 스키마 수정
```sql
-- rule_id 컬럼을 NULL 허용으로 변경
ALTER TABLE regulation_view_logs
ALTER COLUMN rule_id DROP NOT NULL;

-- 부록 로그는 rule_id = NULL로 저장됨
```

### 4. JavaScript 수정
- **파일**: `www/static/js/severance_comm.js`
- **함수**: `getAppendixPdfUrl()` (line 691)
- **변경 내용**:
  ```javascript
  // Before
  return `/static/pdf/${fileName}`;

  // After
  const pdfApiUrl = `https://policyeditor.wizice.com:8443/api/v1/pdf-file/${encodeURIComponent(pdfFileName)}`;
  return `${currentDomain}/static/viewer/web/viewer.html?file=${encodeURIComponent(pdfApiUrl)}`;
  ```

---

## 🧪 테스트 시나리오

### Test 1: API 엔드포인트 확인
```bash
# PDF 파일 다운로드 테스트
curl -s "http://localhost:8800/api/v1/pdf-file/1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf" | file -

# 예상 결과:
# /dev/stdin: PDF document, version 1.7, 1 page(s)
```

### Test 2: 로그 기록 확인
```bash
# 데이터베이스 확인
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -c \
"SELECT log_id, rule_id, rule_name, rule_pubno, viewed_at
 FROM regulation_view_logs
 WHERE rule_id IS NULL
 ORDER BY viewed_at DESC
 LIMIT 10;"

# 예상 결과:
# log_id | rule_id |          rule_name          | rule_pubno |           viewed_at
# -------+---------+-----------------------------+------------+-------------------------------
#    451 |         | 부록1. 구두처방 의약품 목록 | 1.2.1.     | 2025-11-17 11:32:17.020377+09
```

### Test 3: 파일명 파싱 테스트
```bash
# 다양한 파일명 패턴 테스트
curl -s "http://localhost:8800/api/v1/pdf-file/10.2.1._부록2._임상권한_관리절차_가이드라인_20220503검토.pdf" | file -

# DB 확인
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -c \
"SELECT rule_name, rule_pubno FROM regulation_view_logs WHERE rule_name LIKE '%임상권한%' ORDER BY viewed_at DESC LIMIT 1;"

# 예상 결과:
# rule_name: "부록2. 임상권한 관리절차 가이드라인"
# rule_pubno: "10.2.1."
```

### Test 4: 브라우저 테스트
1. **URL 접속**: https://policy.wizice.com:8443/
2. **부록 클릭**: 임의의 내규에서 부록 링크 클릭
3. **PDF 확인**: PDF Viewer에서 정상 표시되는지 확인
4. **로그 확인**:
   ```bash
   PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -c \
   "SELECT * FROM regulation_view_logs ORDER BY viewed_at DESC LIMIT 1;"
   ```

### Test 5: 대시보드 확인
1. **URL 접속**: https://policyeditor.wizice.com:8443/admin/view-analytics
2. **TOP 10 테이블 확인**: 부록 로그가 나타나는지 확인
3. **조회 추이 차트**: 부록 조회가 반영되는지 확인

---

## 📊 테스트 결과 (2025-11-17)

### ✅ API 엔드포인트
```bash
$ curl -s "http://localhost:8800/api/v1/pdf-file/1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf" | file -
/dev/stdin: PDF document, version 1.7, 1 page(s)
```
**결과**: PASS ✅

### ✅ 로그 기록
```
 log_id | rule_id |          rule_name          | rule_pubno |           viewed_at
--------+---------+-----------------------------+------------+-------------------------------
    451 |         | 부록1. 구두처방 의약품 목록 | 1.2.1.     | 2025-11-17 11:32:17.020377+09
```
**결과**: PASS ✅
- rule_id: NULL (부록은 rule_id 없음)
- rule_name: 정확히 파싱됨
- rule_pubno: "1.2.1." 형식 정확

### ✅ 파일명 파싱
- 정규식 패턴 매칭 성공
- 언더스코어 → 공백 변환 성공
- 날짜/상태 제거 성공
- 점(.) 처리 정확

### ⏳ 브라우저 테스트
**상태**: 사용자 테스트 필요
**방법**:
1. https://policy.wizice.com:8443/ 접속
2. 부록 클릭
3. Ctrl+Shift+R (강력 새로고침)
4. 대시보드 확인

---

## 🎯 통합 테스트 스크립트

### 자동 테스트 스크립트 생성
```bash
#!/bin/bash
# test_pdf_logging.sh

echo "=== 부록 PDF 조회 로깅 시스템 테스트 ==="

# Test 1: API 엔드포인트
echo -e "\n[Test 1] API 엔드포인트 확인"
PDF_TYPE=$(curl -s "http://localhost:8800/api/v1/pdf-file/1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf" | file - | grep -o "PDF document")
if [ "$PDF_TYPE" = "PDF document" ]; then
    echo "✅ PASS: PDF 파일 정상 반환"
else
    echo "❌ FAIL: PDF 파일 반환 실패"
fi

# Test 2: 로그 기록 확인
echo -e "\n[Test 2] 로그 기록 확인"
LOG_COUNT=$(PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -c \
"SELECT COUNT(*) FROM regulation_view_logs WHERE rule_id IS NULL AND viewed_at > NOW() - INTERVAL '1 minute';")
if [ "$LOG_COUNT" -gt 0 ]; then
    echo "✅ PASS: 로그 기록됨 (최근 1분 내 $LOG_COUNT건)"
else
    echo "❌ FAIL: 로그 기록 안됨"
fi

# Test 3: 파싱 정확도 확인
echo -e "\n[Test 3] 파일명 파싱 정확도"
PARSED_NAME=$(PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -c \
"SELECT rule_name FROM regulation_view_logs WHERE rule_id IS NULL ORDER BY viewed_at DESC LIMIT 1;" | xargs)
EXPECTED="부록1. 구두처방 의약품 목록"
if [ "$PARSED_NAME" = "$EXPECTED" ]; then
    echo "✅ PASS: 파일명 파싱 정확"
else
    echo "❌ FAIL: 파일명 파싱 오류 (실제: $PARSED_NAME)"
fi

echo -e "\n=== 테스트 완료 ==="
```

### 실행 방법
```bash
cd /home/wizice/regulation/fastapi/test/view_logging
chmod +x test_pdf_logging.sh
./test_pdf_logging.sh
```

---

## 🔍 문제 해결 가이드

### 문제 1: 로그가 기록되지 않음
**원인**:
- FastAPI 서비스 미재시작
- JavaScript 캐시
- 데이터베이스 연결 문제

**해결**:
```bash
# 1. FastAPI 재시작 확인
ps aux | grep uvicorn

# 2. 브라우저 강력 새로고침
# Ctrl+Shift+R (Chrome/Edge)
# Cmd+Shift+R (Mac)

# 3. DB 연결 테스트
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -c "SELECT NOW();"
```

### 문제 2: PDF가 표시되지 않음
**원인**:
- PDF 파일 경로 오류
- 파일명 인코딩 문제
- CORS 이슈

**해결**:
```bash
# 1. 파일 존재 확인
ls -lh "/home/wizice/regulation/www/static/pdf/1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf"

# 2. API 직접 테스트
curl -v "http://localhost:8800/api/v1/pdf-file/1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf" -o test.pdf

# 3. FastAPI 로그 확인
tail -f /home/wizice/regulation/fastapi/logs/app.log
```

### 문제 3: 파일명 파싱 실패
**원인**:
- 파일명 형식이 패턴과 다름
- 정규식 오류

**확인**:
```python
# Python 콘솔에서 테스트
import re

pattern = r'^([0-9.]+)\.?_부록(\d+)\._(.+?)(?:_\d{8})?(?:개정|검토)?\.pdf$'
file_name = "1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf"
match = re.match(pattern, file_name)

if match:
    print(f"규정코드: {match.group(1)}")
    print(f"부록번호: {match.group(2)}")
    print(f"부록명: {match.group(3)}")
```

---

## 📈 성능 고려사항

### 캐싱
- **현재 설정**: `Cache-Control: public, max-age=3600` (1시간)
- **효과**: 동일 PDF 재조회 시 브라우저 캐시 사용

### 로깅 실패 처리
- **패턴**: Silent Fail
- **장점**: 로깅 실패해도 PDF는 정상 반환
- **로그**: 실패 시 WARNING 레벨 로그 남김

### 데이터베이스 인덱스
```sql
-- 필요 시 인덱스 추가
CREATE INDEX idx_regulation_view_logs_viewed_at
ON regulation_view_logs(viewed_at DESC);

CREATE INDEX idx_regulation_view_logs_rule_pubno
ON regulation_view_logs(rule_pubno);
```

---

## 🎯 다음 단계

### 필수 테스트
- [x] API 엔드포인트 테스트
- [x] 로그 기록 테스트
- [x] 파일명 파싱 테스트
- [ ] 브라우저 통합 테스트 (사용자 필요)
- [ ] 대시보드 확인 (사용자 필요)

### 선택 사항
- [ ] 부록 전용 통계 페이지 (별도 개발 필요)
- [ ] 부록별 조회수 TOP 10 (대시보드 추가)
- [ ] 파일명 파싱 패턴 확장 (다양한 형식 지원)

---

**작성일**: 2025-11-17
**테스트 완료**: API, DB, 파일명 파싱
**대기 중**: 사용자 브라우저 테스트
**작성자**: Claude AI Assistant
