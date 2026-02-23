/**
 * KB신용정보 내규 시스템 - 개정이력 모듈
 * @module kbregulation_revision
 */

import { AppState, showToast, formatDate, parseKoreanDate } from './kbregulation_common.js';

// ============================================
// 개정이력 상태
// ============================================

let allRevisionData = [];
let filteredRevisionData = [];
let currentRevisionSort = 'chapter-asc';

// ============================================
// 개정이력 데이터 수집
// ============================================

/**
 * 전체 개정이력 데이터 수집
 */
export function collectRevisionData() {
    allRevisionData = [];

    Object.entries(AppState.hospitalRegulations).forEach(([chapter, chapterData]) => {
        if (!chapterData.regulations) return;

        chapterData.regulations.forEach(regulation => {
            const docInfo = regulation.detail?.documentInfo ||
                           regulation.detailData?.문서정보 ||
                           {};

            allRevisionData.push({
                chapter: chapter,
                chapterTitle: chapterData.title,
                code: regulation.code,
                name: regulation.name,
                제정일: docInfo.제정일 || '-',
                최종개정일: docInfo.최종개정일 || '-',
                최종검토일: docInfo.최종검토일 || '-',
                소관부서: docInfo.소관부서 || '미지정',
                regulation: regulation
            });
        });
    });

    filteredRevisionData = [...allRevisionData];
    return allRevisionData;
}

// ============================================
// 개정이력 페이지
// ============================================

/**
 * 개정이력 페이지 표시
 */
export function displayRevisionContent() {
    const contentBody = document.getElementById('contentBody');
    if (!contentBody) return;

    // 데이터 수집
    if (allRevisionData.length === 0) {
        collectRevisionData();
    }

    // 초기 필터/정렬 적용
    filteredRevisionData = [...allRevisionData];
    sortRevisionData(currentRevisionSort);

    // 통계 계산
    const stats = calculateRevisionStats();

    let html = `
        <div class="revision-page">
            <div class="revision-header">
                <h2><i class="fas fa-history"></i> 개정이력</h2>
                <div class="revision-stats">
                    <span>전체 ${allRevisionData.length}개 내규</span>
                    <span>최근 개정 ${stats.recentlyRevised}건</span>
                </div>
            </div>

            <div class="revision-controls">
                <div class="revision-search">
                    <input type="text" id="revisionSearchInput" placeholder="내규명, 소관부서 검색..."
                           onkeyup="filterRevisionData(this.value)">
                    <i class="fas fa-search"></i>
                </div>
                <div class="revision-sort">
                    <select id="revisionSortSelect" onchange="sortRevisionData(this.value)">
                        <option value="chapter-asc" ${currentRevisionSort === 'chapter-asc' ? 'selected' : ''}>장번호순</option>
                        <option value="name-asc" ${currentRevisionSort === 'name-asc' ? 'selected' : ''}>내규명순</option>
                        <option value="revised-desc" ${currentRevisionSort === 'revised-desc' ? 'selected' : ''}>최종개정일 최신순</option>
                        <option value="revised-asc" ${currentRevisionSort === 'revised-asc' ? 'selected' : ''}>최종개정일 오래된순</option>
                        <option value="enacted-desc" ${currentRevisionSort === 'enacted-desc' ? 'selected' : ''}>제정일 최신순</option>
                        <option value="enacted-asc" ${currentRevisionSort === 'enacted-asc' ? 'selected' : ''}>제정일 오래된순</option>
                    </select>
                </div>
            </div>

            <div class="revision-table-container">
                <table class="revision-table">
                    <thead>
                        <tr>
                            <th>장</th>
                            <th>내규코드</th>
                            <th>내규명</th>
                            <th>제정일</th>
                            <th>최종개정일</th>
                            <th>최종검토일</th>
                            <th>소관부서</th>
                        </tr>
                    </thead>
                    <tbody id="revisionTableBody">
                        ${renderRevisionTableRows()}
                    </tbody>
                </table>
            </div>

            <div class="revision-footer">
                <span id="revisionResultCount">총 ${filteredRevisionData.length}건</span>
            </div>
        </div>
    `;

    contentBody.innerHTML = html;
}

/**
 * 개정이력 테이블 행 렌더링
 */
