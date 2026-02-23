# API 키 사용 가이드

## 개요

API 키를 사용하면 Google/Kakao 로그인 없이도 wzprint API에 접근할 수 있습니다. 테스트 자동화, CI/CD 파이프라인, 외부 시스템 연동 등에 활용할 수 있습니다.

## 특징

- ✅ **사용자별 격리**: 각 사용자가 자신만의 API 키 생성/관리
- ✅ **키 회전 지원**: 언제든지 키 삭제 후 재생성 가능
- ✅ **사용 추적**: 마지막 사용 시간 자동 기록
- ✅ **안전한 저장**: SHA-256 해시로 암호화 저장
- ✅ **운영 환경에서도 사용 가능**: 서비스 런칭 후에도 계속 사용 가능

## API 키 생성

### 1. 웹 UI에서 생성

1. https://sheetprint.wizice.com 접속
2. Google 또는 Kakao로 로그인
3. 좌측 메뉴에서 "API 키" 클릭
4. "새 API 키 생성" 버튼 클릭
5. 키 이름 입력 (선택사항, 예: "테스트용", "CI/CD")
6. "생성" 버튼 클릭
7. **⚠️ 생성된 키를 안전한 곳에 복사** (다시 표시되지 않음!)

### 2. 생성된 API 키 형식

```
wzp_live_abc123def456ghi789jkl012mno345pq
│   │    └────────────────────────────────── 32자 랜덤 문자열
│   └─────────────────────────────────────── 환경 (live = 운영)
└─────────────────────────────────────────── 프로젝트 prefix
```

## API 키 사용 방법

### 기본 사용

API 호출 시 `Authorization` 헤더에 `Bearer <API_KEY>` 형식으로 전달:

```bash
curl -H "Authorization: Bearer wzp_live_abc123..." \
  https://wzprint-api.wizice100.workers.dev/api/orders
```

### 예제 1: 주문 목록 조회

```bash
curl -X GET \
  https://wzprint-api.wizice100.workers.dev/api/orders \
  -H "Authorization: Bearer wzp_live_abc123def456..."
```

### 예제 2: 새 주문 생성

```bash
curl -X POST \
  https://wzprint-api.wizice100.workers.dev/api/orders \
  -H "Authorization: Bearer wzp_live_abc123def456..." \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "테스트 고객",
    "product_name": "테스트 상품",
    "quantity": 100,
    "barcode": "1234567890"
  }'
```

### 예제 3: Google Sheets 데이터 가져오기

```bash
curl -X POST \
  https://wzprint-api.wizice100.workers.dev/api/sheets/import \
  -H "Authorization: Bearer wzp_live_abc123def456..." \
  -H "Content-Type: application/json"
```

## 프로그래밍 언어별 예제

### Python

```python
import requests

API_URL = "https://wzprint-api.wizice100.workers.dev"
API_KEY = "wzp_live_abc123def456..."

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 주문 목록 조회
response = requests.get(f"{API_URL}/api/orders", headers=headers)
orders = response.json()
print(orders)

# 새 주문 생성
new_order = {
    "customer_name": "테스트 고객",
    "product_name": "테스트 상품",
    "quantity": 100,
    "barcode": "1234567890"
}
response = requests.post(f"{API_URL}/api/orders", json=new_order, headers=headers)
print(response.json())
```

### Node.js / TypeScript

```typescript
const API_URL = "https://wzprint-api.wizice100.workers.dev";
const API_KEY = "wzp_live_abc123def456...";

const headers = {
  "Authorization": `Bearer ${API_KEY}`,
  "Content-Type": "application/json"
};

// 주문 목록 조회
const response = await fetch(`${API_URL}/api/orders`, { headers });
const orders = await response.json();
console.log(orders);

// 새 주문 생성
const newOrder = {
  customer_name: "테스트 고객",
  product_name: "테스트 상품",
  quantity: 100,
  barcode: "1234567890"
};
const createResponse = await fetch(`${API_URL}/api/orders`, {
  method: "POST",
  headers,
  body: JSON.stringify(newOrder)
});
console.log(await createResponse.json());
```

### Rust

```rust
use reqwest;
use serde_json::json;

const API_URL: &str = "https://wzprint-api.wizice100.workers.dev";
const API_KEY: &str = "wzp_live_abc123def456...";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();

    // 주문 목록 조회
    let res = client
        .get(&format!("{}/api/orders", API_URL))
        .header("Authorization", format!("Bearer {}", API_KEY))
        .send()
        .await?;

    let orders = res.json::<serde_json::Value>().await?;
    println!("{:?}", orders);

    // 새 주문 생성
    let new_order = json!({
        "customer_name": "테스트 고객",
        "product_name": "테스트 상품",
        "quantity": 100,
        "barcode": "1234567890"
    });

    let res = client
        .post(&format!("{}/api/orders", API_URL))
        .header("Authorization", format!("Bearer {}", API_KEY))
        .header("Content-Type", "application/json")
        .json(&new_order)
        .send()
        .await?;

    println!("{:?}", res.json::<serde_json::Value>().await?);
    Ok(())
}
```

