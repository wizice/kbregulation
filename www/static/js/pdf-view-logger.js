/**
 * pdf-view-logger.js
 * PDF Viewer에서 로드될 때 자동으로 부록 조회를 로깅하는 스크립트
 *
 * 사용법:
 * PDF Viewer HTML에 이 스크립트를 포함시키면
 * URL 파라미터에서 PDF 파일명을 파싱하여 자동으로 로깅 API를 호출합니다.
 */

(function() {
    'use strict';

    // URL에서 PDF 파일 경로 추출
    function getPdfFileFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        const fileParam = urlParams.get('file');

        if (!fileParam) {
            return null;
        }

        // decodeURIComponent 처리
        const decodedFile = decodeURIComponent(fileParam);

        // /static/pdf/파일명.pdf 형식에서 파일명 추출
        const match = decodedFile.match(/\/static\/pdf\/(.+\.pdf)$/i);
        if (match) {
            return match[1];
        }

        return null;
    }

    // 부록 파일명 파싱 (규정코드, 부록번호, 부록명 추출)
    function parseAppendixFilename(fileName) {
        try {
            // 패턴: {규정코드}._부록{번호}._{부록명}_{날짜}{상태}.pdf
            const pattern = /^([0-9.]+)\.?_부록(\d+)\._(.+?)(?:_\d{8})?(?:개정|검토)?\.pdf$/;
            const match = fileName.match(pattern);

            if (match) {
                const rulePubno = match[1].endsWith('.') ? match[1] : match[1] + '.';
                const appendixNo = match[2];
                const appendixNameRaw = match[3];
                const appendixNameClean = appendixNameRaw.replace(/_/g, ' ');
                const appendixName = `부록${appendixNo}. ${appendixNameClean}`;
                const fullName = `${rulePubno} ${appendixName}`;

                return {
                    rulePubno: rulePubno,
                    appendixNo: appendixNo,
                    appendixName: appendixName,
                    fullName: fullName,
                    isAppendix: true
                };
            }

            return null;
        } catch (error) {
            console.error('[PDF Logger] 파일명 파싱 오류:', error);
            return null;
        }
    }

    // 로깅 API 호출
    async function logPdfView(fileName, parsedInfo) {
        try {
            // FastAPI 로깅 API 호출 (GET 요청으로 파일을 받으면서 자동 로깅)
            const apiUrl = `https://policyeditor.wizice.com:8443/api/v1/pdf-file/${encodeURIComponent(fileName)}`;

            console.log(`[PDF Logger] 로깅 시작: ${fileName}`);
            console.log(`[PDF Logger] 파싱 정보:`, parsedInfo);
            console.log(`[PDF Logger] API URL: ${apiUrl}`);

            // Fetch API로 요청만 보내고 응답은 무시 (로깅만 트리거)
            fetch(apiUrl, {
                method: 'GET',
                mode: 'no-cors', // CORS 에러 방지
                credentials: 'omit'
            }).then(() => {
                console.log(`[PDF Logger] ✅ 로깅 요청 전송: ${parsedInfo.fullName}`);
            }).catch(() => {
                // 로깅 실패해도 무시 (no-cors 모드에서는 항상 성공으로 보임)
                console.log(`[PDF Logger] 로깅 요청 완료`);
            });

        } catch (error) {
            // 로깅 실패해도 PDF 뷰어는 정상 작동
            console.warn('[PDF Logger] 로깅 실패 (무시됨):', error);
        }
    }

    // 메인 실행
    function init() {
        // PDF Viewer에서만 실행 (viewer.html)
        if (!window.location.pathname.includes('viewer.html')) {
            return;
        }

        const pdfFileName = getPdfFileFromUrl();
        if (!pdfFileName) {
            console.log('[PDF Logger] PDF 파일명을 찾을 수 없습니다.');
            return;
        }

        console.log(`[PDF Logger] PDF 파일 감지: ${pdfFileName}`);

        // 부록 파일인지 확인
        const parsedInfo = parseAppendixFilename(pdfFileName);
        if (parsedInfo && parsedInfo.isAppendix) {
            console.log(`[PDF Logger] 부록 파일 확인: ${parsedInfo.fullName}`);
            // 로깅 API 호출 (비동기, 실패해도 무시)
            logPdfView(pdfFileName, parsedInfo);
        } else {
            console.log('[PDF Logger] 부록 파일이 아니거나 파싱 실패');
        }
    }

    // DOM 로드 후 실행
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
