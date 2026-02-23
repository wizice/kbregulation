# MariaDB Mock 클래스
# 실제 DB 연결 없이 테스트용으로 사용

class MariaDB:
    """MariaDB Mock 클래스"""

    def __init__(self, app=None, g=None, database=None, user=None, password=None, host=None):
        self.app = app
        self.g = g
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        print(f"MariaDB Mock initialized - Database: {database}")

    def connect(self):
        """Mock 연결"""
        return True

    def disconnect(self):
        """Mock 연결 해제"""
        return True

    def execute(self, query):
        """Mock 쿼리 실행"""
        return []

    def fetchall(self):
        """Mock 결과 조회"""
        return []