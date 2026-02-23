/**
 * KB신용정보 내규 시스템 - 검색 모듈
 * @module kbregulation_search
 */

import { AppState, showToast, highlightText, getSearchTypeText } from './kbregulation_common.js';

// ============================================
// 검색 관련 상태
// ============================================

// AppState에서 관리되는 상태 사용:
// - currentSearchResults
// - currentSearchTerm
// - activeSearchType

// ============================================
// 검색 타입 매핑
// ============================================

/**
 * 로컬 검색 타입을 API 타입으로 매핑
 */
export function mapSearchTypeToAPI(localType) {
    const typeMap = {
        'regu_content': 'content',
        'regu_name': 'title',
        'regu_sup': 'name',
        'regu_sup_content': 'content',
        'regu_dep': 'department',
        'all': 'all'
    };
    return typeMap[localType] || localType;
}

// ============================================
// 로컬 검색 함수
// ============================================

/**
 * 로컬 검색 헬퍼 함수 (결과만 반환)
 */
export function performLocalSearchByType(searchTerm, searchType) {
    let results = [];

    Object.keys(AppState.hospitalRegulations).forEach(chapter => {
        const chapterData = AppState.hospitalRegulations[chapter];

        if (!Array.isArray(chapterData.regulations)) return;

        chapterData.regulations.forEach(regulation => {
            if (!regulation || !regulation.name) return;

            let appendixArray = [];
            if (regulation.appendix) {
                if (Array.isArray(regulation.appendix)) {
                    appendixArray = regulation.appendix;
                } else if (typeof regulation.appendix === 'string') {
                    appendixArray = [regulation.appendix];
                } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
                    try {
                        appendixArray = Object.values(regulation.appendix).filter(item => item != null);
                    } catch (error) {
                        appendixArray = [];
                    }
                }
            }

            let isMatch = false;
            let matchType = '';
            let matchContent = '';
            let appendixIndex = -1;

            if (searchType === 'regu_name') {
                if (regulation.name && regulation.name.includes(searchTerm)) {
                    isMatch = true;
                    matchType = '내규명';
                    matchContent = regulation.name;
                }
            } else if (searchType === 'regu_sup') {
                if (appendixArray.length > 0 && appendixArray.some(app => app && typeof app === 'string' && app.includes(searchTerm))) {
                    isMatch = true;
                    matchType = '부록';
                    const matchedAppendix = appendixArray.find(app => app && typeof app === 'string' && app.includes(searchTerm)) || '';
                    appendixIndex = appendixArray.findIndex(app => app && typeof app === 'string' && app.includes(searchTerm));
                    matchContent = appendixIndex >= 0 ? `부록 ${appendixIndex + 1}. ${matchedAppendix}` : matchedAppendix;
                }
            } else if (searchType === 'regu_dep') {
                const docInfo = regulation.detail?.documentInfo;
                const deptValue = docInfo?.소관부서;
                if (deptValue && deptValue.includes(searchTerm)) {
                    isMatch = true;
                    matchType = '소관부서';
                    matchContent = deptValue;
                }
            }

            if (isMatch) {
                results.push({
                    regulation: regulation,
                    chapter: chapter,
                    chapterTitle: chapterData.title,
                    matchType: matchType,
                    matchContent: matchContent,
                    appendixIndex: appendixIndex
                });
            }
        });
    });

    return results;
}

// ============================================
// API 검색 함수
// ============================================

/**
 * 통합 API 검색 함수
 */
