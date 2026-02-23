/**
 * KB신용정보 내규 시스템 - 상세보기 모듈
 * @module kbregulation_detail
 */

import { AppState, showToast, formatDate, resetAllScrolls, updateNavigation } from './kbregulation_common.js';
import { loadRegulationDetail } from './kbregulation_data.js';
import { applyWatermarkToContent } from './kbregulation_watermark.js';
import { updateSidebarActiveState } from './kbregulation_sidebar.js';

// ============================================
// 상세보기 관련 상태
// ============================================

let regulationHistory = [];
let isNavigatingBack = false;

// ============================================
// 내규 상세보기 함수
// ============================================

/**
 * 내규 상세보기 표시
 */
export async function showRegulationDetail(regulation, chapter) {
    const isMobile = window.innerWidth <= 768;

    // 히스토리에 현재 내규 추가
    const newHistoryItem = {
        regulation: regulation,
        chapter: chapter,
        timestamp: Date.now()
    };

    const lastItem = regulationHistory[regulationHistory.length - 1];
    if (!lastItem ||
        lastItem.regulation.code !== regulation.code ||
        lastItem.chapter !== chapter) {
        regulationHistory.push(newHistoryItem);
        if (regulationHistory.length > 20) {
            regulationHistory.shift();
        }
    }

    isNavigatingBack = false;

    // 전역 상태 업데이트
    AppState.currentRegulation = regulation;
    AppState.currentChapter = chapter;

    // 내규 조회 로그 기록
    if (window.RegulationViewLogger && regulation.wzRuleSeq) {
        RegulationViewLogger.logView(
            regulation.wzRuleSeq,
            regulation.name || '',
            regulation.code || ''
        ).catch(err => console.warn('로그 기록 실패:', err));
    }

    // 페이지 상태 설정
    document.getElementById('sidebar').style.display = 'block';
    document.getElementById('mainPageContent').style.display = 'none';
    document.getElementById('contentBody').style.display = 'block';
    document.getElementById('main-content-header').style.display = 'block';

    updateNavigation('현행 사규');

    const chapterData = AppState.hospitalRegulations[chapter];
    document.getElementById('breadcrumbActive').textContent = `${chapter}. ${chapterData.title}`;
    document.getElementById('pageTitle').textContent = `${regulation.code}. ${regulation.name}`;

    addActionButtonsToHeader(regulation, chapter, isMobile);
    updateSidebarActiveState(regulation, chapter);

    // 내규 상세 내용 렌더링
    await renderRegulationContent(regulation, chapter, isMobile);
}

/**
 * 내규 콘텐츠 렌더링
 */
async function renderRegulationContent(regulation, chapter, isMobile) {
    const contentBody = document.getElementById('contentBody');

    // 부록 배열 안전 처리
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
                safeAppendixArray = [];
            }
        }
    }

    let contentHtml = '';
    let metaHtml = '';

    // 상세 데이터 로드
    if (regulation.detail?.documentInfo?.파일명) {
        const detailData = await loadRegulationDetail(regulation.detail.documentInfo.파일명);
        if (detailData) {
            regulation.detailData = detailData;
        }
    }

    // 메타 정보 HTML 생성
    if ((regulation.detail && regulation.detail.documentInfo) || regulation.detailData) {
        const docInfo = regulation.detailData?.document_info ||
                       regulation.detailData?.문서정보 ||
                       regulation.detail?.documentInfo;

        metaHtml = generateMetaHtml(docInfo, safeAppendixArray, regulation, isMobile);
    } else {
        metaHtml = generateEmptyMetaHtml(isMobile);
    }

    // 조문 내용 HTML 생성
    if (regulation.detailData?.조문내용) {
        contentHtml = generateArticlesHtml(regulation);
    } else if (regulation.detail?.articles && Array.isArray(regulation.detail.articles)) {
        contentHtml = generateLegacyArticlesHtml(regulation.detail.articles);
    } else {
        contentHtml = `
            <div class="article-title">내규 내용</div>
            <div class="article-item">
                <strong>${regulation.name}</strong> 내규의 파일 정보를 찾을 수 없습니다.
            </div>
        `;
    }

    // 콘텐츠 렌더링
    contentBody.style.opacity = '0';
    contentBody.style.transition = 'opacity 0.2s ease-in-out';

    contentBody.innerHTML = `
        <div class="regulation-detail mal-font">
            <div class="regulation-header">
                ${metaHtml}
            </div>
            <div class="regulation-content">
                ${contentHtml}
            </div>
        </div>
    `;

    // 최근 본 내규 업데이트
    updateRecentRegulations(regulation, chapter, 'regulation');

    // 글꼴 크기 적용 및 표시
    setTimeout(() => {
        if (typeof loadSavedFontSize === 'function') {
            loadSavedFontSize();
        }
        requestAnimationFrame(() => {
            setTimeout(() => {
                resetAllScrolls();
            }, 100);
            contentBody.style.opacity = '1';

            // 워터마크 적용
            if (typeof applyWatermarkToContent === 'function') {
                applyWatermarkToContent();
            }
        });
    }, 10);
}

