"""
그룹웨어 API 클라이언트 (Flask 동기 버전)

연세의료원 그룹웨어 모바일 SLO API와 통신
"""

import requests
from typing import Dict, Any
from utils.network_utils import NetworkUtils


class GroupwareClient:
    """그룹웨어 모바일 SLO API 클라이언트 (동기 버전)"""

    def __init__(self, api_url, crypto, log=None):
        """
        Args:
            api_url: 그룹웨어 API URL
            crypto: AES256 암호화 유틸리티 (SLOCrypto 인스턴스)
            log: 로거 객체 (선택)
        """
        self.api_url = api_url
        self.crypto = crypto
        self.log = log

    def validate_k_value(self, k_value):
        """
        K값으로 그룹웨어에 사용자 인증 요청 (동기 버전)

        서버 IP가 10.10.10.12가 아닌 경우 자동으로 server_name 파라미터 추가

        Args:
            k_value: 모바일에서 전달받은 K값

        Returns:
            그룹웨어 API 응답
            {
                "result": "success" | "error" | "not found" | ...,
                "emp_code": "암호화된_직번",
                "ad_id": "암호화된_AD계정",
                "msg": "메시지"
            }
        """

        # 기본 파라미터
        payload = {"K": k_value}

        # 서버 IP 확인하여 조건부로 server_name 추가
        should_send = NetworkUtils.should_send_server_name()

        if should_send:
            # 개발/테스트 서버: server_name 필요
            external_ip = NetworkUtils.get_external_ip()

            if external_ip:
                encrypted_ip = self.crypto.encrypt(external_ip)
                payload["server_name"] = encrypted_ip
                if self.log:
                    self.log.info(f"[GW API] server_name 추가 (개발/테스트) - IP: {external_ip}")
            else:
                if self.log:
                    self.log.warning("[GW API] 외부 IP 확인 실패 - server_name 생략")
        else:
            # 운영 서버 (10.10.10.12): server_name 불필요
            if self.log:
                self.log.info(f"[GW API] server_name 생략 (운영 서버: {NetworkUtils.PRODUCTION_IP})")

        # API 호출
        try:
            if self.log:
                self.log.info(f"[GW API] 요청 URL: {self.api_url}")
                self.log.debug(f"[GW API] 파라미터 키: {list(payload.keys())}")

            response = requests.post(
                self.api_url,
                data=payload,
                verify=False,  # SSL 검증 비활성화 (필요 시)
                timeout=30.0
            )

            if self.log:
                self.log.info(f"[GW API] 응답 상태: {response.status_code}")

            if response.status_code != 200:
                error_msg = f"API 호출 실패: HTTP {response.status_code}"
                if self.log:
                    self.log.error(f"[GW API] {error_msg}")
                return {
                    "result": "error",
                    "msg": error_msg
                }

            result = response.json()
            if self.log:
                self.log.info(f"[GW API] 응답 결과: {result.get('result')}")

            # 응답 상세 로깅 (성공/실패 구분)
            if result.get("result") == "success":
                if self.log:
                    self.log.info("[GW API] ✅ 인증 성공")
            else:
                if self.log:
                    self.log.warning(f"[GW API] ❌ 인증 실패 - {result.get('msg', 'Unknown')}")

            return result

        except requests.exceptions.Timeout:
            error_msg = "그룹웨어 API 타임아웃 (30초)"
            if self.log:
                self.log.error(f"[GW API] {error_msg}")
            return {
                "result": "error",
                "msg": error_msg
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"API 요청 오류: {str(e)}"
            if self.log:
                self.log.error(f"[GW API] {error_msg}")
            return {
                "result": "error",
                "msg": error_msg
            }
        except Exception as e:
            error_msg = f"API 호출 중 예외 발생: {str(e)}"
            if self.log:
                self.log.error(f"[GW API] {error_msg}")
            return {
                "result": "error",
                "msg": error_msg
            }
