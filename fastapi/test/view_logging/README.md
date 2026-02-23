# 내규 조회 통계 로깅 시스템 테스트 가이드

## 📋 개요

내규 조회 통계 로깅 시스템의 테스트 가이드입니다.

- **목적**: 내규별 조회 횟수 추적 (순수 유입량 측정)
- **개인정보**: 저장 안함 (IP, User-Agent, 사용자 정보 제외)
- **무영향 원칙**: 로그 실패해도 내규 조회는 정상 작동

---

## 🗂 파일 구조

```
test/view_logging/
├── README.md                           # 이 파일
├── APPENDIX_SYSTEM_ANALYSIS.md         # 부록 시스템 분석 문서
├── PDF_LOGGING_TEST.md                 # PDF 로깅 테스트 가이드
├── test_pdf_logging.sh                 # 부록 PDF 로깅 자동 테스트
├── test_01_logger_module.sh            # 로거 모듈 단독 테스트
├── test_02_integration.sh              # 통합 테스트
├── test_03_stats_api.sh                # 통계 API 테스트
└── test_04_failure_scenarios.sh        # 장애 시나리오 테스트
```

---

## ✅ 테스트 체크리스트

### 1단계: 로거 모듈 단독 테스트

```bash
cd /home/wizice/regulation/fastapi
python3 test_view_logger.py
```

**검증 항목**:
- [ ] 로그 기록 정상 작동
- [ ] 조회수 조회 정상 작동
- [ ] 전체 통계 조회 정상 작동
- [ ] 외래키 제약 정상 동작

**예상 결과**:
```
✅ 로그 기록 완료
✅ rule_id=1 조회수: N회
✅ 전체 조회수: M회
```

---

### 2단계: 통합 테스트 (API 동작 시뮬레이션)

```bash
python3 test_view_logging_integration.py
```

**검증 항목**:
- [ ] 내규 조회 시 로그 자동 기록
- [ ] TOP 순위 정상 집계
- [ ] 증가량 정상 계산

**예상 결과**:
```
📊 로그 기록 후 통계:
   전체 조회수: 7
   증가량: +3

🏆 조회수 TOP 3:
   1. 성인 진정관리 (5.4.1.) - 3회
```

---

### 3단계: 통계 API 테스트

```bash
python3 test_view_stats_api.py
```

**검증 항목**:
- [ ] TOP 10 쿼리 정상 작동
- [ ] 전체 통계 정상 조회
- [ ] 시간대별 분포 정상 조회

**예상 결과**:
```
🏆 조회수 TOP 10:
   1. [1] 성인 진정관리 (5.4.1.) - 3회

⏰ 시간대별 조회 분포:
   16시: ███████ (7)
```

---

### 4단계: 실제 API 엔드포인트 테스트

**사전 준비**: 관리자 로그인 후 세션 토큰 획득

```bash
# 1. 로그인하여 세션 토큰 획득 (브라우저 개발자도구)
SESSION_TOKEN="your_session_token_here"

# 2. TOP 10 조회
curl -X GET "http://localhost:8800/api/v1/admin/view-stats/top?limit=10" \
  -H "Cookie: session_token=$SESSION_TOKEN" \
  | jq

# 3. 일별 통계 (최근 30일)
curl -X GET "http://localhost:8800/api/v1/admin/view-stats/daily?days=30" \
  -H "Cookie: session_token=$SESSION_TOKEN" \
  | jq

# 4. 시간대별 분포
curl -X GET "http://localhost:8800/api/v1/admin/view-stats/hourly" \
  -H "Cookie: session_token=$SESSION_TOKEN" \
  | jq

# 5. 전체 통계 요약
curl -X GET "http://localhost:8800/api/v1/admin/view-stats/summary" \
  -H "Cookie: session_token=$SESSION_TOKEN" \
  | jq

# 6. 특정 내규 상세 통계
curl -X GET "http://localhost:8800/api/v1/admin/view-stats/detail/1?days=30" \
  -H "Cookie: session_token=$SESSION_TOKEN" \
  | jq
```

---

## 🔥 장애 시나리오 테스트

### 시나리오 1: DB 연결 실패 시

```bash
# PostgreSQL 중단
sudo systemctl stop postgresql

# 내규 조회 API 호출 (브라우저에서)
# → 내규 조회는 정상 작동해야 함 (로그만 실패)

# PostgreSQL 재시작
sudo systemctl start postgresql
```

**예상 결과**:
- ✅ 내규 내용 정상 반환
- ⚠️ 로그 실패 경고 (logs/app.log)
- ✅ 사용자 체감 지연 없음

---

### 시나리오 2: 테이블 없음

```bash
# 테이블 임시 삭제
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance \
  -c "DROP TABLE regulation_view_logs CASCADE;"

# 내규 조회 시도
# → 정상 작동해야 함

# 테이블 복구
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance \
  -f sql/create_regulation_view_logs.sql
```

---

## 📊 데이터 확인 쿼리