/**
 * 메타 정보 HTML 생성
 */
function generateMetaHtml(docInfo, appendixArray, regulation, isMobile) {
    if (isMobile) {
        return `
            <div class="regulation-meta-container">
                <div class="mobile-meta-cards">
                    <div class="mobile-meta-card">
                        <div class="mobile-meta-card-content">
                            <div class="mobile-meta-item">
                                <div class="mobile-meta-label">제정일</div>
                                <div class="mobile-meta-value ${docInfo.제정일 ? '' : 'empty'}">
                                    ${docInfo.제정일 || '-'}
                                </div>
                            </div>
                            <div class="mobile-meta-item">
                                <div class="mobile-meta-label">최근<br>개정일</div>
                                <div class="mobile-meta-value ${docInfo.최종개정일 ? '' : 'empty'}">
                                    ${docInfo.최종개정일 || '-'}
                                </div>
                            </div>
                            <div class="mobile-meta-item">
                                <div class="mobile-meta-label">최근<br>시행일</div>
                                <div class="mobile-meta-value ${docInfo.최종검토일 ? '' : 'empty'}">
                                    ${docInfo.최종검토일 || '-'}
                                </div>
                            </div>
                        </div>
                    </div>
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
        return `
            <div class="regulation-meta-container">
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
}

/**
 * 빈 메타 정보 HTML
 */
function generateEmptyMetaHtml(isMobile) {
    if (isMobile) {
        return `
            <div class="regulation-meta-container">
                <div class="mobile-meta-cards">
                    <div class="mobile-meta-card">
                        <div class="mobile-meta-card-content">
                            <div class="mobile-meta-item">
                                <div class="mobile-meta-label">제정일</div>
                                <div class="mobile-meta-value empty">-</div>
                            </div>
                            <div class="mobile-meta-item">
                                <div class="mobile-meta-label">최근<br>개정일</div>
                                <div class="mobile-meta-value empty">-</div>
                            </div>
                            <div class="mobile-meta-item">
                                <div class="mobile-meta-label">최근<br>시행일</div>
                                <div class="mobile-meta-value empty">-</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else {
        return `
            <div class="regulation-meta-container">
                <table class="regulation-meta-table">
                    <tr>
                        <th class="header-cell">제정일</th>
                        <td class="content-cell" style="text-align:center;">-</td>
                        <th class="header-cell" style="border-left:1px solid #000">최근개정일</th>
                        <td class="content-cell" style="text-align:center;">-</td>
                        <th class="header-cell" style="border-left:1px solid #000">최근시행일</th>
                        <td class="content-cell" style="text-align:center;">-</td>
                    </tr>
                </table>
            </div>
        `;
    }
}

/**
 * 조문 내용 HTML 생성
 */
function generateArticlesHtml(regulation) {
    const articles = regulation.detailData.조문내용;
    if (!articles || !Array.isArray(articles) || articles.length === 0) {
        return `
            <div class="article-title">내규 내용</div>
            <div class="article-item">내규 데이터를 불러오는 중 오류가 발생했습니다.</div>
        `;
    }

    const contentParts = [];
    let previousArticle = null;
    let inAppendixSection = false;
    let appendixCounter = 0;

    articles.forEach((article, index) => {
        if (!article || article.레벨 === 0) return;

        // 부록 섹션 감지
        if (article.번호 === '제4조' && article.내용 && article.내용.includes('부록')) {
            inAppendixSection = true;
        } else if (article.번호 === '제5조') {
            inAppendixSection = false;
        }

        // 제개정 이력 제목
        if (previousArticle && previousArticle.번호 === '제5조' &&
            article.번호 === '제1조' && article.내용?.includes('내규의 제정')) {
            contentParts.push(`<div style="font-weight: 600; color: #2786dd; text-align:center; font-size:20px!important;padding-left: 0px;margin-top:30px;margin-bottom:20px;">내규의 제·개정 이력</div>`);
        }

        // 레벨에 따른 스타일
        let paddingLeft = 0;
        switch (article.레벨) {
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

        let additionalStyle = '';
        if (previousArticle && article.레벨 === 2 && (previousArticle.레벨 >= 3 || previousArticle.레벨 === 2)) {
            additionalStyle = 'margin-top: 25px;';
        }

        let className = '';
        let isHistorySection = false;

        if (article.레벨 === 1) {
            className = 'article-title';
            if (article.내용?.includes('내규의 제·개정 이력')) {
                className = 'article-title history-section';
                isHistorySection = true;
            }
        } else if (article.레벨 === 2) {
            className = 'article-item';
        } else {
            className = 'article-sub-item';
        }

        const displayText = article.번호 ? `${article.번호} ${article.내용}` : article.내용;
        const isAppendixItem = inAppendixSection && article.레벨 === 2;

        if (isAppendixItem) {
            const appendixTitle = article.내용.replace(/^\d+\.\s*/, '');
            contentParts.push(`<div class="${className} appendix-link"
                               style="padding-left: ${paddingLeft}px; cursor: pointer; color: #1976d2; text-decoration: underline;"
                               onclick="openAppendixPdf('${regulation.code}', ${appendixCounter}, '${appendixTitle.replace(/'/g, "\\'")}')">
                               ${displayText}
                            </div>`);
            appendixCounter++;
        } else {
            if (className === 'article-sub-item') {
                contentParts.push(`<div class="${className}" style="padding-left: ${paddingLeft}px; text-indent: -20px;">${displayText}</div>`);
            } else if (className === 'article-item' && article.레벨 === 2) {
                contentParts.push(`<div class="${className}" style="padding-left: 35px; text-indent: -15px; ${additionalStyle}">${displayText}</div>`);
            } else if (isHistorySection) {
                contentParts.push(`<div class="${className}" style="padding-left: 0px; text-align: center; font-size: 1.3rem !important; padding-bottom: 8px; font-weight: 600; color: #1565c0; border-bottom: 1px solid #e3f2fd; ${additionalStyle}">${displayText}</div>`);
            } else {
                contentParts.push(`<div class="${className}" style="padding-left: ${paddingLeft}px; ${additionalStyle}">${displayText}</div>`);
            }
        }

        previousArticle = article;

        // 관련 이미지
        if (article.관련이미지?.length > 0) {
            article.관련이미지.forEach(img => {
                contentParts.push(`<div style="margin: 10px 0; padding-left: ${paddingLeft + 20}px;">
                    <img src="${img.file_path}" style="max-width: 100%; height: auto; border: 1px solid #e0e0e0; border-radius: 4px;">
                </div>`);
            });
        }
    });

    return contentParts.join('');
}

/**
 * 레거시 조문 HTML 생성
 */
function generateLegacyArticlesHtml(articles) {
    let html = '';
    articles.forEach(article => {
        if (!article) return;

        if (article.title) {
            html += `<div class="article-title">${article.title}</div>`;
        }
        if (article.content) {
            html += `<div class="article-item">${article.content}</div>`;
        }
        if (article.subsections && Array.isArray(article.subsections)) {
            article.subsections.forEach(subsection => {
                if (!subsection) return;
                if (subsection.title) {
                    html += `<div class="article-item"><strong>${subsection.title}</strong></div>`;
                }
                if (subsection.items && Array.isArray(subsection.items)) {
                    subsection.items.forEach(item => {
                        if (item) {
                            html += `<div class="article-sub-item" style="padding-left: 60px; text-indent: -20px;">${item}</div>`;
                        }
                    });
                }
            });
        }
    });
    return html;
}

/**
 * 부록 툴팁 생성
 */
export function generateAppendixTooltip(regulation) {
    if (!regulation.appendix || regulation.appendix.length === 0) {
        return '';
    }

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

    const tooltipItems = safeAppendixArray.map((appendix, index) => {
        const cleanAppendixName = appendix.replace(/^\d+\.\s*/, '');
        return `<div class="appendix-tooltip-item" onclick="event.stopPropagation(); openAppendixPdf('${regulation.code}', ${index}, '${cleanAppendixName.replace(/'/g, "\\'")}')">
            <i class="fas fa-file-pdf"></i>
            <span>부록 ${index + 1}. ${cleanAppendixName}</span>
        </div>`;
    }).join('');

    return `<div class="appendix-tooltip">${tooltipItems}</div>`;
}

/**
 * 부록 툴팁 토글
 */
export function toggleAppendixTooltip(event, regulation) {
    event.stopPropagation();
    const tooltip = event.currentTarget.querySelector('.appendix-tooltip');
    if (tooltip) {
        tooltip.classList.toggle('show');
    }
}

/**
 * 헤더에 액션 버튼 추가
 */
export function addActionButtonsToHeader(regulation, chapter, isMobile) {
    const showPrint = (typeof isPrintAllowed === 'function' && isPrintAllowed());

    const actionsHtml = isMobile ? `
        <div class="regulation-actions">
            <button class="action-btn mobile-back-action" onclick="goBackFromRegulation()" data-tooltip="뒤로가기">
                <i class="fas fa-arrow-left"></i>
            </button>
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

    const header = document.getElementById('main-content-header');
    if (header) {
        const existing = header.querySelector('.regulation-actions-wrap') || header.querySelector('.page-actions');
        if (existing) existing.remove();
        header.insertAdjacentHTML('beforeend', actionsHtml);
    }
}

