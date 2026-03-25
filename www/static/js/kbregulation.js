let hospitalRegulations = {};
let isLoading = false; // 데이터 로딩 중 플래그

let currentRegulation = null;
let currentChapter = null;

let regulationHistory = []; // 내규 탐색 히스토리
let isNavigatingBack = false; // 뒤로가기 중인지 구분하는 플래그

// localStorage 사용 가능 여부 플래그 (Android 대응)
let isStorageAvailable = false;

// 즐겨찾기
let favoriteRegulations = []; // DOMContentLoaded에서 localStorage 로드
let filteredFavorites = []; // 검색 필터링용

// 검색 관련 전역 변수
let currentSearchResults = [];
let currentSearchTerm = '';
let activeSearchType = 'all';

// 레이아웃 설정 관련 전역 변수
let currentLayoutMode = 2; // 기본값: 표준 모드

// 사이드바 표시/숨김 헬퍼
function setSidebarDisplay(value) {
    const el = document.getElementById('sidebarWrapper') || document.getElementById('sidebar');
    if (el) el.style.display = value;
}


// 개정이력 관련 전역 변수
let allRevisionData = []; // 전체 개정이력 데이터
let filteredRevisionData = []; // 필터링/정렬된 데이터
let currentRevisionSort = 'chapter-asc'; // 현재 정렬 방식

// 공지사항 관련 전역 변수
let currentNoticesData = []; // 전체 공지사항 데이터
let filteredNoticesData = []; // 필터링된 공지사항 데이터
let currentNoticesPage = 1; // 현재 페이지
let noticesPerPage = 10; // 페이지당 공지사항 수

// 내규 제·개정 절차 관련 전역 변수
let currentProceduresData = []; // 전체 절차 데이터
let filteredProceduresData = []; // 필터링된 절차 데이터
let currentProceduresPage = 1; // 현재 페이지
let proceduresPerPage = 10; // 페이지당 절차 수

// 사용방법 가이드 관련 전역 변수
let currentUsageData = []; // 전체 사용방법 데이터
let filteredUsageData = []; // 필터링된 사용방법 데이터
let currentUsagePage = 1; // 현재 페이지
let usagePerPage = 10; // 페이지당 사용방법 수

// 헬퍼 함수: 중첩된 hospitalRegulations 구조에서 챕터 데이터 찾기
// JSON 구조: { "KB규정": { "1편 정관·이사회": { title, regulations }, ... } }
function getChapterData(chapter) {
    // hospitalRegulations의 모든 카테고리를 순회하여 chapter 찾기
    for (const category of Object.values(hospitalRegulations)) {
        if (category && typeof category === 'object' && category[chapter]) {
            return category[chapter];
        }
    }
    return undefined;
}

// 헬퍼 함수: pubno(예: "6-8")로 규정 찾기 (2중 중첩 구조 순회)
function findRegulationByPubno(pubno) {
    if (!pubno || !hospitalRegulations) return null;
    const targetCode = pubno.replace(/\.$/, '');
    for (const category of Object.values(hospitalRegulations)) {
        if (!category || typeof category !== 'object') continue;
        for (const [chapterKey, chapterData] of Object.entries(category)) {
            if (!chapterData || !Array.isArray(chapterData.regulations)) continue;
            const foundReg = chapterData.regulations.find(reg =>
                reg.code === targetCode || reg.code === pubno
            );
            if (foundReg) {
                return { regulation: foundReg, chapterKey, chapterTitle: chapterData.title || '' };
            }
        }
    }
    return null;
}

// FAQ 관련 전역 변수
let currentFAQData = []; // 전체 FAQ 데이터
let filteredFAQData = []; // 필터링된 FAQ 데이터
let currentFAQPage = 1; // 현재 페이지
let faqPerPage = 10; // 페이지당 FAQ 수

// ================================

// 메인페이지로 새로고침 함수
function refreshToMainPage() {
    // 페이지 완전 새로고침
    window.location.reload();
}

// localStorage 안전 저장 헬퍼 함수 (Android 대응)
function safeSetStorage(key, value) {
    if (isStorageAvailable) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (error) {
            console.warn(`[localStorage] 저장 실패 (${key}):`, error.message);
            return false;
        }
    }
    return false;
}

// localStorage 안전 읽기 헬퍼 함수 (Android 대응)
function safeGetStorage(key) {
    if (isStorageAvailable) {
        try {
            return localStorage.getItem(key);
        } catch (error) {
            console.warn(`[localStorage] 읽기 실패 (${key}):`, error.message);
            return null;
        }
    }
    return null;
}

// localStorage 초기화 함수 (Android 대응)
function initializeLocalStorage() {
    try {
        // localStorage 사용 가능 여부 테스트
        localStorage.setItem('_test', 'test');
        localStorage.removeItem('_test');
        isStorageAvailable = true;

        console.log('[localStorage] 사용 가능 - 데이터 로드 시작');

        // 즐겨찾기 데이터 로드
        try {
            favoriteRegulations = JSON.parse(localStorage.getItem('favoriteRegulations') || '[]');
            console.log(`[localStorage] 즐겨찾기 로드: ${favoriteRegulations.length}개`);
        } catch (e) {
            console.warn('[localStorage] 즐겨찾기 로드 실패:', e);
            favoriteRegulations = [];
        }

        // 최근 본 내규 데이터 로드
        try {
            recentRegulations = JSON.parse(localStorage.getItem('recentRegulations') || '[]');
            console.log(`[localStorage] 최근 본 내규 로드: ${recentRegulations.length}개`);
        } catch (e) {
            console.warn('[localStorage] 최근 본 내규 로드 실패:', e);
            recentRegulations = [];
        }

        // 레이아웃 설정 로드
        try {
            const savedLayout = localStorage.getItem('layoutMode');
            if (savedLayout) {
                currentLayoutMode = parseInt(savedLayout);
                console.log(`[localStorage] 레이아웃 설정 로드: ${currentLayoutMode}`);
            }
        } catch (e) {
            console.warn('[localStorage] 레이아웃 설정 로드 실패:', e);
        }

    } catch (error) {
        // localStorage 사용 불가 (Android 등)
        isStorageAvailable = false;
        console.warn('[Android 모드] localStorage 사용 불가 - 세션 데이터만 사용');
        console.warn('에러 상세:', error.message);

        // 기본값 유지
        favoriteRegulations = [];
        recentRegulations = [];
        currentLayoutMode = 2;

        // 사용자에게 안내 (선택사항)
        // showToast('일부 설정이 브라우저 종료 시 초기화됩니다', 'info');
    }
}

async function loadHospitalRegulations() {
    if (isLoading) return; // 이미 로딩 중이면 중복 호출 방지
    isLoading = true;

    try {
        // summary 파일 로드 - 캐시 방지를 위한 타임스탬프 추가
        const timestamp = new Date().getTime();
        const response = await fetch(`/static/file/summary_kbregulation.json?ts=${timestamp}`);
        if (!response.ok) {
            throw new Error('Summary JSON 파일을 불러올 수 없습니다.');
        }
        const data = await response.json();
        hospitalRegulations = data;

        // JSON 로드 완료 후 초기화 함수들 실행
        initializeApplication();

    } catch (error) {
        console.error('Summary JSON 파일 로드 실패:', error);
        // 에러 발생 시 사용자에게 알림
        showToast('데이터 로드에 실패했습니다. 페이지를 새로고침해주세요.', 'error');
    } finally {
        isLoading = false;
    }
}

// 개별 규정 상세 데이터 로드 함수
async function loadRegulationDetail(fileName) {
    try {
        console.log('Loading regulation detail from:', fileName);
        // 캐시 방지를 위한 타임스탬프 추가
        const timestamp = new Date().getTime();
        const response = await fetch(`/static/file/${fileName}?ts=${timestamp}`);
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error(`규정 파일을 불러올 수 없습니다: ${fileName}`);
        }
        const data = await response.json();
        // docx2json 파싱 결과(sections) → 사용자화면 키(조문내용)로 매핑
        if (!data.조문내용 && data.sections) {
            data.조문내용 = data.sections;
        }
        console.log('Loaded data:', data);
        console.log('조문내용 count:', data.조문내용 ? data.조문내용.length : 0);
        return data;
    } catch (error) {
        console.error('규정 파일 로드 실패:', error);
        console.error('Failed file name:', fileName);
        showToast('규정 상세 정보를 불러올 수 없습니다.', 'error');
        return null;
    }
}

function initializeApplication() {
    // 트리 메뉴 생성
    generateTreeMenu();
   
    // 기타 초기화 작업이 필요한 경우 여기에 추가
    console.log('애플리케이션 초기화 완료');
}

// ================================

// 검색 탭 클릭 이벤트 처리
// DOM이 완전히 로드된 후 실행
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM 로드 완료 - 검색 기능 초기화');

    // 홈 탭 active 스타일 제거 (초기 로드 시 yellow 배경 방지)
    updateNavigation('홈');

    // localStorage 초기화 시도 (Android 대응)
    initializeLocalStorage();

    // JSON 파일 로드 시작
    loadHospitalRegulations();

    // 즐겨찾기 데이터 정리 및 마이그레이션
    migrateLegacyFavorites(); // 기존 문자열 형태 데이터 변환
    cleanupFavoriteRegulations(); // 잘못된 구조 데이터 제거
 
    // 페이지 로드 시 즐겨찾기 목록 초기화
    updateFavoritesList();
    updateRecentRegulationsList();

    // 사이드바 접기/펼치기 핸들 동적 삽입 + 상태 복원
    initSidebarToggle();

    // 검색 폼 이벤트 리스너 (기존 onsubmit 대신 addEventListener 사용)
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        // 기존 onsubmit 속성 제거
        searchForm.removeAttribute('onsubmit');
        
        // 새로운 이벤트 리스너 추가
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('검색 폼 제출됨');
            performSearch(e);
        });
    }
    
    // 검색 버튼 직접 이벤트 리스너 추가
    const searchBtn = document.querySelector('.search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('검색 버튼 클릭됨');
            performSearch(e);
        });
    }
    
    // Enter 키 이벤트 추가
    const searchInput = document.getElementById('mainSearchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                console.log('Enter 키 눌림');
                performSearch(e);
            }
        });
    }
    
    // 검색 탭 이벤트 리스너 추가
    document.querySelectorAll('.search-tab').forEach(tab => {
        tab.addEventListener('click', async function() {
            console.log('검색 탭 클릭:', this.dataset.type);

            // 모든 탭에서 active 클래스 제거
            document.querySelectorAll('.search-tab').forEach(t => t.classList.remove('active'));
            // 클릭한 탭에 active 클래스 추가
            this.classList.add('active');
            // 현재 검색 타입 업데이트
            activeSearchType = this.dataset.type;

            // 이미 검색한 결과가 있다면 재검색
            if (currentSearchTerm) {
                console.log('기존 검색어로 재검색:', currentSearchTerm);
                // API 검색이 필요한 타입인지 확인 (통합검색, 본문검색)
                if (activeSearchType === 'regu_content' || activeSearchType === 'all') {
                    performAPISearch(currentSearchTerm, activeSearchType);
                } else {
                    await performSearchByType(currentSearchTerm, activeSearchType);
                }
            }
        });
    });

    // 새창에서 보낸 메시지 처리
    window.addEventListener('message', function(event) {
        // 보안을 위해 origin 체크 (필요에 따라)
        // if (event.origin !== window.location.origin) return;
        
        if (event.data && event.data.type === 'FAVORITES_UPDATED') {
            // 새창에서 즐겨찾기가 업데이트되었을 때
            favoriteRegulations = event.data.favoriteRegulations;
            safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
            updateFavoritesList();
            
            // 현재 즐겨찾기 페이지가 열려있다면 업데이트
            if (document.getElementById('contentBody').style.display !== 'none' && 
                document.querySelector('.favorites-page')) {
                displayFavoritesContent();
            }
            
            // 현재 보고 있는 내규의 즐겨찾기 상태 업데이트
            if (currentRegulation && currentChapter) {
                const favoriteBtn = document.querySelector('.regulation-actions .action-btn[data-tooltip="즐겨찾기"]') ||
                                   document.querySelector('.page-actions .action-btn[data-tooltip="즐겨찾기"]');
                if (favoriteBtn) {
                    if (isFavorite(currentRegulation, currentChapter)) {
                        favoriteBtn.classList.add('active');
                    } else {
                        favoriteBtn.classList.remove('active');
                    }
                }
            }
        }
    });
    
    console.log('검색 기능 초기화 완료');

    // 저장된 레이아웃 설정 불러오기
    loadLayoutSettings();
});

// search_type 매핑 (로컬 타입 → API 타입)
function mapSearchTypeToAPI(localType) {
    const typeMap = {
        'regu_content': 'content',  // 본문 검색
        'regu_name': 'title',       // 제목 검색
        'regu_sup': 'name',         // 부록명 검색 (부록 API의 name 타입)
        'regu_sup_content': 'content',  // 부록내용 검색 (부록 API의 content 타입)
        'regu_dep': 'department',   // 소관부서 검색
        'all': 'all'                // 통합 검색
    };
    return typeMap[localType] || localType;
}

// 로컬 검색 헬퍼 함수 (결과만 반환)
function performLocalSearchByType(searchTerm, searchType) {
    let results = [];

    // 2중 중첩 구조 순회: { "KB규정": { "1편 ...": { regulations: [...] }, ... } }
    for (const category of Object.values(hospitalRegulations)) {
        if (!category || typeof category !== 'object') continue;
        Object.keys(category).forEach(chapter => {
            const chapterData = category[chapter];

            if (!chapterData || !Array.isArray(chapterData.regulations)) return;

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
            let appendixIndex = -1; // 부록 인덱스 저장용

            if (searchType === 'regu_name') {
                // 내규명에서만 검색
                if (regulation.name && regulation.name.includes(searchTerm)) {
                    isMatch = true;
                    matchType = '내규명';
                    matchContent = regulation.name;
                }
            } else if (searchType === 'regu_sup') {
                // 부록에서만 검색
                if (appendixArray.length > 0 && appendixArray.some(app => app && typeof app === 'string' && app.includes(searchTerm))) {
                    isMatch = true;
                    matchType = '부록';
                    const matchedAppendix = appendixArray.find(app => app && typeof app === 'string' && app.includes(searchTerm)) || '';
                    appendixIndex = appendixArray.findIndex(app => app && typeof app === 'string' && app.includes(searchTerm));
                    matchContent = appendixIndex >= 0 ? `부록 ${appendixIndex + 1}. ${matchedAppendix}` : matchedAppendix;
                }
            } else if (searchType === 'regu_dep') {
                // 소관부서에서만 검색
                if (regulation.detail &&
                    regulation.detail.documentInfo &&
                    regulation.detail.documentInfo.소관부서 &&
                    regulation.detail.documentInfo.소관부서.includes(searchTerm)) {
                    isMatch = true;
                    matchType = '소관부서';
                    matchContent = regulation.detail.documentInfo.소관부서;
                }
            }

            if (isMatch) {
                results.push({
                    regulation: regulation,
                    chapter: chapter,
                    chapterTitle: chapterData.title,
                    matchType: matchType,
                    matchContent: matchContent,
                    appendixIndex: appendixIndex // 부록 인덱스 추가
                });
            }
        });
        });
    }

    return results;
}

