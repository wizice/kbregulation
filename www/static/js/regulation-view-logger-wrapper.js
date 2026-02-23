/**
 * regulation-view-logger-wrapper.js
 * ===================================
 *
 * kbregulation_page_static.html의 displayRegulationDetail 함수를 래핑하여 조회 로깅 추가
 *
 * 작성일: 2025-01-14
 * 작성자: Claude AI Assistant
 */

(function() {
    'use strict';

    console.log('📊 Regulation View Logger Wrapper: Initializing...');

    /**
     * displayRegulationDetail 함수 래핑
     * 원본 함수 실행 후 로깅 추가
     */
    function wrapDisplayRegulationDetail() {
        // 원본 함수가 정의될 때까지 대기
        const checkInterval = setInterval(() => {
            if (typeof window.displayRegulationDetail === 'function') {
                clearInterval(checkInterval);

                // 원본 함수 저장
                const originalDisplayRegulationDetail = window.displayRegulationDetail;

                // 새 함수로 교체
                window.displayRegulationDetail = async function(regulation, chapter, chapterTitle) {
                    console.log('📊 Wrapped displayRegulationDetail called');

                    // 원본 함수 실행
                    const result = await originalDisplayRegulationDetail.call(this, regulation, chapter, chapterTitle);

                    // 로깅 추가
                    try {
                        // regulation 객체에서 wzRuleSeq 직접 가져오기
                        const wzruleseq = regulation.wzRuleSeq;
                        const ruleName = regulation.name || chapterTitle;
                        const rulePubno = regulation.code || '';

                        if (wzruleseq && ruleName) {
                            console.log(`📊 Logging view: ${ruleName} (ID: ${wzruleseq})`);

                            if (window.RegulationViewLogger) {
                                await window.RegulationViewLogger.logView(
                                    wzruleseq,
                                    ruleName,
                                    rulePubno
                                );
                            } else {
                                console.warn('⚠️ RegulationViewLogger not loaded');
                            }
                        } else {
                            console.warn('⚠️ Missing wzRuleSeq or ruleName:', { wzruleseq, ruleName });
                        }
                    } catch (error) {
                        console.warn('⚠️ Logging failed (ignored):', error);
                    }

                    return result;
                };

                console.log('✅ displayRegulationDetail wrapped successfully');
            }
        }, 100);

        // 10초 후에도 함수가 없으면 포기
        setTimeout(() => {
            clearInterval(checkInterval);
        }, 10000);
    }

    // 페이지 로드 후 래핑 시작
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wrapDisplayRegulationDetail);
    } else {
        wrapDisplayRegulationDetail();
    }

    console.log('✅ Regulation View Logger Wrapper: Initialized');
})();
