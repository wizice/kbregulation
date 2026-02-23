// =================== 글꼴 크기 조절 기능 - regulation-content 포함 버전 ===================
// 글꼴 크기 레벨 정의
const FONT_SIZES = ['xs', 'sm', 'md', 'lg', 'xl', 'xxl'];
const FONT_SIZE_NAMES = {
    'xs': '매우 작게',
    'sm': '작게', 
    'md': '보통',
    'lg': '크게',
    'xl': '매우 크게',
    'xxl': '최대'
};
const DEFAULT_FONT_SIZE_INDEX = 2; // 'md' (기본 크기)
let currentFontSizeIndex = DEFAULT_FONT_SIZE_INDEX;

// 글꼴 크기 증가
function increaseFontSize() {
    if (currentFontSizeIndex < FONT_SIZES.length - 1) {
        currentFontSizeIndex++;
        applyFontSize();
        //showFontSizeToast('글꼴 크기 증가', FONT_SIZES[currentFontSizeIndex]);
    } else {
        showFontSizeToast('최대 크기입니다', FONT_SIZES[currentFontSizeIndex]);
    }
}

// 글꼴 크기 감소
function decreaseFontSize() {
    if (currentFontSizeIndex > 0) {
        currentFontSizeIndex--;
        applyFontSize();
        //showFontSizeToast('글꼴 크기 감소', FONT_SIZES[currentFontSizeIndex]);
    } else {
        showFontSizeToast('최소 크기입니다', FONT_SIZES[currentFontSizeIndex]);
    }
}

// 글꼴 크기 초기화
function resetFontSize() {
    currentFontSizeIndex = DEFAULT_FONT_SIZE_INDEX;
    applyFontSize();
    //showFontSizeToast('글꼴 크기 초기화', FONT_SIZES[currentFontSizeIndex]);
}

// 개선된 글꼴 크기 적용 함수 - regulation-content까지 포함
function applyFontSize() {
    // 메인 컨테이너 찾기 (여러 선택자 시도)
    const mainContainers = [
        document.querySelector('.regulation-detail'),           // 메인 페이지
        document.getElementById('regulationContent'),           // 새창 페이지
        document.getElementById('contentBody'),                 // contentBody
        document.querySelector('#contentBody .regulation-detail') // 중첩
    ];
    
    const mainContainer = mainContainers.find(element => element !== null);
    
    if (!mainContainer) {
        console.error('글꼴 크기를 적용할 메인 컨테이너를 찾을 수 없습니다.');
        return;
    }
    
    // 기존 글꼴 크기 클래스 제거
    FONT_SIZES.forEach(size => {
        mainContainer.classList.remove(`font-size-${size}`);
    });
    
    // 새 글꼴 크기 클래스 추가
    const newSizeClass = `font-size-${FONT_SIZES[currentFontSizeIndex]}`;
    mainContainer.classList.add(newSizeClass);
    
    // CSS 변수도 직접 설정
    const fontSizeValue = getFontSizeValue(FONT_SIZES[currentFontSizeIndex]);
    mainContainer.style.setProperty('--content-font-size', fontSizeValue);
    
    // ✅ 수정된 부분: regulation-content에 직접 스타일 적용
    const regulationContent = mainContainer.querySelector('.regulation-content');
    if (regulationContent) {
        regulationContent.style.fontSize = fontSizeValue;
        
        // ✅ 모든 하위 요소를 단순하게 선택
        const allElements = regulationContent.querySelectorAll('*');
        
        allElements.forEach(element => {
            // ✅ 수정된 예외 조건 (중복 제거)
            const isExcluded = element.closest('.regulation-meta-table') || 
                              element.closest('.mobile-meta-cards') || 
                              element.closest('.page-actions') ||
                              element.classList.contains('regulation-meta-table') ||
                              element.classList.contains('mobile-meta-cards') ||
                              element.classList.contains('page-actions') ||
                              element.classList.contains('action-btn');
            
            if (!isExcluded) {
                element.style.fontSize = fontSizeValue;
                console.log(`폰트 적용: ${element.tagName}.${element.className} = ${fontSizeValue}`);
            } else {
                console.log(`폰트 제외: ${element.tagName}.${element.className}`);
            }
        });
    }
    
    // ✅ 추가: 특정 요소들에 개별적으로 적용
    
    // article-title들 (조금 더 크게)
    const articleTitles = mainContainer.querySelectorAll('.article-title');
    articleTitles.forEach(title => {
        if (!title.closest('.regulation-meta-table')) {
            title.style.fontSize = `calc(${fontSizeValue} * 1.2)`;
            console.log(`article-title 폰트 적용: calc(${fontSizeValue} * 1.2)`);
        }
    });
    
    // article-item들
    const articleItems = mainContainer.querySelectorAll('.article-item');
    articleItems.forEach(item => {
        if (!item.closest('.regulation-meta-table')) {
            item.style.fontSize = fontSizeValue;
        }
    });
    
    // article-sub-item들
    const articleSubItems = mainContainer.querySelectorAll('.article-sub-item');
    articleSubItems.forEach(item => {
        if (!item.closest('.regulation-meta-table')) {
            item.style.fontSize = fontSizeValue;
        }
    });
    
    // appendix-section
    const appendixSection = mainContainer.querySelector('.appendix-section');
    if (appendixSection) {
        const appendixElements = appendixSection.querySelectorAll('*');
        appendixElements.forEach(element => {
            element.style.fontSize = fontSizeValue;
        });
    }
    
    // 로컬스토리지에 저장
    localStorage.setItem('regulationFontSize', FONT_SIZES[currentFontSizeIndex]);
    
    console.log(`글꼴 크기 적용됨: ${newSizeClass} (${fontSizeValue}), 컨테이너:`, mainContainer);
    if (regulationContent) {
        console.log('regulation-content에도 적용됨:', regulationContent);
    }
}

// 글꼴 크기 값 반환 함수
function getFontSizeValue(sizeKey) {
    const sizeMap = {
        'xs': '0.9em',
        'sm': '0.95em',
        'md': '1.0em',
        'lg': '1.05em',
        'xl': '1.1em',
        'xxl': '1.15em'
    };
    return sizeMap[sizeKey] || '1.0em';
}

// 글꼴 크기 토스트 메시지
function showFontSizeToast(message, size) {
    // 기존 토스트 제거
    const existingToast = document.querySelector('.font-size-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = 'font-size-toast';
    toast.style.cssText = `
        position: fixed;
        top: 90px;
        right: 20px;
        background: #2786dd;
        color: white;
        padding: 12px 16px;
        border-radius: 6px;
        z-index: 10000;
        font-size: 14px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    
    toast.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 2px; font-size: 14px !important;">${message}</div>
    `;
    
    document.body.appendChild(toast);
    
    // 애니메이션
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // 2초 후 제거
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 2000);
}

// 저장된 글꼴 크기 로드 함수
function loadSavedFontSize() {
    const savedSize = localStorage.getItem('regulationFontSize');
    if (savedSize && FONT_SIZES.includes(savedSize)) {
        const savedIndex = FONT_SIZES.indexOf(savedSize);
        currentFontSizeIndex = savedIndex;

        // 즉시 적용 (내규 전환 시 깜빡임 방지)
        applyFontSize();

        console.log(`저장된 글꼴 크기 로드됨: ${savedSize}`);
    } else {
        console.log('저장된 글꼴 크기가 없습니다. 기본값 사용.');
    }
}

// 디버깅용 함수 - 더 상세한 정보
function debugFontSize() {
    console.log('=== 글꼴 크기 디버깅 정보 ===');
    console.log('현재 인덱스:', currentFontSizeIndex);
    console.log('현재 크기:', FONT_SIZES[currentFontSizeIndex]);
    console.log('현재 값:', getFontSizeValue(FONT_SIZES[currentFontSizeIndex]));
    
    console.log('\n사용 가능한 컨테이너들:');
    console.log('  .regulation-detail:', document.querySelector('.regulation-detail'));
    console.log('  #regulationContent:', document.getElementById('regulationContent'));
    console.log('  #contentBody:', document.getElementById('contentBody'));
    
    console.log('\n내용 요소들:');
    console.log('  .regulation-content:', document.querySelector('.regulation-content'));
    console.log('  .article-title들:', document.querySelectorAll('.article-title').length, '개');
    console.log('  .article-item들:', document.querySelectorAll('.article-item').length, '개');
    
    console.log('\n저장된 값:', localStorage.getItem('regulationFontSize'));
    
    // 현재 적용된 스타일 확인
    const mainContainer = document.querySelector('.regulation-detail') || document.getElementById('regulationContent');
    if (mainContainer) {
        console.log('\n현재 컨테이너 클래스:', mainContainer.className);
        console.log('CSS 변수 값:', getComputedStyle(mainContainer).getPropertyValue('--content-font-size'));
    }
}

// 초기화 함수
function initializeFontSizeControl() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadSavedFontSize);
    } else {
        loadSavedFontSize();
    }
    
    console.log('글꼴 크기 조절 기능 초기화 완료');
}

// 키보드 단축키
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && (e.key === '+' || e.key === '=')) {
        e.preventDefault();
        increaseFontSize();
    }
    else if (e.ctrlKey && e.key === '-') {
        e.preventDefault();
        decreaseFontSize();
    }
    else if (e.ctrlKey && e.key === '0') {
        e.preventDefault();
        resetFontSize();
    }
});

// 자동 초기화
initializeFontSizeControl();


// =================== 공통 부록 기능 ===================