export async function performIntegratedAPISearch(searchTerm) {
    console.log('통합 검색 시작: API + 로컬 검색 혼합');

    const searchResultsSection = document.getElementById('searchResultsSection');
    const resultsBody = document.getElementById('resultsBody');

    try {
        const apiSearchTypes = [
            { local: 'regu_name', api: 'title', korean: '내규명', endpoint: '/api/search/es' },
            { local: 'regu_content', api: 'content', korean: '내규본문', endpoint: '/api/search/es' },
            { local: 'regu_sup_content', api: 'content', korean: '부록내용', endpoint: '/api/search/es/appendix' }
        ];

        const searchPromises = apiSearchTypes.map(async (type) => {
            const apiUrl = `${type.endpoint}?q=${encodeURIComponent(searchTerm)}&search_type=${type.api}&limit=100&page=1`;
            console.log(`API 요청 (${type.korean}): ${apiUrl}`);

            const response = await fetch(apiUrl);
            if (!response.ok) return { type: type.korean, results: [], isAppendix: type.korean === '부록내용' };

            const data = await response.json();
            if (!data.success || !data.results) return { type: type.korean, results: [], isAppendix: type.korean === '부록내용' };

            console.log(`${type.korean} 검색 결과 (API): ${data.results.length}건`);
            return { type: type.korean, results: data.results, isAppendix: type.korean === '부록내용' };
        });

        const allResults = await Promise.all(searchPromises);

        let combinedResults = [];
        allResults.forEach(({ type, results, isAppendix }) => {
            results.forEach(result => {
                if (isAppendix) {
                    const pubno = result.규정표기명 || '';
                    const appendixNo = result.wzappendixno || '1';
                    const appendixIndex = parseInt(appendixNo) - 1;
                    const appendixName = result.wzappendixname || '';
                    const metaContent = `부록 ${appendixNo}. ${appendixName}`;

                    const codeMatch = pubno.match(/^[\d.]+/);
                    const code = codeMatch ? codeMatch[0].replace(/\.$/, '') : pubno;
                    const chapterNum = code.split('.')[0];
                    const finalChapter = `${chapterNum}장`;

                    combinedResults.push({
                        regulation: {
                            name: result.규정명 || 'N/A',
                            code: code,
                            detail: {
                                documentInfo: {
                                    소관부서: result.규정명 || '',
                                    파일명: ''
                                }
                            }
                        },
                        chapter: finalChapter,
                        chapterTitle: result.규정명 || '',
                        matchType: type,
                        matchContent: metaContent,
                        appendixIndex: appendixIndex
                    });
                    return;
                }

                let chapterKey = '';
                let chapterTitle = '';
                let foundRegulation = null;

                if (result.pubno && AppState.hospitalRegulations) {
                    const chapterNum = result.pubno.split('.')[0];
                    const estimatedChapter = `${chapterNum}장`;

                    if (AppState.hospitalRegulations[estimatedChapter]) {
                        const chapterData = AppState.hospitalRegulations[estimatedChapter];
                        const foundReg = chapterData.regulations.find(reg =>
                            reg.code === result.pubno || reg.code === result.pubno.replace(/\.$/, '')
                        );

                        if (foundReg) {
                            foundRegulation = foundReg;
                            chapterKey = estimatedChapter;
                            chapterTitle = chapterData.title || '';
                        }
                    }

                    if (!foundRegulation) {
                        for (const [key, chapterData] of Object.entries(AppState.hospitalRegulations)) {
                            const foundReg = chapterData.regulations.find(reg =>
                                reg.code === result.pubno || reg.code === result.pubno.replace(/\.$/, '')
                            );
                            if (foundReg) {
                                foundRegulation = foundReg;
                                chapterKey = key;
                                chapterTitle = chapterData.title || '';
                                break;
                            }
                        }
                    }
                }

                const extractRegulationCode = (pubno) => {
                    if (!pubno) return 'N/A';
                    const match = pubno.match(/^[\d.]+/);
                    return match ? match[0].replace(/\.$/, '') : pubno;
                };

                const regulationData = foundRegulation || {
                    name: result.name || 'N/A',
                    code: extractRegulationCode(result.pubno),
                    detail: {
                        documentInfo: {
                            소관부서: result.department || '소관부서 미지정',
                            파일명: result.filePath ? result.filePath.split('/').pop() : ''
                        }
                    }
                };

                let finalChapter = chapterKey;
                if (!finalChapter && result.pubno) {
                    const chapterNum = result.pubno.split('.')[0];
                    finalChapter = `${chapterNum}장`;
                }

                combinedResults.push({
                    regulation: regulationData,
                    chapter: finalChapter || '',
                    chapterTitle: chapterTitle || result.name || '',
                    matchType: type,
                    matchContent: result.matchedContent || result.snippet || ''
                });
            });
        });

        // 로컬 검색 추가
        const appendixResults = performLocalSearchByType(searchTerm, 'regu_sup');
        combinedResults = combinedResults.concat(appendixResults);

        const departmentResults = performLocalSearchByType(searchTerm, 'regu_dep');
        combinedResults = combinedResults.concat(departmentResults);

        // 중복 제거
        const uniqueResults = [];
        const seen = new Set();

        combinedResults.forEach(result => {
            const key = `${result.regulation.code}-${result.chapter}-${result.matchType}`;
            if (!seen.has(key)) {
                seen.add(key);
                uniqueResults.push(result);
            }
        });

        combinedResults = uniqueResults;
        AppState.currentSearchResults = combinedResults;

        if (combinedResults.length === 0) {
            resultsBody.innerHTML = `
                <div class="empty-results">
                    <i class="fas fa-search"></i>
                    <h3>검색 결과가 없습니다</h3>
                    <p>"${searchTerm}"에 대한 검색 결과를 찾을 수 없습니다.</p>
                </div>
            `;
            return;
        }

        displaySearchResults(combinedResults, searchTerm, 'all');

    } catch (error) {
        console.error('통합 검색 오류:', error);
        showToast(`검색 중 오류 발생: ${error.message}`, 'error');
        resultsBody.innerHTML = `
            <div class="empty-results">
                <i class="fas fa-exclamation-circle"></i>
                <h3>검색 실패</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

/**
 * API 기반 검색 함수
 */
export async function performAPISearch(searchTerm, searchType) {
    console.log(`API 검색 시작: 검색어="${searchTerm}", 로컬타입="${searchType}"`);

    try {
        const searchResultsSection = document.getElementById('searchResultsSection');
        const resultsBody = document.getElementById('resultsBody');

        searchResultsSection.style.display = 'block';
        resultsBody.innerHTML = '<div class="search-loading"><i class="fas fa-spinner fa-spin"></i> 검색 중...</div>';

        if (searchType === 'all') {
            await performIntegratedAPISearch(searchTerm);
            return;
        }

        const apiSearchType = mapSearchTypeToAPI(searchType);

        let apiUrl;
        if (searchType === 'regu_sup' || searchType === 'regu_sup_content') {
            apiUrl = `/api/search/es/appendix?q=${encodeURIComponent(searchTerm)}&search_type=${apiSearchType}&limit=100&page=1`;
        } else {
            apiUrl = `/api/search/es?q=${encodeURIComponent(searchTerm)}&search_type=${apiSearchType}&limit=100&page=1`;
        }

        const response = await fetch(apiUrl);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`검색 실패: ${response.status} ${errorText}`);
        }

        const data = await response.json();

        if (!data.success) {
            const errorMsg = data.error || data.detail || '알 수 없는 오류';
            showToast(`검색 오류: ${errorMsg}`, 'error');
            resultsBody.innerHTML = `
                <div class="empty-results">
                    <i class="fas fa-exclamation-circle"></i>
                    <h3>검색 실패</h3>
                    <p>${errorMsg}</p>
                </div>
            `;
            return;
        }

        if (!data.results || data.results.length === 0) {
            resultsBody.innerHTML = `
                <div class="empty-results">
                    <i class="fas fa-search"></i>
                    <h3>검색 결과가 없습니다</h3>
                    <p>"${searchTerm}"에 대한 검색 결과를 찾을 수 없습니다.</p>
                </div>
            `;
            return;
        }

        const mapMatchType = (apiMatchType) => {
            if (searchType === 'regu_sup' || searchType === 'regu_sup_content') {
                const appendixMatchTypeMap = {
                    'name': '부록명',
                    'content': '부록내용',
                    'all': '부록'
                };
                return appendixMatchTypeMap[apiMatchType] || '부록내용';
            }

            const matchTypeMap = {
                'title': '내규명',
                'content': '내규본문',
                'appendix': '부록',
                'department': '소관부서'
            };
            return matchTypeMap[apiMatchType] || '내규본문';
        };

        AppState.currentSearchResults = data.results.map((result, index) => {
            if (searchType === 'regu_sup' || searchType === 'regu_sup_content') {
                const appendixNo = result.wzappendixno || '1';
                const appendixIndex = parseInt(appendixNo) - 1;
                const metaContent = `부록 ${appendixNo}. ${result.wzappendixname || ''}`;

                return {
                    regulation: {
                        name: result.규정명 || 'N/A',
                        code: result.규정표기명 || 'N/A',
                        detail: {
                            documentInfo: {
                                소관부서: result.규정명 || '',
                                파일명: ''
                            }
                        }
                    },
                    chapter: '',
                    chapterTitle: result.규정명 || '',
                    matchType: mapMatchType(result.match_type),
                    matchContent: metaContent,
                    appendixIndex: appendixIndex
                };
            }

            let chapterKey = '';
            let chapterTitle = '';
            let foundRegulation = null;

            if (result.pubno && AppState.hospitalRegulations) {
                const chapterNum = result.pubno.split('.')[0];
                const estimatedChapter = `${chapterNum}장`;

                if (AppState.hospitalRegulations[estimatedChapter]) {
                    const chapterData = AppState.hospitalRegulations[estimatedChapter];
                    const foundReg = chapterData.regulations.find(reg =>
                        reg.code === result.pubno || reg.code === result.pubno.replace(/\.$/, '')
                    );

                    if (foundReg) {
                        foundRegulation = foundReg;
                        chapterKey = estimatedChapter;
                        chapterTitle = chapterData.title || '';
                    }
                }

                if (!foundRegulation) {
                    for (const [key, chapterData] of Object.entries(AppState.hospitalRegulations)) {
                        const foundReg = chapterData.regulations.find(reg =>
                            reg.code === result.pubno || reg.code === result.pubno.replace(/\.$/, '')
                        );
                        if (foundReg) {
                            foundRegulation = foundReg;
                            chapterKey = key;
                            chapterTitle = chapterData.title || '';
                            break;
                        }
                    }
                }
            }

            const extractRegulationCode = (pubno) => {
                if (!pubno) return 'N/A';
                const match = pubno.match(/^[\d.]+/);
                return match ? match[0].replace(/\.$/, '') : pubno;
            };

            const regulationData = foundRegulation || {
                name: result.name || 'N/A',
                code: extractRegulationCode(result.pubno),
                detail: {
                    documentInfo: {
                        소관부서: result.department || '소관부서 미지정',
                        파일명: result.filePath ? result.filePath.split('/').pop() : ''
                    }
                }
            };

            let finalChapter = chapterKey;
            if (!finalChapter && result.pubno) {
                const chapterNum = result.pubno.split('.')[0];
                finalChapter = `${chapterNum}장`;
            }

            return {
                regulation: regulationData,
                chapter: finalChapter || '',
                chapterTitle: chapterTitle || result.name || '',
                matchType: mapMatchType(result.matchType),
                matchContent: result.matchedContent || result.snippet || '',
                matchingAppendix: result.matching_appendix || []
            };
        });

        displaySearchResults(AppState.currentSearchResults, searchTerm, searchType);

    } catch (error) {
        console.error('API 검색 오류:', error);
        showToast(`검색 중 오류 발생: ${error.message}`, 'error');
        const resultsBody = document.getElementById('resultsBody');
        resultsBody.innerHTML = `
            <div class="empty-results">
                <i class="fas fa-exclamation-circle"></i>
                <h3>검색 실패</h3>
                <p>${error.message || '검색 중 오류가 발생했습니다.'}</p>
            </div>
        `;
    }
}

// ============================================
// 메인 검색 함수
// ============================================

/**
 * 데이터 로드 확인
 */
async function isDataLoaded() {
    return Object.keys(AppState.hospitalRegulations).length > 0;
}

/**
 * 메인 검색 함수
 */
export async function performSearch(event) {
    console.log('performSearch 함수 실행됨');

    if (event) {
        event.preventDefault();
    }

    const searchInput = document.getElementById('mainSearchInput');
    if (!searchInput) {
        console.error('검색 입력 필드를 찾을 수 없습니다.');
        return;
    }

    const searchTerm = searchInput.value.trim();
    console.log('검색어:', searchTerm);
    console.log('검색 타입:', AppState.activeSearchType);

    if (!searchTerm) {
        alert('검색어를 입력해주세요.');
        return;
    }

    AppState.currentSearchTerm = searchTerm;

    if (AppState.activeSearchType === 'regu_content' || AppState.activeSearchType === 'all' ||
        AppState.activeSearchType === 'regu_sup' || AppState.activeSearchType === 'regu_sup_content') {
        console.log('API 기반 검색 사용');
        performAPISearch(searchTerm, AppState.activeSearchType);
    } else {
        console.log('로컬 검색 사용');
        await performSearchByType(searchTerm, AppState.activeSearchType);
    }
}

/**
 * 검색 타입별 검색 수행 (로컬 검색)
 */
export async function performSearchByType(searchTerm, searchType) {
    if (!(await isDataLoaded())) {
        showToast('데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.', 'info');
        return;
    }

    let results = [];

    Object.keys(AppState.hospitalRegulations).forEach(chapter => {
        const chapterData = AppState.hospitalRegulations[chapter];

        if (!Array.isArray(chapterData.regulations)) return;

        chapterData.regulations.forEach(regulation => {
            if (!regulation || !regulation.name) return;

            let appendixArray = [];
            if (regulation.appendix) {
                if (Array.isArray(regulation.appendix)) {
                    appendixArray = regulation.appendix;
                } else if (typeof regulation.appendix === 'string') {
                    appendixArray = [regulation.appendix];
                } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
                    try {
                        appendixArray = Object.values(regulation.appendix).filter(item => item != null);
                    } catch (error) {
                        appendixArray = [];
                    }
                }
            }

            let isMatch = false;
            let matchType = '';
            let matchContent = '';
            let appendixIndex = -1;

            switch (searchType) {
                case 'all':
                    const deptValueAll = regulation.detail?.documentInfo?.소관부서;
                    if (regulation.name.includes(searchTerm) ||
                        (deptValueAll?.includes(searchTerm)) ||
                        (appendixArray.length > 0 && appendixArray.some(app => app?.includes?.(searchTerm)))) {
                        isMatch = true;
                        if (regulation.name.includes(searchTerm)) {
                            matchType = '내규명';
                            matchContent = regulation.name;
                        } else if (deptValueAll?.includes(searchTerm)) {
                            matchType = '소관부서';
                            matchContent = deptValueAll;
                        } else {
                            matchType = '부록';
                            const matchedAppendix = appendixArray.find(app => app?.includes?.(searchTerm)) || '';
                            appendixIndex = appendixArray.findIndex(app => app?.includes?.(searchTerm));
                            matchContent = appendixIndex >= 0 ? `부록 ${appendixIndex + 1}. ${matchedAppendix}` : matchedAppendix;
                        }
                    }
                    break;

                case 'regu_name':
                    if (regulation.name?.includes(searchTerm)) {
                        isMatch = true;
                        matchType = '내규명';
                        matchContent = regulation.name;
                    }
                    break;

                case 'regu_sup':
                    if (appendixArray.length > 0 && appendixArray.some(app => app?.includes?.(searchTerm))) {
                        isMatch = true;
                        matchType = '부록';
                        const matchedAppendix = appendixArray.find(app => app?.includes?.(searchTerm)) || '';
                        appendixIndex = appendixArray.findIndex(app => app?.includes?.(searchTerm));
                        matchContent = appendixIndex >= 0 ? `부록 ${appendixIndex + 1}. ${matchedAppendix}` : matchedAppendix;
                    }
                    break;

                case 'regu_dep':
                    const deptValueDep = regulation.detail?.documentInfo?.소관부서;
                    if (deptValueDep?.includes(searchTerm)) {
                        isMatch = true;
                        matchType = '소관부서';
                        matchContent = deptValueDep;
                    }
                    break;

                case 'regu_content':
                    let contentMatch = false;
                    if (regulation.detail?.articles) {
                        regulation.detail.articles.forEach(article => {
                            if (article.content?.includes(searchTerm)) {
                                contentMatch = true;
                            }
                            if (article.subsections) {
                                article.subsections.forEach(subsection => {
                                    if (subsection.items) {
                                        subsection.items.forEach(item => {
                                            if (item?.includes(searchTerm)) {
                                                contentMatch = true;
                                            }
                                        });
                                    }
                                });
                            }
                        });
                    }
                    if (contentMatch) {
                        isMatch = true;
                        matchType = '내규본문';
                        matchContent = regulation.name;
                    }
                    break;
            }

            if (isMatch) {
                results.push({
                    regulation: regulation,
                    chapter: chapter,
                    chapterTitle: chapterData.title,
                    matchType: matchType,
                    matchContent: matchContent,
                    appendixIndex: appendixIndex
                });
            }
        });
    });

    AppState.currentSearchResults = results;
    displaySearchResults(results, searchTerm, searchType);
}

// ============================================
// 검색 결과 표시 함수
// ============================================

/**
 * 검색 결과 표시
 */
export function displaySearchResults(results, searchTerm, searchType) {
    const searchResultsSection = document.getElementById('searchResultsSection');
    const resultsBody = document.getElementById('resultsBody');

    searchResultsSection.style.display = 'block';
    const searchTypeText = getSearchTypeText(searchType);

    const resultsMeta = document.querySelector('.results-meta');
    if (resultsMeta) {
        resultsMeta.innerHTML = `
            <span>총 <span id="resultCount">${results.length}</span>건</span>
            <span>검색어: "${searchTerm}" (${searchTypeText})</span>
        `;
    }

    if (results.length === 0) {
        resultsBody.innerHTML = `
            <div class="empty-results">
                <i class="fas fa-search"></i>
                <h3>검색 결과가 없습니다</h3>
                <p>"${searchTerm}"에 대한 검색 결과를 찾을 수 없습니다.</p>
            </div>
        `;
        return;
    }

    if (searchType === 'all') {
        displayIntegratedResultsByMatchType(results, resultsBody);
    } else {
        displaySimpleResults(results, resultsBody);
    }
}

/**
 * 내규 코드 기준 정렬 함수
 */
function sortByRegulationCode(a, b) {
    const codeA = a.regulation.code;
    const codeB = b.regulation.code;

    const partsA = codeA.split('.').map(Number);
    const partsB = codeB.split('.').map(Number);

    for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
        const numA = partsA[i] || 0;
        const numB = partsB[i] || 0;

        if (numA !== numB) {
            return numA - numB;
        }
    }

    return 0;
}

/**
 * 통합검색 결과 표시 (매칭 타입별 그룹)
 */
export function displayIntegratedResultsByMatchType(results, container) {
    const groupedResults = {
        '내규명': [],
        '내규본문': [],
        '부록명': [],
        '부록내용': [],
        '부록': [],
        '소관부서': []
    };

    results.forEach(result => {
        if (groupedResults[result.matchType]) {
            groupedResults[result.matchType].push(result);
        }
    });

    Object.keys(groupedResults).forEach(matchType => {
        groupedResults[matchType].sort(sortByRegulationCode);
    });

    let html = '';
    Object.keys(groupedResults).forEach(matchType => {
        const items = groupedResults[matchType];
        if (items.length > 0) {
            const initialItems = items.slice(0, 6);
            const hiddenItems = items.slice(6);

            html += `
                <div class="search-group">
                    <div class="group-header">
                        <span>${matchType === '부록' ? '부록명' : matchType}</span>
                        <span class="group-count">(${items.length}건)</span>
                    </div>
                    <div class="group-content">
                        ${initialItems.map((item, index) => {
                            const globalIndex = AppState.currentSearchResults.findIndex(r =>
                                r.regulation.code === item.regulation.code && r.chapter === item.chapter
                            );
                            const isAppendixItem = ['부록', '부록명', '부록내용'].includes(item.matchType);
                            const clickHandler = isAppendixItem && item.appendixIndex >= 0
                                ? `openAppendixPdf('${item.regulation.code}', ${item.appendixIndex}, '${item.matchContent.replace(/부록 \d+\. /, '').replace(/'/g, "\\'")}')`
                                : `openRegulationDetail(${globalIndex})`;
                            const appendixMatchInfo = item.matchingAppendix && item.matchingAppendix.length > 0
                                ? `<div class="matching-appendix-info"><i class="fas fa-paperclip"></i> 부록 내용 일치: ${item.matchingAppendix.join(', ')}</div>`
                                : '';
                            return `
                                <div class="integrated-simple-result-item" onclick="${clickHandler}">
                                    <div class="integrated-simple-result-content">
                                        <div class="integrated-simple-result-title">${item.regulation.code}. ${item.regulation.name}</div>
                                        <div class="integrated-simple-result-meta">
                                        ${item.matchContent ? `<div class="match-content-preview">${highlightText(item.matchContent, AppState.currentSearchTerm)}</div>` : ''}
                                        ${appendixMatchInfo}
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                        ${hiddenItems.length > 0 ? `
                            <div class="hidden-items" style="display: none;">
                                ${hiddenItems.map((item, index) => {
                                    const globalIndex = AppState.currentSearchResults.findIndex(r =>
                                        r.regulation.code === item.regulation.code && r.chapter === item.chapter
                                    );
                                    const isAppendixHiddenItem = ['부록', '부록명', '부록내용'].includes(item.matchType);
                                    const clickHandler = isAppendixHiddenItem && item.appendixIndex >= 0
                                        ? `openAppendixPdf('${item.regulation.code}', ${item.appendixIndex}, '${item.matchContent.replace(/부록 \d+\. /, '').replace(/'/g, "\\'")}')`
                                        : `openRegulationDetail(${globalIndex})`;
                                    const appendixMatchInfoHidden = item.matchingAppendix && item.matchingAppendix.length > 0
                                        ? `<div class="matching-appendix-info"><i class="fas fa-paperclip"></i> 부록 내용 일치: ${item.matchingAppendix.join(', ')}</div>`
                                        : '';
                                    return `
                                        <div class="integrated-simple-result-item" onclick="${clickHandler}">
                                            <div class="integrated-simple-result-content">
                                                <div class="integrated-simple-result-title">${item.regulation.code}. ${item.regulation.name}</div>
                                                <div class="integrated-simple-result-meta">
                                                ${item.matchContent ? `<div class="match-content-preview">${highlightText(item.matchContent, AppState.currentSearchTerm)}</div>` : ''}
                                                ${appendixMatchInfoHidden}
                                                </div>
                                            </div>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                            <button class="group-more-btn" onclick="toggleMoreItems(this)">
                                <i class="fas fa-chevron-down"></i>
                                <span>더 보기 (${hiddenItems.length}건)</span>
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }
    });

    container.innerHTML = html;
}

/**
 * 분류별 검색 결과 표시 (간단한 형태)
 */
export function displaySimpleResults(results, container) {
    const sortedResults = [...results].sort(sortByRegulationCode);

    const html = sortedResults.map((result, index) => {
        const globalIndex = AppState.currentSearchResults.findIndex(r =>
            r.regulation.code === result.regulation.code && r.chapter === result.chapter
        );

        let metaInfo = '';
        const isAppendixMatch = ['부록', '부록명', '부록내용'].includes(result.matchType);

        if (isAppendixMatch && result.matchContent) {
            metaInfo = `<div class="simple-result-meta">${result.matchContent}</div>`;
        } else if (result.matchType === '소관부서' && result.matchContent) {
            metaInfo = `<div class="simple-result-meta"><div class="match-content-preview">${highlightText(result.matchContent, AppState.currentSearchTerm)}</div></div>`;
        }

        const appendixMatchInfo = result.matchingAppendix && result.matchingAppendix.length > 0
            ? `<div class="matching-appendix-info"><i class="fas fa-paperclip"></i> 부록 내용 일치: ${result.matchingAppendix.join(', ')}</div>`
            : '';

        const clickHandler = isAppendixMatch && result.appendixIndex >= 0
            ? `openAppendixPdf('${result.regulation.code}', ${result.appendixIndex}, '${result.matchContent.replace(/부록 \d+\. /, '').replace(/'/g, "\\'")}')`
            : `openRegulationDetail(${globalIndex})`;

        return `
            <div class="simple-result-item" onclick="${clickHandler}">
                <div class="simple-result-content">
                    <div class="simple-result-title">${result.regulation.code}. ${result.regulation.name}</div>
                    ${metaInfo}
                    ${appendixMatchInfo}
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

/**
 * 더보기/접기 토글 함수
 */
export function toggleMoreItems(button) {
    const groupContent = button.closest('.group-content');
    const hiddenItems = groupContent.querySelector('.hidden-items');
    const icon = button.querySelector('i');
    const span = button.querySelector('span');

    if (hiddenItems.style.display === 'none') {
        hiddenItems.style.display = 'block';
        icon.className = 'fas fa-chevron-up';
        span.textContent = '접기';
    } else {
        hiddenItems.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
        const hiddenCount = hiddenItems.children.length;
        span.textContent = `더 보기 (${hiddenCount}건)`;
    }
}

// ============================================
// 검색 결과 열기
// ============================================

/**
 * 내규 상세보기 열기
 */
export function openRegulationDetail(resultIndex) {
    const result = AppState.currentSearchResults[resultIndex];
    const regulation = result.regulation;
    const chapter = result.chapter;

    const isMobile = window.innerWidth <= 768;

    if (isMobile) {
        if (typeof window.openMobileRegulationView === 'function') {
            window.openMobileRegulationView(regulation, chapter, result.chapterTitle);
        }
    } else {
        openRegulationInNewWindow(regulation, chapter, result.chapterTitle);
    }
}

/**
 * PC에서 새창으로 열기
 */
export function openRegulationInNewWindow(regulation, chapter, chapterTitle) {
    let url = `/kbregulation_page_static.html?chapter=${encodeURIComponent(chapter)}&code=${encodeURIComponent(regulation.code)}`;

    if (AppState.currentSearchTerm && AppState.currentSearchTerm.trim() !== '') {
        url += `&searchTerm=${encodeURIComponent(AppState.currentSearchTerm)}`;
    }

    const newWindow = window.open(url, '_blank', 'width=1000,height=800,scrollbars=yes,resizable=yes');

    if (!newWindow) {
        alert('팝업이 차단되었습니다. 브라우저 설정에서 팝업을 허용해주세요.');
    }
}

/**
 * 검색 초기화
 */
export function initializeSearchEvents() {
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.removeAttribute('onsubmit');
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            performSearch(e);
        });
    }

    const searchBtn = document.querySelector('.search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', function(e) {
            e.preventDefault();
            performSearch(e);
        });
    }

    const searchInput = document.getElementById('mainSearchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                performSearch(e);
            }
        });
    }

    document.querySelectorAll('.search-tab').forEach(tab => {
        tab.addEventListener('click', async function() {
            document.querySelectorAll('.search-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            AppState.activeSearchType = this.dataset.type;

            if (AppState.currentSearchTerm) {
                if (AppState.activeSearchType === 'regu_content' || AppState.activeSearchType === 'all') {
                    performAPISearch(AppState.currentSearchTerm, AppState.activeSearchType);
                } else {
                    await performSearchByType(AppState.currentSearchTerm, AppState.activeSearchType);
                }
            }
        });
    });
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.performSearch = performSearch;
    window.performSearchByType = performSearchByType;
    window.performAPISearch = performAPISearch;
    window.performIntegratedAPISearch = performIntegratedAPISearch;
    window.displaySearchResults = displaySearchResults;
    window.displayIntegratedResultsByMatchType = displayIntegratedResultsByMatchType;
    window.displaySimpleResults = displaySimpleResults;
    window.toggleMoreItems = toggleMoreItems;
    window.openRegulationDetail = openRegulationDetail;
    window.openRegulationInNewWindow = openRegulationInNewWindow;
    window.initializeSearchEvents = initializeSearchEvents;
}