function renderRevisionTableRows() {
    if (filteredRevisionData.length === 0) {
        return `
            <tr>
                <td colspan="7" class="revision-empty">
                    <i class="fas fa-search"></i>
                    <div>검색 결과가 없습니다</div>
                </td>
            </tr>
        `;
    }

    return filteredRevisionData.map(item => {
        // 최근 6개월 내 개정 여부 표시
        const isRecent = isRecentlyRevised(item.최종개정일);
        const recentClass = isRecent ? 'recently-revised' : '';

        return `
            <tr class="${recentClass}" onclick="openRevisionRegulation('${item.chapter}', '${item.code}')">
                <td>${item.chapter}</td>
                <td>${item.code}</td>
                <td class="revision-name">${item.name}</td>
                <td>${item.제정일}</td>
                <td>${item.최종개정일}${isRecent ? ' <span class="new-badge">NEW</span>' : ''}</td>
                <td>${item.최종검토일}</td>
                <td>${item.소관부서}</td>
            </tr>
        `;
    }).join('');
}

/**
 * 개정이력 통계 계산
 */
function calculateRevisionStats() {
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);

    let recentlyRevised = 0;

    allRevisionData.forEach(item => {
        const revisionDate = parseKoreanDate(item.최종개정일);
        if (revisionDate && revisionDate >= sixMonthsAgo) {
            recentlyRevised++;
        }
    });

    return { recentlyRevised };
}

/**
 * 최근 개정 여부 확인
 */
function isRecentlyRevised(dateString) {
    if (!dateString || dateString === '-') return false;

    const revisionDate = parseKoreanDate(dateString);
    if (!revisionDate) return false;

    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);

    return revisionDate >= sixMonthsAgo;
}

// ============================================
// 필터/정렬
// ============================================

/**
 * 개정이력 데이터 필터링
 */
export function filterRevisionData(searchTerm) {
    const searchLower = searchTerm.toLowerCase();

    if (!searchTerm || searchTerm.trim() === '') {
        filteredRevisionData = [...allRevisionData];
    } else {
        filteredRevisionData = allRevisionData.filter(item => {
            return item.name.toLowerCase().includes(searchLower) ||
                   item.code.toLowerCase().includes(searchLower) ||
                   item.소관부서.toLowerCase().includes(searchLower) ||
                   item.chapter.toLowerCase().includes(searchLower);
        });
    }

    sortRevisionData(currentRevisionSort);
    updateRevisionTable();
}

/**
 * 개정이력 데이터 정렬
 */
export function sortRevisionData(sortType) {
    currentRevisionSort = sortType;

    filteredRevisionData.sort((a, b) => {
        switch (sortType) {
            case 'chapter-asc':
                const chapterA = parseInt(a.chapter.replace('장', ''));
                const chapterB = parseInt(b.chapter.replace('장', ''));
                if (chapterA !== chapterB) return chapterA - chapterB;
                return a.code.localeCompare(b.code, undefined, { numeric: true });

            case 'name-asc':
                return a.name.localeCompare(b.name, 'ko-KR');

            case 'revised-desc':
            case 'revised-asc':
                const dateA = parseKoreanDate(a.최종개정일) || new Date(0);
                const dateB = parseKoreanDate(b.최종개정일) || new Date(0);
                return sortType === 'revised-desc' ? dateB - dateA : dateA - dateB;

            case 'enacted-desc':
            case 'enacted-asc':
                const enactA = parseKoreanDate(a.제정일) || new Date(0);
                const enactB = parseKoreanDate(b.제정일) || new Date(0);
                return sortType === 'enacted-desc' ? enactB - enactA : enactA - enactB;

            default:
                return 0;
        }
    });

    updateRevisionTable();
}

/**
 * 테이블 업데이트
 */
function updateRevisionTable() {
    const tbody = document.getElementById('revisionTableBody');
    const countEl = document.getElementById('revisionResultCount');

    if (tbody) {
        tbody.innerHTML = renderRevisionTableRows();
    }

    if (countEl) {
        countEl.textContent = `총 ${filteredRevisionData.length}건`;
    }
}

/**
 * 개정이력에서 내규 열기
 */
export function openRevisionRegulation(chapter, code) {
    const regulation = AppState.hospitalRegulations[chapter]?.regulations?.find(r => r.code === code);

    if (regulation && typeof window.showRegulationDetail === 'function') {
        window.showRegulationDetail(regulation, chapter);
    } else {
        showToast('내규를 찾을 수 없습니다.', 'error');
    }
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.collectRevisionData = collectRevisionData;
    window.displayRevisionContent = displayRevisionContent;
    window.filterRevisionData = filterRevisionData;
    window.sortRevisionData = sortRevisionData;
    window.openRevisionRegulation = openRevisionRegulation;
}
