"""
PDF에서 표 영역을 감지하고 고해상도 이미지로 크롭하는 모듈

PyMuPDF(fitz)를 사용하여 PDF 페이지의 drawing 요소(직선, 사각형)를
클러스터링하여 개별 표를 감지하고, 300 DPI로 렌더링합니다.

표는 문서 끝부분(별표/별첨/별지)에 위치하며, drawing 요소가 10개 이상인
페이지에서만 감지합니다. 헤더 수평선(drawings=1)은 자동 제외됩니다.
"""

import os
import re
import base64
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import fitz  # PyMuPDF


@dataclass
class TableRegion:
    """감지된 표 영역 정보"""
    page_num: int
    bbox: Any  # fitz.Rect
    num_drawings: int
    title_text: str = ""
    table_text: str = ""


class PdfTableCropper:
    """
    PDF에서 표를 감지하여 고해상도 이미지로 크롭하는 클래스.
    DocxTableRenderer / TableToImageConverter와 동일한 출력 인터페이스를 제공합니다.
    """

    # 페이지 헤더 수평선을 무시하기 위한 최소 drawing 수
    MIN_PAGE_DRAWINGS = 10

    # 표 클러스터 분리를 위한 y축 최소 간격(pt)
    CLUSTER_GAP = 20.0

    # 클러스터 내 최소 rect 수 (이보다 적으면 표가 아님)
    MIN_CLUSTER_RECTS = 3

    # 최소 표 높이(pt)
    MIN_TABLE_HEIGHT = 20.0

    # 제목 텍스트 감지용 키워드 (별표/별지 제목, 단위 등)
    TITLE_KEYWORDS = ["별표", "별지", "별첨", "단위", "정액표", "지급표",
                      "기준표", "서식"]

    def __init__(self, output_dir: str = "extracted_images",
                 article_range: Optional[Tuple[int, int]] = None,
                 dpi: int = 300,
                 margin: float = 3.0,
                 **kwargs):
        self.output_dir = output_dir
        self.article_range = article_range
        self.dpi = dpi
        self.margin = margin

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def extract_tables_as_images(self, pdf_path: str, document_name: str) -> List[Dict[str, Any]]:
        """
        PDF 파일에서 표를 감지하여 고해상도 이미지로 추출합니다.

        Args:
            pdf_path: PDF 파일 경로
            document_name: 문서 이름 (이미지 파일명 접두사)

        Returns:
            추출된 표 이미지 정보 리스트
        """
        doc = fitz.open(pdf_path)
        table_regions = self._detect_all_tables(doc)

        if self.article_range:
            table_regions = self._filter_by_article_range(doc, table_regions)

        table_regions = self._filter_metadata_tables(table_regions)

        print(f"[PdfTableCropper] PDF에서 감지된 표 개수: {len(table_regions)}")

        table_images = []
        for table_idx, region in enumerate(table_regions):
            try:
                image_info = self._crop_table(doc, region, document_name, table_idx)
                if image_info:
                    table_images.append(image_info)
                    print(f"  ✓ 표 {table_idx} 크롭 완료 (page {region.page_num + 1})")
            except Exception as e:
                print(f"  ✗ 표 {table_idx} 크롭 실패: {e}")
                continue

        doc.close()
        return table_images

    # ── 표 감지 ─────────────────────────────────────────

    def _detect_all_tables(self, doc: fitz.Document) -> List[TableRegion]:
        """
        모든 페이지에서 표 영역을 감지합니다.
        표는 문서 끝부분(별표/별첨)에 위치하며, drawing 요소가
        MIN_PAGE_DRAWINGS개 이상인 페이지에서만 탐색합니다.
        """
        all_tables = []

        for page_num in range(doc.page_count):
            page = doc[page_num]
            drawings = page.get_drawings()

            # 헤더 수평선(1~2개)만 있는 페이지는 스킵
            if len(drawings) < self.MIN_PAGE_DRAWINGS:
                continue

            page_tables = self._cluster_drawings_to_tables(page, drawings)
            all_tables.extend(page_tables)

        return all_tables

    def _cluster_drawings_to_tables(self, page: fitz.Page,
                                     drawings: list) -> List[TableRegion]:
        """
        drawing 요소를 y좌표 기준으로 클러스터링하여 개별 표 영역을 분리합니다.
        페이지 상단 헤더 영역(y < 80)의 단독 수평선은 제외합니다.
        """
        all_rects = [d['rect'] for d in drawings if d.get('rect')]
        if not all_rects:
            return []

        sorted_rects = sorted(all_rects, key=lambda r: r.y0)

        # 클러스터링
        clusters = []
        current_cluster = [sorted_rects[0]]

        for r in sorted_rects[1:]:
            prev_bottom = max(cr.y1 for cr in current_cluster)
            if r.y0 - prev_bottom > self.CLUSTER_GAP:
                clusters.append(current_cluster)
                current_cluster = [r]
            else:
                current_cluster.append(r)
        clusters.append(current_cluster)

        # 각 클러스터를 TableRegion으로 변환
        tables = []
        for cluster in clusters:
            if len(cluster) < self.MIN_CLUSTER_RECTS:
                continue

            min_x = min(r.x0 for r in cluster)
            max_x = max(r.x1 for r in cluster)
            # 얇은 장식선(밑줄 등, height < 1pt)은 min_y 계산에서 제외
            substantial_rects = [r for r in cluster if (r.y1 - r.y0) >= 1.0]
            min_y = min(r.y0 for r in substantial_rects) if substantial_rects else min(r.y0 for r in cluster)
            max_y = max(r.y1 for r in cluster)

            height = max_y - min_y
            if height < self.MIN_TABLE_HEIGHT:
                continue

            # 페이지 상단 헤더 수평선만으로 구성된 클러스터 제외
            # (높이가 5pt 미만이고 y < 80 영역)
            if height < 5 and max_y < 80:
                continue

            bbox = fitz.Rect(min_x, min_y, max_x, max_y)

            # 표 위 제목 텍스트 (별표/별첨 제목 포함)
            title_y = max(0, min_y - 80)
            title_text = page.get_text(
                "text", clip=fitz.Rect(min_x, title_y, max_x, min_y)
            ).strip()

            # 표 내부 텍스트
            table_text = page.get_text("text", clip=bbox).strip()

            tables.append(TableRegion(
                page_num=page.number,
                bbox=bbox,
                num_drawings=len(cluster),
                title_text=title_text,
                table_text=table_text,
            ))

        return tables

    # ── 필터링 ──────────────────────────────────────────

    def _filter_by_article_range(self, doc: fitz.Document,
                                  tables: List[TableRegion]) -> List[TableRegion]:
        """조문 범위로 필터링합니다."""
        if not self.article_range:
            return tables

        start_article, end_article = self.article_range

        page_articles = {}
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text")
            articles = re.findall(r'제\s*(\d+)\s*조', text)
            if articles:
                page_articles[page_num] = [int(a) for a in articles]

        filtered = []
        for table in tables:
            page_num = table.page_num
            current_article = 0
            for pn in range(page_num + 1):
                if pn in page_articles:
                    current_article = max(page_articles[pn])

            if start_article <= current_article <= end_article:
                filtered.append(table)
            elif current_article == 0:
                # 조문 번호가 없는 페이지의 표 (별표 등)
                filtered.append(table)

        return filtered

    def _filter_metadata_tables(self, tables: List[TableRegion]) -> List[TableRegion]:
        """
        메타데이터 표를 제외합니다.
        - 제정일/개정일/검토일/소관부서 (문서 헤더)
        - 승인란 (병원장, (인))
        - 제·개정 연혁
        """
        metadata_patterns = [
            "제정일", "최종개정일", "최종검토일", "소관부서",
            "승인", "승  인", "병원장", "(인)",
            "제·개정 연혁", "제·개정연혁", "제개정 연혁", "제개정연혁",
        ]

        filtered = []
        for table in tables:
            text = table.table_text
            is_metadata = any(p in text for p in metadata_patterns)

            # 메타데이터 패턴이 있더라도 실질적 데이터가 많으면(200자 초과) 포함
            if is_metadata and len(text) < 200:
                print(f"  [필터] 메타 표 제외 (page {table.page_num + 1}): {text[:50]}...")
                continue

            filtered.append(table)

        return filtered

    # ── 크롭 및 저장 ────────────────────────────────────

    def _find_title_top_y(self, page: fitz.Page, table_bbox) -> float:
        """
        표 위의 제목 텍스트(별표 제N호, 부제목, 단위 등)의
        상단 y좌표를 찾습니다.

        알고리즘: 표 상단에서 위로 올라가며 인접 텍스트 블록을 포함.
        - gap ≤ 15pt: 무조건 포함 (인접 텍스트)
        - gap > 15pt: 제목 키워드(별표, 단위 등)가 있을 때만 포함
        """
        search_y = max(0, table_bbox.y0 - 80)

        text_dict = page.get_text("dict", clip=fitz.Rect(
            0, search_y, page.rect.width, table_bbox.y0
        ))

        text_blocks = []
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span["text"]
            block_text = block_text.strip()
            if block_text:
                text_blocks.append({
                    "y0": block["bbox"][1],
                    "y1": block["bbox"][3],
                    "text": block_text,
                })

        if not text_blocks:
            return table_bbox.y0

        # 아래에서 위로 정렬 (표에 가까운 것부터)
        text_blocks.sort(key=lambda b: b["y1"], reverse=True)

        title_top_y = table_bbox.y0
        prev_y0 = table_bbox.y0

        for block in text_blocks:
            gap = prev_y0 - block["y1"]
            if gap <= 15:
                title_top_y = block["y0"]
                prev_y0 = block["y0"]
            elif any(kw in block["text"] for kw in self.TITLE_KEYWORDS):
                title_top_y = block["y0"]
                prev_y0 = block["y0"]
            else:
                break

        return title_top_y

    def _crop_table(self, doc: fitz.Document, region: TableRegion,
                    document_name: str, table_idx: int) -> Optional[Dict[str, Any]]:
        """표 영역을 고해상도 이미지로 크롭합니다. 표 그리드만 포함."""
        page = doc[region.page_num]

        # 표 그리드 시작점부터만 크롭 (제목/단위 텍스트 제외)
        title_top_y = region.bbox.y0

        m = self.margin
        clip = fitz.Rect(
            max(0, region.bbox.x0 - m),
            max(0, title_top_y - m),
            min(page.rect.width, region.bbox.x1 + m),
            min(page.rect.height, region.bbox.y1 + m),
        )

        # 고해상도 렌더링
        scale = self.dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, clip=clip)

        png_bytes = pix.tobytes("png")

        # 파일 저장
        table_filename = f"{document_name}_table_{table_idx}.png"
        table_filepath = os.path.join(self.output_dir, table_filename)
        with open(table_filepath, "wb") as f:
            f.write(png_bytes)

        # Base64 인코딩
        base64_data = base64.b64encode(png_bytes).decode('utf-8')

        # 웹 경로 변환
        web_path = table_filepath
        for marker in ('/www/static/', '/fastapi/static/', '/applib/static/'):
            if marker in table_filepath:
                web_path = '/static/' + table_filepath.split(marker)[1]
                break

        # 표 텍스트 → 2차원 배열 근사 (섹션 매칭용)
        table_data = self._extract_table_data_from_text(region.table_text)

        return {
            "table_index": table_idx,
            "file_name": table_filename,
            "file_path": web_path,
            "content_type": "image/png",
            "base64_data": f"data:image/png;base64,{base64_data}",
            "table_data": table_data,
            "rows": len(table_data),
            "cols": max((len(r) for r in table_data), default=0),
            "previous_text": region.title_text,
            "next_text": "",
            "context": "표",
            "table_location": f"PDF 페이지 {region.page_num + 1}",
        }

    @staticmethod
    def _extract_table_data_from_text(text: str) -> List[List[str]]:
        """표 영역의 텍스트를 2차원 배열로 근사 추출합니다."""
        if not text:
            return []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return [[line] for line in lines[:20]]