## CI/CD 통합

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: E2E Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run E2E Tests
        env:
          WZPRINT_API_KEY: ${{ secrets.WZPRINT_API_KEY }}
        run: |
          npm run test:e2e
```

**.env.test**:
```bash
WZPRINT_API_URL=https://wzprint-api.wizice100.workers.dev
WZPRINT_API_KEY=wzp_live_abc123...
```

## 보안 권장사항

### ✅ DO

- API 키를 환경변수에 저장
- `.env` 파일을 `.gitignore`에 추가
- CI/CD에서는 Secrets 관리 기능 사용
- 주기적으로 키 회전 (예: 3개월마다)
- 키별로 명확한 이름 지정 ("테스트용", "CI/CD", "외부 연동")

### ❌ DON'T

- 코드에 API 키 하드코딩
- Git 리포지토리에 커밋
- 공개 채널에 키 공유
- 하나의 키를 여러 용도로 사용

## API 키 관리

### 목록 조회

웹 UI에서:
1. https://sheetprint.wizice.com 접속
2. "API 키" 메뉴 클릭
3. 생성된 키 목록 확인 (prefix만 표시됨)
4. 마지막 사용 시간 확인

### 키 삭제

1. "API 키" 페이지에서 삭제할 키 찾기
2. "삭제" 버튼 클릭
3. 확인 후 즉시 비활성화

⚠️ 삭제된 키는 즉시 사용 불가능하며, 해당 키로 API 호출 시 `401 Unauthorized` 에러 발생

## 문제 해결

### 401 Unauthorized 에러

**원인**:
- API 키가 잘못됨
- API 키가 삭제됨
- Authorization 헤더 형식 오류

**해결**:
```bash
# ✅ 올바른 형식
Authorization: Bearer wzp_live_abc123...

# ❌ 잘못된 형식
Authorization: wzp_live_abc123...  # "Bearer " 누락
Authorization: Bearer: wzp_live_abc123...  # 콜론 잘못 추가
```

### API 키가 작동하지 않음

1. API 키가 정확한지 확인 (복사 시 공백 포함 안 됨?)
2. 웹 UI에서 키가 삭제되지 않았는지 확인
3. 헤더 형식 확인: `Authorization: Bearer <KEY>`

## 테스트 자동화 예제

### Playwright (E2E 테스트)

```typescript
// tests/api.spec.ts
import { test, expect } from '@playwright/test';

const API_URL = process.env.WZPRINT_API_URL;
const API_KEY = process.env.WZPRINT_API_KEY;

test('API 키로 주문 목록 조회', async ({ request }) => {
  const response = await request.get(`${API_URL}/api/orders`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`
    }
  });

  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  expect(data.orders).toBeDefined();
});

test('API 키로 새 주문 생성', async ({ request }) => {
  const newOrder = {
    customer_name: '테스트 고객',
    product_name: '테스트 상품',
    quantity: 100,
    barcode: '1234567890'
  };

  const response = await request.post(`${API_URL}/api/orders`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    data: newOrder
  });

  expect(response.ok()).toBeTruthy();
});
```

### Vitest (API 통합 테스트)

```typescript
// tests/api.test.ts
import { describe, it, expect } from 'vitest';

const API_URL = process.env.WZPRINT_API_URL;
const API_KEY = process.env.WZPRINT_API_KEY;

describe('wzprint API', () => {
  it('should fetch orders with API key', async () => {
    const res = await fetch(`${API_URL}/api/orders`, {
      headers: { 'Authorization': `Bearer ${API_KEY}` }
    });

    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.orders).toBeDefined();
  });
});
```

## FAQ

### Q: API 키는 몇 개까지 생성할 수 있나요?

A: 제한 없습니다. 용도별로 여러 개 생성하는 것을 권장합니다 (예: "로컬 테스트", "CI/CD", "외부 연동").

### Q: API 키의 유효기간은?

A: 무기한입니다. 명시적으로 삭제하기 전까지 계속 사용 가능합니다.

### Q: JWT 토큰과 API 키의 차이는?

A:
- **JWT**: 브라우저에서 사용자 로그인 후 발급, 7일 유효
- **API 키**: 프로그래밍/자동화용, 무기한 유효

### Q: API 키가 유출되었어요!

A:
1. 즉시 웹 UI에서 해당 키 삭제
2. 새 키 생성
3. 시스템/스크립트 업데이트

### Q: 서비스 런칭 후에도 계속 사용 가능한가요?

A: 네! API 키는 운영 환경용으로 설계되어 서비스 런칭 후에도 계속 사용 가능합니다.

## 관련 문서

- [API 문서](../workers/README.md)
- [CLAUDE.md](../workers/CLAUDE.md) - 배포 가이드
- [구현 가이드](./구현가이드.md)

## 지원

문제가 발생하면 GitHub Issues에 등록해주세요.
