/**
 * KB신용정보 내규 시스템 - 즐겨찾기 모듈
 * @module kbregulation_favorites
 */

import { AppState, showToast, safeSetStorage, safeGetStorage } from './kbregulation_common.js';

// ============================================
// 즐겨찾기 상태
// ============================================

let favoriteRegulations = [];
let filteredFavorites = [];

// ============================================
// 즐겨찾기 초기화
// ============================================

/**
 * 즐겨찾기 초기화 (localStorage 로드)
 */
export function initializeFavorites() {
    try {
        const saved = localStorage.getItem('favoriteRegulations');
        if (saved) {
            favoriteRegulations = JSON.parse(saved);
            console.log(`즐겨찾기 로드: ${favoriteRegulations.length}개`);
        }
    } catch (e) {
        console.warn('즐겨찾기 로드 실패:', e);
        favoriteRegulations = [];
    }

    // 데이터 정리
    migrateLegacyFavorites();
    cleanupFavoriteRegulations();
    updateFavoritesList();
}

/**
 * 즐겨찾기 데이터 가져오기
 */
export function getFavoriteRegulations() {
    return favoriteRegulations;
}

// ============================================
// 유효성 검사
// ============================================

/**
 * 즐겨찾기 데이터 유효성 검사
 */
export function isValidFavoriteItem(item) {
    if (!item || typeof item !== 'object') {
        return false;
    }

    const requiredFields = ['key', 'chapter', 'chapterTitle', 'code', 'name', 'dateAdded', 'department'];

    for (let field of requiredFields) {
        if (!item.hasOwnProperty(field) || item[field] === undefined || item[field] === null) {
            return false;
        }
    }

    const stringFields = ['key', 'chapter', 'chapterTitle', 'code', 'name', 'department'];
    for (let field of stringFields) {
        if (typeof item[field] !== 'string' || item[field].trim() === '') {
            return false;
        }
    }

    if (typeof item.dateAdded !== 'string' || isNaN(Date.parse(item.dateAdded))) {
        return false;
    }

    const keyParts = item.key.split('|');
    if (keyParts.length !== 3) {
        return false;
    }

    if (!item.chapter.includes('장') && !item.key.startsWith('부록|')) {
        return false;
    }

    return true;
}

/**
 * 즐겨찾기 배열 정리
 */
export function cleanupFavoriteRegulations() {
    const originalLength = favoriteRegulations.length;

    favoriteRegulations = favoriteRegulations.filter(item => {
        const isValid = isValidFavoriteItem(item);
        if (!isValid && window.location.hostname === 'localhost') {
            console.warn('잘못된 즐겨찾기 항목 제거:', item);
        }
        return isValid;
    });

    if (originalLength !== favoriteRegulations.length) {
        console.log(`즐겨찾기 정리 완료: ${originalLength}개 → ${favoriteRegulations.length}개`);
        safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
    }

    return favoriteRegulations;
}

/**
 * 기존 문자열 형태 즐겨찾기 마이그레이션
 */
export function migrateLegacyFavorites() {
    let needsMigration = false;

    favoriteRegulations = favoriteRegulations.map(item => {
        if (typeof item === 'string') {
            needsMigration = true;

            let chapter, code, name;

            if (item.includes('|')) {
                const parts = item.split('|');
                chapter = parts[0];
                code = parts[1];
                name = parts[2] || '내규명 미상';
            } else if (item.includes('-')) {
                const parts = item.split('-');
                chapter = parts[0];
                code = parts[1]?.replace('.', '') || '코드미상';
                name = '내규명 미상';
            } else {
                return null;
            }

            return {
                key: `${chapter}|${code}|${name}`,
                chapter: chapter,
                chapterTitle: AppState.hospitalRegulations[chapter]?.title || '장제목 미상',
                code: code,
                name: name,
                dateAdded: new Date().toISOString(),
                department: '소관부서 미지정'
            };
        }

        return item;
    }).filter(item => item !== null);

    if (needsMigration) {
        console.log('기존 즐겨찾기 데이터 마이그레이션 완료');
        safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
    }

    return favoriteRegulations;
}

// ============================================
// 즐겨찾기 토글
// ============================================

