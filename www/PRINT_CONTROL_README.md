# 도메인별 인쇄 기능 제어

## 📋 개요

세브란스 내규 상세보기 페이지에서 **도메인별로 인쇄 기능을 제어**합니다.

- `policy.wizice.com` (개발): ✅ 인쇄 허용
- `policy-internal.yuhs.ac` (내부망): ✅ 인쇄 허용
- `policy.yuhs.ac` (외부망): ❌ 인쇄 차단
- 기타 도메인: ❌ 인쇄 차단

---

## 🔧 구현 방식

### 순수 JavaScript 방식 (클라이언트 사이드)

```javascript
// 도메인 설정
const DOMAIN_CONFIG = {
    printAllowedDomains: [
        'policy.wizice.com',
        'policy-internal.yuhs.ac',
        'localhost',
        '127.0.0.1'
    ]
};

// 도메인 체크
function isPrintAllowed() {
    return DOMAIN_CONFIG.printAllowedDomains.includes(window.location.hostname);
}
```

---

## 📁 적용된 파일

### 1. severance_page.html
- **경로**: `/home/wizice/regulation/www/severance_page.html`
- **용도**: FastAPI 서버 사이드 렌더링 페이지 (Jinja2 템플릿)
- **수정 내용**:
  - 인쇄 버튼에 `print-btn` 클래스 추가
  - `DOMAIN_CONFIG` 설정 추가
  - `isPrintAllowed()` 함수 추가
  - `printRegulation()` 함수에 도메인 체크 추가
  - `DOMContentLoaded` 이벤트에서 인쇄 버튼 표시/숨김
  - `Ctrl+P` 키보드 단축키에 도메인 체크 추가

### 2. severance_page_static.html
- **경로**: `/home/wizice/regulation/www/severance_page_static.html`
- **용도**: 정적 HTML 파일 (URL 파라미터 기반)
- **수정 내용**: severance_page.html과 동일

---

## 🎯 동작 방식

### 1. 페이지 로드 시

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const printButton = document.querySelector('.print-btn');

    if (!isPrintAllowed()) {
        // 허용되지 않은 도메인: 버튼 숨김
        printButton.style.display = 'none';
        console.log('[Domain Control] 인쇄 버튼이 숨겨졌습니다.');
    } else {
        console.log('[Domain Control] 인쇄 버튼이 활성화되었습니다.');
    }
});
```

### 2. 인쇄 버튼 클릭 시

```javascript
function printRegulation() {
    if (!isPrintAllowed()) {
        alert('이 도메인에서는 인쇄 기능을 사용할 수 없습니다.\n\n허용된 도메인:\n- policy.wizice.com\n- policy-internal.yuhs.ac');
        console.warn('[Domain Control] 인쇄 기능이 차단되었습니다.');
        return false;
    }

    console.log('[Print] 인쇄를 시작합니다.');
    window.print();
}
```

### 3. 키보드 단축키 (Ctrl+P)

```javascript
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'p') {
        e.preventDefault();

        if (isPrintAllowed()) {
            window.print();
        } else {
            alert('이 도메인에서는 인쇄 기능을 사용할 수 없습니다.\n\n허용된 도메인:\n- policy.wizice.com\n- policy-internal.yuhs.ac');
            console.warn('[Domain Control] 인쇄 단축키가 차단되었습니다.');
        }
    }
});
```

---

## 🧪 테스트 방법

### 1. 개발 서버 (localhost)

```bash
# 브라우저에서 접속
http://localhost/severance_page_static.html?chapter=1&code=1_1
```

**예상 결과**:
- ✅ 인쇄 버튼 보임
- ✅ 인쇄 버튼 클릭 시 인쇄 창 열림
- ✅ Ctrl+P 동작함
- Console: `[Domain Control] 현재 도메인: localhost, 인쇄 허용: true`

### 2. 개발 서버 (policy.wizice.com)

```bash
# 브라우저에서 접속
https://policy.wizice.com:8443/severance_page_static.html?chapter=1&code=1_1
```

**예상 결과**:
- ✅ 인쇄 버튼 보임
- ✅ 인쇄 기능 정상 동작
- Console: `[Domain Control] 현재 도메인: policy.wizice.com, 인쇄 허용: true`

### 3. 내부망 (policy-internal.yuhs.ac)

```bash
# 내부망에서 접속
https://policy-internal.yuhs.ac/severance_page_static.html?chapter=1&code=1_1
```

**예상 결과**:
- ✅ 인쇄 버튼 보임
- ✅ 인쇄 기능 정상 동작
- Console: `[Domain Control] 현재 도메인: policy-internal.yuhs.ac, 인쇄 허용: true`

### 4. 외부망 (policy.yuhs.ac)

```bash
# 외부망에서 접속
https://policy.yuhs.ac/severance_page_static.html?chapter=1&code=1_1
```

**예상 결과**:
- ❌ 인쇄 버튼 숨김 (보이지 않음)
- ❌ Ctrl+P 시 경고 메시지: "이 도메인에서는 인쇄 기능을 사용할 수 없습니다."
- Console: `[Domain Control] 현재 도메인: policy.yuhs.ac, 인쇄 허용: false`
- Console: `[Domain Control] 인쇄 버튼이 숨겨졌습니다.`

### 5. 브라우저 개발자 도구 테스트

```javascript
// 브라우저 콘솔에서 실행
console.log('현재 도메인:', getCurrentDomain());
console.log('인쇄 허용:', isPrintAllowed());

