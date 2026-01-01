# sgk_extract/pdf_splitter.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple, Dict, Any, List
from pypdf import PdfReader, PdfWriter


def _flatten_list_ranges(list_ranges: List[Dict[str, Dict[str, int]]]) -> List[Tuple[str, int, int]]:
    """
    Input: [{"topic_01": {"start": 7, "end": 38}}, {"topic_02": {"start": 39, "end": 55}}]
    Output: [("topic_01", 7, 38), ("topic_02", 39, 55)]
    """
    out: List[Tuple[str, int, int]] = []
    for item in list_ranges:
        if not isinstance(item, dict) or len(item) != 1:
            continue
        name, rng = next(iter(item.items()))
        if not isinstance(rng, dict):
            continue
        start = rng.get("start")
        end = rng.get("end")
        if isinstance(start, int) and isinstance(end, int):
            out.append((str(name), start, end))
    return out


def split_pdf_by_ranges(
    src_pdf: str,
    ranges: Iterable[Tuple[str, int, int]],
    out_dir: str,
) -> List[str]:
    """
    - start/end là PDF pages 1-based, inclusive.
    - pypdf dùng index 0-based => page_idx = start-1 ... end-1
    Returns: list đường dẫn file đã xuất.
    """
    out_paths: List[str] = []
    out_path_dir = Path(out_dir)
    out_path_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(src_pdf)
    total_pages = len(reader.pages)

    for name, start, end in ranges:
        if start < 1 or end < 1 or start > end:
            # bỏ qua range lỗi
            continue
        if start > total_pages:
            continue

        # clamp end không vượt quá tổng trang
        end = min(end, total_pages)

        writer = PdfWriter()
        for idx in range(start - 1, end):  # end inclusive
            writer.add_page(reader.pages[idx])

        safe_name = name.replace("/", "_").replace("\\", "_").strip()
        filename = f"{safe_name}_{start:03d}-{end:03d}.pdf"
        dst = out_path_dir / filename

        with open(dst, "wb") as f:
            writer.write(f)

        out_paths.append(str(dst))

    return out_paths


def split_topics_and_lessons(src_pdf: str, data: Dict[str, Any], out_root: str = "outputs") -> Dict[str, List[str]]:
    """
    Tách cả topic và lesson (nếu có).
    Output:
    {
      "topics": [...paths...],
      "lessons": [...paths...]
    }
    """
    out_root_path = Path(out_root)
    topics_dir = out_root_path / "topics"
    lessons_dir = out_root_path / "lessons"

    result = {"topics": [], "lessons": []}

    if isinstance(data.get("list_topic"), list):
        topic_ranges = _flatten_list_ranges(data["list_topic"])
        result["topics"] = split_pdf_by_ranges(src_pdf, topic_ranges, str(topics_dir))

    if isinstance(data.get("list_lesson"), list):
        lesson_ranges = _flatten_list_ranges(data["list_lesson"])
        result["lessons"] = split_pdf_by_ranges(src_pdf, lesson_ranges, str(lessons_dir))

    return result