// 통합 API 검색 함수 (모든 타입에 대해 검색)
async function performIntegratedAPISearch(searchTerm) {
    console.log('통합 검색 시작: API + 로컬 검색 혼합');

    const searchResultsSection = document.getElementById('searchResultsSection');
    const resultsBody = document.getElementById('resultsBody');

    try {
        // API 검색 타입 (내규명, 내규본문)
        const apiSearchTypes = [
            { local: 'regu_name', api: 'title', korean: '내규명', endpoint: '/api/search/es' },
            { local: 'regu_content', api: 'content', korean: '내규본문', endpoint: '/api/search/es' },
            { local: 'regu_sup_content', api: 'content', korean: '부록내용', endpoint: '/api/search/es/appendix' }
        ];

        // API 검색 실행
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

        // 모든 검색 완료 대기
        const allResults = await Promise.all(searchPromises);

        // 결과 통합
        let combinedResults = [];
        allResults.forEach(({ type, results, isAppendix }) => {
            results.forEach(result => {
                // 부록 내용 검색 결과는 별도 처리
                if (isAppendix) {
                    // 부록 API 응답: 규정표기명, 규정명, wzappendixno, wzappendixname
                    const pubno = result.규정표기명 || '';
                    const appendixNo = result.wzappendixno || '1';
                    const appendixIndex = parseInt(appendixNo) - 1;
                    const appendixName = result.wzappendixname || '';
                    const metaContent = `부록 ${appendixNo}. ${appendixName}`;

                    // 규정 코드 추출 (KB 형식: "6-8" 하이픈 기반)
                    const code = pubno.replace(/\.$/, '');

                    // 편 추정
                    const chapterNum = code.split('-')[0];
                    const finalChapter = `${chapterNum}편`;

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

                // 일반 규정 검색 결과 처리
                // pubno를 기반으로 장 정보 및 regulation 찾기
                let chapterKey = '';
                let chapterTitle = '';
                let foundRegulation = null;

                if (result.pubno && hospitalRegulations) {
                    const found = findRegulationByPubno(result.pubno);
                    if (found) {
                        foundRegulation = found.regulation;
                        chapterKey = found.chapterKey;
                        chapterTitle = found.chapterTitle;
                    }
                }

                // 규정 코드 추출 (예: "6-8" → "6-8")
                const extractRegulationCode = (pubno) => {
                    if (!pubno) return 'N/A';
                    // KB 형식: 숫자와 하이픈으로 구성 (예: "6-8", "11-16")
                    const match = pubno.match(/^[\d\-]+/);
                    return match ? match[0].replace(/[\-.]$/, '') : pubno;
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

                // chapter가 없으면 pubno에서 추정 (예: "6-8" → "6편 ...")
                let finalChapter = chapterKey;
                if (!finalChapter && result.pubno) {
                    const chapterNum = result.pubno.split('-')[0];
                    finalChapter = `${chapterNum}편`;
                }

                combinedResults.push({
                    regulation: regulationData,
                    chapter: finalChapter || '',
                    chapterTitle: chapterTitle || result.name || '',
                    matchType: type,
                    matchContent: result.matchedContent || result.snippet
                        || (result.matching_articles && result.matching_articles.length > 0
                            ? result.matching_articles.slice(0, 3).map(a => {
                                const text = (a.display_text || a.article_content || '').replace(/<[^>]*>/g, '');
                                return text;
                            }).join(' | ')
                            : ''),
                    matchingAppendix: result.matching_appendix || [],
                    matchingArticleCount: result.matching_article_count || 0
                });
            });
        });

        // 로컬 검색 (부록, 소관부서만 - 내규명과 내규본문은 API에서 처리)
        const appendixResults = performLocalSearchByType(searchTerm, 'regu_sup');
        console.log(`부록 검색 결과 (로컬): ${appendixResults.length}건`);
        combinedResults = combinedResults.concat(appendixResults);

        const departmentResults = performLocalSearchByType(searchTerm, 'regu_dep');
        console.log(`소관부서 검색 결과 (로컬): ${departmentResults.length}건`);
        combinedResults = combinedResults.concat(departmentResults);

        // 중복 제거 (같은 내규코드 + 장 + 매칭타입)
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
        console.log(`통합 검색 결과 (중복 제거 후): ${combinedResults.length}건`);

        currentSearchResults = combinedResults;

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

        // 결과 표시
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

// API 기반 검색 함수 (FastAPI 검색 엔진 사용)
async function performAPISearch(searchTerm, searchType) {
    console.log(`API 검색 시작: 검색어="${searchTerm}", 로컬타입="${searchType}"`);

    try {
        // 로딩 표시
        const searchResultsSection = document.getElementById('searchResultsSection');
        const resultsBody = document.getElementById('resultsBody');

        // 정보 탭 숨기고 검색 결과 표시
        const infoTabsSection = document.querySelector('.info-tabs-section');
        if (infoTabsSection) infoTabsSection.style.display = 'none';
        searchResultsSection.style.display = 'block';
        resultsBody.innerHTML = '<div class="search-loading"><i class="fas fa-spinner fa-spin"></i> 검색 중...</div>';

        // 통합검색인 경우 모든 타입에 대해 검색
        if (searchType === 'all') {
            await performIntegratedAPISearch(searchTerm);
            return;
        }

        // search_type을 API 타입으로 매핑
        const apiSearchType = mapSearchTypeToAPI(searchType);
        console.log(`search_type 매핑: "${searchType}" → "${apiSearchType}"`);

        // 부록 검색인 경우 별도 엔드포인트 사용
        let apiUrl;
        if (searchType === 'regu_sup' || searchType === 'regu_sup_content') {
            apiUrl = `/api/search/es/appendix?q=${encodeURIComponent(searchTerm)}&search_type=${apiSearchType}&limit=100&page=1`;
            console.log(`부록 API 요청: ${apiUrl}`);
        } else {
            apiUrl = `/api/search/es?q=${encodeURIComponent(searchTerm)}&search_type=${apiSearchType}&limit=100&page=1`;
            console.log(`API 요청: ${apiUrl}`);
        }

        const response = await fetch(apiUrl);

        console.log(`API 응답 상태: ${response.status}`);

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`HTTP 오류: ${response.status}`, errorText);
            throw new Error(`검색 실패: ${response.status} ${errorText}`);
        }

        const data = await response.json();
        console.log('API 검색 결과:', data);

        if (!data.success) {
            const errorMsg = data.error || data.detail || '알 수 없는 오류';
            console.error('API 오류:', errorMsg);
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

        // 결과 확인
        if (!data.results || data.results.length === 0) {
            console.log('검색 결과 없음');
            resultsBody.innerHTML = `
                <div class="empty-results">
                    <i class="fas fa-search"></i>
                    <h3>검색 결과가 없습니다</h3>
                    <p>"${searchTerm}"에 대한 검색 결과를 찾을 수 없습니다.</p>
                </div>
            `;
            return;
        }

        console.log(`검색 결과: ${data.results.length}건 (총 ${data.total}건)`);

        // matchType 매핑 함수 (API 영어 → 한글)
        const mapMatchType = (apiMatchType) => {
            // 부록 검색인 경우 별도 매핑
            if (searchType === 'regu_sup' || searchType === 'regu_sup_content') {
                const appendixMatchTypeMap = {
                    'name': '부록명',
                    'content': '부록내용',
                    'all': '부록'
                };
                return appendixMatchTypeMap[apiMatchType] || '부록내용';
            }

            // 일반 규정 검색
            const matchTypeMap = {
                'title': '내규명',
                'content': '내규본문',
                'appendix': '부록',
                'department': '소관부서'
            };
            return matchTypeMap[apiMatchType] || '내규본문';
        };

        // 결과를 로컬 형식으로 변환
        currentSearchResults = data.results.map((result, index) => {
            console.log(`결과 ${index + 1}:`, result);

            // 부록 검색 결과인 경우 별도 처리
            if (searchType === 'regu_sup' || searchType === 'regu_sup_content') {
                // wzappendixno는 "1", "2" 등의 문자열, appendixIndex는 0부터 시작
                const appendixNo = result.wzappendixno || '1';
                const appendixIndex = parseInt(appendixNo) - 1;

                // 메타 정보: "부록 1. 부록명" 형식
                const metaContent = `부록 ${appendixNo}. ${result.wzappendixname || ''}`;

                return {
                    regulation: {
                        name: result.규정명 || 'N/A',  // 상위 규정명 (예: "의과대학생 임상실습 교육 및 감독")
                        code: result.규정표기명 || 'N/A',  // 규정 코드 (예: "13.1.1")
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
                    matchContent: metaContent,  // "부록 1. 부록명" 형식
                    appendixIndex: appendixIndex  // openAppendixPdf 함수용 인덱스
                };
            }

            // 일반 규정/조문 검색 결과 처리
            // pubno를 기반으로 장 정보 및 regulation 찾기
            let chapterKey = '';
            let chapterTitle = '';
            let foundRegulation = null;

            if (result.pubno && hospitalRegulations) {
                const found = findRegulationByPubno(result.pubno);
                if (found) {
                    foundRegulation = found.regulation;
                    chapterKey = found.chapterKey;
                    chapterTitle = found.chapterTitle;
                }
            }

            // 규정 코드 추출 (예: "6-8" → "6-8")
            const extractRegulationCode = (pubno) => {
                if (!pubno) return 'N/A';
                // KB 형식: 숫자와 하이픈으로 구성 (예: "6-8", "11-16")
                const match = pubno.match(/^[\d\-]+/);
                return match ? match[0].replace(/[\-.]$/, '') : pubno;
            };

            // foundRegulation이 있으면 그것을 사용, 없으면 API 데이터로 생성
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

            // chapter가 없으면 pubno에서 추정 (예: "6-8" → "6편 ...")
            let finalChapter = chapterKey;
            if (!finalChapter && result.pubno) {
                const chapterNum = result.pubno.split('-')[0];
                finalChapter = `${chapterNum}편`;
            }

            return {
                regulation: regulationData,
                chapter: finalChapter || '',
                chapterTitle: chapterTitle || result.name || '',  // 장 제목 (예: "환자진료")
                matchType: mapMatchType(result.matchType),
                matchContent: result.matchedContent || result.snippet
                    || (result.matching_articles && result.matching_articles.length > 0
                        ? result.matching_articles.slice(0, 3).map(a => {
                            // HTML 태그 제거 후 텍스트만 추출
                            const text = (a.display_text || a.article_content || '').replace(/<[^>]*>/g, '');
                            return text;
                        }).join(' | ')
                        : ''),
                matchingAppendix: result.matching_appendix || [],  // 부록 내용 매칭 정보
                matchingArticleCount: result.matching_article_count || 0
            };
        });

        console.log(`변환된 결과: ${currentSearchResults.length}개`);

        // 결과 표시
        displaySearchResults(currentSearchResults, searchTerm, searchType);

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

// 검색 결과 초기화
function clearSearchResults() {
    // 검색어 초기화
    const searchInput = document.getElementById('mainSearchInput');
    if (searchInput) searchInput.value = '';

    // 검색 상태 초기화
    currentSearchTerm = '';
    currentSearchResults = [];

    // 검색 결과 영역 숨기기
    const searchResultsSection = document.getElementById('searchResultsSection');
    if (searchResultsSection) searchResultsSection.style.display = 'none';

    // 정보 탭 섹션 복원
    const infoTabsSection = document.querySelector('.info-tabs-section');
    if (infoTabsSection) infoTabsSection.style.display = '';

    // X 버튼 숨기기
    const clearBtn = document.getElementById('searchClearBtn');
    if (clearBtn) clearBtn.style.display = 'none';

    // 검색어 입력란 포커스
    if (searchInput) searchInput.focus();
}

// 메인 검색 함수
async function performSearch(event) {
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
    console.log('검색 타입:', activeSearchType);

    if (!searchTerm) {
        alert('검색어를 입력해주세요.');
        return;
    }

    currentSearchTerm = searchTerm;

    // X 버튼 표시
    const clearBtn = document.getElementById('searchClearBtn');
    if (clearBtn) clearBtn.style.display = 'flex';

    // API 검색을 사용할 타입 확인
    // API 사용: 본문 검색, 통합 검색, 부록 검색
    // 로컬: 제목, 부서 검색
    if (activeSearchType === 'regu_content' || activeSearchType === 'all' ||
        activeSearchType === 'regu_sup' || activeSearchType === 'regu_sup_content') {
        // 본문, 통합, 부록 검색은 API 사용 (더 강력한 검색)
        console.log('API 기반 검색 사용');
        performAPISearch(searchTerm, activeSearchType);
    } else {
        // 다른 검색은 로컬 JSON 검색 사용
        console.log('로컬 검색 사용');
        await performSearchByType(searchTerm, activeSearchType);
    }
}


// 검색 타입별 검색 수행 (로컬 검색)
async function performSearchByType(searchTerm, searchType) {
    if (!(await isDataLoaded())) {
        showToast('데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.', 'info');
        return;
    }

    let results = [];
    
    // hospitalRegulations 데이터에서 검색 (2중 중첩 구조)
    for (const category of Object.values(hospitalRegulations)) {
        if (!category || typeof category !== 'object') continue;
        Object.keys(category).forEach(chapter => {
        const chapterData = category[chapter];

        // ✅ regulations 배열 확인
        if (!chapterData || !Array.isArray(chapterData.regulations)) {
            return;
        }

        chapterData.regulations.forEach(regulation => {
            // ✅ regulation 객체 확인
            if (!regulation || !regulation.name) {
                console.warn(`검색 중 오류: 유효하지 않은 regulation`, regulation);
                return;
            }
            
            // ✅ appendix 안전 확인 및 정규화
            let appendixArray = [];
            if (regulation.appendix) {
                if (Array.isArray(regulation.appendix)) {
                    appendixArray = regulation.appendix;
                } else if (typeof regulation.appendix === 'string') {
                    appendixArray = [regulation.appendix];
                    console.warn(`Chapter ${chapter}, regulation ${regulation.code}.: appendix가 문자열입니다. 배열로 변환합니다.`);
                } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
                    try {
                        appendixArray = Object.values(regulation.appendix).filter(item => item != null);
                        console.warn(`Chapter ${chapter}, regulation ${regulation.code}.: appendix가 객체입니다. 배열로 변환합니다.`);
                    } catch (error) {
                        console.error(`Chapter ${chapter}, regulation ${regulation.code}.: appendix 변환 실패`, error);
                        appendixArray = [];
                    }
                } else {
                    console.warn(`Chapter ${chapter}, regulation ${regulation.code}.: appendix가 예상치 못한 타입입니다:`, typeof regulation.appendix);
                    appendixArray = [];
                }
            }
            
            let isMatch = false;
            let matchType = '';
            let matchContent = '';
            let appendixIndex = -1; // 부록 인덱스 저장용

            switch (searchType) {
                case 'all':
                    // ✅ 통합검색: 내규명, 소관부서, 부록에서 모두 검색 (안전한 방식)
                    if (regulation.name.includes(searchTerm) ||
                        (regulation.detail &&
                         regulation.detail.documentInfo &&
                         regulation.detail.documentInfo.소관부서 &&
                         regulation.detail.documentInfo.소관부서.includes(searchTerm)) ||
                        (appendixArray.length > 0 && appendixArray.some(app => app && typeof app === 'string' && app.includes(searchTerm)))) {
                        isMatch = true;
                        if (regulation.name.includes(searchTerm)) {
                            matchType = '내규명';
                            matchContent = regulation.name;
                        } else if (regulation.detail &&
                                   regulation.detail.documentInfo &&
                                   regulation.detail.documentInfo.소관부서 &&
                                   regulation.detail.documentInfo.소관부서.includes(searchTerm)) {
                            matchType = '소관부서';
                            matchContent = regulation.detail.documentInfo.소관부서;
                        } else {
                            matchType = '부록';
                            const matchedAppendix = appendixArray.find(app => app && typeof app === 'string' && app.includes(searchTerm)) || '';
                            appendixIndex = appendixArray.findIndex(app => app && typeof app === 'string' && app.includes(searchTerm));
                            matchContent = appendixIndex >= 0 ? `부록 ${appendixIndex + 1}. ${matchedAppendix}` : matchedAppendix;
                        }
                    }
                    break;

                case 'regu_name':
                    // ✅ 내규명에서만 검색
                    if (regulation.name && regulation.name.includes(searchTerm)) {
                        isMatch = true;
                        matchType = '내규명';
                        matchContent = regulation.name;
                    }
                    break;

                case 'regu_sup':
                    // ✅ 부록에서만 검색 (안전한 방식)
                    if (appendixArray.length > 0 && appendixArray.some(app => app && typeof app === 'string' && app.includes(searchTerm))) {
                        isMatch = true;
                        matchType = '부록';
                        const matchedAppendix = appendixArray.find(app => app && typeof app === 'string' && app.includes(searchTerm)) || '';
                        appendixIndex = appendixArray.findIndex(app => app && typeof app === 'string' && app.includes(searchTerm));
                        matchContent = appendixIndex >= 0 ? `부록 ${appendixIndex + 1}. ${matchedAppendix}` : matchedAppendix;
                    }
                    break;
                    
                case 'regu_dep':
                    // ✅ 소관부서에서만 검색 (안전한 방식)
                    if (regulation.detail &&
                        regulation.detail.documentInfo &&
                        regulation.detail.documentInfo.소관부서 &&
                        regulation.detail.documentInfo.소관부서.includes(searchTerm)) {
                        isMatch = true;
                        matchType = '소관부서';
                        matchContent = regulation.detail.documentInfo.소관부서;
                    }
                    break;
                    
                case 'regu_content':
                    // ✅ 내규 본문에서 검색 (새로 추가)
                    let contentMatch = false;
                    if (regulation.detail && regulation.detail.articles) {
                        regulation.detail.articles.forEach(article => {
                            if (article.content && article.content.includes(searchTerm)) {
                                contentMatch = true;
                            }
                            if (article.subsections) {
                                article.subsections.forEach(subsection => {
                                    if (subsection.items) {
                                        subsection.items.forEach(item => {
                                            if (item && item.includes(searchTerm)) {
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
                    appendixIndex: appendixIndex // 부록 인덱스 추가
                });
            }
        });
        });
    }

    currentSearchResults = results;
    displaySearchResults(results, searchTerm, searchType);

}

// 검색 결과 표시
function displaySearchResults(results, searchTerm, searchType) {
    const searchResultsSection = document.getElementById('searchResultsSection');
    const resultsBody = document.getElementById('resultsBody');
    // 정보 탭 숨기고 검색 결과 섹션 표시
    const infoTabsSection = document.querySelector('.info-tabs-section');
    if (infoTabsSection) infoTabsSection.style.display = 'none';
    searchResultsSection.style.display = 'block';
    // 검색 타입에 따른 추가 정보
    const searchTypeText = getSearchTypeText(searchType);
    // results-meta 요소가 존재하는지 확인하고 업데이트
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
    // 검색 타입에 따라 다른 표시 방식
    if (searchType === 'all') {
        // 통합검색: 매칭 타입별로 그룹화하여 표시
        displayIntegratedResultsByMatchType(results, resultsBody);
    } else {
        // 분류별 검색: 간단한 형태로 표시
        displaySimpleResults(results, resultsBody);
    }
}

// 통합검색 결과 표시 (매칭 타입별 그룹) - 6건 제한 + 더보기
function displayIntegratedResultsByMatchType(results, container) {
    // 매칭 타입별로 그룹화
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

    // 내규 코드 기준 정렬 함수
    const sortByRegulationCode = (a, b) => {
        const codeA = a.regulation.code;
        const codeB = b.regulation.code;

        // 코드를 하이픈(-)으로 분리하여 숫자 배열로 변환 (KB 형식: "6-8")
        const partsA = codeA.split('-').map(Number);
        const partsB = codeB.split('-').map(Number);

        // 각 부분을 순서대로 비교
        for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
            const numA = partsA[i] || 0;
            const numB = partsB[i] || 0;

            if (numA !== numB) {
                return numA - numB;
            }
        }

        return 0;
    };

    // 각 그룹별로 정렬
    Object.keys(groupedResults).forEach(matchType => {
        groupedResults[matchType].sort(sortByRegulationCode);
    });

    // HTML 생성 - 모든 그룹을 한번에 표시 (처음엔 6건씩만)
    let html = '';
    Object.keys(groupedResults).forEach(matchType => {
        const items = groupedResults[matchType];
        if (items.length > 0) {
            // 처음에 보여줄 6건
            const initialItems = items.slice(0, 6);
            // 숨겨진 나머지 항목들
            const hiddenItems = items.slice(6);
            
            html += `
                <div class="search-group">
                    <div class="group-header">
                        <span>${matchType === '부록' ? '부록명' : matchType}</span>
                        <span class="group-count">(${items.length}건)</span>
                    </div>
                    <div class="group-content">
                        ${initialItems.map((item, index) => {
                            const globalIndex = currentSearchResults.findIndex(r =>
                                r.regulation.code === item.regulation.code && r.chapter === item.chapter
                            );
                            // 부록인 경우 PDF 열기, 아니면 내규 상세 열기
                            const isAppendixItem = ['부록', '부록명', '부록내용'].includes(item.matchType);
                            const clickHandler = isAppendixItem && item.appendixIndex >= 0
                                ? `openAppendixPdf('${item.regulation.code}', ${item.appendixIndex}, '${item.matchContent.replace(/부록 \d+\. /, '').replace(/'/g, "\\'")}')`
                                : `openRegulationDetail(${globalIndex})`;
                            // 부록 내용 매칭 정보 생성
                            const appendixMatchInfo = item.matchingAppendix && item.matchingAppendix.length > 0
                                ? `<div class="matching-appendix-info"><i class="fas fa-paperclip"></i> 부록 내용 일치: ${item.matchingAppendix.join(', ')}</div>`
                                : '';
                            return `
                                <div class="integrated-simple-result-item" onclick="${clickHandler}">
                                    <div class="integrated-simple-result-content">
                                        <div class="integrated-simple-result-title">${item.regulation.code}. ${item.regulation.name}</div>
                                        <div class="integrated-simple-result-meta">
                                        ${item.matchContent ? `<div class="match-content-preview">${highlightText(item.matchContent, currentSearchTerm)}</div>` : ''}
                                        ${appendixMatchInfo}
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                        ${hiddenItems.length > 0 ? `
                            <div class="hidden-items" style="display: none;">
                                ${hiddenItems.map((item, index) => {
                                    const globalIndex = currentSearchResults.findIndex(r =>
                                        r.regulation.code === item.regulation.code && r.chapter === item.chapter
                                    );
                                    // 부록인 경우 PDF 열기, 아니면 내규 상세 열기
                                    const isAppendixHiddenItem = ['부록', '부록명', '부록내용'].includes(item.matchType);
                                    const clickHandler = isAppendixHiddenItem && item.appendixIndex >= 0
                                        ? `openAppendixPdf('${item.regulation.code}', ${item.appendixIndex}, '${item.matchContent.replace(/부록 \d+\. /, '').replace(/'/g, "\\'")}')`
                                        : `openRegulationDetail(${globalIndex})`;
                                    // 부록 내용 매칭 정보 생성
                                    const appendixMatchInfoHidden = item.matchingAppendix && item.matchingAppendix.length > 0
                                        ? `<div class="matching-appendix-info"><i class="fas fa-paperclip"></i> 부록 내용 일치: ${item.matchingAppendix.join(', ')}</div>`
                                        : '';
                                    return `
                                        <div class="integrated-simple-result-item" onclick="${clickHandler}">
                                            <div class="integrated-simple-result-content">
                                                <div class="integrated-simple-result-title">${item.regulation.code}. ${item.regulation.name}</div>
                                                <div class="integrated-simple-result-meta">
                                                ${item.matchContent ? `<div class="match-content-preview">${highlightText(item.matchContent, currentSearchTerm)}</div>` : ''}
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

// 더보기/접기 토글 함수
function toggleMoreItems(button) {
    const groupContent = button.closest('.group-content');
    const hiddenItems = groupContent.querySelector('.hidden-items');
    const icon = button.querySelector('i');
    const span = button.querySelector('span');
    if (hiddenItems.style.display === 'none') {
        // 더보기
        hiddenItems.style.display = 'block';
        icon.className = 'fas fa-chevron-up';
        span.textContent = '접기';
    } else {
        // 접기
        hiddenItems.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
        const hiddenCount = hiddenItems.children.length;
        span.textContent = `더 보기 (${hiddenCount}건)`;
    }
}

// 소관부서 추출 헬퍼 함수
function getDepartment(regulation) {
    if (regulation.detail && regulation.detail.documentInfo && regulation.detail.documentInfo['소관부서']) {
        return regulation.detail.documentInfo['소관부서'];
    }
    return '소관부서 미지정';
}

// 분류별 검색 결과 표시 (간단한 형태)
function displaySimpleResults(results, container) {
    // 내규 코드 기준 정렬
    const sortedResults = [...results].sort((a, b) => {
        const codeA = a.regulation.code;
        const codeB = b.regulation.code;

        // 코드를 하이픈(-)으로 분리하여 숫자 배열로 변환 (KB 형식: "6-8")
        const partsA = codeA.split('-').map(Number);
        const partsB = codeB.split('-').map(Number);

        // 각 부분을 순서대로 비교
        for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
            const numA = partsA[i] || 0;
            const numB = partsB[i] || 0;

            if (numA !== numB) {
                return numA - numB;
            }
        }

        return 0;
    });

    const html = sortedResults.map((result, index) => {
        // currentSearchResults에서의 전체 인덱스 찾기
        const globalIndex = currentSearchResults.findIndex(r =>
            r.regulation.code === result.regulation.code && r.chapter === result.chapter
        );
        // 부록 검색일 때만 matchContent 표시 (하이라이트 없이)
        // 소관부서 검색일 때도 matchContent 표시 (하이라이트 포함)
        let metaInfo = '';
        // 부록 관련 매치 타입 처리
        const isAppendixMatch = ['부록', '부록명', '부록내용'].includes(result.matchType);

        if (isAppendixMatch && result.matchContent) {
            metaInfo = `<div class="simple-result-meta">${result.matchContent}</div>`;
        } else if (result.matchType === '소관부서' && result.matchContent) {
            metaInfo = `<div class="simple-result-meta"><div class="match-content-preview">${highlightText(result.matchContent, currentSearchTerm)}</div></div>`;
        }

        // 부록 내용 매칭 정보 생성
        const appendixMatchInfo = result.matchingAppendix && result.matchingAppendix.length > 0
            ? `<div class="matching-appendix-info"><i class="fas fa-paperclip"></i> 부록 내용 일치: ${result.matchingAppendix.join(', ')}</div>`
            : '';

        // 부록인 경우 PDF 열기, 아니면 내규 상세 열기
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

// 검색 타입 텍스트 반환
function getSearchTypeText(searchType) {
    const searchTypeMap = {
        'all': '통합검색',
        'regu_name': '내규명',
        'regu_content': '내규본문',
        'regu_sup': '부록명',
        'regu_sup_content': '부록내용',
        'regu_dep': '소관부서'
    };
    return searchTypeMap[searchType] || '통합검색';
}

// 내규 요약 텍스트 생성
function getRegulationSummary(regulation) {
    // 기존 데이터 구조 확인
    if (regulation.detail && regulation.detail.articles && regulation.detail.articles.length > 0) {
        const firstArticle = regulation.detail.articles[0];
        return firstArticle.content || `${regulation.name}에 관한 내규입니다.`;
    }
    // 요약 파일이므로 상세 내용은 없고 기본 메시지만 반환
    return `${regulation.name}에 관한 내규입니다.`;
}

// 내규 상세보기 열기
function openRegulationDetail(resultIndex) {
    const result = currentSearchResults[resultIndex];
    const regulation = result.regulation;
    const chapter = result.chapter;
    
    // 모바일인지 확인
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile) {
        openMobileRegulationView(regulation, chapter, result.chapterTitle);
    } else {
        // 팝업으로 보여주는 기능 숨김.
        //openRegulationModal(regulation, chapter, result.chapterTitle);

        openRegulationInNewWindow(regulation, chapter, result.chapterTitle);
    }
}

// PC에서 새창으로 열기
function openRegulationInNewWindow(regulation, chapter, chapterTitle) {
    // 정적 HTML 파일 사용
    let url = `/kbregulation_page_static.html?chapter=${encodeURIComponent(chapter)}&code=${encodeURIComponent(regulation.code)}`;

    // 검색어가 있으면 URL에 추가
    if (currentSearchTerm && currentSearchTerm.trim() !== '') {
        url += `&searchTerm=${encodeURIComponent(currentSearchTerm)}`;
    }

    const newWindow = window.open(url, '_blank', 'width=1000,height=800,scrollbars=yes,resizable=yes');
    
    if (!newWindow) {
        alert('팝업이 차단되었습니다. 브라우저 설정에서 팝업을 허용해주세요.');
    }

    // 새창이 닫힐 때 즐겨찾기 상태 동기화
    const checkClosed = setInterval(() => {
        if (newWindow.closed) {
            clearInterval(checkClosed);
            // 새창이 닫혔을 때 localStorage에서 최신 즐겨찾기 정보 다시 로드
            if (isStorageAvailable) {
                try {
                    const updatedFavorites = JSON.parse(localStorage.getItem('favoriteRegulations') || '[]');
                    if (JSON.stringify(favoriteRegulations) !== JSON.stringify(updatedFavorites)) {
                        favoriteRegulations = updatedFavorites;
                        updateFavoritesList();
                    }

                    // 현재 즐겨찾기 페이지가 열려있다면 업데이트
                    if (document.getElementById('contentBody').style.display !== 'none' &&
                        document.querySelector('.favorites-page')) {
                        displayFavoritesContent();
                    }

                    // 현재 보고 있는 내규의 즐겨찾기 상태 업데이트
                    if (currentRegulation && currentChapter) {
                        const favoriteBtn = document.querySelector('.regulation-actions .action-btn[data-tooltip="즐겨찾기"]') ||
                                           document.querySelector('.page-actions .action-btn[data-tooltip="즐겨찾기"]');
                        if (favoriteBtn) {
                            if (isFavorite(currentRegulation, currentChapter)) {
                                favoriteBtn.classList.add('active');
                            } else {
                                favoriteBtn.classList.remove('active');
                            }
                        }
                    }
                } catch (error) {
                    console.warn('[localStorage] 즐겨찾기 동기화 실패:', error.message);
                }
            }
        }
    }, 1000);

}

// 데스크톱 모달 열기
async function openRegulationModal(regulation, chapter, chapterTitle) {
    const modal = document.getElementById('regulationModal');
    const title = document.getElementById('modalRegulationTitle');
    const body = document.getElementById('modalRegulationBody');

    title.textContent = `${regulation.code}. ${regulation.name}`;

    // 로딩 표시
    body.innerHTML = '<div style="text-align: center; padding: 20px;">내규 내용을 불러오는 중...</div>';
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // 배경 스크롤 방지

    // 내규 내용 생성 (기존 showRegulationDetail 함수의 로직 재사용)
    const regulationContent = await generateRegulationContent(regulation, chapter, chapterTitle);
    body.innerHTML = regulationContent;
}

// 모바일 전체화면 뷰 열기
async function openMobileRegulationView(regulation, chapter, chapterTitle) {
    const view = document.getElementById('mobileRegulationView');
    const title = document.getElementById('mobileRegulationTitle');
    const body = document.getElementById('mobileRegulationBody');

    title.textContent = `${regulation.code}. ${regulation.name}`;

    // 로딩 표시
    body.innerHTML = '<div style="text-align: center; padding: 20px;">내규 내용을 불러오는 중...</div>';
    view.style.display = 'flex';

    // 내규 내용 생성
    const regulationContent = await generateRegulationContent(regulation, chapter, chapterTitle);
    body.innerHTML = regulationContent;
}

// 내규 내용 HTML 생성 (비동기 함수로 변경)
async function generateRegulationContent(regulation, chapter, chapterTitle) {
    let contentHtml = '';
    let appendixHtml = '';

    // 파일명이 있으면 상세 데이터 로드
    console.log('Checking for file:', regulation);
    if (regulation.detail && regulation.detail.documentInfo && regulation.detail.documentInfo.파일명) {
        console.log('Loading detail file:', regulation.detail.documentInfo.파일명);
        const detailData = await loadRegulationDetail(regulation.detail.documentInfo.파일명);
        if (detailData) {
            console.log('Detail data loaded successfully:', detailData);
            console.log('Document info in loaded data:', detailData.document_info);
            console.log('조문내용 in loaded data:', detailData.조문내용);
            // 기존 regulation 객체에 상세 데이터 병합
            regulation.detailData = detailData;
        } else {
            console.error('Failed to load detail data');
        }
    } else {
        console.log('No file name found in regulation:', {
            hasDetail: !!regulation.detail,
            hasDocumentInfo: !!(regulation.detail && regulation.detail.documentInfo),
            hasFileName: !!(regulation.detail && regulation.detail.documentInfo && regulation.detail.documentInfo.파일명)
        });
    }
    
    // 부록 HTML 생성 - 제거 (조문에서 직접 처리)
    // appendixHtml은 빈 문자열로 유지
    
    // 내규 상세 내용 생성
    console.log('Checking for detailData:', {
        hasDetailData: !!regulation.detailData,
        has조문내용: !!(regulation.detailData && regulation.detailData.조문내용),
        조문내용Length: regulation.detailData?.조문내용?.length
    });

    if (regulation.detailData && regulation.detailData.조문내용) {
        // 새로운 데이터 구조로 조문 내용 렌더링
        const articles = regulation.detailData.조문내용;
        console.log('Processing articles:', articles.length);

        if (articles && Array.isArray(articles) && articles.length > 0) {
            // 문서 기본 글꼴 적용
            const docFont = regulation.detailData.문서정보?.기본글꼴;
            const fontStyle = docFont ? ` style="font-family: '${docFont}', sans-serif;"` : '';
            contentHtml += `<div class="regulation-articles"${fontStyle}>`;
            let previousLevel = 0; // 이전 레벨 추적
            let inByulpyoSection = false; // 별표/별첨/서식 섹션 내부 추적
            articles.forEach((article, index) => {
                if (!article) return;

                // 별표/별첨/서식 섹션 헤더 감지
                const plainContent = (article.내용 || '').replace(/<[^>]+>/g, '').trim();
                const isByulpyoHeader = !article.번호 && /^『(별표|별첨|서식)\s*제?\s*\d+\s*호/.test(plainContent);

                // 별표 헤더가 나오면 별표 섹션 시작
                if (isByulpyoHeader) {
                    inByulpyoSection = true;

                    // 별표 번호와 유형 추출
                    const headerMatch = plainContent.match(/^『(별표|별첨|서식)\s*제?\s*(\d+)\s*호/);
                    if (headerMatch) {
                        const byulpyoType = headerMatch[1];
                        const byulpyoNum = parseInt(headerMatch[2]);
                        const typeName = `${byulpyoType} 제${byulpyoNum}호`;
                        const escapedName = typeName.replace(/'/g, "\\'");

                        // 별표 제목 추출 (『별표 제N호』 뒤의 텍스트)
                        const titleMatch = plainContent.match(/『[^』]+』\s*(.*)/);
                        const title = titleMatch ? titleMatch[1].trim() : '';

                        contentHtml += `<div style="color: #1976d2; font-weight: 600; margin: 20px 0 5px 0; cursor: pointer; text-decoration: underline;"
                                         onclick="openByulpyoPdf('${regulation.code}', ${byulpyoNum}, '${escapedName}', event)">
                                         『${typeName}』 ${title} <span style="font-size: 0.85em; color: #666; font-weight: normal;">(PDF 보기)</span>
                                       </div>`;
                    }
                    previousLevel = article.레벨;
                    return;
                }

                // 별표 섹션 내부의 하위 항목은 건너뛰기 (다음 별표 헤더 또는 새로운 '제N조' 가 나올 때까지)
                if (inByulpyoSection) {
                    // 새로운 별표 헤더가 아니고, 일반 조문(제N조)도 아니면 건너뛰기
                    const hasArticleNo = article.번호 && /^제\d+조/.test(article.번호);
                    if (!isByulpyoHeader && !hasArticleNo) {
                        return; // 별표 테이블 데이터 건너뛰기
                    }
                    // 새로운 조문이 시작되면 별표 섹션 종료
                    inByulpyoSection = false;
                }

                // 레벨 0인 항목: "제X장" 패턴이면 가운데 정렬로 표시, 아니면 건너뜀
                if (article.레벨 === 0) {
                    if (article.번호 && /^제\d+(장|절)$/.test(article.번호)) {
                        const chapterTitle = article.번호 + ' ' + (article.내용 || '');
                        contentHtml += `<div class="chapter-title">${chapterTitle}</div>`;
                    }
                    return;
                }

                // 제N절 패턴: 별도 section-title 스타일 적용
                if (article.레벨 === 1 && !article.번호 && /^제\d+절/.test(plainContent)) {
                    contentHtml += `<div class="section-title">${article.내용}</div>`;
                    previousLevel = article.레벨;
                    return;
                }

                // 레벨에 따른 스타일 적용 (원본 문서 양식에 맞춤 - 검정색 기본)
                let style = '';
                let paddingLeft = 0;

                // 레벨 3에서 레벨 2로 변경될 때 추가 여백
                let additionalMarginTop = '';
                if (previousLevel >= 3 && article.레벨 === 2) {
                    additionalMarginTop = 'margin-top: 15px;';
                }

                // JSON의 정렬 속성 적용
                let alignmentStyle = '';
                if (article.정렬 === 'center') {
                    alignmentStyle = 'text-align: center;';
                } else if (article.정렬 === 'right') {
                    alignmentStyle = 'text-align: right;';
                }
                if (article.글꼴크기) {
                    alignmentStyle += ` font-size: ${article.글꼴크기}pt;`;
                }

                switch(article.레벨) {
                    case 1: // 제1조, 제2조 등 - <b> 태그로 원본 bold 범위 적용
                        style = 'color: #000; margin: 15px 0 5px 0;';
                        paddingLeft = 0;
                        break;
                    case 2: // ①, ② 등 - 원본: Normal, 11pt, 검정
                        style = `color: #000; margin: 4px 0; ${additionalMarginTop}`;
                        paddingLeft = 20;
                        break;
                    case 3: // 1., 2. 등
                        style = 'color: #000; margin: 2px 0;';
                        paddingLeft = 60;
                        break;
                    case 4: // 가., 나. 등
                        style = 'color: #000; margin: 2px 0;';
                        paddingLeft = 80;
                        break;
                    case 5: // 1), 2) 등
                        style = 'color: #000; margin: 5px 0;';
                        paddingLeft = 105;
                        break;
                    case 6: // 레벨 6 항목
                        style = 'color: #000; margin: 4px 0;';
                        paddingLeft = 125;
                        break;
                    case 7: // 레벨 7 항목
                        style = 'color: #000; margin: 4px 0;';
                        paddingLeft = 140;
                        break;
                    case 8: // 레벨 8 항목
                        style = 'color: #000; margin: 4px 0;';
                        paddingLeft = 160;
                        break;
                    default:
                        style = 'color: #000; margin: 5px 0;';
                        paddingLeft = 160;
                }

                // 번호와 내용 표시 (레벨 1은 번호도 bold)
                let displayText;
                if (article.번호 && article.레벨 === 1) {
                    displayText = `<b>${article.번호}</b> ${article.내용}`;
                } else {
                    displayText = article.번호 ? `${article.번호} ${article.내용}` : article.내용;
                }

                // 별표 참조를 클릭 가능한 링크로 변환
                displayText = linkifyByulpyo(displayText, articles, false, regulation.code);

                // 검색어가 있으면 하이라이트 적용
                if (currentSearchTerm && currentSearchTerm.trim() !== '') {
                    displayText = highlightText(displayText, currentSearchTerm);
                }

                if (article.레벨 === 2) {
                    contentHtml += `<div style="${style} ${alignmentStyle} padding-left: 35px; text-indent: -15px;">${displayText}</div>`;
                } else if (article.레벨 === 3) {
                    contentHtml += `<div style="${style} ${alignmentStyle} padding-left: 60px; text-indent: -20px;">${displayText}</div>`;
                } else if (article.레벨 === 4) {
                    contentHtml += `<div style="${style} ${alignmentStyle} padding-left: 80px; text-indent: -20px;">${displayText}</div>`;
                } else if (article.레벨 === 5) {
                    contentHtml += `<div style="${style} ${alignmentStyle} padding-left: 105px; text-indent: -20px;">${displayText}</div>`;
                } else if (article.레벨 === 6) {
                    contentHtml += `<div style="${style} ${alignmentStyle} padding-left: 125px; text-indent: -20px;">${displayText}</div>`;
                } else if (article.레벨 === 7) {
                    contentHtml += `<div style="${style} ${alignmentStyle} padding-left: 140px; text-indent: -20px;">${displayText}</div>`;
                } else if (article.레벨 === 8) {
                    contentHtml += `<div style="${style} ${alignmentStyle} padding-left: 160px; text-indent: -20px;">${displayText}</div>`;
                } else {
                    contentHtml += `<div style="${style} ${alignmentStyle} padding-left: ${paddingLeft}px;">${displayText}</div>`;
                }

                // 관련 이미지가 있으면 표시
                if (article.관련이미지 && article.관련이미지.length > 0) {
                    article.관련이미지.forEach(img => {
                        contentHtml += `<div style="margin: 10px 0; padding-left: ${paddingLeft + 20}px;">
                            <img src="${img.file_path}" style="max-width: 100%; height: auto; border: 1px solid #e0e0e0; border-radius: 4px;">
                        </div>`;
                    });
                }

                // 현재 레벨을 이전 레벨로 저장
                previousLevel = article.레벨;
            });
            contentHtml += '</div>'; // regulation-articles 닫기
            console.log('Articles rendered successfully');
        } else {
            console.warn('No articles found for regulation:', regulation.code);
            contentHtml = `
                <div style="color: #000; font-weight: bold; margin: 20px 0 10px 0;">내규 내용</div>
                <div style="margin: 10px 0; padding-left: 20px;">이 내규의 상세 내용을 불러오는 중 오류가 발생했습니다.</div>
            `;
        }
    } else if (regulation.detail) {
        // 기존 데이터 구조 처리 (호환성 유지)
        const detail = regulation.detail;

        // articles 배열 존재 여부 확인
        if (detail.articles && Array.isArray(detail.articles) && detail.articles.length > 0) {
            detail.articles.forEach(article => {
                // article 객체 존재 여부 확인
                if (!article) {
                    console.warn('Empty article found in regulation:', regulation.code);
                    return;
                }

                // article.title 존재 여부 확인
                if (article.title) {
                    contentHtml += `<div style="color: #000; font-weight: bold; margin: 20px 0 10px 0; padding: 10px 0;">${article.title}</div>`;
                }

                // article.content 존재 여부 확인
                if (article.content) {
                    contentHtml += `<div style="margin: 10px 0; padding-left: 20px;">${article.content}</div>`;
                }

                // article.subsections 존재 여부 및 배열 확인
                if (article.subsections && Array.isArray(article.subsections)) {
                    article.subsections.forEach(subsection => {
                        // subsection 객체 존재 여부 확인
                        if (!subsection) {
                            console.warn('Empty subsection found in regulation:', regulation.code);
                            return;
                        }

                        // subsection.title 존재 여부 확인
                        if (subsection.title) {
                            contentHtml += `<div style="margin: 10px 0; padding-left: 20px;"><strong>${subsection.title}</strong></div>`;
                        }

                        // subsection.items 존재 여부 및 배열 확인
                        if (subsection.items && Array.isArray(subsection.items)) {
                            subsection.items.forEach(item => {
                                // item 존재 여부 확인
                                if (item) {
                                    contentHtml += `<div style="margin: 8px 0; padding-left: 50px; color: #555;">${item}</div>`;
                                }
                            });
                        }
                    });
                }
            });
        } else {
            // articles가 없거나 비어있는 경우 기본 메시지
            console.warn('No articles found for regulation:', regulation.code);
            contentHtml = `
                <div style="color: #000; font-weight: bold; margin: 20px 0 10px 0;">내규 내용</div>
                <div style="margin: 10px 0; padding-left: 20px;">이 내규의 상세 내용은 관련 부서에서 별도로 관리됩니다.</div>
            `;
        }
    } else {
        // detailData도 없고 기존 detail.articles도 없는 경우
        console.log('No regulation content found, showing default message');
        contentHtml = `
            <div style="color: #000; font-weight: bold; margin: 20px 0 10px 0;">내규 내용</div>
            <div style="margin: 10px 0; padding-left: 20px;">내규 상세 정보를 불러오는 중입니다...</div>
            <div style="margin: 10px 0; padding-left: 20px; color: #666;">
                만약 내용이 계속 표시되지 않는다면 담당 부서에 문의하시기 바랍니다.
            </div>
        `;
    }

    // 문서정보 메타데이터 HTML 생성
    let modalMetaHTML = '';
    const isMobile = window.innerWidth <= 768;

    // 새로운 데이터 구조(detailData) 또는 기존 구조(detail) 모두 지원
    // JSON 파일의 document_info 필드를 체크
    const docInfo = regulation.detailData?.document_info ||
                    regulation.detailData?.문서정보 ||
                    regulation.detail?.documentInfo;

    // 디버깅을 위한 로그 추가
    console.log('Regulation object:', regulation);
    console.log('DocInfo:', docInfo);
    console.log('Has detailData:', !!regulation.detailData);
    console.log('detailData.document_info:', regulation.detailData?.document_info);
    console.log('Has detail:', !!regulation.detail);

    if (!docInfo) {
        console.error('DocInfo is null or undefined!');
        console.log('Trying to find document info in:', {
            'detailData.document_info': regulation.detailData?.document_info,
            'detailData.문서정보': regulation.detailData?.문서정보,
            'detail.documentInfo': regulation.detail?.documentInfo
        });
    }

    if (docInfo) {
        if (isMobile) {
            // 모바일용 카드 형태 HTML
            modalMetaHTML = `
                <div class="regulation-meta-container">
                    <div class="mobile-meta-cards">
                        <!-- 기본 정보 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">제정일</div>
                                    <div class="mobile-meta-value ${docInfo.제정일 ? '' : 'empty'}" style="text-align:center;">
                                        ${docInfo.제정일 || '-'}
                                    </div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">최근<br>개정일</div>
                                    <div class="mobile-meta-value ${docInfo.최종개정일 ? '' : 'empty'}" style="text-align:center;">
                                        ${docInfo.최종개정일 || '-'}
                                    </div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">최근<br>시행일</div>
                                    <div class="mobile-meta-value ${docInfo.최종검토일 ? '' : 'empty'}" style="text-align:center;">
                                        ${docInfo.최종검토일 || '-'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 부서/담당자 정보 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">소관<br>부서</div>
                                    <div class="mobile-meta-value ${docInfo.소관부서 ? '' : 'empty'}">
                                        ${docInfo.소관부서 || '-'}
                                    </div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">제·개정<br>담당자</div>
                                    <div class="mobile-meta-value ${docInfo.제개정담당자 ? '' : 'empty'}">
                                        ${docInfo.제개정담당자 || '-'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 제·개정 사유 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item" style="height: auto;">
                                    <div class="mobile-meta-label">제·개정<br>사유</div>
                                    <div class="mobile-meta-value ${docInfo.관련기준 ? '' : 'empty'}">
                                        ${docInfo.관련기준 ?
                                            (Array.isArray(docInfo.관련기준) ?
                                                docInfo.관련기준.join('<br>') :
                                                docInfo.관련기준) :
                                            '-'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // 기존 PC용 테이블 형태 HTML (기존 코드 그대로)
            modalMetaHTML = `
                <div class="regulation-meta-container">
                    <!-- 기본 정보 테이블 -->
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">제정일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.제정일 || '-'}</td>
                            <th class="header-cell" style="border-left:1px solid #000">최근개정일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.최종개정일 || '-'}</td>
                            <th class="header-cell" style="border-left:1px solid #000">최근시행일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.최종검토일 || '-'}</td>
                        </tr>
                        <tr>
                            <th class="header-cell">소관부서</th>
                            <td class="content-cell" colspan="2">${docInfo.소관부서 || '-'}</td>
                            <th class="header-cell" style="border-left:1px solid #000">제·개정 담당자</th>
                            <td class="content-cell" colspan="2" style="text-align:center;">${docInfo.제개정담당자 || '-'}</td>
                        </tr>
                    </table>

                    <!-- 제·개정 사유 테이블 -->
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">제·개정 사유</th>
                            <td class="content-cell long-content">
                                ${docInfo.관련기준 ?
                                    (Array.isArray(docInfo.관련기준) ?
                                        docInfo.관련기준.join('<br>') :
                                        docInfo.관련기준) :
                                    '-'}
                            </td>
                        </tr>
                    </table>
                </div>
            `;
        }

        return `
            <div style="background: white; border-radius: 8px; padding: 10px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                <div class="page-actions" style="display:flex; justify-content:end; margin-bottom : 0.5rem">
                    <button style="display:none;" class="action-btn " onclick="toggleFavorite(currentRegulation, currentChapter)" data-tooltip="즐겨찾기">
                        <i class="fas fa-star"></i>
                    </button>
                </div>
                ${modalMetaHTML}
                <div>
                    ${contentHtml}
                </div>
            </div>
        `;
    } else {
        // 기본 템플릿
        contentHtml = `
            <div style="margin: 10px 0; padding-left: 20px;">내규데이터 업로드 중.</div>
        `;
    }

    return `
        <div style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <div style="border-bottom: 1px solid #e0e0e0; padding-bottom: 15px; margin-bottom: 20px;">
                <div style="display: flex; gap: 15px; font-size: 12px; color: #666; flex-wrap: wrap;">
                    <span>부록: ${regulation.appendix ? regulation.appendix.length : 0}건</span>
                    ${regulation.detail ? `
                        <span>제정일: ${regulation.detail.documentInfo.제정일}</span>
                        <span>최종개정일: ${regulation.detail.documentInfo.최종개정일}</span>
                        <span>소관부서: ${regulation.detail.documentInfo.소관부서}</span>
                    ` : `
                        <span>제정일: 정보 없음</span>
                        <span>소관부서: 정보 없음</span>
                    `}
                </div>
            </div>
            <div>
                ${contentHtml}
            </div>
        </div>
    `;
}

// 모달 닫기
function closeRegulationModal() {
    const modal = document.getElementById('regulationModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto'; // 배경 스크롤 복원
}

function goBackToPreviousRegulation() {
    console.log('뒤로가기 버튼 클릭. 현재 히스토리 길이:', regulationHistory.length);
    
    if (regulationHistory.length >= 2) {
        // 현재 내규를 히스토리에서 제거
        regulationHistory.pop();
        
        // 이전 내규 가져오기
        const previousItem = regulationHistory[regulationHistory.length - 1];
        
        if (previousItem) {
            // 뒤로가기 플래그 설정 (히스토리에 다시 추가되지 않도록)
            isNavigatingBack = true;
            
            // 기존 showRegulationDetail 함수 재사용
            showRegulationDetail(previousItem.regulation, previousItem.chapter);
            
            console.log('이전 내규로 이동 완료:', previousItem.regulation.code);
        }
    }
}

async function goBackFromRegulation() {
    await showCategoryListPage();
}

// 모바일 뷰 닫기
function closeMobileRegulationView() {
    const view = document.getElementById('mobileRegulationView');
    view.style.display = 'none';
}

// 윈도우 리사이즈 시 모달/모바일 뷰 처리
window.addEventListener('resize', function() {
    // 기존 모달/모바일 뷰 처리 코드
    const modal = document.getElementById('regulationModal');
    const mobileView = document.getElementById('mobileRegulationView');
    
    if (window.innerWidth <= 768) {
        if (modal && modal.style.display === 'flex') {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    } else {
        if (mobileView && mobileView.style.display === 'flex') {
            mobileView.style.display = 'none';
        }
    }

    // 내규 상세보기가 열려있다면 다시 렌더링
    if (currentRegulation && currentChapter) {
        const contentBody = document.getElementById('contentBody');
        if (contentBody && contentBody.style.display !== 'none') {
            showRegulationDetail(currentRegulation, currentChapter);
        }
    }

    // (셋팅부분) 모바일에서는 항상 모드 2로 강제 설정
    if (window.innerWidth <= 768 && currentLayoutMode === 1) {
        setLayoutMode(2, false); // 저장하지 않고 임시로만 변경
    }
});

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    showCategoryTree();
});

// 트리 메뉴 생성
function generateTreeMenu() {
    // hospitalRegulations가 비어있다면 아직 로드되지 않았으므로 리턴
    if (!hospitalRegulations || Object.keys(hospitalRegulations).length === 0) {
        console.log('hospitalRegulations가 아직 로드되지 않음');
        return;
    }

    const treeMenu = document.getElementById('treeMenu');
    treeMenu.innerHTML = '';

    // JSON 구조가 { "KB규정": { "1. 정관·이사회": {...}, ... } } 형태이므로
    // 최상위 카테고리(KB규정 등)를 먼저 순회
    Object.keys(hospitalRegulations).forEach(category => {
        const categoryData = hospitalRegulations[category];

        // 카테고리 내의 각 챕터를 순회
        Object.keys(categoryData).forEach(chapter => {
            const chapterData = categoryData[chapter];

            // regulations 속성이 없으면 건너뛰기
            if (!chapterData || !chapterData.regulations) {
                console.warn(`챕터 ${chapter}에 regulations 속성이 없습니다.`);
                return;
            }

            const treeItem = document.createElement('div');
            treeItem.className = 'tree-item';

            const treeHeader = document.createElement('div');
            treeHeader.className = 'tree-header';
            treeHeader.innerHTML = `
                <span>${chapter}</span>
                <i class="fas fa-chevron-right tree-icon"></i>
            `;
            treeHeader.onclick = () => toggleTreeItem(treeHeader, chapter);

            const treeChildren = document.createElement('div');
            treeChildren.className = 'tree-children';

            chapterData.regulations.forEach(regulation => {
            const childNode = document.createElement('div');
            childNode.className = 'tree-child';
            if (regulation.appendix && regulation.appendix.length > 0) {
                childNode.classList.add('has-appendix');
            }
            childNode.textContent = `${regulation.code}. ${regulation.name}`;
            childNode.onclick = async (event) => {
                event.stopPropagation();
                await selectRegulation(regulation, chapter, childNode);
            };
            
            treeChildren.appendChild(childNode);
            
            // 부록이 있는 경우 서브 레벨 추가
            if (regulation.appendix && regulation.appendix.length > 0) {
                const subChildren = document.createElement('div');
                subChildren.className = 'tree-sub-children';
               
                // 안전한 부록 처리
                let safeAppendixArray = [];
                
                if (Array.isArray(regulation.appendix)) {
                    safeAppendixArray = regulation.appendix;
                } else if (typeof regulation.appendix === 'string') {
                    safeAppendixArray = [regulation.appendix];
                } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
                    try {
                        safeAppendixArray = Object.values(regulation.appendix).filter(item => item != null);
                    } catch (error) {
                        console.error(`부록 변환 실패 - ${regulation.code}:`, error);
                        safeAppendixArray = [];
                    }
                }
                
                // 부록 아이템 생성
                safeAppendixArray.forEach((appendixItem, index) => {
                    // 유효성 검사
                    if (!appendixItem || typeof appendixItem !== 'string') {
                        console.warn(`유효하지 않은 부록 아이템 - ${regulation.code}[${index}]:`, appendixItem);
                        return;
                    }
                    
                    const subChild = document.createElement('div');
                    subChild.className = 'tree-sub-child';

                    // 텍스트에서 중복된 번호가 제거를　위해　cleanAppendixItem　사용
                    const cleanAppendixItem = appendixItem.replace(/^\d+\.\s*/, '');
                    // 별표/별첨/서식 패턴이면 그대로 표시, 아니면 기존 부록 N 형식
                    if (/^(별표|별첨|서식)\s*제\d+호/.test(cleanAppendixItem)) {
                        subChild.textContent = cleanAppendixItem;
                    } else {
                        subChild.textContent = `부록 ${index + 1}. ${cleanAppendixItem}`;
                    }
                    
                    // 핵심 수정: PDF 열기로 변경
                    subChild.onclick = (event) => {
                        event.stopPropagation();
                        openAppendixPdf(regulation.code, index, cleanAppendixItem);
                    };
                    
                    subChildren.appendChild(subChild);
                });

                // has-appendix 클래스가 있으면 DOM 구조를 위해 항상 추가
                treeChildren.appendChild(subChildren);
            }

            });

            treeItem.appendChild(treeHeader);
            treeItem.appendChild(treeChildren);
            treeMenu.appendChild(treeItem);
        });
    });
}

async function isDataLoaded() {
    let check = hospitalRegulations && Object.keys(hospitalRegulations).length > 0;
    if (!check && !isLoading) {
        await loadHospitalRegulations();
        check = hospitalRegulations && Object.keys(hospitalRegulations).length > 0;
    }
    return check;
}

// 트리 메뉴 토글
function toggleTreeItem(header, chapter) {
    const children = header.nextElementSibling;
    const isOpen = children.classList.contains('open');
    const treeMenu = document.getElementById('treeMenu');

    if (!isOpen) {
        // 클릭한 아이템 열기
        children.classList.add('open');
        header.classList.add('active');

        // 클릭한 장으로 스크롤 이동 (다른 장은 그대로 유지)
        setTimeout(() => {
            if (treeMenu && header) {
                const treeItem = header.parentElement;
                const targetScrollPosition = treeItem.offsetTop;

                treeMenu.scrollTo({
                    top: targetScrollPosition - 20,  // 20px 여백
                    behavior: 'smooth'
                });
            }
        }, 50);  // DOM 업데이트 후 실행
    } else {
        // 닫기
        children.classList.remove('open');
        header.classList.remove('active');
    }
}

// 내규 선택
async function selectRegulation(regulation, chapter, element) {
    // 비교 모드에서는 우측 패널에 로드
    if (isComparisonMode) {
        loadComparisonRight(regulation, chapter);
        return;
    }

    // 모바일에서는 sidebar 자동으로 닫기
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        closeSidebar();
    }

    // 현재 요소가 이미 active인지 확인
    const isCurrentlyActive = element.classList.contains('active');
    
    // 부록 관련 요소들
    const hasAppendix = regulation.appendix && regulation.appendix.length > 0;
    const subChildren = hasAppendix ? element.nextElementSibling : null;
    const isCurrentlyOpen = subChildren && subChildren.classList.contains('open');

    // Case 1: 부록이 있고, 이미 선택된 내규를 다시 클릭한 경우 (토글)
    if (hasAppendix && isCurrentlyActive && subChildren) {
        if (isCurrentlyOpen) {
            // 부록 닫기
            subChildren.classList.remove('open');
            subChildren.style.display = 'none';
            element.classList.remove('expanded');
        } else {
            // 부록 열기
            subChildren.classList.add('open');
            subChildren.style.display = 'block';
            element.classList.add('expanded');
        }
        return; // 상세보기는 다시 호출하지 않음
    }

    // Case 2: 새로운 내규 선택 또는 부록이 없는 내규
    
    // 모든 기존 선택 해제
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });
    
    // 현재 선택 표시
    element.classList.add('active');
    
    // 부록이 있는 경우 처리
    if (hasAppendix && subChildren) {
        // 다른 모든 부록들 닫기
        document.querySelectorAll('.tree-sub-children').forEach(sub => {
            if (sub !== subChildren) {
                sub.classList.remove('open');
                sub.style.display = 'none';
            }
        });
        document.querySelectorAll('.has-appendix').forEach(hasApp => {
            if (hasApp !== element) {
                hasApp.classList.remove('expanded');
            }
        });

        // 현재 부록 열기
        subChildren.classList.add('open');
        subChildren.style.display = 'block';
        element.classList.add('expanded');
    }
    
    // 상세보기 표시 (부록 상태 업데이트 방지)
    await showRegulationDetailWithoutSidebarUpdate(regulation, chapter);
}

// 부록 선택
function selectAppendix(regulation, appendixItem, chapter) {
    // 기존 선택 해제
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });
    
    // 현재 선택 표시
    if (event && event.target) {
        event.target.classList.add('active');
    }
    
    // PDF 열기
    const appendixIndex = regulation.appendix.indexOf(appendixItem);
    openAppendixPdf(regulation.code, appendixIndex, appendixItem);
}

// sidebar active 상태 업데이트
function updateSidebarActiveState(regulation, chapter) {
    // 모든 active 상태 초기화
    document.querySelectorAll('.tree-children').forEach(child => {
        child.classList.remove('open');
    });
    document.querySelectorAll('.tree-header').forEach(h => {
        h.classList.remove('active');
    });
    document.querySelectorAll('.tree-child').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-children').forEach(sub => {
        sub.classList.remove('open');
    });

    // 1. 해당 챕터의 tree-header 활성화 (정확한 매칭)
    const chapterHeaders = document.querySelectorAll('.tree-header');
    chapterHeaders.forEach(header => {
        const headerText = header.textContent.trim();
        if (headerText === chapter) {
            header.classList.add('active');
            // 해당 챕터의 tree-children 열기
            const children = header.nextElementSibling;
            if (children) {
                children.classList.add('open');
            }
        }
    });

    // 2. 해당 내규의 tree-child 활성화 (정확한 매칭)
    const treeChildren = document.querySelectorAll('.tree-child');
    treeChildren.forEach(child => {
        const childText = child.textContent.trim();
        if (childText.startsWith(regulation.code + '. ')) {
            child.classList.add('active');
            // 3. 부록이 있는 경우 tree-sub-children도 활성화
            if (regulation.appendix && regulation.appendix.length > 0) {
                child.classList.add('expanded');
                const subChildren = child.nextElementSibling;
                if (subChildren && subChildren.classList.contains('tree-sub-children')) {
                    subChildren.classList.add('open');
                }
            }
        }
    });
}



// 내규 상세보기
async function showRegulationDetail(regulation, chapter) {
    // Android WebView 감지 - 최적화 경로 사용
    if (typeof isAndroidWebView === 'function' && isAndroidWebView()) {
        console.log('[Android WebView 감지] 최적화 경로로 전환');
        if (typeof showRegulationDetailAndroid === 'function') {
            return await showRegulationDetailAndroid(regulation, chapter);
        } else {
            console.warn('[Android WebView] kbregulation_android.js가 로드되지 않음 - 기본 경로 사용');
        }
    }

    // 모바일 감지 코드 추가
    const isMobile = window.innerWidth <= 768;

    // 히스토리에 현재 내규 추가 (같은 내규가 아닐 때만)
    const newHistoryItem = {
        regulation: regulation,
        chapter: chapter,
        timestamp: Date.now()
    };

    // 같은 내규를 연속으로 클릭하는 경우가 아니라면 히스토리에 추가
    const lastItem = regulationHistory[regulationHistory.length - 1];
    console.log('마지막 히스토리 아이템:', lastItem);
    
    if (!lastItem || 
        lastItem.regulation.code !== regulation.code || 
        lastItem.chapter !== chapter) {
        console.log('히스토리에 새 아이템 추가');
        regulationHistory.push(newHistoryItem);
        // 히스토리가 너무 길어지지 않도록 최대 20개로 제한
        if (regulationHistory.length > 20) {
            regulationHistory.shift(); // 가장 오래된 항목 제거
        }
        console.log('추가 후 히스토리 길이:', regulationHistory.length);
        console.log('추가 후 히스토리:', regulationHistory);
    } else {
        console.log('같은 내규이므로 히스토리에 추가하지 않음');
    }
   
    // 플래그 리셋
    isNavigatingBack = false; 

    // 전역 변수에 현재 규정 정보 저장
    currentRegulation = regulation;
    currentChapter = chapter;

    // 내규 조회 로그 기록 (25.12.04 추가)
    if (window.RegulationViewLogger && regulation.wzRuleSeq) {
        RegulationViewLogger.logView(
            regulation.wzRuleSeq,
            regulation.name || '',
            regulation.code || ''
        ).catch(err => console.warn('로그 기록 실패 (무시됨):', err));
    }

    // 페이지 상태 설정 - 이 순서가 중요!
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'block';
    
    // 네비게이션 활성화
    updateNavigation('현행 사규');  // '분류'로 수정
    
    const chapterData = getChapterData(chapter);
    document.getElementById('breadcrumbActive').textContent = `${chapter}`;
    document.getElementById('pageTitle').textContent = `${regulation.code}. ${regulation.name}`;
    
    // 헤더에 액션 버튼 추가
    addActionButtonsToHeader(regulation, chapter, isMobile); 
    // sidebar active 상태 업데이트
    updateSidebarActiveState(regulation, chapter);
   
    // 내규 상세 내용 생성
    const contentBody = document.getElementById('contentBody');
    
    // 부록 HTML 생성 (안전한 방식)
    let appendixHtml = '';
    let safeAppendixArray = [];
    
    if (regulation.appendix) {
        if (Array.isArray(regulation.appendix)) {
            safeAppendixArray = regulation.appendix;
        } else if (typeof regulation.appendix === 'string') {
            safeAppendixArray = [regulation.appendix];
        } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
            try {
                safeAppendixArray = Object.values(regulation.appendix).filter(item => item != null);
            } catch (error) {
                console.error('appendix 변환 실패:', error);
                safeAppendixArray = [];
            }
        }
    }
    
    // 부록 HTML 생성 - 제거 (조문에서 직접 처리)

    // 내규 내용 HTML 생성
    let contentHtml = '';
    let metaHtml = '';
   
    if ((regulation.detail && regulation.detail.documentInfo) || regulation.detailData) {
        const docInfo = regulation.detailData?.document_info ||
                       regulation.detailData?.문서정보 ||
                       regulation.detail?.documentInfo;
        
        if (isMobile) {
            // 모바일용 카드 형태 HTML
            metaHtml = `
                <div class="regulation-meta-container">
                    <div class="mobile-meta-cards">
                        <!-- 기본 정보 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">제정일</div>
                                    <div class="mobile-meta-value ${docInfo.제정일 ? '' : 'empty'}">
                                        ${docInfo.제정일 || '-'}
                                    </div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">최종<br>개정일</div>
                                    <div class="mobile-meta-value ${docInfo.최종개정일 ? '' : 'empty'}">
                                        ${docInfo.최종개정일 || '-'}
                                    </div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">최종<br>검토일</div>
                                    <div class="mobile-meta-value ${docInfo.최종검토일 ? '' : 'empty'}">
                                        ${docInfo.최종검토일 || '-'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 부서 정보 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">소관<br>부서</div>
                                    <div class="mobile-meta-value ${docInfo.소관부서 ? '' : 'empty'}">
                                        ${docInfo.소관부서 || '-'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 관련기준 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item" style="height: auto;">
                                    <div class="mobile-meta-label">관련<br>기준</div>
                                    <div class="mobile-meta-value ${docInfo.관련기준 ? '' : 'empty'}">
                                        ${docInfo.관련기준 ? 
                                            (Array.isArray(docInfo.관련기준) ? 
                                                docInfo.관련기준.join('<br>') : 
                                                docInfo.관련기준) :
                                            '-'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 부록 정보 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">부록</div>
                                    <div class="mobile-meta-value">
                                        ${regulation.appendix ? regulation.appendix.length : 0}건
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // 기존 PC용 테이블 형태 HTML
            metaHtml = `
                <div class="regulation-meta-container">
                    <!-- 기본 정보 테이블 -->
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">제정일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.제정일 || '-'}</td>
                            <th class="header-cell" style="border-left:1px solid #000">최종개정일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.최종개정일 || '-'}</td>
                            <th class="header-cell" style="border-left:1px solid #000">최종검토일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.최종검토일 || '-'}</td>
                        </tr>
                        <tr>
                            <th class="header-cell">소관부서</th>
                            <td class="content-cell" colspan="5">${docInfo.소관부서 || '-'}</td>
                        </tr>
                    </table>
                    
                    <!-- 관련기준 테이블 -->
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">관련기준</th>
                            <td class="content-cell long-content">
                                ${docInfo.관련기준 ? 
                                    (Array.isArray(docInfo.관련기준) ? 
                                        docInfo.관련기준.join('<br>') : 
                                        docInfo.관련기준) :
                                    '-'}
                            </td>
                        </tr>
                    </table>
                    
                    <!-- 부록 테이블 -->
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">부록</th>
                            <td class="content-cell">
                                <span class="appendix-count" onclick="toggleAppendixTooltip(event, currentRegulation)">
                                    ${safeAppendixArray.length}건
                                    ${generateAppendixTooltip(regulation)}
                                </span>
                            </td>
                        </tr>
                    </table>
                </div>
            `;
        }
    } else {
        // detail이 없는 경우도 모바일/PC 구분
        if (isMobile) {
            metaHtml = `
                <div class="regulation-meta-container">
                    <div class="mobile-meta-cards">
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">제정일</div>
                                    <div class="mobile-meta-value empty">-</div>
                                </div>
                                <!-- 나머지 빈 정보들... -->
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // 기존 PC용 빈 테이블...
            metaHtml = `기존 PC용 빈 테이블 HTML`;
        }
    } 
    
    // 파일명이 있으면 무조건 상세 데이터를 로드
    if (regulation.detail && regulation.detail.documentInfo && regulation.detail.documentInfo.파일명) {
        const fileName = regulation.detail.documentInfo.파일명;
        console.log('Loading detail file:', fileName);

        try {
            // 개별 파일 로드
            const detailData = await loadRegulationDetail(fileName);

            // regulation 객체에 detailData 병합
            if (detailData) {
                regulation.detailData = detailData;
                console.log('DetailData merged to regulation object');
            }

            if (detailData && detailData.조문내용) {
                console.log('Detail data loaded, rendering articles:', detailData.조문내용.length);

                // 조문 내용 렌더링 (배열 방식으로 최적화)
                const contentParts = [];

                let previousArticle = null;
                let inAppendixSection = false; // 부록 섹션 여부를 추적
                let appendixCounter = 0; // 부록 인덱스 카운터
                let inByulpyoSectionV2 = false; // 별표/별첨/서식 섹션 내부 추적

                detailData.조문내용.forEach((article, index) => {
                    if (!article) return;

                    // 별표/별첨/서식 섹션 헤더 감지
                    const plainContentV2 = (article.내용 || '').replace(/<[^>]+>/g, '').trim();
                    const isByulpyoHeaderV2 = !article.번호 && /^『(별표|별첨|서식)\s*제?\s*\d+\s*호/.test(plainContentV2);

                    // 별표 헤더가 나오면 PDF 링크로 렌더링하고 이후 내용 건너뛰기
                    if (isByulpyoHeaderV2) {
                        inByulpyoSectionV2 = true;
                        const hm = plainContentV2.match(/^『(별표|별첨|서식)\s*제?\s*(\d+)\s*호/);
                        if (hm) {
                            const bType = hm[1], bNum = parseInt(hm[2]);
                            const tName = `${bType} 제${bNum}호`;
                            const tm = plainContentV2.match(/『[^』]+』\s*(.*)/);
                            const bTitle = tm ? tm[1].trim() : '';
                            contentParts.push(`<div style="color: #1976d2; font-weight: 600; margin: 20px 0 5px 0; cursor: pointer; text-decoration: underline;"
                                             onclick="openByulpyoPdf('${regulation.code}', ${bNum}, '${tName.replace(/'/g, "\\'")}', event)">
                                             『${tName}』 ${bTitle} <span style="font-size: 0.85em; color: #666; font-weight: normal;">(PDF 보기)</span>
                                           </div>`);
                        }
                        previousArticle = article;
                        return;
                    }

                    // 별표 섹션 내부의 하위 항목은 건너뛰기
                    if (inByulpyoSectionV2) {
                        if (!(article.번호 && /^제\d+조/.test(article.번호))) {
                            return;
                        }
                        inByulpyoSectionV2 = false;
                    }

                    // 레벨 0인 항목: "제X장" 패턴이면 가운데 정렬로 표시, 아니면 건너뜀
                    if (article.레벨 === 0) {
                        if (article.번호 && /^제\d+(장|절)$/.test(article.번호)) {
                            const chapterTitle = article.번호 + ' ' + (article.내용 || '');
                            contentParts.push(`<div class="chapter-title">${chapterTitle}</div>`);
                        }
                        previousArticle = article;
                        return;
                    }

                    // 제N절 패턴: 별도 section-title 스타일 적용
                    if (article.레벨 === 1 && !article.번호 && /^제\d+절/.test(plainContentV2)) {
                        contentParts.push(`<div class="section-title">${article.내용}</div>`);
                        previousArticle = article;
                        return;
                    }

                    // 제4조 (부록)이 나오면 부록 섹션 시작
                    if (article.번호 === '제4조' && article.내용 && article.내용.includes('(부록)')) {
                        inAppendixSection = true;
                        appendixCounter = 0; // 부록 카운터 초기화
                    }
                    // 제5조가 나오면 부록 섹션 종료
                    else if (article.번호 === '제5조') {
                        inAppendixSection = false;
                    }

                    // 제5조 다음에 오는 제1조(내규의 제정 및 시행)인지 확인
                    if (previousArticle && previousArticle.번호 === '제5조' &&
                        article.번호 === '제1조' && article.내용 && article.내용.includes('내규의 제정')) {
                        // 제개정 이력 제목 추가
                        contentParts.push(`<div style="font-weight: 600; color: #2786dd; text-align:center; padding-left: 0px;margin-top:30px;margin-bottom:20px;">내규의 제·개정 이력</div>`);
                    }

                    // 레벨에 따른 클래스 설정
                    let className = '';
                    let paddingLeft = 0;
                    switch(article.레벨) {
                        case 1: paddingLeft = 0; break;
                        case 2: paddingLeft = 20; break;
                        case 3: paddingLeft = 60; break;
                        case 4: paddingLeft = 80; break;
                        case 5: paddingLeft = 105; break;
                        case 6: paddingLeft = 125; break;
                        case 7: paddingLeft = 140; break;
                        case 8: paddingLeft = 160; break;
                        default: paddingLeft = 160; break;
                    }

                    // 레벨 전환 시 추가 여백 처리
                    let additionalStyle = '';
                    if (previousArticle && article.레벨 === 2) {
                        // 레벨 3 이상에서 레벨 2로 변경될 때 또는 레벨 2에서 레벨 2로 이어질 때
                        if (previousArticle.레벨 >= 3 || previousArticle.레벨 === 2) {
                            additionalStyle = 'margin-top: 15px;';
                        }
                    }

                    // JSON의 정렬 속성 적용
                    if (article.정렬 === 'center') {
                        additionalStyle += 'text-align: center;';
                    } else if (article.정렬 === 'right') {
                        additionalStyle += 'text-align: right;';
                    }
                    if (article.글꼴크기) {
                        additionalStyle += ` font-size: ${article.글꼴크기}pt;`;
                    }

                    // 내규의 제개정 이력 여부 확인
                    let isHistorySection = false;

                    if (article.레벨 === 1) {
                        className = 'article-title';
                        // 제개정 이력은 특별한 클래스
                        if (article.내용 && article.내용.includes('내규의 제·개정 이력')) {
                            className = 'article-title history-section';
                            isHistorySection = true;
                        }
                    } else if (article.레벨 === 2) {
                        className = 'article-item';
                    } else {
                        className = 'article-sub-item';
                    }

                    let displayText;
                    if (article.번호 && article.레벨 === 1) {
                        displayText = `<b>${article.번호}</b> ${article.내용}`;
                    } else {
                        displayText = article.번호 ? `${article.번호} ${article.내용}` : article.내용;
                    }

                    // 별표 참조를 클릭 가능한 링크로 변환
                    displayText = linkifyByulpyo(displayText, detailData.조문내용, false, regulation.code);

                    // 부록 섹션 내의 레벨 2 항목인지 확인
                    let isAppendixItem = false;

                    if (inAppendixSection && article.레벨 === 2) {
                        isAppendixItem = true;
                    }

                    // 부록 항목이면 클릭 가능하게 만들기
                    if (isAppendixItem) {
                        // 부록 텍스트에서 부록 제목 추출
                        const appendixTitle = article.내용.replace(/^\d+\.\s*/, '');
                        contentParts.push(`<div class="${className} appendix-link"
                                           style="padding-left: ${paddingLeft}px; cursor: pointer; color: #1976d2; text-decoration: underline;"
                                           onclick="openAppendixPdf('${regulation.code}', ${appendixCounter}, '${appendixTitle.replace(/'/g, "\\'")}')">
                                           ${displayText}
                                        </div>`);
                        appendixCounter++; // 다음 부록을 위해 카운터 증가
                    } else {
                        if (className === 'article-sub-item') {
                            if (article.레벨 === 3) {
                                contentParts.push(`<div class="${className}" style="padding-left: 60px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 4) {
                                contentParts.push(`<div class="${className}" style="padding-left: 80px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 5) {
                                contentParts.push(`<div class="${className}" style="padding-left: 105px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 6) {
                                contentParts.push(`<div class="${className}" style="padding-left: 125px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 7) {
                                contentParts.push(`<div class="${className}" style="padding-left: 140px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 8) {
                                contentParts.push(`<div class="${className}" style="padding-left: 160px; text-indent: -20px;">${displayText}</div>`);
                            } else {
                                contentParts.push(`<div class="${className}" style="padding-left: ${paddingLeft}px;">${displayText}</div>`);
                            }
                        } else {
                            if (className === 'article-item' && article.레벨 === 2) {
                                contentParts.push(`<div class="${className}" style="padding-left: 35px; text-indent: -15px; ${additionalStyle}">${displayText}</div>`);
                            } else if (isHistorySection) {
                                // 내규의 제·개정 이력은 특별한 스타일 적용
                                contentParts.push(`<div class="${className}" style="padding-left: 0px; text-align: center; padding-bottom: 8px; font-weight: bold; color: #000; ${additionalStyle}">${displayText}</div>`);
                            } else {
                                contentParts.push(`<div class="${className}" style="padding-left: ${paddingLeft}px; ${additionalStyle}">${displayText}</div>`);
                            }
                        }
                    }

                    // 현재 article을 이전 article로 저장
                    previousArticle = article;

                    // 관련 이미지가 있으면 표시
                    if (article.관련이미지 && article.관련이미지.length > 0) {
                        article.관련이미지.forEach(img => {
                            contentParts.push(`<div style="margin: 10px 0; padding-left: ${paddingLeft + 20}px;">
                                <img src="${img.file_path}" style="max-width: 100%; height: auto; border: 1px solid #e0e0e0; border-radius: 4px;">
                            </div>`);
                        });
                    }
                });

                contentHtml = contentParts.join('');
            } else {
                console.error('Failed to load detail data or no articles found');
                contentHtml = `
                    <div class="article-title">내규 내용</div>
                    <div class="article-item">
                        내규 데이터를 불러오는 중 오류가 발생했습니다.
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading detail file:', error);
            contentHtml = `
                <div class="article-title">내규 내용</div>
                <div class="article-item">
                    내규 데이터를 불러오는 중 오류가 발생했습니다: ${error.message}
                </div>
            `;
        }
    } else if (regulation.detail && regulation.detail.articles && Array.isArray(regulation.detail.articles)) {
        // 기존 articles 구조 처리 (호환성 유지)
        regulation.detail.articles.forEach(article => {
            if (!article) return;

            if (article.title) {
                contentHtml += `<div class="article-title">${article.title}</div>`;
            }

            if (article.content) {
                contentHtml += `<div class="article-item">${article.content}</div>`;
            }

            if (article.subsections && Array.isArray(article.subsections)) {
                article.subsections.forEach(subsection => {
                    if (!subsection) return;
                    if (subsection.title) {
                        contentHtml += `<div class="article-item"><strong>${subsection.title}</strong></div>`;
                    }
                    if (subsection.items && Array.isArray(subsection.items)) {
                        subsection.items.forEach(item => {
                            if (item) {
                                contentHtml += `<div class="article-sub-item" style="padding-left: 60px; text-indent: -20px;">${item}</div>`;
                            }
                        });
                    }
                });
            }
        });
    } else {
        // 파일명이 없는 경우
        contentHtml = `
            <div class="article-title">내규 내용</div>
            <div class="article-item">
                <strong>${regulation.name}</strong> 내규의 파일 정보를 찾을 수 없습니다.
            </div>
        `;
    }

    // 콘텐츠를 숨긴 상태로 시작
    contentBody.style.opacity = '0';
    contentBody.style.transition = 'opacity 0.2s ease-in-out';

    // 문서 기본 글꼴 적용
    const docFontFamily = regulation.detailData?.문서정보?.기본글꼴;
    const regFontStyle = docFontFamily ? ` style="font-family: '${docFontFamily}', sans-serif;"` : '';

    // 최종 HTML 조합
    contentBody.innerHTML = `
        <div class="regulation-detail mal-font">
            <div class="regulation-header">
                ${metaHtml}
            </div>
            <div class="regulation-content"${regFontStyle}>
                ${contentHtml}
            </div>
        </div>
    `;
    console.log('내규 상세보기 렌더링 완료');

    updateRecentRegulations(regulation, chapter, 'regulation');

    // 저장된 글꼴 크기 적용 후 화면 표시
    setTimeout(() => {
        if (typeof loadSavedFontSize === 'function') {
            loadSavedFontSize();
        }
        // 글꼴 크기 적용 직후 콘텐츠 표시
        requestAnimationFrame(() => {
            // 콘텐츠 로드 완료 후 스크롤 리셋
            setTimeout(() => {
                resetAllScrolls();         // 2차 호출 (내부에서 또 3번 실행)
            }, 100);
            contentBody.style.opacity = '1';

            // 워터마크 적용 (사용자 정보가 있는 경우)
            if (typeof applyWatermarkToContent === 'function') {
                applyWatermarkToContent();
            }
        });
    }, 10);

}

// 사이드바 상태 업데이트 없이 내규 상세보기 표시
async function showRegulationDetailWithoutSidebarUpdate(regulation, chapter) {
    // Android WebView 감지 - 최적화 경로 사용
    if (typeof isAndroidWebView === 'function' && isAndroidWebView()) {
        console.log('[Android WebView 감지 - Sidebar] 최적화 경로로 전환');
        if (typeof showRegulationDetailAndroid === 'function') {
            return await showRegulationDetailAndroid(regulation, chapter);
        } else {
            console.warn('[Android WebView] kbregulation_android.js가 로드되지 않음 - 기본 경로 사용');
        }
    }

    // 모바일 감지 코드 추가
    const isMobile = window.innerWidth <= 768;
 
    // 히스토리에 현재 내규 추가 (같은 내규가 아닐 때만)
    const newHistoryItem = {
        regulation: regulation,
        chapter: chapter,
        timestamp: Date.now()
    };

    // 같은 내규를 연속으로 클릭하는 경우가 아니라면 히스토리에 추가
    const lastItem = regulationHistory[regulationHistory.length - 1];
    console.log('마지막 히스토리 아이템:', lastItem);
    
    if (!lastItem || 
        lastItem.regulation.code !== regulation.code || 
        lastItem.chapter !== chapter) {
        console.log('히스토리에 새 아이템 추가');
        regulationHistory.push(newHistoryItem);
        // 히스토리가 너무 길어지지 않도록 최대 20개로 제한
        if (regulationHistory.length > 20) {
            regulationHistory.shift(); // 가장 오래된 항목 제거
        }
        console.log('추가 후 히스토리 길이:', regulationHistory.length);
        console.log('추가 후 히스토리:', regulationHistory);
    } else {
        console.log('같은 내규이므로 히스토리에 추가하지 않음');
    }
   
    // 플래그 리셋
    isNavigatingBack = false; 


    // 전역 변수에 현재 규정 정보 저장
    currentRegulation = regulation;
    currentChapter = chapter;

    // 내규 조회 로그 기록 (25.12.04 추가)
    if (window.RegulationViewLogger && regulation.wzRuleSeq) {
        RegulationViewLogger.logView(
            regulation.wzRuleSeq,
            regulation.name || '',
            regulation.code || ''
        ).catch(err => console.warn('로그 기록 실패 (무시됨):', err));
    }

    // 페이지 상태 설정
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'block';
    
    // 네비게이션 활성화
    updateNavigation('현행 사규');
    
    const chapterData = getChapterData(chapter);
    document.getElementById('breadcrumbActive').textContent = `${chapter}`;
    document.getElementById('pageTitle').textContent = `${regulation.code}. ${regulation.name}`;
   
    // 헤더에 액션 버튼 추가
    addActionButtonsToHeader(regulation, chapter, isMobile); 
    // updateSidebarActiveState 호출하지 않음
    
 
    // 챕터만 활성화 (부록 상태는 건드리지 않음)
    document.querySelectorAll('.tree-header').forEach(h => {
        h.classList.remove('active');
    });
    document.querySelectorAll('.tree-children').forEach(child => {
        child.classList.remove('open');
    });
    
    const chapterHeaders = document.querySelectorAll('.tree-header');
    chapterHeaders.forEach(header => {
        const headerText = header.textContent.trim();
        if (headerText === chapter) {
            header.classList.add('active');
            const children = header.nextElementSibling;
            if (children) {
                children.classList.add('open');
            }
        }
    });

    // 내규 상세 내용 생성
    const contentBody = document.getElementById('contentBody');
    
    // 부록 HTML 생성 (안전한 방식)
    let appendixHtml = '';
    let safeAppendixArray = [];
    
    if (regulation.appendix) {
        if (Array.isArray(regulation.appendix)) {
            safeAppendixArray = regulation.appendix;
        } else if (typeof regulation.appendix === 'string') {
            safeAppendixArray = [regulation.appendix];
        } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
            try {
                safeAppendixArray = Object.values(regulation.appendix).filter(item => item != null);
            } catch (error) {
                console.error('appendix 변환 실패:', error);
                safeAppendixArray = [];
            }
        }
    }

    // 부록 HTML 생성 - 제거 (조문에서 직접 처리)    

    // 내규 내용 HTML 생성
    let contentHtml = '';
    let metaHtml = '';
   
    if ((regulation.detail && regulation.detail.documentInfo) || regulation.detailData) {
        const docInfo = regulation.detailData?.document_info ||
                       regulation.detailData?.문서정보 ||
                       regulation.detail?.documentInfo;
        
        if (isMobile) {
            // 모바일용 카드 형태 HTML
            metaHtml = `
                <div class="regulation-meta-container">
                    <div class="mobile-meta-cards">
                        <!-- 기본 정보 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">제정일</div>
                                    <div class="mobile-meta-value ${docInfo.제정일 ? '' : 'empty'}">
                                        ${docInfo.제정일 || '-'}
                                    </div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">최종<br>개정일</div>
                                    <div class="mobile-meta-value ${docInfo.최종개정일 ? '' : 'empty'}">
                                        ${docInfo.최종개정일 || '-'}
                                    </div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">최종<br>검토일</div>
                                    <div class="mobile-meta-value ${docInfo.최종검토일 ? '' : 'empty'}">
                                        ${docInfo.최종검토일 || '-'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 부서 정보 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">소관<br>부서</div>
                                    <div class="mobile-meta-value ${docInfo.소관부서 ? '' : 'empty'}">
                                        ${docInfo.소관부서 || '-'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 관련기준 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item" style="height: auto;">
                                    <div class="mobile-meta-label">관련<br>기준</div>
                                    <div class="mobile-meta-value ${docInfo.관련기준 ? '' : 'empty'}">
                                        ${docInfo.관련기준 ? 
                                            (Array.isArray(docInfo.관련기준) ? 
                                                docInfo.관련기준.join('<br>') : 
                                                docInfo.관련기준) :
                                            '-'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 부록 정보 카드 -->
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">부록</div>
                                    <div class="mobile-meta-value">
                                        ${regulation.appendix ? regulation.appendix.length : 0}건
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // 기존 PC용 테이블 형태 HTML
            metaHtml = `
                <div class="regulation-meta-container">
                    <!-- 기본 정보 테이블 -->
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">제정일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.제정일 || '-'}</td>
                            <th class="header-cell" style="border-left:1px solid #000">최종개정일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.최종개정일 || '-'}</td>
                            <th class="header-cell" style="border-left:1px solid #000">최종검토일</th>
                            <td class="content-cell" style="text-align:center;">${docInfo.최종검토일 || '-'}</td>
                        </tr>
                        <tr>
                            <th class="header-cell">소관부서</th>
                            <td class="content-cell" colspan="5">${docInfo.소관부서 || '-'}</td>
                        </tr>
                    </table>
                    
                    <!-- 관련기준 테이블 -->
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">관련기준</th>
                            <td class="content-cell long-content">
                                ${docInfo.관련기준 ? 
                                    (Array.isArray(docInfo.관련기준) ? 
                                        docInfo.관련기준.join('<br>') : 
                                        docInfo.관련기준) :
                                    '-'}
                            </td>
                        </tr>
                    </table>
                    
                    <!-- 부록 테이블 -->
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">부록</th>
                            <td class="content-cell">
                                <span class="appendix-count" onclick="toggleAppendixTooltip(event, currentRegulation)">
                                    ${safeAppendixArray.length}건
                                    ${generateAppendixTooltip(regulation)}
                                </span>
                            </td>
                        </tr>
                    </table>
                </div>
            `;
        }
    } else {
        // detail이 없는 경우도 모바일/PC 구분
        if (isMobile) {
            metaHtml = `
                <div class="regulation-meta-container">
                    <div class="mobile-meta-cards">
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">제정일</div>
                                    <div class="mobile-meta-value empty">-</div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">최종<br>개정일</div>
                                    <div class="mobile-meta-value empty">-</div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">최종<br>검토일</div>
                                    <div class="mobile-meta-value empty">-</div>
                                </div>
                            </div>
                        </div>
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">담당<br>부서</div>
                                    <div class="mobile-meta-value empty">-</div>
                                </div>
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">유관<br>부서</div>
                                    <div class="mobile-meta-value empty">-</div>
                                </div>
                            </div>
                        </div>
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">관련<br>기준</div>
                                    <div class="mobile-meta-value empty">-</div>
                                </div>
                            </div>
                        </div>
                        <div class="mobile-meta-card">
                            <div class="mobile-meta-card-content">
                                <div class="mobile-meta-item">
                                    <div class="mobile-meta-label">부록</div>
                                    <div class="mobile-meta-value">${safeAppendixArray.length}건</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            metaHtml = `
                <div class="regulation-meta-container">
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">제정일</th>
                            <td class="content-cell" style="text-align:center;">-</td>
                            <th class="header-cell" style="border-left:1px solid #000">최종개정일</th>
                            <td class="content-cell" style="text-align:center;">-</td>
                            <th class="header-cell" style="border-left:1px solid #000">최종검토일</th>
                            <td class="content-cell" style="text-align:center;">-</td>
                        </tr>
                        <tr>
                            <th class="header-cell">소관부서</th>
                            <td class="content-cell" colspan="5">-</td>
                        </tr>
                    </table>
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">관련기준</th>
                            <td class="content-cell">-</td>
                        </tr>
                    </table>
                    <table class="regulation-meta-table">
                        <tr>
                            <th class="header-cell">부록</th>
                            <td class="content-cell">
                                <span class="appendix-count">${safeAppendixArray.length}건</span>
                            </td>
                        </tr>
                    </table>
                </div>
            `;
        }
    } 
    
    // 파일명이 있으면 무조건 상세 데이터를 로드
    if (regulation.detail && regulation.detail.documentInfo && regulation.detail.documentInfo.파일명) {
        const fileName = regulation.detail.documentInfo.파일명;
        console.log('Loading detail file:', fileName);

        try {
            // 개별 파일 로드
            const detailData = await loadRegulationDetail(fileName);

            // regulation 객체에 detailData 병합
            if (detailData) {
                regulation.detailData = detailData;
                console.log('DetailData merged to regulation object');
            }

            if (detailData && detailData.조문내용) {
                console.log('Detail data loaded, rendering articles:', detailData.조문내용.length);

                // 조문 내용 렌더링 (배열 방식으로 최적화)
                const contentParts = [];

                let previousArticle = null;
                let inAppendixSection = false; // 부록 섹션 여부를 추적
                let appendixCounter = 0; // 부록 인덱스 카운터
                let inByulpyoSectionV2 = false; // 별표/별첨/서식 섹션 내부 추적

                detailData.조문내용.forEach((article, index) => {
                    if (!article) return;

                    // 별표/별첨/서식 섹션 헤더 감지
                    const plainContentV2 = (article.내용 || '').replace(/<[^>]+>/g, '').trim();
                    const isByulpyoHeaderV2 = !article.번호 && /^『(별표|별첨|서식)\s*제?\s*\d+\s*호/.test(plainContentV2);

                    // 별표 헤더가 나오면 PDF 링크로 렌더링하고 이후 내용 건너뛰기
                    if (isByulpyoHeaderV2) {
                        inByulpyoSectionV2 = true;
                        const hm = plainContentV2.match(/^『(별표|별첨|서식)\s*제?\s*(\d+)\s*호/);
                        if (hm) {
                            const bType = hm[1], bNum = parseInt(hm[2]);
                            const tName = `${bType} 제${bNum}호`;
                            const tm = plainContentV2.match(/『[^』]+』\s*(.*)/);
                            const bTitle = tm ? tm[1].trim() : '';
                            contentParts.push(`<div style="color: #1976d2; font-weight: 600; margin: 20px 0 5px 0; cursor: pointer; text-decoration: underline;"
                                             onclick="openByulpyoPdf('${regulation.code}', ${bNum}, '${tName.replace(/'/g, "\\'")}', event)">
                                             『${tName}』 ${bTitle} <span style="font-size: 0.85em; color: #666; font-weight: normal;">(PDF 보기)</span>
                                           </div>`);
                        }
                        previousArticle = article;
                        return;
                    }

                    // 별표 섹션 내부의 하위 항목은 건너뛰기
                    if (inByulpyoSectionV2) {
                        if (!(article.번호 && /^제\d+조/.test(article.번호))) {
                            return;
                        }
                        inByulpyoSectionV2 = false;
                    }

                    // 레벨 0인 항목: "제X장" 패턴이면 가운데 정렬로 표시, 아니면 건너뜀
                    if (article.레벨 === 0) {
                        if (article.번호 && /^제\d+(장|절)$/.test(article.번호)) {
                            const chapterTitle = article.번호 + ' ' + (article.내용 || '');
                            contentParts.push(`<div class="chapter-title">${chapterTitle}</div>`);
                        }
                        previousArticle = article;
                        return;
                    }

                    // 제N절 패턴: 별도 section-title 스타일 적용
                    if (article.레벨 === 1 && !article.번호 && /^제\d+절/.test(plainContentV2)) {
                        contentParts.push(`<div class="section-title">${article.내용}</div>`);
                        previousArticle = article;
                        return;
                    }

                    // 제4조 (부록)이 나오면 부록 섹션 시작
                    if (article.번호 === '제4조' && article.내용 && article.내용.includes('(부록)')) {
                        inAppendixSection = true;
                        appendixCounter = 0; // 부록 카운터 초기화
                    }
                    // 제5조가 나오면 부록 섹션 종료
                    else if (article.번호 === '제5조') {
                        inAppendixSection = false;
                    }

                    // 제5조 다음에 오는 제1조(내규의 제정 및 시행)인지 확인
                    if (previousArticle && previousArticle.번호 === '제5조' &&
                        article.번호 === '제1조' && article.내용 && article.내용.includes('내규의 제정')) {
                        // 제개정 이력 제목 추가
                        contentParts.push(`<div style="font-weight: 600; color: #2786dd; text-align:center; padding-left: 0px;margin-top:30px;margin-bottom:20px;">내규의 제·개정 이력</div>`);
                    }

                    // 레벨에 따른 클래스 설정
                    let className = '';
                    let paddingLeft = 0;
                    switch(article.레벨) {
                        case 1: paddingLeft = 0; break;
                        case 2: paddingLeft = 20; break;
                        case 3: paddingLeft = 60; break;
                        case 4: paddingLeft = 80; break;
                        case 5: paddingLeft = 105; break;
                        case 6: paddingLeft = 125; break;
                        case 7: paddingLeft = 140; break;
                        case 8: paddingLeft = 160; break;
                        default: paddingLeft = 160; break;
                    }

                    // 레벨 전환 시 추가 여백 처리
                    let additionalStyle = '';
                    if (previousArticle && article.레벨 === 2) {
                        // 레벨 3 이상에서 레벨 2로 변경될 때 또는 레벨 2에서 레벨 2로 이어질 때
                        if (previousArticle.레벨 >= 3 || previousArticle.레벨 === 2) {
                            additionalStyle = 'margin-top: 15px;';
                        }
                    }

                    // JSON의 정렬 속성 적용
                    if (article.정렬 === 'center') {
                        additionalStyle += 'text-align: center;';
                    } else if (article.정렬 === 'right') {
                        additionalStyle += 'text-align: right;';
                    }
                    if (article.글꼴크기) {
                        additionalStyle += ` font-size: ${article.글꼴크기}pt;`;
                    }

                    // 내규의 제개정 이력 여부 확인
                    let isHistorySection = false;

                    if (article.레벨 === 1) {
                        className = 'article-title';
                        // 제개정 이력은 특별한 클래스
                        if (article.내용 && article.내용.includes('내규의 제·개정 이력')) {
                            className = 'article-title history-section';
                            isHistorySection = true;
                        }
                    } else if (article.레벨 === 2) {
                        className = 'article-item';
                    } else {
                        className = 'article-sub-item';
                    }

                    let displayText;
                    if (article.번호 && article.레벨 === 1) {
                        displayText = `<b>${article.번호}</b> ${article.내용}`;
                    } else {
                        displayText = article.번호 ? `${article.번호} ${article.내용}` : article.내용;
                    }

                    // 별표 참조를 클릭 가능한 링크로 변환
                    displayText = linkifyByulpyo(displayText, detailData.조문내용, false, regulation.code);

                    // 부록 섹션 내의 레벨 2 항목인지 확인
                    let isAppendixItem = false;

                    if (inAppendixSection && article.레벨 === 2) {
                        isAppendixItem = true;
                    }

                    // 부록 항목이면 클릭 가능하게 만들기
                    if (isAppendixItem) {
                        // 부록 텍스트에서 부록 제목 추출
                        const appendixTitle = article.내용.replace(/^\d+\.\s*/, '');
                        contentParts.push(`<div class="${className} appendix-link"
                                           style="padding-left: ${paddingLeft}px; cursor: pointer; color: #1976d2; text-decoration: underline;"
                                           onclick="openAppendixPdf('${regulation.code}', ${appendixCounter}, '${appendixTitle.replace(/'/g, "\\'")}')">
                                           ${displayText}
                                        </div>`);
                        appendixCounter++; // 다음 부록을 위해 카운터 증가
                    } else {
                        if (className === 'article-sub-item') {
                            if (article.레벨 === 3) {
                                contentParts.push(`<div class="${className}" style="padding-left: 60px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 4) {
                                contentParts.push(`<div class="${className}" style="padding-left: 80px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 5) {
                                contentParts.push(`<div class="${className}" style="padding-left: 105px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 6) {
                                contentParts.push(`<div class="${className}" style="padding-left: 125px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 7) {
                                contentParts.push(`<div class="${className}" style="padding-left: 140px; text-indent: -20px;">${displayText}</div>`);
                            } else if (article.레벨 === 8) {
                                contentParts.push(`<div class="${className}" style="padding-left: 160px; text-indent: -20px;">${displayText}</div>`);
                            } else {
                                contentParts.push(`<div class="${className}" style="padding-left: ${paddingLeft}px;">${displayText}</div>`);
                            }
                        } else {
                            if (className === 'article-item' && article.레벨 === 2) {
                                contentParts.push(`<div class="${className}" style="padding-left: 35px; text-indent: -15px; ${additionalStyle}">${displayText}</div>`);
                            } else if (isHistorySection) {
                                // 내규의 제·개정 이력은 특별한 스타일 적용
                                contentParts.push(`<div class="${className}" style="padding-left: 0px; text-align: center; padding-bottom: 8px; font-weight: bold; color: #000; ${additionalStyle}">${displayText}</div>`);
                            } else {
                                contentParts.push(`<div class="${className}" style="padding-left: ${paddingLeft}px; ${additionalStyle}">${displayText}</div>`);
                            }
                        }
                    }

                    // 현재 article을 이전 article로 저장
                    previousArticle = article;

                    // 관련 이미지가 있으면 표시
                    if (article.관련이미지 && article.관련이미지.length > 0) {
                        article.관련이미지.forEach(img => {
                            contentParts.push(`<div style="margin: 10px 0; padding-left: ${paddingLeft + 20}px;">
                                <img src="${img.file_path}" style="max-width: 100%; height: auto; border: 1px solid #e0e0e0; border-radius: 4px;">
                            </div>`);
                        });
                    }
                });

                contentHtml = contentParts.join('');
            } else {
                console.error('Failed to load detail data or no articles found');
                contentHtml = `
                    <div class="article-title">내규 내용</div>
                    <div class="article-item">
                        내규 데이터를 불러오는 중 오류가 발생했습니다.
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading detail file:', error);
            contentHtml = `
                <div class="article-title">내규 내용</div>
                <div class="article-item">
                    내규 데이터를 불러오는 중 오류가 발생했습니다: ${error.message}
                </div>
            `;
        }
    } else if (regulation.detail && regulation.detail.articles && Array.isArray(regulation.detail.articles)) {
        // 기존 articles 구조 처리 (호환성 유지)
        regulation.detail.articles.forEach(article => {
            if (!article) return;

            if (article.title) {
                contentHtml += `<div class="article-title">${article.title}</div>`;
            }

            if (article.content) {
                contentHtml += `<div class="article-item">${article.content}</div>`;
            }

            if (article.subsections && Array.isArray(article.subsections)) {
                article.subsections.forEach(subsection => {
                    if (!subsection) return;
                    if (subsection.title) {
                        contentHtml += `<div class="article-item"><strong>${subsection.title}</strong></div>`;
                    }
                    if (subsection.items && Array.isArray(subsection.items)) {
                        subsection.items.forEach(item => {
                            if (item) {
                                contentHtml += `<div class="article-sub-item" style="padding-left: 60px; text-indent: -20px;">${item}</div>`;
                            }
                        });
                    }
                });
            }
        });
    } else {
        // 파일명이 없는 경우
        contentHtml = `
            <div class="article-title">내규 내용</div>
            <div class="article-item">
                <strong>${regulation.name}</strong> 내규의 파일 정보를 찾을 수 없습니다.
            </div>
        `;
    }

    // 콘텐츠를 숨긴 상태로 시작
    contentBody.style.opacity = '0';
    contentBody.style.transition = 'opacity 0.2s ease-in-out';

    // 문서 기본 글꼴 적용
    const docFontFamily = regulation.detailData?.문서정보?.기본글꼴;
    const regFontStyle = docFontFamily ? ` style="font-family: '${docFontFamily}', sans-serif;"` : '';

    // 최종 HTML 조합
    contentBody.innerHTML = `
        <div class="regulation-detail mal-font">
            <div class="regulation-header">
                ${metaHtml}
            </div>
            <div class="regulation-content"${regFontStyle}>
                ${contentHtml}
            </div>
        </div>
    `;

    console.log('내규 상세보기 렌더링 완료 (사이드바 업데이트 없음)');
    updateRecentRegulations(regulation, chapter, 'regulation');

    // 저장된 글꼴 크기 적용 후 화면 표시
    setTimeout(() => {
        if (typeof loadSavedFontSize === 'function') {
            loadSavedFontSize();
        }
        // 글꼴 크기 적용 직후 콘텐츠 표시
        requestAnimationFrame(() => {
            // 콘텐츠 로드 완료 후 스크롤 리셋
            setTimeout(() => {
                resetAllScrolls();         // 2차 호출 (내부에서 또 3번 실행)
            }, 100);
            contentBody.style.opacity = '1';
        });
    }, 10);

}

// 헤더에 액션 버튼을 추가하는 함수
function addActionButtonsToHeader(regulation, chapter, isMobile) {
    const header = document.getElementById('main-content-header');

    // 기존 액션 버튼이 있으면 제거
    const existingActions = header.querySelector('.regulation-actions-wrap');
    if (existingActions) existingActions.remove();
    const existingActionsOld = header.querySelector('.regulation-actions');
    if (existingActionsOld) existingActionsOld.remove();

    // 모바일용 뒤로가기 버튼 추가
    const mobileBackButton = isMobile ? `
        <button class="action-btn mobile-back-action" onclick="goBackFromRegulation()" data-tooltip="뒤로가기">
            <i class="fas fa-arrow-left"></i>
        </button>
    ` : '';

    // 인쇄 버튼 (도메인 체크)
    const showPrint = (typeof isPrintAllowed === 'function' && isPrintAllowed());

    // 액션 버튼 HTML 생성
    const actionButtonsHtml = isMobile ? `
        <div class="regulation-actions">
            ${mobileBackButton}
        </div>
    ` : `
        <div class="regulation-actions-wrap">
            <div class="regulation-actions-row">
                <button class="text-action-btn" onclick="toggleRegulationNoticePanel()">안내사항</button>
                <button class="text-action-btn" onclick="toggleContentSearch()">본문검색</button>
                <button class="text-action-btn" onclick="openComparisonTablePdf('${regulation.code}', '${regulation.name}', '${regulation.wzRuleSeq || ''}')">신구대비</button>
                <button class="text-action-btn" id="btnColumnToggle" onclick="toggleColumnView()">2단보기</button>
                <button class="text-action-btn" onclick="downloadRegulationPdf('${regulation.code}', '${regulation.name}')">전문다운</button>
                ${showPrint ? '<button class="text-action-btn" onclick="printRegulation()">인쇄</button>' : ''}
            </div>
            <div class="regulation-actions-row">
                <button class="text-action-btn" onclick="decreaseFontSize()">글꼴 작게</button>
                <button class="text-action-btn" onclick="increaseFontSize()">글꼴 크게</button>
                <button class="text-action-btn" onclick="resetFontSize()">글꼴 원래대로</button>
            </div>
        </div>
    `;

    // 헤더에 버튼 추가
    header.insertAdjacentHTML('beforeend', actionButtonsHtml);
}

// 부록 상세보기
async function showAppendixDetail(regulation, appendixItem, chapter, index = null) {
    // sidebar 보이도록
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';
    // 네비게이션 활성화
    updateNavigation('현행 사규');
    const chapterData = getChapterData(chapter);
    document.getElementById('breadcrumbActive').textContent = `${chapter}`;
    document.getElementById('pageTitle').textContent = `부록${index + 1}. ${appendixItem}`;
    // sidebar active 상태 업데이트 (부록용)
    updateSidebarActiveStateForAppendix(regulation, appendixItem, chapter, index);

    const contentBody = document.getElementById('contentBody');

    // 로딩 표시
    contentBody.innerHTML = `
        <div class="regulation-detail">
            <div style="text-align: center; padding: 40px;">
                <div class="spinner-border" role="status">
                    <span class="sr-only">로딩 중...</span>
                </div>
                <p style="margin-top: 10px;">부록 파일을 불러오는 중...</p>
            </div>
        </div>
    `;

    try {
        // regulation.wzRuleSeq를 사용하여 부록 목록 가져오기
        const ruleSeq = regulation.wzRuleSeq || regulation.wzruleseq;
        const response = await fetch(`/api/v1/appendix/list/${ruleSeq}`);

        if (!response.ok) {
            throw new Error('부록 목록을 불러올 수 없습니다');
        }

        const appendixList = await response.json();

        // index에 해당하는 부록 파일 찾기
        const appendixFile = appendixList[index];

        if (!appendixFile) {
            throw new Error('부록 파일을 찾을 수 없습니다');
        }

        // 부록 파일 표시
        const fileExtension = appendixFile.wzappendixfilename.split('.').pop().toLowerCase();

        contentBody.innerHTML = `
            <div class="regulation-detail">
                <div class="regulation-header">
                    <div class="regulation-meta">
                        <span>문서 유형: 부록</span>
                        <span>부록 번호: ${appendixFile.wzappendixno}</span>
                        <span>파일명: ${appendixFile.wzappendixfilename}</span>
                    </div>
                </div>
                <div class="regulation-content">
                    <div style="margin-bottom: 20px;">
                        <h4 style="color: #1565c0; margin-bottom: 15px;">${appendixItem}</h4>
                        <p>이 부록은 <strong>${regulation.name}</strong> 내규의 시행을 위한 첨부 자료입니다.</p>
                    </div>

                    ${fileExtension === 'pdf' ? `
                        <div style="width: 100%; height: 800px; border: 1px solid #ddd;">
                            <embed src="/api/v1/appendix/download/${ruleSeq}/${encodeURIComponent(appendixFile.wzappendixfilename)}"
                                   type="application/pdf"
                                   width="100%"
                                   height="100%">
                        </div>
                    ` : fileExtension.match(/jpg|jpeg|png|gif/) ? `
                        <div style="text-align: center;">
                            <img src="/api/v1/appendix/download/${ruleSeq}/${encodeURIComponent(appendixFile.wzappendixfilename)}"
                                 style="max-width: 100%; height: auto;"
                                 alt="${appendixItem}">
                        </div>
                    ` : `
                        <div style="text-align: center; padding: 40px; background: #f8f9fa; border-radius: 8px;">
                            <i class="fas fa-file-download" style="font-size: 48px; color: #667eea; margin-bottom: 20px;"></i>
                            <p style="margin-bottom: 20px;">이 파일은 미리보기를 지원하지 않습니다.</p>
                            <a href="/api/v1/appendix/download/${ruleSeq}/${encodeURIComponent(appendixFile.wzappendixfilename)}"
                               download="${appendixFile.wzappendixfilename}"
                               class="btn btn-primary">
                                <i class="fas fa-download"></i> 파일 다운로드
                            </a>
                        </div>
                    `}

                    <div style="margin-top: 20px; padding: 15px; background: #e8f5e8; border-radius: 6px; border-left: 4px solid #4caf50;">
                        <h5 style="color: #2e7d32; margin-bottom: 8px;">💡 참고사항</h5>
                        <p style="font-size: 13px; color: #2e7d32; margin: 0;">
                            부록 파일은 최신 버전으로 관리되며, 다운로드하여 확인할 수 있습니다.
                        </p>
                    </div>
                </div>
            </div>
        `;

    } catch (error) {
        console.error('Error loading appendix:', error);
        contentBody.innerHTML = `
            <div class="regulation-detail">
                <div style="text-align: center; padding: 40px;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #f44336; margin-bottom: 20px;"></i>
                    <h4 style="color: #f44336;">부록을 불러올 수 없습니다</h4>
                    <p style="color: #666; margin-top: 10px;">${error.message}</p>
                    <button onclick="history.back()" class="btn btn-secondary" style="margin-top: 20px;">
                        <i class="fas fa-arrow-left"></i> 돌아가기
                    </button>
                </div>
            </div>
        `;
    }
}

// 인쇄 기능
function old_printRegulation() {
    // 인쇄 스타일 추가
    const printStyle = document.createElement('style');
    printStyle.textContent = `
        @media print {
            body * { visibility: hidden; }
            #contentBody, #contentBody * { visibility: visible; }
            #main-content-header, #main-content-header * { visibility: visible; }  /* 페이지 헤더 추가 */
         
            /* 우측 상단 대외비 표시 */
            body::after {
                content: "대외비";
                position: fixed;
                top: 0px !important;
                right: 10px !important;
                color: #dc3545 !important;
                font-size: 12px;
                font-weight: bold;
                font-family: 'KB금융체Text', sans-serif;
                padding: 2px 6px; 
                border: 1px solid #dc3545;
                border-radius: 3px;
    
                opacity: 0.4;
            }
 
            #main-content-header {
                position: absolute;
                left: 0;
                top: 0;
                width: 100%;
                height: 90px;
                padding: 15px 20px;
                border-bottom: 1px solid #e7e6e6;
                margin-bottom: 20px;
            }
            #contentBody { 
                position: absolute; 
                left: 0; 
                top: 110px;    /* 헤더 공간 확보 */
                width: 100%; 
            }
            .regulation-actions { display: none !important; }
            .sidebar-wrapper { display: none !important; }
            .sidebar { display: none !important; }
            .header { display: none !important; }
            .footer { display: none !important; }
            
            /* 페이지 헤더 스타일 */
            /*.breadcrumb { font-size: 12px; margin-bottom: 5px; color: #666;}
            .page-title { font-size: 18px; margin-bottom: 8px; color: #2786dd;}*/
        }
    `;
    document.head.appendChild(printStyle);
    
    // 인쇄 실행
    window.print();
    
    // 인쇄 후 스타일 제거
    setTimeout(() => {
        document.head.removeChild(printStyle);
    }, 1000);
}


// 규정체계도 표시
function showRegulationHierarchy(regulation, chapter) {
    if (!regulation || !chapter) return;
    const chapterData = getChapterData(chapter);
    // 모달 생성
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">규정 체계도</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
            </div>
            <div class="modal-body">
                <div style="text-align: center; padding: 20px;">
                    <div style="border: 2px solid #1565c0; border-radius: 8px; padding: 15px; margin-bottom: 20px; background: #f0f7ff;">
                        <h4 style="color: #1565c0; margin: 0;">${chapter}</h4>
                        <p style="margin: 5px 0 0 0; color: #666;">총 ${chapterData.regulations.length}개 내규</p>
                    </div>
                    <div style="border: 3px solid #ff9800; border-radius: 8px; padding: 15px; margin-bottom: 20px; background: #fff8e1;">
                        <h4 style="color: #ff9800; margin: 0;">${regulation.code}. ${regulation.name}</h4>
                        <p style="margin: 5px 0 0 0; color: #666;">현재 보고 있는 내규</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    // 모달 외부 클릭 시 닫기
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
    showToast(`"${regulation.name}" 체계도를 표시했습니다.`, 'info');
}

// 토스트 메시지 함수
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        z-index: 10000;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    // 애니메이션
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);
    // 3초 후 제거
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}


// 부록용 sidebar active 상태 업데이트 함수
function updateSidebarActiveStateForAppendix(regulation, appendixItem, chapter, index) {
    // 먼저 기본 상태 업데이트
    updateSidebarActiveState(regulation, chapter);
    // 특정 부록 활성화
    if (index !== null) {
        const subChildren = document.querySelectorAll('.tree-sub-child');
        subChildren.forEach(subChild => {
            if (subChild.textContent.includes(appendixItem)) {
                subChild.classList.add('active');
            }
        });
    }
}

// 빠른 검색
function quickSearch() {
    const searchTerm = document.getElementById('quickSearchInput').value.trim();
    if (searchTerm) {
        alert(`"${searchTerm}" 검색 기능은 구현 예정입니다.`);
    }
}

// 분류별 내규 페이지 표시
async function showCategoryListPage() {
    if (!(await isDataLoaded())) {
        showToast('데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.', 'info');
        return;
    }

    // '분류'탭 선택 시 sidebar 숨기기
    setSidebarDisplay('none');
    document.getElementById('main-content-header').style.display = 'none';

    // 네비게이션 활성화
    updateNavigation('현행 사규');
    document.getElementById('breadcrumbActive').textContent = 'KB신용정보 내규';
    document.getElementById('pageTitle').textContent = 'KB신용정보 내규 시스템';
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';

    // 사이드바의 active 상태 초기화 (다른 탭으로 이동할 때)
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    closeSidebar();
    // 동적으로 챕터 카드들 생성 (2중 중첩 구조)
    function generateChapterCards() {
        const cards = [];
        for (const category of Object.values(hospitalRegulations)) {
            if (!category || typeof category !== 'object') continue;
            for (const [chapter, chapterData] of Object.entries(category)) {
            // regulations 배열 확인
            if (!chapterData || !Array.isArray(chapterData.regulations)) {
                continue;
            }
            
            const regulationsHTML = chapterData.regulations.map((regulation, regIndex) => {
                // regulation 객체 확인
                if (!regulation || !regulation.code || !regulation.name) {
                    console.warn(`generateChapterCards: Chapter ${chapter}, regulation ${regIndex}가 유효하지 않습니다`, regulation);
                    return '';
                }
                
                // appendix 안전성 검사 및 정규화
                let appendixArray = [];
                if (regulation.appendix) {
                    if (Array.isArray(regulation.appendix)) {
                        appendixArray = regulation.appendix;
                    } else if (typeof regulation.appendix === 'string') {
                        appendixArray = [regulation.appendix];
                        console.warn(`generateChapterCards: Chapter ${chapter}, regulation ${regulation.code}.: appendix가 문자열입니다.`);
                    } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
                        try {
                            appendixArray = Object.values(regulation.appendix).filter(item => item != null);
                            console.warn(`generateChapterCards: Chapter ${chapter}, regulation ${regulation.code}.: appendix가 객체입니다.`);
                        } catch (error) {
                            console.error(`generateChapterCards: Chapter ${chapter}, regulation ${regulation.code}.: appendix 변환 실패`, error);
                            appendixArray = [];
                        }
                    } else {
                        console.warn(`generateChapterCards: Chapter ${chapter}, regulation ${regulation.code}.: appendix가 예상치 못한 타입입니다:`, typeof regulation.appendix);
                        appendixArray = [];
                    }
                }
                
                if (appendixArray.length > 0) {
                    // 하위 부록이 있는 경우 - 토글 방식으로 표시
                    const subRegulationsHTML = appendixArray.map((appendixItem, appendixIndex) => {
                        if (typeof appendixItem !== 'string' || !appendixItem.trim()) {
                            return '';
                        }
                        
                        return `
                            <div class="regulation-chip sub-regulation" 
                                 data-chapter="${chapter}" 
                                 data-regulation-code="${regulation.code}"
                                 data-appendix-index="${appendixIndex}"
                                 onclick="event.stopPropagation(); openAppendixPdf('${regulation.code}', ${appendixIndex}, '${appendixItem.replace(/'/g, "\\'")}')">
                                <span class="reg-code">부록${appendixIndex + 1}</span>
                                <span class="reg-name">${appendixItem}</span>
                            </div>
                        `;
                    }).filter(html => html !== '').join('');
                    
                    // ✅ 수정: 메인 내규 + 숨겨진 부록들 + 토글 버튼 형태로 return
                    return `
                        <div class="regulation-group">
                            <div class="regulation-chip main-regulation" 
                                 onclick="showRegulationDetail(getChapterData('${chapter}').regulations[${regIndex}], '${chapter}')">
                                <span class="reg-code">${regulation.code}.</span>
                                <span class="reg-name">${regulation.name}</span>
                                <div class="sub-toggle" onclick="event.stopPropagation(); toggleSubRegulations(this)">
                                    <i class="fas fa-chevron-down"></i>
                                </div>
                            </div>
                            <div class="sub-regulations" style="display: none;">
                                ${subRegulationsHTML}
                            </div>
                        </div>
                    `;
                } else {
                    // 하위 부록이 없는 경우
                    return `
                        <div class="regulation-chip" 
                             onclick="showRegulationDetail(getChapterData('${chapter}').regulations[${regIndex}], '${chapter}')">
                            <span class="reg-code">${regulation.code}.</span>
                            <span class="reg-name">${regulation.name}</span>
                        </div>
                    `;
                }
            }).filter(html => html !== '').join('');
 
            // 챕터에서 번호 추출 (예: "1편 총칙" → "01", "제2편 ..." → "02")
            const chapterNumMatch = chapter.match(/(\d+)/);
            const chapterNum = chapterNumMatch ? String(chapterNumMatch[1]).padStart(2, '0') : '00';

            const cardHtml = `
                <div class="chapter-card" data-chapter="${chapter}">
                    <div class="chapter-card-header">
                        <div class="chapter-icon">
                            <span class="chapter-number">${chapterNum}</span>
                        </div>
                        <div class="chapter-info">
                            <h2>${chapter}</h2>
                            <span class="regulation-count">${chapterData.regulations.length}개 내규</span>
                        </div>
                        <div class="chapter-toggle">
                            <i class="fas fa-chevron-down"></i>
                        </div>
                    </div>
                    <div class="chapter-regulations" style="display: none;">
                        <div class="regulations-grid">
                            ${regulationsHTML}
                        </div>
                    </div>
                </div>
            `;
            cards.push(cardHtml);
            }
        }
        return cards.join('');
    }

    // 웰컴 메시지 표시
    const contentBody = document.getElementById('contentBody');
    contentBody.innerHTML = `
        <div id="welcomeMessage" class="regulation-detail">
            <div class="regulation-header" style="display:none;">
                <div style="display: flex; gap: 1.5rem; font-size: 12px; color: #666;">
                    <div>총 : 13개 장</div>
                    <div>전체 내규 수: 200여 개</div>
                    <div>마지막 업데이트: 2025.03.25</div>
                </div>
            </div>
            <div class="regulation-content">
                <div class="welcome-intro">
                    <div class="control-buttons">
                        <button id="expandAllBtn" class="control-btn" style="display: none;">
                            <i class="fas fa-expand-arrows-alt"></i> 모두 펼치기
                        </button>
                        <button id="collapseAllBtn" class="control-btn" style="display: flex;">
                            <i class="fas fa-compress-arrows-alt"></i> 모두 접기
                        </button>
                    </div>
                </div>
                <div class="chapters-gallery" id="chaptersGallery">
                    ${generateChapterCards()}
                </div>
            </div>
        </div>
    `;

    // 디폴트: 모두 펼치기 상태로 시작
    expandAllChapters();

}

// 갤러리에서 부록 상세보기를 위한 새로운 함수
function showAppendixFromGallery(chapter, regulationIndex, appendixIndex) {
    const regulation = getChapterData(chapter).regulations[regulationIndex];
    const appendixItem = regulation.appendix[appendixIndex];
    openAppendixPdf(regulation.code, appendixIndex, appendixItem);
}

// 사이드바 토글 (모바일)
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.overlay');
    const body = document.body;

    const isOpening = !sidebar.classList.contains('open');

    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');

    // ✅ 모바일에서만 iOS 호환 스크롤 방지
    if (window.innerWidth <= 768) {
        if (isOpening) {
            // 사이드바 열 때: 현재 스크롤 위치 저장 + body 고정
            const scrollY = window.scrollY;
            body.style.position = 'fixed';
            body.style.top = `-${scrollY}px`;
            body.style.width = '100%';
            body.dataset.scrollY = scrollY;  // 스크롤 위치 저장
        } else {
            // 사이드바 닫을 때: 스크롤 위치 복원
            const scrollY = parseInt(body.dataset.scrollY || '0');
            body.style.position = '';
            body.style.top = '';
            body.style.width = '';
            window.scrollTo(0, scrollY);
        }
    }
}

// 사이드바 닫기
function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.overlay');
    const body = document.body;

    sidebar.classList.remove('open');
    overlay.classList.remove('active');

    // ✅ 모바일에서만 스크롤 위치 복원
    if (window.innerWidth <= 768) {
        const scrollY = parseInt(body.dataset.scrollY || '0');
        body.style.position = '';
        body.style.top = '';
        body.style.width = '';
        window.scrollTo(0, scrollY);
    }
}

// ✅ 창 크기 변경 시 body.style 초기화 (PC 전환 시 스크롤 복구)
let resizeTimer;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
        // PC 모드로 전환되었는데 body.style이 남아있으면 초기화
        if (window.innerWidth > 768) {
            const body = document.body;
            if (body.style.position === 'fixed') {
                const scrollY = parseInt(body.dataset.scrollY || '0');
                body.style.position = '';
                body.style.top = '';
                body.style.width = '';
                window.scrollTo(0, scrollY);

                // 사이드바도 닫기
                closeSidebar();
            }
        }
    }, 250);  // 250ms 디바운스
});

// ✅ PDF 모달 표시 함수 (모바일용)
function showPdfModal(url) {
    // 파일명 추출
    const fileName = url.split('/').pop().split('?')[0];
    const decodedFileName = decodeURIComponent(fileName);

    // 모달 HTML 생성
    const modal = document.createElement('div');
    modal.className = 'pdf-modal';
    modal.innerHTML = `
        <div class="pdf-modal-header">
            <div class="pdf-modal-title"></div>
            <button class="pdf-modal-close" onclick="closePdfModal()">
                <i class="fas fa-times"></i> 닫기
            </button>
        </div>
        <iframe src="${url}" class="pdf-iframe"></iframe>
    `;

    document.body.appendChild(modal);

    // 배경 스크롤 방지 (iOS 호환 방식)
    const scrollY = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}px`;
    document.body.style.width = '100%';
    document.body.dataset.pdfScrollY = scrollY;
}

// ✅ PDF 모달 닫기 함수
function closePdfModal() {
    const modal = document.querySelector('.pdf-modal');
    if (modal) {
        modal.remove();

        // 스크롤 위치 복원
        const scrollY = parseInt(document.body.dataset.pdfScrollY || '0');
        document.body.style.position = '';
        document.body.style.top = '';
        document.body.style.width = '';
        window.scrollTo(0, scrollY);
    }
}

// Enter 키로 검색
/*
document.getElementById('quickSearchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        quickSearch();
    }
});
*/
//-- END




// 전역 변수
let currentCategory = '법인';
let currentRegulations = [
    {
        id: 1,
        name: '정확한 환자 확인',
        category: '환자안전보장활동',
        enacted: '2020.03.01',
        revised: '2024.11.15',
        content: '이 내규은 정확한 환자 확인에 관한 사항을 정함으로써 환자 안전과 의료 질 향상에 기여함을 목적으로 한다.',
        status: '시행'
    },
    {
        id: 2,
        name: '협의진료체계',
        category: '환자진료',
        enacted: '2019.09.01',
        revised: '2024.11.10',
        content: '이 내규은 협의진료체계에 관한 사항을 정함으로써 환자 안전과 의료 질 향상에 기여함을 목적으로 한다.',
        status: '시행'
    },
    {
        id: 3,
        name: '시술관리',
        category: '수술 및 마취진정관리',
        enacted: '2018.12.01',
        revised: '2024.11.05',
        content: '이 내규은 시술관리에 관한 사항을 정함으로써 환자 안전과 의료 질 향상에 기여함을 목적으로 한다.',
        status: '시행'
    },
    {
        id: 4,
        name: '진료평가',
        category: '인적자원 관리',
        enacted: '2017.03.01',
        revised: '2024.10.28',
        content: '이 내규은 진료평가에 관한 사항을 정함으로써 환자 안전과 의료 질 향상에 기여함을 목적으로 한다.',
        status: '시행'
    },
    {
        id: 5,
        name: '약어 사용',
        category: '의무기록/의료정보 관리',
        enacted: '2016.09.01',
        revised: '2024.11.01',
        content: '이 내규은 약어 사용에 관한 사항을 정함으로써 환자 안전과 의료 질 향상에 기여함을 목적으로 한다.',
        status: '시행'
    }
];

let searchResults = [];
let recentRegulations = []; // DOMContentLoaded에서 localStorage 로드
let searchHistory = [];

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    displayInitialResults();
});

// 초기 검색 결과 표시
function displayInitialResults() {
    searchResults = currentRegulations;
    //updateResultsDisplay();
}

// 검색 결과 업데이트
function updateResultsDisplay() {
    const resultCount = document.getElementById('resultCount');
    const resultsBody = document.getElementById('resultsBody');
    
    resultCount.textContent = searchResults.length;
    
    if (searchResults.length === 0) {
        resultsBody.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>검색 결과가 없습니다.</p>
            </div>
        `;
        return;
    }
    
    resultsBody.innerHTML = searchResults.map(reg => `
        <div class="result-item">
            <div class="result-title">${reg.name}</div>
            <div class="result-info">
                <span><i class="fas fa-tag"></i> ${reg.category}</span>
                <span><i class="fas fa-calendar"></i> 개정일: ${reg.revised}</span>
                <span><i class="fas fa-check-circle"></i> ${reg.status}</span>
            </div>
            <div class="result-content">${reg.content}</div>
        </div>
    `).join('');
}

