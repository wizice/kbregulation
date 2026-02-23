/**
 * KB신용정보 내규 시스템 - 공통 모듈
 * @module kbregulation_common
 */

// ============================================
// 전역 상태 관리
// ============================================
export const AppState = {
    hospitalRegulations: {},
    isLoading: false,
    currentRegulation: null,
    currentChapter: null,
    regulationHistory: [],
    isNavigatingBack: false,
    isStorageAvailable: false,
    currentSearchResults: [],
    currentSearchTerm: '',
    activeSearchType: 'all',
    currentLayoutMode: 2,
    currentFontFamily: 'nanumsquare',
    currentUserInfo: null
};

// ============================================
// Storage 유틸리티
// ============================================

/**
 * 안전한 localStorage 저장
 */
export function safeSetStorage(key, value) {
    if (!AppState.isStorageAvailable) return false;
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (e) {
        console.warn('localStorage 저장 실패:', e);
        return false;
    }
}

/**
 * 안전한 localStorage 읽기
 */
export function safeGetStorage(key, defaultValue = null) {
    if (!AppState.isStorageAvailable) return defaultValue;
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        console.warn('localStorage 읽기 실패:', e);
        return defaultValue;
    }
}

/**
 * localStorage 초기화
 */
export function initializeLocalStorage() {
    try {
        const testKey = '__storage_test__';
        localStorage.setItem(testKey, testKey);
        localStorage.removeItem(testKey);
        AppState.isStorageAvailable = true;
        console.log('localStorage 사용 가능');
    } catch (e) {
        AppState.isStorageAvailable = false;
        console.warn('localStorage를 사용할 수 없습니다:', e);
    }
}

// ============================================
// 날짜/시간 유틸리티
// ============================================

/**
 * 날짜 포맷팅 (YYYY.MM.DD.)
 */
