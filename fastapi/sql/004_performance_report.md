# PostgreSQL FTS 성능 분석 보고서

**분석 일시:** 2025-11-09
**데이터베이스:** severance (127.0.0.1:35432)

---

## 📊 현재 상태

### 데이터 규모
- **총 규정 수:** 172개
- **인덱싱 완료:** 149개 (86.6%)
- **평균 텍스트 길이:** 2,606자

### 기존 인덱스
| 인덱스명 | 크기 | 사용 횟수 | 상태 |
|---------|------|----------|------|
| idx_wz_rule_content_gin | 4880 kB | **0회** | ❌ 미사용 |
| idx_wz_rule_index_status | 16 kB | 37회 | ✅ 활용 중 |
| wz_rule_pkey | 16 kB | 12,483회 | ✅ 활용 중 |

**문제점:**
- FTS 인덱스가 이미 있지만 **한 번도 사용되지 않음**
- 현재 코드가 ILIKE 사용 → 인덱스 활용 불가

---

## ⚡ 성능 측정 결과

### 테스트 쿼리
```sql
SELECT wzruleseq, wzname, wzpubno
FROM wz_rule
WHERE wznewflag = '현행'
AND index_status = 'completed'
AND [검색 조건]
LIMIT 10;
```

### 실행 시간 비교

| 검색 방식 | Planning Time | Execution Time | Total | 인덱스 |
|---------|--------------|----------------|-------|--------|
| **ILIKE (기존)** | 2.2ms | 1.4ms | **3.6ms** | Seq Scan |
| **FTS (새 방식)** | 12.0ms | 18.0ms | **30.0ms** | Index Scan |

**결과:** ILIKE가 **8.3배 더 빠름** ⚡

---

## 🤔 왜 FTS가 더 느린가?

### 이유 1: 데이터 규모가 작음
- 172개의 규정은 모두 **PostgreSQL 메모리**에 로드됨
- Sequential Scan으로 전체를 읽어도 1.4ms (매우 빠름)
- 인덱스를 거치는 것이 오히려 오버헤드

### 이유 2: 인덱스 선택 문제
```sql
-- FTS 쿼리가 idx_wz_rule_content_gin을 사용해야 하지만
-- PostgreSQL 옵티마이저가 idx_wz_rule_index_status를 선택
-> Index Scan using idx_wz_rule_index_status
   Filter: to_tsvector(...) @@ plainto_tsquery(...)  -- 다시 계산!
```

### 이유 3: Planning Time 증가
- ILIKE: 2.2ms
- FTS: 12.0ms (5.4배 증가)

---

## 📈 데이터 규모별 예상 성능

| 규정 수 | ILIKE 예상 | FTS 예상 | 권장 방식 |
|--------|-----------|---------|----------|
| **100개** | ~3ms | ~30ms | ✅ ILIKE |
| **1,000개** | ~30ms | ~50ms | ⚖️ 비슷 |
| **10,000개** | ~3초 | ~100ms | ✅ FTS |
| **100,000개** | ~30초 | ~300ms | ✅ FTS |

**전환점:** 약 **1,000개** 이상부터 FTS가 유리

---

## 🎯 권장 사항

### 현재 상황 (172개)

#### ✅ 권장: ILIKE 유지
```python
# 현재 코드 그대로 사용
WHERE content_text ILIKE %s
```
**이유:**
- 성능: 3.6ms (충분히 빠름)
- 간단하고 안정적
- 인덱스 없이도 빠름

#### ⚠️ 선택: FTS 적용 (미래 대비)
```python
# FTS 쿼리로 변경
WHERE to_tsvector('simple', content_text) @@ plainto_tsquery('simple', %s)
```
**이유:**
- 현재는 느리지만 (30ms)
- 규정이 1,000개 이상 증가하면 **자동으로 빠른 성능** 확보
- 일관성 있는 검색 품질

---

## 📋 작업 체크리스트

### 옵션 A: 현상 유지 (권장)
- [ ] 아무 작업도 필요 없음
- [ ] 기존 ILIKE 계속 사용
- [ ] 규정 수가 1,000개 넘으면 재검토

### 옵션 B: FTS 적용 (미래 대비)
- [ ] `003_add_missing_fts_indexes.sql` 실행 (title_text, appendix_text 인덱스 추가)
- [ ] `router_public_search.py.fts` → `router_public_search.py` 복사
- [ ] FastAPI 재시작
- [ ] 성능 테스트 (30ms 정도 예상)
- [ ] 사용자 반응 확인

---

## 💡 결론

**현재 데이터 규모(172개)에서는 ILIKE가 더 빠릅니다.**

- 동시 10명 사용 시: ILIKE (36ms) vs FTS (300ms)
- 성능 문제 없음

**하지만, 규정이 1,000개 이상 증가할 계획이라면:**
- 지금 FTS로 전환하는 것도 나쁘지 않음
- 약간 느려도 (30ms) 사용자 경험에 영향 없음
- 데이터 증가 시 자동으로 빠른 성능 확보

**최종 권장:**
- **현재:** ILIKE 유지 ⭐
- **규정 500개 이상 시:** FTS 전환 검토
- **규정 1,000개 이상 시:** FTS 전환 필수

---

**작성자:** Claude AI Assistant
**분석 일시:** 2025-11-09
