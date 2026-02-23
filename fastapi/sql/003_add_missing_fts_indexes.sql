-- ============================================================
-- title_text, appendix_text에 FTS 인덱스 추가
-- (content_text는 이미 idx_wz_rule_content_gin 존재)
-- ============================================================

-- 1. title_text FTS 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_wz_rule_title_fts
ON wz_rule
USING gin(to_tsvector('simple', COALESCE(title_text, '')));

-- 2. appendix_text FTS 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_wz_rule_appendix_fts
ON wz_rule
USING gin(to_tsvector('simple', COALESCE(appendix_text, '')));

-- 3. 인덱스 생성 확인
SELECT
    indexrelname as index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE relname = 'wz_rule'
  AND indexrelname LIKE '%_fts'
ORDER BY indexrelname;