// ========== 부록 PDF 매핑 테이블 ==========
const APPENDIX_PDF_MAPPING = {
    // 매핑 키 형식: "내규코드|부록번호|부록명"
    '1.2.1|1|구두처방 의약품 목록': '1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf',
    '1.2.1|2|구두처방 검사 목록': '1.2.1._부록2._구두처방_검사_목록_20250623개정.pdf',
    '1.2.2|1|PRN 처방 의약품 목록': '1.2.2._부록1._PRN_처방_의약품_목록_20251103개정.pdf',
    '1.2.2|2|PRN 처방 검사 목록': '1.2.2._부록2._PRN_검사_목록_20250623개정.pdf',
    '1.2.4|1|심초음파실 CVR 지침': '1.2.4._부록1._심초음파실_CVR_지침_202503검토.pdf',
    '1.3.1|1|수술 별 수술부위 표시 지침': '1.3.1._부록1._수술_별_수술부위_표시_지침_202503개정.pdf',
    '1.3.2|1|침습적 시술 목록': '1.3.2._부록1._침습적_시술_목록_202503검토.pdf',
    '1.4.1|1|낙상예방 관리지침': '1.4.1._부록1._낙상예방_관리지침_202503개정.pdf',

    '2.1.2.2|1|병동 내 위해도구 점검일지': '2.1.2.2._부록1._병동_내_위해도구_점검일지_202503개정.pdf',
    '2.1.2.2|2|환자 및 보호자 물품 검사 현황': '2.1.2.2._부록2._환자_및_보호자_물품_검사_현황_202503검토.pdf',
    '2.1.2.2|3|자살의 위험성 평가(SSS, Severance Suicide Scale)': '2.1.2.2._부록3._자살의_위험성_평가(SSS)_202503검토_(3.2.6.1._부록2_동일).pdf',
    '2.1.2.2|4|자해의 위험성 평가(SDSHS, Severance Deliberate Self Harm Scale)': '2.1.2.2._부록4._자해의_위험성_평가(SDSHS)_202503검토_(3.2.6.1._부록3_동일).pdf',
    '2.1.2.3|1|환자탈원보고서': '2.1.2.3._부록1._환자탈원보고서_202503검토.pdf',
    '2.1.3.2|1|신생아 진료지침 가이드라인': '2.1.3.2._부록1._신생아_진료지침_가이드라인_202503검토.pdf',
    '2.1.4.2|1|병원 내 이송 시 환자 분류': '2.1.4.2._부록1._병원_내_이송_시_환자_분류_20250704수정.pdf',
    '2.1.4.2|2|병원 내 이송 시 환자 분류_응급진료센터': '2.1.4.2._부록2._병원_내_이송_시_환자_분류_응급진료센터_20250704수정.pdf',
    '2.1.5.2|1|KB신용정보 중환자 이송체계(STARS)': '2.1.5.2._부록1._KB신용정보_중환자_이송체계(STARS)_202503검토_(3.2.1.1._부록2_동일).pdf',
    '2.1.5.3|1|무단이탈 환자 발생시 대처 매뉴얼': '2.1.5.3._부록1._무단이탈_환자_발생시_대처_매뉴얼_202503검토.pdf',
    '2.1.5.3|2|초상권 사용 동의서' : '2.1.5.3._부록2._초상권_사용_동의서_202503검토.pdf',
    '2.1.5.3|3|환자탈원보고서': '2.1.5.3._부록3._환자탈원보고서_202503검토.pdf',
    '2.1.6.1|1|외래예약 및 입원 등에 관한 규정': '2.1.6.1._부록1._외래예약_및_입원_등에_관한_규정_202503검토.pdf',
    '2.2.1.1|1|외래환자 초기평가 항목': '2.2.1.1._부록1._외래환자_초기평가_항목_202503검토.pdf',
    '2.2.1.1|2|진료지원부서 환자상태 평가항목': '2.2.1.1._부록2._진료지원부서_환자상태_평가항목_202503검토.pdf',
    '2.2.1.1|3|외래환자 귀가 시 환자상태 평가항목': '2.2.1.1._부록3._외래환자_귀가_시_환자상태_평가항목_202503검토.pdf',
    '2.2.2.1|1|입원환자 초기평가 항목': '2.2.2.1._부록1._입원환자_초기평가_항목_202503검토.pdf',
    '2.3.1.1|1|진단검사의학과 수탁 및 위탁검사 운영지침': '2.3.1.1._부록1._진단검사의학과_수탁_및_위탁검사_운영지침_202503검토.pdf',
    '2.3.1.1|2|진단검사의학과 수탁검사 의뢰기관별 리스트': '2.3.1.1._부록2._진단검사의학과_수탁검사_의뢰기관별_리스트.pdf',
    '2.3.1.1|3|진단검사의학과 위탁검사 의뢰기관별 리스트': '2.3.1.1._부록3._진단검사의학과_위탁검사_의뢰기관별_리스트_202501검토.pdf',
    '2.3.1.1|4|통합검사위원회 운영내규': '2.3.1.1._부록4._통합검사위원회_운영내규_202503검토.pdf',
    '2.3.1.1|5|진단검사의학과 업무규정': '2.3.1.1._부록5._진단검사의학과_업무규정_202503검토.pdf',
    '2.3.1.2|1|병리과 수탁 및 위탁검사 운영지침': '2.3.1.2._부록1._병리과_수탁_및_위탁검사_운영지침_202503검토.pdf',
    '2.3.1.2|2|병리과 수탁 및 위탁검사 의뢰기관별 리스트': '2.3.1.2._부록2._병리과_수탁_및_위탁검사_의뢰기관별_리스트_202503검토.pdf',
    '2.3.1.2|3|병리과 업무규정': '2.3.1.2._부록3._병리과_업무규정_202503검토.pdf',
    '2.3.2.1|1|진단검사의학과 TAT 지침': '2.3.2.1._부록1._진단검사의학과_TAT_지침_202503검토.pdf',
    '2.3.2.1|2|진단검사의학과 TAT 지침 – 검사별 최대보고시간': '2.3.2.1._부록2._진단검사의학과_TAT_지침_검사별_최대보고시간_202503검토.pdf',
    '2.3.2.1|3|진단검사의학과 CVR 지침': '2.3.2.1._부록3._진단검사의학과_CVR_지침_202503개정.pdf',
    '2.3.2.2|1|병리과 TAT 지침': '2.3.2.2._부록1._병리과_TAT_지침_202503검토.pdf',
    '2.3.3.1|1|검체검사실 안전관리지침': '2.3.3.1._부록1._검체검사실_안전관리지침_202503검토.pdf',
    '2.3.4.1|1|혈액제제의 보존 기준': '2.3.4.1._부록1._혈액제제의_보존_기준_202503검토.pdf',
    '2.3.5.1|1|영상의학과 업무규정': '2.3.5.1._부록1._영상의학과_업무규정_202503개정.pdf',
    '2.3.5.1|2|핵의학과 업무규정 및 지침서': '2.3.5.1._부록2._핵의학과_업무규정_및_지침서_202503검토.pdf',
    '2.3.5.1|3|조영제 사용규정': '2.3.5.1._부록3._조영제_사용규정_202503검토.pdf',
    '2.3.6.1|1|영상의학과 TAT 지침': '2.3.6.1._부록1._영상의학과_TAT_지침_202503검토.pdf',
    '2.3.6.1|2|영상의학과 CVR 지침': '2.3.6.1._부록2._영상의학과_CVR_지침_202503검토.pdf',
    '2.3.6.2|1|핵의학과 TAT 지침': '2.3.6.2._부록1._핵의학과_TAT_지침_202503검토.pdf',
    '2.3.6.2|2|핵의학과 CVR 지침': '2.3.6.2._부록2._핵의학과_CVR_지침_202503검토.pdf',
    '2.3.7.1|1|개인용 방사선 방호장비 관리 매뉴얼': '2.3.7.1._부록1._개인용_방사선_방호장비_관리_매뉴얼_202503검토.pdf',

    '3.1.3.1|1|통증평가 도구': '3.1.3.1._부록1._통증평가_도구_202503검토.pdf',
    '3.1.3.1|2|통증 중재 순서도':'3.1.3.1._부록2._통증_중재_순서도_202503제정.pdf',
    '3.1.4.1|1|식사처방 지침(요약)': '3.1.4.1._부록1._식사처방_지침(요약)_202503개정.pdf',
    '3.1.4.1|2|치료식 식단 작성 지침': '3.1.4.1._부록2._치료식_식단_작성_지침_202503개정.pdf',
    '3.1.4.1|3|임상영양관리 지침(요약)': '3.1.4.1._부록3._임상영양관리_지침(요약)_202503개정.pdf',
    '3.1.4.1|4|영양상담 지침': '3.1.4.1._부록4._영양상담_지침_202503개정.pdf',
    '3.1.4.1|5|치료식 설명 지침': '3.1.4.1._부록5._치료식_설명_지침_202503개정.pdf',
    '3.1.5.1|1|경장영양': '3.1.5.1._부록1._경장영양_202503개정.pdf',
    '3.1.5.1|2|정맥영양': '3.1.5.1._부록2._정맥영양_202503개정.pdf',
    '3.1.6.1|1|욕창 예방 관리지침': '3.1.6.1._부록1._욕창_예방_관리지침_202503검토.pdf',
    '3.1.9.1|1|고위험 알람 의료기기 파라미터 설정 기준 및 권한': '3.1.9.1._부록1._고위험_알람_의료기기_파라미터_설정_기준_및_권한_202503개정.pdf',
    '3.2.1.1|1|응급진료센터 중증도 분류': '3.2.1.1._부록1._응급진료센터_중증도_분류_202503검토.pdf',
    '3.2.1.1|2|KB신용정보 중환자 이송체계(STARS)': '3.2.1.1._부록2._KB신용정보_중환자_이송체계(STARS)_202503검토_(2.1.5.2._부록1_동일).pdf',
    '3.2.1.1|3|환자흐름 관리 프로세스': '3.2.1.1._부록3._환자흐름_관리_프로세스_202503검토.pdf',
    '3.2.1.1|4|응급진료센터 출입통제': '3.2.1.1._부록4._응급진료센터_출입통제_202503검토.pdf',
    '3.2.1.1|5|중증응급환자 수용 정보 관리 지침': '3.2.1.1._부록5._중증응급환자_수용_정보_관리_지침_202503검토.pdf',
    '3.2.1.1|6|응급 회송(전원) 조정 매뉴얼': '3.2.1.1._부록6._응급_회송(전원)_조정_매뉴얼_202503검토.pdf',
    '3.2.1.1|7|KB신용정보 재난대책 지침': '3.2.1.1._부록7._KB신용정보_재난대책_지침_202503검토_(11.7.1._부록1_동일).pdf',
    '3.2.1.1|8|신종 감염병 의심환자 응급진료센터 내원 시 흐름도': '3.2.1.1._부록8._신종_감염병_의심환자_응급진료센터_내원_시_흐름도_202503검토.pdf',
    '3.2.1.1|9|소아전문응급의료센터 운영관리': '3.2.1.1._부록9._소아전문응급의료센터_운영관리_202503검토.pdf',
    '3.2.1.5|1|가정용 인공호흡기 환자 사용 시 관리': '3.2.1.5._부록1._가정용_인공호흡기_환자_사용_시_관리_202503검토.pdf',
    '3.2.2.1|1|구역별 심폐소생팀 담당 진료과': '3.2.2.1._부록1._구역별_심폐소생팀_담당_진료과_202503검토.pdf',
    '3.2.2.1|2|기본심폐소생술 순서도(성인, 소아∙영아)': '3.2.2.1._부록2._기본심폐소생술_순서도(성인,_소아,_영아)_202503검토.pdf',
    '3.2.2.1|3|전문소생술 순서도(성인, 소아, 신생아)': '3.2.2.1._부록3._전문소생술_순서도(성인,_소아,_신생아)_202503검토.pdf',
    '3.2.2.1|4|COVID-19 및 유행성 감염증 의심 시 기본심폐소생술 순서도(성인, 소아)': '3.2.2.1._부록4._COVID-19_및_유행성_감염증_의심_시_기본심폐소생술_순서도(성인,_소아)_202503검토.pdf',
    '3.2.2.1|5|COVID-19 및 유행성 감염증 의심 시 전문소생술 순서도(성인, 소아)': '3.2.2.1._부록5._COVID-19_및_유행성_감염증_의심_시_전문소생술_순서도(성인,_소아)_202503검토.pdf',
    '3.2.2.1|6|의료장비 매뉴얼-제세동기': '3.2.2.1._부록6._의료장비_매뉴얼-제세동기_20250620개정.pdf',
    '3.2.2.2|1|Emergency Cart 관리지침(성인용)': '3.2.2.2._부록1._Emergency_Cart_관리지침(성인용)_202503검토.pdf',
    '3.2.2.2|2|Emergency Cart 관리지침(소아용)': '3.2.2.2._부록2._Emergency_Cart_관리지침(소아용)_202503검토.pdf',
    '3.2.2.2|3|Emergency Cart 배치도(성인)': '3.2.2.2._부록3._Emergency_Cart_배치도(성인)_202503검토.pdf',
    '3.2.2.2|4|Emergency Cart 배치도(소아)': '3.2.2.2._부록4._Emergency_Cart_배치도(소아)_202503검토.pdf',
    '3.2.2.2|5|응급의약품(Emergency Cart) 비치부서 목록': '3.2.2.2._부록5._응급의약품(Emergengy_Cart)_비치부서_목록_202503검토.pdf',
    '3.2.2.2|6|Emergency Cart 점검표(성인)': '3.2.2.2._부록6._Emergency_Cart_점검표(성인)_20250905수정.pdf',
    '3.2.2.2|7|Emergency Cart 점검표(성인)_약품 유효기간 점검표': '3.2.2.2._부록7._Emergency_Cart_점검표(성인)_약품_유효기간_점검표_20250905수정.pdf',
    '3.2.2.2|8|Emergency Cart 점검표(소아)': '3.2.2.2._부록8._Emergency_Cart_점검표(소아)_20250905수정.pdf',
    '3.2.2.2|9|Emergency Cart 점검표(소아)_약품 유효기간 점검표': '3.2.2.2._부록9._Emergency_Cart_점검표(소아)_약품_유효기간_점검표_20250905수정.pdf',
    '3.2.2.2|10|Security Seal 점검표': '3.2.2.2._부록10.__Security_Seal_점검표_20250905수정.pdf',
    '3.2.3.1|1|혈액제제 별 수혈지침': '3.2.3.1._부록1._혈액제제별_수혈지침_202503검토.pdf',
    '3.2.3.1|2|수혈부작용 관리': '3.2.3.1._부록2._수혈부작용_관리_202503검토.pdf',
    '3.2.4.1|1|주사용 항암제 안전사용지침': '3.2.4.1._부록1._주사용_항암제_안전사용지침_202503검토.pdf',
    '3.2.4.1|2|항암제 안전성표': '3.2.4.1._부록2._항암제_안정성표_202503검토.pdf',
    '3.2.4.1|3|항암제 처방 감사(Regimen Screening) 지침': '3.2.4.1._부록3._항암제_처방_감사(Regimen_Screening)_지침_202503개정.pdf',
    '3.2.4.1|4|항암제 조제 지침': '3.2.4.1._부록4._항암제_조제지침_202503검토_(4.4.2._부록16_동일).pdf',
    '3.2.4.1|5|항암제 감사 지침': '3.2.4.1._부록5._항암제_감사_지침_202503검토.pdf',
    '3.2.4.1|6|항암화학요법 투여 시 주의사항 및 부작용 발생 시 대처방안_전체 성분명순(80개 성분)': '3.2.4.1._부록6._항암약물요법_투여_시_주의사항_및_부작용_발생_시_대처방안_전체_성분명순(80개_성분)_20250905수정.pdf',
    '3.2.4.1|7|항암화학요법 투여 시 주의사항 및 부작용 발생 시 대처방안_대표적 약제 부작용(10품목)': '3.2.4.1._부록7._항암약물요법_투여_시_주의사항_및_부작용_발생_시_대처방안_대표적_약제_부작용(10품목)_20250905수정.pdf',
    '3.2.4.1|8|항암화학요법 투여 시 주의사항 및 부작용 발생 시 대처방안_일반 부작용 대처법(7가지)': '3.2.4.1._부록8._항암약물요법_투여_시_주의사항_및_부작용_발생_시_대처방안_일반_부작용_대처법(7가지)_20250905수정.pdf',
    '3.2.5.1|1|간호국 업무지침서-신체보호대 사용 시 간호': '3.2.5.1._부록1._간호국_업무지침서-신체보호대_사용_시_간호_202503검토.pdf',
    '3.2.5.2|1|간호국 특수간호기술 매뉴얼-강박환자 간호': '3.2.5.2._부록1._간호국_특수간호기술_매뉴얼_강박환자_간호_202503검토.pdf',
    '3.2.6.1|1|자살, 자해 위험도에 따른 알고리즘': '3.2.6.1._부록1._자살_자해_위험도에_따른_알고리즘_202503검토.pdf',
    '3.2.6.1|2|자살의 위험성 평가(SSS, Severance Suicide Scale)': '3.2.6.1._부록2._자살의_위험성_평가(SSS)_202503검토_(2.1.2.2._부록3_동일).pdf',
    '3.2.6.1|3|자해의 위험성 평가(SDSHS, Severance Deliberate Self Harm Scale)': '3.2.6.1._부록3._자해의_위험성_평가(SDSHS)_202503검토_(2.1.2.2._부록4_동일).pdf',
    '3.2.6.1|4|자살예방 약속(No Harm Contract)': '3.2.6.1._부록4._자살예방_약속(No_Harm_Contract)_202503검토.pdf',
    '3.2.6.1|5|의도적 자해 예방을 위한 약속(No Harm Contract)': '3.2.6.1._부록5._의도적_자해_예방을_위한_약속(No_Harm_Contract)_202503검토.pdf',

    '4.1.1|1|약사위원회 운영내규': '4.1.1._부록1._약사위원회_운영내규_202504개정.pdf',
    '4.1.1|2|약사위원회 운영세칙': '4.1.1._부록2._약사위원회_운영세칙_202504개정.pdf',
    '4.1.1|3|신약심의위원회 운영내규': '4.1.1._부록3._신약심의위원회_운영내규_202504제정.pdf',
    '4.1.1|4|약물관리위원회 운영내규': '4.1.1._부록4._약물관리위원회_운영내규_202504개정.pdf',
    '4.1.1|5|의약품부작용감시위원회 운영내규': '4.1.1._부록5._의약품부작용감시위원회_운영내규_202504개정.pdf',
    '4.3.1|1|의약품 유효기간 관리지침': '4.3.1._부록1._의약품_유효기간_관리지침_202502개정.pdf',
    '4.3.2|1|응급의약품 및 비품약 관리지침(약무국)': '4.3.2._부록1._응급의약품_및_비품약_관리지침(약무국)_202502개정_(4.3.3._부록4_동일).pdf',
    '4.3.3|1|비품약 목록': '4.3.3._부록1._비품약_목록_202502개정.pdf',
    '4.3.3|2|비품약 정보': '4.3.3._부록2._비품약_정보_202505개정.pdf',
    '4.3.3|3|간호국 비품약 관리지침': '4.3.3._부록3._간호국_비품약_관리지침_202301검토.pdf',
    '4.3.3|4|응급의약품 및 비품약 관리지침(약무국)': '4.3.3._부록4._응급의약품_및_비품약_관리지침(약무국)_202502개정_(4.3.2._부록1_동일).pdf',
    '4.3.4|1|KB신용정보 마약류 관리지침': '4.3.4._부록1._KB신용정보_마약류_관리지침_202503개정.pdf',
    '4.3.4|2|사고마약류 관련 서식(마약류 파손 보고서, 환자반납 발생 보고서)': '4.3.4._부록2._사고마약류_관련_서식(마약류_파손_보고서,_환자반납_발생_보고서)_202503검토.pdf',
    '4.3.5|1|KB신용정보 고위험의약품 목록': '4.3.5._부록1._KB신용정보_고위험의약품_목록_202503개정.pdf',
    '4.3.5|2|고위험의약품 투여 시 주의사항 및 부작용 발생 시 대처방안': '4.3.5._부록2._고위험의약품_투여_시_주의사항_및_부작용_발생_시_대처방안_202503검토.pdf',
    '4.3.5|3|고농도전해질 별 안전사용지침': '4.3.5._부록3._고농도전해질_별_안전사용지침_202504개정.pdf',
    '4.3.5|4|전해질 대체요법에 대한 표준 프로토콜': '4.3.5._부록4._전해질_대체요법에_대한_표준_프로토콜_202501개정.pdf',
    '4.3.5|5|Penicillin G Potassium 안전사용지침': '4.3.5._부록5._Penicillin_G_potassium_안전사용_지침_202503검토.pdf',
    '4.3.5|6|혈전용해제 안전사용지침': '4.3.5._부록6._혈전용해제_안전사용지침_202502검토.pdf',
    '4.3.5|7|주사용 항암제 안전사용지침': '4.3.5._부록7._주사용_항암제_안전사용지침_20250526개정.pdf',
    '4.3.5|8|중등도 진정 의약품 안전사용 지침': '4.3.5._부록8._중등도_진정_의약품_안전사용지침_202503개정.pdf',
    '4.3.5|9|신경근 차단제 안전사용지침': '4.3.5._부록9._신경근_차단제_안전사용지침_202503개정.pdf',
    '4.3.5|10|Heparin inj 안전사용지침': '4.3.5._부록10._Heparin_inj._안전사용지침_202503개정.pdf',
    '4.3.5|11|Warfarin 안전사용지침': '4.3.5._부록11._Warfarin_안전사용지침_202503개정.pdf',
    '4.3.5|12|Insulin(vial) 안전사용지침': '4.3.5._부록12._Insulin(vial)_안전사용지침_202503검토.pdf',
    '4.3.6|1|주의를 요하는 의약품 목록 – 냉장보관이 필요한 의약품(개봉 전·후 의약품 포함)': '4.3.6._부록1._주의를_요하는_의약품_목록_-_냉장보관이_필요한_의약품(개봉_전,후_의약품_포함)_20250905수정.pdf',
    '4.3.6|2|주의를 요하는 의약품 목록 – 차광이 필요한 의약품': '4.3.6._부록2._주의를_요하는_의약품_목록_-_차광이_필요한_의약품_20250905수정.pdf',
    '4.3.6|3|주의를 요하는 의약품 목록 – 유사모양/유사발음 의약품': '4.3.6._부록3._주의를_요하는_의약품_목록_-_유사모양,유사발음_의약품_20250905수정.pdf',
    '4.3.6|4|주의를 요하는 의약품 목록 – 원내 백신': '4.3.6._부록4._주의를_요하는_의약품_목록_-_원내_백신_20250905수정.pdf',
    '4.3.6|5|실내경보시스템이 구비되어 있는 냉장고 관리지침': '4.3.6._부록5._실내경보_시스템이_구비되어_있는_냉장고_관리지침_20250905수정.pdf',
    '4.3.6|6|백신 보관 관리지침': '4.3.6._부록6._백신_보관_관리지침_20250905수정.pdf',
    '4.3.7|1|임상시험센터 표준작업지침서 임상시험용 의약품 관리': '4.3.7._부록1._임상시험센터_표준작업지침서_임상시험용_의약품_관리_202503검토.pdf',
    '4.4.1|1|체중기반으로 처방하는 의약품 목록': '4.4.1._부록1._체중_기반으로_처방하는_의약품_목록_202502개정.pdf',
    '4.4.1|2|관리의약품 목록': '4.4.1._부록2._관리의약품_목록_20250902개정.pdf',
    '4.4.1|3|신기능 저하 환자의 비스테로이드성항염증제(NSAID) 사용지침': '4.4.1._부록3._신기능_저하_환자의_비스테로이드성항염증제(NSAID)_사용지침_202503검토.pdf',
    '4.4.2|1|소아 조제지침': '4.4.2._부록1._소아_조제지침_20250905수정.pdf',
    '4.4.2|2|산제 조제지침': '4.4.2._부록2._산제_조제지침_20250905수정.pdf',
    '4.4.2|3|정제 및 캅셀제 조제지침': '4.4.2._부록3._정제_및_캅셀제_조제지침_20250905수정.pdf',
    '4.4.2|4|수약/외용약 조제지침': '4.4.2._부록4._수약,_외용약_조제지침_20250905수정.pdf',
    '4.4.2|5|주사제 조제지침': '4.4.2._부록5._주사제_조제지침_20250905수정.pdf',
    '4.4.2|6|항암제 조제지침': '4.4.2._부록6._항암제_조제지침_20250905수정(3.2.4.1._부록4_동일).pdf',
    '4.4.2|7|조제실제제 조제지침': '4.4.2._부록7._조제실제제_조제지침_20250905수정.pdf',
    '4.4.2|8|TPN 조제지침': '4.4.2._부록8._TPN_조제지침_20250905수정.pdf',
    '4.4.2|9|취급주의 의약품 조제지침': '4.4.2._부록9._취급주의_의약품_조제지침_20250905수정.pdf',
    '4.4.2|10|임상약제(영양집중지원팀) 업무지침(TPN 업무관련)': '4.4.2._부록10._임상약제(영양집중지원팀)_업무지침(TPN_업무관련)_20250905수정.pdf',
    '4.4.2|11|약물사용 오류 예방 및 처리지침': '4.4.2._부록11._약물사용_오류_예방_및_처리지침_20250905수정.pdf',
    '4.4.2|12|조제안전관리지침': '4.4.2._부록12._조제안전관리지침_20250905수정.pdf',
    '4.4.2|13|조제안전관리지침(조제실)': '4.4.2._부록13._조제안전관리지침(조제실)_20250905수정.pdf',
    '4.4.2|14|조제안전관리지침(특수조제실)': '4.4.2._부록14._조제안전관리지침(특수조제실)_20250905수정.pdf',
    '4.4.2|15|항암제 파손 시 대처지침': '4.4.2._부록15._항암제_파손_시_대처_지침_20250905수정.pdf',
    '4.4.2|16|원외처방전 관리지침': '4.4.2._부록16._원외처방전_관리지침_20250905수정.pdf',
    '4.4.2|17|감사지침': '4.4.2._부록17._감사지침_20250905수정.pdf',
    '4.5.1|1|의약품 표준 투여시간': '4.5.1._부록1._의약품_표준_투여시간_202503검토.pdf',
    '4.5.1|2|의약품 반환 및 반납지침': '4.5.1._부록2._의약품_반환_및_반납지침_202503검토.pdf',
    '4.6.1|1|AATRA(Acute Assessment & Treatment of Radiocontrast media Allergy) Protocol': '4.6.1._부록1._AATRA_protocol_202503검토.pdf',    
   
    '5.2.1|1|수술환자 피부 관리 지침': '5.2.1._부록1._수술환자_피부관리_지침_202503검토.pdf',
    '5.2.1|2|수술계수(Count) 관리 지침': '5.2.1._부록2._수술계수(count)_관리_지침_202503검토.pdf',
    '5.4.1|1|성인 진정 약물 사용 가이드라인': '5.4.1._부록1._성인_진정_약물_사용_가이드라인_202503검토.pdf',
    '5.4.1|2|ASA(American Society of Anesthesiologists) Physical Status Classification – modified by Severance Hospital': '5.4.1._부록2._ASA(American_Society_of_Anesthesiologists)_Physical_Status_Classification_-_modified_by_Severance_202503검토_(5.4.2._부록4,_5.5.1._부록2_동일).pdf',
    '5.4.2|1|소아청소년 진정 약물 사용 가이드라인': '5.4.2._부록1._소아청소년_진정_약물_사용_가이드라인_202503검토.pdf',
    '5.4.2|2|소아 진정 프로토콜': '5.4.2._부록2._소아_진정_프로토콜_202503검토.pdf',
    '5.4.2|3|전신마취 및 소아청소년 진정 시 금식시간': '5.4.2._부록3._전신마취_및_소아청소년_진정_시_금식시간_202503검토.pdf',
    '5.4.2|4|ASA(American Society of Anesthesiologists) Physical Status Classification – modified by Severance Hospital': '5.4.2._부록4._ASA(American_Society_of_Anesthesiologists)_Physical_Status_Classification_-_modified_by_Severance_202503검토_(5.4.1._부록2,_5.5.1._부록2_동일).pdf',
    '5.5.1|1|PAR score(Post Anesthetic Recovery Score)': '5.5.1._부록1._PAR_Score_(Post-Anesthetic_Recovery_Score)_202503검토.pdf',
    '5.5.1|2|ASA(American Society of Anesthesiologists) Physical Status Classification – modified by Severance Hospital': '5.5.1._부록2._ASA(American_Society_of_Anesthesiologists)_Physical_Status_Classification_-_modified_by_Severance_202503검토_(5.4.1._부록2,_5.4.2._부록4_동일).pdf',
    '5.7.1|1|공기조화기 관리지침': '5.7.1._부록1._공기조화기_관리지침_202503검토.pdf',
    '5.7.1|2|공조용 에어필터 관리지침': '5.7.1._부록2._공조용_에어필터_관리지침_202503검토.pdf',

    '6.1.1|1|권리고지 및 확인서': '6.1.1._부록1._권리고지_및_확인서_202503검토.pdf',
    '6.2.1|1|KB신용정보 학대와 방임 (의심)환자 SAFE(Stop Abuse For Everyone) Protocol': '6.2.1._부록1._KB신용정보_학대와_방임_(의심)환자_SAFE_Protocol_202503개정.pdf',
    '6.2.1|2|실종 및 유괴 예방 보호자 수칙': '6.2.1._부록2._실종_및_유괴_예방_보호자_수칙_202503검토.pdf',
    '6.2.1|3|신생아 유괴 예방을 위한 안전관리 지침': '6.2.1._부록3._신생아_유괴_예방을_위한_안전관리_지침_202503검토.pdf',
    '6.2.1|4|실종 및 유괴 대처 매뉴얼': '6.2.1._부록4._실종_및_유괴_대처_매뉴얼_202503검토.pdf',
    '6.2.1|5|아동 실종 및 유괴 시 행동강령': '6.2.1._부록5._아동_실종_및_유괴_시_행동강령_202503검토.pdf',
    '6.4.1|1|KB신용정보 사회사업팀 업무매뉴얼': '6.4.1._부록1._KB신용정보_사회사업팀_업무매뉴얼_202503검토_(10.4.3._부록1_동일).pdf',
    '6.5.1|1|동의서 목록_전산 프로그램 조회 매뉴얼': '6.5.1._부록1._동의서_목록_전산_프로그램_조회_매뉴얼_202503제정.pdf',
    '6.5.1|2|동의서 수령 약물 목록': '6.5.1._부록2._동의서_수령_약물_목록_202503개정.pdf',
    '6.6.1|1|임상시험센터 표준작업지침서': '6.6.1._부록1._임상시험센터_표준작업지침서_202503검토.pdf',
    '6.6.1|2|임상연구보호프로그램 규정': '6.6.1._부록2._임상연구보호프로그램_규정_202503검토.pdf',
    '6.6.1|3|임상연구보호프로그램 절차': '6.6.1._부록3._임상연구보호프로그램_절차_202503검토.pdf',
    '6.7.1|1|뇌사 추정자 발생 시 신고 절차': '6.7.1._부록1._뇌사_추정자_발생_시_신고_절차_202503개정.pdf',

    '7.1.1|1|의료질향상 및 환자안전위원회 운영내규': '7.1.1._부록1._의료질향상_및_환자안전위원회_운영내규_202303제정.pdf',
    '7.2.1|1|위험등록부(Risk Register)': '7.2.1._부록1._위험등록부(Risk_Register)_202503검토.pdf',
    '7.2.1|2|FMEA(Failure Mode and Effect Analysis) Methodology': '7.2.1._부록2._FMEA(Failure_Mode_and_Effect_Analysis)_Methodology_202503검토.pdf',
    '7.2.1|3|RCA(Root Cause Analysis) Methodology': '7.2.1._부록3._RCA(Root_Cause_Analysis)_Methodology_202503검토.pdf',
    '7.2.1|4|HVA(Hazard Vulnerability Analysis)': '7.2.1._부록4._HVA(Hazard_Vulnerability_Analysis)_202503검토.pdf',
    '7.3.1|1|환자안전의사소통 프로세스': '7.3.1._부록1._환자안전의사소통_프로세스_202503검토.pdf',
    '7.3.1|2|중대한 환자안전사건 관련 환자 및 보호자 분쟁 대응 프로세스': '7.3.1._부록2._중대한_환자안전사건_관련_환자_및_보호자_분쟁_대응_프로세스_202503검토.pdf',
    '7.6.1|1|질지표 관리계획서(Measure Profile)': '7.6.1._부록1._질지표_관리계획서(Measure_Profile)_202503검토.pdf',
    '7.6.2|1|데이터 검증 서식': '7.6.2._부록1._데이터_검증_서식_202503검토.pdf',
    '7.7.1|1|안전문화 행동강령(Code of conduct)': '7.7.1._부록1._안전문화_행동강령_202503개정.pdf',

    '8.1.1|1|감염관리지침': '', // 8.1.1의 감염관리지침 파일은 별도로 제공될 예정
    '8.1.2|1|KB신용정보 수술 시 예방적 항생제 사용 지침': '8.1.2._부록1._KB신용정보_수술_시_예방적_항생제_사용_지침_202503개정.pdf',
    '8.1.2|2|KB신용정보 항생제 피부시험 지침': '8.1.2._부록2._KB신용정보_항생제_피부시험_지침_202505개정(★전산개발_후_재업로드_필요).pdf',
    '8.4.1|1|감염관리지침': '', // 8.4.1의 감염관리지침 파일은 별도로 제공될 예정
    '8.5.1|1|감염관리지침': '', // 8.5.1의 감염관리지침 파일은 별도로 제공될 예정
    '8.5.2|1|감염관리지침': '', // 8.5.2의 감염관리지침 파일은 별도로 제공될 예정
    '8.5.3|1|Cutting Burr 재사용 시 세척방법': '8.5.3._부록1._Cutting_burr_재사용_시_세척방법_202503검토.pdf',
    '8.5.3|2|일회용 물품 재사용 허가 신청서': '8.5.3._부록2._일회용_물품_재사용_허가_신청서_202503검토.pdf',
    '8.6.1|1|감염관리지침': '', // 8.6.1의 감염관리지침 파일은 별도로 제공될 예정
    '8.7.1|1|감염관리지침': '', // 8.7.1의 감염관리지침 파일은 별도로 제공될 예정
    '8.8.1|1|감염관리지침': '', // 8.8.1의 감염관리지침 파일은 별도로 제공될 예정
    '8.8.3|1|감염관리지침': '', // 8.8.3의 감염관리지침 파일은 별도로 제공될 예정

    '9.1.1|1|병원운영위원회 운영규정': '9.1.1._부록1._병원운영위원회_운영내규_202003개정.pdf', 
    '9.1.1|2|위임전결규정': '9.1.1._부록2._위임전결_규정_202503개정.pdf', 
    '9.1.3|1|구입 및 계약 사무규정': '9.1.3._부록1._구입_및_계약_사무규정_202306개정.pdf', 
    '9.1.4|1|진료재료위원회 운영내규': '9.1.4._부록1._KB신용정보_진료재료위원회_운영내규_202212개정.pdf',
    '9.1.4|2|기자재위원회 운영내규': '9.1.4._부록2._기자재위원회_운영규정_202502제정.pdf', 
    '9.1.4|3|약사위원회 운영세칙': '9.1.4._부록3._약사위원회_운영세칙_202503검토.pdf',
    '9.1.4|4|자산관리 규정': '9.1.4._부록4._자산관리_규정_202011개정.pdf',
    '9.1.4|5|구입 및 계약 사무규정': '9.1.4._부록5._구입_및_계약_사무규정_202306개정.pdf',
    '9.1.5|1|KB신용정보 내규 서식': '9.1.5._부록1._KB신용정보_내규_서식_202503제정.pdf',
    '9.1.5|2|KB신용정보 내규 관리대장': '9.1.5._부록2._KB신용정보_내규_관리대장_202503검토.pdf',
    '9.4.1|1|KB신용정보 윤리강령 및 실천지침': '9.4.1._부록1._KB신용정보_윤리강령_및_실천지침_202503검토.pdf',
    '9.4.1|2|KB신용정보 병원윤리위원회 운영내규': '9.4.1._부록2._KB신용정보_병원윤리위원회_운영내규_202303개정.pdf',
    '9.4.1|3|상벌규정': '9.4.1._부록3._상벌규정_202308개정.pdf', 

    '10.1.1|1|취업규칙': '10.1.1._부록1._취업규칙_202406개정_(10.4.1._부록1_동일).pdf', 
    '10.1.1|2|일반직 인사규정': '10.1.1._부록2._일반직_인사규정_202403개정_(10.4.1._부록2동일).pdf',
    '10.1.1|3|의과대학 교원 인사관리 내규': '10.1.1._부록3._의과대학_교원_인사관리_내규(신임교원_임용지침_포함)_202412개정_(10.4.1._부록3_동일).pdf',
    '10.2.1|1|KB신용정보 자격신임위원회 운영내규': '10.2.1._부록1._KB신용정보_자격신임위원회_운영내규_201103개정.pdf',
    '10.2.1|2|임상권한 관리절차 가이드라인': '10.2.1._부록2._임상권한_관리절차_가이드라인_2022503검토.pdf',
    '10.2.1|3|임상권한 제한 요청서': '10.2.1._부록3._임상권한_제한_요청서_202503검토.pdf',
    '10.2.3|1|신의료기술 임상권한 신청서': '10.2.3._부록1._신의료기술_임상권한_신청서_202503검토.pdf',
    '10.4.1|1|취업규칙': '10.4.1._부록1._취업규칙_202406개정_(10.1.1._부록1_동일).pdf', 
    '10.4.1|2|일반직 인사규정': '10.4.1._부록2._일반직_인사규정_202403개정_(10.1.1._부록2_동일).pdf',
    '10.4.1|3|의과대학 교원 인사관리 내규': '10.4.1._부록3._의과대학_교원_인사관리_내규(신임교원_임용지침_포함)_202412개정_(10.1.1._부록3_동일).pdf',
    '10.4.2|1|기타 인력 신고서': '10.4.2._부록1._기타_인력_신고서_202503검토.pdf',
    '10.4.3|1|KB신용정보 사회사업팀 업무매뉴얼': '10.4.3._부록1._KB신용정보_사회사업팀_업무매뉴얼_202503검토_(6.4.1._부록1_동일).pdf',
    '10.5.2|1|수탁교육 의뢰서': '10.5.2._부록1._수탁교육_의뢰서_202503개정.pdf',
    '10.5.2|2|수탁생 면역력 점검표': '10.5.2._부록2._수탁생_면역력_점검표_202503개정.pdf',
    '10.5.2|3|수탁교육 동의서(영문서식 포함)': '10.5.2._부록3._수탁교육_동의서(영문서식_포함)_202503개정.pdf',
    '10.5.2|4|수탁교육비 관리지침': '10.5.2._부록4._수탁교육비_관리지침_202503개정.pdf',
    '10.5.3|1|의료원 외국인 연수 운영 규정': '10.5.3._부록1._의료원_외국인_연수_운영_규정_202106개정.pdf',
    '10.7.1|1|교직원 건강진단 지침': '10.7.1._부록1._교직원_건강진단_지침_202503개정.pdf',
    '10.7.1|2|직원 결핵검진 지침': '10.7.1._부록2._직원_결핵검진_지침_202503개정.pdf',
    '10.7.1|3|직원 성희롱·성폭력 관리 지침': '10.7.1._부록3._직원_성희롱_성폭력_관리_지침_202503검토_(10.8.1._부록3_동일).pdf',
    '10.7.1|4|직원 상담·코칭 서비스': '10.7.1._부록4._직원_상담_코칭(검사_교육)_서비스_202503개정.pdf',
    '10.7.1|5|작업환경측정 대상 부서 및 측정 항목': '10.7.1._부록5._작업환경측정_대상_부서_및_측정_항목_202503검토.pdf',
    '10.7.2|1|직무상 재해 접수, 처리 및 추후관리 과정': '10.7.2._부록1._직무상_재해_접수_처리_및_추후관리_과정_202503개정.pdf',
    '10.7.2|2|교직원 건강진단 지침': '10.7.2._부록2._교직원_건강진단_지침_202503개정.pdf',
    '10.8.1|1|폭언 및 폭행 발생 시 직원관리 Process': '10.8.1._부록1._폭언_및_폭행_발생_시_직원관리_Process_202503검토.pdf',
    '10.8.1|2|코드그레이 대응매뉴얼': '10.8.1._부록2._코드그레이_대응매뉴얼_202503검토_(11.4.1._부록1_동일).pdf',
    '10.8.1|3|직원 성희롱·성폭력 관리 지침': '10.8.1._부록3._직원_성희롱_성폭력_관리_지침_202503검토_(10.7.1._부록3_동일).pdf',
    '10.8.1|4|직장 내 괴롭힘 예방 및 처리 규정': '10.8.1._부록4._직장_내_괴롭힘_예방_및_처리_규정_202503검토.pdf',

    '11.1.1|1|시설/환경 안전사고 처리 프로세스': '11.1.1._부록1._시설_환경_안전사고_처리_프로세스_20250827수정_(11.4.1._부록2_동일).pdf',
    '11.3.1|1|KB신용정보 물질안전보건자료(MSDS)': '', // 파일이 아직 제공되지 않음
    '11.3.1|2|유해화학물질 노출 시 응급조치 요령': '11.3.1._부록2._유해화학물질_노출_시_응급조치_요령_202503개정.pdf',
    '11.3.1|3|수은 유출 시 관리지침': '11.3.1._부록3._수은_유출_시_관리지침_202503개정.pdf',
    '11.3.2|1|의료폐기물 관리지침': '11.3.2._부록1._의료폐기물_관리지침_202503개정_(11.5.5._부록1_동일).pdf',
    '11.4.1|1|코드그레이 대응매뉴얼': '11.4.1._부록1._코드그레이_대응매뉴얼_202503검토_(10.8.1._부록2_동일).pdf',
    '11.4.1|2|시설/환경 안전사고 처리 프로세스': '11.4.1._부록2._시설_환경_안전사고_처리_프로세스_20250827수정_(11.1.1._부록1_동일).pdf',
    '11.4.1|3|병문안객 출입통제 운영관리': '11.4.1._부록3._병문안객_출입통제_운영관리_20250529개정.pdf',
    '11.4.1|4|수술실 폐쇄회로 텔레비전 관리': '11.4.1._부록4._수술실_폐쇄회로_텔레비전_관리_202503검토.pdf',
    '11.5.3|1|인체삽입 의료기기(Implantable Medical Device) 목록': '11.5.3._부록1._인체삽입_의료기기(Implantable_Medical_Device)목록_202503개정.pdf',
    '11.5.3|2|인체삽입 의료기기 회수 절차': '11.5.3._부록2._인체삽입_의료기기_회수_절차_202503검토.pdf',
    '11.5.5|1|의료폐기물 관리지침': '11.5.5._부록1._의료폐기물_관리지침_202503개정_(11.3.2._부록1_동일).pdf',
    '11.6.1|1|소방계획서': '2025년_소방계획서.pdf',
    '11.7.1|1|KB신용정보 재난대책 지침': '11.7.1._부록1._KB신용정보_재난대책_지침_202503검토_(3.2.1.1._부록7_동일).pdf', 
    '11.8.1|1|신종감염병 대응 매뉴얼': '11.8.1._부록1._신종감염병_대응_매뉴얼_202503개정.pdf',
    '11.8.1|2|감염관리지침': '', // 감염관리지침 파일은 별도로 제공될 예정

    '12.1.1|1|KB신용정보 제위원회 운영내규 – 의무기록위원회': '12.1.1._부록1._KB신용정보_의무기록위원회_운영내규_202003개정.pdf', 
    '12.1.1|2|KB신용정보 제위원회 운영내규 – 표준화위원회': '12.1.1._부록2._KB신용정보_표준화위원회_운영내규_202212개정.pdf', 
    '12.1.2|1|의무기록 정정 신청서(의무기록 작성자용)': '12.1.2._부록1._의무기록_정정_신청서(의무기록작성자용)_202503검토.pdf',
    '12.1.2|2|의무기록 정정 신청서(환자용)': '12.1.2._부록2._의무기록_정정_신청서(환자용)_202503검토.pdf',
    '12.1.2|3|개인정보(정정·삭제, 처리정지) 요구에 대한 결과 통지서': '12.1.2._부록3._개인정보(정정ㆍ삭제,_처리정지)요구에_대한_결과_통지서_202503검토.pdf',
    '12.1.3|1|직종, 부서(업무), 서식별 의무기록/의료정보 접근권한': '12.1.3._부록1._의무기록정보_직종,_부서(업무),_서식별_접근권한_202503개정.pdf',
    '12.3.1|1|의료원 데이터 활용 등에 관한 규정(연세의료원 규정)': '12.3.1._부록1._의료원_데이터_활용_등에_관한_규정(연세의료원_규정)_202502개정.pdf',
    '12.3.2|1|병원정보시스템 개발 및 운영 절차': '12.3.2._부록1._병원정보시스템_개발_및_운영_절차_202503검토.pdf',
    '12.4.1|1|정보보안감사 지침': '12.4.1._부록1._정보보안감사_지침_202503검토.pdf',
    '12.4.1|2|외주용역 보안관리 지침': '12.4.1._부록2._외주용역_보안관리_지침_202503검토.pdf',
    '12.4.1|3|정보자산관리 지침': '12.4.1._부록3._정보자산관리_지침_202503검토.pdf',
    '12.4.1|4|개발 및 응용시스템 보안 지침': '12.4.1._부록4._개발_및_응용시스템_보안_지침_202503검토.pdf',
    '12.4.1|5|사용자 보안관리 지침': '12.4.1._부록5._사용자_보안관리_지침_202503검토.pdf',
    '12.4.1|6|개인정보보호 관리 지침': '12.4.1._부록6._개인정보보호_관리_지침_202503검토.pdf',
    '12.4.1|7|침해사고 대응 지침': '12.4.1._부록7._침해사고_대응_지침_202503검토.pdf',

    '13.1.1|1|의학교육(의과대학생 교육) 조직도': '13.1.1._부록1._의학교육(의과대학생_교육)_조직도_202503검토.pdf',
    '13.2.1|1|수련의 교육 조직도': '13.2.1._부록1._수련의_교육_조직도_202503검토.pdf',
    '13.2.1|2|수련의 의무기록 작성 권한 및 감독 수준': '13.2.1._부록2._수련의_의무기록_작성_권한_및_감독_수준_202503검토.pdf',
};

