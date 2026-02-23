-- ============================================================
-- PostgreSQL Full Text Search (FTS) 인덱스 추가 (안전 버전)
-- 작성일: 2025-11-09
-- 목적: wz_rule 테이블 본문 검색 성능 개선
-- ============================================================

-- 주의: 'korean' 설정이 없으면 아래 스크립트 실행 전에
-- 'korean'을 'simple'로 변경하세요!

-- 1. 기존 인덱스 확인
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'wz_rule'
  AND indexname LIKE '%fts%';

-- 2. content_text 컬럼에 GIN 인덱스 생성
-- (korean 설정이 없으면 'simple'로 변경)
CREATE INDEX IF NOT EXISTS idx_wz_rule_content_fts
ON wz_rule
USING gin(to_tsvector('simple', COALESCE(content_text, '')));

-- 3. title_text 컬럼에도 FTS 인덱스 추가 (선택사항)
CREATE INDEX IF NOT EXISTS idx_wz_rule_title_fts
ON wz_rule
USING gin(to_tsvector('simple', COALESCE(title_text, '')));

-- 4. appendix_text 컬럼에도 FTS 인덱스 추가 (선택사항)
CREATE INDEX IF NOT EXISTS idx_wz_rule_appendix_fts
ON wz_rule
USING gin(to_tsvector('simple', COALESCE(appendix_text, '')));

-- 5. 인덱스 생성 완료 확인
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND relname = 'wz_rule'
  AND indexrelname LIKE '%_fts'
ORDER BY indexrelname;

-- ============================================================
-- 예상 소요 시간:
-- - 규정 100개: ~1초
-- - 규정 1,000개: ~5-10초
-- - 규정 10,000개: ~1-2분
-- ============================================================
