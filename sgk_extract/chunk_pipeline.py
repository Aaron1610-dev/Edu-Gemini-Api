# sgk_extract/chunk_pipeline.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from pypdf import PdfReader

from .gemini_runner import extract_structure_from_pdf
from .prompts import build_chunk_prompt_start_head
from .pdf_output import split_pdf_by_ranges


def _flatten_start_head(list_chunk: List[Dict[str, Dict[str, Any]]]) -> List[Tuple[str, int, bool]]:
    """
    Input:
      [{"chunk_01":{"start":1,"content_head":false}}, {"chunk_02":{"start":2,"content_head":true}}]
    Output (sorted by start):
      [("chunk_01", 1, False), ("chunk_02", 2, True)]
    """
    out: List[Tuple[str, int, bool]] = []
    for item in list_chunk:
        if not isinstance(item, dict) or len(item) != 1:
            continue
        name, obj = next(iter(item.items()))
        if not isinstance(obj, dict):
            continue

        s = obj.get("start")
        ch = obj.get("content_head")

        if isinstance(s, int) and isinstance(ch, bool):
            out.append((str(name), s, ch))

    out.sort(key=lambda x: x[1])
    return out


def _compute_ranges_from_start_head(
    items: List[Tuple[str, int, bool]],
    total_pages: int,
) -> List[Tuple[str, int, int]]:
    """
    Nếu không có items => fallback chunk_01: 1..total_pages
    """
    if total_pages < 1:
        return []

    if not items:
        return [("chunk_01", 1, total_pages)]

    # Clamp + ép chunk_01 an toàn
    fixed: List[Tuple[str, int, bool]] = []
    for idx, (name, s, ch) in enumerate(items):
        s = max(1, min(s, total_pages))
        if idx == 0:
            s = 1
            ch = False
        fixed.append((name, s, ch))

    ranges: List[Tuple[str, int, int]] = []

    for i in range(len(fixed)):
        name, start, _ch = fixed[i]

        if i < len(fixed) - 1:
            _n_name, next_start, next_head = fixed[i + 1]
            end = next_start if next_head else (next_start - 1)
            end = max(start, min(end, total_pages))
        else:
            end = total_pages

        ranges.append((name, start, end))

    return ranges


def run_extract_and_split_chunks_for_book(
    key_manager,
    book_dir: str | Path,
    model: str = "gemini-2.5-flash",
    resume: bool = True,
) -> Dict[str, Any]:
    """
    Reads:
      Output/<book_stem>/Lesson/*.pdf

    Writes:
      Output/<book_stem>/Chunk/<lesson_stem>_chunk_01.pdf
      Output/<book_stem>/Chunk/<lesson_stem>_chunk_02.pdf
      ...
    """
    book_dir = Path(book_dir)
    lesson_dir = book_dir / "Lesson"
    chunk_dir = book_dir / "Chunk"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    if not lesson_dir.exists():
        raise RuntimeError(f"Không thấy thư mục Lesson: {lesson_dir}")

    lesson_pdfs = sorted(lesson_dir.glob("*.pdf"))
    if not lesson_pdfs:
        raise RuntimeError(f"Không có file PDF nào trong: {lesson_dir}")

    summary: Dict[str, Any] = {
        "book_dir": str(book_dir),
        "lesson_count": len(lesson_pdfs),
        "chunk_pdf_files": [],
        "skipped_lessons": [],
    }

    for lesson_pdf in lesson_pdfs:
        lesson_stem = lesson_pdf.stem  # ví dụ: Tin-hoc-10..._lesson_01

        # resume: nếu đã có chunk pdf thì skip
        if resume:
            exists_any = any(chunk_dir.glob(f"{lesson_stem}_chunk_*.pdf"))
            if exists_any:
                summary["skipped_lessons"].append({"lesson": str(lesson_pdf), "reason": "Đã có chunk pdf, skip"})
                continue

        try:
            total_pages = len(PdfReader(str(lesson_pdf)).pages)

            # 1) Prompt: chỉ lấy start + content_head
            prompt = build_chunk_prompt_start_head(total_pages=total_pages)

            # 2) Gemini -> dict
            raw: Dict[str, Any] = extract_structure_from_pdf(
                key_manager,
                str(lesson_pdf),
                prompt,
                model=model,
            )

            list_chunk = raw.get("list_chunk")

            # 3) parse start/head (có thể rỗng)
            items: List[Tuple[str, int, bool]] = []
            if isinstance(list_chunk, list) and list_chunk:
                items = _flatten_start_head(list_chunk)

            # 4) tính start/end (hàm đã fallback nếu items rỗng)
            chunk_ranges = _compute_ranges_from_start_head(items, total_pages)

            # nếu vì lý do gì đó vẫn không có range thì mới skip
            if not chunk_ranges:
                summary["skipped_lessons"].append(
                    {"lesson": str(lesson_pdf), "reason": "Không tạo được chunk range"}
                )
                continue

            # 5) cắt pdf
            paths = split_pdf_by_ranges(
                src_pdf=str(lesson_pdf),
                ranges=chunk_ranges,
                out_dir=chunk_dir,
                pdf_stem=lesson_stem,
            )
            summary["chunk_pdf_files"].extend([str(p) for p in paths])

        except Exception as e:
            summary["skipped_lessons"].append({"lesson": str(lesson_pdf), "reason": str(e)})

    return summary
