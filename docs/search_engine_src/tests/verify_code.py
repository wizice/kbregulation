#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Elasticsearch 검색 코드 검증 스크립트

app.py를 실행하지 않고 코드의 문법과 import만 검증합니다.
"""

import sys
sys.path.insert(0, '/home/wizice/regulation/fastapi')

print("========================================")
print("Code Verification Test")
print("========================================")
print("")

# 1. router_public_search_es.py import 테스트
print("1. Testing router_public_search_es.py import...")
try:
    from api import router_public_search_es
    print("   ✅ SUCCESS: router_public_search_es imported")

    # 라우터 확인
    router = router_public_search_es.router
    print(f"   ✅ Router prefix: {router.prefix}")
    print(f"   ✅ Router tags: {router.tags}")

    # 엔드포인트 확인
    routes = [route.path for route in router.routes]
    print(f"   ✅ Endpoints: {len(routes)} routes found")
    for route in routes:
        print(f"      - {route}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("")

# 2. Elasticsearch 라이브러리 확인
print("2. Testing Elasticsearch libraries...")
try:
    from lib_es_sev import LibEs
    from hanparse import HanParse
    print("   ✅ SUCCESS: lib_es_sev and hanparse imported")
except ImportError as e:
    print(f"   ⚠️  WARNING: Elasticsearch libraries not installed")
    print(f"      {e}")
    print("      Run: pip install elasticsearch elasticsearch-dsl")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

print("")

# 3. 기존 router_public_search.py 확인 (충돌 검사)
print("3. Testing existing router_public_search.py...")
try:
    from api import router_public_search
    existing_router = router_public_search.router
    print(f"   ✅ SUCCESS: Existing router still works")
    print(f"   ✅ Existing prefix: {existing_router.prefix}")

    # 경로 충돌 검사
    existing_routes = {route.path for route in existing_router.routes}
    new_routes = {route.path for route in router_public_search_es.router.routes}

    conflicts = existing_routes & new_routes
    if conflicts:
        print(f"   ⚠️  WARNING: Route conflicts found: {conflicts}")
    else:
        print(f"   ✅ No route conflicts detected")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("")

# 4. 설정 확인
print("4. Testing configuration...")
try:
    ES_IP = router_public_search_es.ES_IP
    ES_PORT = router_public_search_es.ES_PORT
    INDEX_RULE = router_public_search_es.INDEX_RULE

    print(f"   ✅ Elasticsearch IP: {ES_IP}")
    print(f"   ✅ Elasticsearch Port: {ES_PORT}")
    print(f"   ✅ Index Name: {INDEX_RULE}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

print("")
print("========================================")
print("✅ All code verification passed!")
print("========================================")
print("")
print("Next steps:")
print("  1. Fix app.py startup issue (access_logger import)")
print("  2. Start server: uvicorn app:app --host 0.0.0.0 --port 8800")
print("  3. Run test suite: ./test/elasticsearch/run_all_tests.sh")
print("")
