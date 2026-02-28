# sgk_extract/les_top_pipeline.py
from __future__ import annotations

from typing import Any, Dict
from .pdf_output import prepare_workspace, save_manifest, split_from_manifest
from .prompts import build_topic_lesson_prompt
from .gemini_runner import extract_structure_from_pdf


def run_extract_save_split(key_manager, pdf_path: str, model: str = "gemini-2.5-flash"):
    prompt = build_topic_lesson_prompt()

    # 1) Gemini -> dict (runner tự rotate key)
    data: Dict[str, Any] = extract_structure_from_pdf(key_manager, pdf_path, prompt, model=model)

    # 2) Tạo workspace Output/<pdf_stem>/
    ws = prepare_workspace(pdf_path, output_root="Output")
    base_dir = ws["base_dir"]
    pdf_stem = __import__("pathlib").Path(pdf_path).stem

    # 3) Lưu JSON
    json_path = save_manifest(base_dir, pdf_stem, data)

    # 4) Cắt PDF
    split_result = split_from_manifest(pdf_path, data, base_dir)

    return data, str(json_path), split_result
