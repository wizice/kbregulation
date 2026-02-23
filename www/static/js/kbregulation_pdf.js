/**
 * KB신용정보 내규 시스템 - PDF 모듈
 * @module kbregulation_pdf
 */

import { AppState, showToast } from './kbregulation_common.js';
import { closeSidebar } from './kbregulation_sidebar.js';
import { updateRecentRegulations } from './kbregulation_detail.js';

// ============================================
// 부록 PDF 매핑 테이블
// ============================================

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

    '8.1.1|1|감염관리지침': '',
    '8.1.2|1|KB신용정보 수술 시 예방적 항생제 사용 지침': '8.1.2._부록1._KB신용정보_수술_시_예방적_항생제_사용_지침_202503개정.pdf',
    '8.1.2|2|KB신용정보 항생제 피부시험 지침': '8.1.2._부록2._KB신용정보_항생제_피부시험_지침_202505개정(★전산개발_후_재업로드_필요).pdf',
    '8.4.1|1|감염관리지침': '',
    '8.5.1|1|감염관리지침': '',
    '8.5.2|1|감염관리지침': '',
    '8.5.3|1|Cutting Burr 재사용 시 세척방법': '8.5.3._부록1._Cutting_burr_재사용_시_세척방법_202503검토.pdf',
    '8.5.3|2|일회용 물품 재사용 허가 신청서': '8.5.3._부록2._일회용_물품_재사용_허가_신청서_202503검토.pdf',
    '8.6.1|1|감염관리지침': '',
    '8.7.1|1|감염관리지침': '',
    '8.8.1|1|감염관리지침': '',
    '8.8.3|1|감염관리지침': '',

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
    '11.3.1|1|KB신용정보 물질안전보건자료(MSDS)': '',
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
    '11.8.1|2|감염관리지침': '',

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

// ============================================
// PDF 모달
// ============================================

/**
 * PDF 모달 표시
 */