### 최근 로그 10건

```sql
SELECT
    log_id,
    rule_id,
    rule_name,
    rule_pubno,
    TO_CHAR(viewed_at, 'YYYY-MM-DD HH24:MI:SS') as viewed_at
FROM regulation_view_logs
ORDER BY viewed_at DESC
LIMIT 10;
```

### 조회수 TOP 10

```sql
SELECT
    rule_id,
    rule_name,
    rule_pubno,
    COUNT(*) as view_count
FROM regulation_view_logs
GROUP BY rule_id, rule_name, rule_pubno
ORDER BY view_count DESC
LIMIT 10;
```

### 오늘 조회 통계

```sql
SELECT
    rule_id,
    rule_name,
    COUNT(*) as today_views
FROM regulation_view_logs
WHERE DATE(viewed_at) = CURRENT_DATE
GROUP BY rule_id, rule_name
ORDER BY today_views DESC;
```

### 시간대별 분포

```sql
SELECT
    EXTRACT(HOUR FROM viewed_at) as hour,
    COUNT(*) as views
FROM regulation_view_logs
GROUP BY EXTRACT(HOUR FROM viewed_at)
ORDER BY hour;
```

---

## 🧹 데이터 정리

### 테스트 데이터 삭제

```sql
-- ⚠️ 주의: 모든 로그가 삭제됩니다!
DELETE FROM regulation_view_logs;
```

### 특정 내규 로그만 삭제

```sql
DELETE FROM regulation_view_logs
WHERE rule_id = 1;
```

### 오래된 로그 삭제 (90일 이상)

```sql
DELETE FROM regulation_view_logs
WHERE viewed_at < NOW() - INTERVAL '90 days';
```

---

## 📈 성능 테스트

### 로그 기록 성능

```bash
# 100회 조회 시뮬레이션
for i in {1..100}; do
    python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from api.regulation_view_logger import log_regulation_view

async def test():
    await log_regulation_view(1, '성인 진정관리', '5.4.1.')

asyncio.run(test())
"
done

# 통계 확인
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance \
  -c "SELECT rule_id, COUNT(*) FROM regulation_view_logs GROUP BY rule_id;"
```

---

## 🐛 트러블슈팅

### 문제: 로그가 기록되지 않음

**원인 1**: 외래키 제약 위반
```bash
# wz_rule 테이블에 해당 rule_id가 존재하는지 확인
SELECT wzruleseq FROM wz_rule WHERE wzruleseq = 1;
```

**원인 2**: DB 연결 실패
```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql
```

**원인 3**: 권한 문제
```bash
# 테이블 권한 확인
\dp regulation_view_logs
```

---

### 문제: 통계 API가 401 Unauthorized

**원인**: 관리자 권한 필요

**해결**:
1. 관리자 계정으로 로그인
2. 세션 토큰 획득 (브라우저 쿠키)
3. API 요청 시 쿠키 포함

---

## 📚 관련 파일

- **로거 모듈**: `api/regulation_view_logger.py`
- **통계 API**: `api/service_regulation_view_stats.py`
- **로깅 통합**: `api/service_regulation_content.py` (108-117번 줄)
- **SQL 스키마**: `sql/create_regulation_view_logs.sql`

---

## 🎯 다음 단계

- [x] JSON 파일 로깅 시스템 구현 완료
- [x] 부록 PDF 로깅 시스템 구현 완료
- [x] 관리자 대시보드 UI 추가 완료
- [ ] 일일 통계 리포트 자동 생성 (선택)
- [ ] 90일 이상 로그 자동 삭제 스케줄러 (선택)

---

## 📄 부록 PDF 로깅 시스템 테스트

### 자동 테스트 스크립트

```bash
cd /home/wizice/regulation/fastapi/test/view_logging
./test_pdf_logging.sh
```

### 검증 항목
- [x] PDF API 엔드포인트 정상 작동
- [x] 로그 기록 정상 작동
- [x] 파일명 파싱 정확도 (규정코드, 부록번호, 부록명)
- [x] rule_pubno 형식 정확 (예: "1.2.1.")

### 예상 결과
```
✅ PASS: PDF 파일 정상 반환
✅ PASS: 로그 기록됨 (최근 1분 내 1건)
✅ PASS: 파일명 파싱 정확 (결과: 부록1. 구두처방 의약품 목록)
✅ PASS: rule_pubno 형식 정확 (결과: 1.2.1.)
```

### 상세 가이드
- 📖 [PDF_LOGGING_TEST.md](./PDF_LOGGING_TEST.md) - 부록 PDF 로깅 테스트 상세 가이드
- 📊 [APPENDIX_SYSTEM_ANALYSIS.md](./APPENDIX_SYSTEM_ANALYSIS.md) - 부록 시스템 분석 문서

---

**작성일**: 2025-01-14
**최종 업데이트**: 2025-11-17 (부록 PDF 로깅 추가)
**작성자**: Claude AI Assistant
**버전**: 2.0.0
