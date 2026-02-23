/**
 * 강화된 브라우저 뒤로가기 버튼 완전 차단 모듈
 */

let historyBlockerActive = true;
let historyStack = 0;

// 히스토리 스택을 지속적으로 유지하는 함수
function maintainHistoryStack() {
    // 히스토리 스택이 부족하면 계속 추가
    if (historyStack < 50) {
        for (let i = 0; i < 50; i++) {
            history.pushState({blocked: true, index: i}, '', window.location.href);
            historyStack++;
        }
        console.log('히스토리 스택 보충됨:', historyStack);
    }
}

// popstate 이벤트 완전 차단
function blockPopstateEvent(event) {
    if (!historyBlockerActive) return;
    
    event.preventDefault();
    event.stopImmediatePropagation();
    
    console.log('뒤로가기 이벤트 차단됨, 현재 스택:', historyStack);
    
    // 히스토리 스택 감소
    historyStack--;
    
    // 즉시 히스토리 보충
    setTimeout(() => {
        maintainHistoryStack();
    }, 1);
    
    // 현재 페이지 상태 강제 유지
    setTimeout(() => {
        history.pushState({blocked: true, index: Date.now()}, '', window.location.href);
        historyStack++;
    }, 10);
    
    return false;
}

// 마우스 버튼으로 뒤로가기 차단 (일부 마우스의 뒤로가기 버튼)
function blockMouseNavigation(event) {
    if (!historyBlockerActive) return;
    
    // 마우스 뒤로가기 버튼 (button 3)
    if (event.button === 3) {
        event.preventDefault();
        event.stopImmediatePropagation();
        console.log('마우스 뒤로가기 버튼 차단됨');
        return false;
    }
    
    // 마우스 앞으로가기 버튼 (button 4)  
    if (event.button === 4) {
        event.preventDefault();
        event.stopImmediatePropagation();
        console.log('마우스 앞으로가기 버튼 차단됨');
        return false;
    }
}

// 뒤로가기 차단 초기화
function initializeEnhancedHistoryBlocker() {
    console.log('강화된 히스토리 차단기 초기화 시작');
    
    // 초기 히스토리 스택 생성
    maintainHistoryStack();
    
    // popstate 이벤트 리스너 등록 (캡처와 버블링 단계 모두에서)
    window.addEventListener('popstate', blockPopstateEvent, true);  // 캡처 단계
    window.addEventListener('popstate', blockPopstateEvent, false); // 버블링 단계
    
    // 마우스 이벤트 차단
    document.addEventListener('mousedown', blockMouseNavigation, true);
    window.addEventListener('mousedown', blockMouseNavigation, true);
    
    // 정기적으로 히스토리 스택 점검 및 보충
    setInterval(function() {
        if (historyBlockerActive && historyStack < 30) {
            maintainHistoryStack();
        }
    }, 1000); // 1초마다 점검
    
    // 페이지 포커스 시에도 히스토리 보충
    window.addEventListener('focus', function() {
        if (historyBlockerActive) {
            setTimeout(maintainHistoryStack, 100);
        }
    });
    
    // 페이지 가시성 변경 시에도 히스토리 보충
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && historyBlockerActive) {
            setTimeout(maintainHistoryStack, 100);
        }
    });
    
    console.log('강화된 히스토리 차단기 초기화 완료');
}

// 차단 기능 활성화/비활성화 (디버깅 및 테스트용)
function setHistoryBlocker(enabled) {
    historyBlockerActive = enabled;
    console.log('히스토리 차단기', enabled ? '활성화' : '비활성화');
}

// 현재 상태 확인 (디버깅용)
function getHistoryBlockerStatus() {
    return {
        active: historyBlockerActive,
        stackSize: historyStack,
        historyLength: history.length
    };
}

// 페이지 로드 시 즉시 실행
document.addEventListener('DOMContentLoaded', function() {
    initializeEnhancedHistoryBlocker();
});

// window load에도 추가 보안
window.addEventListener('load', function() {
    setTimeout(() => {
        if (historyBlockerActive) {
            maintainHistoryStack();
        }
    }, 500);
});

// 전역 함수로 노출 (디버깅용)
window.setHistoryBlocker = setHistoryBlocker;
window.getHistoryBlockerStatus = getHistoryBlockerStatus;