// PDF 파일명 가져오기 함수 (동기 버전 - fallback용)
function getAppendixPdfFileName(regulationCode, appendixIndex, appendixName) {
    console.log(`[Mapping] 검색 시작: code="${regulationCode}", index=${appendixIndex}, name="${appendixName}"`);

    // 1. 먼저 부록 이름으로 직접 찾기 (부록 번호 무시)
    // Summary JSON의 순서와 실제 파일의 부록 번호가 다를 수 있으므로
    let foundByName = false;
    for (const key in APPENDIX_PDF_MAPPING) {
        const [code, no, name] = key.split('|');
        if (code === regulationCode) {
            console.log(`[Mapping] 같은 내규 발견: "${key}" (name 매칭: ${name === appendixName})`);
            if (name === appendixName) {
                console.log(`[Mapping] ✓ Found by name: ${key} -> ${APPENDIX_PDF_MAPPING[key]}`);
                return APPENDIX_PDF_MAPPING[key];
            }
        }
    }

    // 2. 부록 번호로 찾기 (fallback)
    const mappingKey = `${regulationCode}|${appendixIndex + 1}|${appendixName}`;
    console.log(`[Mapping] 이름으로 못 찾음, 번호로 시도: "${mappingKey}"`);
    if (APPENDIX_PDF_MAPPING[mappingKey]) {
        console.log(`[Mapping] ✓ Found by index: ${mappingKey} -> ${APPENDIX_PDF_MAPPING[mappingKey]}`);
        return APPENDIX_PDF_MAPPING[mappingKey];
    }

    // 매핑이 없는 경우
    console.warn(`[Mapping] ✗ PDF 매핑을 찾을 수 없습니다: ${mappingKey}`);
    return null;
}

