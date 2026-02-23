/**
 * KB신용정보 내규 시스템 - 데이터 로딩 모듈
 * @module kbregulation_data
 */

import { AppState, showToast, initializeLocalStorage, loadFontSettings, loadLayoutSettings } from './kbregulation_common.js';

// ============================================
// 데이터 로딩
// ============================================

/**
 * 병원 규정 데이터 로드
 */
export async function loadHospitalRegulations() {
    if (AppState.isLoading) return;
    AppState.isLoading = true;

    try {
        const timestamp = new Date().getTime();
        const response = await fetch(`/static/file/summary_kbregulation.json?ts=${timestamp}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data && typeof data === 'object') {
            AppState.hospitalRegulations = data;
            console.log('규정 데이터 로드 완료:', Object.keys(data).length, '개 챕터');
            return data;
        } else {
            throw new Error('데이터 형식 오류');
        }
    } catch (error) {
        console.error('규정 데이터 로드 실패:', error);
        showToast('데이터를 불러오는데 실패했습니다.', 'error');
        return null;
    } finally {
        AppState.isLoading = false;
    }
}

/**
 * 규정 상세 데이터 로드
 */
export async function loadRegulationDetail(fileName) {
    try {
        const timestamp = new Date().getTime();
        const response = await fetch(`/static/file/${fileName}?ts=${timestamp}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data && typeof data === 'object') {
            return data;
        } else {
            throw new Error('상세 데이터 형식 오류');
        }
    } catch (error) {
        console.error('규정 상세 로드 실패:', error);
        return null;
    }
}

/**
 * 데이터 로드 완료 확인
 */
export async function isDataLoaded() {
    if (Object.keys(AppState.hospitalRegulations).length > 0) {
        return true;
    }

    // 데이터가 없으면 로드 시도
    await loadHospitalRegulations();
    return Object.keys(AppState.hospitalRegulations).length > 0;
}

/**
 * 전체 규정 수집
 */
export function collectAllRegulations() {
    const allRegulations = [];

    Object.entries(AppState.hospitalRegulations).forEach(([chapter, chapterData]) => {
        if (chapterData.regulations && Array.isArray(chapterData.regulations)) {
            chapterData.regulations.forEach(regulation => {
                allRegulations.push({
                    ...regulation,
                    chapter: chapter,
                    chapterTitle: chapterData.title
                });
            });
        }
    });

    return allRegulations;
}

/**
 * 규정 코드로 규정 찾기
 */
export function findRegulationByCode(code) {
    for (const [chapter, chapterData] of Object.entries(AppState.hospitalRegulations)) {
        if (chapterData.regulations) {
            const found = chapterData.regulations.find(r => r.code === code);
            if (found) {
                return { regulation: found, chapter: chapter };
            }
        }
    }
    return null;
}

/**
 * wzRuleSeq로 규정 찾기
 */
export function findRegulationBySeq(wzRuleSeq) {
    for (const [chapter, chapterData] of Object.entries(AppState.hospitalRegulations)) {
        if (chapterData.regulations) {
            const found = chapterData.regulations.find(r => r.wzRuleSeq === wzRuleSeq);
            if (found) {
                return { regulation: found, chapter: chapter };
            }
        }
    }
    return null;
}

// ============================================
// 애플리케이션 초기화
// ============================================

/**
 * 애플리케이션 초기화
 */
export async function initializeApplication() {
    console.log('애플리케이션 초기화 시작...');

    // localStorage 초기화
    initializeLocalStorage();

    // 설정 로드
    loadFontSettings();
    loadLayoutSettings();

    // 규정 데이터 로드
    await loadHospitalRegulations();

    console.log('애플리케이션 초기화 완료');

    return true;
}

// ============================================
// 전역 노출 (하위 호환성)
// ============================================
if (typeof window !== 'undefined') {
    window.loadHospitalRegulations = loadHospitalRegulations;
    window.loadRegulationDetail = loadRegulationDetail;
    window.isDataLoaded = isDataLoaded;
    window.collectAllRegulations = collectAllRegulations;
    window.findRegulationByCode = findRegulationByCode;
    window.findRegulationBySeq = findRegulationBySeq;
    window.initializeApplication = initializeApplication;

    // AppState.hospitalRegulations를 전역으로 노출
    Object.defineProperty(window, 'hospitalRegulations', {
        get: () => AppState.hospitalRegulations,
        set: (value) => { AppState.hospitalRegulations = value; }
    });
}
