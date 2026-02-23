# PostgreSQL FTS 적용 가이드

## 📋 적용 순서

### **개발 환경 적용**

#### 1️⃣ 'korean' 설정 확인
```bash
psql -U severance -d severance -h 127.0.0.1 -p 35432 -f sql/000_check_korean_support.sql
```

**결과 확인:**
- `korean`이 있으면 → `001_add_fts_index_safe.sql`에서 'simple'을 'korean'으로 변경
- `korean`이 없으면 → 그대로 'simple' 사용

#### 2️⃣ FTS 인덱스 생성 (피크타임 이후 실행)
```bash
psql -U severance -d severance -h 127.0.0.1 -p 35432 -f sql/001_add_fts_index_safe.sql
```

**예상 소요 시간:**
- 규정 100개: ~1초
- 규정 1,000개: ~5-10초
- 규정 10,000개: ~1-2분

#### 3️⃣ 인덱스 생성 확인
```sql
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE relname = 'wz_rule'
  AND indexrelname LIKE '%_fts'
ORDER BY indexrelname;
```

#### 4️⃣ 기존 파일 백업
```bash
cp fastapi/api/router_public_search.py fastapi/api/router_public_search.py.backup_$(date +%Y%m%d)
```

#### 5️⃣ FTS 코드 적용
```bash
cp fastapi/api/router_public_search.py.fts fastapi/api/router_public_search.py
```

#### 6️⃣ FastAPI 재시작
```bash
# 개발 환경
pkill -f "uvicorn app:app"
nohup uvicorn app:app --host 0.0.0.0 --port 8800 --reload > logs/uvicorn.log 2>&1 &
```

#### 7️⃣ 검색 테스트
```bash
# 브라우저에서 테스트
http://localhost:8800/api/search?q=환자&search_type=content&limit=10

# curl 테스트
curl "http://localhost:8800/api/search?q=환자&search_type=content&limit=10" | jq
```

---

### **운영 환경 적용**

#### 1️⃣ 파일 복사 (개발 → 운영)
```bash
# SSH 또는 FTP로 운영 서버에 복사
scp sql/000_check_korean_support.sql user@운영서버:/path/to/regulation/fastapi/sql/
scp sql/001_add_fts_index_safe.sql user@운영서버:/path/to/regulation/fastapi/sql/
scp fastapi/api/router_public_search.py.fts user@운영서버:/path/to/regulation/fastapi/api/
```

#### 2️⃣ 운영 DB에 인덱스 생성 (피크타임 이후!)
```bash
# 운영 서버에서 실행
psql -U [운영DB사용자] -d [운영DB명] -h [운영DB호스트] -p [운영DB포트] -f sql/001_add_fts_index_safe.sql
```

#### 3️⃣ 코드 적용
```bash
# 운영 서버에서 실행
cd /path/to/regulation/fastapi
cp api/router_public_search.py api/router_public_search.py.backup_$(date +%Y%m%d)
cp api/router_public_search.py.fts api/router_public_search.py
```

#### 4️⃣ FastAPI 재시작
```bash
# 운영 환경 (예시)
sudo systemctl restart fastapi
# 또는
supervisorctl restart fastapi
```

#### 5️⃣ 운영 검색 테스트
```bash
curl "https://운영도메인/api/search?q=환자&search_type=content&limit=10" | jq
```

---

## 🔍 테스트 쿼리

### 1. FTS 인덱스 사용 확인
```sql
EXPLAIN ANALYZE
SELECT
    wzruleseq,
    wzname
FROM wz_rule
WHERE wzNewFlag = '현행'
AND index_status = 'completed'
AND to_tsvector('simple', COALESCE(content_text, '')) @@ plainto_tsquery('simple', '환자');
```

**결과 확인:**
- `Bitmap Index Scan on idx_wz_rule_content_fts` 문구가 있으면 ✅ 인덱스 사용 중
- `Seq Scan` 문구가 있으면 ❌ Full Table Scan (인덱스 미사용)

### 2. 성능 비교 (ILIKE vs FTS)
```sql
-- ILIKE (기존 방식)
EXPLAIN ANALYZE
SELECT * FROM wz_rule
WHERE content_text ILIKE '%환자%';

-- FTS (새 방식)
EXPLAIN ANALYZE
SELECT * FROM wz_rule
WHERE to_tsvector('simple', content_text) @@ plainto_tsquery('simple', '환자');
```

---

## 📊 성능 비교 예상

| 데이터 규모 | ILIKE (기존) | FTS (개선) | 성능 향상 |
|------------|-------------|-----------|---------|
| 규정 100개 | ~500ms | ~50ms | 10배 ⚡ |
| 규정 1,000개 | ~5초 | ~100ms | 50배 ⚡⚡ |
| 규정 10,000개 | ~30초 | ~300ms | 100배 ⚡⚡⚡ |

---

## ⚠️ 주의사항

### 인덱스만 추가하고 코드 변경 안 하면?
- ✅ 기존 코드 정상 동작
- ❌ 성능 향상 전혀 없음
- 💾 불필요한 인덱스만 차지

### 롤백 방법
```bash
# 코드 롤백
cp api/router_public_search.py.backup_YYYYMMDD api/router_public_search.py

# 인덱스 삭제 (선택사항)
psql -U severance -d severance -c "DROP INDEX IF EXISTS idx_wz_rule_content_fts;"
psql -U severance -d severance -c "DROP INDEX IF EXISTS idx_wz_rule_title_fts;"
psql -U severance -d severance -c "DROP INDEX IF EXISTS idx_wz_rule_appendix_fts;"
```

---

## 📝 체크리스트

### 개발 환경
- [ ] 'korean' 설정 확인 완료
- [ ] FTS 인덱스 생성 완료
- [ ] 인덱스 크기 확인 완료
- [ ] 기존 파일 백업 완료
- [ ] FTS 코드 적용 완료
- [ ] FastAPI 재시작 완료
- [ ] 검색 테스트 성공
- [ ] 성능 개선 확인

### 운영 환경
- [ ] 피크타임 이후 작업 시간 확보
- [ ] 운영 서버에 파일 복사 완료
- [ ] 운영 DB 인덱스 생성 완료
- [ ] 운영 코드 백업 완료
- [ ] 운영 코드 적용 완료
- [ ] FastAPI 재시작 완료
- [ ] 운영 검색 테스트 성공
- [ ] 모니터링 확인 (에러 로그, 응답 시간)

---

**작성일:** 2025-11-09
**작성자:** Claude AI Assistant
