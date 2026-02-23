from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import sys

class Settings(BaseSettings):
    SECRET_KEY: str  = "severance-secret-key-vXdsQ7EOxrBvoO0L5Ou6"
    # API Keys
    gpt_openai_key: str = "xxxx"
    anthropic_api_key: str = "xxx"
    ANTHROPIC_API_KEY: str = anthropic_api_key
    telegram_bot_token: Optional[str] = "xxx"

    # Redis 설정
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    REDIS_HOST: str = redis_host
    REDIS_PORT: int = redis_port
    REDIS_PASSWORD:Optional[str] =  redis_password
    REDIS_DB:int = redis_db

    redis_session_prefix: str = "session:"
    redis_refresh_prefix: str = "refresh:"
    redis_default_ttl: int = 86400  # 24시간
    redis_refresh_ttl: int = 604800  # 7일

    # 컨텍스트 관리
    context_expire_days: int = 3
    max_context_length: int = 20
    
    #  설정 
    app_title: str = "세브란스 연세 세칙편집기"
    app_version: str = "1.0.1"
    debug: bool = True
    jinja_cache : str = "/tmp/jinja_cache"
    auto_reload: bool = True
    
    # Claude 설정
    #claude_model: str = "claude-3-sonnet-20240229"
    #claude_model: str = "claude-sonnet-4-20250514"
    claude_model: str = "claude-opus-4-20250514"
    max_tokens: int = 4000
    
    # 로깅
    log_path: str = "/home/wizice/regulation/fastapi/logs"
    log_level: str = "INFO"  # DEBUG에서 INFO로 변경 (pdfminer 로그 과다 출력 방지)

    DB_HOST: str = "localhost"
    DB_PORT: int = 35432
    DB_NAME: str = "severance"
    DB_USER: str = "severance"
    DB_PASSWORD: str = "rkatkseverance!"

    # 파일 경로 설정
    BASE_DIR: str = "/home/wizice/regulation"
    APPLIB_RELATIVE_PATH: str = "fastapi/applib"
    JSON_SERVICE_RELATIVE_PATH: str = "www/static/file"
    FILE_BACKUP_FOLDER: str = "_old"
    JSON_BACKUP_FOLDER: str = "file_old"
    FILE_BACKUP_ENABLED: bool = True

    # Elasticsearch 설정
    ES_HOST: str = "167.71.217.249"  # 운영: localhost, 개발: 167.71.217.249
    ES_PORT: int = 9200
    ES_INDEX_RULE: str = "severance_policy_rule"
    ES_INDEX_ARTICLE: str = "severance_policy_article"
    ES_INDEX_APPENDIX: str = "severance_policy_appendix"
    ES_USE_SSL: bool = False
    ES_VERIFY_CERTS: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

