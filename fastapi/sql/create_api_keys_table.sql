-- API 키 테이블
-- 생성일: 2025-12-28
-- 용도: 외부 시스템 연동, 테스트 자동화, CI/CD 등

CREATE TABLE IF NOT EXISTS wz_api_keys (
    api_key_id SERIAL PRIMARY KEY,

    -- 사용자 정보
    users_id INTEGER NOT NULL,                    -- users 테이블 참조
    username VARCHAR(100) NOT NULL,               -- 사용자명 (편의용)

    -- API 키 정보
    key_name VARCHAR(100),                        -- 키 별명 (예: "테스트용", "CI/CD")
    key_prefix VARCHAR(20) NOT NULL,              -- 키 prefix (표시용, 예: kbr_live_abc1)
    key_hash VARCHAR(64) NOT NULL,                -- SHA-256 해시 (검증용)

    -- 상태 및 추적
    is_active BOOLEAN DEFAULT TRUE,               -- 활성화 여부
    last_used_at TIMESTAMP,                       -- 마지막 사용 시간
    use_count INTEGER DEFAULT 0,                  -- 사용 횟수

    -- 메타 정보
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,                         -- 만료일 (NULL = 무기한)

    -- 유니크 제약조건
    CONSTRAINT uk_api_key_hash UNIQUE (key_hash)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_apikey_users ON wz_api_keys(users_id);
CREATE INDEX IF NOT EXISTS idx_apikey_hash ON wz_api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_apikey_prefix ON wz_api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_apikey_active ON wz_api_keys(is_active) WHERE is_active = TRUE;

-- 코멘트
COMMENT ON TABLE wz_api_keys IS 'API 키 관리 테이블';
COMMENT ON COLUMN wz_api_keys.key_prefix IS '키 앞부분 (UI 표시용)';
COMMENT ON COLUMN wz_api_keys.key_hash IS 'SHA-256 해시 (검증용)';