// 파일 시스템에서 부록 파일 정보 가져오기 (비동기)
// /static/pdf/ 디렉토리에서 파일명 패턴 매칭으로 찾기
async function getAppendixFileFromAPI(regulationCode, appendixIndex) {
    try {
        console.log(`[API] Fetching appendix for ${regulationCode}, index: ${appendixIndex}`);

        // Summary JSON에서 규정의 wzRuleSeq 찾기 - 캐시 방지를 위한 타임스탬프 추가
        const timestamp = new Date().getTime();
        const summaryResponse = await fetch(`/static/file/summary_kbregulation.json?ts=${timestamp}`);
        if (!summaryResponse.ok) {
            console.warn('[API] Summary JSON 로드 실패');
            return null;
        }

        const summaryData = await summaryResponse.json();

        // summary JSON에서 해당 규정 찾기
        let regulation = null;
        for (const chapterKey in summaryData) {
            const chapterData = summaryData[chapterKey];
            if (chapterData.regulations) {
                const found = chapterData.regulations.find(r => r.code === regulationCode);
                if (found) {
                    regulation = found;
                    break;
                }
            }
        }

        if (!regulation) {
            console.warn(`[API] 규정을 찾을 수 없습니다: ${regulationCode}`);
            return null;
        }

        const ruleSeq = regulation.wzRuleSeq || regulation.wzruleseq;
        if (!ruleSeq) {
            console.warn(`[API] wzRuleSeq를 찾을 수 없습니다: ${regulationCode}`);
            return null;
        }

        // 부록 목록 API 호출
        const appendixResponse = await fetch(`/api/v1/appendix/list/${ruleSeq}`);
        if (!appendixResponse.ok) {
            console.warn(`[API] 부록 목록 조회 실패: ${ruleSeq}`);
            return null;
        }

        const appendixList = await appendixResponse.json();

        // appendixIndex에 해당하는 부록 파일 찾기
        const appendixFile = appendixList[appendixIndex];

        if (!appendixFile) {
            console.warn(`[API] 부록 파일을 찾을 수 없습니다: index ${appendixIndex}`);
            return null;
        }

        // wzfilepath에서 실제 파일명 추출 (www/static/pdf/파일명.pdf)
        let fullFileName = appendixFile.wzappendixfilename;
        if (appendixFile.wzfilepath) {
            const pathParts = appendixFile.wzfilepath.split('/');
            fullFileName = pathParts[pathParts.length - 1];
        }

        console.log(`[API] Found appendix file: ${fullFileName}`);
        return fullFileName;

    } catch (error) {
        console.error('[API] Error fetching appendix file:', error);
        return null;
    }
}

