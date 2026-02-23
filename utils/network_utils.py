"""
네트워크 유틸리티 모듈 (Flask 동기 버전)

서버 IP 감지 및 환경 판단 기능 제공
"""

import socket
import requests
from typing import Optional


class NetworkUtils:
    """네트워크 관련 유틸리티 (동기 버전)"""

    # 운영 환경 고정 IP (server_name 불필요)
    PRODUCTION_IP = "10.10.10.12"

    # 캐시된 외부 IP (재계산 방지)
    _cached_external_ip = None

    # 로거
    _log = None

    @classmethod
    def set_logger(cls, log):
        """로거 설정"""
        cls._log = log

    @classmethod
    def get_external_ip(cls):
        """
        서버의 외부 IP 주소 확인 (동기 버전)

        여러 방법을 시도:
        1. api.ipify.org 호출
        2. ifconfig.me 호출
        3. icanhazip.com 호출

        Returns:
            외부 IP 주소 또는 None
        """

        # 캐시된 값이 있으면 반환
        if cls._cached_external_ip:
            if cls._log:
                cls._log.debug(f"[Network] 캐시된 외부 IP 사용: {cls._cached_external_ip}")
            return cls._cached_external_ip

        # 여러 서비스 시도
        services = [
            "https://api.ipify.org?format=text",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
        ]

        for url in services:
            try:
                response = requests.get(url, timeout=5.0)
                if response.status_code == 200:
                    external_ip = response.text.strip()
                    cls._cached_external_ip = external_ip
                    if cls._log:
                        cls._log.info(f"[Network] 외부 IP 확인 성공: {external_ip} (from {url})")
                    return external_ip
            except Exception as e:
                if cls._log:
                    cls._log.debug(f"[Network] {url} 실패: {e}")
                continue

        if cls._log:
            cls._log.warning("[Network] 외부 IP 확인 실패 - 모든 서비스 응답 없음")
        return None

    @classmethod
    def is_production_server(cls):
        """
        현재 서버가 운영 서버(10.10.10.12)인지 확인 (동기 버전)

        Returns:
            True: 운영 서버 (10.10.10.12)
            False: 개발/테스트 서버 (기타 IP)
        """
        external_ip = cls.get_external_ip()

        if external_ip is None:
            # IP 확인 실패 시 안전하게 운영 서버로 간주 (server_name 전송 안함)
            if cls._log:
                cls._log.warning("[Network] IP 확인 실패 - 운영 서버로 간주")
            return True

        is_prod = (external_ip == cls.PRODUCTION_IP)
        if cls._log:
            cls._log.info(f"[Network] 서버 타입: {'운영' if is_prod else '개발/테스트'} ({external_ip})")

        return is_prod

    @classmethod
    def should_send_server_name(cls):
        """
        server_name 파라미터를 전송해야 하는지 확인 (동기 버전)

        Returns:
            True: server_name 전송 필요 (개발/테스트 서버)
            False: server_name 불필요 (운영 서버)
        """
        is_prod = cls.is_production_server()
        should_send = not is_prod

        if cls._log:
            cls._log.info(f"[Network] server_name 전송 여부: {should_send}")
        return should_send

    @classmethod
    def get_local_ip(cls):
        """
        서버의 로컬 IP 주소 확인 (내부망)

        Returns:
            로컬 IP 주소 (예: 172.31.35.222)
        """
        try:
            # 외부 연결 시도하여 로컬 IP 확인 (실제 연결 안함)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            if cls._log:
                cls._log.debug(f"[Network] 로컬 IP: {local_ip}")
            return local_ip
        except Exception as e:
            if cls._log:
                cls._log.warning(f"[Network] 로컬 IP 확인 실패: {e}")
            return "127.0.0.1"

    @classmethod
    def reset_cache(cls):
        """캐시 초기화 (테스트용)"""
        cls._cached_external_ip = None
        if cls._log:
            cls._log.info("[Network] IP 캐시 초기화")