// 제안 적용
function applySuggestion(suggestion) {
    document.getElementById('mainSearchInput').value = suggestion;
    performSearch();
}

// 고급 필터 토글
function toggleAdvancedFilters() {
    const filtersBody = document.getElementById('filtersBody');
    const toggleIcon = document.getElementById('filterToggleIcon');
    
    filtersBody.classList.toggle('open');
    toggleIcon.style.transform = filtersBody.classList.contains('open') ? 'rotate(180deg)' : 'rotate(0deg)';
}

// 고급 필터 적용
function applyAdvancedFilters() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const department = document.getElementById('departmentFilter').value;
    const status = document.getElementById('statusFilter').value;

    let filteredResults = currentRegulations.filter(reg => {
        let match = true;
        
        if (startDate && reg.enacted < startDate) match = false;
        if (endDate && reg.enacted > endDate) match = false;
        if (department && reg.department !== department) match = false;
        if (status && reg.status !== status) match = false;
        
        return match;
    });

    searchResults = filteredResults;
    //updateResultsDisplay();
    
    alert(`고급 필터가 적용되었습니다.\n총 ${filteredResults.length}개의 내규이 검색되었습니다.`);
}

// 트리 메뉴 토글
function toggleTreeItem(header) {
    const children = header.nextElementSibling;
    const isOpen = children.classList.contains('open');

    // 모든 트리 아이템 닫기
    document.querySelectorAll('.tree-children').forEach(child => {
        child.classList.remove('open');
    });
    document.querySelectorAll('.tree-header').forEach(h => {
        h.classList.remove('active');
    });

    // 클릭한 아이템만 열기/닫기
    if (!isOpen) {
        children.classList.add('open');
        header.classList.add('active');
    }

    // 사이드바 스크롤을 맨 위로 리셋
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.scrollTop = 0;
    }
}

