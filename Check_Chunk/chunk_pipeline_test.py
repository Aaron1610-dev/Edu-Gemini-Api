#sgk_extract/chunk_json_pipeline.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pypdf import PdfReader

from .gemini_runner import extract_structure_from_pdf
from .prompts import build_chunk_prompt_start_head


def _flatten_start_head(list_chunk: List[Dict[str, Dict[str, Any]]]) -> List[Tuple[str, int, bool]]:
    """
    [{"chunk_01":{"start":1,"content_head":false}}, ...]
    -> [("chunk_01", 1, False), ...] sorted by start
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


def _compute_end(items: List[Tuple[str, int, bool]], total_pages: int) -> List[Dict[str, Dict[str, Any]]]:
    """
    Quy tắc:
    - chunk_01: content_head=false, start=1
    - end_i phụ thuộc content_head của chunk_(i+1):
        next.content_head == True  -> end_i = next.start
        next.content_head == False -> end_i = next.start - 1
    - chunk_last.end = total_pages
    """
    if not items:
        return []

    fixed: List[Tuple[str, int, bool]] = []
    for idx, (name, s, ch) in enumerate(items):
        s = max(1, min(s, total_pages))
        if idx == 0:
            s = 1
            ch = False
        fixed.append((name, s, ch))

    result: List[Dict[str, Dict[str, Any]]] = []

    for i in range(len(fixed)):
        name, start, ch = fixed[i]
        if i < len(fixed) - 1:
            next_name, next_start, next_ch = fixed[i + 1]
            end = next_start if next_ch else (next_start - 1)
            end = max(start, min(end, total_pages))
        else:
            end = total_pages

        result.append(
            {name: {"start": start, "content_head": ch, "end": end}}
        )

    return result


def extract_chunk_json(
    key_manager,
    lesson_pdf_path: str,
    model: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """
    Return dict có end đã tính:
    {"list_chunk": [{"chunk_01": {"start":..,"content_head":..,"end":..}}, ...]}
    """
    total_pages = len(PdfReader(lesson_pdf_path).pages)
    prompt = build_chunk_prompt_start_head(total_pages)

    raw: Dict[str, Any] = extract_structure_from_pdf(
        key_manager,
        lesson_pdf_path,
        prompt,
        model=model,
    )

    list_chunk = raw.get("list_chunk")
    if not isinstance(list_chunk, list) or not list_chunk:
        return {"list_chunk": []}

    items = _flatten_start_head(list_chunk)
    computed = _compute_end(items, total_pages)

    return {"list_chunk": computed, "total_pages": total_pages}


def save_chunk_json(lesson_pdf_path: str, out_dir: str | Path, data: Dict[str, Any]) -> str:
    lesson_pdf = Path(lesson_pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{lesson_pdf.stem}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_path)
