#sgk_extract/pdf_output.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from pypdf import PdfReader, PdfWriter


def project_root_from_here() -> Path:
    # file này nằm ở: <root>/sgk_extract/pdf_output.py
    return Path(__file__).resolve().parents[1]


def prepare_workspace(pdf_path: str, output_root: str | Path = "Output") -> Dict[str, Path]:
    """
    Tạo cấu trúc:
    Output/<pdf_stem>/
      <pdf_stem>.json
      Topic/
      Lesson/
    """
    pdf = Path(pdf_path)
    stem = pdf.stem

    root = Path(output_root)
    if not root.is_absolute():
        root = project_root_from_here() / root

    base_dir = root / stem
    topic_dir = base_dir / "Topic"
    lesson_dir = base_dir / "Lesson"

    topic_dir.mkdir(parents=True, exist_ok=True)
    lesson_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": root,
        "base_dir": base_dir,
        "topic_dir": topic_dir,
        "lesson_dir": lesson_dir,
        "stem": Path(stem),  # dùng Path để tránh lỗi kiểu, thực tế chỉ cần stem string
    }


def save_manifest(base_dir: Path, pdf_stem: str, data: dict) -> Path:
    out_path = base_dir / f"{pdf_stem}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def _flatten_list_ranges(list_ranges: List[Dict[str, Dict[str, int]]]) -> List[Tuple[str, int, int]]:
    """
    Input:
      [{"topic_01": {"start": 7, "end": 38}}, {"topic_02": {"start": 39, "end": 55}}]
    Output:
      [("topic_01", 7, 38), ("topic_02", 39, 55)]
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
    out_dir: Path,
    pdf_stem: str,
) -> List[Path]:
    """
    - start/end là PDF pages 1-based, inclusive.
    - Xuất file: <pdf_stem>_<name>.pdf vào out_dir
      Ví dụ: test1_topic_01.pdf
    """
    reader = PdfReader(src_pdf)
    total_pages = len(reader.pages)

    outputs: List[Path] = []

    for name, start, end in ranges:
        # validate
        if start < 1 or end < 1 or start > end:
            continue
        if start > total_pages:
            continue

        end = min(end, total_pages)

        writer = PdfWriter()
        for idx in range(start - 1, end):  # end inclusive
            writer.add_page(reader.pages[idx])

        safe_name = name.replace("/", "_").replace("\\", "_").strip()
        out_path = out_dir / f"{pdf_stem}_{safe_name}.pdf"

        with open(out_path, "wb") as f:
            writer.write(f)

        outputs.append(out_path)

    return outputs


def split_from_manifest(src_pdf: str, data: Dict[str, Any], base_dir: Path) -> Dict[str, List[str]]:
    """
    Tạo:
      base_dir/Topic/<pdf_stem>_topic_01.pdf
      base_dir/Lesson/<pdf_stem>_lesson_01.pdf
    """
    pdf_stem = Path(src_pdf).stem
    topic_dir = base_dir / "Topic"
    lesson_dir = base_dir / "Lesson"
    topic_dir.mkdir(parents=True, exist_ok=True)
    lesson_dir.mkdir(parents=True, exist_ok=True)

    result = {"topics": [], "lessons": []}

    if isinstance(data.get("list_topic"), list):
        topic_ranges = _flatten_list_ranges(data["list_topic"])
        paths = split_pdf_by_ranges(src_pdf, topic_ranges, topic_dir, pdf_stem)
        result["topics"] = [str(p) for p in paths]

    if isinstance(data.get("list_lesson"), list):
        lesson_ranges = _flatten_list_ranges(data["list_lesson"])
        paths = split_pdf_by_ranges(src_pdf, lesson_ranges, lesson_dir, pdf_stem)
        result["lessons"] = [str(p) for p in paths]

    return result