/**
 * 즐겨찾기 토글
 */
export function toggleFavorite(regulation, chapter) {
    if (!regulation || !chapter) return;

    const favoriteKey = `${chapter}|${regulation.code}|${regulation.name}`;
    const index = favoriteRegulations.findIndex(fav => fav.key === favoriteKey);
    const favoriteBtn = document.querySelector('.regulation-actions .action-btn[data-tooltip="즐겨찾기"]') ||
                       document.querySelector('.page-actions .action-btn[data-tooltip="즐겨찾기"]');

    if (index > -1) {
        // 제거
        favoriteRegulations.splice(index, 1);
        if (favoriteBtn) favoriteBtn.classList.remove('active');
        showToast(`"${regulation.name}"이(가) 즐겨찾기에서 제거되었습니다.`, 'info');
    } else {
        // 추가
        const favoriteItem = {
            key: favoriteKey,
            chapter: chapter,
            chapterTitle: AppState.hospitalRegulations[chapter]?.title || '',
            code: regulation.code,
            name: regulation.name,
            dateAdded: new Date().toISOString(),
            department: regulation.detail?.documentInfo?.['소관부서'] || '소관부서 미지정'
        };
        favoriteRegulations.push(favoriteItem);
        if (favoriteBtn) favoriteBtn.classList.add('active');
        showToast(`"${regulation.name}"이(가) 즐겨찾기에 추가되었습니다.`, 'success');
    }

    safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
    updateFavoritesList();

    // 즐겨찾기 페이지 업데이트
    if (document.getElementById('contentBody')?.style.display !== 'none' &&
        document.querySelector('.favorites-page')) {
        displayFavoritesContent();
    }
}

/**
 * 부록 즐겨찾기 토글
 */
export function toggleAppendixFavorite(regulation, appendixName, appendixIndex, chapter) {
    if (!regulation || !appendixName) return;

    const favoriteKey = `부록|${regulation.code}|부록${appendixIndex + 1}. ${appendixName}`;
    const index = favoriteRegulations.findIndex(fav => fav.key === favoriteKey);

    if (index > -1) {
        favoriteRegulations.splice(index, 1);
        showToast(`"${appendixName}" 부록이 즐겨찾기에서 제거되었습니다.`, 'info');
    } else {
        const favoriteItem = {
            key: favoriteKey,
            chapter: chapter,
            chapterTitle: AppState.hospitalRegulations[chapter]?.title || '',
            code: regulation.code,
            name: `부록${appendixIndex + 1}. ${appendixName}`,
            dateAdded: new Date().toISOString(),
            department: regulation.detail?.documentInfo?.['소관부서'] || '소관부서 미지정',
            appendixIndex: appendixIndex,
            isAppendix: true
        };
        favoriteRegulations.push(favoriteItem);
        showToast(`"${appendixName}" 부록이 즐겨찾기에 추가되었습니다.`, 'success');
    }

    safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
    updateFavoritesList();
}

/**
 * 즐겨찾기 여부 확인
 */
export function isFavorite(regulation, chapter) {
    if (!regulation || !chapter) return false;
    const favoriteKey = `${chapter}|${regulation.code}|${regulation.name}`;
    return favoriteRegulations.some(fav => fav.key === favoriteKey);
}

// ============================================
// UI 업데이트
// ============================================

/**
 * 사이드바 즐겨찾기 목록 업데이트
 */
export function updateFavoritesList() {
    const favoritesBody = document.getElementById('favoritesBody');
    const favoritesCount = document.getElementById('favoritesCount');

    if (!favoritesBody || !favoritesCount) return;

    cleanupFavoriteRegulations();

    favoritesCount.textContent = favoriteRegulations.length;

    if (favoriteRegulations.length === 0) {
        favoritesBody.innerHTML = `
            <div style="text-align: center; padding: 20px 10px; color: #666; font-size: 12px;">
                <i class="fas fa-star" style="font-size: 20px; color: #ddd; margin-bottom: 8px;"></i>
                <div>즐겨찾기가 없습니다</div>
            </div>
        `;
        return;
    }

    const recentFavorites = favoriteRegulations
        .filter(favorite => isValidFavoriteItem(favorite))
        .sort((a, b) => new Date(b.dateAdded) - new Date(a.dateAdded));

    favoritesBody.innerHTML = recentFavorites.map(favorite => {
        return `
            <div class="panel-item" onclick="openFavoriteRegulation('${favorite.key}')">
                <div>
                    <div class="item-name">
                        ${favorite.code}. ${favorite.name}
                    </div>
                </div>
                <i class="fas fa-times item-remove" onclick="removeFavoriteFromSidebar(event, '${favorite.key}')"></i>
            </div>
        `;
    }).join('');
}

