-- ============================================================================
-- 색인 관리 시스템 테이블 생성 스크립트
-- ============================================================================

-- 1. wz_rule 테이블에 색인 관련 컬럼 추가
-- (기존 테이블이 있다면 ALTER로 추가, 없으면 새로 생성)

-- 기존 테이블에 컬럼 추가 (이미 있으면 무시)
ALTER TABLE wz_rule
ADD COLUMN IF NOT EXISTS title_text TEXT,
ADD COLUMN IF NOT EXISTS content_text TEXT,
ADD COLUMN IF NOT EXISTS appendix_text TEXT,
ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS index_status VARCHAR(20) DEFAULT 'pending';

-- 제목 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_wz_rule_title_search
ON wz_rule USING GIN(to_tsvector('korean', title_text));

-- 본문 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_wz_rule_content_search
ON wz_rule USING GIN(to_tsvector('korean', content_text));

-- 부록 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_wz_rule_appendix_search
ON wz_rule USING GIN(to_tsvector('korean', appendix_text));

-- 색인 상태 인덱스
CREATE INDEX IF NOT EXISTS idx_wz_rule_index_status
ON wz_rule(index_status);

-- 색인 시간 인덱스
CREATE INDEX IF NOT EXISTS idx_wz_rule_indexed_at
ON wz_rule(indexed_at DESC);


-- 2. 색인 로그 테이블
CREATE TABLE IF NOT EXISTS wz_indexing_log (
    log_id SERIAL PRIMARY KEY,
    wzruleseq INT,
    wzname VARCHAR(500),
    index_status VARCHAR(20) NOT NULL,
    error_message TEXT,
    indexed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (wzruleseq) REFERENCES wz_rule(wzruleseq) ON DELETE SET NULL
);

-- 색인 로그 인덱스
CREATE INDEX IF NOT EXISTS idx_indexing_log_status
ON wz_indexing_log(index_status);

CREATE INDEX IF NOT EXISTS idx_indexing_log_rule_id
ON wz_indexing_log(wzruleseq);

CREATE INDEX IF NOT EXISTS idx_indexing_log_created_at
ON wz_indexing_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_indexing_log_rule_name
ON wz_indexing_log USING GIN(to_tsvector('korean', wzname));


-- 3. 검색 인덱스 테이블
CREATE TABLE IF NOT EXISTS wz_search_index (
    index_id SERIAL PRIMARY KEY,
    wzruleseq INT,
    search_type VARCHAR(20),  -- 'title', 'content', 'appendix'
    indexed_text TEXT,
    indexed_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (wzruleseq) REFERENCES wz_rule(wzruleseq) ON DELETE CASCADE
);

-- 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_search_text
ON wz_search_index USING GIN(to_tsvector('korean', indexed_text));

CREATE INDEX IF NOT EXISTS idx_search_type
ON wz_search_index(search_type);

CREATE INDEX IF NOT EXISTS idx_search_rule_id
ON wz_search_index(wzruleseq);


-- 4. 부록 인덱스 테이블
CREATE TABLE IF NOT EXISTS wz_appendix_index (
    appendix_index_id SERIAL PRIMARY KEY,
    wzruleseq INT,
    appendix_no VARCHAR(50),
    appendix_title VARCHAR(255),
    appendix_content TEXT,
    file_path VARCHAR(255),
    file_type VARCHAR(20),
    indexed_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (wzruleseq) REFERENCES wz_rule(wzruleseq) ON DELETE CASCADE
);

-- 부록 인덱스
CREATE INDEX IF NOT EXISTS idx_appendix_search
ON wz_appendix_index USING GIN(to_tsvector('korean', appendix_content));

CREATE INDEX IF NOT EXISTS idx_appendix_title_search
ON wz_appendix_index USING GIN(to_tsvector('korean', appendix_title));

CREATE INDEX IF NOT EXISTS idx_appendix_rule_id
ON wz_appendix_index(wzruleseq);


-- 5. 사용자 검색 기록 테이블
CREATE TABLE IF NOT EXISTS user_search_history (
    history_id SERIAL PRIMARY KEY,
    user_id INT,
    query_text VARCHAR(255),
    search_type VARCHAR(20),  -- 'title', 'content', 'appendix', 'combined'
    result_count INT,
    searched_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 사용자 검색 기록 인덱스
CREATE INDEX IF NOT EXISTS idx_user_search_history_user
ON user_search_history(user_id, searched_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_search_history_query
ON user_search_history USING GIN(to_tsvector('korean', query_text));


-- 6. 데이터 초기화
-- 기존 규정에 대해 'pending' 상태로 설정
UPDATE wz_rule
SET index_status = 'pending'
WHERE index_status IS NULL AND wznewflag = '현행';

-- ============================================================================
-- 확인 쿼리
-- ============================================================================
-- 아래 쿼리들을 실행해서 테이블 생성 확인

-- wz_rule 테이블 컬럼 확인
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'wz_rule' AND column_name IN ('title_text', 'content_text', 'appendix_text', 'indexed_at', 'index_status')
-- ORDER BY ordinal_position;

-- 로그 테이블 확인
-- SELECT COUNT(*) as log_count FROM wz_indexing_log;

-- 색인 상태 확인
-- SELECT index_status, COUNT(*) as count
-- FROM wz_rule
-- GROUP BY index_status
-- ORDER BY index_status;