// PDF 뷰어 URL 생성 (동기 버전 - fallback용)
function getAppendixPdfUrl(regulationCode, appendixIndex, appendixName) {
    const pdfFileName = getAppendixPdfFileName(regulationCode, appendixIndex, appendixName);

    if (!pdfFileName) {
        return null;
    }

    const currentDomain = window.location.origin;  // https://policy.yuhs.ac
    return `${currentDomain}/static/viewer/web/viewer.html?file=/static/pdf/${encodeURIComponent(pdfFileName)}`;
}

// 부록 PDF 열기 함수 (비동기로 변경)
async function openAppendixPdf(regulationCode, appendixIndex, appendixName) {

    // regulation 변수를 함수 시작 부분에서 선언 (로깅에서 사용)
    let regulation = null;

    // PDF 뷰어 열 때는 항상 사이드바 닫기 (모바일/데스크톱 모두)
    if (typeof closeSidebar === 'function') {
        closeSidebar();
    }

    // 부록을 최근 본 내규에 추가
    if (regulationCode && typeof appendixIndex === 'number' && appendixName) {
        // 해당 내규 찾기
        let parentRegulation = null;
        let parentChapter = null;

        Object.keys(hospitalRegulations).forEach(chapter => {
            const chapterData = hospitalRegulations[chapter];
            if (chapterData.regulations) {
                const foundReg = chapterData.regulations.find(reg => reg.code === regulationCode);
                if (foundReg) {
                    parentRegulation = foundReg;
                    parentChapter = chapter;
                }
            }
        });

        if (parentRegulation && parentChapter) {
            const appendixItem = {
                parentCode: regulationCode,
                parentName: parentRegulation.name,
                index: appendixIndex,
                name: appendixName
            };
            updateRecentRegulations(appendixItem, parentChapter, 'appendix');
        }
    }

    // 1. API에서 동적으로 파일 찾기 시도
    console.log(`[openAppendixPdf] Step 1: API 파일 찾기 - code="${regulationCode}", index=${appendixIndex}, name="${appendixName}"`);
    let pdfFileName = await getAppendixFileFromAPI(regulationCode, appendixIndex);
    let pdfUrl = null;

    if (pdfFileName) {
        console.log(`[openAppendixPdf] Step 2: 파일명 찾음 - "${pdfFileName}"`);

        // Summary JSON에서 ruleSeq 찾기 - 캐시 방지를 위한 타임스탬프 추가
        const timestamp = new Date().getTime();
        const summaryResponse = await fetch(`/static/file/summary_kbregulation.json?ts=${timestamp}`);
        if (summaryResponse.ok) {
            const summaryData = await summaryResponse.json();
            regulation = null;  // 이미 함수 시작 부분에서 선언됨
            let allCodes = [];  // 디버깅: 모든 코드 수집
            for (const chapterKey in summaryData) {
                const chapterData = summaryData[chapterKey];
                if (chapterData.regulations) {
                    // 디버깅: 해당 챕터의 모든 코드 수집
                    allCodes.push(...chapterData.regulations.map(r => r.code));

                    const found = chapterData.regulations.find(r => r.code === regulationCode);
                    if (found) {
                        regulation = found;
                        console.log(`[openAppendixPdf] Step 3: summary에서 regulation 찾음 - code="${found.code}", wzRuleSeq=${found.wzRuleSeq || found.wzruleseq}`);
                        break;
                    }
                }
            }

            if (regulation) {
                const ruleSeq = regulation.wzRuleSeq || regulation.wzruleseq;
                const currentDomain = window.location.origin;

                // 캐시 무효화를 위해 파일명에 타임스탬프 추가
                // 예: "a.pdf" → "a.pdf.1730983456"
                const timestamp = Date.now();
                const fileNameWithTimestamp = `${pdfFileName}.${timestamp}`;

                const downloadUrl = `/api/v1/appendix/download/${ruleSeq}/${encodeURIComponent(fileNameWithTimestamp)}`;
                pdfUrl = `${currentDomain}/static/viewer/web/viewer.html?file=${encodeURIComponent(downloadUrl)}`;
                console.log(`[openAppendixPdf] Step 4: API URL 생성 성공`);
                console.log(`[API] Using appendix download API: ${downloadUrl}`);
                console.log(`[Cache Busting] Added timestamp to filename: ${pdfFileName} → ${fileNameWithTimestamp}`);
            } else {
                console.warn(`[openAppendixPdf] Step 3 실패: summary에서 regulation 못 찾음`);
                console.warn(`[openAppendixPdf] 찾는 코드: "${regulationCode}" (타입: ${typeof regulationCode})`);
                console.warn(`[openAppendixPdf] Summary의 13.x 코드들: ${allCodes.filter(c => c && c.startsWith('13')).join(', ')}`);
                console.warn(`[openAppendixPdf] 코드 정확한 매칭 체크: ${allCodes.includes(regulationCode) ? '있음' : '없음'}`);
            }
        } else {
            console.error(`[openAppendixPdf] Step 2.5 실패: summary JSON 로드 실패 - status=${summaryResponse.status}`);
        }
    } else {
        console.warn(`[openAppendixPdf] Step 1 실패: API에서 파일명 못 찾음`);
    }

    // 2. 특정 부록에 대한 알림 처리 (우선순위 높음)
    if (appendixName === '감염관리지침') {
        showToast(`"감염관리지침" 은 [그룹웨어 기관별 게시판 > KB신용정보 > ICO(감염관리실) > 감염관리지침] 에서 확인 가능합니다.`, 'success');
        return;
    }

    if (appendixName === 'KB신용정보 물질안전보건자료(MSDS)') {
        showToast(`유해화학물질 관련 자료는 [그룹웨어 기관별게시판 > 사무처 > 안전보건팀> 6. 보건관리 > MSDS]에서 확인 가능합니다.`, 'success');
        return;
    }

    // 3. API 실패 시 하드코딩된 매핑 사용 (fallback)
    if (!pdfUrl) {
        console.log(`[openAppendixPdf] Step 5: API URL 없음, Fallback 시도`);
        console.log(`[openAppendixPdf] Fallback 검색: code="${regulationCode}", index=${appendixIndex}, name="${appendixName}"`);
        pdfUrl = getAppendixPdfUrl(regulationCode, appendixIndex, appendixName);
        if (pdfUrl) {
            console.log(`[Fallback] Using hardcoded mapping - URL: ${pdfUrl}`);
        } else {
            console.warn(`[Fallback] 하드코딩된 매핑에서도 URL 못 찾음`);
        }
    }

    if (!pdfUrl) {
        console.error(`[openAppendixPdf] 최종 실패: PDF URL 생성 불가 - "${appendixName}"`);
        showToast(`"${appendixName}" 부록 파일을 찾을 수 없습니다.`, 'error');
        return;
    }

    console.log(`[openAppendixPdf] Step 6: 최종 PDF URL - ${pdfUrl}`);

    // 부록 조회 로그 기록 (RegulationViewLogger 사용)
    if (window.RegulationViewLogger) {
        const ruleId = regulation ? (regulation.id || regulation.wzRuleSeq) : null;
        // appendixIndex는 0부터 시작하므로 +1 해서 표시
        const displayIndex = appendixIndex + 1;
        // 형식: "부록N. 부록명"
        const ruleName = `부록${displayIndex}. ${appendixName}`;
        // rule_pubno는 점(.) 없이 저장 (대시보드에서 "pubno. name" 형식으로 표시하므로)
        const rulePubno = regulationCode.replace(/\.+$/, '');

        RegulationViewLogger.logView(ruleId, ruleName, rulePubno)
            .catch(err => console.warn('부록 로그 기록 실패 (무시됨):', err));

        console.log(`✅ 부록 조회 로그: ${rulePubno} ${ruleName} (ID: ${ruleId})`);
    }

    // 최근 본 부록에 추가 (PDF 열기 성공 시에만)
    if (window.addToRecentAppendix) {
        window.addToRecentAppendix(regulationCode, appendixIndex, appendixName);
    }

    // URL에 부록 정보 및 타임스탬프 추가 (캐시 방지)
    const separator = pdfUrl.includes('?') ? '&' : '?';
    const timestamp = new Date().getTime();
    const enhancedUrl = `${pdfUrl}${separator}regCode=${encodeURIComponent(regulationCode)}&appendixIdx=${appendixIndex}&appendixName=${encodeURIComponent(appendixName)}&ts=${timestamp}`;

    // 모바일/PC 검사 및 적절한 방식으로 PDF 열기
    const isMobileUA = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    const isSmallScreen = window.innerWidth <= 768;

    if (isMobileUA || isSmallScreen) {
        // 모바일 또는 작은 화면: iframe 모달
        showPdfModal(enhancedUrl);
    } else {
        // PC: 새 창
        const newWindow = window.open(enhancedUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');

        if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
            // 팝업 차단 시: iframe 모달로 대체
            showPdfModal(enhancedUrl);
        }
    }

    console.log(`부록 PDF 열기: ${appendixName} -> ${pdfUrl}`);
}



