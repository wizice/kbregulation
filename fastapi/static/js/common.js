/**
 * 공통 JavaScript 모듈
 * 모든 페이지에서 사용하는 공통 기능
 */

// API 기본 설정
const API_BASE = '/api/v1';

// 공통 유틸리티 함수
const CommonUtils = {
    /**
     * API 호출 래퍼
     */
    async apiCall(url, options = {}) {
        try {
            const response = await fetch(url, {
                ...options,
                credentials: 'include',  // 쿠키 기반 인증
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    alert('세션이 만료되었습니다. 다시 로그인해주세요.');
                    window.location.href = '/login?reason=session_expired';
                    return;
                }
                throw new Error(`API Error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API 호출 실패:', error);
            this.showAlert('오류가 발생했습니다. 다시 시도해주세요.', 'danger');
            throw error;
        }
    },

    /**
     * 알림 메시지 표시
     */
    showAlert(message, type = 'info', duration = 3000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.textContent = message;
        alertDiv.style.cssText = `
            position: fixed;
            top: 70px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => alertDiv.remove(), 300);
        }, duration);
    },

    /**
     * 로딩 스피너 표시/숨김
     */
    showLoading(show = true) {
        let loadingDiv = document.getElementById('global-loading');

        if (show) {
            if (!loadingDiv) {
                loadingDiv = document.createElement('div');
                loadingDiv.id = 'global-loading';
                loadingDiv.innerHTML = `
                    <div class="spinner-backdrop">
                        <div class="spinner"></div>
                    </div>
                `;
                loadingDiv.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.3);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 9998;
                `;
                document.body.appendChild(loadingDiv);
            }
            loadingDiv.style.display = 'flex';
        } else {
            if (loadingDiv) {
                loadingDiv.style.display = 'none';
            }
        }
    },

    /**
     * 날짜 포맷팅
     */
    formatDate(dateStr, format = 'YYYY-MM-DD') {
        const date = new Date(dateStr);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes);
    },

    /**
     * 디바운스 함수
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

/**
 * 로그아웃 처리
 */
async function logout() {
    if (!confirm('로그아웃 하시겠습니까?')) return;

    try {
        await fetch('/api/v1/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('로그아웃 실패:', error);
    }

    // 로그인 페이지로 이동
    window.location.href = '/login';
}

/**
 * 페이지 초기화
 */
document.addEventListener('DOMContentLoaded', () => {
    // 현재 페이지 네비게이션 하이라이트
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });

    // 전역 이벤트 리스너
    document.addEventListener('keydown', (e) => {
        // ESC 키로 모달 닫기
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                modal.style.display = 'none';
                modal.classList.remove('show');
            });
        }
    });
});

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 전역 객체로 내보내기
window.CommonUtils = CommonUtils;