/**
 * 최근 본 내규 업데이트
 */
export function updateRecentRegulations(regulation, chapter, type = 'regulation') {
    const maxRecent = 10;
    let recentKey = type === 'appendix' ? `부록|${regulation.code}|${regulation.name}` : `${chapter}|${regulation.code}|${regulation.name}`;

    // 기존에 있으면 제거
    const existingIndex = AppState.regulationHistory?.findIndex(item => item.key === recentKey) ?? -1;
    if (existingIndex > -1) {
        AppState.regulationHistory.splice(existingIndex, 1);
    }

    // 맨 앞에 추가
    const recentItem = {
        key: recentKey,
        chapter: chapter,
        code: regulation.code,
        name: regulation.name,
        timestamp: new Date().toISOString(),
        type: type
    };

    if (!AppState.regulationHistory) {
        AppState.regulationHistory = [];
    }

    AppState.regulationHistory.unshift(recentItem);

    // 최대 개수 유지
    if (AppState.regulationHistory.length > maxRecent) {
        AppState.regulationHistory = AppState.regulationHistory.slice(0, maxRecent);
    }

    // UI 업데이트
    if (typeof updateRecentRegulationsList === 'function') {
        updateRecentRegulationsList();
    }
}

/**
 * 새창으로 열기
 */
