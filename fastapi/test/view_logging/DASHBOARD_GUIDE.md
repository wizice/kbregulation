# 유입량 분석 대시보드 사용 가이드

## 📋 개요

관리자 전용 유입량 분석 대시보드로, 내규별 조회 통계를 시각화합니다.

---

## 🚀 접속 방법

### 1. 관리자 로그인

```
http://localhost:8800/login
```

**관리자 계정**:
- ID: `sevpolicy`
- PW: `sevpolicy123!@#`

### 2. 유입량 분석 대시보드 접속

**방법 1**: 편집기 상단 탭 메뉴 클릭
```
관리자 대시보드 → 유입량 분석 탭 클릭
```

**방법 2**: 직접 URL 접속
```
http://localhost:8800/admin/view-analytics
```

---

## 📊 대시보드 구성

### 1. 전체 통계 카드 (4개)

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  전체 조회수    │  조회된 내규 수  │  오늘 조회수    │  이번 주 조회수  │
│     435         │       3         │      120        │      350        │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

- **전체 조회수**: 누적 총 조회수
- **조회된 내규 수**: 1회 이상 조회된 내규 개수
- **오늘 조회수**: 금일 조회수
- **이번 주 조회수**: 이번 주 조회수

### 2. 일별 조회 추이 (라인 차트)

```
일별 조회수
 │
 │     ╱╲
 │    ╱  ╲     ╱╲
 │   ╱    ╲   ╱  ╲
 │  ╱      ╲ ╱    ╲
 └──────────────────────
   7일전         오늘
```

- **X축**: 날짜 (최근 7일/30일/90일/1년)
- **Y축**: 조회수
- **기능**: 호버 시 상세 수치 표시

### 3. 시간대별 조회 분포 (바 차트)

```
시간대별 조회수
 │
 │  █
 │  █     █
 │  █  █  █  █
 │  █  █  █  █     █
 └────────────────────────
   0  6  12 18 23시
```

- **X축**: 시간대 (0시~23시)
- **Y축**: 조회수
- **용도**: 피크 시간대 파악

### 4. TOP 10 조회수 (테이블)

```
순위 │ 공포번호 │ 내규 명칭              │ 조회수 │ 마지막 조회
─────┼─────────┼───────────────────────┼────────┼──────────────────
 1  │ 5.4.1.  │ 성인 진정관리          │  400   │ 2025-01-14 16:30
 2  │ 1.5.1.  │ 손위생                │   15   │ 2025-01-14 15:20
 3  │ 11.5.3. │ 인체삽입 의료기기      │   10   │ 2025-01-14 14:10
```

- **순위**: 금/은/동 메달 아이콘 (1/2/3위)
- **정렬**: 조회수 내림차순
- **최대**: TOP 10까지만 표시

---

## 🔧 필터 기능

### 기간 선택

```
기간 선택: [최근 30일 ▼]  [새로고침]
```

**옵션**:
- 최근 7일
- 최근 30일 (기본값)
- 최근 90일
- 최근 1년

**동작**:
1. 기간 선택
2. 자동으로 일별 차트 갱신
3. 새로고침 버튼으로 수동 갱신

---

## 🧪 테스트 시나리오

### 시나리오 1: 기본 조회

```bash
# 1. 관리자 로그인
브라우저에서 http://localhost:8800/login 접속

# 2. 유입량 분석 탭 클릭
편집기 상단 메뉴바 → "유입량 분석" 탭 클릭

# 3. 대시보드 로드 확인
✅ 전체 통계 카드 4개 표시
✅ 일별 차트 렌더링
✅ 시간대별 차트 렌더링
✅ TOP 10 테이블 표시
```

### 시나리오 2: 필터 변경

```bash
# 1. 기간 선택 변경
기간 선택 드롭다운 → "최근 7일" 선택

# 2. 차트 갱신 확인
✅ 일별 차트가 7일치 데이터로 변경
✅ 로딩 스피너 표시 후 데이터 로드
```

