# sgk_extract/chunk_pipeline.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pypdf import PdfReader

from .gemini_runner import extract_structure_from_pdf
from .prompts import build_chunk_prompt_start_head
from .pdf_output import split_pdf_by_ranges


def _flatten_start_head(list_chunk: List[Dict[str, Dict[str, Any]]]) -> List[Tuple[int, bool, str, str]]:
    """
    Input (Gemini):
      [{"chunk_01":{"start":1,"content_head":false,"heading":"1.","title":"ABC"}}, ...]
    Output (sorted):
      [(start, content_head, heading, title), ...]
    """
    out: List[Tuple[int, bool, str, str]] = []
    for item in list_chunk:
        if not isinstance(item, dict) or len(item) != 1:
            continue
        _name, obj = next(iter(item.items()))
        if not isinstance(obj, dict):
            continue

        s = obj.get("start")
        ch = obj.get("content_head")
        heading = obj.get("heading", "")
        title = obj.get("title", "")

        if isinstance(s, int) and isinstance(ch, bool) and isinstance(title, str) and isinstance(heading, str):
            out.append((s, ch, heading.strip(), title.strip()))

    out.sort(key=lambda x: x[0])
    return out


def _compute_chunks_from_start_head(
    items: List[Tuple[int, bool, str, str]],
    total_pages: int,
) -> List[Dict[str, Dict[str, Any]]]:
    """
    Trả ra list_chunk đã có start/end/heading/title/content_head.
    Rule end:
      next.content_head == True  -> end = next.start
      next.content_head == False -> end = next.start - 1
    Fallback:
      nếu items rỗng -> chunk_01: 1..total_pages, heading="", title="KHÔNG CÓ MỤC CHÍNH"
    """
    if total_pages < 1:
        return []

    if not items:
        return [
            {"chunk_01": {"start": 1, "end": total_pages, "content_head": False, "heading": "", "title": "KHÔNG CÓ MỤC CHÍNH"}}
        ]

    fixed: List[Tuple[int, bool, str, str]] = []
    for idx, (s, ch, heading, title) in enumerate(items):
        s = max(1, min(s, total_pages))
        heading = (heading or "").strip()
        title = (title or "").strip()

        if idx == 0:
            s = 1
            ch = False
            # nếu Gemini có trả heading thì tốt, không thì để ""
            # heading = heading or "1."  # (tuỳ bạn có muốn ép không)
        fixed.append((s, ch, heading, title))

    computed: List[Dict[str, Dict[str, Any]]] = []

    for i in range(len(fixed)):
        start, ch, heading, title = fixed[i]

        if i < len(fixed) - 1:
            next_start, next_ch, _next_heading, _next_title = fixed[i + 1]
            end = next_start if next_ch else (next_start - 1)
            end = max(start, min(end, total_pages))
        else:
            end = total_pages

        chunk_name = f"chunk_{i+1:02d}"
        computed.append(
            {chunk_name: {"start": start, "end": end, "content_head": ch, "heading": heading, "title": title}}
        )

    return computed


def _to_ranges(list_chunk_computed: List[Dict[str, Dict[str, Any]]]) -> List[Tuple[str, int, int]]:
    """
    [{"chunk_01": {"start":1,"end":3,...}}, ...]
    -> [("chunk_01",1,3), ...]
    """
    ranges: List[Tuple[str, int, int]] = []
    for item in list_chunk_computed:
        if not isinstance(item, dict) or len(item) != 1:
            continue
        name, obj = next(iter(item.items()))
        if not isinstance(obj, dict):
            continue
        s = obj.get("start")
        e = obj.get("end")
        if isinstance(s, int) and isinstance(e, int):
            ranges.append((str(name), s, e))
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
      Output/<book_stem>/Chunk/<lesson_stem>_chunk_01.pdf ...
      Output/<book_stem>/ChunkJson/<lesson_stem>_chunk_01.json ...
    """
    book_dir = Path(book_dir)
    lesson_dir = book_dir / "Lesson"
    chunk_dir = book_dir / "Chunk"
    chunk_json_dir = book_dir / "ChunkJson"

    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_json_dir.mkdir(parents=True, exist_ok=True)

    if not lesson_dir.exists():
        raise RuntimeError(f"Không thấy thư mục Lesson: {lesson_dir}")

    lesson_pdfs = sorted(lesson_dir.glob("*.pdf"))
    if not lesson_pdfs:
        raise RuntimeError(f"Không có file PDF nào trong: {lesson_dir}")

    summary: Dict[str, Any] = {
        "book_dir": str(book_dir),
        "lesson_count": len(lesson_pdfs),
        "chunk_pdf_files": [],
        "chunk_json_files": [],
        "skipped_lessons": [],
    }

    for lesson_pdf in lesson_pdfs:
        lesson_stem = lesson_pdf.stem

        # resume: nếu đã có chunk_01 thì skip
        if resume:
            exists_any = any(chunk_dir.glob(f"{lesson_stem}_chunk_*.pdf"))
            if exists_any:
                summary["skipped_lessons"].append({"lesson": str(lesson_pdf), "reason": "Đã có chunk pdf, skip"})
                continue

        try:
            total_pages = len(PdfReader(str(lesson_pdf)).pages)

            prompt = build_chunk_prompt_start_head(total_pages=total_pages)

            raw: Dict[str, Any] = extract_structure_from_pdf(
                key_manager,
                str(lesson_pdf),
                prompt,
                model=model,
            )

            list_chunk_raw = raw.get("list_chunk")

            items: List[Tuple[int, bool, str, str]] = []

            if isinstance(list_chunk_raw, list) and list_chunk_raw:
                items = _flatten_start_head(list_chunk_raw)

            # tính list_chunk có end
            list_chunk_computed = _compute_chunks_from_start_head(items, total_pages)

            # cắt pdf
            ranges = _to_ranges(list_chunk_computed)
            if not ranges:
                summary["skipped_lessons"].append({"lesson": str(lesson_pdf), "reason": "Không tạo được chunk range"})
                continue

            paths = split_pdf_by_ranges(
                src_pdf=str(lesson_pdf),
                ranges=ranges,
                out_dir=chunk_dir,
                pdf_stem=lesson_stem,
            )
            summary["chunk_pdf_files"].extend([str(p) for p in paths])

            # xuất JSON cho từng chunk (mỗi chunk 1 file)
            for item in list_chunk_computed:
                chunk_name, obj = next(iter(item.items()))
                out_json = chunk_json_dir / f"{lesson_stem}_{chunk_name}.json"

                payload = {
                    "source_lesson_pdf": str(lesson_pdf),
                    "lesson_stem": lesson_stem,
                    "chunk": chunk_name,
                    "heading": obj.get("heading", ""),  # <-- thêm dòng này
                    "title": obj.get("title", ""),
                    "start": obj.get("start"),
                    "end": obj.get("end"),
                    "content_head": obj.get("content_head"),
                    "total_pages": total_pages,
                }

                out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                summary["chunk_json_files"].append(str(out_json))

        except Exception as e:
            summary["skipped_lessons"].append({"lesson": str(lesson_pdf), "reason": str(e)})

    return summary
