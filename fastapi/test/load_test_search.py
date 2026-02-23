#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
검색 API 부하 테스트 스크립트
- 동시 10명 사용자 시뮬레이션
- ILIKE vs FTS 성능 비교
"""

import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 테스트 설정
BASE_URL = "http://localhost:8800"
CONCURRENT_USERS = 10
REQUESTS_PER_USER = 5
SEARCH_KEYWORDS = ["환자", "의료", "진료", "수술", "검사", "진단", "치료", "간호", "응급", "입원"]

# 결과 저장
results = {
    'ilike': [],
    'fts': []
}

def search_request(keyword, search_type="content", method="ilike"):
    """단일 검색 요청"""
    url = f"{BASE_URL}/api/search"
    params = {
        'q': keyword,
        'search_type': search_type,
        'limit': 20,
        'page': 1
    }

    start_time = time.time()
    try:
        response = requests.get(url, params=params, timeout=30)
        elapsed_time = (time.time() - start_time) * 1000  # ms로 변환

        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'elapsed_ms': elapsed_time,
                'total_results': data.get('total', 0),
                'returned_count': len(data.get('results', [])),
                'keyword': keyword,
                'method': method
            }
        else:
            return {
                'success': False,
                'elapsed_ms': elapsed_time,
                'error': f"HTTP {response.status_code}",
                'keyword': keyword,
                'method': method
            }
    except Exception as e:
        elapsed_time = (time.time() - start_time) * 1000
        return {
            'success': False,
            'elapsed_ms': elapsed_time,
            'error': str(e),
            'keyword': keyword,
            'method': method
        }

def run_concurrent_test(method="ilike", num_users=10, requests_per_user=5):
    """동시 사용자 테스트"""
    print(f"\n{'='*70}")
    print(f"[{method.upper()}] 동시 {num_users}명 사용자 테스트 시작")
    print(f"  - 사용자당 요청 수: {requests_per_user}")
    print(f"  - 총 요청 수: {num_users * requests_per_user}")
    print(f"{'='*70}\n")

    test_results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []

        # 동시 요청 생성
        for user_id in range(num_users):
            for req_id in range(requests_per_user):
                keyword = SEARCH_KEYWORDS[req_id % len(SEARCH_KEYWORDS)]
                future = executor.submit(search_request, keyword, "content", method)
                futures.append(future)

        # 결과 수집
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            test_results.append(result)
            completed += 1

            if completed % 10 == 0 or completed == len(futures):
                print(f"  진행: {completed}/{len(futures)} 완료 ({completed/len(futures)*100:.1f}%)")

    total_time = (time.time() - start_time) * 1000  # ms

    # 통계 계산
    success_results = [r for r in test_results if r['success']]
    failed_results = [r for r in test_results if not r['success']]

    if success_results:
        response_times = [r['elapsed_ms'] for r in success_results]

        stats = {
            'method': method,
            'total_requests': len(test_results),
            'successful_requests': len(success_results),
            'failed_requests': len(failed_results),
            'total_time_ms': total_time,
            'min_response_ms': min(response_times),
            'max_response_ms': max(response_times),
            'avg_response_ms': statistics.mean(response_times),
            'median_response_ms': statistics.median(response_times),
            'p95_response_ms': sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0],
            'p99_response_ms': sorted(response_times)[int(len(response_times) * 0.99)] if len(response_times) > 1 else response_times[0],
            'requests_per_second': len(success_results) / (total_time / 1000) if total_time > 0 else 0,
            'results': test_results
        }
    else:
        stats = {
            'method': method,
            'total_requests': len(test_results),
            'successful_requests': 0,
            'failed_requests': len(failed_results),
            'total_time_ms': total_time,
            'error': 'All requests failed',
            'results': test_results
        }

    return stats

def print_statistics(stats):
    """통계 출력"""
    print(f"\n{'='*70}")
    print(f"[{stats['method'].upper()}] 테스트 결과")
    print(f"{'='*70}")
    print(f"총 요청 수:        {stats['total_requests']}")
    print(f"성공 요청:         {stats['successful_requests']}")
    print(f"실패 요청:         {stats['failed_requests']}")
    print(f"총 소요 시간:      {stats['total_time_ms']:.2f} ms ({stats['total_time_ms']/1000:.2f}초)")

    if stats['successful_requests'] > 0:
        print(f"\n[응답 시간 통계]")
        print(f"최소:              {stats['min_response_ms']:.2f} ms")
        print(f"최대:              {stats['max_response_ms']:.2f} ms")
        print(f"평균:              {stats['avg_response_ms']:.2f} ms")
        print(f"중앙값:            {stats['median_response_ms']:.2f} ms")
        print(f"95 백분위수:       {stats['p95_response_ms']:.2f} ms")
        print(f"99 백분위수:       {stats['p99_response_ms']:.2f} ms")
        print(f"\n[처리량]")
        print(f"초당 요청 수:      {stats['requests_per_second']:.2f} req/s")

    if stats['failed_requests'] > 0:
        print(f"\n⚠️  {stats['failed_requests']}개 요청 실패")
        failed = [r for r in stats['results'] if not r['success']]
        for r in failed[:5]:  # 처음 5개만 표시
            print(f"  - {r['keyword']}: {r.get('error', 'Unknown error')}")

    print(f"{'='*70}\n")

def compare_results(ilike_stats, fts_stats):
    """두 방식 비교"""
    print(f"\n{'='*70}")
    print(f"📊 ILIKE vs FTS 성능 비교")
    print(f"{'='*70}\n")

    if ilike_stats['successful_requests'] > 0 and fts_stats['successful_requests'] > 0:
        comparison = {
            '구분': ['최소 응답시간', '평균 응답시간', '중앙값', '95 백분위', '최대 응답시간', '초당 처리량'],
            'ILIKE': [
                f"{ilike_stats['min_response_ms']:.2f} ms",
                f"{ilike_stats['avg_response_ms']:.2f} ms",
                f"{ilike_stats['median_response_ms']:.2f} ms",
                f"{ilike_stats['p95_response_ms']:.2f} ms",
                f"{ilike_stats['max_response_ms']:.2f} ms",
                f"{ilike_stats['requests_per_second']:.2f} req/s"
            ],
            'FTS': [
                f"{fts_stats['min_response_ms']:.2f} ms",
                f"{fts_stats['avg_response_ms']:.2f} ms",
                f"{fts_stats['median_response_ms']:.2f} ms",
                f"{fts_stats['p95_response_ms']:.2f} ms",
                f"{fts_stats['max_response_ms']:.2f} ms",
                f"{fts_stats['requests_per_second']:.2f} req/s"
            ],
            '차이': []
        }

        # 성능 차이 계산
        metrics = [
            ('min_response_ms', 'ms'),
            ('avg_response_ms', 'ms'),
            ('median_response_ms', 'ms'),
            ('p95_response_ms', 'ms'),
            ('max_response_ms', 'ms'),
            ('requests_per_second', 'req/s')
        ]

        for metric, unit in metrics:
            ilike_val = ilike_stats[metric]
            fts_val = fts_stats[metric]

            if metric == 'requests_per_second':
                # 처리량은 높을수록 좋음
                diff_pct = ((fts_val - ilike_val) / ilike_val * 100) if ilike_val > 0 else 0
                if diff_pct > 0:
                    comparison['차이'].append(f"FTS +{diff_pct:.1f}% 빠름 ⚡")
                else:
                    comparison['차이'].append(f"ILIKE +{abs(diff_pct):.1f}% 빠름 ⚡")
            else:
                # 응답시간은 낮을수록 좋음
                diff_pct = ((fts_val - ilike_val) / ilike_val * 100) if ilike_val > 0 else 0
                if diff_pct > 0:
                    comparison['차이'].append(f"ILIKE +{abs(diff_pct):.1f}% 빠름 ⚡")
                else:
                    comparison['차이'].append(f"FTS +{diff_pct:.1f}% 빠름 ⚡")

        # 테이블 출력
        print(f"{'구분':<15} {'ILIKE':<20} {'FTS':<20} {'성능 차이':<30}")
        print(f"{'-'*15} {'-'*20} {'-'*20} {'-'*30}")
        for i, metric in enumerate(comparison['구분']):
            print(f"{metric:<15} {comparison['ILIKE'][i]:<20} {comparison['FTS'][i]:<20} {comparison['차이'][i]:<30}")

        # 권장 사항
        print(f"\n{'='*70}")
        if ilike_stats['avg_response_ms'] < fts_stats['avg_response_ms']:
            faster = 'ILIKE'
            slower = 'FTS'
            diff = ((fts_stats['avg_response_ms'] - ilike_stats['avg_response_ms']) / ilike_stats['avg_response_ms'] * 100)
        else:
            faster = 'FTS'
            slower = 'ILIKE'
            diff = ((ilike_stats['avg_response_ms'] - fts_stats['avg_response_ms']) / fts_stats['avg_response_ms'] * 100)

        print(f"🎯 결론: {faster}가 평균 {diff:.1f}% 더 빠릅니다.")
        print(f"\n💡 권장 사항:")

        if faster == 'ILIKE':
            print(f"  ✅ 현재 데이터 규모(172개)에서는 ILIKE 방식 유지 권장")
            print(f"  ⚠️  규정이 1,000개 이상 증가하면 FTS 전환 검토")
        else:
            print(f"  ✅ FTS 방식 적용 권장")
            print(f"  ⚡ 데이터 증가 시 더 큰 성능 향상 예상")

    print(f"{'='*70}\n")

def main():
    """메인 함수"""
    print(f"\n{'#'*70}")
    print(f"# 검색 API 부하 테스트")
    print(f"# 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# 동시 사용자: {CONCURRENT_USERS}명")
    print(f"# 사용자당 요청: {REQUESTS_PER_USER}회")
    print(f"# 총 요청 수: {CONCURRENT_USERS * REQUESTS_PER_USER}회")
    print(f"{'#'*70}\n")

    # 1. 현재 ILIKE 방식 테스트
    print("\n[1/2] ILIKE 방식 테스트 중...")
    ilike_stats = run_concurrent_test("ilike", CONCURRENT_USERS, REQUESTS_PER_USER)
    print_statistics(ilike_stats)

    # 잠시 대기
    print("2초 대기 중...\n")
    time.sleep(2)

    # 2. FTS 방식 테스트 (코드 변경 필요 - 일단 시뮬레이션)
    print("\n[2/2] FTS 방식 성능 예측...")
    print("⚠️  주의: FTS 코드가 아직 적용되지 않았습니다.")
    print("   실제 FTS 성능 측정을 위해서는:")
    print("   1. router_public_search.py.fts → router_public_search.py 복사")
    print("   2. FastAPI 재시작")
    print("   3. 이 스크립트 재실행\n")

    # 비교 결과 출력
    print(f"\n{'='*70}")
    print(f"📊 테스트 요약")
    print(f"{'='*70}")
    print(f"ILIKE 방식:")
    print(f"  - 평균 응답시간: {ilike_stats['avg_response_ms']:.2f} ms")
    print(f"  - 동시 10명 처리: {ilike_stats['total_time_ms']:.2f} ms ({ilike_stats['total_time_ms']/1000:.2f}초)")
    print(f"  - 처리량: {ilike_stats['requests_per_second']:.2f} req/s")

    print(f"\n현재 코드 상태: ILIKE 방식 사용 중")
    print(f"동시 10명 사용 시 성능: {'✅ 양호' if ilike_stats['avg_response_ms'] < 100 else '⚠️ 개선 필요'}")
    print(f"{'='*70}\n")

    # CSV 결과 저장
    csv_file = f"/home/wizice/regulation/fastapi/test/load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("method,keyword,success,elapsed_ms,total_results,returned_count\n")
        for r in ilike_stats['results']:
            f.write(f"{r['method']},{r['keyword']},{r['success']},{r['elapsed_ms']},{r.get('total_results', 0)},{r.get('returned_count', 0)}\n")

    print(f"📁 상세 결과 저장: {csv_file}\n")

if __name__ == "__main__":
    main()
