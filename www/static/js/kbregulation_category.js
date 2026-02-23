/**
 * KB신용정보 내규 시스템 - 분류 페이지 모듈
 * @module kbregulation_category
 */

import { AppState, showToast, updateNavigation } from './kbregulation_common.js';

// ============================================
// 분류 페이지 함수
// ============================================

/**
 * 분류 페이지 표시
 */
export function displayCategoryContent() {
    const contentBody = document.getElementById('contentBody');
    if (!contentBody) return;

    // 통계 계산
    const stats = calculateCategoryStats();

    let html = `
        <div class="category-page">
            <div class="category-header">
                <h2><i class="fas fa-folder-open"></i> 내규 분류</h2>
                <div class="category-stats">
                    <span>총 ${stats.totalChapters}개 장</span>
                    <span>${stats.totalRegulations}개 내규</span>
                </div>
                <div class="category-controls">
                    <button id="expandAllBtn" class="category-btn" onclick="expandAllChapters()">
                        <i class="fas fa-expand-alt"></i> 모두 펼치기
                    </button>
                    <button id="collapseAllBtn" class="category-btn" style="display: none;" onclick="collapseAllChapters()">
                        <i class="fas fa-compress-alt"></i> 모두 접기
                    </button>
                </div>
            </div>
            <div class="category-cards">
                ${renderCategoryCards()}
            </div>
        </div>
    `;

    contentBody.innerHTML = html;
}

/**
 * 분류 카드 렌더링
 */