export function showPdfModal(url) {
    let modal = document.getElementById('pdfModal');

    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'pdfModal';
        modal.className = 'pdf-modal';
        modal.innerHTML = `
            <div class="pdf-modal-content">
                <div class="pdf-modal-header">
                    <span class="pdf-modal-title">PDF 뷰어</span>
                    <button class="pdf-modal-close" onclick="closePdfModal()">&times;</button>
                </div>
                <div class="pdf-modal-body">
                    <iframe id="pdfViewer" src="" frameborder="0"></iframe>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    const iframe = document.getElementById('pdfViewer');
    if (iframe) {
        iframe.src = url;
    }

    modal.classList.add('active');
}

/**
 * PDF 모달 닫기
 */
export function closePdfModal() {
    const modal = document.getElementById('pdfModal');
    if (modal) {
        modal.classList.remove('active');
        const iframe = document.getElementById('pdfViewer');
        if (iframe) {
            iframe.src = '';
        }
    }
}

// ============================================
// 부록 PDF 관련 함수
// ============================================

/**
 * PDF 파일명 가져오기 (동기 버전 - fallback용)
 */
function getAppendixPdfFileName(regulationCode, appendixIndex, appendixName) {
    console.log(`[Mapping] 검색 시작: code="${regulationCode}", index=${appendixIndex}, name="${appendixName}"`);

    // 1. 먼저 부록 이름으로 직접 찾기 (부록 번호 무시)
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

    console.warn(`[Mapping] ✗ PDF 매핑을 찾을 수 없습니다: ${mappingKey}`);
    return null;
}

/**
 * 파일 시스템에서 부록 파일 정보 가져오기 (비동기)
 */
async function getAppendixFileFromAPI(regulationCode, appendixIndex) {
    try {
        console.log(`[API] Fetching appendix for ${regulationCode}, index: ${appendixIndex}`);

        const timestamp = new Date().getTime();
        const summaryResponse = await fetch(`/static/file/summary_kbregulation.json?ts=${timestamp}`);
        if (!summaryResponse.ok) {
            console.warn('[API] Summary JSON 로드 실패');
            return null;
        }

        const summaryData = await summaryResponse.json();

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

        const appendixResponse = await fetch(`/api/v1/appendix/list/${ruleSeq}`);
        if (!appendixResponse.ok) {
            console.warn(`[API] 부록 목록 조회 실패: ${ruleSeq}`);
            return null;
        }

        const appendixList = await appendixResponse.json();
        const appendixFile = appendixList[appendixIndex];

        if (!appendixFile) {
            console.warn(`[API] 부록 파일을 찾을 수 없습니다: index ${appendixIndex}`);
            return null;
        }

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

/**
 * PDF 뷰어 URL 생성 (동기 버전 - fallback용)
 */
function getAppendixPdfUrl(regulationCode, appendixIndex, appendixName) {
    const pdfFileName = getAppendixPdfFileName(regulationCode, appendixIndex, appendixName);

    if (!pdfFileName) {
        return null;
    }

    const currentDomain = window.location.origin;
    return `${currentDomain}/static/viewer/web/viewer.html?file=/static/pdf/${encodeURIComponent(pdfFileName)}`;
}

/**
 * 부록 PDF 열기 함수 (비동기)
 */
export async function openAppendixPdf(regulationCode, appendixIndex, appendixName) {
    let regulation = null;

    // PDF 뷰어 열 때는 항상 사이드바 닫기
    if (typeof closeSidebar === 'function') {
        closeSidebar();
    }

    // 부록을 최근 본 내규에 추가
    if (regulationCode && typeof appendixIndex === 'number' && appendixName) {
        let parentRegulation = null;
        let parentChapter = null;

        Object.keys(AppState.hospitalRegulations).forEach(chapter => {
            const chapterData = AppState.hospitalRegulations[chapter];
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
            if (typeof updateRecentRegulations === 'function') {
                updateRecentRegulations(appendixItem, parentChapter, 'appendix');
            }
        }
    }

    // 1. API에서 동적으로 파일 찾기 시도
    console.log(`[openAppendixPdf] Step 1: API 파일 찾기 - code="${regulationCode}", index=${appendixIndex}, name="${appendixName}"`);
    let pdfFileName = await getAppendixFileFromAPI(regulationCode, appendixIndex);
    let pdfUrl = null;

    if (pdfFileName) {
        console.log(`[openAppendixPdf] Step 2: 파일명 찾음 - "${pdfFileName}"`);

        const timestamp = new Date().getTime();
        const summaryResponse = await fetch(`/static/file/summary_kbregulation.json?ts=${timestamp}`);
        if (summaryResponse.ok) {
            const summaryData = await summaryResponse.json();
            regulation = null;
            let allCodes = [];
            for (const chapterKey in summaryData) {
                const chapterData = summaryData[chapterKey];
                if (chapterData.regulations) {
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

                const timestamp = Date.now();
                const fileNameWithTimestamp = `${pdfFileName}.${timestamp}`;

                const downloadUrl = `/api/v1/appendix/download/${ruleSeq}/${encodeURIComponent(fileNameWithTimestamp)}`;
                pdfUrl = `${currentDomain}/static/viewer/web/viewer.html?file=${encodeURIComponent(downloadUrl)}`;
                console.log(`[openAppendixPdf] Step 4: API URL 생성 성공`);
                console.log(`[API] Using appendix download API: ${downloadUrl}`);
            } else {
                console.warn(`[openAppendixPdf] Step 3 실패: summary에서 regulation 못 찾음`);
            }
        }
    } else {
        console.warn(`[openAppendixPdf] Step 1 실패: API에서 파일명 못 찾음`);
    }

    // 2. 특정 부록에 대한 알림 처리
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

    // 부록 조회 로그 기록
    if (window.RegulationViewLogger) {
        const ruleId = regulation ? (regulation.id || regulation.wzRuleSeq) : null;
        const displayIndex = appendixIndex + 1;
        const ruleName = `부록${displayIndex}. ${appendixName}`;
        const rulePubno = regulationCode.replace(/\.+$/, '');

        RegulationViewLogger.logView(ruleId, ruleName, rulePubno)
            .catch(err => console.warn('부록 로그 기록 실패 (무시됨):', err));

        console.log(`✅ 부록 조회 로그: ${rulePubno} ${ruleName} (ID: ${ruleId})`);
    }

    // 최근 본 부록에 추가
    if (window.addToRecentAppendix) {
        window.addToRecentAppendix(regulationCode, appendixIndex, appendixName);
    }

    // URL에 부록 정보 및 타임스탬프 추가
    const separator = pdfUrl.includes('?') ? '&' : '?';
    const timestamp = new Date().getTime();
    const enhancedUrl = `${pdfUrl}${separator}regCode=${encodeURIComponent(regulationCode)}&appendixIdx=${appendixIndex}&appendixName=${encodeURIComponent(appendixName)}&ts=${timestamp}`;

    // 모바일/PC 검사 및 적절한 방식으로 PDF 열기
    const isMobileUA = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    const isSmallScreen = window.innerWidth <= 768;

    if (isMobileUA || isSmallScreen) {
        showPdfModal(enhancedUrl);
    } else {
        const newWindow = window.open(enhancedUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
        if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
            showPdfModal(enhancedUrl);
        }
    }

    console.log(`부록 PDF 열기: ${appendixName} -> ${pdfUrl}`);
}

// ============================================
// 현행 내규 PDF / 신구대비표
// ============================================

/**
 * 현재 규정 PDF 열기
 */
export async function openCurrentRegulationPdf(regulationCode, regulationName) {
    console.log('현행내규 PDF 열기:', regulationCode, regulationName);

    const apiCode = regulationCode.replace(/\./g, '_');
    console.log('[Print] API 호출 코드:', apiCode);

    try {
        const apiResponse = await fetch(`/api/v1/pdf/print-file/${apiCode}`);
        const result = await apiResponse.json();

        if (!result.success) {
            showToast(result.error || `"${regulationName}" 현행내규 PDF 파일을 찾을 수 없습니다.`, 'error');
            console.warn('[Print] PDF 파일을 찾을 수 없습니다:', regulationCode, result.error);
            return;
        }

        const currentDomain = window.location.origin;
        const pdfUrl = `${currentDomain}/static/viewer/web/viewer.html?file=${encodeURIComponent(result.path)}`;
        console.log('[Print] PDF URL:', pdfUrl);

        const isMobileUA = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        const isSmallScreen = window.innerWidth <= 768;

        if (isMobileUA || isSmallScreen) {
            showPdfModal(pdfUrl);
        } else {
            const newWindow = window.open(pdfUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
            if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
                showPdfModal(pdfUrl);
            }
        }
    } catch (error) {
        console.error('PDF 열기 실패:', error);
        showToast('PDF를 불러오는데 실패했습니다.', 'error');
    }
}

/**
 * 신구대비표 PDF 열기
 */
export async function openComparisonTablePdf(regulationCode, regulationName, wzRuleSeq) {
    console.log('비교표 PDF 열기:', regulationCode, 'wzRuleSeq:', wzRuleSeq);

    const timestamp = new Date().getTime();
    let pdfPath;

    try {
        if (wzRuleSeq && AppState.hospitalRegulations) {
            for (const chapter in AppState.hospitalRegulations) {
                const regulations = AppState.hospitalRegulations[chapter].regulations || [];
                for (const reg of regulations) {
                    if (reg.wzRuleSeq === wzRuleSeq) {
                        const comparisonPdfFromJson = reg.detail?.documentInfo?.신구대비표PDF;
                        if (comparisonPdfFromJson) {
                            pdfPath = `/static/pdf/comparisonTable/${comparisonPdfFromJson}`;
                            console.log('[JSON] 신구대비표PDF 사용:', pdfPath);
                            const pdfPathWithTimestamp = `/static/viewer/web/viewer.html?file=${pdfPath}?ts=${timestamp}`;
                            openPdfViewer(pdfPathWithTimestamp);
                            return;
                        }

                        const jsonFileName = reg.detail?.documentInfo?.파일명;
                        const revisionDate = reg.detail?.documentInfo?.최종개정일;

                        if (jsonFileName && revisionDate) {
                            const wzRuleId = jsonFileName.replace('.json', '');
                            const dateStr = revisionDate.replace(/[.\-]/g, '').slice(0, 8);
                            const newStylePath = `/static/pdf/comparisonTable/${wzRuleId}_${wzRuleSeq}_${dateStr}.pdf`;

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
                        break;
                    }
                }
            }
        }

        pdfPath = `/static/pdf/comparisonTable/comparisonTable_${regulationCode}.pdf`;
        const response = await fetch(pdfPath, { method: 'HEAD' });

        if (!response.ok) {
            showToast('신구대비표가 존재하지 않습니다.', 'error');
            return;
        }

        const pdfPathWithTimestamp = `/static/viewer/web/viewer.html?file=${pdfPath}?ts=${timestamp}`;
        openPdfViewer(pdfPathWithTimestamp);

    } catch (error) {
        console.error('신구대비표 열기 실패:', error);
        showToast('신구대비표를 불러오는데 실패했습니다.', 'error');
    }
}

/**
 * PDF 뷰어 열기
 */
export function openPdfViewer(pdfPathWithTimestamp) {
    const viewerUrl = `/static/viewer/web/viewer.html?file=${encodeURIComponent(pdfPathWithTimestamp)}`;
    window.open(viewerUrl, '_blank', 'width=900,height=700,scrollbars=yes,resizable=yes');
}

/**
 * 규정 인쇄
 */
export function printRegulation() {
    const contentBody = document.getElementById('contentBody');
    if (!contentBody) {
        showToast('인쇄할 내용이 없습니다.', 'error');
        return;
    }

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
        showToast('팝업이 차단되었습니다. 팝업을 허용해주세요.', 'error');
        return;
    }

    const printContent = contentBody.innerHTML;
    const title = document.getElementById('pageTitle')?.textContent || 'KB신용정보 내규';

    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>${title}</title>
            <link rel="stylesheet" href="/static/css/kbregulation.css">
            <style>
                body { padding: 20px; }
                .watermark-overlay { display: none !important; }
                @media print {
                    body { padding: 0; }
                }
            </style>
        </head>
        <body>
            <h1>${title}</h1>
            ${printContent}
        </body>
        </html>
    `);

    printWindow.document.close();

    setTimeout(() => {
        printWindow.print();
    }, 500);
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.showPdfModal = showPdfModal;
    window.closePdfModal = closePdfModal;
    window.openCurrentRegulationPdf = openCurrentRegulationPdf;
    window.openComparisonTablePdf = openComparisonTablePdf;
    window.openPdfViewer = openPdfViewer;
    window.printRegulation = printRegulation;
    window.openAppendixPdf = openAppendixPdf;
}
