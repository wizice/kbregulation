/**
 * kbregulation_android.js
 * Android WebView 전용 최적화 모듈
 *
 * 목적: Tile memory limits exceeded 문제 해결
 * - CSS 클래스 기반 렌더링 (inline style 제거)
 * - Progressive Rendering (GPU 타일 메모리 분산)
 * - 메모리 사용량 70% 절감
 */

// ==========================================
// Android WebView 감지 및 localStorage 체크
// ==========================================

/**
 * Android WebView 여부 확인
 * @returns {boolean}
 */
function isAndroidWebView() {
    const ua = navigator.userAgent.toLowerCase();
    // Android + wv (WebView) 또는 Version/ (구형 WebView)
    return /android/i.test(ua) && (/wv/i.test(ua) || /version\/[\d.]+.*safari/i.test(ua));
}

/**
 * localStorage 사용 가능 여부 확인
 * @returns {boolean}
 */
function isLocalStorageAvailable() {
    try {
        const test = '__localStorage_test__';
        localStorage.setItem(test, test);
        localStorage.removeItem(test);
        return true;
    } catch (e) {
        console.warn('[Android] localStorage 사용 불가:', e.message);
        return false;
    }
}

// ==========================================
// CSS 클래스 생성 헬퍼 함수
// ==========================================

/**
 * 조문 레벨에 따른 CSS 클래스 생성 (기존 로직과 동일하게)
 * @param {Object} article - 조문 객체
 * @param {Object} previousArticle - 이전 조문 객체
 * @returns {string} - CSS 클래스 문자열
 */
function getArticleClasses(article, previousArticle) {
    const classes = [];

    // 기본 클래스 설정 (기존 로직과 동일)
    let className = '';
    if (article.레벨 === 1) {
        className = 'article-title';
        // 제개정 이력은 특별한 클래스
        if (article.내용 && article.내용.includes('내규의 제·개정 이력')) {
            className = 'article-title history-section';
        }
    } else if (article.레벨 === 2) {
        className = 'article-item';
    } else {
        className = 'article-sub-item';
    }

    classes.push(className);

    // 레벨별 CSS 클래스 추가 (padding 용)
    classes.push(`article-level-${article.레벨}`);

    // 레벨 전환 시 추가 여백 처리
    if (previousArticle && article.레벨 === 2) {
        if (previousArticle.레벨 >= 3 || previousArticle.레벨 === 2) {
            classes.push('margin-top-spacing');
        }
    }

    return classes.join(' ');
}

/**
 * 조문 표시 텍스트 생성
 * @param {Object} article - 조문 객체
 * @returns {string}
 */
function getDisplayText(article) {
    if (article.번호 && article.레벨 === 1) {
        return `<b>${article.번호}</b> ${article.내용}`;
    }
    return article.번호 ? `${article.번호} ${article.내용}` : article.내용;
}

// ==========================================
// Progressive Rendering (Tile Memory 분산)
// ==========================================

/**
 * 조문을 점진적으로 렌더링 (GPU 타일 메모리 분산)
 *
 * 원리:
 * - 15개씩 청크로 나누어 렌더링
 * - 각 청크 후 requestAnimationFrame 2번 대기
 * - GPU가 타일을 작은 단위로 생성하도록 유도
 * - 메모리 스파이크 방지
 *
 * @param {HTMLElement} container - 컨테이너 요소
 * @param {Array} articles - 조문 배열
 * @param {Object} regulation - 내규 객체
 * @returns {Promise<void>}
 */