// ========== 부록 툴팁 관련 함수 ==========

// 부록 툴팁 HTML 생성
function generateAppendixTooltip(regulation) {
    if (!regulation.appendix || regulation.appendix.length === 0) {
        return '';
    }
    
    // 안전한 부록 배열 생성
    let safeAppendixArray = [];
    if (Array.isArray(regulation.appendix)) {
        safeAppendixArray = regulation.appendix;
    } else if (typeof regulation.appendix === 'string') {
        safeAppendixArray = [regulation.appendix];
    } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
        try {
            safeAppendixArray = Object.values(regulation.appendix).filter(item => item != null);
        } catch (error) {
            console.error('부록 변환 실패:', error);
            safeAppendixArray = [];
        }
    }
    
    if (safeAppendixArray.length === 0) {
        return '';
    }
    
    // 툴팁 아이템들 생성
    const tooltipItems = safeAppendixArray.map((appendixItem, index) => {
        const escapedItem = appendixItem.replace(/'/g, "\\'").replace(/"/g, "&quot;");
        // 텍스트에서 중복된 번호가 제거를　위해　cleanAppendixItem　사용
        const cleanAppendixItem = appendixItem.replace(/^\d+\.\s*/, '');
        return `
            <a href="#" class="appendix-tooltip-item" 
               onclick="event.preventDefault(); event.stopPropagation(); openAppendixPdf('${regulation.code}', ${index}, '${cleanAppendixItem}'); hideAppendixTooltip(event);">
                부록 ${index + 1}. ${cleanAppendixItem}
            </a>
        `;
    }).join('');
    
    return `
        <div class="appendix-tooltip">
            ${tooltipItems}
        </div>
    `;
}