/**
 * 사이드바에서 즐겨찾기 제거
 */
export function removeFavoriteFromSidebar(event, favoriteKey) {
    event.stopPropagation();

    const index = favoriteRegulations.findIndex(fav => fav.key === favoriteKey);
    if (index > -1) {
        const favorite = favoriteRegulations[index];
        favoriteRegulations.splice(index, 1);
        safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
        updateFavoritesList();

        // 현재 보고 있는 내규의 버튼 상태 업데이트
        if (AppState.currentRegulation && AppState.currentChapter) {
            const currentKey = `${AppState.currentChapter}|${AppState.currentRegulation.code}|${AppState.currentRegulation.name}`;
            if (currentKey === favoriteKey) {
                const favoriteBtn = document.querySelector('.regulation-actions .action-btn[data-tooltip="즐겨찾기"]') ||
                                   document.querySelector('.page-actions .action-btn[data-tooltip="즐겨찾기"]');
                if (favoriteBtn) favoriteBtn.classList.remove('active');
            }
        }

        showToast(`"${favorite.name}"이(가) 즐겨찾기에서 제거되었습니다.`, 'info');

        // 즐겨찾기 페이지 업데이트
        if (document.getElementById('contentBody')?.style.display !== 'none' &&
            document.querySelector('.favorites-page')) {
            displayFavoritesContent();
        }
    }
}

/**
 * 즐겨찾기 내규 열기
 */
export function openFavoriteRegulation(favoriteKey) {
    const favorite = favoriteRegulations.find(fav => fav.key === favoriteKey);
    if (!favorite) return;

    if (favorite.key.startsWith('부록|')) {
        openFavoriteAppendix(favorite);
    } else {
        const regulation = AppState.hospitalRegulations[favorite.chapter]?.regulations?.find(reg =>
            reg.code === favorite.code && reg.name === favorite.name
        );

        if (regulation) {
            if (typeof window.showRegulationDetail === 'function') {
                window.showRegulationDetail(regulation, favorite.chapter);
            }
            if (typeof window.closeSidebar === 'function') {
                window.closeSidebar();
            }
        } else {
            showToast('해당 내규를 찾을 수 없습니다.', 'error');
        }
    }
}

/**
 * 즐겨찾기된 부록 열기
 */
export function openFavoriteAppendix(favorite) {
    const keyParts = favorite.key.split('|');
    if (keyParts.length !== 3) {
        showToast('부록 정보가 올바르지 않습니다.', 'error');
        return;
    }

    const regulationCode = keyParts[1];
    const appendixInfo = keyParts[2];
    const appendixMatch = appendixInfo.match(/부록(\d+)\./);
    const appendixIndex = appendixMatch ? parseInt(appendixMatch[1]) - 1 : 0;

    if (typeof window.openAppendixPdf === 'function') {
        window.openAppendixPdf(regulationCode, appendixIndex, appendixInfo);
    }

    if (typeof window.closeSidebar === 'function') {
        window.closeSidebar();
    }
}

// ============================================
// 즐겨찾기 페이지
// ============================================

/**
 * 즐겨찾기 콘텐츠 표시
 */
