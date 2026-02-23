/**
 * regulation-view-logger.js
 * ==========================
 *
 * 서비스 페이지용 내규 조회 로깅 모듈
 *
 * 기능:
 * - 내규 조회 시 자동으로 로깅 API 호출
 * - 기존 기능에 영향 없음 (Silent fail)
 * - 비동기 처리
 *
 * 사용법:
 * 1. HTML에 스크립트 추가
 * 2. RegulationViewLogger.logView(ruleId, ruleName, rulePubno) 호출
 *
 * 작성일: 2025-01-14
 * 작성자: Claude AI Assistant
 */

const RegulationViewLogger = {
    /**
     * API 엔드포인트 (FastAPI 서버)
     */
    //API_ENDPOINT: 'https://policyeditor.wizice.com:8443/api/v1/admin/view-stats/public/log-view',
    //내규 사용자 화면에서 로그 남기기25.12.04
    API_ENDPOINT: '/api/v1/log-view',

    /**
     * 로깅 활성화 여부
     */
    enabled: true,

    /**
     * 내규 조회 로그 기록
     *
     * @param {number|string} ruleId - 내규 ID (wzruleseq)
     * @param {string} ruleName - 내규 명칭
     * @param {string} rulePubno - 공포번호
     */
    async logView(ruleId, ruleName, rulePubno = '') {
        // 로깅 비활성화 시 무시
        if (!this.enabled) {
            return;
        }

        // 필수 파라미터 검증
        if (!ruleId || !ruleName) {
            console.warn('⚠️ RegulationViewLogger: Missing required parameters');
            return;
        }

        try {
            const response = await fetch(this.API_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    rule_id: parseInt(ruleId),
                    rule_name: ruleName,
                    rule_pubno: rulePubno || ''
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    console.log(`✅ View logged: ${ruleName}`);
                } else {
                    console.warn('⚠️ View logging failed but ignored');
                }
            } else {
                console.warn('⚠️ View logging request failed but ignored');
            }
        } catch (error) {
            // 네트워크 오류 등은 무시 (서비스에 영향 없음)
            console.warn('⚠️ View logging error (ignored):', error.message);
        }
    },

    /**
     * 로깅 활성화/비활성화
     *
     * @param {boolean} enabled - 활성화 여부
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        console.log(`RegulationViewLogger: ${enabled ? 'Enabled' : 'Disabled'}`);
    }
};

// 전역 객체로 등록
window.RegulationViewLogger = RegulationViewLogger;
