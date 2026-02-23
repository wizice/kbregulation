#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import glob
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException
from applib.merge_json import JSONMerger
from app_logger import get_logger

logger = get_logger(__name__)


class MergeOnlyService:
    """병합 전용 서비스 - 업로드/파싱 없이 기존 JSON 파일만 병합"""

    def __init__(self):
        self.docx_json_dir = Path("applib/docx_json")
        self.txt_json_dir = Path("applib/txt_json")
        self.output_dir = Path("applib/merge_json")
        self.output_dir.mkdir(exist_ok=True)

    async def merge_regulation_111(self) -> Dict[str, Any]:
        """
        1.1.1 규정의 최신 docx_json과 txt_json 파일을 찾아서 병합
        """
        try:
            # 1. 최신 1.1.1 파일 찾기
            docx_file = self._find_latest_111_file(self.docx_json_dir)
            txt_file = self._find_latest_111_file(self.txt_json_dir)

            if not docx_file and not txt_file:
                raise HTTPException(
                    status_code=404,
                    detail="1.1.1 규정 파일을 찾을 수 없습니다"
                )

            logger.info(f"DOCX JSON: {docx_file}")
            logger.info(f"TXT JSON: {txt_file}")

            # 2. JSONMerger로 병합
            merger = JSONMerger(
                pdf_json_path=txt_file,
                docx_json_path=docx_file
            )

            # JSON 파일 로드
            merger.load_json_files()

            # 병합
            merged_data = merger.merge_json()

            if not merged_data:
                raise HTTPException(
                    status_code=500,
                    detail="병합 실패: 데이터가 비어있습니다"
                )

            # 3. 병합 결과 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"merged_1.1.1_정확한_환자_확인_{timestamp}.json"
            output_path = self.output_dir / output_filename

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)

            logger.info(f"병합 완료: {output_path}")

            return {
                "success": True,
                "message": "1.1.1 규정 병합 완료",
                "docx_file": os.path.basename(docx_file) if docx_file else None,
                "txt_file": os.path.basename(txt_file) if txt_file else None,
                "output_file": str(output_path),
                "timestamp": timestamp,
                "merged_content": merged_data
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"병합 중 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _find_latest_111_file(self, directory: Path) -> Optional[str]:
        """
        디렉토리에서 가장 최근의 1.1.1 파일 찾기
        """
        # 여러 패턴으로 검색
        patterns = [
            "*1.1.1*정확한*환자*확인*.json",
            "*1.1.1.*json",
            "1.1.1*.json"
        ]

        all_files = []
        for pattern in patterns:
            files = list(directory.glob(pattern))
            all_files.extend(files)

        # 중복 제거
        all_files = list(set(all_files))

        if not all_files:
            return None

        # 수정 시간 기준으로 정렬하여 최신 파일 선택
        latest_file = max(all_files, key=lambda f: f.stat().st_mtime)

        return str(latest_file)

    async def get_available_111_files(self) -> Dict[str, Any]:
        """
        사용 가능한 1.1.1 파일 목록 조회
        """
        docx_files = sorted(
            [f.name for f in self.docx_json_dir.glob("*1.1.1*.json")],
            reverse=True
        )[:5]  # 최근 5개만

        txt_files = sorted(
            [f.name for f in self.txt_json_dir.glob("*1.1.1*.json")],
            reverse=True
        )[:5]  # 최근 5개만

        return {
            "docx_json_files": docx_files,
            "txt_json_files": txt_files,
            "latest_docx": docx_files[0] if docx_files else None,
            "latest_txt": txt_files[0] if txt_files else None
        }


# 서비스 인스턴스 생성
merge_only_service = MergeOnlyService()