// 내규 검색 (사이드바에서)
function searchRegulation(name) {
    alert(`"${name}" 검색 기능은 구현 예정입니다.`);
    updateRecentRegulations(name);
    closeSidebar();
}

// 내규 로드 (트리에서)
function loadRegulation(name) {
    // 트리 child 활성화
    document.querySelectorAll('.tree-child').forEach(child => {
        child.classList.remove('active');
    });
    if (event && event.target) {
        event.target.classList.add('active');
    }
    
    searchRegulation(name);
}

// 최근 본 내규 업데이트
function updateRecentRegulations(regulation, chapter, type = 'regulation') {
    if (!regulation || !chapter) return;
    
    let recentItem;
    
    if (type === 'appendix') {
        // 부록인 경우
        recentItem = {
            key: `부록|${regulation.parentCode}|부록${regulation.index + 1}. ${regulation.name}`,
            type: 'appendix',
            code: regulation.parentCode,
            name: `부록${regulation.index + 1}. ${regulation.name}`,
            chapter: chapter,
            chapterTitle: getChapterData(chapter)?.title || '',
            parentRegulationName: regulation.parentName || '',
            dateAccessed: new Date().toISOString()
        };
    } else {
        // 일반 내규인 경우
        recentItem = {
            key: `${chapter}|${regulation.code}|${regulation.name}`,
            type: 'regulation', 
            code: regulation.code,
            name: regulation.name,
            chapter: chapter,
            chapterTitle: getChapterData(chapter)?.title || '',
            dateAccessed: new Date().toISOString()
        };
    }
    
    // 기존에 같은 항목이 있는지 확인하여 제거
    const existingIndex = recentRegulations.findIndex(item => item.key === recentItem.key);
    if (existingIndex > -1) {
        recentRegulations.splice(existingIndex, 1);
    }
    
    // 새 항목을 맨 앞에 추가
    recentRegulations.unshift(recentItem);

    // localStorage에 저장
    safeSetStorage('recentRegulations', JSON.stringify(recentRegulations));

    // 사이드바 표시 업데이트 (카운트도 함께 업데이트)
    updateRecentRegulationsList();
}

