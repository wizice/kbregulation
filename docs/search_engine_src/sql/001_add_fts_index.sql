-- ============================================================
-- PostgreSQL Full Text Search (FTS) 인덱스 추가
-- 작성일: 2025-11-09
-- 목적: wz_rule 테이블 본문 검색 성능 개선
-- ============================================================

-- 1. 한글 FTS 지원을 위한 텍스트 검색 설정 확인
-- (기본 제공되는 'simple' 또는 'english' 사용 - 한글은 별도 설정 필요 시 추가)

-- 2. content_text 컬럼에 GIN 인덱스 생성
-- GIN (Generalized Inverted Index)은 Full Text Search에 최적화된 인덱스
CREATE INDEX IF NOT EXISTS idx_wz_rule_content_fts
ON wz_rule
USING gin(to_tsvector('simple', COALESCE(content_text, '')));

-- 3. title_text 컬럼에도 FTS 인덱스 추가 (제목 검색 성능 향상)
CREATE INDEX IF NOT EXISTS idx_wz_rule_title_fts
ON wz_rule
USING gin(to_tsvector('simple', COALESCE(title_text, '')));

-- 4. appendix_text 컬럼에도 FTS 인덱스 추가 (부록 검색 성능 향상)
CREATE INDEX IF NOT EXISTS idx_wz_rule_appendix_fts
ON wz_rule
USING gin(to_tsvector('simple', COALESCE(appendix_text, '')));

-- 5. 복합 검색을 위한 통합 FTS 인덱스 (선택사항)
-- title, content, appendix를 모두 검색할 때 사용
CREATE INDEX IF NOT EXISTS idx_wz_rule_all_text_fts
ON wz_rule
USING gin(
    to_tsvector('simple',
        COALESCE(title_text, '') || ' ' ||
        COALESCE(content_text, '') || ' ' ||
        COALESCE(appendix_text, '')
    )
);

-- 6. 인덱스 생성 완료 확인
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'wz_rule'
  AND indexname LIKE '%_fts'
ORDER BY indexname;

-- 7. 인덱스 크기 확인
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND relname = 'wz_rule'
  AND indexrelname LIKE '%_fts'
ORDER BY indexrelname;

-- ============================================================
-- 주의사항:
-- 1. 인덱스 생성 시간은 데이터 양에 따라 달라짐 (수천 개 = 수초~수분)
-- 2. 'simple'은 한글 형태소 분석 없이 공백 기준 분리 (빠름)
-- 3. 한글 형태소 분석이 필요하면 pg_korean 확장 설치 필요
-- 4. 운영 DB에 적용 시 피크타임 이후 실행 권장
-- ============================================================