// 부록 개수 클릭 핸들러 (모바일용)
function toggleAppendixTooltip(event, regulation) {
    event.stopPropagation();
    
    const isMobile = window.innerWidth <= 768;
    if (!isMobile) return; // 데스크톱에서는 호버로 동작
    
    const tooltip = event.currentTarget.querySelector('.appendix-tooltip');
    if (!tooltip) return;
    
    // 다른 열린 툴팁들 닫기
    document.querySelectorAll('.appendix-tooltip.mobile-show').forEach(t => {
        if (t !== tooltip) {
            t.classList.remove('mobile-show');
        }
    });
    
    // 현재 툴팁 토글
    tooltip.classList.toggle('mobile-show');
    
    // 배경 클릭으로 닫기
    if (tooltip.classList.contains('mobile-show')) {
        setTimeout(() => {
            document.addEventListener('click', function closeTooltip(e) {
                if (!tooltip.contains(e.target) && !event.currentTarget.contains(e.target)) {
                    tooltip.classList.remove('mobile-show');
                    document.removeEventListener('click', closeTooltip);
                }
            });
        }, 100);
    }
}

// 툴팁 숨기기
function hideAppendixTooltip(event) {
    const tooltip = event.target.closest('.appendix-tooltip');
    if (tooltip) {
        tooltip.classList.remove('mobile-show');
    }
}


// ========== 내규 PDF 매핑 테이블 ==========
const REGULATION_PDF_MAPPING = {
    // 매핑 키 형식: "장.절.항"
    '1.1.1': '1.1.1._정확한_환자_확인_202503개정.pdf',
    '1.2.1': '1.2.1._구두,전화처방_202503개정.pdf', 
    '1.2.2': '1.2.2._PRN_처방_20250704개정.pdf',
    '1.2.3': '1.2.3._정확한_의사소통_-_혼동하기_쉬운_부정확한_처방_202503개정.pdf',
    '1.2.4': '1.2.4._정확한_의사소통_-_이상검사결과_보고_202503개정.pdf',
    '1.3.1': '1.3.1._수술의_정확한_수행_202503개정.pdf',
    '1.3.2': '1.3.2._시술의_정확한_수행_202503개정.pdf',
    '1.4.1': '1.4.1._낙상_예방_202503개정.pdf',
    '1.5.1': '1.5.1._손위생_202503개정.pdf',

    // 2장
    '2.1.1.1': '2.1.1.1._KB신용정보_이용_-_외래_202503개정.pdf',
    '2.1.1.2': '2.1.1.2._KB신용정보_이용_-_응급진료센터_202503개정.pdf',
    '2.1.2.1': '2.1.2.1._KB신용정보_이용_-_입원_202503개정.pdf',
    '2.1.2.2': '2.1.2.2._정신건강의학과_·_소아정신과_입원환자_관리_202503개정.pdf',
    '2.1.2.3': '2.1.2.3._외출,_외박_202503개정.pdf',
    '2.1.2.4': '2.1.2.4._무연고_환자_관리_202503개정.pdf',
    '2.1.3.1': '2.1.3.1._입퇴실_절차_-_중환자실_202503개정.pdf',
    '2.1.3.2': '2.1.3.2._입퇴실_절차_-_신생아집중치료실_202503개정.pdf',
    '2.1.3.3': '2.1.3.3._입퇴실_절차_-_뇌졸중집중치료실_202503개정.pdf',
    '2.1.3.4': '2.1.3.4._입퇴실_절차_-_분만실_202503개정.pdf',
    '2.1.3.5': '2.1.3.5._입퇴실_절차_-_고위험임산부태아집중치료실_202503개정.pdf',
    '2.1.3.6': '2.1.3.6._입퇴실_절차_-_임상시험센터_입원실_202503개정.pdf',
    '2.1.3.7': '2.1.3.7._입퇴실_절차_-_장기이식병동_202503개정.pdf',
    '2.1.3.8': '2.1.3.8._입퇴실_절차_-_조혈모세포이식병동_202503개정.pdf',
    '2.1.3.9': '2.1.3.9._입퇴실_절차_-_정신건강의학과_보호병동_202503개정.pdf',
    '2.1.3.10': '2.1.3.10._입퇴실_절차_-_방사성동위원소_치료병실_202503개정.pdf',
    '2.1.4.1': '2.1.4.1._환자정보_공유_및_인수인계(전과,_전동,_근무교대)_202503개정.pdf',
    '2.1.4.2': '2.1.4.2._환자_원내_이송_20250704개정.pdf',
    '2.1.4.3': '2.1.4.3._신속대응체계_202503개정.pdf',
    '2.1.5.1': '2.1.5.1._퇴원_202503개정.pdf',
    '2.1.5.2': '2.1.5.2_회송(전원)_202503개정.pdf',
    '2.1.5.3': '2.1.5.3._진료_·_치료_거부_및_무단이탈_환자_관리_202503개정.pdf',
    '2.1.6.1': '2.1.6.1._외국인_진료_202503개정.pdf',
    '2.2.1.1': '2.2.1.1._외래환자_평가_202503개정.pdf',
    '2.2.2.1': '2.2.2.1._입원환자_평가_202503개정.pdf',
    '2.2.3.1': '2.2.3.1._응급진료센터환자_평가_202503개정.pdf',
    '2.3.1.1': '2.3.1.1._검체검사_검사과정_관리_-_진단검사의학과_20250905수정.pdf',
    '2.3.1.2': '2.3.1.2._검체검사_검사과정_관리_-_병리과_202503개정.pdf',
    '2.3.2.1': '2.3.2.1._검체검사_결과_보고_-_진단검사의학과_202503개정.pdf',
    '2.3.2.2': '2.3.2.2._검체검사_결과_보고_-_병리과_202503개정.pdf',
    '2.3.3.1': '2.3.3.1._검체검사실_안전관리_202503개정.pdf',
    '2.3.4.1': '2.3.4.1._혈액제제_관리_202503개정.pdf',
    '2.3.5.1': '2.3.5.1._영상검사_검사과정_관리_202503개정.pdf',
    '2.3.6.1': '2.3.6.1._영상검사_결과_보고_-_영상의학과_202503개정.pdf',
    '2.3.6.2': '2.3.6.2._영상검사_결과_보고_-_핵의학과_202503개정.pdf',
    '2.3.7.1': '2.3.7.1._방사선안전관리_202503개정.pdf',

    // 3장
    '3.1.1.1': '3.1.1.1._입원환자_치료계획_202503개정.pdf',
    '3.1.2.1': '3.1.2.1._협의진료체계_202503개정.pdf',
    '3.1.3.1': '3.1.3.1._통증관리_202505수정.pdf',
    '3.1.4.1': '3.1.4.1._영양_관리_202503개정.pdf',
    '3.1.5.1': '3.1.5.1._영양집중지원서비스_202503개정.pdf',
    '3.1.6.1': '3.1.6.1._욕창관리_202503개정.pdf',
    '3.1.7.1': '3.1.7.1._호스피스·완화의료_환자_진료_202503개정.pdf',
    '3.1.7.2': '3.1.7.2._연명의료결정_환자_진료_20250704개정.pdf',
    '3.1.8.1': '3.1.8.1._투석환자_관리_202503개정.pdf',
    '3.1.9.1': '3.1.9.1._의료기기_알람_시스템_관리_202503개정.pdf',
    '3.2.1.1': '3.2.1.1._응급진료센터_진료절차_202503개정.pdf',
    '3.2.1.2': '3.2.1.2._중증응급환자_진료_202503개정.pdf',
    '3.2.1.3': '3.2.1.3._중증응급환자_이송서비스_관리_202503개정.pdf',
    '3.2.1.4': '3.2.1.4._혼수상태_환자_관리_20250704개정.pdf',
    '3.2.1.5': '3.2.1.5._인공호흡기_적용_환자_관리_202503개정.pdf',
    '3.2.2.1': '3.2.2.1._심폐소생술_202503개정.pdf',
    '3.2.2.2': '3.2.2.2._Emergency_Cart_관리_20250905수정.pdf',
    '3.2.3.1': '3.2.3.1._수혈환자_관리_202503개정.pdf',
    '3.2.4.1': '3.2.4.1._항암화학요법_20250905수정.pdf',
    '3.2.5.1': '3.2.5.1._신체보호대_적용_환자_관리_202503개정.pdf',
    '3.2.5.2': '3.2.5.2._정신건강의학과_격리_및_강박_202503개정.pdf',
    '3.2.6.1': '3.2.6.1._자살_또는_자해_위험_환자_관리_202503개정.pdf',
    '3.2.7.1': '3.2.7.1._소아환자_진료_202503개정.pdf',
    '3.2.8.1': '3.2.8.1._노인환자_진료_202503개정.pdf',
    
    // 4장
    '4.1.1': '4.1.1._의약품관리체계_202503개정.pdf',
    '4.2.1': '4.2.1._의약품_선정_및_공급_20250704개정.pdf',
    '4.3.1': '4.3.1._의약품_보관_202503개정.pdf',
    '4.3.2': '4.3.2._Emergency_Cart_내_응급의약품_보관_및_관리_202503개정.pdf',
    '4.3.3': '4.3.3._비품약_관리_202503개정.pdf',
    '4.3.4': '4.3.4._마약류_관리_202503개정.pdf',
    '4.3.5': '4.3.5._고위험의약품_안전사용_202503개정.pdf',
    '4.3.6': '4.3.6._주의를_요하는_의약품_안전사용_20250905수정.pdf',
    '4.3.7': '4.3.7._임상시험용_의약품관리_202503개정.pdf',
    '4.3.8': '4.3.8._방사성의약품_관리_202503개정.pdf',
    '4.3.9': '4.3.9._의약품_회수_202503개정.pdf',
    '4.4.1': '4.4.1._의약품_처방_202503개정.pdf',
    '4.4.2': '4.4.2._의약품_조제_20250905수정.pdf',
    '4.5.1': '4.5.1._의약품_투여_202503개정.pdf',
    '4.5.2': '4.5.2._지참약_관리_202503개정.pdf',
    '4.6.1': '4.6.1._의약품부작용_모니터링_및_약물_알레르기_관리_202503개정.pdf',
    '4.6.2': '4.6.2._의약품사용_오류_관리_202503개정.pdf',

    // 5장
    '5.2.1': '5.2.1._수술_시_환자안전보장_202503개정.pdf',
    '5.3.1': '5.3.1._시술관리_202503개정.pdf',
    '5.4.1': '5.4.1._성인_진정관리_202503개정.pdf',
    '5.4.2': '5.4.2._소아청소년_진정관리_202503개정.pdf',
    '5.5.1': '5.5.1._마취_진료_202503개정.pdf',
    '5.7.1': '5.7.1._수술실_안전관리_202503개정.pdf',
    
    // 6장
    '6.1.1': '6.1.1._환자의_권리와_의무_202503개정.pdf',
    '6.1.2': '6.1.2._일관된_진료_202503개정.pdf',
    '6.1.3': '6.1.3._환자와_가족_교육_202503개정.pdf',
    '6.2.1': '6.2.1._취약환자_서비스_202503개정.pdf',
    '6.3.1': '6.3.1._환자경험관리_202503개정.pdf',
    '6.4.1': '6.4.1._의료사회복지체계_202503개정.pdf',
    '6.5.1': '6.5.1._동의서_202503개정.pdf',
    '6.6.1': '6.6.1._임상연구_프로그램_202503개정.pdf',
    '6.7.1': '6.7.1._장기기증_202503개정.pdf',
    '6.7.2': '6.7.2._장기이식_202503개정.pdf',
    '6.7.3': '6.7.3._조직은행_202503개정.pdf',
    
    // 7장
    '7.1.1': '7.1.1._의료질향상_및_환자안전_운영_체계_202503개정.pdf',
    '7.2.1': '7.2.1._위험관리체계_202503개정.pdf',
    '7.3.1': '7.3.1._환자안전사건_관리_202503개정.pdf',
    '7.4.1': '7.4.1._질_향상_활동_202503제정.pdf',
    '7.5.1': '7.5.1._표준진료지침_202503개정.pdf',
    '7.6.1': '7.6.1._질지표_관리_202503개정.pdf',
    '7.6.2': '7.6.2._데이터_검증_202503개정.pdf',
    '7.7.1': '7.7.1._안전문화_프로그램_202503개정.pdf',
    
    // 8장
    '8.1.1': '8.1.1._감염관리_프로그램_202503개정.pdf',
    '8.1.2': '8.1.2._항생제_관리체계(제한_항생제,_수술_시_예방적_항생제_사용)_202503개정.pdf',
    '8.4.1': '8.4.1._의료기구_감염관리_202503개정.pdf',
    '8.5.1': '8.5.1._세척,_소독,_멸균_202503개정.pdf',
    '8.5.2': '8.5.2._세탁물_관리_202503개정.pdf',
    '8.5.3': '8.5.3._일회용_물품의_재사용_202503개정.pdf',
    '8.6.1': '8.6.1._환자치료영역_환경관리_202503개정.pdf',
    '8.7.1': '8.7.1._급식서비스_관리_202503개정.pdf',
    '8.8.1': '8.8.1._감염성질환_관리_202503개정.pdf',
    '8.8.2': '8.8.2._면역저하_환자_관리_20250704개정.pdf',
    '8.8.3': '8.8.3._개인보호구_사용_202503개정.pdf',

    // 9장 
    '9.1.1': '9.1.1._KB신용정보_운영_규정_202503개정.pdf',
    '9.1.2': '9.1.2._KB신용정보_의사소통_체계_202503개정.pdf',
    '9.1.3': '9.1.3._위탁서비스_관리_202503개정.pdf',
    '9.1.4': '9.1.4._자원의_구매와_공급망_관리_202503개정.pdf',
    '9.1.5': '9.1.5._KB신용정보_내규_관리_202503개정.pdf',
    '9.2.1': '9.2.1._KB신용정보_사명과_비전_202503개정.pdf',
    '9.3.1': '9.3.1._부서_조직_및_운영_202503개정.pdf',
    '9.4.1': '9.4.1._윤리적_관리_체계_202503개정.pdf',
    
    // 10장 
    '10.1.1': '10.1.1._인사관리_체계_202503개정.pdf',
    '10.2.1': '10.2.1_전문의_임상권한_및_자격관리_202503개정.pdf',
    '10.2.2': '10.2.2._진료평가_202503개정.pdf',
    '10.2.3': '10.2.3._신의료기술_도입_시_임상권한_승인_202503개정.pdf',
    '10.3.1': '10.3.1._직무관리_및_평가_202503개정.pdf',
    '10.4.1': '10.4.1._인사정보관리_202503개정.pdf',
    '10.4.2': '10.4.2._기타_인력_신고_및_관리_202503개정.pdf',
    '10.4.3': '10.4.3._자원봉사자_관리_202503개정.pdf',
    '10.5.1': '10.5.1._직원교육_202505수정.pdf',
    '10.5.2': '10.5.2._수탁교육_관리_202503개정.pdf',
    '10.5.3': '10.5.3._수탁교육_관리_-_의료원_외국인_연수생_202503개정.pdf',
    '10.7.1': '10.7.1._직원_안전보건_관리_202503개정.pdf',
    '10.7.2': '10.7.2._직무상_재해_관리_202503개정.pdf',
    '10.8.1': '10.8.1._직무상_폭력_예방_및_관리_202503개정.pdf',
    
    // 11장 
    '11.1.1': '11.1.1._시설안전관리_202503개정.pdf',
    '11.2.1': '11.2.1._유틸리티시스템관리_202503개정.pdf',
    '11.3.1': '11.3.1._유해화학물질_관리_202503개정.pdf',
    '11.3.2': '11.3.2._의료폐기물_관리_202503개정.pdf',
    '11.4.1': '11.4.1._안전_및_보안관리_20250704개정.pdf',
    '11.5.1': '11.5.1._의료기기_관리_20250909개정.pdf',
    '11.5.2': '11.5.2._임의_의료기기_승인_202503개정.pdf',
    '11.5.3': '11.5.3._인체삽입_의료기기_202503개정.pdf',
    '11.5.4': '11.5.4._레이저_및_기타_광학_방사선_기기_안전_관리_프로그램_202503개정.pdf',
    '11.5.5': '11.5.5._물품의_유효기간_관리_202503개정.pdf',
    '11.6.1': '11.6.1._화재안전관리_202503개정.pdf',
    '11.6.2': '11.6.2._금연관리_202503개정.pdf',
    '11.7.1': '11.7.1._재난관리체계_202503개정.pdf',
    '11.8.1': '11.8.1._유행성감염병_대량발생_시_관리_202503개정.pdf',
    
    // 12장 
    '12.1.1': '12.1.1._의무기록,의료정보_관리_202503개정.pdf',
    '12.1.2': '12.1.2._환자정보_및_의무기록_정정_202503개정.pdf',
    '12.1.3': '12.1.3._의무기록,의료정보_접근권한_202503개정.pdf',
    '12.1.4': '12.1.4._의무기록_사본발급_및_열람_202503개정.pdf',
    '12.1.5': '12.1.5._약어_사용_202503개정.pdf',
    '12.1.6': '12.1.6._의무기록_관련_표준_코드_202503개정.pdf',
    '12.1.7': '12.1.7._진단명_및_진단코드_관리_202503개정.pdf',
    '12.1.8': '12.1.8._전자의무기록의_복사기능_사용_202503개정.pdf',
    '12.2.1': '12.2.1._의무기록_완결도_관리_202503개정.pdf',
    '12.3.1': '12.3.1._의료정보수집_및_정보공유_활용_202503개정.pdf',
    '12.3.2': '12.3.2._정보관리_202503개정.pdf',
    '12.4.1': '12.4.1._개인정보_보호_및_보안_202503개정.pdf',
    
    // 13장 
    '13.1.1': '13.1.1._의과대학생_임상실습_교육_및_감독_202503개정.pdf',
    '13.2.1': '13.2.1._수련의_교육_및_감독_202503개정.pdf',

};