function updateRecentRegulationsList() {
    const recentBody = document.getElementById('recentBody');
    const recentCount = document.getElementById('recentCount'); // ← 카운트 요소 추가
    
    if (!recentBody) return;
    
    if (recentRegulations.length === 0) {
        recentBody.innerHTML = `
            <div style="text-align: center; padding: 20px 10px; color: #666; font-size: 12px;">
                <i class="fas fa-history" style="font-size: 20px; color: #ddd; margin-bottom: 8px;"></i>
                <div>최근 본 내규가 없습니다</div>
            </div>
        `;
        return;
    }
    let s_recentRegulations = recentRegulations
        .filter(item => item.chapter === 'KB규정')  // KB규정만 표시 (세브란스규정 백업용 제외)
        .sort((a, b) => new Date(b.dateAccessed) - new Date(a.dateAccessed))
        .slice(0, 20);
     
    // 카운트 업데이트 추가
    if (recentCount) {
        recentCount.textContent = s_recentRegulations.length;
    }
    
    recentBody.innerHTML = s_recentRegulations.map((item, index) => {
        const timeText = getTimeAgoText(item.dateAccessed, index);
        const isAppendix = item.type === 'appendix';
        
        return `
            <div class="panel-item" onclick="openRecentRegulation('${item.key}')">
                <div>
                    <div class="item-name">
                        ${item.code}. ${item.name}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function openRecentRegulation(recentKey) {
    const recentItem = recentRegulations.find(item => item.key === recentKey);
    if (!recentItem) return;
    
    if (recentItem.type === 'appendix') {
        // 부록 열기
        const keyParts = recentItem.key.split('|');
        const regulationCode = keyParts[1];
        const appendixFullName = keyParts[2];
        
        const appendixMatch = appendixFullName.match(/^부록(\d+)\.\s*(.+)$/);
        if (appendixMatch) {
            const appendixIndex = parseInt(appendixMatch[1]) - 1;
            const appendixName = appendixMatch[2];
            openAppendixPdf(regulationCode, appendixIndex, appendixName);
        }
    } else {
        // 일반 내규 열기
        const regulation = getChapterData(recentItem.chapter)?.regulations?.find(reg =>
            reg.code === recentItem.code && reg.name === recentItem.name
        );
        
        if (regulation) {
            showRegulationDetail(regulation, recentItem.chapter);
            closeSidebar();
        } else {
            showToast('해당 내규를 찾을 수 없습니다.', 'error');
        }
    }
}

function getTimeAgoText(dateString, index) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMinutes = Math.floor((now - date) / (1000 * 60));
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (index === 0) return '방금 전';
    if (diffMinutes < 1) return '방금 전';
    if (diffMinutes < 60) return `${diffMinutes}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays === 1) return '어제';
    if (diffDays < 7) return `${diffDays}일 전`;
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${d}`;
}
// 메인 페이지 표시
function showMainPage() {
    // sidebar 보이도록
    setSidebarDisplay('');
    document.getElementById('main-content-header').style.display = 'none';


    document.getElementById('breadcrumbActive').textContent = 'KB신용정보 내규';
    document.getElementById('pageTitle').textContent = 'KB신용정보 내규 시스템';

    document.getElementById('mainPageContent').style.display = 'block';
    document.getElementById('contentBody').style.display = 'none';

    // 검색 결과 숨기고 정보 탭 복원
    const searchResultsSection = document.getElementById('searchResultsSection');
    if (searchResultsSection) searchResultsSection.style.display = 'none';
    const infoTabsSection = document.querySelector('.info-tabs-section');
    if (infoTabsSection) infoTabsSection.style.display = '';

    // 네비게이션 활성화
    updateNavigation('홈');

    // 사이드바의 active 상태 초기화 (다른 탭으로 이동할 때)
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    // 데스크톱에서만 사이드바 닫기
    if (window.innerWidth > 768) {
        closeSidebar();
    }

    // 검색어 입력란 자동 포커스
    setTimeout(() => {
        const searchInput = document.getElementById('mainSearchInput');
        if (searchInput) searchInput.focus();
    }, 100);
}

// 보기 모드 설정
let currentViewMode = 'gallery';

// AI 어시스턴트 기능들
function toggleAIChat() {
    const panel = document.getElementById('aiChatPanel');
    panel.classList.toggle('active');
}

function sendAIMessage(messageOrEvent) {
    let message;
    
    if (typeof messageOrEvent === 'string') {
        message = messageOrEvent;
    } else {
        messageOrEvent.preventDefault();
        message = document.getElementById('aiInput').value.trim();
        if (!message) return;
        document.getElementById('aiInput').value = '';
    }

    const chatBody = document.getElementById('aiChatBody');
    chatBody.innerHTML += `
        <div class="ai-message user">
            <div class="message-avatar user">
                <i class="fas fa-user"></i>
            </div>
            <div class="message-content user">${message}</div>
        </div>
    `;


    chatBody.scrollTop = chatBody.scrollHeight;
}

function performAISearch(searchTerm) {
    document.getElementById('mainSearchInput').value = searchTerm;
    showMainPage();
    performSearch();
}

// 특정 분류 내규 페이지 표시
function showCategoryPage(category) {
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    
    // 현재 카테고리 설정
    currentCategory = category;
    
    // 네비게이션 활성화
    updateNavigation('현행 사규');
    
    // 카테고리 탭 활성화
    updateCategoryTabs(category);
    
    closeSidebar();
}

// 카테고리 선택
function selectCategory(category, event) {
    if (event) {
        event.preventDefault();
    }
    showCategoryPage(category);
}


// 레이아웃 설정 불러오기
function loadLayoutSettings() {
    // initializeLocalStorage에서 이미 로드됨
    if (currentLayoutMode) {
        setLayoutMode(currentLayoutMode, false); // 저장하지 않고 적용만
    }
}

// 레이아웃 설정 패널 토글
function toggleLayoutSettings() {
    // 이벤트 기본 동작 방지
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const panel = document.getElementById('layoutSettingsPanel');
    const overlay = document.getElementById('settingsOverlay');
    
    panel.classList.add('active');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// 레이아웃 설정 패널 닫기
function closeLayoutSettings() {
    const panel = document.getElementById('layoutSettingsPanel');
    const overlay = document.getElementById('settingsOverlay');
    
    panel.classList.remove('active');
    overlay.classList.remove('active');
    document.body.style.overflow = 'auto';
}

// ========== 데스크톱 사이드바 토글 ==========
// 사이드바 접기/펼치기 핸들 동적 삽입
function initSidebarToggle() {
    if (window.innerWidth <= 768) return;

    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    // 이미 토글 버튼이 있으면 스킵
    if (document.querySelector('.sidebar-toggle-text-btn')) return;

    // wrapper가 없으면 생성
    let wrapper = document.getElementById('sidebarWrapper');
    if (!wrapper) {
        wrapper = document.createElement('div');
        wrapper.className = 'sidebar-wrapper';
        wrapper.id = 'sidebarWrapper';
        sidebar.parentNode.insertBefore(wrapper, sidebar);
        wrapper.appendChild(sidebar);
    }

    // 사이드바 헤더 영역(side-tabs)에 접기 버튼 추가
    const sideTabs = sidebar.querySelector('.side-tabs');
    if (sideTabs && !sideTabs.querySelector('.sidebar-toggle-text-btn')) {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'sidebar-toggle-text-btn';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-left"></i> 접기';
        toggleBtn.onclick = function(e) { e.stopPropagation(); toggleDesktopSidebar(); };
        sideTabs.appendChild(toggleBtn);
    }

    // 접힌 상태에서 열기 플로팅 버튼 추가
    if (!wrapper.querySelector('.sidebar-open-float')) {
        const floatBtn = document.createElement('button');
        floatBtn.className = 'sidebar-open-float';
        floatBtn.innerHTML = '<i class="fas fa-chevron-right"></i> 열기';
        floatBtn.onclick = toggleDesktopSidebar;
        wrapper.appendChild(floatBtn);
    }

    // 저장된 접힘 상태 복원
    restoreDesktopSidebarState();
}

function toggleDesktopSidebar() {
    const wrapper = document.getElementById('sidebarWrapper');
    if (!wrapper) return;

    const isCollapsed = wrapper.classList.toggle('collapsed');
    safeSetStorage('sidebarCollapsed', isCollapsed ? '1' : '0');

    // 헤더 내 접기/열기 버튼 텍스트 업데이트
    const toggleBtn = wrapper.querySelector('.sidebar-toggle-text-btn');
    if (toggleBtn) {
        toggleBtn.innerHTML = isCollapsed
            ? '<i class="fas fa-chevron-right"></i> 열기'
            : '<i class="fas fa-chevron-left"></i> 접기';
    }
}

function restoreDesktopSidebarState() {
    const wrapper = document.getElementById('sidebarWrapper');
    if (!wrapper || window.innerWidth <= 768) return;

    const saved = safeGetStorage('sidebarCollapsed');
    if (saved === '1') {
        wrapper.classList.add('collapsed');
        // 접기 버튼 텍스트도 업데이트
        const toggleBtn = wrapper.querySelector('.sidebar-toggle-text-btn');
        if (toggleBtn) {
            toggleBtn.innerHTML = '<i class="fas fa-chevron-right"></i> 열기';
        }
    }
}

// 레이아웃 모드 설정
function setLayoutMode(mode, saveToStorage = true) {
    document.body.classList.remove('layout-mode-1', 'layout-mode-2', 'layout-mode-3');
    document.body.classList.add(`layout-mode-${mode}`);

    document.querySelectorAll('.layout-option').forEach(option => {
        option.classList.remove('active');
        if (parseInt(option.dataset.layout) === mode) {
            option.classList.add('active');
        }
    });

    const sidebarWrapper = document.getElementById('sidebarWrapper');

    if (window.innerWidth > 768) {
        if (mode === 1) {
            if (sidebarWrapper) sidebarWrapper.style.display = 'none';
        } else {
            if (sidebarWrapper) sidebarWrapper.style.display = '';
            restoreDesktopSidebarState();
        }
    } else {
        if (sidebarWrapper) sidebarWrapper.style.display = '';
    }

    currentLayoutMode = mode;

    if (saveToStorage) {
        safeSetStorage('layoutMode', mode.toString());
    }
}

// 네비게이션 업데이트
function updateNavigation(activeTab) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');

        const linkText = link.textContent.trim();
        if (linkText === activeTab) {
            link.classList.add('active');
        }
    });
}

// 카테고리 탭 업데이트
function updateCategoryTabs(category) {
    document.querySelectorAll('.category-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    const activeTab = Array.from(document.querySelectorAll('.category-tab')).find(tab => 
        tab.onclick.toString().includes(`'${category}'`)
    );
    if (activeTab) {
        activeTab.classList.add('active');
    }
}

// 모달 닫기
function closeModal() {
    document.getElementById('detailModal').style.display = 'none';
}

// 챕터 카드 클릭 이벤트 (이벤트 위임 방식)
document.addEventListener('click', function(e) {
    // 챕터 카드 헤더 클릭
    if (e.target.closest('.chapter-card-header')) {
        const header = e.target.closest('.chapter-card-header');
        const card = header.closest('.chapter-card');
        toggleChapterCard(card);
    }
    // 하위 내규 토글 클릭
    if (e.target.closest('.sub-toggle')) {
        const toggleBtn = e.target.closest('.sub-toggle');
        toggleSubRegulations(toggleBtn);
    } 
   
    // 모두 펼치기 버튼 클릭
    if (e.target.closest('#expandAllBtn')) {
        expandAllChapters();
    }
    
    // 모두 접기 버튼 클릭
    if (e.target.closest('#collapseAllBtn')) {
        collapseAllChapters();
    }
    // 부록 클릭 이벤트 추가
    if (e.target.closest('.sub-regulation')) {
        e.stopPropagation(); // 상위 이벤트 전파 방지
        const subRegulation = e.target.closest('.sub-regulation');
        const regulationGroup = subRegulation.closest('.regulation-group');
        const mainRegulation = regulationGroup.querySelector('.main-regulation');
        // 데이터 속성에서 정보 추출
        const chapter = subRegulation.dataset.chapter;
        const regulationCode = subRegulation.dataset.regulationCode;
        const appendixIndex = parseInt(subRegulation.dataset.appendixIndex);
        const appendixName = subRegulation.querySelector('.reg-name').textContent;
        // 해당 내규 찾기
        const regulation = getChapterData(chapter).regulations.find(reg => reg.code === regulationCode);
        if (regulation) {
            showAppendixDetail(regulation, appendixName, chapter, appendixIndex);
        }
    }
});

// 개별 챕터 카드 토글
function toggleChapterCard(card) {
    if (!card) return;
    
    const regulations = card.querySelector('.chapter-regulations');
    const isExpanded = card.classList.contains('expanded');
    
    if (isExpanded) {
        // 접기
        card.classList.remove('expanded');
        regulations.style.display = 'none';
    } else {
        // 펼치기
        card.classList.add('expanded');
        regulations.style.display = 'block';
    }
}
// 하위 내규 토글 함수
function toggleSubRegulations(toggleBtn) {
    const regulationGroup = toggleBtn.closest('.regulation-group');
    const mainRegulation = regulationGroup.querySelector('.main-regulation');
    const subRegulations = regulationGroup.querySelector('.sub-regulations');
    const isExpanded = toggleBtn.classList.contains('expanded');
    
    if (isExpanded) {
        // 접기
        toggleBtn.classList.remove('expanded');
        mainRegulation.classList.remove('expanded');
        subRegulations.style.display = 'none';
        subRegulations.classList.remove('show');
    } else {
        // 펼치기
        toggleBtn.classList.add('expanded');
        mainRegulation.classList.add('expanded');
        subRegulations.style.display = 'flex';
        subRegulations.classList.add('show');
    }
}

// 모든 챕터 펼치기
function expandAllChapters() {
    const chapterCards = document.querySelectorAll('.chapter-card');
    const expandBtn = document.getElementById('expandAllBtn');
    const collapseBtn = document.getElementById('collapseAllBtn');
    
    chapterCards.forEach(card => {
        const regulations = card.querySelector('.chapter-regulations');
        if (regulations) {
            card.classList.add('expanded');
            regulations.style.display = 'block';
            
            // 하위 내규들도 모두 펼치기
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
    
    // 버튼 표시 전환
    if (expandBtn) expandBtn.style.display = 'none';
    if (collapseBtn) collapseBtn.style.display = 'flex';
}

// 모든 챕터 접기
function collapseAllChapters() {
    const chapterCards = document.querySelectorAll('.chapter-card');
    const expandBtn = document.getElementById('expandAllBtn');
    const collapseBtn = document.getElementById('collapseAllBtn');
    
    chapterCards.forEach(card => {
        const regulations = card.querySelector('.chapter-regulations');
        if (regulations) {
            card.classList.remove('expanded');
            regulations.style.display = 'none';
            
            // 하위 내규들도 모두 접기
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
    
    // 버튼 표시 전환
    if (expandBtn) expandBtn.style.display = 'flex';
    if (collapseBtn) collapseBtn.style.display = 'none';
}

// 챕터별 내규 개수 업데이트 (실제 데이터 기반)
function updateRegulationCounts() {
    const chapterData = {
        '1장': 9,
        '2장': 25,
        '3장': 18,
        '4장': 12,
        '5장': 8,
        '6장': 15,
        '7장': 10,
        '8장': 12,
        '9장': 14,
        '10장': 16,
        '11장': 20,
        '12장': 8,
        '13장': 6
    };
    
    Object.keys(chapterData).forEach(chapter => {
        const card = document.querySelector(`[data-chapter="${chapter}"]`);
        if (card) {
            const countSpan = card.querySelector('.regulation-count');
            if (countSpan) {
                countSpan.textContent = `${chapterData[chapter]}개 내규`;
            }
        }
    });
}
// 현재 보고 있는 내규를 새창으로 열기
function openInNewWindow() {
    if (currentRegulation && currentChapter) {
        const chapterData = getChapterData(currentChapter);
        openRegulationInNewWindow(currentRegulation, currentChapter, chapterData?.title || '');
    }
}

// ========== 즐겨찾기 관련 함수들 ==========

// ----------- 잘못된 구조 해결용 -----------
// 즐겨찾기 데이터 유효성 검사 함수
function isValidFavoriteItem(item) {
    // 기본 구조 확인
    if (!item || typeof item !== 'object') {
        return false;
    }
    
    // 필수 필드 확인
    const requiredFields = ['key', 'chapter', 'chapterTitle', 'code', 'name', 'dateAdded', 'department'];
    
    for (let field of requiredFields) {
        if (!item.hasOwnProperty(field) || item[field] === undefined || item[field] === null) {
            return false;
        }
    }
    
    // 문자열 필드 확인
    const stringFields = ['key', 'chapter', 'chapterTitle', 'code', 'name', 'department'];
    for (let field of stringFields) {
        if (typeof item[field] !== 'string' || item[field].trim() === '') {
            return false;
        }
    }
    
    // dateAdded가 유효한 ISO 날짜 문자열인지 확인
    if (typeof item.dateAdded !== 'string' || isNaN(Date.parse(item.dateAdded))) {
        return false;
    }
    
    // key 형식 확인 (예: "3장|3.1.1.1|입원환자 치료계획" 또는 "부록|11.8.1|부록1. ...")
    const keyParts = item.key.split('|');
    if (keyParts.length !== 3) {
        return false;
    }
    
    // chapter 형식 확인 (예: "3장" 또는 부록의 경우는 예외)
    if (!item.chapter.includes('장') && !item.key.startsWith('부록|')) {
        return false;
    }
    
    return true;
}

// 즐겨찾기 배열 정리 함수
function cleanupFavoriteRegulations() {
    const originalLength = favoriteRegulations.length;
    
    // 유효한 항목만 필터링
    favoriteRegulations = favoriteRegulations.filter(item => {
        const isValid = isValidFavoriteItem(item);
        
        // 디버깅용 로그 (개발 중에만 사용)
        if (!isValid && window.location.hostname === 'localhost') {
            console.warn('잘못된 즐겨찾기 항목 제거:', item);
        }
        
        return isValid;
    });
    
    // 정리 결과 로그
    if (originalLength !== favoriteRegulations.length) {
        console.log(`즐겨찾기 정리 완료: ${originalLength}개 → ${favoriteRegulations.length}개`);

        // localStorage 업데이트
        safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
    }

    return favoriteRegulations;
}

// 기존 문자열 형태의 즐겨찾기를 새 구조로 마이그레이션하는 함수
function migrateLegacyFavorites() {
    let needsMigration = false;
    
    favoriteRegulations = favoriteRegulations.map(item => {
        // 문자열 형태의 기존 데이터인지 확인
        if (typeof item === 'string') {
            needsMigration = true;
            
            // 기존 형태: "1장-1.1.1." 또는 "1장|1.1.1|내규명"
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
                // 파싱 불가능한 경우 건너뛰기
                return null;
            }
            
            // 새 구조로 변환
            return {
                key: `${chapter}|${code}|${name}`,
                chapter: chapter,
                chapterTitle: getChapterData(chapter)?.title || '장제목 미상',
                code: code,
                name: name,
                dateAdded: new Date().toISOString(),
                department: '소관부서 미지정'
            };
        }
        
        return item;
    }).filter(item => item !== null); // null인 항목 제거
    
    if (needsMigration) {
        console.log('기존 즐겨찾기 데이터 마이그레이션 완료');
        safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
    }

    return favoriteRegulations;
}

// ----------- 잘못된 구조 해결용 -----------


// 즐겨찾기 토글 함수 (기존 함수 수정)
function toggleFavorite(regulation, chapter) {
    if (!regulation || !chapter) return;
    
    const favoriteKey = `${chapter}|${regulation.code}|${regulation.name}`;
    const index = favoriteRegulations.findIndex(fav => fav.key === favoriteKey);
    const favoriteBtn = document.querySelector('.regulation-actions .action-btn[data-tooltip="즐겨찾기"]') ||
                       document.querySelector('.page-actions .action-btn[data-tooltip="즐겨찾기"]');

    if (index > -1) {
        // 즐겨찾기에서 제거
        favoriteRegulations.splice(index, 1);
        if (favoriteBtn) favoriteBtn.classList.remove('active');
        showToast(`"${regulation.name}"이(가) 즐겨찾기에서 제거되었습니다.`, 'info');
    } else {
        // 즐겨찾기에 추가
        const favoriteItem = {
            key: favoriteKey,
            chapter: chapter,
            chapterTitle: getChapterData(chapter)?.title || '',
            code: regulation.code,
            name: regulation.name,
            dateAdded: new Date().toISOString(),
            department: regulation.detail?.documentInfo?.['소관부서'] || '소관부서 미지정'
        };
        favoriteRegulations.push(favoriteItem);
        if (favoriteBtn) favoriteBtn.classList.add('active');
        showToast(`"${regulation.name}"이(가) 즐겨찾기에 추가되었습니다.`, 'success');
    }

    // localStorage에 저장
    safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));

    // 사이드바 및 즐겨찾기 페이지 업데이트
    updateFavoritesList();
    
    // 현재 즐겨찾기 페이지가 열려있다면 업데이트
    if (document.getElementById('contentBody').style.display !== 'none' && 
        document.querySelector('.favorites-page')) {
        displayFavoritesContent();
    }
}

// 즐겨찾기 여부 확인 함수 (기존 함수 수정)
function isFavorite(regulation, chapter) {
    if (!regulation || !chapter) return false;
    const favoriteKey = `${chapter}|${regulation.code}|${regulation.name}`;
    return favoriteRegulations.some(fav => fav.key === favoriteKey);
}

// 사이드바 즐겨찾기 목록 업데이트 함수 (기존 함수 수정)
function updateFavoritesList() {
    const favoritesBody = document.getElementById('favoritesBody');
    const favoritesCount = document.getElementById('favoritesCount');
    
    if (!favoritesBody || !favoritesCount) return;
   
    // 표시하기 전에 데이터 정리
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
    
    // 최근 추가된 순으로 정렬
    const recentFavorites = favoriteRegulations
        .filter(favorite => isValidFavoriteItem(favorite)) // NEW: 한 번 더 검증
        .sort((a, b) => new Date(b.dateAdded) - new Date(a.dateAdded));
    
    favoritesBody.innerHTML = recentFavorites.map(favorite => {
        // 부록인지 확인하여 아이콘 변경
        const isAppendix = favorite.key.startsWith('부록|');
        
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

// 사이드바에서 즐겨찾기 제거
function removeFavoriteFromSidebar(event, favoriteKey) {
    event.stopPropagation();
    
    const index = favoriteRegulations.findIndex(fav => fav.key === favoriteKey);
    if (index > -1) {
        const favorite = favoriteRegulations[index];
        favoriteRegulations.splice(index, 1);
        safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
        updateFavoritesList();
        
        // 현재 보고 있는 내규가 제거된 즐겨찾기라면 버튼 상태 업데이트
        if (currentRegulation && currentChapter) {
            const currentKey = `${currentChapter}|${currentRegulation.code}|${currentRegulation.name}`;
            if (currentKey === favoriteKey) {
                const favoriteBtn = document.querySelector('.regulation-actions .action-btn[data-tooltip="즐겨찾기"]') ||
                                   document.querySelector('.page-actions .action-btn[data-tooltip="즐겨찾기"]');
                if (favoriteBtn) favoriteBtn.classList.remove('active');
            }
        }
        
        showToast(`"${favorite.name}"이(가) 즐겨찾기에서 제거되었습니다.`, 'info');
        
        // 즐겨찾기 페이지가 열려있다면 업데이트
        if (document.getElementById('contentBody').style.display !== 'none' && 
            document.querySelector('.favorites-page')) {
            displayFavoritesContent();
        }
    }
}

// 사이드바에서 즐겨찾기 내규 열기 (기존 함수 수정)
function openFavoriteRegulation(favoriteKey) {
    const favorite = favoriteRegulations.find(fav => fav.key === favoriteKey);
    if (!favorite) return;
    
    // 부록인지 확인 (키가 "부록|"으로 시작하는지 체크)
    if (favorite.key.startsWith('부록|')) {
        // 부록 처리
        openFavoriteAppendix(favorite);
    } else {
        // 기존 내규 처리
        const regulation = getChapterData(favorite.chapter)?.regulations?.find(reg =>
            reg.code === favorite.code && reg.name === favorite.name
        );

        if (regulation) {
            showRegulationDetail(regulation, favorite.chapter);
            closeSidebar();
        } else {
            showToast('해당 내규를 찾을 수 없습니다.', 'error');
        }
    }
}

// 즐겨찾기 페이지에서 내규 열기 (기존 함수 수정)
function openFavoriteRegulationFromPage(favoriteKey) {
    const favorite = favoriteRegulations.find(fav => fav.key === favoriteKey);
    if (!favorite) return;
    
    // 부록인지 확인
    if (favorite.key.startsWith('부록|')) {
        // 부록 처리
        openFavoriteAppendix(favorite);
    } else {
        // 기존 내규 처리
        const regulation = getChapterData(favorite.chapter)?.regulations?.find(reg =>
            reg.code === favorite.code && reg.name === favorite.name
        );

        if (regulation) {
            showRegulationDetail(regulation, favorite.chapter);
        } else {
            showToast('해당 내규를 찾을 수 없습니다.', 'error');
        }
    }
}

// 즐겨찾기된 부록 열기 함수
function openFavoriteAppendix(favorite) {
    // 즐겨찾기 키에서 정보 추출: "부록|1.2.1|부록1. 구두처방 의약품 목록"
    const keyParts = favorite.key.split('|');
    if (keyParts.length !== 3) {
        showToast('부록 정보를 파싱할 수 없습니다.', 'error');
        return;
    }
    
    const regulationCode = keyParts[1];  // 1.2.1
    const appendixFullName = keyParts[2]; // 부록1. 구두처방 의약품 목록
    
    // 부록 번호와 이름 분리
    const appendixMatch = appendixFullName.match(/^부록(\d+)\.\s*(.+)$/);
    if (!appendixMatch) {
        showToast('부록 이름을 파싱할 수 없습니다.', 'error');
        return;
    }
    
    const appendixIndex = parseInt(appendixMatch[1]) - 1; // 부록1 -> 인덱스 0
    const appendixName = appendixMatch[2]; // 구두처방 의약품 목록
    
    // PDF 열기
    openAppendixPdf(regulationCode, appendixIndex, appendixName);
    
    console.log(`즐겨찾기 부록 열기: ${regulationCode}, 인덱스: ${appendixIndex}, 이름: ${appendixName}`);
}

// 즐겨찾기 페이지 표시
function showFavoritesPage() {
    // 사이드바 표시
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';

    // 네비게이션 활성화
    updateNavigation('홈');

    // 사이드바의 active 상태 초기화 (다른 탭으로 이동할 때)
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    // 즐겨찾기 페이지 내용 생성
    displayFavoritesPage();

    // 데스크톱에서는 사이드바 닫기
    if (window.innerWidth > 768) {
        closeSidebar();
    }

}

// 즐겨찾기 페이지 내용 표시
function displayFavoritesPage() {
    const contentBody = document.getElementById('contentBody');
    
    contentBody.innerHTML = `
        <div class="favorites-page">
            <div class="favorites-controls">
                <div class="favorites-search">
                    <input type="text" id="favoritesSearchInput" placeholder="즐겨찾기에서 검색..." onkeyup="filterFavorites(this.value)">
                    <i class="fas fa-search"></i>
                </div>
                <div class="favorites-actions">
                    <button class="favorites-btn danger" onclick="clearAllFavorites()">
                        <i class="fas fa-trash"></i>
                        전체 삭제
                    </button>
                </div>
            </div>
            
            <div class="favorites-content" id="favoritesContent">
                <!-- 동적으로 생성됨 -->
            </div>
        </div>
    `;
    
    displayFavoritesContent();
}

// 즐겨찾기 내용 표시
function displayFavoritesContent() {
    const favoritesContent = document.getElementById('favoritesContent');
    if (!favoritesContent) return;
    
    if (favoriteRegulations.length === 0) {
        favoritesContent.innerHTML = `
            <div class="favorites-empty">
                <i class="fas fa-star"></i>
                <h3>즐겨찾기가 비어있습니다</h3>
                <p>
                    자주 사용하는 내규를 즐겨찾기에 추가해보세요.
                </p>
            </div>
        `;
        return;
    }
    
    // 사용할 즐겨찾기 목록 (필터링된 것이 있으면 사용)
    const favoritesToShow = filteredFavorites.length > 0 ? filteredFavorites : favoriteRegulations;
    
    // 챕터별로 그룹화
    const groupedFavorites = favoritesToShow.reduce((groups, favorite) => {
        const chapterKey = `${favorite.chapter}. ${favorite.chapterTitle}`;
        if (!groups[chapterKey]) {
            groups[chapterKey] = {
                chapter: favorite.chapter,
                chapterTitle: favorite.chapterTitle,
                items: []
            };
        }
        groups[chapterKey].items.push(favorite);
        return groups;
    }, {});
    
    // 챕터 순서대로 정렬
    const sortedGroups = Object.keys(groupedFavorites).sort().map(key => groupedFavorites[key]);
    
    let html = '';
    
    sortedGroups.forEach(group => {
        // 각 그룹 내에서 코드 순으로 정렬
        group.items.sort((a, b) => a.code.localeCompare(b.code));
        
        html += `
            <div class="favorites-chapter-group">
                <div class="favorites-chapter-header">
                    <div class="favorites-chapter-title">
                        ${group.chapter}. ${group.chapterTitle}
                    </div>
                    <div class="favorites-chapter-count">${group.items.length}개</div>
                </div>
                <div class="favorites-regulations">
                    ${group.items.map(favorite => {
                        // 부록인지 확인하여 아이콘과 스타일 변경
                        const isAppendix = favorite.key.startsWith('부록|');
                        
                        return `
                            <div class="favorite-regulation-item" data-key="${favorite.key}">
                                <div class="favorite-regulation-main" onclick="openFavoriteRegulationFromPage('${favorite.key}')">
                                    <span class="favorite-regulation-code">
                                        ${favorite.code}.
                                    </span>
                                    <div class="favorite-regulation-info">
                                        <div class="favorite-regulation-name">${favorite.name}</div>
                                        <div class="favorite-regulation-meta">
                                            <span>${favorite.department}</span>
                                            <span>${formatDate(favorite.dateAdded)}</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="favorite-regulation-actions">
                                    <button class="favorite-action-btn remove" onclick="removeFavoriteFromPage('${favorite.key}')" title="즐겨찾기 제거">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    });
    
    favoritesContent.innerHTML = html;
}

// 날짜 포맷팅 (yyyy-mm-dd)
function formatDate(dateString) {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString || '-';
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

// 즐겨찾기 페이지에서 제거
function removeFavoriteFromPage(favoriteKey) {
    const favorite = favoriteRegulations.find(fav => fav.key === favoriteKey);
    if (!favorite) return;
    
    if (confirm(`"${favorite.name}"을(를) 즐겨찾기에서 제거하시겠습니까?`)) {
        const index = favoriteRegulations.findIndex(fav => fav.key === favoriteKey);
        if (index > -1) {
            favoriteRegulations.splice(index, 1);
            safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
            updateFavoritesList();
            displayFavoritesContent();
            showToast(`"${favorite.name}"이(가) 즐겨찾기에서 제거되었습니다.`, 'info');
        }
    }
}

// 즐겨찾기 검색 필터링
function filterFavorites(searchTerm) {
    if (!searchTerm.trim()) {
        filteredFavorites = [];
    } else {
        const term = searchTerm.toLowerCase();
        filteredFavorites = favoriteRegulations.filter(favorite => 
            favorite.name.toLowerCase().includes(term) ||
            favorite.code.toLowerCase().includes(term) ||
            favorite.chapterTitle.toLowerCase().includes(term) ||
            favorite.department.toLowerCase().includes(term)
        );
    }
    displayFavoritesContent();
}

// 선택된 항목 수 업데이트
function updateBulkSelection() {
    if (!isBulkSelectionMode) return;
    
    const selectedCheckboxes = document.querySelectorAll('.favorite-checkbox:checked');
    const selectedCount = document.getElementById('selectedCount');
    if (selectedCount) {
        selectedCount.textContent = selectedCheckboxes.length;
    }
}

// 전체 즐겨찾기 삭제
function clearAllFavorites() {
    if (favoriteRegulations.length === 0) {
        showToast('삭제할 즐겨찾기가 없습니다.', 'info');
        return;
    }
    
    if (confirm(`모든 즐겨찾기(${favoriteRegulations.length}개)를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
        favoriteRegulations = [];
        safeSetStorage('favoriteRegulations', JSON.stringify(favoriteRegulations));
        updateFavoritesList();
        displayFavoritesContent();
        showToast('모든 즐겨찾기가 삭제되었습니다.', 'info');
    }
}

// ========== 개정이력 관련 함수들 ==========

// 개정이력 페이지 표시
async function showRevisionHistoryPage() {
    if (!(await isDataLoaded())) {
        showToast('데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.', 'info');
        return;
    }

    // 사이드바 표시
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';

    // 네비게이션 활성화
    updateNavigation('사규 제·개정');

    // 사이드바의 active 상태 초기화 (다른 탭으로 이동할 때)
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    // 개정이력 페이지 내용 생성
    displayRevisionHistoryPage();

    // 데스크톱에서는 사이드바 닫기
    if (window.innerWidth > 768) {
        closeSidebar();
    }

}

// 외규 제·개정 페이지 표시
function showExternalRevisionPage() {
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';

    updateNavigation('외규 제·개정');

    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    const contentBody = document.getElementById('contentBody');
    contentBody.innerHTML = `
        <div style="padding: 40px 20px; text-align: center;">
            <i class="fas fa-file-alt" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
            <h3 style="color: #666; margin-bottom: 8px;">외규 제·개정</h3>
            <p style="color: #999;">준비 중입니다.</p>
        </div>
    `;

    if (window.innerWidth > 768) {
        closeSidebar();
    }
}

function displayRevisionHistoryPage() {
    const contentBody = document.getElementById('contentBody');
    
    contentBody.innerHTML = `
        <div class="revision-history-page">
            <!-- 뷰 전환 탭 추가 -->
            <div class="revision-view-tabs" style="display:none;">
                <button class="revision-view-tab active" onclick="switchRevisionView('list')">
                    <i class="fas fa-list"></i> 목록형
                </button>
                <button class="revision-view-tab" onclick="switchRevisionView('calendar')">
                    <i class="fas fa-calendar-alt"></i> 캘린더형
                </button>
            </div>

            <!-- 기존 목록형 뷰 -->
            <div class="revision-list-view" id="revisionListView">
                <div class="revision-controls">
                    <div class="revision-search">
                        <input type="text" id="revisionSearchInput" placeholder="내규명으로 검색..." onkeyup="filterRevisionHistory(this.value)">
                        <i class="fas fa-search"></i>
                    </div>
                    <div class="revision-sort">
                        <select id="revisionSortSelect" onchange="sortRevisionHistory(this.value)">
                            <option value="chapter-asc">챕터 순서</option>
                            <option value="name-asc">내규명 가나다순</option>
                        </select>
                    </div>
                </div>
               
                <div class="revision-content" id="revisionContent">
                    <!-- 기존 목록 내용 -->
                </div>
            </div>

            <!-- 새로운 캘린더형 뷰 -->
            <div class="revision-calendar-view" id="revisionCalendarView" style="display: none;">
                <div class="revision-calendar">
                    <div class="calendar-header">
                        <button class="calendar-nav-btn" onclick="changeMonth(-1)">
                            <i class="fas fa-chevron-left"></i>
                        </button>
                        <div class="calendar-title" id="calendarTitle">2025년 8월</div>
                        <button class="calendar-nav-btn" onclick="changeMonth(1)">
                            <i class="fas fa-chevron-right"></i>
                        </button>
                    </div>
                    
                    <div class="calendar-grid" id="calendarGrid">
                        <!-- 캘린더 그리드가 여기에 동적으로 생성됨 -->
                    </div>
                </div>
            </div>
        </div>

        <!-- 날짜별 상세보기 모달 -->
        <div class="revision-detail-modal" id="revisionDetailModal">
            <div class="revision-detail-content">
                <div class="revision-detail-header">
                    <div class="revision-detail-title" id="revisionDetailTitle">개정내규 상세</div>
                    <button class="revision-detail-close" onclick="closeRevisionDetailModal()">×</button>
                </div>
                <div class="revision-detail-body" id="revisionDetailBody">
                    <!-- 테이블이 여기에 동적으로 생성됨 -->
                </div>
            </div>
        </div>
    `;
    
    displayRevisionHistoryContent();
}

// ========== 캘린더 뷰 관련 함수들 ==========

// 캘린더 관련 전역 변수
let currentCalendarDate = new Date();
let revisionDataByDate = {};

// 뷰 전환 함수
function switchRevisionView(viewType) {
    const tabs = document.querySelectorAll('.revision-view-tab');
    const listView = document.getElementById('revisionListView');
    const calendarView = document.getElementById('revisionCalendarView');
    
    tabs.forEach(tab => tab.classList.remove('active'));
    
    if (viewType === 'list') {
        document.querySelector('.revision-view-tab').classList.add('active');
        listView.style.display = 'block';
        calendarView.style.display = 'none';
    } else {
        document.querySelectorAll('.revision-view-tab')[1].classList.add('active');
        listView.style.display = 'none';
        calendarView.style.display = 'block';
        generateCalendar();
    }
}

// 캘린더 생성 함수
function generateCalendar() {
    const calendarGrid = document.getElementById('calendarGrid');
    const calendarTitle = document.getElementById('calendarTitle');
    
    if (!calendarGrid || !calendarTitle) return;
    
    const year = currentCalendarDate.getFullYear();
    const month = currentCalendarDate.getMonth();
    
    calendarTitle.textContent = `${year}년 ${month + 1}월`;
    
    // 캘린더 그리드 초기화
    calendarGrid.innerHTML = '';
    
    // 요일 헤더 생성
    const dayHeaders = ['일', '월', '화', '수', '목', '금', '토'];
    dayHeaders.forEach(day => {
        const dayHeader = document.createElement('div');
        dayHeader.className = 'calendar-day-header';
        dayHeader.textContent = day;
        calendarGrid.appendChild(dayHeader);
    });
    
    // 해당 월의 첫째 날과 마지막 날
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    // 6주간의 날짜 생성 (42일)
    for (let i = 0; i < 42; i++) {
        const currentDate = new Date(startDate);
        currentDate.setDate(startDate.getDate() + i);
        
        const dayElement = createCalendarDay(currentDate, month);
        calendarGrid.appendChild(dayElement);
    }
}

// 캘린더 일자 엘리먼트 생성
function createCalendarDay(date, currentMonth) {
    const dayElement = document.createElement('div');
    dayElement.className = 'calendar-day';
    
    const isOtherMonth = date.getMonth() !== currentMonth;
    const isTodayDate = isTodayCheck(date);
    const dateString = formatDateForComparison(date);
    const revisions = getRevisionsForDate(dateString);
    
    if (isOtherMonth) {
        dayElement.classList.add('other-month');
    }
    if (isTodayDate) {
        dayElement.classList.add('today');
    }
    if (revisions.length > 0) {
        dayElement.classList.add('has-revision');
    }
    
    const dayNumber = document.createElement('div');
    dayNumber.className = 'day-number';
    dayNumber.textContent = date.getDate();
    dayElement.appendChild(dayNumber);
    
    if (revisions.length > 0) {
        const indicator = document.createElement('div');
        indicator.className = 'revision-indicator';
        indicator.innerHTML = `개정 <span class="revision-count">${revisions.length}</span>`;
        dayElement.appendChild(indicator);
    }
    
    // 클릭 이벤트 추가
    dayElement.addEventListener('click', () => {
        if (revisions.length > 0) {
            showRevisionDetailModal(date, revisions);
        }
    });
    
    return dayElement;
}

// 오늘 날짜 확인 (함수명 충돌 방지)
function isTodayCheck(date) {
    const today = new Date();
    return date.toDateString() === today.toDateString();
}

// 날짜를 비교용 문자열로 변환
function formatDateForComparison(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}`;
}

// 특정 날짜의 개정내규 조회
function getRevisionsForDate(dateString) {
    return revisionDataByDate[dateString] || [];
}

// 월 변경
function changeMonth(delta) {
    currentCalendarDate.setMonth(currentCalendarDate.getMonth() + delta);
    generateCalendar();
}

// 개정내규 데이터를 날짜별로 인덱싱
function indexRevisionsByDate(regulations) {
    revisionDataByDate = {};
    
    regulations.forEach(regulation => {
        const dateString = regulation.revisionDate;
        if (!revisionDataByDate[dateString]) {
            revisionDataByDate[dateString] = [];
        }
        revisionDataByDate[dateString].push(regulation);
    });
}

// 날짜별 상세보기 모달 표시
function showRevisionDetailModal(date, revisions) {
    const modal = document.getElementById('revisionDetailModal');
    const title = document.getElementById('revisionDetailTitle');
    const body = document.getElementById('revisionDetailBody');
    
    if (!modal || !title || !body) return;
    
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    
    title.textContent = `${year}년 ${month}월 ${day}일 개정내규 (${revisions.length}건)`;
    
    // 테이블 생성
    let tableHTML = `
        <table class="revision-table">
            <thead>
                <tr>
                    <th style="width: 80px;">내규번호</th>
                    <th>내규명</th>
                    <th style="width: 120px;">소속 장</th>
                    <th style="width: 100px;">소관부서</th>
                    <th style="width: 80px;">제정일</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    revisions.forEach(revision => {
        tableHTML += `
            <tr onclick="openComparisonTablePdf('${revision.code}', '${revision.name}', ${revision.wzRuleSeq || 'null'})" style="cursor: pointer;">
                <td><span class="regulation-code">${revision.code}</span></td>
                <td><a href="#" class="regulation-link">${revision.name}</a></td>
                <td>${revision.chapter}. ${revision.chapterTitle}</td>
                <td>${revision.department}</td>
                <td>${revision.enactmentDate || '-'}</td>
            </tr>
        `;
    });
    
    tableHTML += '</tbody></table>';
    body.innerHTML = tableHTML;
    
    modal.style.display = 'flex';
}

// 모달 닫기
function closeRevisionDetailModal() {
    const modal = document.getElementById('revisionDetailModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 개정이력 내용 표시
function displayRevisionHistoryContent() {
    const revisionContent = document.getElementById('revisionContent');
    if (!revisionContent) return;
    
    // 전역 변수에서 데이터 가져오기
    if (allRevisionData.length === 0) {
        // 데이터가 없으면 수집
        collectAllRegulations();
    }
    
    if (filteredRevisionData.length === 0) {
        revisionContent.innerHTML = `
            <div class="revision-empty">
                <i class="fas fa-history"></i>
                <h3>검색 결과가 없습니다</h3>
                <p>검색 조건을 확인해주세요.</p>
            </div>
        `;
        return;
    }
    
    // 일자별로 그룹핑
    const groupedByDay = groupRevisionsByDay(filteredRevisionData);
    
    let html = '';
    
    Object.keys(groupedByDay).sort((a, b) => new Date(b) - new Date(a)).forEach(dayKey => {
        const dayData = groupedByDay[dayKey];
        const dayDate = new Date(dayKey);
        const dayLabel = `${dayDate.getFullYear()}년 ${dayDate.getMonth() + 1}월 ${dayDate.getDate()}일`;
       
        // 2025년 3월 25일인 경우 건너뛰기
        if (dayLabel === '2025년 3월 25일') {
            return;
        }
 
        html += `
            <div class="revision-month-group">
                <div class="revision-month-header">
                    <div class="revision-month-title">
                        <i class="fas fa-calendar-alt"></i>
                        ${dayLabel}
                    </div>
                    <div class="revision-month-count">${dayData.length}건</div>
                </div>
                <div class="revision-regulations">
                    ${dayData.map(regulation => `
                        <div class="revision-regulation-item">
                            <div class="revision-regulation-main">
                                <span class="revision-regulation-code">
                                    ${regulation.code}. <span style="margin-left:0.3rem;">${regulation.name}</span>
                                </span>
                                <div class="revision-regulation-info">
                                    <div class="revision-regulation-meta">
                                        <span>제정일 : ${regulation.enactmentDate || '-'}</span>
                                        <span>최종 개정일 : ${regulation.revisionDate}</span>
                                        <span>시행일 : ${regulation.effectiveDate || '-'}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="revision-regulation-actions">
                                <button class="revision-action-btn revision-comparison-btn" onclick="openComparisonTablePdf('${regulation.code}', '${regulation.name}', ${regulation.wzRuleSeq || 'null'}); event.stopPropagation();" title="신구대비표 보기">
                                    <span>신구대비표</span>
                                </button>
                                <button class="revision-action-btn revision-current-btn" onclick="openCurrentRegulationPdf('${regulation.code}', '${regulation.name}'); event.stopPropagation();" title="현행내규 보기">
                                    <span>현행내규</span>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });   
 
    revisionContent.innerHTML = html;
}

// 모든 내규 수집 함수
function collectAllRegulations() {
    const regulations = [];

    // 2중 중첩 구조 순회
    for (const category of Object.values(hospitalRegulations)) {
        if (!category || typeof category !== 'object') continue;
        Object.keys(category).forEach(chapter => {
        const chapterData = category[chapter];

        if (!chapterData || !Array.isArray(chapterData.regulations)) {
            return;
        }

        chapterData.regulations.forEach(regulation => {
            if (!regulation || !regulation.code || !regulation.name) {
                console.warn(`개정이력: 유효하지 않은 regulation`, regulation);
                return;
            }
            
            const revisionDate = regulation.detail?.documentInfo?.최종개정일;
            const enactmentDate = regulation.detail?.documentInfo?.제정일;
            const effectiveDate = regulation.detail?.documentInfo?.시행일;
            const department = regulation.detail?.documentInfo?.소관부서 || '소관부서 미지정';

            // 개정일이 있는 경우만 추가
            if (revisionDate && revisionDate !== '-') {
                const cleanRevisionDate = revisionDate.trim().replace(/\.$/, '');

                regulations.push({
                    chapter: chapter,
                    chapterTitle: chapterData.title,
                    code: regulation.code,
                    name: regulation.name,
                    wzRuleSeq: regulation.wzRuleSeq || null,
                    revisionDate: cleanRevisionDate,
                    enactmentDate: enactmentDate && enactmentDate !== '-' ? enactmentDate : null,
                    effectiveDate: effectiveDate && effectiveDate !== '-' ? effectiveDate : null,
                    department: department,
                    regulation: regulation
                });
            }
        });
        });
    }

    // 전역 변수에 저장
    allRevisionData = regulations;
    filteredRevisionData = [...regulations]; // 복사본 생성

    // 캘린더용 날짜별 인덱싱
    indexRevisionsByDate(regulations);

    // 기본 정렬 적용
    applySortToRevisionData(currentRevisionSort);

    return regulations;
}

// 한국어 날짜 형식 파싱 (예: "2024.11.15" -> Date 객체)
function parseKoreanDate(dateString) {
    if (!dateString || dateString === '-' || dateString === '') return new Date(0);
    
    // 끝에 있는 점(.) 제거
    let cleanDateString = dateString.trim().replace(/\.$/, '');
    
    // "2024.11.15" 형식 처리
    if (cleanDateString.includes('.')) {
        const dateParts = cleanDateString.split('.');
        if (dateParts.length === 3) {
            const year = parseInt(dateParts[0]);
            const month = parseInt(dateParts[1]) - 1; // 월은 0부터 시작
            const day = parseInt(dateParts[2]);
            const result = new Date(year, month, day);
            return result;
        }
    }
    
    // "2024-11-15" 형식 처리
    if (cleanDateString.includes('-')) {
        const dateParts = cleanDateString.split('-');
        if (dateParts.length === 3) {
            const year = parseInt(dateParts[0]);
            const month = parseInt(dateParts[1]) - 1;
            const day = parseInt(dateParts[2]);
            return new Date(year, month, day);
        }
    }
    
    // 다른 형식도 시도
    const result = new Date(cleanDateString);
    return result;
}

// 월별 그룹핑
function old_groupRevisionsByMonth(regulations) {
    const grouped = {};
    
    regulations.forEach(regulation => {
        const date = parseKoreanDate(regulation.revisionDate);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-01`;
        
        if (!grouped[monthKey]) {
            grouped[monthKey] = [];
        }
        grouped[monthKey].push(regulation);
    });
    
    return grouped;
}

function groupRevisionsByDay(regulations) {
    const grouped = {};
    
    regulations.forEach(regulation => {
        const date = parseKoreanDate(regulation.revisionDate);
        // 월별 키 생성 → 일자별 키 생성으로 변경
        const dayKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        
        if (!grouped[dayKey]) {
            grouped[dayKey] = [];
        }
        grouped[dayKey].push(regulation);
    });
    
    return grouped;
}

// 개정일로부터 경과 일수 계산
function calculateDaysSinceRevision(revisionDate) {
    const date = parseKoreanDate(revisionDate);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
}

// 개정이력에서 내규 열기
function openRevisionRegulation(chapter, code) {
    const regulation = getChapterData(chapter)?.regulations?.find(reg => reg.code === code);
    
    if (regulation) {
        showRegulationDetail(regulation, chapter);
    } else {
        showToast('해당 내규를 찾을 수 없습니다.', 'error');
    }
}

// 개정이력 검색 필터링
function filterRevisionHistory(searchTerm) {
    console.log('개정이력 검색:', searchTerm);
    
    if (!searchTerm || searchTerm.trim() === '') {
        // 검색어가 없으면 전체 데이터 표시
        filteredRevisionData = [...allRevisionData];
    } else {
        const searchLower = searchTerm.trim().toLowerCase();

        // 내규명과 내규코드로 검색 (코드 뒤에 점(.)이 있어도 검색되도록)
        filteredRevisionData = allRevisionData.filter(item => {
            const nameMatch = item.name.toLowerCase().includes(searchLower);
            const codeMatch = item.code.toLowerCase().includes(searchLower);
            // "1.2.1" 검색 시 "1.2.1."도 매칭되도록
            const codeWithDotMatch = (item.code + '.').toLowerCase().includes(searchLower);
            // "1.2.2. PRN 처방" 형식으로 검색했을 때도 매칭되도록
            const fullFormatMatch = (item.code + '. ' + item.name).toLowerCase().includes(searchLower);

            return nameMatch || codeMatch || codeWithDotMatch || fullFormatMatch;
        });
    }
    
    // 현재 정렬 방식 적용
    applySortToRevisionData(currentRevisionSort);
    
    // 화면 업데이트
    displayRevisionHistoryContent();
    
}

// 개정이력 정렬
function sortRevisionHistory(sortType) {
    console.log('개정이력 정렬:', sortType);
    
    currentRevisionSort = sortType;
    applySortToRevisionData(sortType);
    displayRevisionHistoryContent();
}

// 정렬 로직 적용
function applySortToRevisionData(sortType) {
    switch (sortType) {
        case 'name-asc':
            // 내규명 가나다순
            filteredRevisionData.sort((a, b) => {
                return a.name.localeCompare(b.name, 'ko-KR');
            });
            break;
            
        case 'chapter-asc':
            // 챕터 순서
            filteredRevisionData.sort((a, b) => {
                // 먼저 챕터번호로 정렬
                const chapterA = parseInt(a.chapter.replace('장', ''));
                const chapterB = parseInt(b.chapter.replace('장', ''));
                
                if (chapterA !== chapterB) {
                    return chapterA - chapterB;
                }
                
                // 같은 챕터면 내규코드로 정렬
                return a.code.localeCompare(b.code, undefined, { numeric: true });
            });
            break;
            
        default:
            console.warn('알 수 없는 정렬 타입:', sortType);
    }
}

// 현행내규 PDF 열기 함수
async function openCurrentRegulationPdf(regulationCode, regulationName) {
    console.log('현행내규 PDF 열기:', regulationCode, regulationName);

    // 내규 코드를 API 형식으로 변환 (11.5.1 → 11_5_1)
    const apiCode = regulationCode.replace(/\./g, '_');
    console.log('[Print] API 호출 코드:', apiCode);

    try {
        // API 호출하여 PDF 파일명 찾기
        const apiResponse = await fetch(`/api/v1/pdf/print-file/${apiCode}`);
        const result = await apiResponse.json();

        if (!result.success) {
            showToast(result.error || `"${regulationName}" 현행내규 PDF 파일을 찾을 수 없습니다.`, 'error');
            console.warn('[Print] PDF 파일을 찾을 수 없습니다:', regulationCode, result.error);
            return;
        }

        // PDF 뷰어 URL 생성
        const currentDomain = window.location.origin;
        const pdfUrl = `${currentDomain}/static/viewer/web/viewer.html?file=${encodeURIComponent(result.path)}`;
        console.log('[Print] PDF URL:', pdfUrl);

        // 파일이 존재하면 PDF 열기 (모바일: iframe 모달, PC: 새 창)
        const isMobileUA = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        const isSmallScreen = window.innerWidth <= 768;

        if (isMobileUA || isSmallScreen) {
            // 모바일 또는 작은 화면: iframe 모달
            showPdfModal(pdfUrl);
        } else {
            // PC: 새 창
            const newWindow = window.open(pdfUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');

            if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
                // 팝업 차단 시: iframe 모달로 대체
                showPdfModal(pdfUrl);
            }
        }

    } catch (error) {
        console.error('현행내규 PDF 확인 중 오류:', error);
        showToast('현행내규 PDF를 불러오는 중 오류가 발생했습니다.', 'error');
    }
}

// 비교표 PDF 열기 함수 (파일 존재 여부 확인 포함)
async function openComparisonTablePdf(regulationCode, regulationName, wzRuleSeq) {
    console.log('비교표 PDF 열기:', regulationCode, 'wzRuleSeq:', wzRuleSeq);

    const timestamp = new Date().getTime();
    let pdfPath;

    try {
        // 1순위: summary JSON에서 신구대비표PDF 필드 확인
        if (wzRuleSeq && hospitalRegulations) {
            // 2중 중첩 구조 순회: { "KB규정": { "1편...": { regulations: [...] } } }
            let foundReg = null;
            for (const category of Object.values(hospitalRegulations)) {
                if (!category || typeof category !== 'object') continue;
                for (const chapterData of Object.values(category)) {
                    if (!chapterData || !Array.isArray(chapterData.regulations)) continue;
                    foundReg = chapterData.regulations.find(r => r.wzRuleSeq === wzRuleSeq || r.wzRuleSeq === String(wzRuleSeq));
                    if (foundReg) break;
                }
                if (foundReg) break;
            }

            if (foundReg) {
                // JSON 파일에 명시된 신구대비표PDF가 있으면 바로 사용
                const comparisonPdfFromJson = foundReg.detail?.documentInfo?.신구대비표PDF;
                if (comparisonPdfFromJson) {
                    pdfPath = `/static/pdf/comparisonTable/${comparisonPdfFromJson}`;
                    console.log('[JSON] 신구대비표PDF 사용:', pdfPath);
                    const pdfPathWithTimestamp = `/static/viewer/web/viewer.html?file=${pdfPath}?ts=${timestamp}`;
                    openPdfViewer(pdfPathWithTimestamp);
                    return;
                }

                // 폴백: DB wzFileComparison 경로로 시도
                const jsonFileName = foundReg.detail?.documentInfo?.파일명;
                const revisionDate = foundReg.detail?.documentInfo?.최종개정일;

                if (revisionDate) {
                    // wzRuleId 추출 시도
                    const wzRuleId = foundReg.wzRuleId || foundReg.detail?.documentInfo?.wzRuleId || '';
                    if (wzRuleId) {
                        const dateStr = revisionDate.replace(/[.\-\s]/g, '').slice(0, 8);
                        const newStylePath = `/static/pdf/comparisonTable/${wzRuleId}_${wzRuleSeq}_${dateStr}.pdf`;
                        console.log('[Auto] 신구대비표 시도:', newStylePath);

                        try {
                            const testResponse = await fetch(newStylePath, { method: 'HEAD' });
                            if (testResponse.ok) {
                                pdfPath = newStylePath;
                                const pdfPathWithTimestamp = `/static/viewer/web/viewer.html?file=${pdfPath}?ts=${timestamp}`;
                                openPdfViewer(pdfPathWithTimestamp);
                                return;
                            }
                        } catch (e) {
                            console.log('신규 방식 파일 없음, 레거시 방식 시도');
                        }
                    }
                }
            }
        }

        // 신규 방식으로 파일을 못 찾으면 레거시 방식 시도
        pdfPath = `/static/pdf/comparisonTable/comparisonTable_${regulationCode}.pdf`;
        console.log('신구대비표 파일 경로 (레거시):', pdfPath);

        // 파일 존재 여부 확인
        const response = await fetch(pdfPath, { method: 'HEAD' });

        if (!response.ok) {
            // 파일이 없으면 한글 메시지 표시
            showToast('신구대비표가 존재하지 않습니다.', 'error');
            return;
        }

        // ✅ 레거시 파일이 존재하면 PDF 열기
        const pdfPathWithTimestamp = `/static/viewer/web/viewer.html?file=${pdfPath}?ts=${timestamp}`;
        openPdfViewer(pdfPathWithTimestamp);

    } catch (error) {
        console.error('비교표 PDF 확인 중 오류:', error);
        showToast('신구대비표를 불러오는 중 오류가 발생했습니다.', 'error');
    }
}

// PDF 뷰어 열기 함수 (중복 코드 제거)
function openPdfViewer(pdfPathWithTimestamp) {
    const isMobileUA = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    const isSmallScreen = window.innerWidth <= 768;

    if (isMobileUA || isSmallScreen) {
        // 모바일 또는 작은 화면: iframe 모달
        showPdfModal(pdfPathWithTimestamp);
    } else {
        // PC: 새 창
        const newWindow = window.open(pdfPathWithTimestamp, '_blank', 'width=1000,height=800,scrollbars=yes,resizable=yes');

        if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
            // 팝업 차단 시: iframe 모달로 대체
            showPdfModal(pdfPathWithTimestamp);
        }
    }
}


// 소관부서별 데이터 구조화 변수
let departmentTreeData = {};

// 사이드 탭 클릭 이벤트 추가 (DOMContentLoaded 이벤트 리스너 안에 추가)
document.addEventListener('DOMContentLoaded', function() {
    // 기존 코드들...
    
    // 사이드 탭 이벤트 리스너 추가
    document.querySelectorAll('.side-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabType = this.dataset.type;
            switchSideTab(tabType, this);
        });
    });
});

// 사이드 탭 전환 함수
function switchSideTab(tabType, clickedTab) {
    // 모든 탭에서 active 클래스 제거
    document.querySelectorAll('.side-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 클릭한 탭에 active 클래스 추가
    clickedTab.classList.add('active');
    
    // 탭 유형에 따라 다른 메뉴 표시
    if (tabType === 'side_category') {
        showCategoryTree();
    } else if (tabType === 'side_dep') {
        showDepartmentTree();
    }
}

// 분류별 트리 표시 (기존 generateTreeMenu 함수 내용)
// 분류별 트리 표시 - generateTreeMenu 재사용
function showCategoryTree() {
    generateTreeMenu();
}

// 소관부서별 트리 표시 (검색 기능 포함)
function showDepartmentTree() {
    if (!hospitalRegulations || Object.keys(hospitalRegulations).length === 0) {
        console.log('hospitalRegulations가 아직 로드되지 않음');
        return;
    }

    // 소관부서별로 데이터 구조화
    buildDepartmentTreeData();

    const treeMenu = document.getElementById('treeMenu');

    // 검색창과 트리 컨테이너를 포함한 전체 구조 생성
    treeMenu.innerHTML = `
        <div class="department-search-container">
            <div class="department-search-box">
                <input type="text"
                       id="departmentSearchInput"
                       placeholder="소관부서 검색..."
                       onkeyup="filterDepartmentTree(this.value)"
                       autocomplete="off">
                <i class="fas fa-search department-search-icon"></i>
                <button class="department-search-clear"
                        onclick="clearDepartmentSearch()"
                        style="display: none;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="department-search-stats" id="departmentSearchStats" style="display: none;">
                <!-- 검색 결과 통계가 여기 표시됨 -->
            </div>
        </div>
        <div class="department-tree-container" id="departmentTreeContainer">
            <!-- 부서 트리가 여기 표시됨 -->
        </div>
    `;

    // 실제 트리 렌더링
    renderDepartmentTree();
}

// 소관부서 트리 검색 필터링 함수
function filterDepartmentTree(searchTerm) {
    const searchInput = document.getElementById('departmentSearchInput');
    const clearButton = document.querySelector('.department-search-clear');
    const statsDiv = document.getElementById('departmentSearchStats');
    
    // 검색어가 비어있으면 전체 표시
    if (!searchTerm || searchTerm.trim() === '') {
        renderDepartmentTree(); // 전체 부서 표시
        clearButton.style.display = 'none';
        statsDiv.style.display = 'none';
        return;
    }
    
    // 검색어가 있으면 클리어 버튼 표시
    clearButton.style.display = 'block';
    
    const searchLower = searchTerm.trim().toLowerCase();
    
    // 부서명에서 검색어가 포함된 부서들 필터링
    const matchingDepartments = Object.keys(departmentTreeData).filter(department => {
        return department.toLowerCase().includes(searchLower);
    });
    
    // 검색 결과 통계 업데이트
    updateSearchStats(matchingDepartments.length, Object.keys(departmentTreeData).length, searchTerm);
    
    // 필터링된 결과로 트리 다시 렌더링
    renderDepartmentTree(matchingDepartments);
    
    // 검색 결과가 있으면 하이라이팅 적용
    if (matchingDepartments.length > 0) {
        highlightSearchTerm(searchTerm);
    }
}

// 검색 결과 통계 업데이트
function updateSearchStats(matchCount, totalCount, searchTerm) {
    const statsDiv = document.getElementById('departmentSearchStats');
    
    if (matchCount === 0) {
        statsDiv.innerHTML = `
            <div class="search-stats-item no-results">
                <i class="fas fa-exclamation-circle"></i>
                <span>"${searchTerm}"에 대한 검색 결과가 없습니다</span>
            </div>
        `;
    } else {
        statsDiv.innerHTML = `
            <div class="search-stats-item">
                <i class="fas fa-filter"></i>
                <span>"${searchTerm}" 검색: ${matchCount}/${totalCount}개 부서</span>
            </div>
        `;
    }
    
    statsDiv.style.display = 'block';
}

// 텍스트 내 검색어 하이라이트 (빨간색 강조)
function highlightText(text, searchTerm) {
    if (!text || !searchTerm || searchTerm.trim() === '') {
        return text;
    }

    const searchLower = searchTerm.trim().toLowerCase();
    const textLower = text.toLowerCase();

    // 검색어가 텍스트에 없으면 원본 반환
    if (!textLower.includes(searchLower)) {
        return text;
    }

    // 대소문자 구분 없이 모든 매치를 찾아서 빨간색으로 강조
    let result = '';
    let lastIndex = 0;
    let index = textLower.indexOf(searchLower);

    while (index !== -1) {
        // 매치 이전 텍스트
        result += text.substring(lastIndex, index);
        // 매치된 텍스트 (빨간색 강조)
        result += `<span class="search-highlight-red">${text.substring(index, index + searchTerm.length)}</span>`;

        lastIndex = index + searchTerm.length;
        index = textLower.indexOf(searchLower, lastIndex);
    }

    // 나머지 텍스트
    result += text.substring(lastIndex);

    return result;
}

// 별표/별첨/서식 참조 텍스트를 클릭 가능한 PDF 팝업 링크로 변환
// isByulpyoSection=true이면 별표 섹션 자체이므로 링크 변환하지 않음
function linkifyByulpyo(text, articles, isByulpyoSection, regulationCode) {
    if (!text || isByulpyoSection) return text;

    // 『별표 제N호』, 『별첨 제N호』, 『서식 제N호』 패턴 매치
    const pattern = /『(별표|별첨|서식)\s*제?\s*(\d+)\s*호』/g;
    if (!pattern.test(text)) return text;

    // 패턴을 <a> 링크로 교체 - PDF 팝업 열기
    pattern.lastIndex = 0;
    return text.replace(pattern, (match, type, numStr) => {
        const num = parseInt(numStr);
        if (regulationCode) {
            // appendixIndex는 num-1 (0-based), appendixName은 DB의 wzappendixname과 매칭
            const appendixName = `${type} 제${num}호`;
            const escapedName = appendixName.replace(/'/g, "\\'");
            return `<a class="byulpyo-link" onclick="openByulpyoPdf('${regulationCode}', ${num}, '${escapedName}', event)">${match}</a>`;
        }
        return match;
    });
}

// 별표 섹션 div에 추가할 data 속성 문자열 생성 (실제 별표 섹션만 대상)
function getByulpyoDataAttrs(content) {
    if (!content) return '';
    // 실제 별표 섹션(『별표로 시작)에만 data 속성 부여, 참조하는 조문은 제외
    const plainText = content.replace(/<[^>]+>/g, '').trim();
    if (!plainText.startsWith('『별표')) return '';
    const matches = content.matchAll(/별표\s*제?\s*(\d+)\s*호/g);
    const attrs = [];
    for (const m of matches) {
        attrs.push(`data-byulpyo-${m[1]}="1"`);
    }
    return attrs.join(' ');
}

// 별표/별첨/서식 번호로 PDF 팝업 열기
// regulationCode: 내규 코드 (예: '6-8')
// byulpyoNo: 별표/별첨/서식 번호 (1-based)
// typeName: '별표 제N호' 형태의 이름
async function openByulpyoPdf(regulationCode, byulpyoNo, typeName, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    // APPENDIX_PDF_MAPPING에서 해당 별표 번호로 직접 검색
    if (typeof APPENDIX_PDF_MAPPING !== 'undefined') {
        for (const key in APPENDIX_PDF_MAPPING) {
            const [code, no] = key.split('|');
            if (code === regulationCode && parseInt(no) === byulpyoNo) {
                // 매핑 찾음 - 매핑의 appendixName을 사용하여 openAppendixPdf 호출
                const parts = key.split('|');
                const appendixName = parts[2];
                await openAppendixPdf(regulationCode, byulpyoNo - 1, appendixName);
                return;
            }
        }
    }

    // 매핑에 없으면 API를 통해 appendix 목록에서 번호로 검색
    try {
        const timestamp = new Date().getTime();
        const summaryResponse = await fetch(`/static/file/summary_kbregulation.json?ts=${timestamp}`);
        if (summaryResponse.ok) {
            const summaryData = await summaryResponse.json();
            let regulation = null;
            function findReg(data) {
                if (!data || typeof data !== 'object') return;
                if (data.regulations) {
                    const found = data.regulations.find(r => r.code === regulationCode);
                    if (found) { regulation = found; return; }
                }
                for (const key of Object.keys(data)) {
                    if (regulation) break;
                    findReg(data[key]);
                }
            }
            findReg(summaryData);

            if (regulation) {
                const ruleSeq = regulation.wzRuleSeq || regulation.wzruleseq;
                if (ruleSeq) {
                    const appendixResponse = await fetch(`/api/v1/appendix/list/${ruleSeq}`);
                    if (appendixResponse.ok) {
                        const appendixList = await appendixResponse.json();
                        // wzappendixno가 byulpyoNo와 매칭되는 항목 찾기
                        const matchIdx = appendixList.findIndex(a => parseInt(a.wzappendixno) === byulpyoNo);
                        if (matchIdx >= 0) {
                            const appendix = appendixList[matchIdx];
                            await openAppendixPdf(regulationCode, matchIdx, appendix.wzappendixname);
                            return;
                        }
                    }
                }
            }
        }
    } catch (error) {
        console.error('[openByulpyoPdf] API 검색 오류:', error);
    }

    // 최종 fallback: 못 찾으면 토스트
    if (typeof showToast === 'function') {
        showToast(`"${typeName}" PDF 파일을 찾을 수 없습니다.`, 'error');
    }
}

// 검색어 하이라이팅
function highlightSearchTerm(searchTerm) {
    if (!searchTerm || searchTerm.trim() === '') return;

    const searchLower = searchTerm.trim().toLowerCase();
    const departmentHeaders = document.querySelectorAll('.department-tree-header span:first-child');
    
    departmentHeaders.forEach(header => {
        const originalText = header.textContent;
        const lowerText = originalText.toLowerCase();
        
        if (lowerText.includes(searchLower)) {
            // 대소문자 구분 없이 원본 텍스트에서 일치하는 부분 찾기
            const startIndex = lowerText.indexOf(searchLower);
            const endIndex = startIndex + searchTerm.length;
            
            const beforeMatch = originalText.substring(0, startIndex);
            const matchText = originalText.substring(startIndex, endIndex);
            const afterMatch = originalText.substring(endIndex);
            
            header.innerHTML = `${beforeMatch}<mark class="search-highlight">${matchText}</mark>${afterMatch}`;
        }
    });
}

// 검색어 지우기
function clearDepartmentSearch() {
    const searchInput = document.getElementById('departmentSearchInput');
    const clearButton = document.querySelector('.department-search-clear');
    const statsDiv = document.getElementById('departmentSearchStats');
    
    searchInput.value = '';
    clearButton.style.display = 'none';
    statsDiv.style.display = 'none';
    
    // 전체 트리 다시 표시
    renderDepartmentTree();
    
    // 포커스를 검색창으로 이동
    searchInput.focus();
}


// 검색 기능 고도화: 내규명으로도 검색 (선택사항)
function advancedFilterDepartmentTree(searchTerm) {
    const searchInput = document.getElementById('departmentSearchInput');
    const clearButton = document.querySelector('.department-search-clear');
    const statsDiv = document.getElementById('departmentSearchStats');
    
    if (!searchTerm || searchTerm.trim() === '') {
        renderDepartmentTree();
        clearButton.style.display = 'none';
        statsDiv.style.display = 'none';
        return;
    }
    
    clearButton.style.display = 'block';
    const searchLower = searchTerm.trim().toLowerCase();
    
    // 부서명 또는 해당 부서의 내규명에 검색어가 포함된 부서들 찾기
    const matchingDepartments = Object.keys(departmentTreeData).filter(department => {
        // 1. 부서명에서 검색
        if (department.toLowerCase().includes(searchLower)) {
            return true;
        }
        
        // 2. 해당 부서의 내규명에서 검색
        const regulations = departmentTreeData[department];
        return regulations.some(item => 
            item.regulation.name.toLowerCase().includes(searchLower)
        );
    });
    
    updateSearchStats(matchingDepartments.length, Object.keys(departmentTreeData).length, searchTerm);
    renderDepartmentTree(matchingDepartments);
    
    if (matchingDepartments.length > 0) {
        highlightSearchTerm(searchTerm);
    }
}

// 실제 부서 트리 렌더링 함수 (검색 필터링 가능)
function renderDepartmentTree(filteredDepartments = null) {
    const container = document.getElementById('departmentTreeContainer');
    if (!container) return;
    
    // 사용할 부서 목록 결정 (필터링된 것이 있으면 사용, 없으면 전체)
    const departmentsToShow = filteredDepartments || Object.keys(departmentTreeData);
    
    // 부서명을 한국어 순서로 정렬 (소관부서 미지정은 맨 아래)
    const sortedDepartments = departmentsToShow.sort((a, b) => {
        if (a === '소관부서 미지정') return 1;
        if (b === '소관부서 미지정') return -1;
        return a.localeCompare(b, 'ko-KR');
    });
    
    container.innerHTML = '';
    
    if (sortedDepartments.length === 0) {
        container.innerHTML = `
            <div class="department-search-empty">
                <i class="fas fa-search"></i>
                <div>검색 결과가 없습니다</div>
            </div>
        `;
        return;
    }
    
    sortedDepartments.forEach(department => {
        const departmentData = departmentTreeData[department];
        const uniqueRegulations = removeDuplicateRegulations(departmentData);
        
        const treeItem = document.createElement('div');
        treeItem.className = 'department-tree-item';
        treeItem.setAttribute('data-department', department.toLowerCase());
        
        const treeHeader = document.createElement('div');
        treeHeader.className = 'department-tree-header';
        treeHeader.innerHTML = `
            <span>${department}</span>
            <span style="background: #ebf6fe; padding: 2px 6px; border-radius: 8px; font-size: 11px;">${uniqueRegulations.length}개</span>
        `;
        treeHeader.onclick = () => toggleDepartmentItem(treeHeader);
        
        const treeChildren = document.createElement('div');
        treeChildren.className = 'department-tree-children';
        
        uniqueRegulations.forEach(item => {
            const childNode = document.createElement('div');
            childNode.className = 'department-regulation';
            childNode.innerHTML = `
                ${item.regulation.code}. ${item.regulation.name}
            `;
            childNode.onclick = (event) => {
                event.stopPropagation();
                selectDepartmentRegulation(item.regulation, item.chapter, childNode);
            };
            
            treeChildren.appendChild(childNode);
        });
        
        treeItem.appendChild(treeHeader);
        treeItem.appendChild(treeChildren);
        container.appendChild(treeItem);
    });
}


// 중복된 내규 제거 함수
function removeDuplicateRegulations(departmentData) {
    const seen = new Set();
    const uniqueData = [];
    
    departmentData.forEach(item => {
        // 장번호와 내규코드로 고유 키 생성
        const uniqueKey = `${item.chapter}-${item.regulation.code}`;
        
        if (!seen.has(uniqueKey)) {
            seen.add(uniqueKey);
            uniqueData.push(item);
        }
    });
    
    // 장번호와 내규코드로 정렬
    uniqueData.sort((a, b) => {
        // 먼저 장번호로 정렬
        const chapterA = parseInt(a.chapter.replace('장', ''));
        const chapterB = parseInt(b.chapter.replace('장', ''));
        
        if (chapterA !== chapterB) {
            return chapterA - chapterB;
        }
        
        // 같은 장이면 내규코드로 정렬
        return a.regulation.code.localeCompare(b.regulation.code, undefined, { numeric: true });
    });
    
    return uniqueData;
}

// 소관부서별 데이터 구조화 (콤마 분리 처리)
function buildDepartmentTreeData() {
    departmentTreeData = {};

    Object.keys(hospitalRegulations).forEach(category => {
        const categoryData = hospitalRegulations[category];
        if (!categoryData || typeof categoryData !== 'object') return;

        Object.keys(categoryData).forEach(chapter => {
            const chapterData = categoryData[chapter];
            if (!chapterData || !Array.isArray(chapterData.regulations)) {
                return;
            }

            chapterData.regulations.forEach(regulation => {
                if (!regulation || !regulation.code || !regulation.name) {
                    return;
                }

                let departmentString = '소관부서 미지정';
                if (regulation.detail &&
                    regulation.detail.documentInfo &&
                    regulation.detail.documentInfo.소관부서) {
                    departmentString = regulation.detail.documentInfo.소관부서;
                }

                // 콤마로 구분된 소관부서들을 분리
                const departments = splitDepartments(departmentString);

                // 각각의 소관부서에 대해 개별적으로 처리
                departments.forEach(department => {
                    if (!departmentTreeData[department]) {
                        departmentTreeData[department] = [];
                    }

                    departmentTreeData[department].push({
                        chapter: chapter,
                        chapterTitle: chapterData.title,
                        regulation: regulation
                    });
                });
            });
        });
    });
}

// 소관부서 문자열을 개별 부서로 분리하는 헬퍼 함수
function splitDepartments(departmentString) {
    if (!departmentString || departmentString.trim() === '' || departmentString === '소관부서 미지정') {
        return ['소관부서 미지정'];
    }
    
    // 콤마로 분리하고 앞뒤 공백 제거
    const departments = departmentString.split(',')
        .map(dept => dept.trim())
        .filter(dept => dept.length > 0);
    
    // 분리된 부서가 없으면 원본 반환
    if (departments.length === 0) {
        return [departmentString];
    }
    
    return departments;
}

// 소관부서 트리 아이템 토글
function toggleDepartmentItem(header) {
    const children = header.nextElementSibling;
    const isOpen = children.classList.contains('open');

    // 모든 소관부서 트리 아이템 닫기
    document.querySelectorAll('.department-tree-children').forEach(child => {
        child.classList.remove('open');
    });
    document.querySelectorAll('.department-tree-header').forEach(h => {
        h.classList.remove('active');
    });

    // 클릭한 아이템만 열기/닫기
    if (!isOpen) {
        children.classList.add('open');
        header.classList.add('active');
    }
}

// 소관부서에서 내규 선택
function selectDepartmentRegulation(regulation, chapter, element) {
    // 모든 스크롤 리셋
    setTimeout(() => {
        resetAllScrolls();         // 2차 호출 (내부에서 또 3번 실행)
    }, 100);

    // 기존 선택 해제
    document.querySelectorAll('.department-regulation.active').forEach(child => {
        child.classList.remove('active');
    });
    
    // 현재 선택 표시
    element.classList.add('active');
    
    // 상세보기 표시
    showRegulationDetail(regulation, chapter);
}


//=============== 지원 탭===================
// 지원 페이지 표시
function showSupportPage() {
    // 사이드바 표시
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';

    // 네비게이션 활성화
    updateNavigation('홈');

    // 사이드바의 active 상태 초기화 (다른 탭으로 이동할 때)
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    // 지원 페이지 내용 생성
    displaySupportPage();

    // 데스크톱에서는 사이드바 닫기
    if (window.innerWidth > 768) {
        closeSidebar();
    }

}

// 지원 페이지 내용 표시
function displaySupportPage() {
    const contentBody = document.getElementById('contentBody');
    
    contentBody.innerHTML = `
        <div class="support-page">
            <div class="support-intro">
                <h2>고객 지원</h2>
                <p>KB신용정보 내규 시스템 사용에 도움이 필요하시거나 궁금한 점이 있으시면<br>
                아래 항목을 선택해주세요.</p>
            </div>
            
            <div class="support-grid">
                <div class="support-card" onclick="showNotices()">
                    <div class="support-card-icon">
                        <i class="fas fa-bullhorn"></i>
                    </div>
                    <div class="support-card-title">공지사항</div>
                </div>
                <div class="support-card" onclick="showProcedure()">
                    <div class="support-card-icon">
                        <i class="fa fa-pencil"></i>
                    </div>
                    <div class="support-card-title">KB신용정보 내규<br>제·개정 절차</div>
                </div>
                <div class="support-card" onclick="showUsageGuide()">
                    <div class="support-card-icon">
                        <i class="fas fa-book"></i>
                    </div>
                    <div class="support-card-title">사용방법</div>
                </div>
                
                <div class="support-card" onclick="showFAQ()">
                    <div class="support-card-icon">
                        <i class="fas fa-question-circle"></i>
                    </div>
                    <div class="support-card-title">자주 묻는 질문</div>
                </div>
                
                <div class="support-card" onclick="showQnA()" style="display:none;">
                    <div class="support-card-icon">
                        <i class="fas fa-comments"></i>
                    </div>
                    <div class="support-card-title">Q&A</div>
                    <div class="support-card-description">
                        궁금한 점을 질문하고<br>
                        답변을 받아보세요.
                    </div>
                    <button class="support-card-button">질문하기</button>
                </div>
                
            </div>
        </div>
    `;
}


// 사용방법 가이드 표시
async function showUsageGuide() {
    // 사이드바 표시
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';

    // 네비게이션 활성화
    updateNavigation('홈');

    // 사이드바의 active 상태 초기화
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    const contentBody = document.getElementById('contentBody');

    // 로딩 표시
    contentBody.innerHTML = '<div style="text-align:center; padding:50px;"><i class="fas fa-spinner fa-spin fa-3x"></i><p>사용방법 가이드를 불러오는 중...</p></div>';

    try {
        // API에서 데이터 가져오기
        const response = await fetch('/api/support/pages/public?page_type=usage');
        if (!response.ok) throw new Error('사용방법 가이드를 불러올 수 없습니다');

        const pages = await response.json();

        // 날짜 포맷팅 및 isNew 판단 (2주일 이내)
        const today = new Date();
        currentUsageData = pages.map(page => {
            const createdDate = new Date(page.created_at);
            const diffDays = Math.floor((today - createdDate) / (1000 * 60 * 60 * 24));

            return {
                id: page.page_id,
                title: page.title,
                author: page.updated_by || '관리자',
                date: page.updated_at ? page.updated_at.split('T')[0] : '-',
                views: page.view_count || 0,
                isNew: diffDays <= 14,
                is_important: page.is_important || false,
                attachment_name: page.attachment_name || null,
                attachment_path: page.attachment_name ? `/api/support/attachments/${page.page_id}` : null,
                content: page.content
            };
        });

        filteredUsageData = [...currentUsageData];
        currentUsagePage = 1;

    contentBody.innerHTML = `
        <div class="support-detail-page">
            <div class="support-detail-header">
                <div class="support-detail-icon">
                    <i class="fas fa-book"></i>
                </div>
                <div class="support-detail-title">사용방법 가이드</div>
                <button class="support-back-btn" onclick="showSupportPage()">
                    <i class="fas fa-arrow-left"></i> 돌아가기
                </button>
            </div>

            <!-- 검색 영역 -->
            <div class="notices-search-area">
                <div class="search-controls">
                    <select class="search-type-select" id="usageSearchType">
                        <option value="title">제목</option>
                        <option value="author">작성자</option>
                        <option value="all">전체</option>
                    </select>
                    <div class="search-input-wrapper">
                        <input type="text" id="usageSearchInput" placeholder="검색어를 입력하세요" class="search-input">
                        <button class="search-btn" onclick="searchUsage()">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </div>
                <div class="notices-stats">
                    <span><!-- 동적으로 업데이트 --></span>
                </div>
            </div>

            <!-- 테이블 영역 -->
            <div class="notices-table-container">
                <table class="notices-table">
                    <thead>
                        <tr>
                            <th class="col-number">번호</th>
                            <th class="col-important">구분</th>
                            <th class="col-title">제목</th>
                            <th class="col-author">작성자</th>
                            <th class="col-date">작성일</th>
                            <th class="col-views">조회수</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 페이지네이션으로 동적 생성 -->
                    </tbody>
                </table>
            </div>

            <!-- 페이지네이션 -->
            <div class="notices-pagination">
                <!-- 동적으로 생성 -->
            </div>
        </div>
    `;

        // 페이지네이션 초기화
        renderUsageTableWithPagination();

    } catch (error) {
        console.error('사용방법 가이드 로드 실패:', error);
        contentBody.innerHTML = `
            <div style="text-align:center; padding:50px;">
                <i class="fas fa-exclamation-triangle" style="font-size:48px; color:#dc3545;"></i>
                <h3 style="margin-top:20px;">사용방법 가이드를 불러올 수 없습니다</h3>
                <p style="color:#666;">${error.message}</p>
                <button onclick="showUsageGuide()" style="margin-top:20px; padding:10px 20px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer;">
                    다시 시도
                </button>
            </div>
        `;
    }

    // 데스크톱에서는 사이드바 닫기
    if (window.innerWidth > 768) {
        closeSidebar();
    }
}

// FAQ 표시
async function showFAQ() {
    // 사이드바 표시
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';

    // 네비게이션 활성화
    updateNavigation('홈');

    // 사이드바의 active 상태 초기화
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    const contentBody = document.getElementById('contentBody');

    // 로딩 표시
    contentBody.innerHTML = '<div style="text-align:center; padding:50px;"><i class="fas fa-spinner fa-spin fa-3x"></i><p>자주 묻는 질문을 불러오는 중...</p></div>';

    try {
        // API에서 데이터 가져오기
        const response = await fetch('/api/support/pages/public?page_type=faq');
        if (!response.ok) throw new Error('자주 묻는 질문을 불러올 수 없습니다');

        const pages = await response.json();

        // 날짜 포맷팅 및 isNew 판단 (2주일 이내)
        const today = new Date();
        currentFAQData = pages.map(page => {
            const createdDate = new Date(page.created_at);
            const diffDays = Math.floor((today - createdDate) / (1000 * 60 * 60 * 24));

            return {
                id: page.page_id,
                title: page.title,
                author: page.updated_by || '관리자',
                date: page.updated_at ? page.updated_at.split('T')[0] : '-',
                views: page.view_count || 0,
                isNew: diffDays <= 14,
                is_important: page.is_important || false,
                attachment_name: page.attachment_name || null,
                attachment_path: page.attachment_name ? `/api/support/attachments/${page.page_id}` : null,
                content: page.content
            };
        });

        filteredFAQData = [...currentFAQData];
        currentFAQPage = 1;

    contentBody.innerHTML = `
        <div class="support-detail-page">
            <div class="support-detail-header">
                <div class="support-detail-icon">
                    <i class="fas fa-question-circle"></i>
                </div>
                <div class="support-detail-title">자주 묻는 질문</div>
                <button class="support-back-btn" onclick="showSupportPage()">
                    <i class="fas fa-arrow-left"></i> 돌아가기
                </button>
            </div>

            <!-- 검색 영역 -->
            <div class="notices-search-area">
                <div class="search-controls">
                    <select class="search-type-select" id="faqSearchType">
                        <option value="title">제목</option>
                        <option value="author">작성자</option>
                        <option value="all">전체</option>
                    </select>
                    <div class="search-input-wrapper">
                        <input type="text" id="faqSearchInput" placeholder="검색어를 입력하세요" class="search-input">
                        <button class="search-btn" onclick="searchFAQ()">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </div>
                <div class="notices-stats">
                    <span><!-- 동적으로 업데이트 --></span>
                </div>
            </div>

            <!-- 테이블 영역 -->
            <div class="notices-table-container">
                <table class="notices-table">
                    <thead>
                        <tr>
                            <th class="col-number">번호</th>
                            <th class="col-important">구분</th>
                            <th class="col-title">제목</th>
                            <th class="col-author">작성자</th>
                            <th class="col-date">작성일</th>
                            <th class="col-views">조회수</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 페이지네이션으로 동적 생성 -->
                    </tbody>
                </table>
            </div>

            <!-- 페이지네이션 -->
            <div class="notices-pagination">
                <!-- 동적으로 생성 -->
            </div>
        </div>
    `;

        // 페이지네이션 초기화
        renderFAQTableWithPagination();

    } catch (error) {
        console.error('자주 묻는 질문 로드 실패:', error);
        contentBody.innerHTML = `
            <div style="text-align:center; padding:50px;">
                <i class="fas fa-exclamation-triangle" style="font-size:48px; color:#dc3545;"></i>
                <h3 style="margin-top:20px;">자주 묻는 질문을 불러올 수 없습니다</h3>
                <p style="color:#666;">${error.message}</p>
                <button onclick="showFAQ()" style="margin-top:20px; padding:10px 20px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer;">
                    다시 시도
                </button>
            </div>
        `;
    }

    // 데스크톱에서는 사이드바 닫기
    if (window.innerWidth > 768) {
        closeSidebar();
    }
}

// HTML 이스케이프 함수 (XSS 방지)
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Q&A 표시
function showQnA() {
    const contentBody = document.getElementById('contentBody');
    
    contentBody.innerHTML = `
        <div class="support-detail-page">
            <div class="support-detail-header">
                <div class="support-detail-icon">
                    <i class="fas fa-comments"></i>
                </div>
                <div class="support-detail-title">Q&A</div>
                <button class="support-back-btn" onclick="showSupportPage()">
                    <i class="fas fa-arrow-left"></i> 돌아가기
                </button>
            </div>
            
            <div class="support-content">
                <div style="text-align: center; padding: 60px 20px;">
                    <i class="fas fa-tools" style="font-size: 48px; color: #ddd; margin-bottom: 20px;"></i>
                    <h3 style="color: #666; margin-bottom: 15px;">Q&A 기능 준비 중</h3>
                    <p style="color: #999; line-height: 1.6;">
                        질문과 답변 기능을 준비하고 있습니다.<br>
                        빠른 시일 내에 서비스를 제공해드리겠습니다.
                    </p>
                    <div style="margin-top: 30px;">
                        <button class="support-card-button" onclick="showSupportPage()">
                            지원 메뉴로 돌아가기
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function showNotices() {
    // 사이드바 표시
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';

    // 네비게이션 활성화
    updateNavigation('홈');

    // 사이드바의 active 상태 초기화 (다른 탭으로 이동할 때)
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    const contentBody = document.getElementById('contentBody');

    // 로딩 표시
    contentBody.innerHTML = '<div style="text-align:center; padding:50px;"><i class="fas fa-spinner fa-spin fa-3x"></i><p>공지사항을 불러오는 중...</p></div>';

    try {
        // API에서 공지사항 데이터 가져오기
        const response = await fetch('/api/notices/?is_active=true');
        if (!response.ok) throw new Error('공지사항을 불러올 수 없습니다');

        const notices = await response.json();

        // 날짜 포맷팅 및 isNew 판단 (2주일 이내)
        const today = new Date();
        const noticesData = notices.map(notice => {
            const createdDate = new Date(notice.created_at);
            const diffDays = Math.floor((today - createdDate) / (1000 * 60 * 60 * 24));

            return {
                id: notice.notice_id,
                title: notice.title,
                author: notice.created_by || '관리자',
                date: notice.created_at.split('T')[0],
                views: notice.view_count,
                isNew: diffDays <= 14,
                is_important: notice.is_important,
                attachment_name: notice.attachment_name,
                attachment_path: notice.attachment_path
            };
        });

        // 전역 변수에 저장
        currentNoticesData = noticesData;
        filteredNoticesData = [...noticesData];
        currentNoticesPage = 1;
    
    contentBody.innerHTML = `
        <div class="support-detail-page">
            <div class="support-detail-header">
                <div class="support-detail-icon">
                    <i class="fas fa-comments"></i>
                </div>
                <div class="support-detail-title">공지사항</div>
                <button class="support-back-btn" onclick="showSupportPage()">
                    <i class="fas fa-arrow-left"></i> 돌아가기
                </button>
            </div>

            <!-- 검색 영역 -->
            <div class="notices-search-area">
                <div class="search-controls">
                    <select class="search-type-select">
                        <option value="title">제목</option>
                        <option value="author">작성자</option>
                        <!-- <option value="content">내용</option> -->
                        <option value="all">전체</option>
                    </select>
                    <div class="search-input-wrapper">
                        <input type="text" id="noticesSearchInput" placeholder="검색어를 입력하세요" class="search-input">
                        <button class="search-btn" onclick="searchNotices()">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </div>
                <div class="notices-stats">
                    <span><!-- 동적으로 업데이트 --></span>
                </div>
            </div>

            <!-- 테이블 영역 -->
            <div class="notices-table-container">
                <table class="notices-table">
                    <thead>
                        <tr>
                            <th class="col-number">번호</th>
                            <th class="col-important">구분</th>
                            <th class="col-title">제목</th>
                            <th class="col-author">작성자</th>
                            <th class="col-date">작성일</th>
                            <th class="col-views">조회수</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 페이지네이션으로 동적 생성 -->
                    </tbody>
                </table>
            </div>

            <!-- 페이지네이션 -->
            <div class="notices-pagination">
                <!-- 동적으로 생성 -->
            </div>
        </div>
    `;

        // 페이지네이션 초기화
        renderNoticesTableWithPagination();

    } catch (error) {
        console.error('공지사항 로드 실패:', error);
        contentBody.innerHTML = `
            <div style="text-align:center; padding:50px;">
                <i class="fas fa-exclamation-triangle" style="font-size:48px; color:#dc3545;"></i>
                <h3 style="margin-top:20px;">공지사항을 불러올 수 없습니다</h3>
                <p style="color:#666;">${error.message}</p>
                <button onclick="showNotices()" style="margin-top:20px; padding:10px 20px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer;">
                    다시 시도
                </button>
            </div>
        `;
    }

    // 데스크톱에서는 사이드바 닫기
    if (window.innerWidth > 768) {
        closeSidebar();
    }
}

// 페이지네이션 렌더링 함수
function renderNoticesPagination() {
    const paginationContainer = document.querySelector('.notices-pagination');
    if (!paginationContainer) return;

    const totalPages = Math.ceil(filteredNoticesData.length / noticesPerPage);

    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }

    paginationContainer.style.display = 'flex';

    // 페이지 번호 생성
    let pageNumbers = [];

    if (totalPages <= 7) {
        // 7페이지 이하면 모두 표시
        for (let i = 1; i <= totalPages; i++) {
            pageNumbers.push(i);
        }
    } else {
        // 7페이지 초과시 축약 표시
        if (currentNoticesPage <= 4) {
            pageNumbers = [1, 2, 3, 4, 5, '...', totalPages];
        } else if (currentNoticesPage >= totalPages - 3) {
            pageNumbers = [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
        } else {
            pageNumbers = [1, '...', currentNoticesPage - 1, currentNoticesPage, currentNoticesPage + 1, '...', totalPages];
        }
    }

    // 페이지 번호 HTML 생성
    const pageNumbersHTML = pageNumbers.map(page => {
        if (page === '...') {
            return '<span class="pagination-dots">...</span>';
        }
        return `<button class="pagination-number ${page === currentNoticesPage ? 'active' : ''}"
                        onclick="changeNoticesPage(${page})">${page}</button>`;
    }).join('');

    paginationContainer.innerHTML = `
        <div class="pagination-info">
            <span>${currentNoticesPage} of ${totalPages}</span>
        </div>
        <div class="pagination-controls">
            <button class="pagination-btn" onclick="changeNoticesPage(${currentNoticesPage - 1})"
                    ${currentNoticesPage === 1 ? 'disabled' : ''}>
                <i class="fas fa-chevron-left"></i>
            </button>
            <span class="pagination-numbers">
                ${pageNumbersHTML}
            </span>
            <button class="pagination-btn" onclick="changeNoticesPage(${currentNoticesPage + 1})"
                    ${currentNoticesPage === totalPages ? 'disabled' : ''}>
                <i class="fas fa-chevron-right"></i>
            </button>
        </div>
    `;
}

// 페이지 변경 함수
function changeNoticesPage(page) {
    const totalPages = Math.ceil(filteredNoticesData.length / noticesPerPage);

    if (page < 1 || page > totalPages) return;

    currentNoticesPage = page;
    renderNoticesTableWithPagination();
}

// 공지사항 테이블 렌더링 함수 (페이지네이션 적용)
function renderNoticesTableWithPagination() {
    const startIndex = (currentNoticesPage - 1) * noticesPerPage;
    const endIndex = startIndex + noticesPerPage;
    const pageData = filteredNoticesData.slice(startIndex, endIndex);

    renderNoticesTable(pageData);
    renderNoticesPagination();
}

// 공지사항 테이블 렌더링 함수
function renderNoticesTable(noticesData) {
    const tbody = document.querySelector('.notices-table tbody');
    const noticesStats = document.querySelector('.notices-stats span');

    if (!tbody) return;

    if (filteredNoticesData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 50px; color: #999;">
                    <i class="fas fa-search" style="font-size: 48px; margin-bottom: 20px; display: block;"></i>
                    검색 결과가 없습니다.
                </td>
            </tr>
        `;
        if (noticesStats) {
            noticesStats.innerHTML = '총 <strong>0</strong>건의 공지사항';
        }
        return;
    }

    tbody.innerHTML = noticesData.map((item, index) => {
        // 등록 순서대로 번호 계산 (페이지네이션 고려)
        const actualIndex = filteredNoticesData.findIndex(notice => notice.id === item.id);
        const number = actualIndex + 1;

        return `
        <tr class="notices-row" onclick="openNoticeDetail(${item.id})">
            <td class="col-number">${number}</td>
            <td class="col-important">
                ${item.is_important ? '<span class="notice-important-badge">중요</span>' : ''}
            </td>
            <td class="col-title">
                <span class="notices-title">${item.title}</span>
                ${item.isNew ? '<span class="new-badge" style="margin-left: 5px;">N</span>' : ''}
                ${item.attachment_name ? '<i class="fas fa-paperclip" style="color: #667eea; margin-left: 5px;" title="' + item.attachment_name + '"></i>' : ''}
            </td>
            <td class="col-author">${item.author}</td>
            <td class="col-date">${item.date}</td>
            <td class="col-views">${item.views.toLocaleString()}</td>
        </tr>
    `}).join('');

    if (noticesStats) {
        noticesStats.innerHTML = `총 <strong>${filteredNoticesData.length}</strong>건의 공지사항`;
    }
}

// 검색 함수
function searchNotices() {
    const searchInput = document.getElementById('noticesSearchInput');
    const searchTerm = searchInput.value.trim().toLowerCase();
    const searchType = document.querySelector('.search-type-select').value;

    if (!searchTerm) {
        // 검색어가 없으면 전체 데이터 표시
        filteredNoticesData = [...currentNoticesData];
        currentNoticesPage = 1;
        renderNoticesTableWithPagination();
        return;
    }

    // 검색 타입에 따라 필터링
    filteredNoticesData = currentNoticesData.filter(notice => {
        switch(searchType) {
            case 'title':
                return notice.title.toLowerCase().includes(searchTerm);
            case 'author':
                return notice.author.toLowerCase().includes(searchTerm);
            case 'content':
                // content는 현재 noticesData에 없으므로 title로 대체
                return notice.title.toLowerCase().includes(searchTerm);
            case 'all':
            default:
                return notice.title.toLowerCase().includes(searchTerm) ||
                       notice.author.toLowerCase().includes(searchTerm);
        }
    });

    // 검색 후 첫 페이지로 이동
    currentNoticesPage = 1;
    renderNoticesTableWithPagination();
}

// 공지사항 상세보기
async function openNoticeDetail(id) {
    try {
        // API에서 공지사항 상세 정보 가져오기
        const response = await fetch(`/api/notices/${id}`);
        if (!response.ok) throw new Error('공지사항을 불러올 수 없습니다');

        const notice = await response.json();

        // 모바일 감지
        const isMobile = window.innerWidth <= 768;

        // 날짜 포맷팅
        const formatDate = (dateStr) => {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}.`;
        };

        // 첨부파일 HTML
        const attachmentHTML = notice.attachment_name ? `
            <div style="margin-top: 25px; padding: ${isMobile ? '15px' : '18px'}; background: #f0f7ff; border-radius: 8px; border: 1px solid #d0e4ff;">
                <div style="display: flex; ${isMobile ? 'flex-direction: column;' : 'align-items: center;'} gap: ${isMobile ? '10px' : '12px'};">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #1976d2; margin-bottom: 6px; font-size: 14px;">첨부파일</div>
                        <div style="font-size: ${isMobile ? '13px' : '14px'}; color: #555; word-break: break-all;">${notice.attachment_name}</div>
                    </div>
                    <a href="/api/notices/download/${notice.notice_id}"
                       download
                       style="padding: 10px 20px; background: #2786dd; color: white; border-radius: 6px;
                              text-decoration: none; font-size: 14px; font-weight: 500;
                              transition: all 0.3s; white-space: nowrap; ${isMobile ? 'text-align: center;' : ''}"
                       onmouseover="this.style.background='#1976d2'"
                       onmouseout="this.style.background='#2786dd'">
                        다운로드
                    </a>
                </div>
            </div>
        ` : '';

        // 모달 생성
        const modalHTML = `
            <div id="noticeDetailModal" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                animation: fadeIn 0.3s;
            " onclick="closeNoticeDetailModal(event)">
                <div style="
                    background: white;
                    max-width: 800px;
                    width: 90%;
                    max-height: 90vh;
                    border-radius: 15px;
                    overflow: hidden;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    animation: slideUp 0.3s;
                " onclick="event.stopPropagation()">
                    <!-- 헤더 -->
                    <div style="
                        background: #1976d2;
                        color: white;
                        padding: ${isMobile ? '20px' : '20px 30px'};
                        border-bottom: 3px solid #1565c0;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 20px;">
                            <div style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                                    ${notice.is_important ? '<span style="background: #c53030; padding: 5px 12px; border-radius: 4px; font-size: 12px; font-weight: 600;">중요</span>' : ''}
                                </div>
                                <h2 style="font-size: ${isMobile ? '18px' : '22px'}; margin: 0; font-weight: 600; line-height: 1.4;">
                                    ${notice.title}
                                </h2>
                            </div>
                            <button onclick="closeNoticeDetailModal()" style="
                                background: rgba(255,255,255,0.15);
                                border: none;
                                color: white;
                                font-size: 28px;
                                cursor: pointer;
                                width: 36px;
                                height: 36px;
                                border-radius: 4px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                transition: all 0.2s;
                                flex-shrink: 0;
                                line-height: 1;
                            " onmouseover="this.style.background='rgba(255,255,255,0.25)'"
                               onmouseout="this.style.background='rgba(255,255,255,0.15)'">
                                ×
                            </button>
                        </div>
                    </div>

                    <!-- 메타 정보 -->
                    <div style="
                        padding: ${isMobile ? '15px 20px' : '18px 30px'};
                        border-bottom: 1px solid #e3f2fd;
                        background: #f8fbff;
                        display: flex;
                        flex-direction: ${isMobile ? 'column' : 'row'};
                        gap: ${isMobile ? '12px' : '24px'};
                        font-size: 14px;
                        color: #555;
                    ">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-weight: 600; color: #1976d2; min-width: ${isMobile ? '60px' : 'auto'};">작성자</span>
                            <span>${notice.created_by || '관리자'}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-weight: 600; color: #1976d2; min-width: ${isMobile ? '60px' : 'auto'};">작성일</span>
                            <span>${formatDate(notice.created_at)}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-weight: 600; color: #1976d2; min-width: ${isMobile ? '60px' : 'auto'};">조회수</span>
                            <span>${notice.view_count.toLocaleString()}</span>
                        </div>
                    </div>

                    <!-- 내용 -->
                    <div style="
                        padding: ${isMobile ? '20px' : '25px 30px'};
                        max-height: 60vh;
                        overflow-y: auto;
                        background: white;
                    ">
                        <div style="
                            line-height: 1.8;
                            font-size: 15px;
                            color: #333;
                            white-space: pre-wrap;
                            word-break: break-word;
                        ">${notice.content}</div>

                        ${attachmentHTML}
                    </div>

                </div>
            </div>
        `;

        // 모달을 body에 추가
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHTML;
        document.body.appendChild(modalContainer.firstElementChild);

        // 스크롤 방지
        document.body.style.overflow = 'hidden';

    } catch (error) {
        console.error('공지사항 상세보기 오류:', error);
        alert('공지사항을 불러오는데 실패했습니다.');
    }
}

// 공지사항 상세 모달 닫기
function closeNoticeDetailModal(event) {
    // 배경 클릭이거나 닫기 버튼 클릭인 경우에만 닫기
    if (!event || event.target.id === 'noticeDetailModal' || event.type === 'click') {
        const modal = document.getElementById('noticeDetailModal');
        if (modal) {
            modal.remove();
            document.body.style.overflow = '';
        }
    }
}

// Enter 키 검색 지원
document.addEventListener('keypress', function(e) {
    if (e.target.id === 'noticesSearchInput' && e.key === 'Enter') {
        searchNotices();
    }
    if (e.target.id === 'proceduresSearchInput' && e.key === 'Enter') {
        searchProcedures();
    }
});

// KB신용정보 내규 제·개정 절차 표시
async function showProcedure() {
    // 사이드바 표시
    setSidebarDisplay('');
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'none';

    // 네비게이션 활성화
    updateNavigation('홈');

    // 사이드바의 active 상태 초기화 (다른 탭으로 이동할 때)
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    const contentBody = document.getElementById('contentBody');

    // 로딩 표시
    contentBody.innerHTML = '<div style="text-align:center; padding:50px;"><i class="fas fa-spinner fa-spin fa-3x"></i><p>제·개정 절차 정보를 불러오는 중...</p></div>';

    try {
        // API에서 데이터 가져오기
        const response = await fetch('/api/support/pages/public?page_type=procedure');
        if (!response.ok) throw new Error('제·개정 절차 정보를 불러올 수 없습니다');

        const pages = await response.json();

        // 날짜 포맷팅 및 isNew 판단 (2주일 이내)
        const today = new Date();
        currentProceduresData = pages.map(page => {
            const createdDate = new Date(page.created_at);
            const diffDays = Math.floor((today - createdDate) / (1000 * 60 * 60 * 24));

            return {
                id: page.page_id,
                title: page.title,
                author: page.updated_by || '관리자',
                date: page.updated_at ? page.updated_at.split('T')[0] : '-',
                views: page.view_count || 0,
                isNew: diffDays <= 14,
                is_important: page.is_important || false,
                attachment_name: page.attachment_name || null,
                attachment_path: page.attachment_name ? `/api/support/attachments/${page.page_id}` : null,
                content: page.content
            };
        });

        filteredProceduresData = [...currentProceduresData];
        currentProceduresPage = 1;

    contentBody.innerHTML = `
        <div class="support-detail-page">
            <div class="support-detail-header">
                <div class="support-detail-icon">
                    <i class="fa fa-pencil"></i>
                </div>
                <div class="support-detail-title">KB신용정보 내규 제·개정 절차</div>
                <button class="support-back-btn" onclick="showSupportPage()">
                    <i class="fas fa-arrow-left"></i> 돌아가기
                </button>
            </div>

            <!-- 검색 영역 -->
            <div class="notices-search-area">
                <div class="search-controls">
                    <select class="search-type-select" id="procedureSearchType">
                        <option value="title">제목</option>
                        <option value="author">작성자</option>
                        <option value="all">전체</option>
                    </select>
                    <div class="search-input-wrapper">
                        <input type="text" id="proceduresSearchInput" placeholder="검색어를 입력하세요" class="search-input">
                        <button class="search-btn" onclick="searchProcedures()">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </div>
                <div class="notices-stats">
                    <span>총 <strong>1</strong>건의 제·개정 절차</span>
                </div>
            </div>

            <!-- 테이블 영역 -->
            <div class="notices-table-container">
                <table class="notices-table">
                    <thead>
                        <tr>
                            <th class="col-number">번호</th>
                            <th class="col-important">구분</th>
                            <th class="col-title">제목</th>
                            <th class="col-author">작성자</th>
                            <th class="col-date">작성일</th>
                            <th class="col-views">조회수</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 페이지네이션으로 동적 생성 -->
                    </tbody>
                </table>
            </div>

            <!-- 페이지네이션 -->
            <div class="notices-pagination">
                <!-- 동적으로 생성 -->
            </div>
        </div>
    `;

        // 페이지네이션 초기화
        renderProceduresTableWithPagination();

    } catch (error) {
        console.error('제·개정 절차 로드 실패:', error);
        contentBody.innerHTML = `
            <div style="text-align:center; padding:50px;">
                <i class="fas fa-exclamation-triangle" style="font-size:48px; color:#dc3545;"></i>
                <h3 style="margin-top:20px;">제·개정 절차 정보를 불러올 수 없습니다</h3>
                <p style="color:#666;">${error.message}</p>
                <button onclick="showProcedure()" style="margin-top:20px; padding:10px 20px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer;">
                    다시 시도
                </button>
            </div>
        `;
    }

    // 데스크톱에서는 사이드바 닫기
    if (window.innerWidth > 768) {
        closeSidebar();
    }
}

// 제·개정 절차 테이블 렌더링 함수 (페이지네이션 적용)
function renderProceduresTableWithPagination() {
    const startIndex = (currentProceduresPage - 1) * proceduresPerPage;
    const endIndex = startIndex + proceduresPerPage;
    const pageData = filteredProceduresData.slice(startIndex, endIndex);

    renderProceduresTable(pageData);
    renderProceduresPagination();
}

// 제·개정 절차 테이블 렌더링 함수
function renderProceduresTable(proceduresData) {
    const tbody = document.querySelector('.notices-table tbody');
    const proceduresStats = document.querySelector('.notices-stats span');

    if (!tbody) return;

    if (filteredProceduresData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 50px; color: #999;">
                    <i class="fas fa-search" style="font-size: 48px; margin-bottom: 20px; display: block;"></i>
                    검색 결과가 없습니다.
                </td>
            </tr>
        `;
        if (proceduresStats) {
            proceduresStats.innerHTML = '총 <strong>0</strong>건의 제·개정 절차';
        }
        return;
    }

    tbody.innerHTML = proceduresData.map((item, index) => {
        // 등록 순서대로 번호 계산 (페이지네이션 고려)
        const actualIndex = filteredProceduresData.findIndex(procedure => procedure.id === item.id);
        const number = actualIndex + 1;

        return `
        <tr class="notices-row" onclick="openProcedureDetail(${item.id})">
            <td class="col-number">${number}</td>
            <td class="col-important">
                ${item.is_important ? '<span class="notice-important-badge">중요</span>' : ''}
            </td>
            <td class="col-title">
                <span class="notices-title">${item.title}</span>
                ${item.isNew ? '<span class="new-badge" style="margin-left: 5px;">N</span>' : ''}
                ${item.attachment_name ? '<i class="fas fa-paperclip" style="color: #667eea; margin-left: 5px;" title="' + item.attachment_name + '"></i>' : ''}
            </td>
            <td class="col-author">${item.author}</td>
            <td class="col-date">${item.date}</td>
            <td class="col-views">${item.views.toLocaleString()}</td>
        </tr>
    `}).join('');

    if (proceduresStats) {
        proceduresStats.innerHTML = `총 <strong>${filteredProceduresData.length}</strong>건의 제·개정 절차`;
    }
}

// 제·개정 절차 페이지네이션 렌더링
function renderProceduresPagination() {
    const paginationContainer = document.querySelector('.notices-pagination');
    if (!paginationContainer) return;

    const totalPages = Math.ceil(filteredProceduresData.length / proceduresPerPage);

    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }

    paginationContainer.style.display = 'flex';

    // 페이지 번호 생성
    let pageNumbers = [];

    if (totalPages <= 7) {
        // 7페이지 이하면 모두 표시
        for (let i = 1; i <= totalPages; i++) {
            pageNumbers.push(i);
        }
    } else {
        // 7페이지 초과시 축약 표시
        if (currentProceduresPage <= 4) {
            pageNumbers = [1, 2, 3, 4, 5, '...', totalPages];
        } else if (currentProceduresPage >= totalPages - 3) {
            pageNumbers = [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
        } else {
            pageNumbers = [1, '...', currentProceduresPage - 1, currentProceduresPage, currentProceduresPage + 1, '...', totalPages];
        }
    }

    // 페이지 번호 HTML 생성
    const pageNumbersHTML = pageNumbers.map(page => {
        if (page === '...') {
            return '<span class="pagination-dots">...</span>';
        }
        return `<button class="pagination-number ${page === currentProceduresPage ? 'active' : ''}"
                        onclick="changeProceduresPage(${page})">${page}</button>`;
    }).join('');

    paginationContainer.innerHTML = `
        <button class="pagination-arrow"
                onclick="changeProceduresPage(${currentProceduresPage - 1})"
                ${currentProceduresPage === 1 ? 'disabled' : ''}>
            <i class="fas fa-chevron-left"></i>
        </button>
        ${pageNumbersHTML}
        <button class="pagination-arrow"
                onclick="changeProceduresPage(${currentProceduresPage + 1})"
                ${currentProceduresPage === totalPages ? 'disabled' : ''}>
            <i class="fas fa-chevron-right"></i>
        </button>
    `;
}

// 제·개정 절차 페이지 변경
function changeProceduresPage(page) {
    const totalPages = Math.ceil(filteredProceduresData.length / proceduresPerPage);
    if (page < 1 || page > totalPages) return;

    currentProceduresPage = page;
    renderProceduresTableWithPagination();
}

// 제·개정 절차 검색 함수
function searchProcedures() {
    const searchInput = document.getElementById('proceduresSearchInput');
    const searchTerm = searchInput.value.trim().toLowerCase();
    const searchType = document.getElementById('procedureSearchType').value;

    if (!searchTerm) {
        filteredProceduresData = [...currentProceduresData];
    } else {
        filteredProceduresData = currentProceduresData.filter(item => {
            if (searchType === 'title') {
                return item.title.toLowerCase().includes(searchTerm);
            } else if (searchType === 'author') {
                return item.author.toLowerCase().includes(searchTerm);
            } else if (searchType === 'all') {
                return item.title.toLowerCase().includes(searchTerm) ||
                       item.author.toLowerCase().includes(searchTerm);
            }
            return false;
        });
    }

    currentProceduresPage = 1;
    renderProceduresTableWithPagination();
}

// ==================== 사용방법 가이드 테이블/페이지네이션 함수 ====================

// 사용방법 테이블 렌더링 (페이지네이션 적용)
function renderUsageTableWithPagination() {
    const startIndex = (currentUsagePage - 1) * usagePerPage;
    const endIndex = startIndex + usagePerPage;
    const pageData = filteredUsageData.slice(startIndex, endIndex);

    renderUsageTable(pageData);
    renderUsagePagination();
}

// 사용방법 테이블 렌더링
function renderUsageTable(usageData) {
    const tbody = document.querySelector('.notices-table tbody');
    const usageStats = document.querySelector('.notices-stats span');

    if (!tbody) return;

    if (filteredUsageData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 50px; color: #999;">
                    <i class="fas fa-search" style="font-size: 48px; margin-bottom: 20px; display: block;"></i>
                    검색 결과가 없습니다.
                </td>
            </tr>
        `;
        if (usageStats) {
            usageStats.innerHTML = '총 <strong>0</strong>건의 사용방법 가이드';
        }
        return;
    }

    tbody.innerHTML = usageData.map((item, index) => {
        const actualIndex = filteredUsageData.findIndex(usage => usage.id === item.id);
        const number = actualIndex + 1;

        return `
        <tr class="notices-row" onclick="openUsageDetail(${item.id})">
            <td class="col-number">${number}</td>
            <td class="col-important">
                ${item.is_important ? '<span class="notice-important-badge">중요</span>' : ''}
            </td>
            <td class="col-title">
                <span class="notices-title">${item.title}</span>
                ${item.isNew ? '<span class="new-badge" style="margin-left: 5px;">N</span>' : ''}
                ${item.attachment_name ? '<i class="fas fa-paperclip" style="color: #667eea; margin-left: 5px;" title="' + item.attachment_name + '"></i>' : ''}
            </td>
            <td class="col-author">${item.author}</td>
            <td class="col-date">${item.date}</td>
            <td class="col-views">${item.views}</td>
        </tr>
    `}).join('');

    if (usageStats) {
        usageStats.innerHTML = `총 <strong>${filteredUsageData.length}</strong>건의 사용방법 가이드`;
    }
}

// 사용방법 페이지네이션 렌더링
function renderUsagePagination() {
    const paginationContainer = document.querySelector('.notices-pagination');
    if (!paginationContainer) return;

    const totalPages = Math.ceil(filteredUsageData.length / usagePerPage);

    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }

    paginationContainer.style.display = 'flex';

    let pageNumbers = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) {
            pageNumbers.push(i);
        }
    } else {
        if (currentUsagePage <= 4) {
            pageNumbers = [1, 2, 3, 4, 5, '...', totalPages];
        } else if (currentUsagePage >= totalPages - 3) {
            pageNumbers = [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
        } else {
            pageNumbers = [1, '...', currentUsagePage - 1, currentUsagePage, currentUsagePage + 1, '...', totalPages];
        }
    }

    const pageNumbersHTML = pageNumbers.map(page => {
        if (page === '...') {
            return '<span class="pagination-dots">...</span>';
        }
        return `<button class="pagination-number ${page === currentUsagePage ? 'active' : ''}"
                        onclick="changeUsagePage(${page})">${page}</button>`;
    }).join('');

    paginationContainer.innerHTML = `
        <button class="pagination-arrow"
                onclick="changeUsagePage(${currentUsagePage - 1})"
                ${currentUsagePage === 1 ? 'disabled' : ''}>
            <i class="fas fa-chevron-left"></i>
        </button>
        ${pageNumbersHTML}
        <button class="pagination-arrow"
                onclick="changeUsagePage(${currentUsagePage + 1})"
                ${currentUsagePage === totalPages ? 'disabled' : ''}>
            <i class="fas fa-chevron-right"></i>
        </button>
    `;
}

// 사용방법 페이지 변경
function changeUsagePage(page) {
    const totalPages = Math.ceil(filteredUsageData.length / usagePerPage);
    if (page < 1 || page > totalPages) return;

    currentUsagePage = page;
    renderUsageTableWithPagination();
}

// 사용방법 검색 함수
function searchUsage() {
    const searchInput = document.getElementById('usageSearchInput');
    const searchTerm = searchInput.value.trim().toLowerCase();
    const searchType = document.getElementById('usageSearchType').value;

    if (!searchTerm) {
        filteredUsageData = [...currentUsageData];
    } else {
        filteredUsageData = currentUsageData.filter(item => {
            if (searchType === 'title') {
                return item.title.toLowerCase().includes(searchTerm);
            } else if (searchType === 'author') {
                return item.author.toLowerCase().includes(searchTerm);
            } else if (searchType === 'all') {
                return item.title.toLowerCase().includes(searchTerm) ||
                       item.author.toLowerCase().includes(searchTerm);
            }
            return false;
        });
    }

    currentUsagePage = 1;
    renderUsageTableWithPagination();
}

// 사용방법 상세보기
async function openUsageDetail(id) {
    try {
        const response = await fetch(`/api/support/pages/${id}`);
        if (!response.ok) throw new Error('상세 정보를 불러올 수 없습니다');

        const usage = await response.json();
        const isMobile = window.innerWidth <= 768;

        const formatDate = (dateStr) => {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}.`;
        };

        const attachmentHTML = usage.attachment_name ? `
            <div style="margin-top: 25px; padding: ${isMobile ? '15px' : '18px'}; background: #f0f7ff; border-radius: 8px; border: 1px solid #d0e4ff;">
                <div style="display: flex; ${isMobile ? 'flex-direction: column;' : 'align-items: center;'} gap: ${isMobile ? '10px' : '12px'};">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #1976d2; margin-bottom: 6px; font-size: 14px;">첨부파일</div>
                        <div style="font-size: ${isMobile ? '13px' : '14px'}; color: #555; word-break: break-all;">${usage.attachment_name}</div>
                    </div>
                    <a href="/api/support/attachments/${usage.page_id}"
                       download
                       style="padding: 10px 20px; background: #2786dd; color: white; border-radius: 6px;
                              text-decoration: none; font-size: 14px; font-weight: 500;
                              transition: all 0.3s; white-space: nowrap; ${isMobile ? 'text-align: center;' : ''}"
                       onmouseover="this.style.background='#1976d2'"
                       onmouseout="this.style.background='#2786dd'">
                        다운로드
                    </a>
                </div>
            </div>
        ` : '';

        const contentHTML = `
            <div style="white-space: pre-wrap; font-family: inherit; line-height: 1.8;">${usage.content || '내용이 없습니다.'}</div>
        `;

        const modalHTML = `
            <div id="noticeDetailModal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center; animation: fadeIn 0.3s;" onclick="closeNoticeDetailModal(event)">
                <div style="background: white; max-width: 800px; width: 90%; max-height: 90vh; border-radius: 15px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: slideUp 0.3s;" onclick="event.stopPropagation()">
                    <div style="background: #1976d2; color: white; padding: ${isMobile ? '20px' : '20px 30px'}; border-bottom: 3px solid #1565c0;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 20px;">
                            <div style="flex: 1;">
                                <h2 style="font-size: ${isMobile ? '18px' : '22px'}; margin: 0; font-weight: 600; line-height: 1.4;">${usage.title}</h2>
                            </div>
                            <button onclick="closeNoticeDetailModal()" style="background: rgba(255,255,255,0.15); border: none; color: white; font-size: 28px; cursor: pointer; width: 36px; height: 36px; border-radius: 4px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; flex-shrink: 0; line-height: 1;" onmouseover="this.style.background='rgba(255,255,255,0.25)'" onmouseout="this.style.background='rgba(255,255,255,0.15)'">×</button>
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: ${isMobile ? '15px 20px' : '15px 30px'}; border-bottom: 1px solid #e9ecef;">
                        <div style="display: flex; gap: ${isMobile ? '12px' : '20px'}; flex-wrap: wrap; font-size: 14px; color: #666;">
                            <div style="display: flex; align-items: center; gap: 6px;"><i class="fas fa-user" style="color: #1976d2;"></i><span>${usage.updated_by || '관리자'}</span></div>
                            <div style="display: flex; align-items: center; gap: 6px;"><i class="fas fa-calendar" style="color: #1976d2;"></i><span>${formatDate(usage.updated_at)}</span></div>
                            <div style="display: flex; align-items: center; gap: 6px;"><i class="fas fa-eye" style="color: #1976d2;"></i><span>${usage.view_count || 0}</span></div>
                        </div>
                    </div>
                    <div style="padding: ${isMobile ? '20px' : '30px'}; max-height: calc(90vh - 280px); overflow-y: auto;">${contentHTML}${attachmentHTML}</div>
                    <div style="background: #f8f9fa; padding: ${isMobile ? '15px 20px' : '20px 30px'}; border-top: 1px solid #e9ecef; display: flex; justify-content: flex-end;">
                        <button onclick="closeNoticeDetailModal()" style="padding: 10px 24px; background: #6c757d; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#5a6268'" onmouseout="this.style.background='#6c757d'">닫기</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.body.style.overflow = 'hidden';

    } catch (error) {
        console.error('상세 정보 로드 실패:', error);
        alert('상세 정보를 불러올 수 없습니다.\n' + error.message);
    }
}

// ==================== FAQ 테이블/페이지네이션 함수 ====================

// FAQ 테이블 렌더링 (페이지네이션 적용)
function renderFAQTableWithPagination() {
    const startIndex = (currentFAQPage - 1) * faqPerPage;
    const endIndex = startIndex + faqPerPage;
    const pageData = filteredFAQData.slice(startIndex, endIndex);

    renderFAQTable(pageData);
    renderFAQPagination();
}

// FAQ 테이블 렌더링
function renderFAQTable(faqData) {
    const tbody = document.querySelector('.notices-table tbody');
    const faqStats = document.querySelector('.notices-stats span');

    if (!tbody) return;

    if (filteredFAQData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 50px; color: #999;">
                    <i class="fas fa-search" style="font-size: 48px; margin-bottom: 20px; display: block;"></i>
                    검색 결과가 없습니다.
                </td>
            </tr>
        `;
        if (faqStats) {
            faqStats.innerHTML = '총 <strong>0</strong>건의 FAQ';
        }
        return;
    }

    tbody.innerHTML = faqData.map((item, index) => {
        const actualIndex = filteredFAQData.findIndex(faq => faq.id === item.id);
        const number = actualIndex + 1;

        return `
        <tr class="notices-row" onclick="openFAQDetail(${item.id})">
            <td class="col-number">${number}</td>
            <td class="col-important">
                ${item.is_important ? '<span class="notice-important-badge">중요</span>' : ''}
            </td>
            <td class="col-title">
                <span class="notices-title">${item.title}</span>
                ${item.isNew ? '<span class="new-badge" style="margin-left: 5px;">N</span>' : ''}
                ${item.attachment_name ? '<i class="fas fa-paperclip" style="color: #667eea; margin-left: 5px;" title="' + item.attachment_name + '"></i>' : ''}
            </td>
            <td class="col-author">${item.author}</td>
            <td class="col-date">${item.date}</td>
            <td class="col-views">${item.views}</td>
        </tr>
    `}).join('');

    if (faqStats) {
        faqStats.innerHTML = `총 <strong>${filteredFAQData.length}</strong>건의 FAQ`;
    }
}

// FAQ 페이지네이션 렌더링
function renderFAQPagination() {
    const paginationContainer = document.querySelector('.notices-pagination');
    if (!paginationContainer) return;

    const totalPages = Math.ceil(filteredFAQData.length / faqPerPage);

    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }

    paginationContainer.style.display = 'flex';

    let pageNumbers = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) {
            pageNumbers.push(i);
        }
    } else {
        if (currentFAQPage <= 4) {
            pageNumbers = [1, 2, 3, 4, 5, '...', totalPages];
        } else if (currentFAQPage >= totalPages - 3) {
            pageNumbers = [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
        } else {
            pageNumbers = [1, '...', currentFAQPage - 1, currentFAQPage, currentFAQPage + 1, '...', totalPages];
        }
    }

    const pageNumbersHTML = pageNumbers.map(page => {
        if (page === '...') {
            return '<span class="pagination-dots">...</span>';
        }
        return `<button class="pagination-number ${page === currentFAQPage ? 'active' : ''}"
                        onclick="changeFAQPage(${page})">${page}</button>`;
    }).join('');

    paginationContainer.innerHTML = `
        <button class="pagination-arrow"
                onclick="changeFAQPage(${currentFAQPage - 1})"
                ${currentFAQPage === 1 ? 'disabled' : ''}>
            <i class="fas fa-chevron-left"></i>
        </button>
        ${pageNumbersHTML}
        <button class="pagination-arrow"
                onclick="changeFAQPage(${currentFAQPage + 1})"
                ${currentFAQPage === totalPages ? 'disabled' : ''}>
            <i class="fas fa-chevron-right"></i>
        </button>
    `;
}

// FAQ 페이지 변경
function changeFAQPage(page) {
    const totalPages = Math.ceil(filteredFAQData.length / faqPerPage);
    if (page < 1 || page > totalPages) return;

    currentFAQPage = page;
    renderFAQTableWithPagination();
}

// FAQ 검색 함수
function searchFAQ() {
    const searchInput = document.getElementById('faqSearchInput');
    const searchTerm = searchInput.value.trim().toLowerCase();
    const searchType = document.getElementById('faqSearchType').value;

    if (!searchTerm) {
        filteredFAQData = [...currentFAQData];
    } else {
        filteredFAQData = currentFAQData.filter(item => {
            if (searchType === 'title') {
                return item.title.toLowerCase().includes(searchTerm);
            } else if (searchType === 'author') {
                return item.author.toLowerCase().includes(searchTerm);
            } else if (searchType === 'all') {
                return item.title.toLowerCase().includes(searchTerm) ||
                       item.author.toLowerCase().includes(searchTerm);
            }
            return false;
        });
    }

    currentFAQPage = 1;
    renderFAQTableWithPagination();
}

// FAQ 상세보기
async function openFAQDetail(id) {
    try {
        const response = await fetch(`/api/support/pages/${id}`);
        if (!response.ok) throw new Error('상세 정보를 불러올 수 없습니다');

        const faq = await response.json();
        const isMobile = window.innerWidth <= 768;

        const formatDate = (dateStr) => {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}.`;
        };

        const attachmentHTML = faq.attachment_name ? `
            <div style="margin-top: 25px; padding: ${isMobile ? '15px' : '18px'}; background: #f0f7ff; border-radius: 8px; border: 1px solid #d0e4ff;">
                <div style="display: flex; ${isMobile ? 'flex-direction: column;' : 'align-items: center;'} gap: ${isMobile ? '10px' : '12px'};">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #1976d2; margin-bottom: 6px; font-size: 14px;">첨부파일</div>
                        <div style="font-size: ${isMobile ? '13px' : '14px'}; color: #555; word-break: break-all;">${faq.attachment_name}</div>
                    </div>
                    <a href="/api/support/attachments/${faq.page_id}"
                       download
                       style="padding: 10px 20px; background: #2786dd; color: white; border-radius: 6px;
                              text-decoration: none; font-size: 14px; font-weight: 500;
                              transition: all 0.3s; white-space: nowrap; ${isMobile ? 'text-align: center;' : ''}"
                       onmouseover="this.style.background='#1976d2'"
                       onmouseout="this.style.background='#2786dd'">
                        다운로드
                    </a>
                </div>
            </div>
        ` : '';

        const contentHTML = `
            <div style="white-space: pre-wrap; font-family: inherit; line-height: 1.8;">${faq.content || '내용이 없습니다.'}</div>
        `;

        const modalHTML = `
            <div id="noticeDetailModal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center; animation: fadeIn 0.3s;" onclick="closeNoticeDetailModal(event)">
                <div style="background: white; max-width: 800px; width: 90%; max-height: 90vh; border-radius: 15px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: slideUp 0.3s;" onclick="event.stopPropagation()">
                    <div style="background: #1976d2; color: white; padding: ${isMobile ? '20px' : '20px 30px'}; border-bottom: 3px solid #1565c0;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 20px;">
                            <div style="flex: 1;">
                                <h2 style="font-size: ${isMobile ? '18px' : '22px'}; margin: 0; font-weight: 600; line-height: 1.4;">${faq.title}</h2>
                            </div>
                            <button onclick="closeNoticeDetailModal()" style="background: rgba(255,255,255,0.15); border: none; color: white; font-size: 28px; cursor: pointer; width: 36px; height: 36px; border-radius: 4px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; flex-shrink: 0; line-height: 1;" onmouseover="this.style.background='rgba(255,255,255,0.25)'" onmouseout="this.style.background='rgba(255,255,255,0.15)'">×</button>
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: ${isMobile ? '15px 20px' : '15px 30px'}; border-bottom: 1px solid #e9ecef;">
                        <div style="display: flex; gap: ${isMobile ? '12px' : '20px'}; flex-wrap: wrap; font-size: 14px; color: #666;">
                            <div style="display: flex; align-items: center; gap: 6px;"><i class="fas fa-user" style="color: #1976d2;"></i><span>${faq.updated_by || '관리자'}</span></div>
                            <div style="display: flex; align-items: center; gap: 6px;"><i class="fas fa-calendar" style="color: #1976d2;"></i><span>${formatDate(faq.updated_at)}</span></div>
                            <div style="display: flex; align-items: center; gap: 6px;"><i class="fas fa-eye" style="color: #1976d2;"></i><span>${faq.view_count || 0}</span></div>
                        </div>
                    </div>
                    <div style="padding: ${isMobile ? '20px' : '30px'}; max-height: calc(90vh - 280px); overflow-y: auto;">${contentHTML}${attachmentHTML}</div>
                    <div style="background: #f8f9fa; padding: ${isMobile ? '15px 20px' : '20px 30px'}; border-top: 1px solid #e9ecef; display: flex; justify-content: flex-end;">
                        <button onclick="closeNoticeDetailModal()" style="padding: 10px 24px; background: #6c757d; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#5a6268'" onmouseout="this.style.background='#6c757d'">닫기</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.body.style.overflow = 'hidden';

    } catch (error) {
        console.error('상세 정보 로드 실패:', error);
        alert('상세 정보를 불러올 수 없습니다.\n' + error.message);
    }
}

// 제·개정 절차 상세보기
async function openProcedureDetail(id) {
    try {
        // API에서 상세 정보 가져오기
        const response = await fetch(`/api/support/pages/${id}`);
        if (!response.ok) throw new Error('상세 정보를 불러올 수 없습니다');

        const procedure = await response.json();

        // 모바일 감지
        const isMobile = window.innerWidth <= 768;

        // 날짜 포맷팅
        const formatDate = (dateStr) => {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}.`;
        };

        // 첨부파일 HTML
        const attachmentHTML = procedure.attachment_name ? `
            <div style="margin-top: 25px; padding: ${isMobile ? '15px' : '18px'}; background: #f0f7ff; border-radius: 8px; border: 1px solid #d0e4ff;">
                <div style="display: flex; ${isMobile ? 'flex-direction: column;' : 'align-items: center;'} gap: ${isMobile ? '10px' : '12px'};">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #1976d2; margin-bottom: 6px; font-size: 14px;">첨부파일</div>
                        <div style="font-size: ${isMobile ? '13px' : '14px'}; color: #555; word-break: break-all;">${procedure.attachment_name}</div>
                    </div>
                    <a href="/api/support/attachments/${procedure.page_id}"
                       download
                       style="padding: 10px 20px; background: #2786dd; color: white; border-radius: 6px;
                              text-decoration: none; font-size: 14px; font-weight: 500;
                              transition: all 0.3s; white-space: nowrap; ${isMobile ? 'text-align: center;' : ''}"
                       onmouseover="this.style.background='#1976d2'"
                       onmouseout="this.style.background='#2786dd'">
                        다운로드
                    </a>
                </div>
            </div>
        ` : '';

        // 내용 HTML
        const contentHTML = `
            <div style="white-space: pre-wrap; font-family: inherit; line-height: 1.8;">${procedure.content || '내용이 없습니다.'}</div>
        `;

    // 모달 생성
    const modalHTML = `
        <div id="noticeDetailModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s;
        " onclick="closeNoticeDetailModal(event)">
            <div style="
                background: white;
                max-width: 800px;
                width: 90%;
                max-height: 90vh;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideUp 0.3s;
            " onclick="event.stopPropagation()">
                <!-- 헤더 -->
                <div style="
                    background: #1976d2;
                    color: white;
                    padding: ${isMobile ? '20px' : '20px 30px'};
                    border-bottom: 3px solid #1565c0;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 20px;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                                ${procedure.is_important ? '<span style="background: #c53030; padding: 5px 12px; border-radius: 4px; font-size: 12px; font-weight: 600;">중요</span>' : ''}
                            </div>
                            <h2 style="font-size: ${isMobile ? '18px' : '22px'}; margin: 0; font-weight: 600; line-height: 1.4;">
                                ${procedure.title}
                            </h2>
                        </div>
                        <button onclick="closeNoticeDetailModal()" style="
                            background: rgba(255,255,255,0.2);
                            border: none;
                            color: white;
                            width: 36px;
                            height: 36px;
                            border-radius: 50%;
                            cursor: pointer;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            transition: all 0.2s;
                            flex-shrink: 0;
                        " onmouseover="this.style.background='rgba(255,255,255,0.3)'"
                           onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                            <i class="fas fa-times" style="font-size: 18px;"></i>
                        </button>
                    </div>
                </div>

                <!-- 정보 영역 -->
                <div style="
                    background: #f8f9fa;
                    padding: ${isMobile ? '15px 20px' : '15px 30px'};
                    border-bottom: 1px solid #e9ecef;
                ">
                    <div style="display: flex; gap: ${isMobile ? '12px' : '20px'}; flex-wrap: wrap; font-size: 14px; color: #666;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <i class="fas fa-user" style="color: #1976d2;"></i>
                            <span>${procedure.updated_by || '관리자'}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <i class="fas fa-calendar" style="color: #1976d2;"></i>
                            <span>${formatDate(procedure.updated_at)}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <i class="fas fa-eye" style="color: #1976d2;"></i>
                            <span>${procedure.view_count || 0}</span>
                        </div>
                    </div>
                </div>

                <!-- 내용 영역 -->
                <div style="
                    padding: ${isMobile ? '20px' : '30px'};
                    max-height: calc(90vh - 280px);
                    overflow-y: auto;
                ">
                    <div style="color: #444; font-size: ${isMobile ? '14px' : '15px'};">
                        ${contentHTML}
                    </div>
                    ${attachmentHTML}
                </div>

                <!-- 푸터 -->
                <div style="
                    background: #f8f9fa;
                    padding: ${isMobile ? '15px 20px' : '20px 30px'};
                    border-top: 1px solid #e9ecef;
                    display: flex;
                    justify-content: flex-end;
                ">
                    <button onclick="closeNoticeDetailModal()" style="
                        padding: 10px 24px;
                        background: #6c757d;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        font-size: 14px;
                        font-weight: 500;
                        cursor: pointer;
                        transition: all 0.2s;
                    " onmouseover="this.style.background='#5a6268'"
                       onmouseout="this.style.background='#6c757d'">
                        닫기
                    </button>
                </div>
            </div>
        </div>
    `;

        // 모달을 body에 추가
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // body 스크롤 막기
        document.body.style.overflow = 'hidden';

    } catch (error) {
        console.error('상세 정보 로드 실패:', error);
        alert('상세 정보를 불러올 수 없습니다.\n' + error.message);
    }
}

// FAQ 토글 함수
function toggleFAQ(element) {
    const answer = element.nextElementSibling;
    const isActive = element.classList.contains('active');
    
    // 모든 FAQ 닫기
    document.querySelectorAll('.faq-question').forEach(q => q.classList.remove('active'));
    document.querySelectorAll('.faq-answer').forEach(a => a.classList.remove('active'));
    
    // 클릭한 FAQ만 열기 (이미 열려있지 않은 경우)
    if (!isActive) {
        element.classList.add('active');
        answer.classList.add('active');
    }
}

//=============== 지원 탭===================

function resetAllScrolls() {
    // 1. 전체 윈도우 스크롤 리셋 (한 번만)
    window.scrollTo(0, 0);

    const contentBodyElements = document.querySelectorAll('.content-body');
    console.log('content-body 요소 개수:', contentBodyElements.length);
    contentBodyElements.forEach((element, index) => {
        element.scrollTop = 0;
        element.scrollLeft = 0;
        // 강제로 스크롤 위치 변경
        element.scroll(0, 0);
    });

    // 2. 주요 컨텐츠 영역 스크롤 리셋
    const contentBody = document.getElementById('contentBody');
    if (contentBody) {
        contentBody.scrollTop = 0;
    }

    // 3. 기타 스크롤 가능한 요소 리셋 (필요한 것만)
    const scrollContainers = document.querySelectorAll(
        '.regulation-detail, .main-content, .tree-menu'
    );
    scrollContainers.forEach(container => {
        if (container.scrollTop > 0) {
            container.scrollTop = 0;
        }
    });
}

/* ========================================
   워터마크 기능
   ======================================== */

/**
 * 워터마크 설정 객체
 */
const WatermarkConfig = {
    enabled: true,           // 워터마크 활성화 여부
    opacity: 0.08,          // 투명도 (0.05 ~ 0.15 권장)
    fontSize: 14,           // 글자 크기 (px)
    rotation: -30,          // 회전 각도
    spacing: { x: 60, y: 40 } // 워터마크 간격
};

/**
 * 사용자 정보로 워터마크 텍스트 생성
 * @param {Object} userInfo - 사용자 정보 객체
 * @returns {string} 워터마크 텍스트
 */
function createWatermarkText(userInfo) {
    const name = userInfo.name || '사용자';
    const empNo = userInfo.empNo || userInfo.employeeNumber || '';
    const dept = userInfo.dept || userInfo.department || '';
    const timestamp = new Date().toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
    
    // 워터마크 텍스트 구성
    let text = name;
    if (empNo) text += ` (${empNo})`;
    if (dept) text += `\n${dept}`;
    text += `\n${timestamp}`;
    
    return text;
}

/**
 * 워터마크 HTML 요소 생성
 * @param {string} text - 워터마크에 표시할 텍스트
 * @param {number} repeatCount - 반복 횟수
 * @returns {HTMLElement} 워터마크 오버레이 요소
 */
function createWatermarkElement(text, repeatCount = 100) {
    // 기존 워터마크 제거
    const existingWatermark = document.querySelector('.watermark-overlay');
    if (existingWatermark) {
        existingWatermark.remove();
    }
    
    // 워터마크 오버레이 생성
    const overlay = document.createElement('div');
    overlay.className = 'watermark-overlay';
    overlay.style.opacity = WatermarkConfig.opacity;
    
    // 워터마크 패턴 생성
    const pattern = document.createElement('div');
    pattern.className = 'watermark-pattern';
    pattern.style.transform = `rotate(${WatermarkConfig.rotation}deg)`;
    
    // 워터마크 아이템 반복 생성
    for (let i = 0; i < repeatCount; i++) {
        const item = document.createElement('div');
        item.className = 'watermark-item';
        item.style.fontSize = `${WatermarkConfig.fontSize}px`;
        item.style.padding = `${WatermarkConfig.spacing.y}px ${WatermarkConfig.spacing.x}px`;
        item.innerHTML = text.replace(/\n/g, '<br>');
        pattern.appendChild(item);
    }
    
    overlay.appendChild(pattern);
    return overlay;
}

/**
 * 특정 컨테이너에 워터마크 적용
 * @param {string|HTMLElement} container - 컨테이너 선택자 또는 요소
 * @param {Object} userInfo - 사용자 정보 객체
 */
function applyWatermark(container, userInfo) {
    if (!WatermarkConfig.enabled) return;
    
    const containerEl = typeof container === 'string' 
        ? document.querySelector(container) 
        : container;
    
    if (!containerEl) {
        console.warn('워터마크 컨테이너를 찾을 수 없습니다:', container);
        return;
    }
    
    // 컨테이너에 워터마크 클래스 추가
    containerEl.classList.add('watermark-container');
    
    // 기존 내용을 워터마크 컨텐츠로 감싸기 (이미 감싸져 있지 않은 경우)
    if (!containerEl.querySelector('.watermark-content')) {
        const content = document.createElement('div');
        content.className = 'watermark-content';
        while (containerEl.firstChild) {
            content.appendChild(containerEl.firstChild);
        }
        containerEl.appendChild(content);
    }
    
    // 워터마크 텍스트 생성
    const watermarkText = createWatermarkText(userInfo);
    
    // 워터마크 요소 생성 및 추가
    const watermarkEl = createWatermarkElement(watermarkText);
    containerEl.insertBefore(watermarkEl, containerEl.firstChild);
}

/**
 * 워터마크 제거
 * @param {string|HTMLElement} container - 컨테이너 선택자 또는 요소
 */
function removeWatermark(container) {
    const containerEl = typeof container === 'string' 
        ? document.querySelector(container) 
        : container;
    
    if (!containerEl) return;
    
    const overlay = containerEl.querySelector('.watermark-overlay');
    if (overlay) {
        overlay.remove();
    }
    containerEl.classList.remove('watermark-container');
}

/**
 * 워터마크 활성화/비활성화 토글
 * @param {boolean} enabled - 활성화 여부
 */
function toggleWatermark(enabled) {
    WatermarkConfig.enabled = enabled;
    const containers = document.querySelectorAll('.watermark-container');
    containers.forEach(container => {
        if (enabled) {
            container.classList.remove('watermark-disabled');
        } else {
            container.classList.add('watermark-disabled');
        }
    });
}

/**
 * 워터마크 설정 업데이트
 * @param {Object} config - 설정 객체
 */
function updateWatermarkConfig(config) {
    Object.assign(WatermarkConfig, config);
}

/**
 * 현재 사용자 정보 저장 (백엔드에서 받은 정보)
 */
let currentUserInfo = null;

/**
 * 사용자 정보 설정 (백엔드에서 호출)
 * @param {Object} userInfo - 사용자 정보
 */
function setUserInfo(userInfo) {
    currentUserInfo = userInfo;
    console.log('사용자 정보 설정됨:', userInfo.name);
}

/**
 * 규정 본문에 워터마크 자동 적용
 * showRegulationDetail 함수 호출 시 사용
 */
function applyWatermarkToContent() {
    if (!currentUserInfo) {
        console.log('사용자 정보가 없어 워터마크를 적용하지 않습니다.');
        return;
    }
    
    // contentBody에 워터마크 적용
    const contentBody = document.getElementById('contentBody');
    if (contentBody && contentBody.style.display !== 'none') {
        applyWatermark(contentBody, currentUserInfo);
    }
}

// 전역으로 노출
window.WatermarkConfig = WatermarkConfig;
window.applyWatermark = applyWatermark;
window.removeWatermark = removeWatermark;
window.toggleWatermark = toggleWatermark;
window.setUserInfo = setUserInfo;
window.applyWatermarkToContent = applyWatermarkToContent;

// ================================================
// 메인 페이지 정보 탭 관련 함수
// ================================================

// 정보 탭 전환
function switchInfoTab(tabName, clickedTab) {
    // 같은 패널 내의 탭들만 처리
    const panel = clickedTab.closest('.info-panel');

    // 모든 탭 비활성화
    panel.querySelectorAll('.info-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // 클릭한 탭 활성화
    clickedTab.classList.add('active');

    // 콘텐츠 전환
    if (tabName === 'notices') {
        document.getElementById('noticesPanel').style.display = 'block';
        document.getElementById('formsPanel').style.display = 'none';
    } else if (tabName === 'forms') {
        document.getElementById('noticesPanel').style.display = 'none';
        document.getElementById('formsPanel').style.display = 'block';
    }
}

// 제·개정 사규/외규 탭 전환
function switchRevisionTab(tabName, clickedTab) {
    const panel = clickedTab.closest('.info-panel');

    // 모든 탭 비활성화
    panel.querySelectorAll('.info-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // 클릭한 탭 활성화
    clickedTab.classList.add('active');

    // 콘텐츠 전환
    const revisionPanel = document.getElementById('revisionPanel');
    const externalPanel = document.getElementById('externalRevisionPanel');
    if (tabName === 'sagyu') {
        if (revisionPanel) revisionPanel.style.display = 'block';
        if (externalPanel) externalPanel.style.display = 'none';
    } else if (tabName === 'oegyu') {
        if (revisionPanel) revisionPanel.style.display = 'none';
        if (externalPanel) externalPanel.style.display = 'block';
    }
}

function switchNoticeTab(tabName, clickedTab) {
    const panel = clickedTab.closest('.info-panel');

    panel.querySelectorAll('.info-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    clickedTab.classList.add('active');

    const noticesPanel = document.getElementById('noticesPanel');
    const formsPanel = document.getElementById('formsPanel');
    if (tabName === 'notices') {
        if (noticesPanel) noticesPanel.style.display = 'block';
        if (formsPanel) formsPanel.style.display = 'none';
    } else if (tabName === 'forms') {
        if (noticesPanel) noticesPanel.style.display = 'none';
        if (formsPanel) formsPanel.style.display = 'block';
    }
}

// 메인 페이지 정보 로드
async function loadMainPageInfo() {
    loadRevisionInfo();
    loadExternalRevisionInfo();
    loadNoticesInfo();
    loadFormsInfo();
}

// 사규 제·개정 정보 로드
async function loadRevisionInfo() {
    const tbody = document.getElementById('revisionTableBody');
    if (!tbody) return;
    
    try {
        // hospitalRegulations에서 최근 개정된 내규 가져오기
        const revisionData = [];
        
        if (hospitalRegulations && Object.keys(hospitalRegulations).length > 0) {
            Object.entries(hospitalRegulations).forEach(([chapter, chapterData]) => {
                if (chapterData.regulations) {
                    chapterData.regulations.forEach(reg => {
                        const docInfo = reg.detail?.documentInfo || reg.detailData?.문서정보 || {};
                        const revisionDate = docInfo.최종개정일 || docInfo.제정일 || '';
                        
                        if (revisionDate && revisionDate !== '-') {
                            revisionData.push({
                                name: reg.name,
                                code: reg.code,
                                chapter: chapter,
                                date: revisionDate,
                                type: docInfo.최종개정일 ? '개정' : '제정'
                            });
                        }
                    });
                }
            });
        }
        
        // 날짜순 정렬 (최신순)
        revisionData.sort((a, b) => {
            const dateA = parseKoreanDate(a.date) || new Date(0);
            const dateB = parseKoreanDate(b.date) || new Date(0);
            return dateB - dateA;
        });
        
        // 상위 7개만 표시
        const displayData = revisionData.slice(0, 7);
        
        if (displayData.length === 0) {
            tbody.innerHTML = '<div class="info-table-row"><span class="col-name" style="text-align:center;">데이터가 없습니다.</span></div>';
            return;
        }
        
        tbody.innerHTML = displayData.map(item => {
            const badgeClass = item.type === '개정' ? 'revision' : 'enact';
            return `
                <div class="info-table-row" onclick="openRegulationByCode('${item.chapter}', '${item.code}')">
                    <span class="col-type"><span class="badge-type ${badgeClass}">${item.type}</span></span>
                    <span class="col-name">${item.name}</span>
                    <span class="col-date">${item.date}</span>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('사규 제·개정 정보 로드 실패:', error);
        tbody.innerHTML = '<div class="info-table-row"><span class="col-name">로드 실패</span></div>';
    }
}

// 외규 제·개정 정보 로드
async function loadExternalRevisionInfo() {
    const tbody = document.getElementById('externalRevisionTableBody');
    if (!tbody) return;

    try {
        tbody.innerHTML = '<div class="info-table-row"><span class="col-name" style="text-align:center;">준비 중입니다.</span></div>';
    } catch (error) {
        console.error('외규 제·개정 정보 로드 실패:', error);
    }
}

// 공지사항 정보 로드
async function loadNoticesInfo() {
    const tbody = document.getElementById('noticesTableBody');
    if (!tbody) return;
    
    try {
        const response = await fetch('/api/notices/?is_active=true');
        const data = await response.json();
        
        const notices = Array.isArray(data) ? data : (data.data || []);
        const displayData = notices.slice(0, 7);
        
        if (displayData.length === 0) {
            tbody.innerHTML = '<div class="info-table-row"><span class="col-title" style="text-align:center;">등록된 공지사항이 없습니다.</span></div>';
            return;
        }
        
        tbody.innerHTML = displayData.map(item => {
            const date = item.created_at ? formatDate(item.created_at) : '-';
            return `
                <div class="info-table-row" onclick="openNoticeDetail(${item.notice_id})">
                    <span class="col-title">${item.title}</span>
                    <span class="col-date">${date}</span>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('공지사항 로드 실패:', error);
        tbody.innerHTML = '<div class="info-table-row"><span class="col-title">로드 실패</span></div>';
    }
}

// 별표·서식 정보 로드
async function loadFormsInfo() {
    const tbody = document.getElementById('formsTableBody');
    if (!tbody) return;
    
    try {
        // 별표·서식 API가 있다면 호출, 없으면 빈 상태
        tbody.innerHTML = '<div class="info-table-row"><span class="col-title" style="text-align:center;">준비 중입니다.</span></div>';
    } catch (error) {
        console.error('별표·서식 로드 실패:', error);
    }
}

// 내규 코드로 열기
function openRegulationByCode(chapter, code) {
    const regulation = getChapterData(chapter)?.regulations?.find(r => r.code === code);
    if (regulation) {
        showRegulationDetail(regulation, chapter);
    }
}

// 별표·서식 페이지 (임시)
function showFormsPage() {
    showSupportPage();
}

// DOMContentLoaded에서 호출
document.addEventListener('DOMContentLoaded', function() {
    // 데이터 로드 후 메인 페이지 정보 로드
    setTimeout(loadMainPageInfo, 1000);
    // 초기 로드 시 검색어 입력란 포커스
    setTimeout(() => {
        const searchInput = document.getElementById('mainSearchInput');
        if (searchInput && document.getElementById('mainPageContent')?.style.display !== 'none') {
            searchInput.focus();
        }
    }, 500);
});

// ========== 본문검색 기능 ==========
let contentSearchMatches = [];
let contentSearchCurrentIndex = -1;

function toggleContentSearch() {
    let searchBar = document.querySelector('.content-search-bar');
    if (!searchBar) {
        // 검색 바 생성
        const regulationDetail = document.querySelector('.regulation-detail');
        if (!regulationDetail) return;
        searchBar = document.createElement('div');
        searchBar.className = 'content-search-bar';
        searchBar.innerHTML = `
            <input type="text" placeholder="본문에서 검색..." id="contentSearchInput"
                   onkeydown="if(event.key==='Enter'){event.preventDefault();searchInContent();}">
            <button onclick="searchInContent()">검색</button>
            <button onclick="navigateContentSearch(-1)">이전</button>
            <button onclick="navigateContentSearch(1)">다음</button>
            <span class="search-count" id="contentSearchCount"></span>
            <button onclick="closeContentSearch()">닫기</button>
        `;
        regulationDetail.insertBefore(searchBar, regulationDetail.firstChild);
    }
    searchBar.classList.toggle('show');
    if (searchBar.classList.contains('show')) {
        document.getElementById('contentSearchInput')?.focus();
    } else {
        clearContentSearchHighlights();
    }
}

function searchInContent() {
    clearContentSearchHighlights();
    const keyword = document.getElementById('contentSearchInput')?.value.trim();
    if (!keyword) return;

    const contentEl = document.querySelector('.regulation-content');
    if (!contentEl) return;

    const walker = document.createTreeWalker(contentEl, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);

    contentSearchMatches = [];
    const regex = new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');

    textNodes.forEach(node => {
        const text = node.textContent;
        if (!regex.test(text)) return;
        regex.lastIndex = 0;

        const frag = document.createDocumentFragment();
        let lastIndex = 0;
        let match;
        while ((match = regex.exec(text)) !== null) {
            if (match.index > lastIndex) {
                frag.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
            }
            const span = document.createElement('span');
            span.className = 'content-search-highlight';
            span.textContent = match[0];
            frag.appendChild(span);
            contentSearchMatches.push(span);
            lastIndex = regex.lastIndex;
        }
        if (lastIndex < text.length) {
            frag.appendChild(document.createTextNode(text.slice(lastIndex)));
        }
        node.parentNode.replaceChild(frag, node);
    });

    const countEl = document.getElementById('contentSearchCount');
    if (countEl) countEl.textContent = contentSearchMatches.length > 0 ? `${contentSearchMatches.length}건` : '0건';

    if (contentSearchMatches.length > 0) {
        contentSearchCurrentIndex = 0;
        contentSearchMatches[0].classList.add('current');
        contentSearchMatches[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function navigateContentSearch(direction) {
    if (contentSearchMatches.length === 0) return;
    contentSearchMatches[contentSearchCurrentIndex]?.classList.remove('current');
    contentSearchCurrentIndex = (contentSearchCurrentIndex + direction + contentSearchMatches.length) % contentSearchMatches.length;
    contentSearchMatches[contentSearchCurrentIndex].classList.add('current');
    contentSearchMatches[contentSearchCurrentIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
    const countEl = document.getElementById('contentSearchCount');
    if (countEl) countEl.textContent = `${contentSearchCurrentIndex + 1}/${contentSearchMatches.length}건`;
}

function clearContentSearchHighlights() {
    document.querySelectorAll('.content-search-highlight').forEach(el => {
        const parent = el.parentNode;
        parent.replaceChild(document.createTextNode(el.textContent), el);
        parent.normalize();
    });
    contentSearchMatches = [];
    contentSearchCurrentIndex = -1;
    const countEl = document.getElementById('contentSearchCount');
    if (countEl) countEl.textContent = '';
}

function closeContentSearch() {
    clearContentSearchHighlights();
    const searchBar = document.querySelector('.content-search-bar');
    if (searchBar) searchBar.classList.remove('show');
}

// ========== 2단 규정 비교 모드 ==========
let isComparisonMode = false;
let comparisonLeftRegulation = null;
let comparisonLeftChapter = null;
let comparisonOriginalHtml = '';

function toggleColumnView() {
    if (isComparisonMode) {
        exitComparisonMode();
        return;
    }

    const contentBody = document.getElementById('contentBody');
    if (!contentBody || !currentRegulation) return;

    // 비교 모드 진입
    isComparisonMode = true;
    comparisonLeftRegulation = currentRegulation;
    comparisonLeftChapter = currentChapter;

    // 현재 콘텐츠를 좌측 패널로 보존
    comparisonOriginalHtml = contentBody.innerHTML;

    const leftContent = contentBody.innerHTML;

    contentBody.innerHTML = `
        <div class="comparison-container">
            <div class="comparison-header">
                <span><i class="fas fa-columns"></i> 규정 비교 모드 — 사이드바에서 비교할 규정을 선택하세요</span>
            </div>
            <div class="comparison-panels">
                <div class="comparison-panel" id="comparisonLeft">
                    <div class="comparison-panel-header">
                        <strong>${currentRegulation.code}. ${currentRegulation.name}</strong>
                    </div>
                    <div class="comparison-panel-body">${leftContent}</div>
                </div>
                <div class="comparison-divider"></div>
                <div class="comparison-panel" id="comparisonRight">
                    <div class="comparison-panel-header">
                        <strong>비교 대상</strong>
                    </div>
                    <div class="comparison-panel-body">
                        <div class="comparison-placeholder">
                            <i class="fas fa-arrow-left" style="font-size: 32px; margin-bottom: 15px;"></i>
                            <p>사이드바에서 비교할 규정을 선택하세요</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // 부모 content-body의 스크롤을 비활성화 (각 패널이 독립 스크롤)
    const contentBodyEl = contentBody.closest('.content-body');
    if (contentBodyEl) contentBodyEl.style.overflow = 'hidden';

    // 사이드바가 접혀있으면 자동 펼침
    const sidebarWrap = document.getElementById('sidebarWrapper');
    if (sidebarWrap && sidebarWrap.classList.contains('collapsed')) {
        sidebarWrap.classList.remove('collapsed');
        safeSetStorage('sidebarCollapsed', '0');
    }

    // 버튼 텍스트 변경
    const btn = document.getElementById('btnColumnToggle');
    if (btn) {
        btn.classList.add('active');
        btn.textContent = '비교종료';
    }
}

function exitComparisonMode() {
    isComparisonMode = false;

    // 부모 content-body 스크롤 복원
    const contentBodyEl = document.getElementById('contentBody');
    const parentBody = contentBodyEl ? contentBodyEl.closest('.content-body') : null;
    if (parentBody) parentBody.style.overflow = '';

    const btn = document.getElementById('btnColumnToggle');
    if (btn) {
        btn.classList.remove('active');
        btn.textContent = '2단보기';
    }

    // 원래 규정 다시 로드
    if (comparisonLeftRegulation && comparisonLeftChapter) {
        showRegulationDetailWithoutSidebarUpdate(comparisonLeftRegulation, comparisonLeftChapter);
    }
    comparisonLeftRegulation = null;
    comparisonLeftChapter = null;
    comparisonOriginalHtml = '';
}

async function loadComparisonRight(regulation, chapter) {
    const rightPanel = document.getElementById('comparisonRight');
    if (!rightPanel) return;

    // 헤더 업데이트
    const header = rightPanel.querySelector('.comparison-panel-header');
    if (header) {
        header.innerHTML = `<strong>${regulation.code}. ${regulation.name}</strong>`;
    }

    const body = rightPanel.querySelector('.comparison-panel-body');
    if (!body) return;

    body.innerHTML = '<div class="comparison-placeholder"><p>규정 로딩 중...</p></div>';

    try {
        // 파일명 가져오기
        const fileName = regulation.detail?.documentInfo?.파일명;
        if (!fileName) {
            body.innerHTML = '<div class="comparison-placeholder"><p>규정 파일 정보를 찾을 수 없습니다.</p></div>';
            return;
        }

        const detailData = await loadRegulationDetail(fileName);
        if (!detailData || !detailData.조문내용) {
            body.innerHTML = '<div class="comparison-placeholder"><p>규정 데이터를 불러올 수 없습니다.</p></div>';
            return;
        }

        // 메타 정보 생성
        const docInfo = detailData.문서정보 || detailData.document_info || {};
        let metaHtml = `
            <div class="regulation-meta-container">
                <table class="regulation-meta-table">
                    <tr>
                        <th class="header-cell">제정일</th>
                        <td class="content-cell" style="text-align:center;">${docInfo.제정일 || '-'}</td>
                        <th class="header-cell" style="border-left:1px solid #000">최종개정일</th>
                        <td class="content-cell" style="text-align:center;">${docInfo.최종개정일 || '-'}</td>
                    </tr>
                    <tr>
                        <th class="header-cell">소관부서</th>
                        <td class="content-cell" colspan="3">${docInfo.소관부서 || '-'}</td>
                    </tr>
                </table>
            </div>
        `;

        // 조문 내용 렌더링
        const contentParts = [];
        let previousArticle = null;

        detailData.조문내용.forEach((article) => {
            if (!article) return;

            if (article.레벨 === 0) {
                if (article.번호 && /^제\d+(장|절)$/.test(article.번호)) {
                    contentParts.push(`<div class="chapter-title">${article.번호} ${article.내용 || ''}</div>`);
                }
                previousArticle = article;
                return;
            }

            if (article.레벨 === 1 && !article.번호 && /^제\d+절/.test((article.내용 || '').replace(/<[^>]+>/g, '').trim())) {
                contentParts.push(`<div class="section-title">${article.내용}</div>`);
                previousArticle = article;
                return;
            }

            let paddingLeft = 0;
            switch(article.레벨) {
                case 1: paddingLeft = 0; break;
                case 2: paddingLeft = 20; break;
                case 3: paddingLeft = 60; break;
                case 4: paddingLeft = 80; break;
                case 5: paddingLeft = 105; break;
                default: paddingLeft = 125; break;
            }

            let additionalStyle = '';
            if (previousArticle && article.레벨 === 2 && (previousArticle.레벨 >= 3 || previousArticle.레벨 === 2)) {
                additionalStyle = 'margin-top: 15px;';
            }
            if (article.정렬 === 'center') additionalStyle += 'text-align: center;';
            if (article.글꼴크기) additionalStyle += ` font-size: ${article.글꼴크기}pt;`;

            let className = article.레벨 === 1 ? 'article-title' : (article.레벨 === 2 ? 'article-item' : 'article-sub-item');

            let displayText = article.번호 && article.레벨 === 1
                ? `<b>${article.번호}</b> ${article.내용}`
                : (article.번호 ? `${article.번호} ${article.내용}` : article.내용);

            if (className === 'article-item' && article.레벨 === 2) {
                contentParts.push(`<div class="${className}" style="padding-left: 35px; text-indent: -15px; ${additionalStyle}">${displayText}</div>`);
            } else if (className === 'article-sub-item') {
                contentParts.push(`<div class="${className}" style="padding-left: ${paddingLeft}px; text-indent: -20px;">${displayText}</div>`);
            } else {
                contentParts.push(`<div class="${className}" style="padding-left: ${paddingLeft}px; ${additionalStyle}">${displayText}</div>`);
            }

            previousArticle = article;

            if (article.관련이미지 && article.관련이미지.length > 0) {
                article.관련이미지.forEach(img => {
                    contentParts.push(`<div style="margin: 10px 0; padding-left: ${paddingLeft + 20}px;">
                        <img src="${img.file_path}" style="max-width: 100%; height: auto; border: 1px solid #e0e0e0; border-radius: 4px;">
                    </div>`);
                });
            }
        });

        const docFontFamily = detailData.문서정보?.기본글꼴;
        const regFontStyle = docFontFamily ? ` style="font-family: '${docFontFamily}', sans-serif;"` : '';

        body.innerHTML = `
            <div class="regulation-detail mal-font">
                <div class="regulation-header">${metaHtml}</div>
                <div class="regulation-content"${regFontStyle}>${contentParts.join('')}</div>
            </div>
        `;
    } catch (error) {
        console.error('비교 규정 로드 실패:', error);
        body.innerHTML = '<div class="comparison-placeholder"><p>규정 데이터를 불러오는 중 오류가 발생했습니다.</p></div>';
    }
}

// ========== 전문다운(DOCX) 기능 ==========
async function downloadRegulationPdf(regulationCode, regulationName) {
    try {
        const response = await fetch(`/api/v1/docx/download/${encodeURIComponent(regulationCode)}`);
        if (response.ok) {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('json')) {
                const result = await response.json();
                showToast(result.error || `"${regulationName}" 다운로드 파일을 찾을 수 없습니다.`, 'error');
                return;
            }
            // Content-Disposition 헤더에서 원본 파일명 추출
            let fileName = `${regulationName}.docx`;
            const disposition = response.headers.get('content-disposition');
            if (disposition) {
                // filename*=utf-8'' 형식 우선
                const utf8Match = disposition.match(/filename\*=(?:UTF-8|utf-8)''(.+)/i);
                if (utf8Match) {
                    fileName = decodeURIComponent(utf8Match[1]);
                } else {
                    const match = disposition.match(/filename="?([^";\n]+)"?/i);
                    if (match) fileName = decodeURIComponent(match[1]);
                }
            }
            const blob = await response.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
            return;
        }
        showToast(`"${regulationName}" 다운로드 파일을 찾을 수 없습니다.`, 'error');
    } catch (error) {
        console.error('DOCX 다운로드 중 오류:', error);
        showToast('다운로드 중 오류가 발생했습니다.', 'error');
    }
}

// ========== 안내사항 사이드 패널 ==========
let _regulationNoticesCache = {};

function toggleRegulationNoticePanel() {
    const panel = document.getElementById('regulationNoticePanel');
    const overlay = document.getElementById('regulationNoticeOverlay');
    if (!panel) return;

    if (panel.classList.contains('show')) {
        closeRegulationNoticePanel();
    } else {
        panel.classList.add('show');
        if (overlay) overlay.classList.add('show');
        loadRegulationNotices();
    }
}

function closeRegulationNoticePanel() {
    const panel = document.getElementById('regulationNoticePanel');
    const overlay = document.getElementById('regulationNoticeOverlay');
    if (panel) panel.classList.remove('show');
    if (overlay) overlay.classList.remove('show');
}

function escapeNoticeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function loadRegulationNotices() {
    const body = document.getElementById('regulationNoticePanelBody');
    const footer = document.getElementById('regulationNoticePanelFooter');
    if (!body) return;

    const regulationCode = currentRegulation?.code;
    if (!regulationCode) {
        body.innerHTML = '<div class="regulation-notice-empty">규정을 선택해주세요.</div>';
        return;
    }

    try {
        const response = await fetch(`/api/regulation-notices/${encodeURIComponent(regulationCode)}`);
        if (!response.ok) throw new Error('API 오류');
        const data = await response.json();
        const notices = Array.isArray(data) ? data : (data.data || []);

        // 캐시 저장
        _regulationNoticesCache = {};
        notices.forEach(n => { _regulationNoticesCache[n.id] = n; });

        const isAdminUser = typeof isAdmin === 'function' && isAdmin();

        if (notices.length === 0) {
            body.innerHTML = '<div class="regulation-notice-empty">등록된 안내사항이 없습니다.</div>';
        } else {
            body.innerHTML = notices.map(notice => `
                <div class="regulation-notice-item" data-id="${notice.id}">
                    ${notice.title ? `<div class="regulation-notice-title">${escapeNoticeHtml(notice.title)}</div>` : ''}
                    <div class="regulation-notice-meta">
                        ${escapeNoticeHtml(notice.created_by || '관리자')} | ${formatDate(notice.created_at)}
                    </div>
                    <div class="regulation-notice-content">${escapeNoticeHtml(notice.content)}</div>
                    ${isAdminUser ? `
                        <div class="regulation-notice-actions">
                            <button onclick="editRegulationNotice(${notice.id})" class="btn-notice-edit">수정</button>
                            <button onclick="deleteRegulationNotice(${notice.id})" class="btn-notice-delete">삭제</button>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        }

        // 관리자인 경우 작성 버튼 표시
        if (footer && isAdminUser) {
            footer.style.display = 'block';
        }
    } catch (error) {
        console.warn('안내사항 로드:', error);
        body.innerHTML = '<div class="regulation-notice-empty">안내사항을 불러올 수 없습니다.</div>';
    }
}

function showRegulationNoticeForm(editId, editTitle, editCreatedBy, editContent) {
    const body = document.getElementById('regulationNoticePanelBody');
    if (!body) return;

    const existingForm = body.querySelector('.regulation-notice-form');
    if (existingForm) { existingForm.remove(); }

    const isEdit = editId != null;
    const form = document.createElement('div');
    form.className = 'regulation-notice-form';
    form.innerHTML = `
        <input type="text" id="noticeFormTitle" placeholder="제목" value="${isEdit ? escapeNoticeHtml(editTitle || '') : ''}">
        <input type="text" id="noticeFormCreatedBy" placeholder="작성자" value="${isEdit ? escapeNoticeHtml(editCreatedBy || '') : escapeNoticeHtml(window.__currentUser?.full_name || '관리자')}">
        <textarea id="noticeFormContent" placeholder="안내사항 내용을 입력하세요...">${isEdit ? escapeNoticeHtml(editContent || '') : ''}</textarea>
        <div class="form-actions">
            <button onclick="this.closest('.regulation-notice-form').remove()">취소</button>
            <button class="btn-save" onclick="saveRegulationNotice(${isEdit ? editId : 'null'})">${isEdit ? '수정' : '저장'}</button>
        </div>
    `;
    body.insertBefore(form, body.firstChild);
    form.querySelector('#noticeFormTitle')?.focus();
}

function editRegulationNotice(noticeId) {
    const n = _regulationNoticesCache[noticeId];
    if (!n) return;
    showRegulationNoticeForm(noticeId, n.title || '', n.created_by || '', n.content || '');
}

async function saveRegulationNotice(editId) {
    const title = document.getElementById('noticeFormTitle')?.value?.trim() || '';
    const createdBy = document.getElementById('noticeFormCreatedBy')?.value?.trim() || '';
    const content = document.getElementById('noticeFormContent')?.value?.trim();
    if (!content) { showToast('내용을 입력해주세요.', 'warning'); return; }

    const regulationCode = currentRegulation?.code;
    if (!regulationCode) return;

    try {
        const isEdit = editId != null;
        const url = isEdit
            ? `/api/regulation-notices/${encodeURIComponent(regulationCode)}/${editId}`
            : `/api/regulation-notices/${encodeURIComponent(regulationCode)}`;

        const body = isEdit
            ? { title, content }
            : { title, content, created_by: createdBy };

        const response = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!response.ok) throw new Error('저장 실패');
        showToast(isEdit ? '안내사항이 수정되었습니다.' : '안내사항이 저장되었습니다.', 'success');
        loadRegulationNotices();
    } catch (error) {
        console.error('안내사항 저장 실패:', error);
        showToast('저장에 실패했습니다.', 'error');
    }
}

async function deleteRegulationNotice(noticeId) {
    if (!confirm('이 안내사항을 삭제하시겠습니까?')) return;

    const regulationCode = currentRegulation?.code;
    if (!regulationCode) return;

    try {
        const response = await fetch(
            `/api/regulation-notices/${encodeURIComponent(regulationCode)}/${noticeId}`,
            { method: 'DELETE' }
        );
        if (!response.ok) throw new Error('삭제 실패');
        showToast('안내사항이 삭제되었습니다.', 'success');
        loadRegulationNotices();
    } catch (error) {
        console.error('안내사항 삭제 실패:', error);
        showToast('삭제에 실패했습니다.', 'error');
    }
}

// ========== 복사/붙여넣기 제한 ==========
(function() {
    function isRegulationContent(el) {
        if (!el || typeof el.closest !== 'function') return false;
        return el.closest('.regulation-content') || el.closest('.regulation-detail');
    }

    document.addEventListener('copy', function(e) {
        if (isRegulationContent(e.target)) { e.preventDefault(); }
    });
    document.addEventListener('cut', function(e) {
        if (isRegulationContent(e.target)) { e.preventDefault(); }
    });
    document.addEventListener('selectstart', function(e) {
        if (isRegulationContent(e.target)) { e.preventDefault(); }
    });
    document.addEventListener('contextmenu', function(e) {
        if (isRegulationContent(e.target)) { e.preventDefault(); }
    });
    document.addEventListener('keydown', function(e) {
        if (!isRegulationContent(e.target)) return;
        // Ctrl+C, Ctrl+A, Ctrl+X 차단
        if (e.ctrlKey && (e.key === 'c' || e.key === 'a' || e.key === 'x' || e.key === 'C' || e.key === 'A' || e.key === 'X')) {
            e.preventDefault();
        }
    });
})();
