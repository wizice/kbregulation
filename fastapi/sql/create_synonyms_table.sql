-- ============================================================================
-- 유사어(Synonym) 관리 테이블
-- 검색 엔진에서 유사어 확장 검색을 위한 테이블
-- ============================================================================

-- 유사어 그룹 테이블 (메인)
CREATE TABLE IF NOT EXISTS search_synonyms (
    synonym_id SERIAL PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL,           -- 유사어 그룹명 (예: "환자", "의약품")
    synonyms TEXT[] NOT NULL,                   -- 유사어 배열 (예: {"환자", "피검자", "수진자"})
    description VARCHAR(500),                   -- 그룹 설명
    is_active BOOLEAN DEFAULT TRUE,             -- 활성화 여부
    priority INTEGER DEFAULT 0,                 -- 우선순위 (높을수록 먼저 적용)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),                    -- 생성자
    updated_by VARCHAR(100)                     -- 수정자
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_synonyms_group_name ON search_synonyms(group_name);
CREATE INDEX IF NOT EXISTS idx_synonyms_is_active ON search_synonyms(is_active);
CREATE INDEX IF NOT EXISTS idx_synonyms_priority ON search_synonyms(priority DESC);

-- GIN 인덱스 (배열 검색용)
CREATE INDEX IF NOT EXISTS idx_synonyms_synonyms_gin ON search_synonyms USING GIN(synonyms);

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_synonyms_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_synonyms_updated_at ON search_synonyms;
CREATE TRIGGER trigger_synonyms_updated_at
    BEFORE UPDATE ON search_synonyms
    FOR EACH ROW
    EXECUTE FUNCTION update_synonyms_updated_at();

-- 코멘트 추가
COMMENT ON TABLE search_synonyms IS '검색 엔진 유사어 관리 테이블';
COMMENT ON COLUMN search_synonyms.synonym_id IS '유사어 그룹 고유 ID';
COMMENT ON COLUMN search_synonyms.group_name IS '유사어 그룹명 (대표 단어)';
COMMENT ON COLUMN search_synonyms.synonyms IS '유사어 목록 (PostgreSQL 배열)';
COMMENT ON COLUMN search_synonyms.description IS '그룹 설명';
COMMENT ON COLUMN search_synonyms.is_active IS '활성화 여부';
COMMENT ON COLUMN search_synonyms.priority IS '우선순위 (높을수록 먼저 적용)';

-- 샘플 데이터 (의료 용어 기준)
INSERT INTO search_synonyms (group_name, synonyms, description, priority, created_by) VALUES
('환자', ARRAY['환자', '피검자', '수진자', '진료대상자', '입원환자', '외래환자'], '환자 관련 유사어', 100, 'system'),
('의약품', ARRAY['의약품', '약품', '약물', '의료품', '약제', '처방약'], '의약품 관련 유사어', 95, 'system'),
('입원', ARRAY['입원', '재원', '내원', '방문', '입실'], '입원 관련 유사어', 90, 'system'),
('처방', ARRAY['처방', '처방전', '오더', '지시', '투약지시'], '처방 관련 유사어', 85, 'system'),
('진료', ARRAY['진료', '치료', '시술', '의료행위', '진찰'], '진료 관련 유사어', 80, 'system'),
('병동', ARRAY['병동', '병실', '입원실', '간호단위', '병상'], '병동 관련 유사어', 75, 'system'),
('의사', ARRAY['의사', '전문의', '주치의', '담당의', '진료의'], '의사 관련 유사어', 70, 'system'),
('간호사', ARRAY['간호사', '간호인력', '간호직', '담당간호사'], '간호사 관련 유사어', 65, 'system'),
('감염', ARRAY['감염', '전염', '원내감염', '병원감염', '감염병'], '감염 관련 유사어', 60, 'system'),
('낙상', ARRAY['낙상', '추락', '넘어짐', '미끄러짐'], '낙상 관련 유사어', 55, 'system'),
('수술', ARRAY['수술', '오퍼레이션', 'OP', '시술', '수술실'], '수술 관련 유사어', 50, 'system'),
('응급', ARRAY['응급', '긴급', '응급실', 'ER', '응급환자'], '응급 관련 유사어', 45, 'system')
ON CONFLICT DO NOTHING;

-- 확인 쿼리
SELECT synonym_id, group_name, synonyms, is_active, priority
FROM search_synonyms
ORDER BY priority DESC;
