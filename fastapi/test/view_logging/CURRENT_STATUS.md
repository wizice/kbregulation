# 🔍 현재 상태 점검

## 📋 구현 완료된 항목

### 1. 데이터베이스
```sql
-- regulation_view_logs 테이블
✅ 존재함
✅ 외래키 제약 제거됨
✅ 현재 레코드: 0건
```

### 2. 백엔드 API
```python
# 엔드포인트: POST /api/v1/admin/view-stats/public/log-view
# 파일: fastapi/api/service_regulation_view_stats.py (424-486줄)

✅ 구현 완료
✅ curl 직접 호출 시 작동 확인됨
```

**테스트 결과**:
```bash
curl -X POST "http://localhost:8800/api/v1/admin/view-stats/public/log-view" \
  -H "Content-Type: application/json" \
  -d '{"rule_id": 8902, "rule_name": "테스트", "rule_pubno": "1.1.1"}'

# 응답: {"success":true,"message":"Logged successfully"}
# DB 확인: 로그 기록됨
```

### 3. 프론트엔드 JavaScript
```javascript
// 파일: www/static/js/regulation-view-logger.js
// 위치: https://policy.wizice.com:8443/static/js/regulation-view-logger.js

✅ 파일 존재함
✅ 서버에서 정상 서빙됨 (HTTP 200)
✅ Content-Type: application/javascript
```

**주요 함수**:
```javascript
RegulationViewLogger.logView(ruleId, ruleName, rulePubno)
```

**API 엔드포인트 설정**:
```javascript
API_ENDPOINT: 'https://policyeditor.wizice.com:8443/api/v1/admin/view-stats/public/log-view'
```

### 4. HTML 통합
```html
<!-- www/severance_page_static.html -->

✅ 스크립트 로드 (895줄)
<script src="/static/js/regulation-view-logger.js?ts=202501141830"></script>

✅ 로깅 호출 코드 추가 (390-410줄)
displayRegulationDetail() 함수 내부
```

---

## ❌ 문제점

### 실제 로그가 쌓이지 않음

```bash
# DB 확인
SELECT COUNT(*) FROM regulation_view_logs;
# 결과: 0건

# 애플리케이션 로그 확인
tail -100 /home/wizice/regulation/fastapi/logs/app.log | grep "log-view"
# 결과: 아무것도 없음 (API 호출 자체가 안 되고 있음)
```

### 가능한 원인

1. **브라우저 캐시**
   - 사용자가 오래된 HTML/JS를 보고 있을 수 있음
   - 타임스탬프: `?ts=202501141830`

2. **JavaScript 로드 실패**
   - 브라우저 콘솔 에러
   - 네트워크 에러

3. **JavaScript 실행 안 됨**
   - `RegulationViewLogger` 객체가 undefined
   - `displayRegulationDetail` 함수 내부 로직이 실행 안 됨

4. **CORS 문제**
   - policy.wizice.com → policyeditor.wizice.com 크로스 도메인
   - 현재 CORS 설정: `allow_origins=["*"]` (모든 도메인 허용)

5. **네트워크 경로 문제**
   - HTTPS 인증서 문제
   - 방화벽

---

## 🧪 디버깅 방법

### 1. 테스트 페이지 접속
```
https://policy.wizice.com:8443/test_view_logging.html
```

**확인 사항**:
- "테스트 로그 전송" 버튼 클릭
- 브라우저 콘솔(F12) 확인
- 결과 메시지 확인

**예상 결과**:
```
✅ 로그 전송 완료! DB를 확인하세요.
```

### 2. 실제 서비스 페이지 디버깅
```
https://policy.wizice.com:8443/
→ 아무 내규나 클릭
```

**브라우저 콘솔(F12)에서 확인**:
```javascript
// 1. RegulationViewLogger 로드 확인
console.log(window.RegulationViewLogger);
// 예상: {logView: ƒ, setEnabled: ƒ, ...}

// 2. 수동 호출 테스트
await RegulationViewLogger.logView(9999, '테스트', 'TEST');
// 예상: "✅ View logged: 테스트"
```

**네트워크 탭 확인**:
- `/static/js/regulation-view-logger.js` 로드 확인 (200 OK)
- `POST /api/v1/admin/view-stats/public/log-view` 호출 확인
- 응답: `{"success":true}`

### 3. 실시간 로그 모니터링
```bash
# 터미널에서 실행
tail -f /home/wizice/regulation/fastapi/logs/app.log | grep --line-buffered "log-view\|View logged"
```

