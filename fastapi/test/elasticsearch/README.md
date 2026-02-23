# Elasticsearch 검색 테스트 가이드

## 📁 테스트 파일 구조

```
test/elasticsearch/
├── README.md                 # 이 파일
├── test_es_health.sh        # ES 헬스체크 테스트
├── test_es_search.sh        # ES 검색 기능 테스트
├── test_compare.sh          # PostgreSQL vs ES 비교 테스트
└── run_all_tests.sh         # 모든 테스트 일괄 실행
```

## 🎯 테스트 목적

Elasticsearch 검색 엔진을 **기존 서비스에 영향 없이** 안전하게 도입하기 위한 테스트 스위트입니다.

## 🚀 사용 방법

### 1. Elasticsearch 헬스체크

```bash
./test_es_health.sh
```

**확인 사항**:
- ES 서버가 정상적으로 실행 중인지
- 인덱스가 생성되어 있는지
- 문서가 색인되어 있는지

**예상 출력**:
```
✅ SUCCESS: Elasticsearch is healthy!

📊 Index Statistics:
  - Rules Index: 1234 documents
  - Articles Index: 5678 documents
```

---

### 2. Elasticsearch 검색 테스트

```bash
./test_es_search.sh
```

**테스트 항목**:
- Title 검색 (`/api/search/es?search_type=title`)
- Content 검색 (`/api/search/es?search_type=content`)
- All 검색 (`/api/search/es?search_type=all`)

**예상 출력**:
```
✅ SUCCESS
📊 Results: 15 total documents, took 45.23ms
```

---

### 3. PostgreSQL vs Elasticsearch 비교

```bash
./test_compare.sh
```

**비교 항목**:
- 검색 속도 (응답 시간)
- 검색 결과 수
- 정확도 차이

**예상 출력**:
```
🔍 Query: '환자'
📊 PostgreSQL:
   - Time: 1200ms
   - Results: 15 documents

📊 Elasticsearch:
   - Time: 45ms
   - Results: 18 documents
   - Speed: 26.7x faster

🚀 Overall speed improvement: 25.3x faster
```

---

### 4. 모든 테스트 일괄 실행

```bash
./run_all_tests.sh
```

전체 테스트를 순차적으로 실행하고 최종 요약 리포트를 제공합니다.

---

## 📊 테스트 결과 해석

### ✅ 성공 케이스

- **HTTP 200**: 모든 테스트 통과
- **ES 속도 > PostgreSQL**: 성능 개선 확인
- **문서 수 유사**: 검색 정확도 유지

### ⚠️ 주의 케이스

- **ES 결과 수 < PostgreSQL**: 인덱스 재색인 필요
- **ES 속도 < PostgreSQL**: ES 설정 튜닝 필요
- **에러 발생**: ES 서버 상태 확인

### ❌ 실패 케이스

- **HTTP 503**: ES 서버 다운 → `docker restart elasticsearch` 또는 ES 서버 재시작
- **HTTP 500**: 코드 오류 → 로그 확인 (`logs/app.log`)
- **Import Error**: 패키지 미설치 → `pip install elasticsearch elasticsearch-dsl`

---

## 🔧 트러블슈팅

### 1. Elasticsearch 서버가 응답하지 않는 경우

```bash
# ES 서버 상태 확인
curl http://127.0.0.1:9201/_cluster/health

# ES 서버 재시작 (Docker 사용 시)
docker restart elasticsearch
```

### 2. "elasticsearch module not found" 에러

```bash
# 패키지 설치
pip install elasticsearch==7.17.9 elasticsearch-dsl==7.4.1
```

### 3. 검색 결과가 0건인 경우

```bash
# 인덱스 확인
curl http://127.0.0.1:9201/policy_rule/_count

# 인덱스 재색인 (관리자 페이지에서 수행)
# 또는 API 호출
curl -X POST http://localhost:8800/api/v1/search/reindex-all \
  -H "Cookie: session_token=YOUR_SESSION_TOKEN"
```

---

## 📝 테스트 결과 기록

테스트 실행 후 결과를 기록하세요:

| 날짜 | 테스트 | 결과 | 비고 |
|------|--------|------|------|
| 2025-01-XX | Health Check | ✅ | 1234 documents indexed |
| 2025-01-XX | Search Test | ✅ | Average 50ms |
| 2025-01-XX | Comparison | ✅ | 25x faster |

---

## 🔄 다음 단계

### Phase 1: 내부 테스트 (현재)
- ✅ ES 헬스체크
- ✅ 검색 기능 테스트
- ✅ 성능 비교

### Phase 2: 베타 테스트
- [ ] 개발팀 사용자에게 `/api/search/es` 공유
- [ ] 피드백 수집
- [ ] 버그 수정

### Phase 3: 점진적 전환
- [ ] Feature Flag 구현
- [ ] 트래픽 5% → ES
- [ ] 모니터링 및 성능 측정

### Phase 4: 완전 전환
- [ ] `/api/search` → Elasticsearch로 교체
- [ ] PostgreSQL 검색 비활성화 (백업 보관)
- [ ] 운영 모니터링

---

## 📚 참고 자료

- **Elasticsearch 문서**: https://www.elastic.co/guide/en/elasticsearch/reference/7.x/index.html
- **Query String 문법**: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html
- **한글 형태소 분석**: HanParse 라이브러리 사용

---

**작성일**: 2025-01-XX
**작성자**: Claude AI Assistant
**버전**: 1.0