export function openInNewWindow() {
    if (AppState.currentRegulation && AppState.currentChapter) {
        const chapterData = AppState.hospitalRegulations[AppState.currentChapter];
        let url = `/kbregulation_page_static.html?chapter=${encodeURIComponent(AppState.currentChapter)}&code=${encodeURIComponent(AppState.currentRegulation.code)}`;

        if (AppState.currentSearchTerm) {
            url += `&searchTerm=${encodeURIComponent(AppState.currentSearchTerm)}`;
        }

        window.open(url, '_blank', 'width=1000,height=800,scrollbars=yes,resizable=yes');
    }
}

/**
 * 모바일 상세보기 열기
 */
export async function openMobileRegulationView(regulation, chapter, chapterTitle) {
    const view = document.getElementById('mobileRegulationView');
    const title = document.getElementById('mobileRegulationTitle');
    const body = document.getElementById('mobileRegulationBody');

    title.textContent = `${regulation.code}. ${regulation.name}`;
    body.innerHTML = '<div style="text-align: center; padding: 20px;">내규 내용을 불러오는 중...</div>';
    view.style.display = 'flex';

    const regulationContent = await generateRegulationContent(regulation, chapter, chapterTitle);
    body.innerHTML = regulationContent;
}

/**
 * 모바일 뷰 닫기
 */
export function closeMobileRegulationView() {
    const view = document.getElementById('mobileRegulationView');
    if (view) {
        view.style.display = 'none';
    }
}

/**
 * 모달 닫기
 */
export function closeRegulationModal() {
    const modal = document.getElementById('regulationModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.showRegulationDetail = showRegulationDetail;
    window.generateAppendixTooltip = generateAppendixTooltip;
    window.toggleAppendixTooltip = toggleAppendixTooltip;
    window.addActionButtonsToHeader = addActionButtonsToHeader;
    window.updateRecentRegulations = updateRecentRegulations;
    window.openInNewWindow = openInNewWindow;
    window.openMobileRegulationView = openMobileRegulationView;
    window.closeMobileRegulationView = closeMobileRegulationView;
    window.closeRegulationModal = closeRegulationModal;
}