def find_matching_pdf(docx_path: str, pdf_search_dirs: Optional[List[str]] = None) -> Optional[str]:
    """
    DOCX/DOC 파일에 대응하는 PDF 파일을 찾습니다.

    탐색 순서:
    1. DOCX와 같은 디렉토리
    2. settings.PDF_DIR (applib/pdf/)
    3. settings.WWW_STATIC_PDF_DIR
    4. pdf_search_dirs에 지정된 추가 디렉토리

    Args:
        docx_path: DOCX/DOC 파일 경로
        pdf_search_dirs: 추가로 탐색할 디렉토리 목록

    Returns:
        PDF 파일 경로 (없으면 None)
    """
    # .docx 또는 .doc 확장자 모두 처리
    basename = os.path.basename(docx_path)
    name_without_ext = os.path.splitext(basename)[0]
    pdf_filename = name_without_ext + ".pdf"

    search_dirs = []

    # 1. DOCX와 같은 디렉토리
    search_dirs.append(os.path.dirname(docx_path))

    # 2. settings에서 PDF 디렉토리
    try:
        from settings import settings
        search_dirs.append(settings.PDF_DIR)
        search_dirs.append(settings.WWW_STATIC_PDF_DIR)
    except ImportError:
        pass

    # 3. 추가 디렉토리
    if pdf_search_dirs:
        search_dirs.extend(pdf_search_dirs)

    for search_dir in search_dirs:
        if not search_dir or not os.path.isdir(search_dir):
            continue
        pdf_path = os.path.join(search_dir, pdf_filename)
        if os.path.isfile(pdf_path):
            return pdf_path

    return None
