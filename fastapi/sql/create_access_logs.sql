-- 접속 로그 테이블 생성
-- 실행: psql -h localhost -p 35432 -U severance -d severance -f create_access_logs.sql

-- 기존 테이블이 있으면 삭제 (주의: 운영 환경에서는 주석 처리)
-- DROP TABLE IF EXISTS access_logs CASCADE;

CREATE TABLE IF NOT EXISTS access_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),

    -- 사용자 정보
    user_id VARCHAR(100),           -- 로그인 사용자 ID (세션에서 추출)
    user_name VARCHAR(200),          -- 사용자 이름

    -- 네트워크 정보
    ip_address VARCHAR(50),          -- IP 주소

    -- 요청 정보
    method VARCHAR(10),              -- HTTP 메서드 (GET, POST 등)
    path TEXT,                       -- 요청 경로 (예: /api/search)
    query_string TEXT,               -- 쿼리 파라미터
    referrer TEXT,                   -- 이전 페이지 (Referer)

    -- 클라이언트 정보
    user_agent TEXT,                 -- User-Agent 전체 문자열
    device_type VARCHAR(50),         -- PC/Mobile/Tablet
    browser VARCHAR(100),            -- 브라우저 종류
    os VARCHAR(100),                 -- 운영체제

    -- 응답 정보
    status_code INTEGER,             -- HTTP 상태 코드
    response_time_ms INTEGER,        -- 응답 시간 (밀리초)

    -- 세션 정보
    session_id VARCHAR(200)          -- 세션 ID
);

-- 인덱스 생성 (빠른 검색을 위해)
CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON access_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_access_logs_user_id ON access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_ip ON access_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_access_logs_path ON access_logs(path);
CREATE INDEX IF NOT EXISTS idx_access_logs_session ON access_logs(session_id);

-- 파티셔닝을 위한 설정 (선택사항, 대용량 데이터 시 사용)
-- TimescaleDB를 사용 중이라면 하이퍼테이블로 변환 가능
-- SELECT create_hypertable('access_logs', 'timestamp', if_not_exists => TRUE);

COMMENT ON TABLE access_logs IS '웹 접속 로그 테이블';
COMMENT ON COLUMN access_logs.timestamp IS '접속 시간';
COMMENT ON COLUMN access_logs.user_id IS '로그인 사용자 ID';
COMMENT ON COLUMN access_logs.ip_address IS 'IP 주소';
COMMENT ON COLUMN access_logs.path IS '요청 경로';
COMMENT ON COLUMN access_logs.response_time_ms IS '응답 시간 (ms)';