내규 클릭 시 다음 메시지가 나와야 함:
```
✅ View logged (public): [내규명] (ID: [번호])
```

### 4. DB 실시간 확인
```bash
# 터미널에서 실행
watch -n 2 'PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -c "SELECT COUNT(*) FROM regulation_view_logs;"'
```

---

## 🔧 문제별 해결 방법

### Case 1: RegulationViewLogger가 undefined
**증상**:
```javascript
console.log(window.RegulationViewLogger);
// undefined
```

**원인**: JavaScript 파일 로드 실패

**해결**:
1. 브라우저 강력 새로고침 (Ctrl+Shift+R)
2. 네트워크 탭에서 regulation-view-logger.js 확인
3. 404 에러 → 파일 경로 확인
4. CORS 에러 → CORS 설정 확인

---

### Case 2: API 호출 시 네트워크 에러
**증상**:
```
POST https://policyeditor.wizice.com:8443/api/v1/admin/view-stats/public/log-view
ERR_CONNECTION_REFUSED
```

**원인**: FastAPI 서버가 꺼져있음

**해결**:
```bash
# 서버 실행 확인
ps aux | grep uvicorn

# 서버 재시작
cd /home/wizice/regulation/fastapi
uvicorn app:app --host 0.0.0.0 --port 8800 --reload
```

---

### Case 3: CORS 에러
**증상**:
```
Access to fetch at '...' from origin 'https://policy.wizice.com:8443'
has been blocked by CORS policy
```

**원인**: CORS 설정 문제

**해결**:
```python
# app.py (이미 설정됨)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Case 4: displayRegulationDetail 함수가 실행 안 됨
**증상**:
- 내규는 정상 표시됨
- 하지만 로그 전송 메시지가 콘솔에 없음

**원인**: 로깅 코드가 실행 전에 에러 발생

**해결**:
```javascript
// severance_page_static.html (390-410줄)
// 이미 try-catch로 감싸져 있음
```

---

## ✅ 정상 작동 시 예상 플로우

### 사용자 액션
```
1. https://policy.wizice.com:8443/ 접속
2. "1.1.1. 정확한 환자 확인" 클릭
```

### 브라우저 동작
```
3. /severance_page_static.html?chapter=8902_1.1.1...&code=5.4.1. 로드
4. /static/js/regulation-view-logger.js 로드 완료
5. displayRegulationDetail(regulation, "8902_1.1.1...", ...) 실행
6. RegulationViewLogger.logView(8902, "1.1.1. 정확한 환자 확인", "5.4.1.") 호출
7. POST https://policyeditor.wizice.com:8443/api/v1/admin/view-stats/public/log-view
```

### 서버 동작
```
8. FastAPI 로그: "✅ View logged (public): 1.1.1. 정확한 환자 확인 (ID: 8902)"
9. DB INSERT: regulation_view_logs 테이블에 1건 추가
```

### 브라우저 콘솔 출력
```
📊 Logging view: 1.1.1. 정확한 환자 확인 (ID: 8902)
✅ View logged: 1.1.1. 정확한 환자 확인
```

### DB 확인
```sql
SELECT * FROM regulation_view_logs ORDER BY viewed_at DESC LIMIT 1;

-- 결과:
-- rule_id: 8902
-- rule_name: 1.1.1. 정확한 환자 확인
-- rule_pubno: 5.4.1.
-- viewed_at: 2025-11-14 18:00:00
```

### 대시보드 확인
```
https://policyeditor.wizice.com:8443/admin/view-analytics

TOP 10:
순위  공포번호  내규 명칭                     조회수  마지막 조회
1     5.4.1.   1.1.1. 정확한 환자 확인    1      방금 전
```

---

## 📝 다음 단계

1. **테스트 페이지 확인**
   ```
   https://policy.wizice.com:8443/test_view_logging.html
   → "테스트 로그 전송" 버튼 클릭
   → 브라우저 콘솔 + DB 확인
   ```

2. **실제 페이지에서 디버깅**
   ```
   https://policy.wizice.com:8443/
   → F12 (개발자도구) 열기
   → 콘솔 탭에서 에러 확인
   → 네트워크 탭에서 요청 확인
   → 아무 내규나 클릭
   → 로그 메시지 확인
   ```

3. **에러 메시지 공유**
   - 브라우저 콘솔의 빨간 에러
   - 네트워크 탭의 실패한 요청
   - 예상과 다른 동작

---

**작성일**: 2025-01-14
**현재 상태**: 구현 완료, 실제 작동 확인 필요
**작성자**: Claude AI Assistant
