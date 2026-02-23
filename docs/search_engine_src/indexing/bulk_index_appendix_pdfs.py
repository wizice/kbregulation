#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 부록 대량 텍스트 추출 및 색인
wz_appendix 테이블의 286개 PDF를 모두 처리
"""
import sys
import os
import psycopg2
from pathlib import Path
from datetime import datetime
import time

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'applib'))
from pdf2txt import extract_text_from_pdf

# DB 연결 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 35432,
    'database': 'severance',
    'user': 'severance',
    'password': 'rkatkseverance!'
}

def bulk_index_pdfs():
    """PDF 부록 대량 색인"""

    print("=" * 80)
    print("PDF 부록 대량 텍스트 추출 및 색인")
    print("=" * 80)
    print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 출력 디렉토리 설정
    project_root = Path("/home/wizice/regulation")
    output_dir = project_root / "www" / "static" / "pdf_txt"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 출력 디렉토리: {output_dir}")
    print()

    # DB 연결
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 전체 PDF 목록 조회
    print("🔍 PDF 부록 목록 조회 중...")
    cur.execute("""
        SELECT
            wzappendixseq,
            wzruleseq,
            wzappendixno,
            wzappendixname,
            wzfilepath
        FROM wz_appendix
        WHERE wzfilepath IS NOT NULL
          AND wzfilepath LIKE '%.pdf'
        ORDER BY wzappendixseq
    """)

    appendices = cur.fetchall()
    total = len(appendices)

    print(f"✓ 총 {total}개 PDF 발견\n")

    # 통계 변수
    success_count = 0
    skip_count = 0
    error_count = 0
    total_size = 0
    total_txt_size = 0
    errors = []
    skipped = []  # 건너뛴 파일 목록

    start_time = time.time()

    # 각 PDF 처리
    for idx, (seq, rule_seq, appendix_no, name, filepath) in enumerate(appendices, 1):
        # 진행률 표시
        progress = (idx / total) * 100
        elapsed = time.time() - start_time
        avg_time = elapsed / idx if idx > 0 else 0
        remaining = avg_time * (total - idx)

        print(f"\r[{idx}/{total}] {progress:.1f}% | "
              f"성공:{success_count} 건너뜀:{skip_count} 실패:{error_count} | "
              f"남은시간:{remaining/60:.1f}분", end='', flush=True)

        # 소방계획서 제외 (페이지가 너무 많아 처리 시간이 오래 걸림)
        if '소방계획서' in name or '소방계획서' in filepath:
            skip_count += 1
            skipped.append({'seq': seq, 'name': name, 'reason': 'LARGE_FILE_EXCLUDED'})
            continue

        # 파일 경로 처리
        if filepath.startswith('www/'):
            pdf_path = project_root / filepath
        else:
            pdf_path = project_root / 'www' / 'static' / 'pdf' / Path(filepath).name

        # 파일 존재 확인
        if not pdf_path.exists():
            error_count += 1
            errors.append({
                'seq': seq,
                'name': name,
                'error': 'FILE_NOT_FOUND',
                'path': str(pdf_path)
            })
            continue

        # 출력 파일 경로 생성 (원본 파일명 기반)
        txt_filename = pdf_path.stem + '.txt'
        txt_path = output_dir / txt_filename

        # 이미 처리된 파일은 건너뛰기 (선택적)
        if txt_path.exists():
            skip_count += 1
            skipped.append({'seq': seq, 'name': name, 'reason': 'ALREADY_EXISTS'})
            continue

        # 텍스트 추출
        try:
            result = extract_text_from_pdf(str(pdf_path), str(txt_path))

            if result and txt_path.exists():
                file_size = pdf_path.stat().st_size
                txt_size = txt_path.stat().st_size
                total_size += file_size
                total_txt_size += txt_size
                success_count += 1

                # 10개마다 상세 로그
                if idx % 10 == 0:
                    print(f"\n  [{idx}] ✓ {name[:50]}... ({file_size/1024:.1f}KB → {txt_size/1024:.1f}KB)")
            else:
                error_count += 1
                errors.append({
                    'seq': seq,
                    'name': name,
                    'error': 'EXTRACTION_FAILED'
                })

        except Exception as e:
            error_count += 1
            errors.append({
                'seq': seq,
                'name': name,
                'error': str(e)
            })

    # 최종 통계
    elapsed_total = time.time() - start_time

    print("\n")
    print("=" * 80)
    print("📊 색인 작업 완료")
    print("=" * 80)
    print(f"\n종료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"소요 시간: {elapsed_total/60:.1f}분 ({elapsed_total:.1f}초)")
    print()

    print("📈 처리 결과:")
    print(f"  • 전체: {total}개")
    print(f"  • 성공: {success_count}개 ({success_count/total*100:.1f}%)")
    print(f"  • 건너뜀: {skip_count}개 ({skip_count/total*100:.1f}%)")
    print(f"  • 실패: {error_count}개 ({error_count/total*100:.1f}%)")
    print()

    if success_count > 0:
        print("💾 파일 크기:")
        print(f"  • 원본 PDF 합계: {total_size/1024/1024:.1f} MB")
        print(f"  • 추출 텍스트 합계: {total_txt_size/1024/1024:.1f} MB")
        print(f"  • 압축률: {(total_txt_size/total_size)*100:.1f}%")
        print()

        print(f"📁 출력 위치: {output_dir}")
        print()

    # 건너뛴 파일 상세
    if skipped:
        print(f"⏭️  건너뛴 파일 ({len(skipped)}개):")
        # 사유별 분류
        by_reason = {}
        for s in skipped:
            reason = s['reason']
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(s)

        for reason, items in by_reason.items():
            reason_kr = {
                'ALREADY_EXISTS': '이미 처리됨',
                'LARGE_FILE_EXCLUDED': '대용량 파일 제외'
            }.get(reason, reason)
            print(f"  [{reason_kr}] {len(items)}개:")
            for item in items[:5]:  # 각 사유별 5개만 표시
                print(f"    - [{item['seq']}] {item['name'][:50]}")
            if len(items) > 5:
                print(f"    ... 외 {len(items)-5}개")
        print()

    # 에러 상세
    if errors:
        print(f"❌ 실패한 파일 ({len(errors)}개):")
        for i, err in enumerate(errors[:10], 1):  # 처음 10개만 표시
            print(f"  {i}. [{err['seq']}] {err['name'][:60]}")
            print(f"     에러: {err['error']}")
        if len(errors) > 10:
            print(f"  ... 외 {len(errors)-10}개")
        print()

    # 로그 파일 저장 (건너뛴 파일 + 에러)
    if skipped or errors:
        log_path = project_root / 'fastapi' / 'bulk_index_report.log'
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"PDF 부록 색인 리포트\n")
            f.write(f"생성일시: {datetime.now()}\n")
            f.write(f"=" * 60 + "\n\n")

            if skipped:
                f.write(f"[건너뛴 파일] {len(skipped)}개\n")
                f.write("-" * 40 + "\n")
                for s in skipped:
                    f.write(f"SEQ: {s['seq']}\n")
                    f.write(f"이름: {s['name']}\n")
                    f.write(f"사유: {s['reason']}\n\n")
                f.write("\n")

            if errors:
                f.write(f"[실패한 파일] {len(errors)}개\n")
                f.write("-" * 40 + "\n")
                for err in errors:
                    f.write(f"SEQ: {err['seq']}\n")
                    f.write(f"이름: {err['name']}\n")
                    f.write(f"에러: {err['error']}\n")
                    if 'path' in err:
                        f.write(f"경로: {err['path']}\n")
                    f.write("\n")

        print(f"📝 상세 리포트: {log_path}")

    print("=" * 80)

    cur.close()
    conn.close()

if __name__ == '__main__':
    try:
        bulk_index_pdfs()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 작업을 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()