export function formatDate(dateString) {
    if (!dateString || dateString === '-') return '-';

    // ISO 형식 또는 YYYY-MM-DD 형식 처리
    const match = dateString.match(/(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
        return `${match[1]}.${match[2]}.${match[3]}.`;
    }

    // 이미 YYYY.MM.DD. 형식인 경우
    if (/^\d{4}\.\d{2}\.\d{2}\.$/.test(dateString)) {
        return dateString;
    }

    return dateString;
}

/**
 * 한국어 날짜 파싱
 */
export function parseKoreanDate(dateString) {
    if (!dateString) return null;

    // "2024년 3월 15일" 형식
    const koreanMatch = dateString.match(/(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일/);
    if (koreanMatch) {
        return new Date(
            parseInt(koreanMatch[1]),
            parseInt(koreanMatch[2]) - 1,
            parseInt(koreanMatch[3])
        );
    }

    // "2024.03.15" 또는 "2024.03.15." 형식
    const dotMatch = dateString.match(/(\d{4})\.(\d{1,2})\.(\d{1,2})\.?/);
    if (dotMatch) {
        return new Date(
            parseInt(dotMatch[1]),
            parseInt(dotMatch[2]) - 1,
            parseInt(dotMatch[3])
        );
    }

    // ISO 형식
    const isoMatch = dateString.match(/(\d{4})-(\d{2})-(\d{2})/);
    if (isoMatch) {
        return new Date(
            parseInt(isoMatch[1]),
            parseInt(isoMatch[2]) - 1,
            parseInt(isoMatch[3])
        );
    }

    return null;
}

/**
 * 상대 시간 텍스트 생성
 */
export function getTimeAgoText(dateString, index = 0) {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '방금 전';
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;

    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
}

/**
 * 오늘 날짜인지 확인
 */
export function isToday(date) {
    const today = new Date();
    return date.getDate() === today.getDate() &&
           date.getMonth() === today.getMonth() &&
           date.getFullYear() === today.getFullYear();
}

/**
 * 날짜를 비교용 문자열로 변환
 */
export function formatDateForComparison(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}.`;
}

// ============================================
// UI 유틸리티
// ============================================

/**
 * 토스트 메시지 표시
 */
export function showToast(message, type = 'info') {
    // 기존 토스트 제거
    const existingToast = document.querySelector('.toast-message');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast-message toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;

    document.body.appendChild(toast);

    // 애니메이션 시작
    setTimeout(() => toast.classList.add('show'), 10);

    // 자동 제거
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * HTML 이스케이프
 */
export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 검색어 하이라이트
 */
export function highlightText(text, searchTerm) {
    if (!searchTerm || !text) return text;

    const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark class="search-highlight">$1</mark>');
}

/**
 * 모든 스크롤 초기화
 */
export function resetAllScrolls() {
    // 메인 콘텐츠 스크롤
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.scrollTop = 0;
    }

    // contentBody 스크롤
    const contentBody = document.getElementById('contentBody');
    if (contentBody) {
        contentBody.scrollTop = 0;
    }

    // 윈도우 스크롤
    window.scrollTo(0, 0);
}

/**
 * 더보기 토글
 */
export function toggleMoreItems(button) {
    const moreItems = button.previousElementSibling;
    if (moreItems) {
        const isHidden = moreItems.style.display === 'none';
        moreItems.style.display = isHidden ? 'block' : 'none';
        button.innerHTML = isHidden
            ? '<i class="fas fa-chevron-up"></i> 접기'
            : `<i class="fas fa-chevron-down"></i> 더보기`;
    }
}

// ============================================
// 설정 관리
// ============================================

/**
 * 폰트 설정
 */
export function setFontFamily(fontName, saveToStorage = true) {
    // 기존 폰트 클래스 제거
    document.body.classList.remove(
        'font-yonsei', 'font-noto', 'font-spoqa',
        'font-pretendard', 'font-malgun', 'font-nanum', 'font-nanumsquare'
    );

    // 새 폰트 클래스 추가
    if (fontName && fontName !== 'yonsei') {
        document.body.classList.add(`font-${fontName}`);
    }

    // 활성 상태 업데이트
    document.querySelectorAll('.font-option').forEach(option => {
        option.classList.toggle('active', option.dataset.font === fontName);
    });

    AppState.currentFontFamily = fontName;

    if (saveToStorage) {
        safeSetStorage('kbregulation_font', fontName);
    }
}

/**
 * 폰트 설정 로드
 */
export function loadFontSettings() {
    const savedFont = safeGetStorage('kbregulation_font', 'nanumsquare');
    setFontFamily(savedFont, false);
}

/**
 * 레이아웃 모드 설정
 */
export function setLayoutMode(mode, saveToStorage = true) {
    AppState.currentLayoutMode = mode;

    // 레이아웃 옵션 활성화 상태 업데이트
    document.querySelectorAll('.layout-option').forEach(option => {
        option.classList.toggle('active', parseInt(option.dataset.layout) === mode);
    });

    // 바디 클래스 업데이트
    document.body.classList.remove('layout-mode-1', 'layout-mode-2', 'layout-mode-3');
    document.body.classList.add(`layout-mode-${mode}`);

    if (saveToStorage) {
        safeSetStorage('kbregulation_layout', mode);
    }
}

/**
 * 레이아웃 설정 로드
 */
export function loadLayoutSettings() {
    const savedLayout = safeGetStorage('kbregulation_layout', 2);
    setLayoutMode(savedLayout, false);
}

/**
 * 레이아웃 설정 패널 토글
 */
export function toggleLayoutSettings() {
    const panel = document.getElementById('layoutSettingsPanel');
    if (panel) {
        panel.classList.toggle('active');
    }
}

/**
 * 레이아웃 설정 패널 닫기
 */
export function closeLayoutSettings() {
    const panel = document.getElementById('layoutSettingsPanel');
    if (panel) {
        panel.classList.remove('active');
    }
}

// ============================================
// 네비게이션 유틸리티
// ============================================

/**
 * 메인 페이지로 새로고침
 */
export function refreshToMainPage() {
    window.location.href = window.location.pathname;
}

/**
 * 네비게이션 활성화 상태 업데이트
 */
export function updateNavigation(activeTab) {
    document.querySelectorAll('.nav-link').forEach(link => {
        const linkText = link.textContent.trim();
        link.classList.toggle('active', linkText === activeTab);
    });
}

/**
 * 모달 닫기
 */
export function closeModal() {
    const modal = document.getElementById('detailModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// ============================================
// 유틸리티 함수들
// ============================================

/**
 * 부서 정보 추출 (소관부서만 사용)
 */
export function getDepartment(regulation) {
    if (regulation.detail?.documentInfo?.소관부서) {
        return regulation.detail.documentInfo.소관부서;
    }
    if (regulation.detailData?.문서정보?.소관부서) {
        return regulation.detailData.문서정보.소관부서;
    }
    return '';
}

/**
 * 검색 타입 텍스트 변환
 */
export function getSearchTypeText(searchType) {
    const typeMap = {
        'all': '전체',
        'title': '규정명',
        'content': '본문',
        'appendix': '부록'
    };
    return typeMap[searchType] || '전체';
}

/**
 * 규정 요약 생성
 */
export function getRegulationSummary(regulation) {
    if (regulation.detail?.documentInfo) {
        const docInfo = regulation.detail.documentInfo;
        return `소관부서: ${docInfo.소관부서 || '-'} | 제정일: ${docInfo.제정일 || '-'}`;
    }
    return '';
}

// ============================================
// 전역 노출 (하위 호환성)
// ============================================
if (typeof window !== 'undefined') {
    window.AppState = AppState;
    window.safeSetStorage = safeSetStorage;
    window.safeGetStorage = safeGetStorage;
    window.initializeLocalStorage = initializeLocalStorage;
    window.formatDate = formatDate;
    window.parseKoreanDate = parseKoreanDate;
    window.getTimeAgoText = getTimeAgoText;
    window.showToast = showToast;
    window.escapeHtml = escapeHtml;
    window.highlightText = highlightText;
    window.resetAllScrolls = resetAllScrolls;
    window.toggleMoreItems = toggleMoreItems;
    window.setFontFamily = setFontFamily;
    window.loadFontSettings = loadFontSettings;
    window.setLayoutMode = setLayoutMode;
    window.loadLayoutSettings = loadLayoutSettings;
    window.toggleLayoutSettings = toggleLayoutSettings;
    window.closeLayoutSettings = closeLayoutSettings;
    window.refreshToMainPage = refreshToMainPage;
    window.updateNavigation = updateNavigation;
    window.closeModal = closeModal;
    window.getDepartment = getDepartment;
    window.getSearchTypeText = getSearchTypeText;
    window.getRegulationSummary = getRegulationSummary;
}