### 시나리오 3: 실시간 데이터 반영

```bash
# 1. 내규 조회 (브라우저 새 탭)
http://localhost:8800/api/v1/regulation/content/1

# 2. 대시보드 새로고침
유입량 분석 페이지 → "새로고침" 버튼 클릭

# 3. 데이터 증가 확인
✅ 전체 조회수 +1
✅ 오늘 조회수 +1
✅ 일별 차트 금일 데이터 증가
✅ TOP 10에서 해당 내규 조회수 증가
```

---

## 🐛 트러블슈팅

### 문제 1: 대시보드가 로드되지 않음

**증상**: 빈 화면 또는 로딩 무한

**원인**:
- API 엔드포인트 오류
- 관리자 권한 없음

**해결**:
```bash
# 1. 콘솔 확인 (F12 → Console)
# 401 Unauthorized → 관리자 권한 없음
# 500 Internal Error → 서버 오류

# 2. 관리자 권한 확인
SELECT role FROM users WHERE username = 'sevpolicy';
# → 'admin' 이어야 함

# 3. API 직접 테스트
curl -X GET "http://localhost:8800/api/v1/admin/view-stats/summary" \
  -H "Cookie: session_token=YOUR_TOKEN"
```

---

### 문제 2: 차트가 표시되지 않음

**증상**: 카드는 보이지만 차트가 안 보임

**원인**:
- Chart.js 로드 실패
- 데이터 형식 오류

**해결**:
```bash
# 1. 브라우저 콘솔 확인
Chart is not defined
# → Chart.js CDN 로드 실패

# 2. 네트워크 탭 확인
Failed to load resource: chart.umd.min.js
# → CDN 차단 또는 네트워크 문제

# 3. 데이터 확인
console.log(data);
# → API 응답이 비어있는지 확인
```

---

### 문제 3: TOP 10이 비어있음

**증상**: "조회 데이터가 없습니다" 메시지

**원인**:
- 실제로 조회 데이터가 없음

**해결**:
```bash
# 1. DB 직접 확인
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance \
  -c "SELECT COUNT(*) FROM regulation_view_logs;"

# 2. 테스트 데이터 생성
python3 test_view_logger.py

# 3. 대시보드 새로고침
```

---

## 📊 성능 최적화

### 데이터베이스 인덱스 확인

```sql
-- 인덱스 존재 확인
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'regulation_view_logs';

-- 예상 결과:
-- idx_regulation_view_logs_rule_viewed
-- idx_regulation_view_logs_viewed
-- idx_regulation_view_logs_pubno
```

### 쿼리 성능 분석

```sql
-- TOP 10 쿼리 실행 계획
EXPLAIN ANALYZE
SELECT
    rule_id,
    rule_name,
    rule_pubno,
    COUNT(*) as view_count
FROM regulation_view_logs
GROUP BY rule_id, rule_name, rule_pubno
ORDER BY view_count DESC
LIMIT 10;

-- 예상: Index Scan 사용 (Full Table Scan 아님)
```

---

## 🔐 보안

### 접근 제어

- ✅ 관리자 권한 필수 (`@require_role("admin")`)
- ✅ 세션 기반 인증
- ✅ 개인정보 미수집 (IP, User-Agent 저장 안함)

### API 권한

```python
# app.py
@app.get("/admin/view-analytics")
@login_required(redirect_to="/login")
async def view_analytics_dashboard(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    # 관리자만 접근 가능
```

---

## 📈 향후 개선 사항

- [ ] Excel 다운로드 기능
- [ ] 특정 기간 커스텀 선택
- [ ] 부서별 조회 통계
- [ ] 실시간 갱신 (WebSocket)
- [ ] 비교 기간 설정 (전주 대비 등)
- [ ] 알림 설정 (특정 조회수 도달 시)

---

**작성일**: 2025-01-14
**버전**: 1.0.0
**작성자**: Claude AI Assistant