function renderCategoryCards() {
    if (!AppState.hospitalRegulations || Object.keys(AppState.hospitalRegulations).length === 0) {
        return `
            <div class="category-empty">
                <i class="fas fa-folder-open"></i>
                <h3>내규 데이터를 불러오는 중...</h3>
            </div>
        `;
    }

    return Object.entries(AppState.hospitalRegulations).map(([chapter, chapterData]) => {
        const regulationCount = chapterData.regulations?.length || 0;

        return `
            <div class="chapter-card" data-chapter="${chapter}">
                <div class="chapter-card-header">
                    <div class="chapter-info">
                        <span class="chapter-number">${chapter}</span>
                        <span class="chapter-title">${chapterData.title}</span>
                    </div>
                    <div class="chapter-meta">
                        <span class="regulation-count">${regulationCount}개 내규</span>
                        <i class="fas fa-chevron-down chapter-toggle-icon"></i>
                    </div>
                </div>
                <div class="chapter-regulations" style="display: none;">
                    ${renderChapterRegulations(chapter, chapterData.regulations || [])}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 챕터 내 규정 목록 렌더링
 */
function renderChapterRegulations(chapter, regulations) {
    if (!regulations || regulations.length === 0) {
        return '<div class="no-regulations">등록된 내규가 없습니다.</div>';
    }

    return regulations.map(regulation => {
        const hasAppendix = regulation.appendix && regulation.appendix.length > 0;
        const appendixCount = hasAppendix ? regulation.appendix.length : 0;

        return `
            <div class="regulation-group">
                <div class="main-regulation" onclick="openCategoryRegulation('${chapter}', '${regulation.code}')">
                    <span class="reg-code">${regulation.code}</span>
                    <span class="reg-name">${regulation.name}</span>
                    ${hasAppendix ? `
                        <button class="sub-toggle" onclick="event.stopPropagation(); toggleSubRegulations(this);">
                            <i class="fas fa-paperclip"></i>
                            <span>${appendixCount}</span>
                        </button>
                    ` : ''}
                </div>
                ${hasAppendix ? renderAppendixList(regulation, chapter) : ''}
            </div>
        `;
    }).join('');
}

/**
 * 부록 목록 렌더링
 */
function renderAppendixList(regulation, chapter) {
    let safeAppendixArray = [];

    if (Array.isArray(regulation.appendix)) {
        safeAppendixArray = regulation.appendix;
    } else if (typeof regulation.appendix === 'string') {
        safeAppendixArray = [regulation.appendix];
    } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
        try {
            safeAppendixArray = Object.values(regulation.appendix).filter(item => item != null);
        } catch (error) {
            safeAppendixArray = [];
        }
    }

    if (safeAppendixArray.length === 0) return '';

    return `
        <div class="sub-regulations" style="display: none;">
            ${safeAppendixArray.map((appendix, index) => {
                const cleanAppendixName = appendix.replace(/^\d+\.\s*/, '');
                return `
                    <div class="sub-regulation"
                         data-chapter="${chapter}"
                         data-regulation-code="${regulation.code}"
                         data-appendix-index="${index}"
                         onclick="event.stopPropagation(); openAppendixFromCategory('${regulation.code}', ${index}, '${cleanAppendixName.replace(/'/g, "\\'")}')">
                        <i class="fas fa-file-pdf"></i>
                        <span class="reg-name">부록 ${index + 1}. ${cleanAppendixName}</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

/**
 * 통계 계산
 */
function calculateCategoryStats() {
    let totalChapters = 0;
    let totalRegulations = 0;

    Object.entries(AppState.hospitalRegulations).forEach(([chapter, chapterData]) => {
        totalChapters++;
        totalRegulations += chapterData.regulations?.length || 0;
    });

    return { totalChapters, totalRegulations };
}

// ============================================
// 카드 토글
// ============================================

/**
 * 챕터 카드 토글
 */
export function toggleChapterCard(card) {
    if (!card) return;

    const regulations = card.querySelector('.chapter-regulations');
    const isExpanded = card.classList.contains('expanded');

    if (isExpanded) {
        card.classList.remove('expanded');
        regulations.style.display = 'none';
    } else {
        card.classList.add('expanded');
        regulations.style.display = 'block';
    }
}

/**
 * 하위 내규 토글
 */
export function toggleSubRegulations(toggleBtn) {
    const regulationGroup = toggleBtn.closest('.regulation-group');
    const mainRegulation = regulationGroup.querySelector('.main-regulation');
    const subRegulations = regulationGroup.querySelector('.sub-regulations');
    const isExpanded = toggleBtn.classList.contains('expanded');

    if (isExpanded) {
        toggleBtn.classList.remove('expanded');
        mainRegulation.classList.remove('expanded');
        subRegulations.style.display = 'none';
        subRegulations.classList.remove('show');
    } else {
        toggleBtn.classList.add('expanded');
        mainRegulation.classList.add('expanded');
        subRegulations.style.display = 'flex';
        subRegulations.classList.add('show');
    }
}

/**
 * 모든 챕터 펼치기
 */
export function expandAllChapters() {
    const chapterCards = document.querySelectorAll('.chapter-card');
    const expandBtn = document.getElementById('expandAllBtn');
    const collapseBtn = document.getElementById('collapseAllBtn');

    chapterCards.forEach(card => {
        const regulations = card.querySelector('.chapter-regulations');
        if (regulations) {
            card.classList.add('expanded');
            regulations.style.display = 'block';

            // 하위 내규도 펼치기
            const subToggles = card.querySelectorAll('.sub-toggle');
            subToggles.forEach(toggle => {
                const regulationGroup = toggle.closest('.regulation-group');
                const mainRegulation = regulationGroup.querySelector('.main-regulation');
                const subRegulations = regulationGroup.querySelector('.sub-regulations');

                toggle.classList.add('expanded');
                mainRegulation.classList.add('expanded');
                if (subRegulations) {
                    subRegulations.style.display = 'flex';
                    subRegulations.classList.add('show');
                }
            });
        }
    });

    if (expandBtn) expandBtn.style.display = 'none';
    if (collapseBtn) collapseBtn.style.display = 'flex';
}

/**
 * 모든 챕터 접기
 */
export function collapseAllChapters() {
    const chapterCards = document.querySelectorAll('.chapter-card');
    const expandBtn = document.getElementById('expandAllBtn');
    const collapseBtn = document.getElementById('collapseAllBtn');

    chapterCards.forEach(card => {
        const regulations = card.querySelector('.chapter-regulations');
        if (regulations) {
            card.classList.remove('expanded');
            regulations.style.display = 'none';

            // 하위 내규도 접기
            const subToggles = card.querySelectorAll('.sub-toggle');
            subToggles.forEach(toggle => {
                const regulationGroup = toggle.closest('.regulation-group');
                const mainRegulation = regulationGroup.querySelector('.main-regulation');
                const subRegulations = regulationGroup.querySelector('.sub-regulations');

                toggle.classList.remove('expanded');
                mainRegulation.classList.remove('expanded');
                if (subRegulations) {
                    subRegulations.style.display = 'none';
                    subRegulations.classList.remove('show');
                }
            });
        }
    });

    if (expandBtn) expandBtn.style.display = 'flex';
    if (collapseBtn) collapseBtn.style.display = 'none';
}

// ============================================
// 내규 열기
// ============================================

/**
 * 분류에서 내규 열기
 */
export function openCategoryRegulation(chapter, code) {
    const regulation = AppState.hospitalRegulations[chapter]?.regulations?.find(r => r.code === code);

    if (regulation && typeof window.showRegulationDetail === 'function') {
        window.showRegulationDetail(regulation, chapter);
    } else {
        showToast('내규를 찾을 수 없습니다.', 'error');
    }
}

/**
 * 분류에서 부록 열기
 */
export function openAppendixFromCategory(regulationCode, appendixIndex, appendixName) {
    if (typeof window.openAppendixPdf === 'function') {
        window.openAppendixPdf(regulationCode, appendixIndex, appendixName);
    }
}

// ============================================
// 이벤트 위임
// ============================================

/**
 * 분류 페이지 이벤트 초기화
 */
export function initializeCategoryEvents() {
    document.addEventListener('click', function(e) {
        // 챕터 카드 헤더 클릭
        if (e.target.closest('.chapter-card-header')) {
            const header = e.target.closest('.chapter-card-header');
            const card = header.closest('.chapter-card');
            toggleChapterCard(card);
        }
    });
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.displayCategoryContent = displayCategoryContent;
    window.toggleChapterCard = toggleChapterCard;
    window.toggleSubRegulations = toggleSubRegulations;
    window.expandAllChapters = expandAllChapters;
    window.collapseAllChapters = collapseAllChapters;
    window.openCategoryRegulation = openCategoryRegulation;
    window.openAppendixFromCategory = openAppendixFromCategory;
    window.initializeCategoryEvents = initializeCategoryEvents;
}