export function displayFavoritesContent() {
    const contentBody = document.getElementById('contentBody');
    if (!contentBody) return;

    cleanupFavoriteRegulations();

    // 정렬된 즐겨찾기
    const sortedFavorites = [...favoriteRegulations].sort((a, b) =>
        new Date(b.dateAdded) - new Date(a.dateAdded)
    );

    let html = `
        <div class="favorites-page">
            <div class="favorites-header">
                <h2><i class="fas fa-star"></i> 즐겨찾기</h2>
                <div class="favorites-stats">총 ${sortedFavorites.length}개</div>
            </div>
    `;

    if (sortedFavorites.length === 0) {
        html += `
            <div class="favorites-empty">
                <i class="fas fa-star"></i>
                <h3>즐겨찾기가 없습니다</h3>
                <p>내규 상세 화면에서 별 아이콘을 클릭하여 즐겨찾기에 추가할 수 있습니다.</p>
            </div>
        `;
    } else {
        html += `
            <div class="favorites-search">
                <input type="text" id="favoritesSearchInput" placeholder="즐겨찾기 검색..."
                       onkeyup="filterFavorites(this.value)">
            </div>
            <div class="favorites-list" id="favoritesListContainer">
        `;

        sortedFavorites.forEach(favorite => {
            const isAppendix = favorite.key.startsWith('부록|');
            const iconClass = isAppendix ? 'fa-file-pdf' : 'fa-file-alt';
            const formattedDate = new Date(favorite.dateAdded).toLocaleDateString('ko-KR');

            html += `
                <div class="favorites-item" onclick="openFavoriteRegulationFromPage('${favorite.key}')">
                    <div class="favorites-item-icon">
                        <i class="fas ${iconClass}"></i>
                    </div>
                    <div class="favorites-item-content">
                        <div class="favorites-item-title">${favorite.code}. ${favorite.name}</div>
                        <div class="favorites-item-meta">
                            <span>${favorite.chapter}. ${favorite.chapterTitle}</span>
                            <span>${favorite.department}</span>
                            <span>${formattedDate}</span>
                        </div>
                    </div>
                    <div class="favorites-item-actions">
                        <button class="favorites-remove-btn" onclick="event.stopPropagation(); removeFavoriteFromPage('${favorite.key}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        });

        html += '</div>';
    }

    html += '</div>';
    contentBody.innerHTML = html;
}

/**
 * 페이지에서 즐겨찾기 제거
 */
export function removeFavoriteFromPage(favoriteKey) {
    const index = favoriteRegulations.findIndex(fav => fav.key === favoriteKey);
    if (index > -1) {
        const favorite = favoriteRegulations[index];
        favoriteRegulations.splice(index, 1);
        safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
        showToast(`"${favorite.name}"이(가) 즐겨찾기에서 제거되었습니다.`, 'info');
        updateFavoritesList();
        displayFavoritesContent();
    }
}

/**
 * 페이지에서 즐겨찾기 내규 열기
 */
export function openFavoriteRegulationFromPage(favoriteKey) {
    openFavoriteRegulation(favoriteKey);
}

/**
 * 즐겨찾기 필터링
 */
export function filterFavorites(searchTerm) {
    const container = document.getElementById('favoritesListContainer');
    if (!container) return;

    const items = container.querySelectorAll('.favorites-item');
    const searchLower = searchTerm.toLowerCase();

    items.forEach(item => {
        const title = item.querySelector('.favorites-item-title')?.textContent.toLowerCase() || '';
        const meta = item.querySelector('.favorites-item-meta')?.textContent.toLowerCase() || '';

        if (title.includes(searchLower) || meta.includes(searchLower)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.initializeFavorites = initializeFavorites;
    window.getFavoriteRegulations = getFavoriteRegulations;
    window.toggleFavorite = toggleFavorite;
    window.toggleAppendixFavorite = toggleAppendixFavorite;
    window.isFavorite = isFavorite;
    window.updateFavoritesList = updateFavoritesList;
    window.removeFavoriteFromSidebar = removeFavoriteFromSidebar;
    window.openFavoriteRegulation = openFavoriteRegulation;
    window.openFavoriteAppendix = openFavoriteAppendix;
    window.displayFavoritesContent = displayFavoritesContent;
    window.removeFavoriteFromPage = removeFavoriteFromPage;
    window.openFavoriteRegulationFromPage = openFavoriteRegulationFromPage;
    window.filterFavorites = filterFavorites;
    window.cleanupFavoriteRegulations = cleanupFavoriteRegulations;
    window.migrateLegacyFavorites = migrateLegacyFavorites;
}