// 강제로 인쇄 시도 (버튼 숨김 우회)
printRegulation();  // 허용되지 않은 도메인에서는 경고 메시지 출력
```

---

## 🔍 디버깅

### Console 로그 확인

모든 동작에서 Console에 로그가 출력됩니다:

```
[Domain Control] 현재 도메인: policy.yuhs.ac, 인쇄 허용: false
[Domain Control] 인쇄 버튼이 숨겨졌습니다.
[Domain Control] 인쇄 기능이 차단되었습니다.
[Domain Control] 인쇄 단축키가 차단되었습니다.
```

### 브라우저 개발자 도구

1. **F12** 키를 눌러 개발자 도구 열기
2. **Console** 탭 확인
3. `[Domain Control]` 로그 확인

---

## ⚙️ 설정 변경 방법

### 허용 도메인 추가/삭제

두 파일 모두 수정 필요:
1. `severance_page.html` (라인 168-173)
2. `severance_page_static.html` (라인 808-813)

```javascript
const DOMAIN_CONFIG = {
    printAllowedDomains: [
        'policy.wizice.com',
        'policy-internal.yuhs.ac',
        'new-domain.com',  // 새 도메인 추가
        'localhost',
        '127.0.0.1'
    ]
};
```

### 경고 메시지 변경

```javascript
alert('이 도메인에서는 인쇄 기능을 사용할 수 없습니다.\n\n허용된 도메인:\n- policy.wizice.com\n- policy-internal.yuhs.ac');
```

---

## ⚠️ 보안 고려사항

### 1. JavaScript 비활성화 우회

**한계**: 사용자가 JavaScript를 비활성화하면 이 제어가 동작하지 않습니다.

**대응**:
- 일반 사용자는 JavaScript를 끄지 않음
- UI 레벨 제어로 충분한 경우가 많음
- 더 강력한 보안이 필요하면 서버 사이드 제어 추가 필요

### 2. 개발자 도구 우회

**한계**: 개발자 도구로 버튼을 다시 보이게 할 수 있습니다.

**대응**:
- `printRegulation()` 함수에서 이중 체크
- 함수 호출 시에도 도메인 검증

### 3. 브라우저 기본 인쇄 (Ctrl+P)

**한계**: Ctrl+P는 막지만, 브라우저 메뉴 → 인쇄는 막을 수 없습니다.

**대응**:
- `@media print` CSS로 워터마크 추가 (이미 구현됨: "대외비")
- 중요 정보는 이미지로 렌더링
- 서버 사이드에서 PDF 생성 시 워터마크 추가

---

## 🚀 향후 개선 방안

### 1. 중앙 설정 파일 분리

```javascript
// /static/js/domain-config.js (별도 파일)
const DomainConfig = {
    features: {
        print: {
            allowed: ['policy.wizice.com', 'policy-internal.yuhs.ac']
        },
        export: {
            allowed: ['policy-internal.yuhs.ac']
        }
    },

    isFeatureAllowed(feature) {
        return this.features[feature]?.allowed.includes(window.location.hostname);
    }
};
```

### 2. 서버 사이드 제어 추가

```python
# FastAPI 라우터
@app.get("/severance/page")
async def severance_page(request: Request):
    host = request.headers.get("host", "").split(":")[0]

    features = {
        "print_enabled": host in ["policy.wizice.com", "policy-internal.yuhs.ac"]
    }

    return templates.TemplateResponse("severance_page.html", {
        "request": request,
        "features": features
    })
```

### 3. IP 기반 제어

```javascript
// 내부망 IP 대역 체크
async function isInternalNetwork() {
    const response = await fetch('/api/network-check');
    const data = await response.json();
    return data.is_internal;
}
```

---

## 📊 적용 현황

| 파일명 | 경로 | 상태 | 비고 |
|--------|------|------|------|
| severance_page.html | /www/severance_page.html | ✅ 완료 | FastAPI 템플릿 |
| severance_page_static.html | /www/severance_page_static.html | ✅ 완료 | 정적 HTML |

---

## 📝 변경 이력

- **2025-10-31**: 초기 구현 (순수 JavaScript 방식)
  - 도메인별 인쇄 버튼 표시/숨김
  - 인쇄 함수 도메인 체크
  - Ctrl+P 단축키 도메인 체크
  - Console 로그 추가

---

## 🔗 관련 파일

- `/www/severance_page.html` - FastAPI 템플릿
- `/www/severance_page_static.html` - 정적 HTML
- `/www/static/css/severance.css` - 스타일시트
- `/fastapi/CLAUDE.md` - 프로젝트 개발 가이드

---

**작성자**: Claude AI Assistant
**최종 수정**: 2025-10-31