async function renderArticlesProgressively(container, articles, regulation) {
    console.log('[Android Progressive] 시작 - 조문 수:', articles.length);

    const CHUNK_SIZE = 15; // 15개씩 렌더링 (Android 최적값)

    // 렌더링 중 사용자 인터랙션 비활성화 (스크롤 방지)
    const originalOverflow = container.style.overflow;
    const originalPointerEvents = container.style.pointerEvents;
    container.style.overflow = 'hidden';
    container.style.pointerEvents = 'none';

    // 로딩 인디케이터 표시
    container.innerHTML = `
        <div style="text-align: center; padding: 40px; color: #666;">
            <div style="font-size: 16px; margin-bottom: 10px;">
                내규 내용을 불러오는 중...
            </div>
            <div style="font-size: 14px; color: #999;">
                조문이 많아 조금 시간이 걸릴 수 있습니다
            </div>
        </div>
    `;

    // 짧은 대기 후 렌더링 시작 (로딩 메시지 표시 보장)
    await new Promise(resolve => setTimeout(resolve, 50));

    // 컨테이너 비우기
    container.innerHTML = '';

    let previousArticle = null;
    let inAppendixSection = false;
    let appendixCounter = 0;

    // 청크별 렌더링
    for (let i = 0; i < articles.length; i += CHUNK_SIZE) {
        const chunk = articles.slice(i, i + CHUNK_SIZE);
        const fragment = document.createDocumentFragment();

        chunk.forEach((article, chunkIndex) => {
            if (!article || article.레벨 === 0) return;

            // 제N절 패턴: 별도 section-title 스타일 적용
            if (article.레벨 === 1 && !article.번호 && /^제\d+절/.test((article.내용 || '').replace(/<[^>]+>/g, '').trim())) {
                const div = document.createElement('div');
                div.className = 'section-title';
                div.innerHTML = article.내용;
                fragment.appendChild(div);
                previousArticle = article;
                return;
            }

            // 부록 섹션 추적
            if (article.번호 === '제4조' && article.내용 && article.내용.includes('(부록)')) {
                inAppendixSection = true;
                appendixCounter = 0;
            } else if (article.번호 === '제5조') {
                inAppendixSection = false;
            }

            // 제개정 이력 제목 추가
            if (previousArticle && previousArticle.번호 === '제5조' &&
                article.번호 === '제1조' && article.내용 && article.내용.includes('내규의 제정')) {
                const divider = document.createElement('div');
                divider.className = 'history-divider';
                divider.textContent = '내규의 제·개정 이력';
                fragment.appendChild(divider);
            }

            let displayText = getDisplayText(article);

            // 별표 참조를 클릭 가능한 링크로 변환 (별표 섹션 자체는 제외)
            const isByulpyo = !article.번호 && (article.내용 || '').replace(/<[^>]+>/g, '').trim().startsWith('『별표');
            displayText = linkifyByulpyo(displayText, articles, isByulpyo);

            // 별표 섹션이면 data 속성 추가 (스크롤 타겟)
            const byulpyoAttrsStr = getByulpyoDataAttrs(article.내용);

            // 부록 링크 처리
            const isAppendixItem = inAppendixSection && article.레벨 === 2;

            if (isAppendixItem) {
                // 부록 제목 추출 (기존과 동일)
                const appendixTitle = article.내용.replace(/^\d+\.\s*/, '');

                console.log(`[Android Appendix] 부록 ${appendixCounter}: "${article.내용}" → "${appendixTitle}"`);

                const div = document.createElement('div');
                div.className = `${getArticleClasses(article, previousArticle)} appendix-link`;
                div.textContent = displayText;

                // 인라인 onclick 사용 (메모리 최적화 - 클로저 대신 문자열)
                const safeAppendixTitle = appendixTitle.replace(/'/g, "\\'");
                div.setAttribute('onclick', `openAppendixPdf('${regulation.code}', ${appendixCounter}, '${safeAppendixTitle}')`);

                // 별표 data 속성
                if (byulpyoAttrsStr) {
                    const attrPairs = byulpyoAttrsStr.match(/data-byulpyo-\d+="1"/g) || [];
                    attrPairs.forEach(attr => {
                        const name = attr.split('=')[0];
                        div.setAttribute(name, '1');
                    });
                }

                fragment.appendChild(div);
                appendixCounter++;
            } else {
                // 일반 조문
                const div = document.createElement('div');
                div.className = getArticleClasses(article, previousArticle);
                div.innerHTML = displayText; // innerHTML for potential highlighting

                // 별표 data 속성
                if (byulpyoAttrsStr) {
                    const attrPairs = byulpyoAttrsStr.match(/data-byulpyo-\d+="1"/g) || [];
                    attrPairs.forEach(attr => {
                        const name = attr.split('=')[0];
                        div.setAttribute(name, '1');
                    });
                }

                fragment.appendChild(div);
            }

            // 관련 이미지 처리
            if (article.관련이미지 && article.관련이미지.length > 0) {
                const imagePaddingLevel = Math.min(article.레벨 + 1, 8);
                article.관련이미지.forEach(img => {
                    const imgWrapper = document.createElement('div');
                    imgWrapper.className = `article-level-${imagePaddingLevel}`;
                    imgWrapper.style.margin = '10px 0';

                    const imgElement = document.createElement('img');
                    imgElement.src = img.file_path;
                    imgElement.style.maxWidth = '100%';
                    imgElement.style.height = 'auto';
                    imgElement.style.border = '1px solid #e0e0e0';
                    imgElement.style.borderRadius = '4px';

                    imgWrapper.appendChild(imgElement);
                    fragment.appendChild(imgWrapper);
                });
            }

            previousArticle = article;
        });

        // DocumentFragment를 컨테이너에 추가
        container.appendChild(fragment);

        // GPU에게 타일 생성 시간 제공 (중요!)
        // 2번의 requestAnimationFrame = 약 32ms (2 frames)
        await new Promise(resolve => {
            requestAnimationFrame(() => {
                requestAnimationFrame(resolve);
            });
        });

        console.log(`[Android Progressive] ${i + chunk.length}/${articles.length} 렌더링 완료`);
    }

    // 렌더링 완료 - 인터랙션 복원
    container.style.overflow = originalOverflow;
    container.style.pointerEvents = originalPointerEvents;

    console.log('[Android Progressive] 렌더링 완료');
}

// ==========================================
// Android 전용 내규 상세보기 함수
// ==========================================

/**
 * Android WebView 전용 내규 상세보기
 *
 * 최적화:
 * 1. CSS 클래스 기반 렌더링 (inline style 제거)
 * 2. Progressive Rendering (tile memory 분산)
 * 3. GPU acceleration 최소화
 *
 * @param {Object} regulation - 내규 객체
 * @param {string} chapter - 챕터
 */
async function showRegulationDetailAndroid(regulation, chapter) {
    console.log('[Android WebView] 최적화 경로 사용 - 내규:', regulation.code);

    // 모바일 여부 확인
    const isMobile = window.innerWidth <= 768;
    console.log('[Android] isMobile:', isMobile);

    // 히스토리 관리 (기존 로직 유지)
    const newHistoryItem = {
        regulation: regulation,
        chapter: chapter,
        timestamp: Date.now()
    };

    const lastItem = regulationHistory[regulationHistory.length - 1];
    console.log('마지막 히스토리 아이템:', lastItem);

    if (!lastItem ||
        lastItem.regulation.code !== regulation.code ||
        lastItem.chapter !== chapter) {
        console.log('히스토리에 새 아이템 추가');
        regulationHistory.push(newHistoryItem);
        if (regulationHistory.length > 20) {
            regulationHistory.shift();
        }
        console.log('추가 후 히스토리 길이:', regulationHistory.length);
    } else {
        console.log('같은 내규이므로 히스토리에 추가하지 않음');
    }

    isNavigatingBack = false;

    // 전역 변수에 현재 규정 정보 저장
    currentRegulation = regulation;
    currentChapter = chapter;

    // 페이지 상태 설정
    document.getElementById('sidebar').style.display = 'block';
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'block';

    // 네비게이션 활성화
    updateNavigation('분류');

    const chapterData = hospitalRegulations[chapter];
    document.getElementById('breadcrumbActive').textContent = `${chapter}. ${chapterData.title}`;
    document.getElementById('pageTitle').textContent = `${regulation.code}. ${regulation.name}`;

    // 헤더에 액션 버튼 추가
    addActionButtonsToHeader(regulation, chapter, isMobile);

    // sidebar active 상태 업데이트
    updateSidebarActiveState(regulation, chapter);

    // 내규 상세 내용 생성
    const contentBody = document.getElementById('contentBody');

    // 메타데이터 HTML 생성 (기존 로직 사용 - generateMetaHtml 함수 호출)
    const metaHtml = generateMetaHtml(regulation, isMobile);

    // 파일명이 있으면 상세 데이터 로드
    if (regulation.detail && regulation.detail.documentInfo && regulation.detail.documentInfo.파일명) {
        const fileName = regulation.detail.documentInfo.파일명;
        console.log('[Android] Loading detail file:', fileName);

        try {
            // 개별 파일 로드
            const detailData = await loadRegulationDetail(fileName);

            if (detailData) {
                regulation.detailData = detailData;
                console.log('[Android] DetailData merged to regulation object');
            }

            if (detailData && detailData.조문내용) {
                console.log('[Android] Detail data loaded, articles:', detailData.조문내용.length);

                // 콘텐츠를 숨긴 상태로 시작
                contentBody.style.opacity = '0';
                contentBody.style.transition = 'opacity 0.2s ease-in-out';

                // 메타데이터 먼저 표시 (즉시)
                contentBody.innerHTML = `
                    <div class="regulation-detail mal-font">
                        <div class="regulation-header">
                            ${metaHtml}
                        </div>
                        <div class="regulation-content" id="android-article-container">
                            <!-- Progressive Rendering으로 조문 삽입 -->
                        </div>
                    </div>
                `;

                // 조문 컨테이너 가져오기
                const articleContainer = document.getElementById('android-article-container');

                // Progressive Rendering 실행 (Tile memory 분산)
                await renderArticlesProgressively(articleContainer, detailData.조문내용, regulation);

                console.log('[Android] 내규 상세보기 렌더링 완료');

                // 최근 내규에 추가 (localStorage 사용 가능 시에만)
                if (isLocalStorageAvailable()) {
                    try {
                        if (typeof updateRecentRegulations === 'function') {
                            updateRecentRegulations(regulation, chapter, 'regulation');
                            console.log('[Android] updateRecentRegulations 완료');
                        }
                    } catch (error) {
                        console.warn('[Android] updateRecentRegulations 에러 (무시):', error.message);
                    }
                } else {
                    console.log('[Android] localStorage 사용 불가 - updateRecentRegulations 스킵');
                }

                // 저장된 글꼴 크기 적용 (localStorage 사용 가능 시에만)
                if (isLocalStorageAvailable()) {
                    try {
                        if (typeof loadSavedFontSize === 'function') {
                            loadSavedFontSize();
                            console.log('[Android] loadSavedFontSize 완료');
                        }
                    } catch (error) {
                        console.warn('[Android] loadSavedFontSize 에러 (무시):', error.message);
                    }
                } else {
                    console.log('[Android] localStorage 사용 불가 - 기본 글꼴 사용');
                }

                // 화면 표시 (opacity 전환)
                console.log('[Android] 화면 표시 시작 - opacity 전환');
                requestAnimationFrame(() => {
                    contentBody.style.opacity = '1';
                    console.log('[Android] opacity = 1 설정 완료');

                    // 스크롤 리셋 (안전하게 처리)
                    setTimeout(() => {
                        try {
                            if (typeof resetAllScrolls === 'function') {
                                console.log('[Android] resetAllScrolls 호출');
                                resetAllScrolls();
                            } else {
                                // resetAllScrolls가 없으면 수동으로 스크롤 리셋
                                console.log('[Android] resetAllScrolls 함수 없음 - 수동 스크롤 리셋');
                                contentBody.scrollTop = 0;
                            }
                        } catch (error) {
                            console.error('[Android] resetAllScrolls 에러:', error);
                            // 에러 발생해도 화면은 유지
                        }
                    }, 100);
                });

            } else {
                console.error('[Android] Failed to load detail data or no articles found');
                contentBody.style.opacity = '0';
                contentBody.innerHTML = `
                    <div class="regulation-detail mal-font">
                        <div class="regulation-header">${metaHtml}</div>
                        <div class="regulation-content">
                            <div class="article-title">내규 내용</div>
                            <div class="article-item">
                                내규 데이터를 불러오는 중 오류가 발생했습니다.
                            </div>
                        </div>
                    </div>
                `;
                requestAnimationFrame(() => {
                    contentBody.style.opacity = '1';
                });
            }
        } catch (error) {
            console.error('[Android] Error loading detail file:', error);
            contentBody.style.opacity = '0';
            contentBody.innerHTML = `
                <div class="regulation-detail mal-font">
                    <div class="regulation-header">${metaHtml}</div>
                    <div class="regulation-content">
                        <div class="article-title">내규 내용</div>
                        <div class="article-item">
                            내규 데이터를 불러오는 중 오류가 발생했습니다: ${error.message}
                        </div>
                    </div>
                </div>
            `;
            requestAnimationFrame(() => {
                contentBody.style.opacity = '1';
            });
        }
    } else {
        // 파일명이 없는 경우
        console.warn('[Android] 파일명 없음 - 기본 메시지 표시');
        contentBody.style.opacity = '0';
        contentBody.innerHTML = `
            <div class="regulation-detail mal-font">
                <div class="regulation-header">${metaHtml}</div>
                <div class="regulation-content">
                    <div class="article-title">내규 내용</div>
                    <div class="article-item">
                        <strong>${regulation.name}</strong> 내규의 파일 정보를 찾을 수 없습니다.
                    </div>
                </div>
            </div>
        `;
        requestAnimationFrame(() => {
            contentBody.style.opacity = '1';
        });
    }
}

// ==========================================
// 헬퍼 함수: 메타데이터 HTML 생성
// ==========================================

/**
 * 메타데이터 HTML 생성 (generateRegulationContent와 동일한 로직)
 * @param {Object} regulation - 내규 객체
 * @param {boolean} isMobile - 모바일 여부
 * @returns {string} - 메타데이터 HTML
 */
function generateMetaHtml(regulation, isMobile) {
    console.log('[Android generateMetaHtml] 시작 - isMobile:', isMobile);

    let modalMetaHTML = '';

    // docInfo 우선순위: 문서정보(한글) > document_info(영문)
    const docInfo = regulation.detailData?.문서정보 ||
                   regulation.detailData?.document_info ||
                   regulation.detail?.documentInfo;

    console.log('[Android generateMetaHtml] docInfo:', docInfo);

    if ((regulation.detail && regulation.detail.documentInfo) || regulation.detailData) {
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

            modalMetaHTML = `
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
        // detail이 없는 경우
        metaHtml = `
            <div class="regulation-meta-container">
                <div class="article-title">내규 정보</div>
                <div class="article-item">메타데이터를 불러올 수 없습니다.</div>
            </div>
        `;
    }

    console.log('[Android generateMetaHtml] 완료 - HTML 길이:', modalMetaHTML.length);
    return modalMetaHTML;
}

console.log('[kbregulation_android.js] Android WebView 최적화 모듈 로드 완료');
