/**
 * 날짜 유틸리티 함수
 *
 * KB신용정보 내규 편집기에서 사용하는 날짜 포맷 관련 공통 함수
 *
 * @author Claude AI Assistant
 * @date 2025-10-14
 */

/**
 * 날짜 문자열을 yyyy.mm.dd. 형식으로 변환
 *
 * @param {string} dateStr - 변환할 날짜 문자열 (yyyy-mm-dd 또는 ISO 형식)
 * @returns {string} - yyyy.mm.dd. 형식의 날짜 문자열 또는 '-'
 *
 * @example
 * formatDate('2025-03-15')        // '2025.03.15.'
 * formatDate('2025-03-15T10:30')  // '2025.03.15.'
 * formatDate(null)                // '-'
 * formatDate('')                  // '-'
 */
function formatDate(dateStr) {
    if (!dateStr || dateStr === '-') return '-';

    // yyyy-mm-dd 형식 추출 (ISO 8601, 일반 날짜 모두 지원)
    const match = dateStr.match(/(\d{4})-(\d{2})-(\d{2})/);

    if (match) {
        return `${match[1]}.${match[2]}.${match[3]}.`;
    }

    // 매칭 실패 시 원본 반환
    return dateStr;
}

/**
 * yyyy.mm.dd. 형식을 yyyy-mm-dd 형식으로 역변환
 *
 * @param {string} dateStr - yyyy.mm.dd. 형식의 날짜 문자열
 * @returns {string} - yyyy-mm-dd 형식의 날짜 문자열
 *
 * @example
 * reverseDateFormat('2025.03.15.')  // '2025-03-15'
 */
function reverseDateFormat(dateStr) {
    if (!dateStr || dateStr === '-') return null;

    const match = dateStr.match(/(\d{4})\.(\d{2})\.(\d{2})\./);

    if (match) {
        return `${match[1]}-${match[2]}-${match[3]}`;
    }

    return dateStr;
}

/**
 * 현재 날짜를 yyyy.mm.dd. 형식으로 반환
 *
 * @returns {string} - 현재 날짜 (yyyy.mm.dd. 형식)
 *
 * @example
 * getCurrentDate()  // '2025.03.15.'
 */
function getCurrentDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');

    return `${year}.${month}.${day}.`;
}

/**
 * 날짜 유효성 검증
 *
 * @param {string} dateStr - 검증할 날짜 문자열
 * @returns {boolean} - 유효한 날짜면 true
 *
 * @example
 * isValidDate('2025-03-15')    // true
 * isValidDate('2025.03.15.')   // true
 * isValidDate('invalid')       // false
 */
function isValidDate(dateStr) {
    if (!dateStr || dateStr === '-') return false;

    // yyyy-mm-dd 또는 yyyy.mm.dd. 형식 체크
    const pattern1 = /^\d{4}-\d{2}-\d{2}$/;
    const pattern2 = /^\d{4}\.\d{2}\.\d{2}\.$/;

    if (!pattern1.test(dateStr) && !pattern2.test(dateStr)) {
        return false;
    }

    // Date 객체로 파싱하여 유효성 확인
    const normalized = dateStr.replace(/\./g, '-').replace(/-$/, '');
    const date = new Date(normalized);

    return date instanceof Date && !isNaN(date);
}

/**
 * 두 날짜 비교
 *
 * @param {string} date1 - 첫 번째 날짜
 * @param {string} date2 - 두 번째 날짜
 * @returns {number} - date1이 더 최근이면 양수, date2가 더 최근이면 음수, 같으면 0
 *
 * @example
 * compareDates('2025-03-15', '2025-03-10')  // 양수
 * compareDates('2025.03.10.', '2025.03.15.')  // 음수
 */
function compareDates(date1, date2) {
    if (!date1 || !date2) return 0;

    const normalized1 = date1.replace(/\./g, '-').replace(/-$/, '');
    const normalized2 = date2.replace(/\./g, '-').replace(/-$/, '');

    const d1 = new Date(normalized1);
    const d2 = new Date(normalized2);

    return d1 - d2;
}

// 모듈 export (Node.js 환경)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatDate,
        reverseDateFormat,
        getCurrentDate,
        isValidDate,
        compareDates
    };
}
