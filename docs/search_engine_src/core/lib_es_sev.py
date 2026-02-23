# -*- coding: utf-8 -*-
"""
    lib_es_sev
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    세브란스 elasticsearch 활용 모듈
    (연세대 lib_es.py v1.1 기반)

    version : 1.1

    :copyright: (c) 2016 by wizice.
    :license: MIT LICENSE 2.0, see license for more details.
"""

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, MultiSearch
from hanparse import HanParse

# 설정 파일에서 기본값 가져오기
try:
    from settings import settings
    DEFAULT_ES_HOST = settings.ES_HOST
    DEFAULT_ES_PORT = settings.ES_PORT
    DEFAULT_INDEX_RULE = settings.ES_INDEX_RULE
except ImportError:
    # settings 없을 경우 기본값
    DEFAULT_ES_HOST = "localhost"
    DEFAULT_ES_PORT = 9200
    DEFAULT_INDEX_RULE = "severance_policy_rule"


dao_es = None
dao_esSearch = None

class LibEs:
    __session = None
    __sessionSearch = None

    @staticmethod
    def init(index=None, doc_type="list", es_ip=None, es_port=None):
        # 기본값 설정
        if index is None:
            index = DEFAULT_INDEX_RULE
        if es_ip is None:
            es_ip = DEFAULT_ES_HOST
        if es_port is None:
            es_port = DEFAULT_ES_PORT
        """Elasticsearch 세션 초기화

        Args:
            index: 인덱스 이름 (기본값: policy_rule)
            doc_type: 문서 타입 (기본값: list)
            es_ip: Elasticsearch 서버 IP (기본값: 127.0.0.1)
            es_port: Elasticsearch 포트 (기본값: 9201)
        """
        LibEs.__session = Elasticsearch([{'host': es_ip, 'port': int(es_port), 'use_ssl': False}])
        LibEs.__sessionSearch = Search(index=index, doc_type=doc_type, using=LibEs.__session)

        global dao_es
        dao_es = LibEs.__session
        global dao_esSearch
        dao_esSearch = LibEs.__sessionSearch


    def __init__(self, index=None, doc_type="list", es_ip=None, es_port=None):
        # 기본값 설정
        if index is None:
            index = DEFAULT_INDEX_RULE
        if es_ip is None:
            es_ip = DEFAULT_ES_HOST
        if es_port is None:
            es_port = DEFAULT_ES_PORT
        """LibEs 인스턴스 초기화

        Args:
            index: 인덱스 이름 (기본값: policy_rule)
            doc_type: 문서 타입 (기본값: list)
            es_ip: Elasticsearch 서버 IP (기본값: 127.0.0.1)
            es_port: Elasticsearch 포트 (기본값: 9201)
        """
        self.es = Elasticsearch([{'host': es_ip, 'port': int(es_port), 'use_ssl': False}])
        self.esSearch = Search(index=index, doc_type=doc_type, using=self.es)
        self.parser = HanParse()
        self.Log = None


    def index_rulelist(self, rule_list, index="policy_rule", doc_type="list"):
        """규정 리스트 색인

        Args:
            rule_list: 규정 데이터 딕셔너리
            index: 인덱스 이름
            doc_type: 문서 타입

        Returns:
            색인 결과 리스트
        """
        data_list = rule_list
        for data_id, data in data_list.items():
            data["name"] = self.parser.utf8(data["name"])
            if self.Log:
                self.Log.debug("name=%s" % (data["name"]))
            data["tags"] = self.parser.parse_join(data["name"], " ")
            if self.Log:
                self.Log.debug("tag=%s" % (data["tags"]))

        return self.index(data_list, index=index, doc_type=doc_type)

    def index_delete(self, index="policy_rule"):
        """인덱스 삭제

        Args:
            index: 삭제할 인덱스 이름

        Returns:
            삭제 결과
        """
        result = self.es.indices.delete(index=index, ignore=[400, 404])
        return result


    def index(self, data_list, index="policy_rule", doc_type="list"):
        """데이터 색인 생성

        Args:
            data_list: 색인할 데이터 딕셔너리
            index: 인덱스 이름
            doc_type: 문서 타입

        Returns:
            색인 결과 리스트
        """
        results = []
        row = 0
        for data_id, data in data_list.items():
            res = self.es.index(index=index, doc_type=doc_type, id=data_id, body=data)
            results.append(res)
            if self.Log:
                self.Log.debug("res={0} Created={1}".format(str(res), str(res.get('created', False))))
        return results

    def search_bytags(self, keywd, index="policy_rule", doc_type="list", debug=False):
        """tags 필드로 검색

        Args:
            keywd: 검색 키워드
            index: 검색할 인덱스
            doc_type: 문서 타입
            debug: 디버그 모드

        Returns:
            검색 결과
        """
        results = self.es.search(
            index=index,
            body={
                "from": 0,
                "size": 9000,
                "query": {
                    "term": {
                        "tags": self.parser.utf8(keywd)
                    }
                }
            }
        )
        if debug:
            self.show_results(results)
        return results

    def search_q(self, q_string, index="policy_rule", doc_type="list", from_=0, size=10000, sort="wzrulename:asc", debug=False):
        """query DSL을 사용하여 검색

        Elasticsearch Query String 문법 사용:
        - "+환자 +안전 +관리" => 모두 포함
        - "-레이저 +안전 +관리" => 레이저 제외
        - "tags:(-레이저 +안전 +관리)"
        - "wzrulename:( +*규정* +*관리*)"
        - "+wzrulename:( +*규정* -*폐지*) +wzdeptname:의료질향상팀"
        - "wzrulename:/.*환자.*안전/"
        - "+wzrulename:/환자.*(안전|관리)/ +wzrulename:/.*(규정|지침).*/"

        Args:
            q_string: Query String 쿼리
            index: 검색할 인덱스
            doc_type: 문서 타입 (ES 7.x+ deprecated, 호환성 유지용)
            from_: 시작 위치
            size: 결과 개수
            sort: 정렬 기준 (예: "규정명.keyword:asc")
            debug: 디버그 모드

        Returns:
            검색 결과
        """
        # sort 문자열을 body 형식으로 변환 (한글 필드명 인코딩 문제 해결)
        # "규정명.keyword:asc" -> [{"규정명.keyword": {"order": "asc"}}]
        sort_body = []
        if sort:
            parts = sort.split(':')
            if len(parts) == 2:
                field, order = parts
                sort_body.append({field: {"order": order}})
            else:
                # 기본값: 점수 내림차순
                sort_body.append({"_score": {"order": "desc"}})

        # body에 query와 sort 포함
        body = {
            "query": {
                "query_string": {
                    "query": q_string
                }
            },
            "sort": sort_body
        }

        results = self.es.search(
            index=index,
            from_=from_,
            size=size,
            body=body
        )
        if debug:
            self.show_results(results, index=index)
        return results

    def search_dsl(self, q_string, from_=0, size=1000, debug=False):
        """DSL의 search 기능 사용

        Args:
            q_string: 검색 쿼리 문자열
            from_: 시작 위치
            size: 결과 개수
            debug: 디버그 모드

        Returns:
            검색 결과
        """
        myesSearch = self.esSearch[from_:size]
        myesSearch = myesSearch.query("multi_match", query=q_string, fields=["tags"]).sort("wzrulename")
        print("count=%s" % (myesSearch.count()))
        response = myesSearch.execute()
        if debug:
            self.show_results(response.to_dict(), debug=debug)
            print("======")
        return response


    def show_results(self, results, index="policy_rule", debug=False):
        """검색 결과 표시

        Args:
            results: 검색 결과
            index: 인덱스 이름
            debug: 디버그 모드
        """
        iTotal = len(results["hits"]["hits"])
        maxScore = results["hits"]["max_score"]
        iTook = results["took"]

        for row in results["hits"]["hits"]:
            if index == "policy_rule":
                if debug:
                    print("%s/%s/%s score:%s name:%s dept:%s" % (
                        row["_index"],
                        row["_type"],
                        row["_id"],
                        row["_score"],
                        self.parser.utf8(row['_source'].get("wzrulename", "")),
                        row['_source'].get("wzdeptname", "")
                    ))
                if self.Log:
                    self.Log.debug("%s/%s/%s score:%s name:%s dept:%s" % (
                        row["_index"],
                        row["_type"],
                        row["_id"],
                        row["_score"],
                        self.parser.utf8(row['_source'].get("wzrulename", "")),
                        row['_source'].get("wzdeptname", "")
                    ))

            elif index == "policy_article":
                if self.Log:
                    self.Log.debug("%s/%s/%s score:%s text:%s\n%s" % (
                        row["_index"],
                        row["_type"],
                        row["_id"],
                        row["_score"],
                        self.parser.utf8(row['_source'].get("wzcont", "")),
                        self.parser.utf8(row['_source'].get("wzrulename", ""))
                    ))
            print(" ")

        if self.Log:
            self.Log.info("total=%s maxScore=%s took=%s" % (iTotal, maxScore, iTook))

    def test_index_rulelist(self):
        """테스트용 규정 색인 생성"""
        rule_list = {
            "101": {
                "wzrulename": "레이저 및 기타 광학 방사선 기기 안전 관리 프로그램",
                "wzseq": 1.0,
                "wzdeptname": "의료질향상팀"
            },
            "102": {
                "wzrulename": "환자안전 관리 규정",
                "wzseq": 2.0,
                "wzdeptname": "의료질향상팀"
            },
            "103": {
                "wzrulename": "의료기기 안전 관리 지침",
                "wzseq": 3.0,
                "wzdeptname": "시설관리팀"
            }
        }
        return self.index_rulelist(rule_list)

    def test_search_dsl(self, q="안전"):
        """테스트용 DSL 검색"""
        return self.search_dsl(q, debug=True)


# 전역 인스턴스 생성
myEs = LibEs()

if __name__ == '__main__':
    from app_logger import get_logger

    # 로깅 초기화
    logger = get_logger(__name__)
    myEs.Log = logger

    # Elasticsearch 연결 테스트
    try:
        myEs.es = Elasticsearch([{'host': '127.0.0.1', 'port': 9201, 'use_ssl': False}])
        info = myEs.es.info()
        print("Elasticsearch 연결 성공:")
        print(f"  버전: {info['version']['number']}")
        print(f"  클러스터: {info['cluster_name']}")
    except Exception as e:
        print(f"Elasticsearch 연결 실패: {e}")
        print("9201 포트에 Elasticsearch가 실행 중인지 확인하세요.")