// 내규 PDF 파일명 가져오기 함수
function getRegulationPdfFileName(regulationCode) {
    // 1순위: summary JSON에서 현행내규PDF 필드 확인 (가장 정확함)
    if (hospitalRegulations) {
        for (const chapter in hospitalRegulations) {
            const regulations = hospitalRegulations[chapter].regulations || [];
            for (const reg of regulations) {
                if (reg.code === regulationCode) {
                    // JSON 파일에 명시된 현행내규PDF가 있으면 바로 사용
                    const pdfFromJson = reg.detail?.documentInfo?.현행내규PDF;
                    if (pdfFromJson) {
                        console.log(`[JSON] 현행내규PDF 사용: ${pdfFromJson}`);
                        return pdfFromJson;
                    }

                    // 폴백 1: wzFilePdf (DB 기반, 레거시)
                    if (reg.wzFilePdf) {
                        console.log(`[DB] wzFilePdf 사용: ${reg.wzFilePdf}`);
                        return reg.wzFilePdf;
                    }

                    // 폴백 2: 날짜 기반 파일명 생성
                    const revisionDate = reg.detail?.documentInfo?.최종개정일;
                    const regulationName = reg.name || reg.detail?.documentInfo?.규정명;

                    if (revisionDate && regulationName) {
                        const safeName = regulationName.replace(regulationCode, '').replace(/^\./, '').trim();
                        const safeNameForFile = safeName.replace(/[^가-힣a-zA-Z0-9\s-]/g, '_').replace(/\s+/g, '_');
                        const dateStr = revisionDate.replace(/[.\-]/g, '').slice(0, 6);
                        const pdfFileName = `${regulationCode}._${safeNameForFile}_${dateStr}개정.pdf`;

                        console.log(`[Auto] PDF 파일명 생성: ${pdfFileName}`);
                        return pdfFileName;
                    }
                }
            }
        }
    }

    // 폴백 3: 하드코딩된 매핑에서 찾기 (레거시 최종 폴백)
    if (REGULATION_PDF_MAPPING[regulationCode]) {
        console.log(`[Legacy] PDF 매핑 사용: ${REGULATION_PDF_MAPPING[regulationCode]}`);
        return REGULATION_PDF_MAPPING[regulationCode];
    }

    console.warn(`PDF 매핑을 찾을 수 없습니다: ${regulationCode}`);
    return null;
}

// 내규 PDF URL 생성
function getRegulationPdfUrl(regulationCode) {
    const pdfFileName = getRegulationPdfFileName(regulationCode);
    
    if (!pdfFileName) {
        return null;
    }
    
    const currentDomain = window.location.origin;
    return `${currentDomain}/static/viewer/web/viewer.html?file=/static/pdf/print/${encodeURIComponent(pdfFileName)}`;
}

// ==============인쇄==============
// 도메인에서 인쇄 기능 사용 가능 여부 체크 (도메인 제한 해제됨)
function isPrintAllowed() {
    return true;
}

// PDF 파일 인쇄 방법 (static/pdf/print 폴더의 PDF 사용)
async function printRegulation() {
    if (!currentRegulation || !currentChapter) {
        showToast('인쇄할 내규가 선택되지 않았습니다.', 'error');
        return;
    }

    // 내규 코드로 print PDF 파일 검색
    const regCode = currentRegulation.code;
    console.log('[Print] 내규 코드:', regCode);

    try {
        // API 호출하여 PDF 파일명 찾기
        const response = await fetch(`/api/v1/pdf/print-file/${regCode}`);
        const result = await response.json();

        if (!result.success) {
            showToast(result.error || '해당 내규의 PDF 파일을 찾을 수 없습니다.', 'error');
            console.warn('[Print] PDF 파일을 찾을 수 없습니다:', regCode, result.error);
            return;
        }

        // PDF 뷰어 URL 생성
        const pdfViewerUrl = `/static/viewer/web/viewer.html?file=${encodeURIComponent(result.path)}`;
        console.log('[Print] PDF 인쇄 URL:', pdfViewerUrl);

        // 새창으로 PDF 열기
        const printWindow = window.open(pdfViewerUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');

        if (!printWindow) {
            alert('팝업이 차단되었습니다. 브라우저 설정에서 팝업을 허용해주세요.');
            return;
        }
    } catch (error) {
        console.error('[Print] API 호출 오류:', error);
        showToast('PDF 파일을 찾는 중 오류가 발생했습니다.', 'error');
    }
}


