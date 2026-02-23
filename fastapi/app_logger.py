# logger.py
import logging
import sys
from pathlib import Path
from settings import settings

def setup_logging(file_name):
    """로깅 설정"""
    
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 루트 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    # 일반 텍스트 포맷터 설정
    console_formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (로그 로테이션 적용)
    from logging.handlers import RotatingFileHandler
    print(f"log_file={log_dir}/{file_name}")
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=5,  # 최대 5개 백업 파일 유지
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s %(filename)s L%(lineno)d %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    # 특정 로거(httpcore)의 로그 레벨을 WARNING 이상으로 설정
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    # pdfminer 로그 레벨 조정 (DEBUG 로그 과다 출력 방지)
    for pdfminer_logger in ["pdfminer", "pdfminer.psparser", "pdfminer.pdfinterp",
                            "pdfminer.pdfdocument", "pdfminer.pdfpage", "pdfminer.converter"]:
        logging.getLogger(pdfminer_logger).setLevel(logging.WARNING)
    #if sys.stdout.isatty():  # 터미널에서 실행 중일 때만
    #    logging.getLogger("httpx").setLevel(logging.DEBUG)
    #    logging.getLogger("anthropic").setLevel(logging.DEBUG)
    #    logging.getLogger("redis").setLevel(logging.DEBUG)

def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 생성"""
    return logging.getLogger(name)


