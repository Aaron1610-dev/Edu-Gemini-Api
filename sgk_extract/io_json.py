#sgk_extract/io_json.py
import json
from pathlib import Path

def save_json_next_to_pdf(pdf_path: str, data: dict) -> str:
    pdf = Path(pdf_path)
    out_path = pdf.with_suffix(".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(out_path)
