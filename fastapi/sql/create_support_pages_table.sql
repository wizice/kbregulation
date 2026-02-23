-- 지원 페이지 관리 테이블 생성
CREATE TABLE IF NOT EXISTS wz_support_pages (
    page_id SERIAL PRIMARY KEY,
    page_type VARCHAR(20) NOT NULL CHECK (page_type IN ('procedure', 'usage', 'faq')),  -- 제개정절차, 사용방법, FAQ
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    order_no INTEGER DEFAULT 0,  -- 정렬 순서
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),  -- 수정자
    is_active BOOLEAN DEFAULT TRUE,
    attachment_path VARCHAR(500),  -- 첨부파일 경로
    attachment_name VARCHAR(255),  -- 원본 파일명
    attachment_size BIGINT         -- 파일 크기 (bytes)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_support_pages_type ON wz_support_pages(page_type);
CREATE INDEX IF NOT EXISTS idx_support_pages_active ON wz_support_pages(is_active);
CREATE INDEX IF NOT EXISTS idx_support_pages_created ON wz_support_pages(created_at DESC);

-- 코멘트 추가
COMMENT ON TABLE wz_support_pages IS '지원 페이지 관리 (제개정절차, 사용방법, FAQ)';
COMMENT ON COLUMN wz_support_pages.page_type IS '페이지 유형: procedure(제개정절차), usage(사용방법), faq(FAQ)';
COMMENT ON COLUMN wz_support_pages.order_no IS '정렬 순서 (작은 번호가 먼저)';
